"""Differential validation of next-candidate code; frozen beta remains intact."""
import base64
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class FastPrepare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='xdj-fast-prepare-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.binary=Path(cls.temp.name)/'parity'
        subprocess.run(['cc','-std=c99','-O1','-Wall','-Wextra','-Werror',
            '-fsanitize=undefined','-fno-sanitize-recover=all',
            '-I',str(ROOT/'native'),*[str(ROOT/p) for p in (
                'native/waveform_prepare.c','native/waveform_prepare_fast.c',
                'tests/native_fast_prepare_test.c')],'-o',str(cls.binary)],
            check=True,capture_output=True,timeout=30)

    def test_all_widths_heights_ties_zero_maximum_and_invalid_pair(self):
        report=json.loads(subprocess.run([str(self.binary)],check=True,
            capture_output=True,text=True,timeout=60).stdout)
        self.assertEqual(report['pixel_and_callback_parity_cases'],18940)

    @unittest.skipUnless((ROOT/'private/owner/andrei-sample/color-manifest.json').exists(),
                         'Private owner fixtures absent')
    def test_real_50_tracks_blue_and_rgb_at_six_widths(self):
        fixtures=json.loads(subprocess.run(['node',str(ROOT/'tests/native-prepare-fixtures.mjs')],
            check=True,capture_output=True,text=True,timeout=30).stdout)
        self.assertEqual(len(fixtures),100)
        corpus=Path(self.temp.name)/'corpus.bin'
        with corpus.open('wb') as stream:
            for fixture in fixtures:
                stream.write(bytes([int(fixture['mode']=='rgb')]))
                stream.write(base64.b64decode(fixture['payload']))
        report=json.loads(subprocess.run([str(self.binary),str(corpus)],check=True,
            capture_output=True,text=True,timeout=30).stdout)
        self.assertEqual(report['pixel_and_callback_parity_cases'],1200)
