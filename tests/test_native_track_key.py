import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class NativeTrackKey(unittest.TestCase):
    def test_source_track_and_media_incarnation_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'key-test'
            subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'native'),str(ROOT/'native/track_key.c'),str(ROOT/'tests/native_track_key_test.c'),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([str(exe)],check=True,capture_output=True)
