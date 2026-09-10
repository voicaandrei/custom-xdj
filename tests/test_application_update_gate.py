import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_application_update_gate import main_gate, parse_numeric_version, verify


APP = ROOT / "private/extracted/v144/main-040000-unpacked.bin"
STOCK = b"XDJ-1000MK2 MAINVer1.44\0       0"


class ApplicationUpdateGateModel(unittest.TestCase):
    def test_force_marker_preserves_numeric_version_and_processes(self):
        forced = bytearray(STOCK)
        forced[24] = ord("+")
        self.assertEqual(parse_numeric_version(STOCK), 1440)
        self.assertEqual(parse_numeric_version(bytes(forced)), 1440)
        self.assertEqual(main_gate(STOCK, 1440), 2)
        self.assertEqual(main_gate(bytes(forced), 1440), 3)

    def test_newer_version_and_runtime_force_process(self):
        self.assertEqual(main_gate(STOCK, 1430), 3)
        self.assertEqual(main_gate(STOCK, 1440, runtime_flag=1), 3)
        self.assertEqual(main_gate(STOCK, 1450), 2)

    def test_label_shape_is_bounded(self):
        with self.assertRaises(ValueError):
            parse_numeric_version(STOCK[:-1])


@unittest.skipUnless(APP.exists(), "Private v1.44 application absent")
class ApplicationUpdateGateBinary(unittest.TestCase):
    def test_exact_gate_bytes_and_pointers(self):
        report = verify(APP.read_bytes())
        self.assertEqual(report["same_version_default_result"], 2)
        self.assertEqual(report["same_version_forced_result"], 3)

    def test_rejects_an_altered_gate(self):
        changed = bytearray(APP.read_bytes())
        changed[0x1557330] ^= 1
        with self.assertRaises(ValueError):
            verify(bytes(changed))


if __name__ == "__main__":
    unittest.main()
