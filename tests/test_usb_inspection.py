import unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from inspect_usb_player import analyze
class USBInspection(unittest.TestCase):
    def test_wrong_device_fails_closed(self):
        with self.assertRaises(ValueError):analyze('"idVendor" = 1\n"idProduct" = 17')
    @unittest.skipUnless((ROOT/'private/owner/usb-xdj-services.txt').exists(),'Private device snapshot absent')
    def test_real_snapshot_and_descriptor_match(self):
        raw=(ROOT/'private/owner/usb-xdj-services.txt').read_text()
        r=analyze(raw)
        self.assertEqual([x['bInterfaceNumber'] for x in r['interfaces']],[0,1,2,3,4])
        self.assertEqual(r['hid']['sha256'],'7765f4aeb734b1467951d518c070c30cf38aa101b9e6e59f7204fed9ef85cd15')
        self.assertEqual(r['hid']['max_output_report'],64)
        self.assertFalse(r['serial_interface_in_observed_configuration'])
        with self.assertRaises(ValueError):analyze(raw,b'wrong firmware')
        image=ROOT/'private/extracted/v144/main-040000-unpacked.bin'
        if image.exists():self.assertEqual(analyze(raw,image.read_bytes())['firmware_match']['descriptor_offsets'],[0x15f0ec0])
