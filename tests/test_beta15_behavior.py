import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class Beta15Behavior(unittest.TestCase):
    def compile_run(self,sources,args=()):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'test'
            subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'native'),
                *[str(ROOT/p) for p in sources],'-o',str(exe)],check=True,capture_output=True,timeout=30)
            subprocess.run([str(exe),*map(str,args)],check=True,timeout=15)

    def test_exact_rows_bounds_releases_errors_and_non_info_passthrough(self):
        self.compile_run(['tests/native_beta_info15_test.c'])

    def test_real_rgb_frame_and_blank_info_fit_new_transfer(self):
        if not (ROOT/'private/owner/link-fixtures/player4-3902/link-preview-rgb.bin').exists(): self.skipTest('Private RGB capture not supplied')
        self.compile_run(['native/beta_runtime_14.c','native/waveform_prepare_fast.c',
            'native/waveform_cell.c','native/pixel_channels.c','tests/native_beta_runtime14_test.c'],
            [ROOT/'private/owner/link-fixtures/player4-3902/link-preview-rgb.bin'])

    def test_historical_beta14_sources_unchanged(self):
        if not (ROOT/'evidence/browser-waveform-beta-v144-test14.json').exists(): self.skipTest('Private historical manifest not supplied')
        manifest=json.loads((ROOT/'evidence/browser-waveform-beta-v144-test14.json').read_text())
        for source,expected in manifest['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/source).read_bytes()).hexdigest(),expected,source)

    def test_ui_bounds_icon_variants_and_footer_only(self):
        self.compile_run(['tests/native_beta_ui15_test.c'])

    def test_preview_scope_preserves_cancel_latch_and_restores_original(self):
        self.compile_run(['tests/native_beta_scope15_test.c'])
