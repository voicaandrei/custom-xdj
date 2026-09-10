import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from decode_link_preview import blue_to_pwav,rgb_to_pwv4
FIXTURE=ROOT/'private/owner/link-fixtures/player4-3902'
@unittest.skipUnless((FIXTURE/'link-preview-rgb.bin').exists(),'Private player fixture absent')
class NativeDbserver(unittest.TestCase):
    def test_player_payloads_feed_native_cache_and_bounded_info_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp=Path(directory);blue=FIXTURE/'link-preview-blue.bin';rgb=FIXTURE/'link-preview-rgb.bin'
            (tmp/'pwav').write_bytes(blue_to_pwav(blue.read_bytes()))
            (tmp/'pwv4').write_bytes(rgb_to_pwv4(rgb.read_bytes()))
            units=['waveform_dbserver','waveform_adapter','waveform_prepare','waveform_cell']
            subprocess.run(['cc','-std=c99','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'native'),*[str(ROOT/'native'/f'{u}.c') for u in units],str(ROOT/'tests/native_waveform_dbserver_test.c'),'-o',str(tmp/'test')],check=True,capture_output=True,text=True,timeout=30)
            subprocess.run([str(tmp/'test'),str(blue),str(rgb),str(tmp/'pwav'),str(tmp/'pwv4')],check=True,capture_output=True,text=True,timeout=15)
