"""Execute only project SH wrappers, with all stock calls mocked."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from tests import test_beta10_execution as previous
from tests.test_beta10_execution import Machine as PreviousMachine
from tests.test_beta08_execution import SP
from build_beta11 import link_beta
from build_sh import toolchain

ROOT=Path(__file__).resolve().parents[1]
class ReachedContinuation(Exception): pass

class Machine(PreviousMachine):
    def ordinary(self,w,pc):
        if w==0xffff: raise ReachedContinuation(pc)
        elif w & 0xf00f == 0x000c:  # mov.b @(r0,rM),rN
            v=self.read(self.r[0]+self.r[(w>>4)&15],1)
            self.r[(w>>8)&15]=(v-256 if v&128 else v)&0xffffffff
        elif w & 0xf00f == 0x2009: self.r[(w>>8)&15] &= self.r[(w>>4)&15]
        elif w & 0xf00f == 0x300c:
            n=(w>>8)&15; self.r[n]=(self.r[n]+self.r[(w>>4)&15])&0xffffffff
        elif w & 0xf0ff == 0x4018:
            n=(w>>8)&15; self.r[n]=(self.r[n]<<8)&0xffffffff
        elif w==0x016a: self.r[1]=self.fpscr
        elif w==0x416a: self.fpscr=self.r[1]
        else: super().ordinary(w,pc)

class Beta11Execution(previous.Beta10Execution):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            linked=link_beta(folder,(ROOT/'private/extracted/v144/main-040000-unpacked.bin').stat().st_size)
            out=subprocess.run([toolchain()['nm'],'-n',str(folder/'browser-waveform-beta06.elf')],check=True,capture_output=True,text=True).stdout
            cls.symbols={p[2]:int(p[0],16) for line in out.splitlines() if len(p:=line.split())==3}
            cls.base=linked['code_pointer']
            cls.code=linked['payload'][:cls.symbols['_render']-cls.base]
            cls.inline_copy=linked['inline_copy']

    def test_info_wrappers_forward_descriptor_without_corrupting_registers(self):
        for suffix, forwarded in [('create',None),('access',7),('fallback',5)]:
            events=[]
            def call(m):
                events.append(m.r[:]); return 0x1234
            m=Machine(self.code,self.base,self.symbols['xdj_beta_info_'+suffix+'_hook'],{self.symbols['_xdj_beta_info_'+suffix]:call})
            m.r[4:8]=[11,22,33,44]
            m.r[9]=0x13bca510
            # Three-instruction tail adapter, followed by a mocked C function.
            pc=m.pc
            m.ordinary(m.read(pc,2),pc)
            self.assertEqual(m.read(pc+2,2),0x412b)  # jmp @r1
            target=m.r[1]
            m.ordinary(m.read(pc+4,2),pc+4)
            self.assertEqual(target,self.symbols['_xdj_beta_info_'+suffix])
            m.r[0]=call(m)
            self.assertEqual(m.r[0],0x1234)
            self.assertEqual(m.r[9],0x13bca510)
            self.assertEqual(m.r[15],SP)
            if forwarded: self.assertEqual(events[0][forwarded],0x13bca510)
            else: self.assertEqual(events[0][4:6],[11,22])

    def test_note_mapper_preserves_context_and_reads_only_stock_match_flag(self):
        for flag in (0,1,255):
            events=[]
            def stock(m):
                self.assertEqual(m.r[4:7],[0x600000,0x610000,0x620000])
                events.append('stock'); return 0x404
            def decorate(m):
                self.assertEqual(m.r[4:6],[0x404,flag if flag<128 else 0xffffffff])
                events.append('decorate'); return 0x45b if flag==1 else 0x404
            m=Machine(self.code,self.base,self.symbols['xdj_beta_key_note_hook'],{
                self.symbols['xdj_beta_key_note_original']:stock,
                self.symbols['_xdj_beta_key_note']:decorate})
            saved=m.r[8:15]
            m.r[4:7]=[0x600000,0x610000,0x620000]
            m.mem[0x620000+38]=flag
            m.run()
            self.assertEqual(m.r[15],SP)
            self.assertEqual(m.r[8:15],saved)
            self.assertEqual(events,['stock','decorate'])
            self.assertEqual(m.r[0],0x45b if flag==1 else 0x404)

    def test_note_trampoline_replays_exact_prologue_before_stock_resume(self):
        entry=self.symbols['xdj_beta_key_note_original']
        m=Machine(self.code,self.base,entry,{})
        saved=m.r[8:14]
        for off in range(0,14,2): m.ordinary(m.read(entry+off,2),entry+off)
        self.assertEqual(m.r[1],0x092b92b2)
        self.assertEqual(m.read(entry+14,2),0x412b)
        self.assertEqual(m.read(entry+16,2),0x0009)
        self.assertEqual(m.r[15],SP-24)
        self.assertEqual([m.read(SP-4*(i+1)) for i in range(6)],saved)

    def test_inline_info_copy_uses_one_bounded_copy_and_stock_continuation(self):
        events=[]
        def copy(m):
            events.append(m.r[4:7]); return m.r[4]
        # Append only a model stop sentinel at the continuation boundary.
        # No original firmware instruction is executed by this model.
        m=Machine(self.inline_copy+bytes.fromhex('ffff'),0x152084a,0x152084c,{0x095a6570:copy})
        m.fpscr=0x12345678; m.r[8]=0xffe7ffff
        m.write(SP+52,0x630000); m.write(SP+32,0x640000)
        m.write(SP+44,544); m.write(0x640000+544,0x650000)
        with self.assertRaises(ReachedContinuation) as stop: m.run()
        self.assertEqual(stop.exception.args,(0x152087e,))
        self.assertEqual(events,[[0x630000,0x650000,16240]])
        self.assertEqual(m.r[15],SP)
        self.assertEqual(m.fpscr,0x12345678 & 0xffe7ffff)
