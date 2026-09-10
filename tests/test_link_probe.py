import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from probe_link_db import announcement, receive_exact, PORT_QUERY, GREETING


class FakeSocket:
    def __init__(self, pieces): self.pieces = iter(pieces)
    def settimeout(self, value): pass
    def recv(self, size): return next(self.pieces, b'')


class LinkProbeTests(unittest.TestCase):
    def test_packet_validation(self):
        packet = bytearray(54)
        packet[:11] = b'Qspt1WmJOL\x06'
        packet[12:23] = b'XDJ-1000MK2'
        packet[36] = 4
        self.assertEqual(announcement(packet), {'model': 'XDJ-1000MK2', 'player_number': 4})
        self.assertIsNone(announcement(packet[:-1]))
        packet[10] = 5
        self.assertIsNone(announcement(packet))

    def test_fragmented_response_and_disconnect(self):
        self.assertEqual(receive_exact(FakeSocket([b'\x04', b'\x1b']), 2), b'\x04\x1b')
        with self.assertRaises(EOFError): receive_exact(FakeSocket([b'\x04']), 2)

    def test_only_service_discovery_and_greeting_payloads(self):
        self.assertEqual(PORT_QUERY.hex(), '0000000f52656d6f7465444253657276657200')
        self.assertEqual(GREETING.hex(), '1100000001')
