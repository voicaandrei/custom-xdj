import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NativeCell(unittest.TestCase):
    def test_pixel_channels_with_ubsan(self):
        compiler = shutil.which('cc')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory(prefix='xdj-pixel-test-') as temporary:
            executable = str(Path(temporary) / 'pixel-test')
            subprocess.run([compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                            '-I', str(ROOT / 'native'),
                            str(ROOT / 'native/pixel_channels.c'),
                            str(ROOT / 'tests/native_pixel_channels_test.c'),
                            '-o', executable], check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([executable], check=True, capture_output=True, text=True, timeout=15)

    def test_freestanding_objects_need_no_runtime_helpers(self):
        """No libc or compiler runtime calls are left in the objects.

        A firmware adapter links no libc and no libgcc, so any helper the
        compiler emits (memcpy for a struct copy, a division helper) would only
        surface at link time. Only the project's own functions may stay
        undefined across units. This checks the source, on the host toolchain;
        it is not an SH build and says nothing about SH code generation.
        """
        compiler = shutil.which('cc')
        lister = shutil.which('nm')
        self.assertIsNotNone(compiler)
        self.assertIsNotNone(lister)
        with tempfile.TemporaryDirectory(prefix='xdj-freestanding-') as temporary:
            for name in ('waveform_cell', 'waveform_prepare', 'pixel_channels',
                         'waveform_adapter'):
                obj = str(Path(temporary) / (name + '.o'))
                subprocess.run([compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                                '-O2', '-ffreestanding', '-fno-builtin',
                                '-I', str(ROOT / 'native'),
                                str(ROOT / 'native' / (name + '.c')),
                                '-c', '-o', obj],
                               check=True, capture_output=True, text=True, timeout=30)
                undefined = subprocess.run([lister, '-u', obj], check=True,
                                           capture_output=True, text=True, timeout=15)
                external = [line.split()[-1].lstrip('_') for line in undefined.stdout.splitlines() if line.strip()]
                self.assertEqual([s for s in external if not s.startswith('xdj_')], [],
                                 f'{name} needs a symbol outside this project')

    def test_division_without_a_divide_instruction(self):
        """SH-4A has no integer divide; the helper must match the C operator exactly."""
        compiler = shutil.which('cc')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory(prefix='xdj-divide-test-') as temporary:
            executable = str(Path(temporary) / 'divide-test')
            subprocess.run([compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                            '-I', str(ROOT / 'native'),
                            str(ROOT / 'tests/native_divide_test.c'),
                            '-o', executable], check=True, capture_output=True, text=True, timeout=60)
            subprocess.run([executable], check=True, capture_output=True, text=True, timeout=120)

    def test_prepare_with_ubsan_and_guards(self):
        compiler = shutil.which('cc')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory(prefix='xdj-prepare-test-') as temporary:
            executable = str(Path(temporary) / 'prepare-test')
            subprocess.run([compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                            '-I', str(ROOT / 'native'),
                            str(ROOT / 'native/waveform_cell.c'),
                            str(ROOT / 'native/waveform_prepare.c'),
                            str(ROOT / 'tests/native_waveform_prepare_test.c'),
                            '-o', executable], check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([executable], check=True, capture_output=True, text=True, timeout=15)

    def test_region_and_scaled_geometry_with_ubsan_and_guards(self):
        """The INFO cell rectangle and column counts other than 80."""
        compiler = shutil.which('cc')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory(prefix='xdj-region-test-') as temporary:
            executable = str(Path(temporary) / 'region-test')
            subprocess.run([compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                            '-I', str(ROOT / 'native'),
                            str(ROOT / 'native/waveform_cell.c'),
                            str(ROOT / 'native/waveform_prepare.c'),
                            str(ROOT / 'tests/native_waveform_region_test.c'),
                            '-o', executable], check=True, capture_output=True, text=True, timeout=60)
            subprocess.run([executable], check=True, capture_output=True, text=True, timeout=60)

    def test_adapter_cache_and_draw_with_ubsan_and_guards(self):
        compiler = shutil.which('cc')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory(prefix='xdj-adapter-test-') as temporary:
            executable = str(Path(temporary) / 'adapter-test')
            subprocess.run([compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                            '-I', str(ROOT / 'native'),
                            str(ROOT / 'native/waveform_cell.c'),
                            str(ROOT / 'native/waveform_prepare.c'),
                            str(ROOT / 'native/waveform_adapter.c'),
                            str(ROOT / 'tests/native_waveform_adapter_test.c'),
                            '-o', executable], check=True, capture_output=True, text=True, timeout=60)
            subprocess.run([executable], check=True, capture_output=True, text=True, timeout=30)

    def test_c_render_contract_with_ubsan_and_guards(self):
        compiler = shutil.which('cc')
        self.assertIsNotNone(compiler, 'C compiler required to verify native render core')
        with tempfile.TemporaryDirectory(prefix='xdj-cell-test-') as temporary:
            executable = str(Path(temporary) / 'cell-test')
            subprocess.run([compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                            '-fno-omit-frame-pointer',
                            '-I', str(ROOT / 'native'),
                            str(ROOT / 'native/waveform_cell.c'),
                            str(ROOT / 'tests/native_waveform_cell_test.c'),
                            '-o', executable], check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([executable], check=True, capture_output=True, text=True, timeout=15)
