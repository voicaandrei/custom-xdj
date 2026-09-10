import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from index_row_request import analyze, built_word, shift_jis_at

IMAGE = ROOT / 'private/extracted/v144/main-040000-unpacked.bin'


class RowRequestHelpers(unittest.TestCase):
    def test_built_word_checks_every_instruction(self):
        # mov #7,r4 ; shll8 r4 ; add #11,r4  ->  0x70b
        data = bytes.fromhex('07e4') + bytes.fromhex('1844') + bytes.fromhex('0b74')
        self.assertEqual(built_word(data, 0, 2, 4), 0x70b)
        with self.assertRaises(ValueError):
            built_word(data, 0, 4, 4)   # the middle word is not SHLL8
        with self.assertRaises(ValueError):
            built_word(data, 2, 2, 4)   # the first word is not an immediate MOV

    def test_shift_jis_bounds(self):
        data = 'ﾘｽﾄ要求'.encode('shift_jis') + b'\x00'
        self.assertEqual(shift_jis_at(data, 0xa8000000), 'ﾘｽﾄ要求')
        self.assertIsNone(shift_jis_at(data, 0xa7ffffff))
        self.assertIsNone(shift_jis_at(data, 0xa8000000 + len(data)))
        self.assertIsNone(shift_jis_at(b'\xff\xfe\x00', 0xa8000000))

    def test_hash_guard(self):
        with self.assertRaises(ValueError):
            analyze(b'not the 1.44 application')


@unittest.skipUnless(IMAGE.exists(), 'Private 1.44 application absent')
class RowRequest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = analyze(IMAGE.read_bytes())

    def test_artwork_eligibility_is_distinct_from_a_sent_request(self):
        gate=self.report['artwork_eligibility']
        self.assertEqual(gate['flag_halfword_mask'],0x4000)
        self.assertEqual(gate['state_without_flag'],1)
        self.assertEqual(gate['state_with_flag'],2)
        self.assertFalse(gate['state_2_alone_means_request_sent'])

    def test_three_tracked_message_kinds(self):
        kinds = {kind['message_number']: kind['label']
                 for kind in self.report['message_kinds']}
        self.assertEqual(sorted(kinds), [0x709, 0x70b, 0x71b])
        self.assertEqual(kinds[0x709], 'ﾘｽﾄ要求')
        self.assertEqual(kinds[0x70b], 'ｱｰﾄﾜｰｸ要求')
        self.assertEqual(kinds[0x71b], 'ﾌｨﾙﾀ要求')
        # Each kind occupies its own fields, so none of them share a slot.
        used = [field for kind in self.report['message_kinds']
                for field in kind['tracking_fields_bytes']]
        self.assertEqual(len(used), len(set(used)))

    def test_preparer_marks_the_slot_pending_before_the_request(self):
        preparer = self.report['request_preparer']
        self.assertEqual(preparer['entry_file_offset'], 0x1514c7c)
        self.assertEqual(preparer['pending_state_value'], 2)
        self.assertEqual(preparer['skip_when_pending_opcode'], 0x8802)
        self.assertEqual(preparer['skip_when_complete_opcode'], 0x8803)
        # The state is written after both skip tests, never before.
        self.assertLess(preparer['skip_when_pending_file_offset'],
                        preparer['skip_when_complete_file_offset'])
        self.assertLess(preparer['skip_when_complete_file_offset'],
                        preparer['pending_state_store_file_offset'])

    def test_builder_sends_the_artwork_number_with_the_row_identifier(self):
        builder = self.report['request_builder']
        artwork = next(kind for kind in self.report['message_kinds']
                       if kind['label'] == 'ｱｰﾄﾜｰｸ要求')
        self.assertEqual(builder['message_number'], artwork['message_number'])
        self.assertEqual(builder['message_number'], 0x70b)
        self.assertEqual(builder['message_bytes'], 112)
        self.assertEqual(builder['marker'], '_MSG')
        # The two identifier halves come from the helpers the row model also uses.
        self.assertEqual(builder['identifier_helpers'], [0x09445c90, 0x09445c94])
        self.assertEqual(builder['identifier_fields_bytes'], [36, 40])

    def test_dispatcher_wires_prepare_and_completion(self):
        dispatcher = self.report['dispatcher']
        self.assertEqual(dispatcher['callers_of_preparer'], [0x154a45c])
        self.assertEqual(dispatcher['callers_of_completion'], [0x154a42c])
        # The completion is consulted before a new request is prepared.
        self.assertLess(dispatcher['callers_of_completion'][0],
                        dispatcher['callers_of_preparer'][0])


@unittest.skipUnless(IMAGE.exists(), 'Private 1.44 application absent')
class ListRequestSites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = analyze(IMAGE.read_bytes())

    def test_every_request_asks_for_the_slot_capacity(self):
        """Rows are always 8, so the browser does not choose the INFO fields."""
        sites = self.report['list_request_sites']
        self.assertEqual(sites['log_text'], 'ﾘｽﾄ要求 MODE=%s, 行数=%d, 選択位置=%d'
                         .replace('ﾘｽﾄ', '右ﾘｽﾄ'))
        self.assertEqual({site['rows'] for site in sites['sites']}, {8})
        self.assertGreaterEqual(len({site['mode'] for site in sites['sites']}), 8)
        self.assertEqual(sites['constructor_file_offset'], 0x151898a)
