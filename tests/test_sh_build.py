import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_sh import FLAGS, UNITS, build, toolchain


class ShToolchain(unittest.TestCase):
    def test_missing_toolchain_is_reported_not_guessed(self):
        if toolchain() is None:
            with tempfile.TemporaryDirectory() as temporary:
                with self.assertRaises(FileNotFoundError):
                    build(Path(temporary))

    def test_flags_avoid_the_fpu_and_any_hosted_assumption(self):
        self.assertIn('-m4a-nofpu', FLAGS)
        self.assertIn('-ml', FLAGS)
        self.assertIn('-ffreestanding', FLAGS)
        self.assertIn('-fno-builtin', FLAGS)
        self.assertIn('-Werror', FLAGS)


@unittest.skipUnless(toolchain() is not None, 'sh-elf cross toolchain absent')
class ShBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix='xdj-sh-build-test-') as temporary:
            cls.report = build(Path(temporary))

    def test_every_unit_compiles_for_the_target(self):
        self.assertEqual([unit['unit'] for unit in self.report['units']], list(UNITS))
        for unit in self.report['units']:
            self.assertIsNotNone(unit['text_bytes'], unit['unit'])
            self.assertGreater(unit['text_bytes'], 0, unit['unit'])

    def test_nothing_outside_this_project_is_needed(self):
        """SH-4A has no divide instruction, so a libgcc call would show up here."""
        self.assertEqual(self.report['symbols_outside_this_project'], [])
        self.assertFalse(self.report['needs_compiler_runtime'])
        self.assertEqual(self.report['combined_undefined_symbols'], [])

    def test_no_writable_static_state(self):
        """The core keeps no globals; the caller owns every buffer."""
        for unit in self.report['units']:
            self.assertEqual(unit['data_bytes'], 0, unit['unit'])
            self.assertEqual(unit['bss_bytes'], 0, unit['unit'])
