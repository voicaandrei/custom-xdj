"""Run existing bounded wrapper cases against the actual Test 16 extension."""
import subprocess
import tempfile
from pathlib import Path
from tests import test_beta15_execution as previous
from build_beta16 import link_beta
from build_sh import toolchain

ROOT=Path(__file__).resolve().parents[1]

class Beta16Execution(previous.Beta15Execution):
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

