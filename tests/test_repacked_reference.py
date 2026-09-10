import binascii
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from repack_reference import split_container,validate
STOCK=ROOT/'private/originals/v144/XDJ1KMK2.UPD'
CANDIDATE=ROOT/'private/stock-recompressed-validation-v144.UPD'
APP=ROOT/'private/extracted/v144/main-040000-unpacked.bin'

@unittest.skipUnless(all(p.exists() for p in (STOCK,CANDIDATE,APP)), 'Private stock packaging experiment absent')
class RepackedReference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock=STOCK.read_bytes();cls.candidate=CANDIDATE.read_bytes();cls.app=APP.read_bytes()

    def test_full_candidate_extracts_to_exact_application(self):
        result=validate(self.candidate,self.stock,self.app)
        self.assertEqual(result['unpacked_bytes'],len(self.app))

    def test_valid_checksums_do_not_allow_boot_modification(self):
        main,panel=split_container(self.candidate)
        lines=main[32:-2].splitlines(keepends=True)
        for i,line in enumerate(lines):
            if line.startswith(b'S2'):
                raw=bytearray.fromhex(line[2:].decode())
                raw[4]^=1
                raw[-1]=255-(sum(raw[:-1])&255)
                lines[i]=b'S2'+raw.hex().upper().encode()+b'\r\n'
                break
        altered=main[:32]+b''.join(lines)
        altered+=binascii.crc_hqx(altered,0).to_bytes(2,'little')
        candidate=str(len(altered)).encode()+b'\r\n'+str(len(panel)).encode()+b'\r\n'+altered+panel
        with self.assertRaisesRegex(ValueError,'outside application block'):
            validate(candidate,self.stock,self.app)
