import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_beta07 as beta07
from build_sh import toolchain


APP = ROOT / "private/extracted/v144/main-040000-unpacked.bin"


@unittest.skipUnless(APP.exists() and toolchain() is not None, "private input/toolchain absent")
class Beta07Build(unittest.TestCase):
    def test_adapter_supplies_request_numeric_id_without_context_table(self):
        with tempfile.TemporaryDirectory() as temporary:
            linked = beta07.link_beta(Path(temporary), len(APP.read_bytes()))
            tools = toolchain()
            prefix = str(Path(tools["gcc"]).parent / "sh-elf-")
            elf = Path(temporary) / "browser-waveform-beta06.elf"
            disassembly = subprocess.run(
                [prefix + "objdump", "-d", str(elf)], check=True,
                capture_output=True, text=True,
            ).stdout
            adapter = disassembly.split("<xdj_beta_getimage_hook>:", 1)[1]
            self.assertIn("mov.l\t@(40,r11),r0", adapter)
            self.assertIn("mov.l\tr8,@(16,r15)", adapter)
            self.assertIn("mov\tr15,r13", adapter)
            self.assertIn("xdj_beta_getimage_hook06", disassembly)
            self.assertEqual(linked["bss_bytes"], 0)
            self.assertEqual(linked["remaining_relocations"], [])

    def test_marker_is_fixed_width(self):
        self.assertEqual(len(beta07.MARKER_TEXT), 22)


if __name__ == "__main__":
    unittest.main()
