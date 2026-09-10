import binascii
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_force_probe import (
    AFTER,
    BEFORE,
    FOLDER,
    FORCE_OFFSET,
    apply_force_marker,
    validate_forced,
)
from build_marker_probe import patch as marker_patch
from repack_reference import split_container


ORIGINAL = ROOT / "private/originals/v144/XDJ1KMK2.UPD"
APP = ROOT / "private/extracted/v144/main-040000-unpacked.bin"
BASE = ROOT / "private/marker-probe-v144-02/XDJ1KMK2.UPD"


@unittest.skipUnless(ORIGINAL.exists() and APP.exists() and BASE.exists(), "Private inputs absent")
class ForceProbe(unittest.TestCase):
    def test_only_label_padding_and_crc_change_from_diagnostic_02(self):
        original = ORIGINAL.read_bytes()
        base = BASE.read_bytes()
        candidate = apply_force_marker(base, original)
        base_parts = split_container(base)
        candidate_parts = split_container(candidate)
        self.assertEqual(candidate_parts[1], base_parts[1])
        self.assertEqual(candidate_parts[0][32:-2], base_parts[0][32:-2])
        self.assertEqual(base_parts[0][FORCE_OFFSET], BEFORE)
        self.assertEqual(candidate_parts[0][FORCE_OFFSET], AFTER)
        self.assertEqual(
            candidate_parts[0][:FORCE_OFFSET], base_parts[0][:FORCE_OFFSET]
        )
        self.assertEqual(
            candidate_parts[0][FORCE_OFFSET + 1 : 32],
            base_parts[0][FORCE_OFFSET + 1 : 32],
        )
        self.assertEqual(
            int.from_bytes(candidate_parts[0][-2:], "little"),
            binascii.crc_hqx(candidate_parts[0][:-2], 0),
        )

    def test_validator_reextracts_exact_marker_application(self):
        original = ORIGINAL.read_bytes()
        base = BASE.read_bytes()
        result = validate_forced(
            apply_force_marker(base, original),
            base,
            original,
            marker_patch(APP.read_bytes()),
        )
        self.assertTrue(result["panel_byte_identical"])
        self.assertTrue(result["reconstructed_main_identical_to_diagnostic_02"])

    def test_validator_rejects_stream_or_panel_change(self):
        original = ORIGINAL.read_bytes()
        base = BASE.read_bytes()
        candidate = bytearray(apply_force_marker(base, original))
        # Outer header is 17 bytes; this byte is in the MAIN S-record stream.
        candidate[17 + 40] ^= 1
        with self.assertRaises(ValueError):
            validate_forced(
                bytes(candidate), base, original, marker_patch(APP.read_bytes())
            )

    @unittest.skipUnless((FOLDER / "XDJ1KMK2.UPD").exists(), "Diagnostic 03 absent")
    def test_generated_artifact_passes_full_validator(self):
        result = validate_forced(
            (FOLDER / "XDJ1KMK2.UPD").read_bytes(),
            BASE.read_bytes(),
            ORIGINAL.read_bytes(),
            marker_patch(APP.read_bytes()),
        )
        self.assertTrue(result["boot_and_updater_identical_to_stock"])


if __name__ == "__main__":
    unittest.main()
