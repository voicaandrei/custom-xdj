import random
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_lzss_encoder import encoder
from unpack_main import lzss

class LzssEncoder(unittest.TestCase):
    def test_overlaps_ring_wrap_and_incompressible_inputs_roundtrip(self):
        rng=random.Random(77144)
        samples=[b'',b'A',b'AB',b'A'*20000,b' '*5000,b'\0'*10000,
                 bytes(range(256))*80,bytes(rng.randrange(256) for _ in range(18000)),
                 b'abcd'*1024+b'xyz'+b'abcd'*1024]
        samples += [bytes(rng.randrange(8) for _ in range(n)) for n in (7,8,9,17,18,19,4095,4096,4097)]
        with tempfile.TemporaryDirectory() as tmp:
            compress=encoder(tmp)
            for data in samples:
                with self.subTest(length=len(data),prefix=data[:4]):
                    packed=compress(data)
                    self.assertEqual(lzss(packed,limit=len(data)),data)
                    self.assertLessEqual(len(packed),len(data)+(len(data)+7)//8)
                    self.assertEqual(compress(data),packed)
