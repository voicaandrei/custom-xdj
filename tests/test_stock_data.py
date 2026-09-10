import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from index_stock_data import analyze, ascii_at, entry_of, named_api

IMAGE = ROOT / 'private/extracted/v144/main-040000-unpacked.bin'


class StockDataHelpers(unittest.TestCase):
    def test_ascii_at_bounds_and_terminator(self):
        data = b'EXT\x00' + b'x' * 4
        self.assertEqual(ascii_at(data, 0xa8000000), 'EXT')
        self.assertIsNone(ascii_at(data, 0xa7ffffff))
        self.assertIsNone(ascii_at(data, 0xa8000000 + len(data)))
        self.assertIsNone(ascii_at(data, 0xa8000004))          # no terminator
        self.assertIsNone(ascii_at(data, 0xa8000000, limit=2))  # longer than allowed

    def test_entry_requires_a_recognised_prologue(self):
        # RTS, delay slot, then a push prologue: accepted.
        good = bytes.fromhex('0b00') + bytes.fromhex('0900') + bytes.fromhex('962f') + b'\x00\x00'
        self.assertEqual(entry_of(good, 6), 4)
        # Same shape but the candidate is not a prologue: reported as unknown.
        bad = bytes.fromhex('0b00') + bytes.fromhex('0900') + bytes.fromhex('0000') + b'\x00\x00'
        self.assertIsNone(entry_of(bad, 6))
        self.assertIsNone(entry_of(b'\x00' * 8, 6))

    def test_named_api_finds_prefixed_names_only(self):
        data = b'\x00dbcl_GetImage\x00DbReqJpegData\x00nope_GetImage\x00'
        names = [entry['name'] for entry in named_api(data)]
        self.assertEqual(names, ['DbReqJpegData', 'dbcl_GetImage'])

    def test_hash_guard(self):
        with self.assertRaises(ValueError):
            analyze(b'not the 1.44 application')


@unittest.skipUnless(IMAGE.exists(), 'Private 1.44 application absent')
class StockData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = IMAGE.read_bytes()
        cls.report = analyze(cls.data)

    def test_colour_getter_shape(self):
        getter = self.report['colour_setting_getter']
        self.assertEqual(getter['entry_file_offset'], 0x1445274)
        self.assertEqual(getter['first_argument_upper_bound'], 72)
        self.assertEqual(getter['second_argument_upper_bound_exclusive'], 6)
        self.assertEqual(getter['first_argument_stride_bytes'], 0x414)
        self.assertEqual(getter['second_argument_stride_bytes'], 0xa8)
        self.assertEqual(getter['table_pointer'], 0x0c7a4a7a)
        self.assertEqual(getter['state_pointer'], 0x0c7a484c)
        self.assertEqual(getter['accepted_values'], [1, 3])
        self.assertEqual(getter['accept_opcodes'], [0x8801, 0x8803])
        self.assertEqual(getter['default_value'], 1)

    def test_colour_getter_is_already_called_from_several_places(self):
        callers = self.report['colour_setting_getter']['callers']
        self.assertGreaterEqual(len(callers), 5)
        # One caller sits in the settings UI, another in the song-info assembly.
        self.assertIn(0x12b4452, callers)
        self.assertIn(0x12cad64, callers)

    def test_preview_and_image_accessors_resolve(self):
        by_name = {entry['name']: entry for entry in self.report['resolved_api']}
        self.assertEqual(by_name['dbcl_GetWaveData']['entry_file_offset_candidates'],
                         [0x1293d76])
        self.assertEqual(by_name['dbcl_GetParWaveData']['entry_file_offset_candidates'],
                         [0x1295914])
        self.assertEqual(by_name['dbcl_GetImage2']['entry_file_offset_candidates'],
                         [0x1293c98])
        # The heuristic refuses to name a function it cannot confirm.
        self.assertEqual(by_name['dbcl_GetImage']['entry_file_offset_candidates'], [])

    def test_named_api_surface_is_large_and_includes_the_wave_calls(self):
        names = {entry['name'] for entry in self.report['named_api']}
        self.assertGreater(len(names), 80)
        for expected in ('dbcl_GetWaveData', 'dbcl_GetParWaveData', 'dbcl_GetImage',
                         'dbcl_GetImage2', 'DbReq_TabletSongInfo', 'DbReqJpegData2'):
            self.assertIn(expected, names)

    def test_section_lookup_asks_the_ext_file_for_named_tags(self):
        sites = self.report['section_lookup']['sites']
        self.assertEqual(len(sites), 7)
        self.assertTrue(all(site['file_kind'] == 'EXT' for site in sites))
        tags = {site['tag'] for site in sites}
        self.assertEqual(tags, {'PVB2', 'PQT2', 'PWV5', 'PWV4'})
        pwv4 = [site for site in sites if site['tag'] == 'PWV4']
        self.assertEqual([site['call_file_offset'] for site in pwv4], [0x12cbf94])
