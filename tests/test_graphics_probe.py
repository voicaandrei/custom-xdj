import binascii
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_graphics_probe import (
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
class GraphicsProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temporary.name)
        cls.reference = APP.read_bytes()
        cls.linked = link_beta(cls.folder, len(cls.reference))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_extension_is_fixed_linked_and_self_contained(self):
        self.assertEqual(self.linked["file_offset"], aligned(len(self.reference)))
        self.assertEqual(self.linked["code_pointer"],
                         0x08000000 + self.linked["file_offset"])
        self.assertGreater(len(self.linked["payload"]), 30000)
        self.assertEqual(self.linked["bss_bytes"], 0)
        self.assertEqual(self.linked["undefined_symbols"], [])
        self.assertEqual(self.linked["remaining_relocations"], [])
        for symbol in ("xdj_beta_getimage_hook", "xdj_beta_decode_hook"):
            self.assertGreaterEqual(self.linked["symbols"][symbol],
                                    self.linked["code_pointer"])

    def test_decode_wrapper_forwards_exact_stock_five_argument_contract(self):
        tools = toolchain()
        objdump = str(Path(tools["gcc"]).parent / "sh-elf-objdump")
        disassembly = subprocess.run(
            [objdump, "-d", str(self.folder / "browser-waveform-beta.elf")],
            check=True, capture_output=True, text=True,
        ).stdout
        wrapper = disassembly.split("<xdj_beta_decode_hook>:", 1)[1]
        wrapper = wrapper.split("<_render>:", 1)[0]
        # Stock 0x09304066 reads its only stack argument at entry SP +0. The
        # wrapper must preserve original r7 as surface A and original arg 5 as
        # surface B; caller SP +4 is unrelated local state.
        for instruction in (
            "mov.l\t@(12,r15),r8", "mov\t#56,r0",
            "mov.l\t@(r0,r15),r9", "add\t#-4,r15",
            "mov.l\tr9,@(0,r15)", "mov.l\t@(4,r15),r4",
            "mov.l\t@(8,r15),r5", "mov.l\t@(12,r15),r6",
            "mov.l\t@(16,r15),r7", "add\t#4,r15",
        ):
            self.assertIn(instruction, wrapper)
        self.assertNotIn("mov\t#60,r0", wrapper)
        self.assertNotIn("mov.l\tr8,@(0,r15)", wrapper)

    def test_getimage_wrapper_guards_shared_non_local_call_site(self):
        tools = toolchain()
        objdump = str(Path(tools["gcc"]).parent / "sh-elf-objdump")
        disassembly = subprocess.run(
            [objdump, "-d", str(self.folder / "browser-waveform-beta.elf")],
            check=True, capture_output=True, text=True,
        ).stdout
        wrapper = disassembly.split("<xdj_beta_getimage_hook>:", 1)[1]
        wrapper = wrapper.split("<xdj_beta_decode_hook>:", 1)[0]
        guard = [
            "tst\tr13,r13", "mov.l\t@r13,r0", "cmp/eq\t#1,r0",
            "mov\t#80,r0", "mov.l\t@(r0,r15),r8", "mov.l\t@r8,r9",
        ]
        positions = [wrapper.index(instruction) for instruction in guard]
        self.assertEqual(positions, sorted(positions))

        # DbReqJpegData v1.44 retains its original context in r13, branches on
        # context[0] == 1, and shares the GetImage literal across both paths.
        self.assertEqual(
            self.reference[0x12A4A90:0x12A4AAA],
            bytes.fromhex(
                "a62fb62fc62fd62fe62f224f124fd47f436da6de4264536bd151"
            ),
        )
        self.assertEqual(
            self.reference[0x12A4B28:0x12A4B32],
            bytes.fromhex("43600188588b6de002e1"),
        )

    def test_hook_literal_users_are_an_exact_allowlist(self):
        def users(target):
            found = []
            for address in range(0, len(self.reference) - 1, 2):
                low, high = self.reference[address:address + 2]
                if high >> 4 != 0xD:
                    continue
                literal = ((address + 4) & ~3) + low * 4
                if literal == target:
                    found.append((address, high & 0xF))
            return found

        # All three GetImage calls share one slot. Only 0x12a4bc0 is the local
        # browser branch; the context-type guard bypasses 0x12a4b0e/0x12a4cb0.
        self.assertEqual(
            users(0x12A4D4C),
            [(0x12A4B0E, 1), (0x12A4BC0, 12), (0x12A4CB0, 12)],
        )
        self.assertEqual(users(0x141289C), [(0x141274A, 1)])

    def test_stock_decoder_call_and_prologue_prove_one_stack_argument(self):
        # FILE offsets in the exact v1.44 decompressed application. Decoder
        # 0x1304066 saves 28 bytes and reserves 52, then reads caller SP +0 as
        # current SP +80. The caller pushes r14 exactly once before the JSR.
        self.assertEqual(
            self.reference[0x1304066:0x1304076],
            bytes.fromhex("962fa62fb62fc62fd62fe62f224fcc7f"),
        )
        self.assertEqual(
            self.reference[0x13040A0:0x13040A4],
            bytes.fromhex("50e0fe01"),
        )
        call_setup = self.reference[0x1412738:0x141275A]
        self.assertEqual(
            call_setup,
            bytes.fromhex(
                "0f7e492ee62f6a0d52d0f75518777c1f0f7754d14927592d"
                "f3566a4df4550b41ce04"
            ),
        )
        self.assertEqual(call_setup.count(bytes.fromhex("e62f")), 1)

    def test_stock_cache_entry_bounds_both_beta_surfaces(self):
        base = 0x157F905C
        stride = 30744
        row_bytes = 80 * 28 * 2
        info_bytes = 112 * 117 * 2
        for index in range(512):
            entry = base + index * stride
            next_entry = entry + stride
            row = (entry + 24 + 15) & ~15
            info = (entry + 4520 + 15) & ~15
            self.assertGreaterEqual(info - row, row_bytes)
            self.assertGreaterEqual(next_entry - info, info_bytes)
            self.assertLess(next_entry - info, 113 * 121 * 2)

    def test_exact_application_allowlist_and_stock_inline_colour_restored(self):
        candidate = patch_application(self.reference, self.linked)
        expected = bytearray(self.reference)
        for offset in TEXT_OFFSETS:
            self.assertEqual(expected[offset:offset + 24], BEFORE_TEXT + b"\0\0")
            expected[offset:offset + len(MARKER_TEXT)] = MARKER_TEXT
            self.assertEqual(candidate[offset + 22:offset + 24], b"\0\0")
        for offset, (before, symbol) in PATCHES.items():
            self.assertEqual(int.from_bytes(expected[offset:offset + 4], "little"), before)
            expected[offset:offset + 4] = self.linked["symbols"][symbol].to_bytes(4, "little")
        # Test 03's global blue diagnostic was at this instruction; beta must
        # restore the stock word so valid waveform pixels are visible.
        self.assertEqual(candidate[0x152D1B6:0x152D1B8], bytes.fromhex("2d08"))
        self.assertEqual(candidate[:len(self.reference)], bytes(expected))
        self.assertEqual(candidate[len(self.reference):self.linked["file_offset"]],
                         bytes(self.linked["padding_bytes"]))
        self.assertEqual(candidate[self.linked["file_offset"]:], self.linked["payload"])
        verify_application(self.reference, candidate, self.linked)

    def test_application_validator_rejects_any_extra_change(self):
        candidate = bytearray(patch_application(self.reference, self.linked))
        candidate[0] ^= 1
        with self.assertRaisesRegex(ValueError, "exact Test 04 beta"):
            verify_application(self.reference, bytes(candidate), self.linked)

    @unittest.skipUnless((FOLDER / "XDJ1KMK2.UPD").exists(), "Test 04 beta absent")
    def test_generated_update_reextracts_exact_extended_application(self):
        candidate = (FOLDER / "XDJ1KMK2.UPD").read_bytes()
        parts = split_container(candidate)
        self.assertEqual(parts[0][FORCE_OFFSET], FORCE_AFTER)
        self.assertEqual(int.from_bytes(parts[0][-2:], "little"),
                         binascii.crc_hqx(parts[0][:-2], 0))
        base_main = bytearray(parts[0])
        base_main[FORCE_OFFSET] = ord(" ")
        base_main[-2:] = binascii.crc_hqx(base_main[:-2], 0).to_bytes(2, "little")
        base = (str(len(base_main)).encode() + b"\r\n"
                + str(len(parts[1])).encode() + b"\r\n"
                + bytes(base_main) + parts[1])
        result = validate_forced_candidate(
            candidate, base, ORIGINAL.read_bytes(),
            patch_application(self.reference, self.linked),
        )
        self.assertTrue(result["panel_byte_identical"])
        self.assertEqual(result["application"]["unpacked_bytes"],
                         self.linked["file_offset"] + len(self.linked["payload"]))


if __name__ == "__main__":
    unittest.main()
