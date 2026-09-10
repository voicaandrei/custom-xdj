import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import recovery_session as module


class RecoverySessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        private = root / 'private'
        private.mkdir()
        (root / 'docs').mkdir()
        (root / 'docs/recovery-procedure.md').write_text('fixture procedure')
        stock = private / 'original.UPD'
        stock.write_bytes(b'unit-test stock fixture, not actual firmware')
        self.patch = patch.multiple(module, ROOT=root, PRIVATE=private,
                                    STOCK=stock, STOCK_SHA=hashlib.sha256(stock.read_bytes()).hexdigest())
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.session = private / 'session'
        self.root = root

    def test_refuses_wrong_stock_without_creating_session(self):
        module.STOCK.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            module.initialize(self.session)
        self.assertFalse(self.session.exists())

    def test_confines_output_and_refuses_overwrite(self):
        with self.assertRaises(ValueError):
            module.initialize(self.root / 'outside')
        module.initialize(self.session)
        with self.assertRaises(FileExistsError):
            module.initialize(self.session)

    def test_photo_and_success_note_do_not_certify_recovery(self):
        module.initialize(self.session)
        photo = self.root / 'photo.jpg'
        photo.write_bytes(b'photo fixture')
        result = module.record(self.session, 'recovery_trial', photo, 'Succeeded')
        self.assertFalse(result['ready_for_player_patch'])
        self.assertEqual(result['observations'][0]['review'], 'not_reviewed')
        with self.assertRaises(FileExistsError):
            module.record(self.session, 'recovery_trial', photo, 'Overwrite')
        attachment = next((self.session / 'observations').glob('*.attachment'))
        attachment.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            module.inspect(self.session)

    def test_detects_stock_corruption_and_escaping_evidence(self):
        module.initialize(self.session)
        copied = self.session / 'stock-reference/XDJ1KMK2.UPD'
        copied.chmod(0o644)
        copied.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            module.inspect(self.session)
        copied.write_bytes(module.STOCK.read_bytes())
        module.save(self.session / 'observations/bad.json', {
            'kind': 'version_screen', 'file': '../../original.UPD',
            'sha256': module.STOCK_SHA})
        with self.assertRaises(ValueError):
            module.inspect(self.session)
