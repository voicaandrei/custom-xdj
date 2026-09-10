import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "private/owner/link-fixtures/player4-3902"


@unittest.skipUnless(
    (FIXTURE / "link-preview-rgb.bin").exists()
    and (FIXTURE / "link-preview-blue.bin").exists(),
    "Frozen PLAYER 4 preview captures absent",
)
class BetaRuntime(unittest.TestCase):
    def test_real_rgb_and_blue_payloads_render_both_stock_surfaces(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "beta-runtime-test"
            subprocess.run(
                [
                    "cc",
                    "-std=c99",
                    "-O1",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-fsanitize=undefined",
                    "-fno-sanitize-recover=all",
                    "-I",
                    str(ROOT / "native"),
                    str(ROOT / "native/beta_runtime.c"),
                    str(ROOT / "native/waveform_prepare.c"),
                    str(ROOT / "native/waveform_cell.c"),
                    str(ROOT / "native/pixel_channels.c"),
                    str(ROOT / "tests/native_beta_runtime_test.c"),
                    "-o",
                    str(target),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            subprocess.run(
                [
                    str(target),
                    str(FIXTURE / "link-preview-rgb.bin"),
                    str(FIXTURE / "link-preview-blue.bin"),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )


if __name__ == "__main__":
    unittest.main()
