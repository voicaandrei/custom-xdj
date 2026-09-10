import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from index_compositor import analyze, third_argument

IMAGE = ROOT / 'private/extracted/v144/main-040000-unpacked.bin'


class CompositorHelpers(unittest.TestCase):
    def test_third_argument_takes_the_nearest_preceding_load(self):
        # mov #3,r6 ; mov #7,r6 ; nop  -> the later load wins
        data = bytes.fromhex('03e6') + bytes.fromhex('07e6') + bytes.fromhex('0900')
        self.assertEqual(third_argument(data, 4), 7)
        # A load into another register is ignored.
        other = bytes.fromhex('03e5') + bytes.fromhex('0900')
        self.assertIsNone(third_argument(other, 2))
        self.assertIsNone(third_argument(b'\x00' * 8, 6))

    def test_hash_guard(self):
        with self.assertRaises(ValueError):
            analyze(b'not the 1.44 application')


@unittest.skipUnless(IMAGE.exists(), 'Private 1.44 application absent')
class Compositor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = analyze(IMAGE.read_bytes())

    def test_exactly_two_layers(self):
        layers = self.report['layers']
        self.assertEqual(layers['count'], 2)
        self.assertEqual(layers['array_pointer'], 0x0b5fa640)
        self.assertEqual(layers['entry_stride_bytes'], 48)
        self.assertEqual(layers['capacity'], 256)
        self.assertEqual(layers['reject_message'], 'Not a valid layer')

    def test_window_pool_is_a_fixed_array(self):
        pool = self.report['window_pool']
        self.assertEqual(pool['pool_pointer'], 0x0b5f6640)
        self.assertEqual(pool['entry_stride_bytes'], 64)
        self.assertEqual(pool['in_use_flag'], 0x40000000)
        self.assertEqual(pool['exhausted_message'], 'can not created new window')
        # Nothing outside graphics init and the constructor touches the pool,
        # so no compositor walks it.
        self.assertEqual(len(pool['literal_users']), 4)

    def test_artwork_surfaces_go_to_layer_zero(self):
        constructor = self.report['window_constructor']
        self.assertEqual(constructor['artwork_layer_argument'], 0)
        self.assertEqual(constructor['layer_field_in_params_bytes'], 16)
        self.assertGreater(constructor['call_sites'], 30)

    def test_attach_value_never_varies(self):
        """The one byte that could order windows is the same at every site."""
        attach = self.report['layer_attach']
        self.assertEqual(attach['distinct_third_arguments'], [0])
        self.assertGreaterEqual(len(attach['sites']), 5)

    def test_stacking_order_is_reported_unknown(self):
        self.assertEqual(self.report['stacking_order']['status'], 'UNKNOWN')
        self.assertIn('not established',
                      self.report['stacking_order']['consequence'])

    def test_screen_size_comes_from_code_not_a_photo(self):
        screen = self.report['screen']
        self.assertEqual((screen['width'], screen['height']), (800, 480))
        # The INFO artwork rectangle fits inside it with room to spare.
        self.assertLess(659 + 128, screen['width'])
        self.assertLess(132 + 121, screen['height'])
