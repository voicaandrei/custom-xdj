"""Test 09 project-wrapper execution, reusing the bounded SH instruction model."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_beta09 import link_beta
from build_sh import toolchain
from tests.test_beta08_execution import Machine, MASK, RETURN, SP, CONTEXT, ROW, CONNECTION

@unittest.skipUnless(toolchain() and (ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(), 'toolchain/reference absent')
class Beta09Execution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            linked = link_beta(folder, (ROOT / 'private/extracted/v144/main-040000-unpacked.bin').stat().st_size)
            nm = subprocess.run([toolchain()['nm'], '-n', str(folder/'browser-waveform-beta06.elf')], check=True, capture_output=True, text=True).stdout
            cls.symbols = {p[2]: int(p[0], 16) for line in nm.splitlines() if len(p := line.split()) == 3}
            cls.base = linked['code_pointer']
            # Exclude all C code from the executable model. C is tested separately.
            cls.code = linked['payload'][:cls.symbols['_render']-cls.base]

    def request(self, kind=2, track=3902, artwork=77, stock_return=1,
                rgb=True, rgb_result=1, rgb_valid=True, blue_result=1,
                blue_valid=True, row_present=True, source_remote=1,
                source_player=4, source_slot=3, source_present=True):
        events = []
        def reset(m): events.append(('reset',)); return 0
        def trace(m): events.append(('stage', m.r[4])); return 0
        def invalidate(m): events.append(('invalidate',)); return 0
        def colour(m):
            self.assertEqual(m.r[4:6], [source_player if source_remote else 0, source_slot])
            events.append(("colour", m.r[4], m.r[5])); return 3 if rgb else 1
        def wave_rgb(m):
            self.assertEqual(m.r[4:6], [CONNECTION, track])
            self.assertEqual(m.r[6:8], [self.symbols['_xdj_beta_pwv4_tag'], self.symbols['_xdj_beta_ext_name']])
            for off, value in ((0, 7228), (4, 0x700000 if rgb_result else 0), (8, 123)):
                m.write(m.read(m.r[15]+off), value)
            events.append(('rgb', track)); return rgb_result
        def wave_blue(m):
            self.assertEqual(m.r[4:6], [CONNECTION, track])
            self.assertEqual([m.read(m.r[15]+i) for i in (0,4,8)], [0,0,0])
            m.write(m.r[6], 900); m.write(m.r[7], 0x710000 if blue_result else 0)
            events.append(('blue', track)); return blue_result
        def prepare(m, which, valid, pointer, size):
            self.assertEqual(m.r[4:7], [pointer, size, track])
            events.append(('prepare', which)); return int(valid)
        def release(m): events.append(('release', m.r[4])); return 0
        def image(m):
            self.assertEqual(m.r[4:8], [CONNECTION, 77, 0x630000, 0x630004])
            m.write(m.r[6], 1234); m.write(m.r[7], 0x720000)
            events.append(('image',)); return stock_return
        callbacks = {
            self.symbols['_xdj_beta_trace_reset']: reset, self.symbols['_xdj_beta_trace']: trace,
            self.symbols['_xdj_beta_invalidate']: invalidate, 0x09445274: colour,
            0x0929626c: wave_rgb, 0x09293d76: wave_blue, 0x09382a9a: release,
            self.symbols['_xdj_beta_prepare_rgb']: lambda m: prepare(m, 'rgb', rgb_valid, 0x700000, 7228),
            self.symbols['_xdj_beta_prepare_blue']: lambda m: prepare(m, 'blue', blue_valid, 0x710000, 900),
            0x09293bb0: image}
        machine = Machine(self.code, self.base, self.symbols['xdj_beta_getimage_hook'], callbacks)
        machine.r[4:8] = [CONNECTION, 77, 0x630000, 0x630004]
        machine.r[13] = CONTEXT if kind is not None else 0
        if kind is not None: machine.write(CONTEXT, kind)
        if kind in (1, 2):
            machine.write(SP+16, ROW if row_present else 0)
            machine.write(ROW, track); machine.write(ROW+8, artwork)
        machine.write(CONNECTION, 0x640000 if source_present else 0)
        machine.write(CONNECTION+4, source_slot); machine.write(CONNECTION+8, 1)
        if source_present:
            machine.write(0x640004, source_remote)
            if source_remote: machine.write(0x640008, source_player)
        original = machine.r.copy()
        machine.run()
        self.assertEqual(machine.r[8:16], original[8:16])
        self.assertEqual(machine.r[0], stock_return & MASK)
        self.assertEqual(machine.read(0x630000), 1234)
        self.assertEqual(machine.read(0x630004), 0x720000)
        self.assertEqual(events.count(('image',)), 1)
        return events, machine

    def test_both_validated_row_branches_fetch_rgb_and_release_once(self):
        for kind in (1, 2):
            with self.subTest(kind=kind):
                events, _ = self.request(kind=kind)
                self.assertIn(('rgb', 3902), events)
                self.assertIn(('stage', 7), events)
                self.assertEqual(events.count(('release', 0x700000)), 1)
                self.assertFalse(any(e[0] == 'blue' for e in events))

    def test_unsupported_contexts_never_read_uninitialized_caller_row(self):
        for kind in (0, 3, None):
            with self.subTest(kind=kind):
                events, machine = self.request(kind=kind)
                self.assertNotIn((SP+16, 4), machine.reads)
                self.assertFalse(any(e[0] in ('rgb', 'blue') for e in events))
                self.assertIn(('stage', 11) if kind is not None else ('reset',), events)

    def test_zero_id_mismatch_and_null_row_do_not_query(self):
        for args in ({'track':0}, {'artwork':78}, {'row_present':False}):
            with self.subTest(args=args):
                events, _ = self.request(**args)
                self.assertFalse(any(e[0] in ('rgb', 'blue') for e in events))

    def test_blue_setting_skips_rgb_and_releases_blue_once(self):
        events, _ = self.request(rgb=False)
        self.assertNotIn(('rgb', 3902), events)
        self.assertIn(('stage',10), events)
        self.assertEqual(events.count(('release',0x710000)), 1)

    def test_rgb_failure_and_malformed_payload_fall_back_to_blue(self):
        for args in ({'rgb_result':0}, {'rgb_result':-1}, {'rgb_valid':False}):
            with self.subTest(args=args):
                events, _ = self.request(**args)
                self.assertIn(('blue', 3902), events)
                self.assertEqual(events.count(('release',0x710000)), 1)
                self.assertLessEqual(events.count(('release',0x700000)), 1)

    def test_stock_result_survives_callee_saved_register_restore(self):
        for result in (0, 1, -1, -123):
            with self.subTest(result=result):
                events, _ = self.request(stock_return=result)
                self.assertEqual(('invalidate',) in events, result <= 0)

    def test_decoder_five_arguments_success_error_and_register_preservation(self):
        for result in (0, 1, -1):
            with self.subTest(result=result):
                calls = []
                def decoder(m):
                    self.assertEqual(m.r[4:8], [11, 22, 33, 44])
                    self.assertEqual(m.read(m.r[15]), 55)
                    return result
                def apply(m):
                    self.assertEqual(m.r[4:6], [44,55]); calls.append('apply'); return 1
                def invalid(m): calls.append('invalidate'); return 0
                callbacks = {0x09304066:decoder,
                             self.symbols['_xdj_beta_apply_or_trace_surfaces']:apply,
                             self.symbols['_xdj_beta_invalidate']:invalid}
                m = Machine(self.code, self.base, self.symbols['xdj_beta_decode_hook'], callbacks)
                m.r[4:8] = [11,22,33,44]; m.write(SP,55)
                saved = m.r.copy(); m.run()
                self.assertEqual(m.r[8:16], saved[8:16])
                self.assertEqual(m.r[0], result & MASK)
                self.assertEqual(calls, ['apply'] if result >= 0 else ['invalidate'])

    def test_local_source_uses_zero_player_and_media_slot_not_database_type(self):
        events, _ = self.request(source_remote=0, source_slot=3)
        self.assertIn(('colour', 0, 3), events)
        self.assertIn(('rgb', 3902), events)

    def test_remote_source_uses_actual_player_and_slot(self):
        for player, slot in ((1,2), (4,3), (72,5)):
            with self.subTest(player=player, slot=slot):
                events, _ = self.request(source_player=player, source_slot=slot)
                self.assertIn(('colour',player,slot), events)
                self.assertIn(('rgb',3902), events)

    def test_missing_source_falls_back_without_dereferencing_null(self):
        events, _ = self.request(source_present=False)
        self.assertFalse(any(e[0] in ('colour','rgb') for e in events))
        self.assertIn(('blue',3902), events)


if __name__ == '__main__': unittest.main()
