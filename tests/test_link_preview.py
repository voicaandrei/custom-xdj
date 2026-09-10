import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from read_link_preview import message,read_message,keepalive,status

class Stream:
    def __init__(self,data):self.data=data
    def settimeout(self,t):pass
    def recv(self,n):
        part=self.data[:min(n,2)];self.data=self.data[len(part):];return part

class LinkPreviewTests(unittest.TestCase):
    def test_request_allowlist(self):
        with self.assertRaises(ValueError):message(1,0x9999)
        with self.assertRaises(ValueError):message(1,0,[0]*13)
        data=message(0xfffffffe,0,[1])
        self.assertEqual(read_message(Stream(data)),(0xfffffffe,0,[1]))

    def test_response_fragmentation_and_payload(self):
        header=bytearray(message(1,0,[0x2004,0,3]))
        header[11:13]=(0x4402).to_bytes(2,'big');header[14]=4;header[23]=3
        data=bytes(header)+b'\x14\0\0\0\x03abc'
        self.assertEqual(read_message(Stream(data)),(1,0x4402,[0x2004,0,3,b'abc']))
        with self.assertRaises(EOFError):read_message(Stream(data[:-1]))

    def test_omitted_empty_blob(self):
        header=bytearray(message(1,0,[0x2004,0,0]));header[14]=4;header[23]=3
        self.assertEqual(read_message(Stream(header))[2][-1],b'')

    def test_status_and_keepalive_identity(self):
        packet=keepalive('169.254.1.2','00:01:02:03:04:05')
        self.assertEqual(len(packet),54);self.assertEqual(packet[36],1)
        self.assertEqual(packet[38:48],bytes.fromhex('000102030405a9fe0102'))
        d=bytearray(0x124);d[:11]=b'Qspt1WmJOL\x0a';d[0x21]=d[0x24]=4
        d[0x28:0x2b]=bytes([4,3,1]);d[0x2c:0x30]=(123).to_bytes(4,'big')
        self.assertEqual(status(d)['track_id'],123)
        d[0x24]=3;self.assertIsNone(status(d))
