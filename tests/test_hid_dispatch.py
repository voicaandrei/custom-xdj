import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from index_hid_dispatch import analyze, relative_switch


class HIDDispatchIndex(unittest.TestCase):
    def test_signed_branch_pc_relative_not_table_relative(self):
        data = bytearray(128)
        data[32:34] = (0x0023).to_bytes(2, 'little')
        data[64:66] = (-12).to_bytes(2, 'little', signed=True)
        data[66:68] = (64).to_bytes(2, 'little', signed=True)
        result = relative_switch(data, 64, 32, 42, 2)
        self.assertEqual([x['target_file_offset'] for x in result], [24, 100])
        self.assertEqual([x['selector'] for x in result], [42, 43])
        with self.assertRaises(ValueError): relative_switch(data, 126, 32, 42, 2)
        with self.assertRaises(ValueError): relative_switch(data, 65, 32, 42, 2)
        with self.assertRaises(ValueError): relative_switch(data, 64, 34, 42, 2)
        data[64:66] = (-38).to_bytes(2, 'little', signed=True)
        with self.assertRaises(ValueError): relative_switch(data, 64, 32, 42, 2)

    def test_wrong_target_fails_closed(self):
        with self.assertRaises(ValueError): analyze(b'not the exact firmware')

    @unittest.skipUnless((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(),
                         'Private 1.44 application absent')
    def test_real_switches_and_cross_subsystem_getter(self):
        report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
        first, accumulate, complete = report['switches']
        self.assertEqual(len(first['entries']), 38)
        self.assertEqual(first['entries'][1]['target_file_offset'], 0x155d368)
        self.assertEqual(first['entries'][7]['target_file_offset'], 0x155dfa2)
        self.assertEqual(first['entries'][-1]['target_file_offset'], 0x155df82)
        self.assertEqual(accumulate['entries'][4]['target_file_offset'], 0x155dad6)
        self.assertEqual(complete['entries'][4]['target_file_offset'], 0x155dca6)
        getter = next(x for x in report['pointers'] if x['pointer_value'] == 0x0955e7be)
        self.assertEqual([x['literal_file_offset'] for x in getter['references']], [0x1543d2c])
