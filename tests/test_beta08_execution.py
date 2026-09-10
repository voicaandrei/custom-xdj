"""Bounded execution of project SH wrappers only; every stock/C callee is mocked.

Checks actual linked instructions, caller stack offsets, ABI and failure paths.
This is not device emulation, and never executes firmware instructions.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_beta08 import link_beta
from build_sh import toolchain

MASK = 0xffffffff
RETURN = 0x300000
SP = 0x500000
CONTEXT = 0x600000
ROW = 0x610000
CONNECTION = 0x620000


class Machine:
    def __init__(self, code, base, entry, callbacks):
        self.mem = {base+i: v for i, v in enumerate(code)}
        self.r = [0x10000+i for i in range(16)]
        self.r[15] = SP
        self.pc = entry
        self.pr = RETURN
        self.t = False
        self.callbacks = callbacks
        self.calls = []
        self.reads = []

    def read(self, address, size=4):
        self.reads.append((address, size))
        return int.from_bytes(bytes(self.mem[address+i] for i in range(size)), 'little')

    def write(self, address, value):
        for i, v in enumerate((value & MASK).to_bytes(4, 'little')):
            self.mem[address+i] = v

    def ordinary(self, w, pc):
        n = (w >> 8) & 15
        m = (w >> 4) & 15
        signed = (w & 255) - (256 if w & 128 else 0)
        r = self.r
        if w == 0x0009: pass
        elif w == 0x4f22:
            r[15] -= 4
            self.write(r[15], self.pr)
        elif w == 0x4f26:
            self.pr = self.read(r[15]); r[15] += 4
        elif w & 0xf000 == 0xe000: r[n] = signed & MASK
        elif w & 0xf000 == 0x7000: r[n] = (r[n] + signed) & MASK
        elif w & 0xf000 == 0xd000: r[n] = self.read(((pc+4) & ~3) + 4*(w & 255))
        elif w & 0xf000 == 0x5000: r[n] = self.read(r[m] + 4*(w & 15))
        elif w & 0xf000 == 0x1000: self.write(r[n] + 4*(w & 15), r[m])
        elif w & 0xf00f == 0x6003: r[n] = r[m]
        elif w & 0xf00f == 0x6002: r[n] = self.read(r[m])
        elif w & 0xf00f == 0x2002: self.write(r[n], r[m])
        elif w & 0xf00f == 0x2006:
            value = r[m]; r[n] -= 4; self.write(r[n], value)
        elif w & 0xf00f == 0x6006:
            address = r[m]; r[n] = self.read(address)
            if n != m: r[m] += 4
        elif w & 0xf00f == 0x000e: r[n] = self.read(r[0] + r[m])
        elif w & 0xf00f == 0x2008: self.t = (r[n] & r[m]) == 0
        elif w & 0xf00f == 0x3000: self.t = r[n] == r[m]
        elif w & 0xff00 == 0x8800: self.t = r[0] == (signed & MASK)
        elif w & 0xf0ff == 0x4011: self.t = r[n] < 0x80000000
        else: raise AssertionError(f'Unsupported project instruction {w:04x} at {pc:x}')

    def run(self):
        for _ in range(3000):
            pc = self.pc
            w = self.read(pc, 2)
            next_pc = pc + 2
            if w & 0xf000 == 0xa000:
                displacement = (w & 0xfff) - (4096 if w & 0x800 else 0)
                self.ordinary(self.read(pc+2, 2), pc+2)
                next_pc = pc+4+2*displacement
            elif w & 0xff00 in (0x8900, 0x8b00, 0x8d00, 0x8f00):
                taken = self.t == ((w & 0xff00) in (0x8900, 0x8d00))
                delayed = (w & 0xff00) in (0x8d00, 0x8f00)
                if delayed:
                    self.ordinary(self.read(pc+2, 2), pc+2)
                    next_pc = pc+4
                if taken: next_pc = pc+4+2*((w & 255)-(256 if w & 128 else 0))
            elif w & 0xf0ff == 0x400b:
                target = self.r[(w >> 8) & 15]
                self.pr = pc+4
                self.ordinary(self.read(pc+2, 2), pc+2)
                if target not in self.callbacks:
                    raise AssertionError(f'Unmocked callee {target:x}')
                self.calls.append(target)
                result = self.callbacks[target](self)
                for i in range(8): self.r[i] = 0xdead0000+i
                self.r[0] = result & MASK
                next_pc = self.pr
            elif w == 0x000b:
                target = self.pr
                self.ordinary(self.read(pc+2, 2), pc+2)
                if target == RETURN: return
                raise AssertionError('Unexpected return')
            else: self.ordinary(w, pc)
            self.pc = next_pc
        raise AssertionError('Project wrapper did not return within budget')


@unittest.skipUnless(toolchain() and (ROOT / 'private/extracted/v144/main-040000-unpacked.bin').exists(), 'toolchain/reference absent')
class Beta08Execution(unittest.TestCase):
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
                blue_valid=True, row_present=True):
        events = []
        def reset(m): events.append(('reset',)); return 0
        def trace(m): events.append(('stage', m.r[4])); return 0
        def invalidate(m): events.append(('invalidate',)); return 0
        def colour(m):
            self.assertEqual(m.r[4:6], [4, 3]); return 3 if rgb else 1
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
        machine.write(CONNECTION+4, 4); machine.write(CONNECTION+8, 3)
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


if __name__ == '__main__': unittest.main()
