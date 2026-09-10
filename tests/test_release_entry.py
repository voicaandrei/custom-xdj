"""Public release input validation without manufacturer or owner fixtures."""
import sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_release import read_official,save_exact
class ReleaseEntry(unittest.TestCase):
    def test_unknown_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'XDJ1KMK2.UPD';p.write_bytes(b'not firmware')
            with self.assertRaisesRegex(ValueError,'Unsupported firmware'):read_official(p)
    def test_zip_paths_are_not_extracted(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('../XDJ1KMK2.UPD',b'bad')
            with self.assertRaisesRegex(ValueError,'ZIP layout'):read_official(p)
            self.assertEqual(sorted(x.name for x in Path(d).iterdir()),['input.zip'])
    def test_existing_different_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'original';save_exact(p,b'original');save_exact(p,b'original')
            with self.assertRaisesRegex(ValueError,'Refusing'):save_exact(p,b'changed')
            self.assertEqual(p.read_bytes(),b'original')
