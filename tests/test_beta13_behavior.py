"""Own C and numerical pitch contracts; no stock firmware execution."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class Beta13Behavior(unittest.TestCase):
    def test_stock_contract_hash_and_alignment_anchors(self):
        if not (ROOT/'private/extracted/v144/main-040000-unpacked.bin').exists(): self.skipTest('Official firmware not supplied')
        import sys
        sys.path.insert(0,str(ROOT/'scripts'))
        from index_beta13_contract import inspect
        report=inspect()['C_static']
        self.assertNotEqual(report['test12_cpu_pitch'],report['test12_compositor_pitch'])
        self.assertEqual(report['test13_cpu_pitch'],report['test13_compositor_pitch'])

    def test_browse_settle_restarts_and_resumes_without_mutating_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/'settle'
            subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fno-sanitize-recover=all',
                '-I',str(ROOT/'native'),str(ROOT/'tests/native_beta_browse_settle_test.c'),
                '-o',str(binary)],check=True,capture_output=True,timeout=30)
            subprocess.run([str(binary)],check=True,timeout=10)

    def test_aligned_geometry_preserves_290_pixel_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Reuse the frozen contract, changing only allocated surface width.
            source=(ROOT/'tests/native_beta_info_band_test.c').read_text()
            source=source.replace('"beta_info_band.c"','"beta_info_band_aligned.c"')
            source=source.replace('((uint16_t *)d)[6]==290','((uint16_t *)d)[6]==292')
            source=source.replace('(28u<<16)|290u','(28u<<16)|292u')
            test=Path(tmp)/'geometry.c'; test.write_text(source)
            binary=Path(tmp)/'geometry'
            subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fno-sanitize-recover=all',
                '-I',str(ROOT/'native'),str(test),'-o',str(binary)],
                check=True,capture_output=True,timeout=30)
            subprocess.run([str(binary)],check=True,timeout=10)

    def test_source_destination_compositor_rows_have_no_phase_shift(self):
        # Distinct pixels identify every source row/column and expose shearing.
        width,height=290,28
        source=[y*width+x+1 for y in range(height) for x in range(width)]
        for allocation in (290,292):
            cpu_pitch=allocation*2
            hardware_pitch=(cpu_pitch+7)&~7
            surface=bytearray(hardware_pitch*height)
            for y in range(height):
                for x in range(width):
                    i=y*cpu_pitch+2*x
                    surface[i:i+2]=source[y*width+x].to_bytes(2,'little')
            observed=[int.from_bytes(surface[y*hardware_pitch+2*x:y*hardware_pitch+2*x+2],'little')
                      for y in range(height) for x in range(width)]
            if allocation==290:
                self.assertNotEqual(observed,source)
                self.assertEqual(observed[width],source[width+2])
            else:
                self.assertEqual(observed,source)
                for y in range(height):
                    self.assertEqual(surface[y*hardware_pitch+580:(y+1)*hardware_pitch],bytes(4))

    def test_historical_beta12_sources_remain_frozen(self):
        if not (ROOT/'evidence/browser-waveform-beta-v144-test12.json').exists(): self.skipTest('Private historical manifest not supplied')
        manifest=json.loads((ROOT/'evidence/browser-waveform-beta-v144-test12.json').read_text())
        for source,expected in manifest['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/source).read_bytes()).hexdigest(),expected,source)
