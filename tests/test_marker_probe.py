import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build_marker_probe import patch, verify_patch, TEXT_OFFSETS, BEFORE_TEXT, AFTER_TEXT, FOLDER
from build_inline_probe import OFFSET, AFTER
from repack_reference import validate
APP = ROOT/'private/extracted/v144/main-040000-unpacked.bin'


@unittest.skipUnless(APP.exists(), 'Private reference absent')
class MarkerProbe(unittest.TestCase):
    def test_entire_image_diff_allowlist_and_terminators(self):
        original = APP.read_bytes()
        candidate = patch(original)
        expected = bytearray(original)
        expected[OFFSET:OFFSET+2] = AFTER
        # Independent inventory: reject missed or unintended string matches.
        found = []
        start = 0
        while True:
            start = original.find(BEFORE_TEXT+b'\0\0', start)
            if start < 0:
                break
            found.append(start)
            start += len(BEFORE_TEXT)
        self.assertEqual(tuple(found), TEXT_OFFSETS)
        for offset in found:
            self.assertEqual(offset % 2, 0)
            expected[offset:offset+22] = AFTER_TEXT
            self.assertEqual(candidate[offset+22:offset+24], b'\0\0')
        self.assertEqual(len(candidate), len(original))
        self.assertEqual(candidate, bytes(expected))
        verify_patch(original, candidate)

    def test_refuses_wrong_reference_and_unlisted_mutation(self):
        original = APP.read_bytes()
        with self.assertRaises(ValueError):
            patch(original[:-1])
        candidate = bytearray(patch(original))
        candidate[TEXT_OFFSETS[0]+22] = 1
        with self.assertRaises(ValueError):
            verify_patch(original, bytes(candidate))

    @unittest.skipUnless((FOLDER/'XDJ1KMK2.UPD').exists(), 'Diagnostic 02 absent')
    def test_full_container_reextracts_exact_candidate(self):
        result = validate((FOLDER/'XDJ1KMK2.UPD').read_bytes(),
                          (ROOT/'private/originals/v144/XDJ1KMK2.UPD').read_bytes(),
                          patch(APP.read_bytes()))
        self.assertEqual(result['unpacked_bytes'], APP.stat().st_size)
