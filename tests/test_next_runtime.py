import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'private/owner/link-fixtures/player4-3902/link-preview-rgb.bin'

@unittest.skipUnless(FIXTURE.exists(),'Frozen RGB fixture absent')
class NextRuntime(unittest.TestCase):
    def test_frame_parity_cancellation_invalid_input_and_bounds(self):
        with tempfile.TemporaryDirectory(prefix='xdj-next-runtime-') as tmp:
            obj=Path(tmp)/'reference.o';binary=Path(tmp)/'next-runtime'
            flags=['-std=c99','-O1','-Wall','-Wextra','-Werror',
                   '-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'native')]
            names=['prepare_rgb','prepare_blue','invalidate','apply_surfaces',
                   'trace_reset','trace','apply_or_trace_surfaces','pwv4_tag','ext_name']
            subprocess.run(['cc',*flags,*[f'-Dxdj_beta_{n}=reference_{n}' for n in names],
                '-c',str(ROOT/'native/beta_runtime_band.c'),'-o',str(obj)],
                check=True,capture_output=True,timeout=30)
            subprocess.run(['cc',*flags,str(obj),*[str(ROOT/p) for p in (
                'native/beta_runtime_next.c','native/waveform_prepare_fast.c',
                'native/waveform_prepare.c','native/waveform_cell.c','native/pixel_channels.c',
                'tests/native_next_runtime_test.c')],'-o',str(binary)],
                check=True,capture_output=True,timeout=30)
            subprocess.run([str(binary),str(FIXTURE)],check=True,capture_output=True,timeout=20)
