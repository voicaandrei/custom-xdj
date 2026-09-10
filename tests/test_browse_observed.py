"""Unpackaged follow-up: observe navigation even while artwork is pending."""
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class BrowseObserved(unittest.TestCase):
    def test_navigation_during_pending_and_stock_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'observed'
            subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror',
                '-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'native'),
                str(ROOT/'tests/native_beta_browse_observed_test.c'),'-o',str(exe)],
                check=True,capture_output=True,timeout=30)
            subprocess.run([str(exe)],check=True,timeout=10)

    def test_new_callsite_is_after_dispatch_before_pending_exit(self):
        if not (ROOT/'private/extracted/v144/main-040000-unpacked.bin').exists(): self.skipTest('Official firmware not supplied')
        b=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
        self.assertEqual(hashlib.sha256(b).hexdigest(),
            '9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0')
        self.assertEqual(b[0x154a59c:0x154a5a0].hex(),'ca1e5109')
        self.assertEqual(b[0x154a404:0x154a41c].hex(),
            '65d1c36401ed0b41d22c6a020820e922028d6a4235ae0900')
