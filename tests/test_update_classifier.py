import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_update_classifier import inspect, prove_routine, START, JOIN, END
APP=ROOT/'private/extracted/v144/main-010000-unpacked.bin'

@unittest.skipUnless(APP.exists(),'Private updater absent')
class Classifier(unittest.TestCase):
    def test_all_normal_paths_return_three(self):
        report=inspect(APP.read_bytes())
        self.assertTrue(report['every_structural_path_reaches_constant_return'])
        self.assertEqual(report['return_value'],3)
        self.assertGreater(len(report['branches']),10)

    def test_rejects_bypass_of_constant_return(self):
        code=bytearray(APP.read_bytes()[START:END])
        # Replace the entry by BRA directly to ADD SP after MOV #3.
        disp=(JOIN+2-(START+4))//2
        code[:2]=(0xa000|disp).to_bytes(2,'little')
        code[2:4]=b'\x09\x00'
        with self.assertRaisesRegex(ValueError,'bypasses'):
            prove_routine(bytes(code))

    def test_refuses_different_return_value_or_reference(self):
        data=APP.read_bytes();code=bytearray(data[START:END]);code[JOIN-START]=2
        with self.assertRaises(ValueError):prove_routine(bytes(code))
        with self.assertRaises(ValueError):inspect(data[:-1])
