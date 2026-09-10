import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from index_artwork_render import analyze, mov_immediate


class ArtworkRenderIndex(unittest.TestCase):
    @unittest.skipUnless((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(),
                         'Private 1.44 application absent')
    def test_special_geometry_sites_are_stores_not_patch_immediates(self):
        data = (ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
        stores = analyze(data)['special_descriptor_stores']
        self.assertEqual([s['field'] for s in stores],
                         ['x', 'y', 'width', 'source_stride', 'height'])
        # MOV.L Rm,@(R0,Rn) / MOV.W Rm,@(R0,Rn), not MOV #imm,Rn.
        self.assertEqual([s['opcode'] & 0xf00f for s in stores], [6, 6, 5, 5, 5])

    def test_signed_sh_immediate(self):
        data = bytes.fromhex('86e150e71ce0')
        self.assertEqual(mov_immediate(data, 0)['signed_value'], -122)
        self.assertEqual(mov_immediate(data, 2)['signed_value'], 80)
        self.assertEqual(mov_immediate(data, 2)['register'], 7)
        for offset in [-2, 1, 6]:
            with self.assertRaises(ValueError): mov_immediate(data, offset)
        with self.assertRaises(ValueError): mov_immediate(b'\x09\x00', 0)
        self.assertEqual(mov_immediate(bytes.fromhex('3c74'), 0, 'add')['signed_value'], 60)

    def test_hash_guard(self):
        with self.assertRaises(ValueError): analyze(b'unknown firmware')

    @unittest.skipUnless((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(),
                         'Private 1.44 application absent')
    def test_native_geometry_and_surface_calls(self):
        report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
        geometry = report['normal_surface_static']
        self.assertEqual((geometry['width'], geometry['height'], geometry['source_bytes']),
                         (80, 28, 4480))
        self.assertEqual(report['initializers']['pair_count']['signed_value'], 3)
        values = {x['movl_file_offset']: x['pointer_value'] for x in report['inspected_literals']}
        self.assertEqual(values[0x152e852], 0x0952cbac)
        self.assertEqual(values[0x152d140], 0x0935a24c)
        self.assertEqual(values[0x152d1d0], 0x0935a2ec)
        self.assertEqual(values[0x152cbc4], 0x0da77de4)
        self.assertEqual(values[0x1363918], 0x0935e182)
        self.assertEqual(values[0x1363966], 0x0935e196)
        self.assertEqual(report['pixel_format']['constructor_format_immediate']['signed_value'], 9)
        self.assertEqual(report['surface_access_static']['outer_release_mask']['pointer_value'], 0xfeffffff)
        self.assertEqual(values[0x135acec], 0x09363ab0)
        self.assertEqual(values[0x1363aca], 0x09363a92)
        self.assertEqual(values[0x1363a96], 0x0935e778)
        self.assertEqual(values[0x135e78e], 0x0935c324)
        self.assertEqual(report['pixel_format']['channel_packing_static']['middle_clear_mask_value'], 0xf81f)
        # Confirm pixel transfer width, not just constants that resemble sizes.
        data = (ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
        self.assertEqual(int.from_bytes(data[0x152d1b6:0x152d1b8], 'little'), 0x082d)
        self.assertEqual(int.from_bytes(data[0x152d1b8:0x152d1ba], 'little'), 0x2581)
        # Literal AND opcodes at the inspected channel extraction sites.
        for pc, mask in [(0x135c35c, 31), (0x135c380, 63), (0x135c392, 31)]:
            self.assertEqual(int.from_bytes(data[pc:pc+2], 'little'), 0xc900 | mask)

    @unittest.skipUnless((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(),
                         'Private 1.44 application absent')
    def test_special_destination_is_a_single_large_surface(self):
        """Destination 7 is one big rectangle, not one of the seven row cells."""
        report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
        special = report['special_surface_static']
        normal = report['normal_surface_static']
        self.assertEqual(special['destination'], normal['special_destination'])
        self.assertEqual((special['x'], special['y']), (659, 132))
        self.assertEqual((special['width'], special['height']), (128, 121))
        self.assertEqual(special['source_stride_words'], 113)
        # The resource B copy fits inside the declared rectangle.
        self.assertLessEqual(special['copy_visible_pixels_per_row'], special['width'])
        self.assertLessEqual(special['copy_rows'], special['height'])
        self.assertEqual(special['copy_destination_stride_pixels'],
                         special['source_stride_words'])
        # It is far larger than a row cell, and reads the other resource field.
        self.assertGreater(special['width'] * special['height'],
                           6 * normal['width'] * normal['height'])
        self.assertEqual(special['resource_field'], normal['special_resource_field'].split(',')[0])

    @unittest.skipUnless((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(),
                         'Private 1.44 application absent')
    def test_descriptor_table_has_no_spare_entry(self):
        """A ninth surface cannot be appended: the next used pointer is adjacent."""
        report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
        capacity = report['descriptor_table_capacity']
        self.assertEqual(capacity['table_pointer'], 0x13bca44c)
        self.assertEqual(capacity['entry_stride_bytes'] * capacity['entries'],
                         capacity['table_bytes'])
        self.assertEqual(capacity['next_used_pointer'] - capacity['table_pointer'],
                         capacity['table_bytes'])
        # Every literal that would have to be repointed if the table moved.
        self.assertIn(0x152ced0, capacity['literal_users_of_table'])
        self.assertGreaterEqual(len(capacity['literal_users_of_table']), 4)

    @unittest.skipUnless((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(),
                         'Private 1.44 application absent')
    def test_special_surface_budget_bounds_any_new_rectangle(self):
        """Repointing destination 7 is limited by the resource B buffer size."""
        report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
        budget = report['special_surface_budget']
        special = report['special_surface_static']
        self.assertEqual(budget['resource_b_words_per_slot'],
                         budget['resource_b_fill_bytes_per_slot'] // 2)
        # The declared rectangle is exactly the buffer, so nothing is wasted.
        self.assertEqual(budget['declared_stride_words'] * budget['declared_height'],
                         budget['resource_b_words_per_slot'])
        self.assertEqual(budget['declared_stride_words'], special['source_stride_words'])
        # A full-width bar of 325 x 42 fits; 325 x 43 does not.
        self.assertLessEqual(325 * 42, budget['resource_b_words_per_slot'])
        self.assertGreater(325 * 43, budget['resource_b_words_per_slot'])

    @unittest.skipUnless((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(),
                         'Private 1.44 application absent')
    def test_surface_registration_sets_flags_not_a_stacking_order(self):
        """The two calls at creation are bit sets on the object flags."""
        data = (ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
        flags = analyze(data)['surface_flag_calls']
        self.assertEqual([site['argument_r6'] for site in flags['call_sites']], [8, 1])
        self.assertEqual({site['argument_r5'] for site in flags['call_sites']}, {1})
        self.assertEqual(flags['operations']['1'], 'object[+4] |= mask')
        # The backend switches on the operation and ORs the mask into +4.
        self.assertEqual(int.from_bytes(data[0x135df48:0x135df4a], 'little'), 0x8801)
        # or r12,r6 : the mask is ORed into the flags before the store.
        self.assertEqual(int.from_bytes(data[0x135df64:0x135df66], 'little'), 0x26cb)
        # mov.l r6,@(4,r13) : the store back into the object's flag field.
        self.assertEqual(int.from_bytes(data[0x135df68:0x135df6a], 'little'), 0x1d61)


@unittest.skipUnless((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(),
                     'Private 1.44 application absent')
class SurfaceOuterStatus(unittest.TestCase):
    def test_outer_status_does_not_confuse_backend_one_with_success(self):
        data=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
        result=analyze(data)['surface_outer_status']
        for operation in ('access_returns','release_returns'):
            observed=result[operation]
            self.assertEqual([v['signed_value'] for v in observed.values()],[0,1,5,2,4])
            self.assertTrue(all(v['register']==0 for v in observed.values()))
            for v in observed.values():
                pc=v['file_offset']
                self.assertEqual(int.from_bytes(data[pc:pc+2],'little'),0xe000+v['signed_value'])
