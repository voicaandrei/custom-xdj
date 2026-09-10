import base64
import ctypes as c
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Column(c.Structure):
    _fields_ = [('back', c.c_uint8), ('front', c.c_uint8),
                ('color', c.c_uint16), ('front_color', c.c_uint16)]


class NativePrepareParity(unittest.TestCase):
    @unittest.skipUnless((ROOT / 'private/owner/andrei-sample/color-manifest.json').exists(),
                         'Private owner color fixtures absent')
    def test_c_matches_js_for_50_hash_verified_tracks_in_both_modes(self):
        # Local host equivalence only. Callback records RGB8 before any packing.
        cases = json.loads(subprocess.run(
            ['node', str(ROOT / 'tests/native-prepare-fixtures.mjs')],
            capture_output=True, text=True, check=True, timeout=30).stdout)
        self.assertEqual(len(cases), 100)
        compiler = shutil.which('cc')
        self.assertIsNotNone(compiler)
        with tempfile.TemporaryDirectory(prefix='xdj-prepare-parity-') as temporary:
            library = str(Path(temporary) / 'prepare.so')
            subprocess.run([compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-shared', '-fPIC', '-O1', str(ROOT / 'native/waveform_prepare.c'),
                            '-o', library], capture_output=True, check=True, timeout=30)
            native = c.CDLL(library)
            pack_type = c.CFUNCTYPE(c.c_uint16, c.c_uint8, c.c_uint8, c.c_uint8, c.c_void_p)
            observed = []

            @pack_type
            def pack(r, g, b, context):
                observed.append([r, g, b])
                return len(observed)  # Test tokens, not hardware colors.

            for case_index, case in enumerate(cases):
                with self.subTest(case=case_index, mode=case['mode']):
                    payload = base64.b64decode(case['payload'])
                    source = (c.c_uint8 * len(payload)).from_buffer_copy(payload)
                    output = (Column * 80)()
                    function = getattr(native, 'xdj_prepare_pwav' if case['mode'] == 'blue' else 'xdj_prepare_pwv4')
                    function.argtypes = [c.POINTER(c.c_uint8), c.c_size_t, c.POINTER(Column),
                                         c.c_size_t, pack_type, c.c_void_p]
                    function.restype = c.c_int
                    observed.clear()
                    self.assertEqual(function(source, len(payload), output, 80, pack, None), 1)
                    self.assertEqual(len(observed), 80 if case['mode'] == 'blue' else 160)
                    for actual, expected in zip(output, case['columns']):
                        self.assertEqual((actual.back, actual.front), (expected['back'], expected['front']))
                        self.assertEqual(observed[actual.color - 1], expected['color'])
                        if case['mode'] == 'rgb':
                            self.assertEqual(observed[actual.front_color - 1], expected['frontColor'])
