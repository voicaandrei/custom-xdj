import binascii
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_beta06 import (
    FOLDER, FORCE_AFTER, FORCE_OFFSET, MARKER_TEXT, PATCHES,
    TEXT_OFFSETS, aligned, link_beta, patch_application,
    validate_forced_candidate, verify_application,
)
from build_marker_probe import BEFORE_TEXT
from build_sh import toolchain
from repack_reference import split_container


APP = ROOT / "private/extracted/v144/main-040000-unpacked.bin"
ORIGINAL = ROOT / "private/originals/v144/XDJ1KMK2.UPD"


@unittest.skipUnless(
    APP.exists() and ORIGINAL.exists() and toolchain() is not None,
    "Private references or SH toolchain absent",
)
class Beta06Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temporary.name)
        cls.reference = APP.read_bytes()
        cls.linked = link_beta(cls.folder, len(cls.reference))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_extension_is_fixed_linked_self_contained_and_has_no_bss(self):
        self.assertEqual(self.linked["file_offset"], aligned(len(self.reference)))
        self.assertEqual(
            self.linked["code_pointer"],
            0x08000000 + self.linked["file_offset"],
        )
        self.assertGreater(len(self.linked["payload"]), 30000)
        self.assertEqual(self.linked["bss_bytes"], 0)
        self.assertEqual(self.linked["undefined_symbols"], [])
        self.assertEqual(self.linked["remaining_relocations"], [])

    def test_exact_application_allowlist_and_marker(self):
        candidate = patch_application(self.reference, self.linked)
        expected = bytearray(self.reference)
        for offset in TEXT_OFFSETS:
            self.assertEqual(expected[offset:offset + 24], BEFORE_TEXT + b"\0\0")
            expected[offset:offset + len(MARKER_TEXT)] = MARKER_TEXT
            self.assertEqual(candidate[offset + 22:offset + 24], b"\0\0")
        for offset, (before, symbol) in PATCHES.items():
            self.assertEqual(
                int.from_bytes(expected[offset:offset + 4], "little"), before,
            )
            expected[offset:offset + 4] = self.linked["symbols"][symbol].to_bytes(
                4, "little",
            )
        self.assertEqual(candidate[:len(self.reference)], bytes(expected))
        self.assertEqual(candidate[0x152D1B6:0x152D1B8], bytes.fromhex("2d08"))
        verify_application(self.reference, candidate, self.linked)

    def test_trace_decoder_preserves_stock_five_argument_contract(self):
        tools = toolchain()
        objdump = str(Path(tools["gcc"]).parent / "sh-elf-objdump")
        disassembly = subprocess.run(
            [objdump, "-d", str(self.folder / "browser-waveform-beta06.elf")],
            check=True, capture_output=True, text=True,
        ).stdout
        wrapper = disassembly.split("<xdj_beta_decode_hook>:", 1)[1]
        wrapper = wrapper.split("<_render>:", 1)[0]
        for instruction in (
            "mov.l\t@(12,r15),r8", "mov\t#56,r0",
            "mov.l\t@(r0,r15),r9", "add\t#-4,r15",
            "mov.l\tr9,@(0,r15)", "mov.l\t@(4,r15),r4",
            "mov.l\t@(8,r15),r5", "mov.l\t@(12,r15),r6",
            "mov.l\t@(16,r15),r7", "add\t#4,r15",
        ):
            self.assertIn(instruction, wrapper)
        self.assertNotIn("mov\t#60,r0", wrapper)

    def test_trace_stage_calls_are_linked_into_getimage_wrapper(self):
        tools = toolchain()
        objdump = str(Path(tools["gcc"]).parent / "sh-elf-objdump")
        symbols = subprocess.run(
            [tools["nm"], "-n", str(self.folder / "browser-waveform-beta06.elf")],
            check=True, capture_output=True, text=True,
        ).stdout
        for symbol in (
            "xdj_beta_trace_reset", "xdj_beta_trace",
            "xdj_beta_apply_or_trace_surfaces",
        ):
            self.assertIn(symbol, symbols)
        disassembly = subprocess.run(
            [objdump, "-d", str(self.folder / "browser-waveform-beta06.elf")],
            check=True, capture_output=True, text=True,
        ).stdout
        getimage = disassembly.split("<xdj_beta_getimage_hook>:", 1)[1]
        getimage = getimage.split("<xdj_beta_decode_hook>:", 1)[0]
        for stage in range(2, 11):
            self.assertIn(f"mov\t#{stage},r4", getimage)

    def test_non_local_branches_cannot_reset_or_invalidate_preview_state(self):
        tools = toolchain()
        objdump = str(Path(tools["gcc"]).parent / "sh-elf-objdump")
        disassembly = subprocess.run(
            [objdump, "-d", str(self.folder / "browser-waveform-beta06.elf")],
            check=True, capture_output=True, text=True,
        ).stdout
        wrapper = disassembly.split("<xdj_beta_getimage_hook>:", 1)[1]
        wrapper = wrapper.split("<xdj_beta_decode_hook>:", 1)[0]
        guard = wrapper.index("cmp/eq\t#1,r0")
        accept = wrapper.index("bt\t", guard)
        reset_literal = wrapper.index("_xdj_beta_trace_reset", accept)
        first_row_read = wrapper.index("mov\t#80,r0")
        self.assertLess(guard, accept)
        self.assertLess(accept, reset_literal)
        self.assertLess(reset_literal, first_row_read)
        source = (ROOT / "native/v144/beta06_hooks.S").read_text()
        self.assertIn(
            "cmp/eq #1,r0\n    bf .Lstock_image\n\n"
            "    mov.l .Lbeta_trace_reset,r1",
            source,
        )

    @unittest.skipUnless((FOLDER / "XDJ1KMK2.UPD").exists(), "Test 06 absent")
    def test_generated_update_reextracts_exact_extended_application(self):
        candidate = (FOLDER / "XDJ1KMK2.UPD").read_bytes()
        parts = split_container(candidate)
        self.assertEqual(parts[0][FORCE_OFFSET], FORCE_AFTER)
        self.assertEqual(
            int.from_bytes(parts[0][-2:], "little"),
            binascii.crc_hqx(parts[0][:-2], 0),
        )
        base_main = bytearray(parts[0])
        base_main[FORCE_OFFSET] = ord(" ")
        base_main[-2:] = binascii.crc_hqx(base_main[:-2], 0).to_bytes(2, "little")
        base = (
            str(len(base_main)).encode() + b"\r\n"
            + str(len(parts[1])).encode() + b"\r\n"
            + bytes(base_main) + parts[1]
        )
        result = validate_forced_candidate(
            candidate, base, ORIGINAL.read_bytes(),
            patch_application(self.reference, self.linked),
        )
        self.assertTrue(result["panel_byte_identical"])
        self.assertEqual(
            result["application"]["unpacked_bytes"],
            self.linked["file_offset"] + len(self.linked["payload"]),
        )


if __name__ == "__main__":
    unittest.main()
