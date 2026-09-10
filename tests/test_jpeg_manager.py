import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from index_jpeg_manager import analyze, bsr_target


class JpegManager(unittest.TestCase):
    def test_hash_guard(self):
        with self.assertRaises(ValueError): analyze(b'other image')

    def test_relative_call_forward_backward_and_invalid(self):
        self.assertEqual(bsr_target(bytes.fromhex('02b0'), 0), 8)
        self.assertEqual(bsr_target(bytes.fromhex('ffbf'), 0), 2)
        for data, pc in [(b'\0\0', 0), (b'\x02\xb0', 1), (b'', 0)]:
            with self.assertRaises(ValueError): bsr_target(data, pc)

    @unittest.skipUnless((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(),
                         'Private 1.44 application absent')
    def test_request_consumed_by_jpeg_manager_and_forwarded_on_cache_miss(self):
        report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
        self.assertEqual(report['task']['name'], 'JpegMgrTask')
        self.assertEqual(report['task']['entry_pointer'], 0x09411d90)
        self.assertEqual(report['task']['request_number'], 0x70b)
        self.assertEqual(report['task']['request_handler'], 0x14122e0)
        self.assertEqual(report['task']['completion_handler'], 0x1412614)
        cache = report['cache_static']
        self.assertEqual((cache['entries'], cache['entry_stride_bytes']), (512, 30744))
        self.assertEqual(cache['entries'] * cache['entry_stride_bytes'], 0xf03000)
        self.assertEqual(cache['miss_request_constructor'], 0x14121a0)
        self.assertEqual(report['miss_forwarding']['message_number'], 0x70b)
        self.assertEqual(report['miss_forwarding']['destination_mailbox_literal']['pointer_value'], 0x0c7a3090)

        downstream = report['downstream']
        self.assertEqual(downstream['mailbox_alias_a']['pointer_value'], 0x0b2138c0)
        self.assertEqual(downstream['mailbox_alias_b']['pointer_value'], 0x0c7a3090)
        self.assertEqual(downstream['jpeg_request_handler_literal']['pointer_value'], 0x092a4a90)
        self.assertEqual(downstream['get_image_literal']['pointer_value'], 0x09293bb0)
        self.assertEqual(downstream['get_image_diagnostic'], 'dbcl_GetImage')
        self.assertEqual(downstream['image_request_number'], 0x2003)
        self.assertEqual(downstream['image_response_number'], 0x4002)
