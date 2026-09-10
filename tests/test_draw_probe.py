import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class DrawProbe(unittest.TestCase):
    def test_pixels_bounds_order_and_disabled_are_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable=Path(tmp)/'probe-test'
            subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'native'),
                *[str(ROOT/'native'/f'{name}.c') for name in ('draw_probe','waveform_cell','pixel_channels')],
                str(ROOT/'tests/native_draw_probe_test.c'),'-o',str(executable)],check=True,capture_output=True)
            subprocess.run([str(executable)],check=True,capture_output=True)
