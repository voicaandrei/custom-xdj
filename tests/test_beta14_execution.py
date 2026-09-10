"""Run existing bounded wrapper cases against the actual Test 14 extension."""
import subprocess
import tempfile
from pathlib import Path
from tests import test_beta13_execution as previous
from build_beta14 import link_beta
from build_sh import toolchain

ROOT=Path(__file__).resolve().parents[1]

class Beta14Execution(previous.Beta13Execution):
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
