"""Run existing bounded wrapper cases against the actual Test 15 extension."""
import subprocess
import tempfile
from pathlib import Path
from tests import test_beta14_execution as previous
from build_beta15 import link_beta
from build_sh import toolchain

ROOT=Path(__file__).resolve().parents[1]

class Beta15Execution(previous.Beta14Execution):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            linked=link_beta(folder,(ROOT/'private/extracted/v144/main-040000-unpacked.bin').stat().st_size)
            out=subprocess.run([toolchain()['nm'],'-n',str(folder/'browser-waveform-beta06.elf')],
                check=True,capture_output=True,text=True).stdout
            cls.symbols={p[2]:int(p[0],16) for line in out.splitlines() if len(p:=line.split())==3}
            cls.base=linked['code_pointer']
            cls.code=linked['payload'][:cls.symbols['_render']-cls.base]
            cls.inline_copy=linked['inline_copy']

    def test_optimized_preparation_is_in_the_linked_extension(self):
        self.assertIn('_xdj_fast_prepare_pair',self.symbols)
        self.assertNotIn('_xdj_prepare_pwv4_scaled',self.symbols)

    def test_info_wrappers_forward_descriptor_without_corrupting_registers(self):
        from tests.test_beta11_execution import Machine
        from tests.test_beta08_execution import SP
        for suffix in ('create','fallback'):
            m=Machine(self.code,self.base,self.symbols['xdj_beta_info_'+suffix+'_hook'],{})
            m.r[4:8]=[11,22,33,44]; m.r[9]=0x13bca510
            pc=m.pc; m.ordinary(m.read(pc,2),pc)
            self.assertEqual(m.read(pc+2,2),0x412b)
            m.ordinary(m.read(pc+4,2),pc+4)
            self.assertEqual(m.r[1],self.symbols['_xdj_beta_info_'+suffix])
            self.assertEqual(m.r[15],SP)
            if suffix=='fallback': self.assertEqual(m.r[5],0x13bca510)
        events=[]
        def access(m):
            events.append((m.r[4:8],m.read(m.r[15])))
            return 1
        m=Machine(self.code,self.base,self.symbols['xdj_beta_info_access_hook'],{
            self.symbols['_xdj_beta_info_access']:access})
        m.r[4:8]=[11,22,33,44]; m.r[9]=0x13bca510; m.r[11]=0x650000
        saved=m.r[8:15].copy(); m.run()
        self.assertEqual(events,[([11,22,33,0x13bca510],0x650000)])
        self.assertEqual(m.r[15],SP); self.assertEqual(m.r[8:15],saved)
        self.assertEqual(m.r[0],1)

    def test_inline_info_copy_uses_one_bounded_copy_and_stock_continuation(self):
        from tests.test_beta11_execution import Machine, ReachedContinuation
        from tests.test_beta08_execution import SP
        events=[]
        def copy(m): events.append(m.r[4:7]); return m.r[4]
        m=Machine(self.inline_copy+bytes.fromhex('ffff'),0x152084a,0x152084c,{0x095a6570:copy})
        m.fpscr=0x12345678; m.r[8]=0xffe7ffff
        m.write(SP+52,0x630000); m.write(SP+32,0x640000)
        m.write(SP+44,544); m.write(0x640000+544,0x650000)
        with self.assertRaises(ReachedContinuation) as stop: m.run()
        self.assertEqual(stop.exception.args,(0x152087e,))
        self.assertEqual(events,[[0x630000,0x650000,16128]])
        self.assertEqual(m.r[15],SP)
        self.assertEqual(m.fpscr,0x12345678 & 0xffe7ffff)

    def request(self, kind=2, track=3902, artwork=77, stock_return=1,
                rgb=True, rgb_result=1, rgb_valid=True, blue_result=1,
                blue_valid=True, row_present=True, source_remote=1,
                source_player=4, source_slot=3, source_present=True,
                cancel_phase=None, pending_cancel=False, cancel_enabled=True):
        from tests.test_beta10_execution import Machine
        from tests.test_beta08_execution import MASK, SP, CONTEXT, ROW, CONNECTION
        events = []
        scope_events = []
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
            self.assertEqual(m.read(CONTEXT+13,1),0)
            self.assertEqual(m.r[4:6], [CONNECTION, track])
            self.assertEqual(m.r[6:8], [self.symbols['_xdj_beta_pwv4_tag'], self.symbols['_xdj_beta_ext_name']])
            for off, value in ((0, 7228), (4, 0x700000 if rgb_result else 0), (8, 123)):
                m.write(m.read(m.r[15]+off), value)
            cancel(m, 'rgb')
            events.append(('rgb', track)); return rgb_result
        def wave_blue(m):
            self.assertEqual(m.read(CONTEXT+13,1),0)
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
            if kind is not None: self.assertEqual(m.read(CONTEXT+13,1),int(cancel_enabled))
            self.assertEqual(m.r[4:8], [CONNECTION, 77, 0x630000, 0x630004])
            m.write(m.r[6], 1234); m.write(m.r[7], 0x720000)
            cancel(m, 'image')
            events.append(('image',)); return stock_return
        def enter(m):
            self.assertEqual(m.r[4], CONTEXT)
            saved=0x100|m.read(CONTEXT+13,1)
            m.mem[CONTEXT+13]=0
            scope_events.append('enter')
            return saved
        def leave(m):
            if m.r[4] and m.r[5]&0x100:
                m.mem[m.r[4]+13]=m.r[5]&255
                scope_events.append('leave')
            return 0
        callbacks = {
            self.symbols['_xdj_beta_preview_enter']:enter,
            self.symbols['_xdj_beta_preview_leave']:leave,
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
        if kind is not None: self.assertEqual(machine.read(CONTEXT+13,1),int(cancel_enabled))
        self.assertIn(scope_events, ([], ['enter','leave']))
        return events, machine


    def test_ui_trampolines_replay_pushes_and_resume_at_exact_stock_boundary(self):
        from tests.test_beta11_execution import Machine
        from tests.test_beta08_execution import SP
        for name,registers,resume in [('title',range(8,14),0x0952c250),('note',range(9,15),0x0952c028)]:
            m=Machine(self.code,self.base,self.symbols['_xdj_beta_'+name+'_original'],{})
            before=m.r.copy()
            for _ in range(7):
                m.ordinary(m.read(m.pc,2),m.pc);m.pc+=2
            self.assertEqual(m.read(m.pc,2),0x412b)
            self.assertEqual(m.r[1],resume)
            self.assertEqual(m.r[15],SP-24)
            self.assertEqual([m.read(SP-4*(i+1)) for i in range(6)],[before[r] for r in registers])
            self.assertEqual(m.r[4:8],before[4:8])

    def test_serializer_uses_row_match_and_preserves_original_arguments(self):
        from tests.test_beta11_execution import Machine
        from tests.test_beta08_execution import SP,RETURN
        for flag in (0,1,255):
            m=Machine(self.code,self.base,self.symbols['xdj_beta_serialize_note'],{})
            m.r[4:8]=[0x600000,0x404,0x620000,127];m.r[14]=0x610000
            m.mem[0x610011]=flag;m.write(SP,999)
            before=m.r.copy();called=0
            for _ in range(40):
                pc=m.pc;w=m.read(pc,2)
                if w==0x412b:
                    self.assertEqual(m.r[1],0x092bd968)
                    break
                if w==0x410b:
                    self.assertEqual(m.r[1],self.symbols['_xdj_beta_key_note'])
                    self.assertEqual(m.r[4:6],[0x404,flag if flag<128 else 0xffffffff])
                    m.pr=pc+4;m.ordinary(m.read(pc+2,2),pc+2)
                    for i in range(8):m.r[i]=0xdead0000+i
                    m.r[0]=0x45b if flag==1 else 0x404
                    m.pc=pc+4;called+=1
                else:
                    m.ordinary(w,pc);m.pc+=2
            else:self.fail('No serializer continuation')
            self.assertEqual(called,1)
            self.assertEqual(m.r[4:8],[before[4],0x45b if flag==1 else 0x404,*before[6:8]])
            self.assertEqual(m.r[8:16],before[8:16]);self.assertEqual(m.pr,RETURN)
            self.assertEqual(m.read(SP),999)
