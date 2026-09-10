import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class BrowserRow(unittest.TestCase):
    def test_all_row_kinds_and_main_id_independent_of_artwork(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'test'
            subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'native'),
                str(ROOT/'native/browser_row.c'),str(ROOT/'tests/native_browser_row_test.c'),
                '-o',str(target)],check=True,capture_output=True,text=True)
            subprocess.run([str(target)],check=True,capture_output=True,text=True)
