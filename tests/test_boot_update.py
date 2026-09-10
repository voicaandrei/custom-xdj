import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from index_boot_update import (FIRST_STAGE_SHA, SHA, analyze, analyze_first_stage,
                               build_constant, immediate_value, opcode, sector_table,
                               string_at)

BLOCK = ROOT / 'private/extracted/v144/main-010000-unpacked.bin'
MAIN = ROOT / 'private/extracted/v144/main.bin'
UPDATE = ROOT / 'private/originals/v144/XDJ1KMK2.UPD'
SECTOR = 0x20000


class BootUpdateHelpers(unittest.TestCase):
    def test_string_refuses_drift(self):
        data = b'hello\x00'
        self.assertEqual(string_at(data, 0, 'hello')['data_pointer'], 0xa8000000)
        with self.assertRaises(ValueError):
            string_at(data, 0, 'hallo')
        with self.assertRaises(ValueError):
            string_at(b'no terminator', 0, 'no terminator')

    def test_opcode_guard(self):
        data = bytes.fromhex('3188')
        self.assertEqual(opcode(data, 0, 0x8831)['opcode'], 0x8831)
        for pc in (-2, 1, 2):
            with self.assertRaises(ValueError):
                opcode(data, pc, 0x8831)
        with self.assertRaises(ValueError):
            opcode(data, 0, 0x8830)

    def test_sector_table_requires_contiguous_sectors(self):
        good = b''.join((SECTOR * i).to_bytes(4, 'little') for i in range(3))
        self.assertEqual(sector_table(good, 0, 3)['end_flash_offset_exclusive'], 3 * SECTOR)
        self.assertTrue(sector_table(good, 0, 3)['covers_flash_0'])
        gap = b''.join((SECTOR * i).to_bytes(4, 'little') for i in (0, 1, 3))
        with self.assertRaises(ValueError):
            sector_table(gap, 0, 3)
        unaligned = (SECTOR + 1).to_bytes(4, 'little') * 2
        with self.assertRaises(ValueError):
            sector_table(unaligned, 0, 2)
        with self.assertRaises(ValueError):
            sector_table(good, 0, 4)

    def test_hash_guard(self):
        with self.assertRaises(ValueError):
            analyze(b'not the boot block')


@unittest.skipUnless(BLOCK.exists(), 'Private 1.44 boot block absent')
class BootUpdateIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = BLOCK.read_bytes()
        cls.report = analyze(cls.data)

    def test_block_identity(self):
        self.assertEqual(self.report['image_sha256'], SHA)

    def test_boot_brings_up_usb_storage_and_gui_without_the_application(self):
        names = [task['name'] for task in self.report['boot_tasks']]
        for expected in ('usbh_ini', 'usbh_msc_driver_ini', 'usbh_load', 'gui_task_init'):
            self.assertIn(expected, names)
        for task in self.report['boot_tasks'][1:]:
            self.assertIsNotNone(task['code_file_offset_candidate'])

    def test_five_update_components_at_fixed_strides(self):
        components = self.report['components']
        self.assertEqual([c['update_filename']['text'] for c in components],
                         ['XDJ1KM2G.UPD', 'XDJ1KM2D.UPD', 'XDJ1KM2M.UPD',
                          'XDJ1KM2P.UPD', 'XDJ1KMK2.UPD'])
        self.assertEqual(components[2]['label']['text'], 'XDJ-1000MK2 MAIN')
        self.assertEqual(self.report['component_name_stride_bytes'], 14)
        self.assertEqual(self.report['component_label_stride_bytes'], 17)

    def test_update_task_descriptor_points_at_the_inspected_entry(self):
        task = self.report['update_task']
        self.assertEqual(task['entry_code_pointer'],
                         0x08000000 + task['entry_file_offset_candidate'])
        self.assertEqual(task['name']['text'], 'UpDtae_TASK')

    def test_only_selector_2_erases_the_boot_sectors(self):
        profiles = self.report['erase_profiles']
        self.assertEqual(profiles['selector_1']['first_flash_offset'], 0x40000)
        self.assertEqual(profiles['selector_1']['entry_count'], 118)
        self.assertFalse(profiles['selector_1']['covers_flash_0'])
        self.assertEqual(profiles['selector_0']['first_flash_offset'], 0xf00000)
        self.assertFalse(profiles['selector_0']['covers_flash_0'])
        self.assertEqual(profiles['selector_2']['first_flash_offset'], 0)
        self.assertEqual(profiles['selector_2']['entry_count'], 120)
        self.assertTrue(profiles['selector_2']['covers_flash_0'])
        # The block itself lives at flash 0x010000, inside the first sector.
        self.assertLess(0x10000, profiles['selector_1']['first_flash_offset'])

    def test_selector_decision_reads_byte_31_and_compares_ascii_one(self):
        decision = self.report['selector_decision']
        self.assertEqual(decision['read_byte_offset_in_record'], 31)
        self.assertEqual(decision['compare_opcode']['opcode'], 0x8831)
        self.assertEqual((decision['value_when_equal'], decision['value_otherwise']), (2, 1))
        # mov #31,r0 immediately before the byte load at the inspected site.
        self.assertEqual(int.from_bytes(self.data[0x2e82e:0x2e830], 'little'), 0xe01f)
        self.assertEqual(int.from_bytes(self.data[0x2e830:0x2e832], 'little'), 0x004c)

    def test_erase_selector_comes_from_the_checksummed_component_record(self):
        """The profile is chosen per component label, not by the container filename."""
        site = self.report['selector_decision']['inline_site']
        self.assertEqual(site['record_pointer'], 0x0815d970)
        self.assertEqual(site['immediate_31']['opcode'], 0xe01f)
        self.assertEqual(site['compare_opcode']['opcode'], 0x8831)
        # mov.l @r1,r5 ; mov.b @(r0,r5),r0 ; cmp/eq #'1' -- the record is dereferenced
        # from the pointer, and the selector reaches erase/write through the stack.
        self.assertEqual(site['record_dereference']['opcode'], 0x6512)
        self.assertEqual(site['byte_load']['opcode'], 0x005c)
        self.assertLess(site['selector_to_stack_file_offset'],
                        site['selector_from_stack_file_offset'])
        self.assertLess(site['selector_from_stack_file_offset'],
                        site['erase_write_dispatch_file_offset'])
        # The same pointer the CRC routine is handed is the one byte 31 is read from.
        decision = self.report['selector_decision']
        self.assertLess(decision['record_pointer_store_file_offset'],
                        decision['checksum_call_file_offset'])

    def test_state_machine_retries_then_idles_without_rebooting(self):
        """No medium means an error status and more waiting, not a reset loop."""
        machine = self.report['state_machine']
        self.assertEqual(machine['status_word_pointer'], 0x0815d600)
        self.assertEqual(machine['tail_loops_back_to'], machine['dispatch_head_file_offset'])
        wait = machine['media_wait']
        self.assertEqual(wait['retry_limit'], 30)
        self.assertEqual(wait['delay_argument'], 100)
        self.assertEqual(wait['status_on_exhaustion'], 128)
        self.assertIn(wait['status_on_exhaustion'], machine['observed_error_status_values'])
        # Nothing in the block touches the watchdog, so it cannot reset the unit there.
        self.assertEqual(machine['reset_register_users']['wdt_counter'], [])
        self.assertEqual(machine['reset_register_users']['wdt_control'], [])

    def test_name_scan_walks_the_five_component_filenames(self):
        scan = self.report['state_machine']['name_scan']
        self.assertEqual(scan['iterations'], len(self.report['components']))
        self.assertEqual(scan['name_stride_step'], self.report['component_name_stride_bytes'])
        self.assertEqual(sum(scan['slot_stride_steps']),
                         self.report['update_task']['component_slot_bytes'])
        self.assertEqual(scan['first_name_pointer'],
                         self.report['components'][0]['update_filename']['data_pointer'])
        self.assertEqual(scan['slot_base_pointer'],
                         self.report['update_task']['component_slot_pointer'])

    def test_completion_sets_the_terminal_status(self):
        completion = self.report['state_machine']['completion']
        self.assertEqual(completion['status_value'], 255)
        # The message pointer is two bytes before the plain string: it carries CRLF.
        end_message = self.report['messages']['update_end']
        self.assertEqual(completion['message_pointer'], end_message['data_pointer'] - 2)

    def test_immediate_value_helper(self):
        self.assertEqual(immediate_value(bytes.fromhex('1eec'), 0, 0xec1e), 30)
        self.assertEqual(immediate_value(bytes.fromhex('a0e4'), 0, 0xe4a0), -96)
        with self.assertRaises(ValueError):
            immediate_value(bytes.fromhex('1eec'), 0, 0xec1f)

    def test_checksum_is_crc16_xmodem(self):
        checksum = self.report['checksum']
        self.assertEqual(checksum['polynomial_literal_value'], 0x01102100)
        # The literal carries the polynomial shifted into bits 8..23; bit 24 is the
        # carry bit the routine tests, so it is folded into the same XOR constant.
        self.assertEqual((checksum['polynomial_literal_value'] >> 8) & 0xffff,
                         checksum['polynomial'])
        self.assertEqual(checksum['polynomial_literal_value'] & 0xff000000,
                         checksum['test_bit'])
        self.assertEqual(checksum['test_bit'], 1 << 24)
        self.assertEqual(checksum['trailing_zero_bytes'], 2)

    def test_flash_unlock_literals(self):
        commands = self.report['flash_command_addresses']
        self.assertEqual(commands['unlock_1'], 0xa0000aaa)
        self.assertEqual(commands['unlock_2'], 0xa0000554)

    @unittest.skipUnless(UPDATE.exists(), 'Private 1.44 update archive absent')
    def test_official_labels_do_not_select_the_boot_erasing_profile(self):
        """The shipped 1.44 labels end with '0' and ' ', not the '1' that picks profile 2."""
        update = UPDATE.read_bytes()
        for offset in (17, 25301273):
            self.assertNotEqual(update[offset + 31], ord('1'))
        self.assertEqual(update[17:17 + 16], b'XDJ-1000MK2 MAIN')
        self.assertEqual(update[17 + 31], ord('0'))


class FirstStageHelpers(unittest.TestCase):
    def test_build_constant_follows_the_inspected_steps(self):
        # mov #-96,r4 ; shll8 ; add #4 ; shll16  ->  0xa0040000
        data = bytes.fromhex('a0e4') + bytes.fromhex('1844') + bytes.fromhex('0474') + bytes.fromhex('2844')
        self.assertEqual(build_constant(data, (
            ('mov', 0, 0xe4a0), ('shll8', 2, 0x4418),
            ('add', 4, 0x7404), ('shll16', 6, 0x4428))), 0xa0040000)
        with self.assertRaises(ValueError):
            build_constant(data, (('mov', 0, 0xe4a1),))
        with self.assertRaises(ValueError):
            build_constant(data, (('rotl', 0, 0xe4a0),))

    def test_hash_guard(self):
        with self.assertRaises(ValueError):
            analyze_first_stage(b'not the reconstructed MAIN')


@unittest.skipUnless(MAIN.exists(), 'Private 1.44 reconstructed MAIN absent')
class FirstStageFallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = analyze_first_stage(MAIN.read_bytes())

    def test_identity(self):
        self.assertEqual(self.report['image_sha256'], FIRST_STAGE_SHA)

    def test_normal_boot_loads_the_application_block(self):
        self.assertEqual(self.report['application_block']['flash_source'], 0xa0040000)
        self.assertEqual(self.report['staging_ram'], 0xb70fd000)
        decompressor = self.report['decompressor']
        self.assertEqual(decompressor['flash_source'], 0xa0000900)
        self.assertEqual(decompressor['ram_destination'], 0xb7ffd000)
        # The jump target is inside the copied stub, addressed through its cached alias.
        entry_offset = ((decompressor['entry_value'] & 0x1fffffff)
                        - (decompressor['ram_destination'] & 0x1fffffff))
        self.assertGreaterEqual(entry_offset, 0)
        self.assertLess(entry_offset, decompressor['copied_bytes'])
        # That offset lands on the loader routine inspected in the flash copy.
        self.assertEqual(decompressor['flash_source'] - 0xa0000000 + entry_offset, 0xaaa)

    def test_checksum_failure_falls_back_to_the_updater_block(self):
        fallback = self.report['fallback_block']
        self.assertEqual(fallback['flash_source'], 0xa0010000)
        self.assertEqual(fallback['copied_bytes'], 0x30000)
        self.assertFalse(fallback['checksum_verified_before_use'])
        # The fallback source is inside the sectors the application erase profile skips.
        block = analyze(BLOCK.read_bytes())
        application_erase = block['erase_profiles']['selector_1']['first_flash_offset']
        self.assertLess(fallback['flash_source'] - 0xa0000000, application_erase)

    def test_both_paths_decompress_and_enter_at_the_same_address(self):
        self.assertEqual(self.report['decompress_destinations'], [0xa8000000, 0xa8000000])
        self.assertEqual(self.report['entry_table']['entries'], [0xa8000800, 0xa8000800])
        # The match branch skips the fallback copy entirely.
        gate = self.report['checksum_gate']
        self.assertGreater(gate['match_target_file_offset'],
                           self.report['fallback_block']['copy_call_file_offset'])
