import hashlib
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from decode_link_preview import blue_to_pwav,rgb_to_pwv4

class LinkPreviewDecodeTests(unittest.TestCase):
    def test_blue_height_shade_roundtrip(self):
        packed=bytes(i%256 for i in range(400))
        expanded=bytes(x for v in packed for x in (v&31,v>>5))+bytes(100)
        self.assertEqual(blue_to_pwav(expanded),packed)
        with self.assertRaises(ValueError):blue_to_pwav(expanded[:-1])
        with self.assertRaises(ValueError):blue_to_pwav(bytes([32])+expanded[1:])
        with self.assertRaises(ValueError):blue_to_pwav(expanded[:1]+bytes([8])+expanded[2:])

    def test_rgb_rejects_each_invalid_header(self):
        header=(7224).to_bytes(4,'little')+b'PWV4'+b''.join(v.to_bytes(4,'big') for v in [24,7224,6,1200,0])
        packet=header+bytes(7200)
        self.assertEqual(rgb_to_pwv4(packet),bytes(7200))
        for pos in [0,4,8,12,16,20]:
            bad=bytearray(packet);bad[pos]^=1
            with self.assertRaises(ValueError):rgb_to_pwv4(bad)
        with self.assertRaises(ValueError):rgb_to_pwv4(packet[:-1])

    @unittest.skipUnless((ROOT/'private/owner/link-fixtures/player4-3902/link-preview-rgb.bin').exists(),'Private player capture absent')
    def test_real_player_capture_frozen_hashes(self):
        base=ROOT/'private/owner/link-fixtures/player4-3902'
        blue=(base/'link-preview-blue.bin').read_bytes();rgb=(base/'link-preview-rgb.bin').read_bytes()
        self.assertEqual(hashlib.sha256(blue).hexdigest(),'e2a2f462406d88120999fea99176c3a6c008edb9f5cf10ba3c35428771e1cbb1')
        self.assertEqual(hashlib.sha256(rgb).hexdigest(),'129a48a5b963e4b3c6c702ac9543435dc36f2ffb7cd6afba558f212c802933dc')
        self.assertEqual(len(blue_to_pwav(blue)),400)
        self.assertEqual(len(rgb_to_pwv4(rgb)),7200)
