import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from index_row_identity import analyze,movl

class RowIdentityTests(unittest.TestCase):
    def test_hash_guard(self):
        with self.assertRaises(ValueError):analyze(b'wrong image')
    def test_unrelated_opcode_rejected(self):
        with self.assertRaises(ValueError):movl(b'\x09\x00',0)
    @unittest.skipUnless((ROOT/'private/extracted/v144/main-040000-unpacked.bin').exists(),'Private firmware absent')
    def test_main_id_is_distinct_from_artwork_and_blue_is_not_detailed(self):
        r=analyze((ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
        self.assertEqual(r['record_main_id']['target']['displacement'],0)
        self.assertEqual(r['record_artwork_id']['target']['displacement'],20)
        self.assertEqual(r['row_main_id']['source']['displacement'],16)
        self.assertEqual(r['row_main_id']['target']['displacement'],0)
        self.assertEqual(r['row_artwork_id']['source']['displacement'],36)
        self.assertEqual(r['row_artwork_id']['target']['displacement'],8)
        self.assertEqual(r['row_table_offset_literal']['pointer_value'],0x178d8)
        self.assertEqual(r['row_stride'],276)
        self.assertEqual((r['blue_preview']['request'],r['blue_preview']['response']),(0x2004,0x4402))
        self.assertEqual((r['detailed_waveform']['request'],r['detailed_waveform']['response']),(0x2904,0x4a02))

        result=r['binary_result_transfer']
        self.assertEqual(result['length']['source']['displacement'],28)
        self.assertEqual(result['buffer']['source']['displacement'],32)
        self.assertEqual(result['detach_store']['displacement'],32)
        self.assertEqual(result['detach_store']['register'],9)
        self.assertEqual(result['zero_register_instruction']['signed_value'],0)
