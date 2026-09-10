import subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from build_sh import toolchain
from link_native_candidate import link
@unittest.skipUnless(toolchain() and (ROOT/'private/extracted/v144/main-040000-unpacked.bin').exists(),
                     'Private firmware/toolchain absent')
class NativeCandidateLink(unittest.TestCase):
    def test_all_own_functions_are_linked_in_candidate_not_a_proven_device_region(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);report=link(folder);tools=toolchain()
            self.assertFalse(report['modified_firmware'])
            self.assertFalse(report['placement_verified_on_player'])
            self.assertFalse(report['all_runtime_writers_excluded'])
            self.assertEqual(report['candidate_code_pointer']&15,0)
            self.assertEqual((folder/'native-candidate.bin').stat().st_size,report['linked_text_bytes'])
            symbols=subprocess.run([tools['nm'],'--defined-only',str(folder/'native-candidate.elf')],
                check=True,capture_output=True,text=True).stdout.splitlines()
            own=[line.split() for line in symbols if '_xdj_' in line]
            self.assertGreater(len(own),20)
            for address,kind,name in own:
                self.assertGreaterEqual(int(address,16),report['candidate_code_pointer'],name)
                self.assertLess(int(address,16),report['candidate_end_exclusive'],name)
            prefix=str(Path(tools['gcc']).parent/'sh-elf-')
            relocations=subprocess.run([prefix+'objdump','-r',str(folder/'native-candidate.elf')],
                check=True,capture_output=True,text=True).stdout
            self.assertNotIn('RELOCATION RECORDS',relocations)
