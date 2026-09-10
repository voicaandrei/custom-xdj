import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_custom_v1 import patch,BASE,LABEL,TEXT_OFFSETS,BEFORE_TEXT

class CustomV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (BASE/'application.bin').exists() or not (ROOT/'private/extracted/v144/main-040000-unpacked.bin').exists():
            raise unittest.SkipTest('Private release base and official firmware not supplied')
        cls.base=(BASE/'application.bin').read_bytes()
        cls.stock=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    def test_label_is_terminated_and_every_reference_resolves_with_segment_preserved(self):
        app,m=patch(self.base,self.stock);start=m['label_file_offset']
        self.assertEqual(app[start:],b'C\0u\0s\0t\0o\0m\0 \0X\0D\0J\0 \0v\x001\0\0\0')
        self.assertEqual(len(m['pointer_changes']),22)
        for entry in m['pointer_changes']:
            p=int.from_bytes(app[entry['file_offset']:entry['file_offset']+4],'little')
            self.assertEqual(p & 0xe0000000,entry['before'] & 0xe0000000)
            self.assertEqual((p&0x1fffffff)-0x08000000,start)
    def test_runtime_and_neighbor_strings_unchanged(self):
        app,m=patch(self.base,self.stock);normalized=bytearray(app[:len(self.base)])
        for at in TEXT_OFFSETS:
            self.assertEqual(app[at:at+24],BEFORE_TEXT+b'\0\0')
            self.assertEqual(app[at+24:at+48],self.base[at+24:at+48])
            normalized[at:at+22]=self.base[at:at+22]
        for e in m['pointer_changes']:
            at=e['file_offset'];normalized[at:at+4]=self.base[at:at+4]
        self.assertEqual(normalized,self.base)
    def test_unrecognized_application_is_refused(self):
        bad=bytearray(self.base);bad[-1]^=1
        with self.assertRaises(AssertionError):patch(bytes(bad),self.stock)
