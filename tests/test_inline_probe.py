import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_inline_probe import patch,verify_patch,OFFSET,AFTER
from repack_reference import validate
APP=ROOT/'private/extracted/v144/main-040000-unpacked.bin'
UPD=ROOT/'private/inline-probe-v144/XDJ1KMK2.UPD'


@unittest.skipUnless(APP.exists(),'Private application reference absent')
class InlineProbe(unittest.TestCase):
    def test_exact_instruction_and_exclusive_change(self):
        original=APP.read_bytes();candidate=patch(original)
        self.assertEqual(candidate[:OFFSET],original[:OFFSET])
        self.assertEqual(candidate[OFFSET+2:],original[OFFSET+2:])
        word=int.from_bytes(candidate[OFFSET:OFFSET+2],'little')
        self.assertEqual(word>>12,0xe)  # SH MOV immediate
        self.assertEqual((word>>8)&15,8)
        self.assertEqual(word&255,31)
        verify_patch(original,candidate)

    def test_rejects_foreign_reference_and_additional_change(self):
        original=APP.read_bytes()
        with self.assertRaisesRegex(ValueError,'Wrong application'):
            patch(original[:-1])
        changed=bytearray(patch(original));changed[0]^=1
        with self.assertRaisesRegex(ValueError,'exact two-byte'):
            verify_patch(original,bytes(changed))

    @unittest.skipUnless(UPD.exists(),'Private diagnostic update absent')
    def test_generated_update_extracts_to_only_allowed_change(self):
        original=APP.read_bytes()
        result=validate(UPD.read_bytes(),
            (ROOT/'private/originals/v144/XDJ1KMK2.UPD').read_bytes(),patch(original))
        self.assertEqual(result['unpacked_bytes'],len(original))
