import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'private/owner/link-fixtures/player4-3902/link-preview-rgb.bin'

class InfoBand(unittest.TestCase):
    def compile_run(self,sources,args=()):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/'test'
            subprocess.run(['cc','-std=c99','-O1','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'native'),
                *[str(ROOT/s) for s in sources],'-o',str(binary)],check=True,capture_output=True,timeout=30)
            subprocess.run([str(binary),*map(str,args)],check=True,timeout=15)

    def test_geometry_fallback_and_stock_return_values(self):
        self.compile_run(['tests/native_beta_info_band_test.c'])

    def test_key_note_mapping_preserves_flags_and_other_categories(self):
        self.compile_run(['native/beta_key_note.c','tests/native_beta_key_note_test.c'])

    @unittest.skipUnless(FIXTURE.exists(),'Frozen RGB absent')
    def test_band_bounds_baseline_and_cancelled_preview(self):
        self.compile_run(['native/beta_runtime_band.c','native/waveform_prepare.c',
            'native/waveform_cell.c','native/pixel_channels.c','tests/native_beta_runtime_band_test.c'],[FIXTURE])
