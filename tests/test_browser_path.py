import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from index_browser_path import analyze, pc_literal


class BrowserPathIndex(unittest.TestCase):
    def test_pc_alignment_and_bounds(self):
        data = bytearray(24)
        # PC=2: ((2+4)&~3)+2*4 = 12, not 14.
        data[2:4] = (0xd302).to_bytes(2, 'little')
        data[12:16] = (0x09512e4c).to_bytes(4, 'little')
        result = pc_literal(data, 2)
        self.assertEqual(result['literal_file_offset'], 12)
        self.assertEqual(result['pointer_value'], 0x09512e4c)
        for pc in (-2, 1, 24, 0):
            with self.assertRaises(ValueError): pc_literal(data, pc)
        data[2:4] = (0xd3ff).to_bytes(2, 'little')
        with self.assertRaises(ValueError): pc_literal(data, 2)

    def test_wrong_target_fails_closed(self):
        with self.assertRaises(ValueError): analyze(b'not firmware 1.44')

    @unittest.skipUnless((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(),
                         'Private 1.44 application absent')
    def test_real_message_path_and_consumers(self):
        report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
        command, message, mode = report['switches']
        def target(switch, selector):
            return next(x['target_file_offset'] for x in switch['entries']
                        if x['selector'] == selector)
        self.assertEqual(target(command, 5), 0x150f166)
        self.assertEqual(target(message, 0x1008), 0x154c072)
        self.assertEqual(target(mode, 1), 0x154c112)
        self.assertEqual(target(mode, 7), 0x154c112)
        values = {x['movl_file_offset']: x['pointer_value']
                  for x in report['inspected_literals']}
        self.assertEqual(values[0x150f166], 0x09511a28)
        self.assertEqual(values[0x154d0c2], 0x09512e4c)
        self.assertEqual(values[0x154d590], 0x095135c6)
        self.assertEqual(values[0x1519522], 0x0da74d5c)
        self.assertEqual(values[0x1519548], 0x0da74cb0)
        self.assertEqual(values[0x1514eda], 0x09445cbc)
        self.assertEqual(values[0x151a9ac], 0x0da71808)
        self.assertEqual(values[0x1520744], 0x0da7185c)
        self.assertEqual(values[0x1520754], 0x0da77de4)

    def test_immediate_helper_rejects_other_instructions(self):
        from index_browser_path import immediate
        self.assertEqual(immediate(bytes.fromhex('12e6'), 0)['signed_value'], 18)
        self.assertEqual(immediate(bytes.fromhex('8076'), 0, 'add')['signed_value'], -128)
        self.assertEqual(immediate(bytes.fromhex('10c8'), 0, 'tst')['signed_value'], 16)
        with self.assertRaises(ValueError):
            immediate(bytes.fromhex('12e6'), 0, 'add')
        with self.assertRaises(ValueError):
            immediate(bytes.fromhex('12e6'), 0, 'tst')
        with self.assertRaises(ValueError):
            immediate(bytes.fromhex('12e6'), 0, 'sub')
        for pc in (-2, 1, 2):
            with self.assertRaises(ValueError):
                immediate(bytes.fromhex('12e6'), pc)

    @unittest.skipUnless((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(),
                         'Private 1.44 application absent')
    def test_resource_A_destination_is_static_and_gated(self):
        data = (ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
        destination = analyze(data)['resource_A_destination_static']
        self.assertEqual(destination['destination_base_literal']['pointer_value'], 0x0daacb68)
        self.assertEqual(destination['destination_slot_stride_bytes'], 4480)
        self.assertEqual(destination['slot_stride_bytes'], 544)
        # One group holds exactly the eight per-slot buffers.
        self.assertEqual(destination['destination_group_stride_literal']['pointer_value'],
                         destination['slots_per_group'] * destination['destination_slot_stride_bytes'])
        # The copy is gated on group flag bit 0x10, not run on every repaint.
        self.assertEqual(destination['copy_gate']['test_instruction']['signed_value'], 0x10)
        self.assertEqual(int.from_bytes(data[0x15207ee:0x15207f0], 'little'), 0xc810)
        # Nothing outside the propagation function loads the destination base.
        users = [pc for entry in destination['literal_users_of_destination_base']
                 for pc in entry['candidate_movl_file_offsets']]
        self.assertEqual(sorted(users), [0x1520750, 0x15207d8])
