import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SurfaceAdapter(unittest.TestCase):
    def test_release_on_successful_access_including_invalid_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable=Path(tmp)/'surface-test'
            units=('surface_adapter','waveform_adapter','waveform_prepare','waveform_cell','pixel_channels')
            subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'native'),
                *[str(ROOT/'native'/f'{n}.c') for n in units],
                str(ROOT/'tests/native_surface_adapter_test.c'),'-o',str(executable)],
                check=True,capture_output=True)
            subprocess.run([str(executable)],check=True,capture_output=True,timeout=10)
