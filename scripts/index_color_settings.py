#!/usr/bin/env python3
"""Read-only, hash-locked settings anchors and candidate SH literal users in 1.44."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IMAGE=ROOT/'private/extracted/v144/main-040000-unpacked.bin'
SHA='9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'
def scan(data):
    if hashlib.sha256(data).hexdigest()!=SHA:raise ValueError('Unexpected 1.44 application SHA')
    terms=['WAVEFORM COLOR','BLUE','RGB',' :/PIONEER/DEVSETTING.DAT',' :/.PIONEER/DEVSETTING.DAT']
    anchors=[]
    for term in terms:
        for match in re.finditer(re.escape((term+'\0').encode('utf-16le')),data):
            off=match.start()
            if off%2:continue
            refs=[]
            for base in (0x08000000,0xa8000000):
                for literal in re.finditer(re.escape((base+off).to_bytes(4,'little')),data):
                    pool=literal.start()
                    if pool%4:continue
                    users=[]
                    for pc in range(max(0,pool-1024)&~1,pool,2):
                        ins=int.from_bytes(data[pc:pc+2],'little')
                        if ins&0xf000==0xd000 and ((pc+4)&~3)+(ins&255)*4==pool:users.append(pc)
                    refs.append({'literal_file_offset':pool,'pointer_value':base+off,'candidate_movl_file_offsets':users})
            anchors.append({'term':term,'encoding':'UTF-16LE aligned','file_offset':off,'references':refs})
    return {'image_sha256':SHA,'firmware':'1.44','address_space':'file offsets in unpacked main-040000; pointer aliases inferred, not patch addresses','anchors':anchors,'limitations':'Aligned string matches and MOV.L pattern candidates do not establish function boundaries, ABI, setting field ownership or execution route.'}
if __name__=='__main__':
    r=scan(IMAGE.read_bytes());(ROOT/'evidence/color-settings-v144.json').write_text(json.dumps(r,indent=2)+'\n')
    for a in r['anchors']:
        users=[hex(u) for ref in a['references'] for u in ref['candidate_movl_file_offsets']]
        print(hex(a['file_offset']),a['term'],','.join(users))
