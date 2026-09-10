import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "private/owner/link-fixtures/player4-3902/link-preview-rgb.bin"


@unittest.skipUnless(FIXTURE.exists(), "Frozen PLAYER 4 RGB preview absent")
class BetaRuntimeTrace(unittest.TestCase):
    def test_trace_strip_and_real_waveform_are_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "beta-runtime-trace-test"
            subprocess.run(
                [
                    "cc", "-std=c99", "-O1", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=undefined", "-fno-sanitize-recover=all",
                    "-I", str(ROOT / "native"),
                    str(ROOT / "native/beta_runtime_trace.c"),
                    str(ROOT / "native/waveform_prepare.c"),
                    str(ROOT / "native/waveform_cell.c"),
                    str(ROOT / "native/pixel_channels.c"),
                    str(ROOT / "tests/native_beta_runtime_trace_test.c"),
                    "-o", str(target),
                ],
                check=True, capture_output=True, text=True, timeout=30,
            )
            subprocess.run(
                [str(target), str(FIXTURE)],
                check=True, capture_output=True, text=True, timeout=15,
            )


if __name__ == "__main__":
    unittest.main()
