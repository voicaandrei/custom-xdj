"""Run existing bounded wrapper cases against the actual Test 12 extension."""
import subprocess
import tempfile
from pathlib import Path
from tests import test_beta11_execution as previous
from build_beta12 import link_beta
from build_sh import toolchain

ROOT=Path(__file__).resolve().parents[1]

class Beta12Execution(previous.Beta11Execution):
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
