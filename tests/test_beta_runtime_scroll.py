"""Cancellation/fallback pixel regression with real RGB and UBSan."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'private/owner/link-fixtures/player4-3902/link-preview-rgb.bin'

@unittest.skipUnless(FIXTURE.exists(), 'Frozen RGB fixture absent')
class BetaRuntimeScroll(unittest.TestCase):
    def test_cancelled_preview_preserves_all_stock_pixels_and_success_is_consumed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/'scroll-runtime'
            subprocess.run(['cc','-std=c99','-O1','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'native'),
                *[str(ROOT/p) for p in ('native/beta_runtime_scroll.c',
                    'native/waveform_prepare.c','native/waveform_cell.c',
                    'native/pixel_channels.c','tests/native_beta_runtime_scroll_test.c')],
                '-o',str(binary)], check=True, capture_output=True, timeout=30)
            subprocess.run([str(binary),str(FIXTURE)],check=True,timeout=15)
