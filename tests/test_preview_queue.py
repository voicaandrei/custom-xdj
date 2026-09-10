import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'private/owner/link-fixtures/player4-3902/link-preview-blue.bin'
@unittest.skipUnless(FIXTURE.exists(),'Private preview response absent')
class PreviewQueue(unittest.TestCase):
    def test_worker_integration_scroll_eject_mode_disable_failure_and_token(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'test'
            units=['preview_queue','blue_request','waveform_dbserver','waveform_adapter',
                   'waveform_prepare','waveform_cell','track_key','pixel_channels']
            subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'native'),
                *[str(ROOT/'native'/f'{u}.c') for u in units],
                str(ROOT/'tests/native_preview_queue_test.c'),'-o',str(target)],
                check=True,capture_output=True,text=True)
            subprocess.run([str(target),str(FIXTURE)],check=True,capture_output=True,text=True)
