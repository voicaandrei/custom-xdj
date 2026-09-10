import hashlib
import struct
import unittest
from pathlib import Path
from scripts.index_key_note import inspect, SHA
ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/'private/extracted/v144/main-040000-unpacked.bin'

@unittest.skipUnless(REFERENCE.exists(),'Stock reference absent')
class Beta11Static(unittest.TestCase):
    def test_stock_key_flag_and_green_icon_silhouettes(self):
        evidence=inspect()
        self.assertEqual(evidence['stock_default_matching_selector'],12)
        self.assertEqual(len(evidence['icons']),6)

    def test_patched_info_literals_have_only_the_reviewed_callers(self):
        b=REFERENCE.read_bytes()
        self.assertEqual(hashlib.sha256(b).hexdigest(),SHA)
        wanted={0x152cebc:[],0x152d204:[],0x152d214:[],0x152d218:[]}
        for a in range(0,len(b)-2,2):
            if b[a+1]&240!=208: continue
            pool=((a+4)&~3)+4*b[a]
            if pool in wanted: wanted[pool].append(a)
        self.assertEqual(wanted,{
            0x152cebc:[0x152cc30,0x152cd8c],
            0x152d204:[0x152cfec],
            0x152d214:[0x152d0e8],
            0x152d218:[0x152d140]})

    def test_key_mapper_entry_has_no_direct_branch_into_overwritten_pushes(self):
        b=REFERENCE.read_bytes()
        hits=[]
        for a in range(0x12b8000,0x12ba000,2):
            word=struct.unpack_from('<H',b,a)[0]
            if word>>12 not in (10,11): continue
            disp=word&4095
            if disp&2048:disp-=4096
            target=a+4+2*disp
            if 0x12b92a6<target<0x12b92b2: hits.append(a)
        self.assertEqual(hits,[])
