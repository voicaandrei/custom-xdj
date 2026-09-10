import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from roundtrip_upd import encode_record,rebuild
from extract_upd import decode_srecords

class UpdateSerialization(unittest.TestCase):
    def test_checksums_address_widths_and_sparse_ranges(self):
        lines=encode_record('2',0x10000,b'abc')+encode_record('2',0x40000,b'xyz')+encode_record('7',0xa0000000,b'')
        image,meta=decode_srecords(lines)
        self.assertEqual(image[:3],b'abc');self.assertEqual(image[-3:],b'xyz')
        self.assertEqual(meta['ranges'],[[0x10000,0x10003],[0x40000,0x40003]])
        self.assertEqual(meta['entry_record'],0xa0000000)
        for line in lines.splitlines():self.assertEqual(sum(bytes.fromhex(line[2:].decode()))&255,255)

    def test_refuses_unrecognized_input(self):
        with self.assertRaises(ValueError):rebuild(b'not official stock')
        with self.assertRaises(ValueError):encode_record('2',0,b'x'*252)
