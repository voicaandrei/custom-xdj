import importlib.util
from pathlib import Path
import unittest

def module(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).resolve().parents[1]/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
upd=module('extract_upd');pack=module('unpack_main')
def record(typ,address,payload=b''):
    n={'0':2,'1':2,'2':3,'3':4,'5':2,'7':4,'8':3,'9':2}[typ]
    b=bytes([n+len(payload)+1])+address.to_bytes(n,'big')+payload
    return b'S'+typ.encode()+(b+bytes([255-(sum(b)&255)])).hex().upper().encode()+b'\r\n'
class FirmwareTests(unittest.TestCase):
    def test_sparse_addresses_and_entry(self):
        b,meta=upd.decode_srecords(record('2',0x100,b'ABC')+record('2',0x108,b'Z')+record('8',0))
        self.assertEqual(b,b'ABC'+b'\xff'*5+b'Z');self.assertEqual(meta['base_address'],0x100);self.assertEqual(meta['data_bytes'],4)
    def test_bad_checksum_count_overlap_and_missing_end(self):
        good=record('2',0,b'ABC')
        for data in [good[:-4]+b'00\r\n'+record('8',0),good+good+record('8',0),good,good+record('5',7)+record('8',0),good+record('8',0)+good]:
            with self.assertRaises(ValueError):upd.decode_srecords(data)
    def test_address_bomb_rejected(self):
        with self.assertRaises(ValueError):upd.decode_srecords(record('3',0xffffffff,b'A')+record('7',0))
    def test_unknown_firmware_hash_rejected(self):
        with self.assertRaises(ValueError):upd.extract(b'not firmware')
    def test_literals_and_overlapping_back_reference(self):
        self.assertEqual(pack.lzss(b'\x07ABC'),b'ABC')
        self.assertEqual(pack.lzss(b'\x01A\xee\xf2'),b'AAAAAA')
    def test_truncated_and_bounded_decompression(self):
        for b in [b'\x00\x01',b'\x01']:
            with self.assertRaises(ValueError):pack.lzss(b)
        with self.assertRaises(ValueError):pack.lzss(b'\x01A\xee\xff',limit=4)
    def test_packed_checksum_and_bounds(self):
        data=b'\x07ABC';b=len(data).to_bytes(4,'little')+data;b+=(sum(b)&65535).to_bytes(2,'little')
        self.assertEqual(pack.unpack(b,0)[0],b'ABC')
        with self.assertRaises(ValueError):pack.unpack(b[:-1],0)
        with self.assertRaises(ValueError):pack.unpack(b[:-1]+bytes([b[-1]^1]),0)

class OfficialReferenceTests(unittest.TestCase):
    def check_reference(self, relative, version, main_sha):
        path=Path(__file__).resolve().parents[1]/relative
        if not path.exists():self.skipTest('Official firmware not archived locally')
        parts=upd.extract(path.read_bytes())
        self.assertTrue(parts[0][2]['label'].startswith(f'XDJ-1000MK2 MAINVer{version}'))
        self.assertEqual(parts[0][2]['image_sha256'],main_sha)
        self.assertEqual(parts[1][2]['image_sha256'],'41bb11e2ff69c59d1e20b251f35cbfd71b119fb9ea0dd6f050fd580169502271')
    def test_official_v144(self):
        self.check_reference('private/originals/v144/XDJ1KMK2.UPD','1.44','4d7d55fe7c905c511aaef54fdeddc7f7f5ec2c935a8c9f59404d3dff4dac1f21')
    def test_official_v145(self):
        self.check_reference('private/originals/XDJ1KMK2.UPD','1.45','27109e16082ab444f726547f3188577dafd4f55c7de23ea9ee658532dd9373da')

if __name__=='__main__':unittest.main()
