"""Test 10 project-wrapper execution, reusing the bounded SH instruction model."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_beta10 import link_beta
from build_sh import toolchain
from tests.test_beta08_execution import Machine as BaseMachine, MASK, RETURN, SP, CONTEXT, ROW, CONNECTION

class Machine(BaseMachine):
    def ordinary(self, w, pc):
        if w & 0xff00 == 0x8400:  # mov.b @(disp,rM),r0 (sign extended)
            v = self.read(self.r[(w >> 4) & 15] + (w & 15), 1)
            self.r[0] = (v - 256 if v & 128 else v) & MASK
        elif w & 0xf00f == 0x600c:  # extu.b
            self.r[(w >> 8) & 15] = self.r[(w >> 4) & 15] & 255
        else:
            super().ordinary(w, pc)

@unittest.skipUnless(toolchain() and (ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(), 'toolchain/reference absent')
class Beta10Execution(unittest.TestCase):
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
                source_player=4, source_slot=3, source_present=True,
                cancel_phase=None, pending_cancel=False, cancel_enabled=True):
        events = []
        def cancel(m, phase):
            if cancel_phase == phase: m.mem[CONTEXT+12] = 1
        def lookup(m):
            self.assertEqual(m.r[4], 0x670000)
            events.append(('lookup',)); return 2 if pending_cancel else -1
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
            cancel(m, 'rgb')
            events.append(('rgb', track)); return rgb_result
        def wave_blue(m):
            self.assertEqual(m.r[4:6], [CONNECTION, track])
            self.assertEqual([m.read(m.r[15]+i) for i in (0,4,8)], [0,0,0])
            m.write(m.r[6], 900); m.write(m.r[7], 0x710000 if blue_result else 0)
            cancel(m, 'blue')
            events.append(('blue', track)); return blue_result
        def prepare(m, which, valid, pointer, size):
            self.assertEqual(m.r[4:7], [pointer, size, track])
            events.append(('prepare', which)); return int(valid)
        def release(m):
            cancel(m, 'release')
            events.append(('release', m.r[4])); return 0
        def image(m):
            self.assertEqual(m.r[4:8], [CONNECTION, 77, 0x630000, 0x630004])
            m.write(m.r[6], 1234); m.write(m.r[7], 0x720000)
            cancel(m, 'image')
            events.append(('image',)); return stock_return
        callbacks = {
            self.symbols['_xdj_beta_trace_reset']: reset, self.symbols['_xdj_beta_trace']: trace,
            self.symbols['_xdj_beta_invalidate']: invalidate, 0x09445274: colour,
            0x0929626c: wave_rgb, 0x09293d76: wave_blue, 0x09382a9a: release,
            self.symbols['_xdj_beta_prepare_rgb']: lambda m: prepare(m, 'rgb', rgb_valid, 0x700000, 7228),
            self.symbols['_xdj_beta_prepare_blue']: lambda m: prepare(m, 'blue', blue_valid, 0x710000, 900),
            0x09293bb0: image, 0x09548738: lookup}
        machine = Machine(self.code, self.base, self.symbols['xdj_beta_getimage_hook'], callbacks)
        machine.r[4:8] = [CONNECTION, 77, 0x630000, 0x630004]
        machine.r[13] = CONTEXT if kind is not None else 0
        if kind is not None:
            machine.write(CONTEXT, kind)
            machine.write(CONTEXT+12, 0x100 if cancel_enabled else 0)
            machine.write(CONTEXT+180, 0x670000)
            cancel(machine, 'before')
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
        cancelled_early = cancel_phase in ('before', 'rgb', 'blue', 'release')
        self.assertEqual(machine.r[0], 0 if cancelled_early else stock_return & MASK)
        self.assertEqual(machine.read(0x630000), 0 if cancelled_early else 1234)
        self.assertEqual(machine.read(0x630004), 0 if cancelled_early else 0x720000)
        self.assertEqual(events.count(('image',)), 0 if cancelled_early else 1)
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

    def test_rgb_failure_or_malformed_data_never_chain_blue(self):
        for args in ({'rgb_result':0}, {'rgb_result':-1}, {'rgb_valid':False}):
            with self.subTest(args=args):
                events, _ = self.request(**args)
                self.assertNotIn(('blue', 3902), events)
                self.assertNotIn(('release',0x710000), events)
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

    def test_already_cancelled_never_queries_or_clears_stock_cancel(self):
        events, m = self.request(cancel_phase='before')
        self.assertFalse(any(e[0] in ('lookup','colour','rgb','blue','image') for e in events))
        self.assertEqual(m.read(CONTEXT+12,1), 1)

    def test_pending_token_skips_preview_but_leaves_cancellation_to_stock(self):
        events, m = self.request(pending_cancel=True)
        self.assertIn(('lookup',), events)
        self.assertFalse(any(e[0] in ('colour','rgb','blue') for e in events))
        self.assertEqual(m.read(CONTEXT+12,1), 0)
        self.assertIn(('image',), events)

    def test_disabled_cancellation_registry_does_not_lookup(self):
        events, _ = self.request(cancel_enabled=False)
        self.assertNotIn(('lookup',), events)
        self.assertIn(('rgb',3902), events)

    def test_cancellation_during_rgb_releases_without_preparing_or_restarting(self):
        for result in (1, 0, -1, -200):
            events, m = self.request(cancel_phase='rgb', rgb_result=result)
            self.assertFalse(any(e[0] in ('blue','image','prepare') for e in events))
            self.assertEqual(events.count(('release',0x700000)), int(bool(result)))
            self.assertEqual(m.read(CONTEXT+12,1), 1)

    def test_cancellation_during_blue_releases_without_restarting(self):
        for result in (1, 0, -1):
            events, m = self.request(rgb=False, cancel_phase='blue', blue_result=result)
            self.assertFalse(any(e[0] in ('image','prepare') for e in events))
            self.assertEqual(events.count(('release',0x710000)), int(bool(result)))
            self.assertEqual(m.read(CONTEXT+12,1), 1)

    def test_cancellation_during_release_prevents_next_transaction(self):
        for rgb in (True, False):
            events, _ = self.request(rgb=rgb, cancel_phase='release')
            self.assertIn(('invalidate',), events)
            self.assertFalse(any(e[0]=='image' for e in events))

    def test_cancellation_inside_stock_getimage_invalidates_prepared_pixels(self):
        events, m = self.request(cancel_phase='image')
        self.assertIn(('invalidate',), events)
        self.assertEqual(m.read(CONTEXT+12,1), 1)

    def test_repeated_cancel_and_normal_requests_each_return_with_balanced_stack(self):
        for i in range(200):
            cancelled = i % 2 == 0
            events, _ = self.request(cancel_phase='rgb' if cancelled else None)
            self.assertEqual(sum(e[0] in ('rgb','blue') for e in events), 1)
            self.assertEqual(events.count(('image',)), int(not cancelled))


if __name__ == '__main__': unittest.main()

