#!/usr/bin/env python3
"""Index exact-image anchors and candidate SH PC-relative references, no execution."""
import argparse
import hashlib
import json
import re
from pathlib import Path

APP_SHA='46aaaed98179157c523cd2797ecd3223862387a8baec21c9d4dffba87a1237df'
APP_TARGETS={APP_SHA:'1.45','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0':'1.44'}
TERMS=[b'PWAV',b'PWV2',b'PWV4',b'PMAI',b'/ANLZ%04X.',b'NORTi(c)MiSPO',b'dbcl_GetWaveData(): rmif=NULL',b'Tot_CueWaveGetTASK',b'@Ui_Browse> BROWSE_CMD UPDATE_LIST',b'@Ui_Browse> BROWSE_CMD MODE_CHANGE',b'Ui_BrowseCommTask',b'UI_BROWSEDATA_SEM',b'show browse list info']
def locations(data,term):return [m.start() for m in re.finditer(re.escape(term),data)]
def index(data):
    if hashlib.sha256(data).hexdigest() not in APP_TARGETS:raise ValueError('Unexpected application SHA-256')
    report={'image_sha256':hashlib.sha256(data).hexdigest(),'firmware_version':APP_TARGETS[hashlib.sha256(data).hexdigest()],'address_space':'file offsets in unpacked main-040000; pointer aliases are static candidates','anchors':[]}
    for term in TERMS:
        for offset in locations(data,term):
            anchor={'term':term.decode(),'file_offset':offset,'references':[]}
            for base in (0x08000000,0xa8000000):
                pointer=base+offset
                for pool in locations(data,pointer.to_bytes(4,'little')):
                    if pool%4:continue
                    users=[]
                    for pc in range(max(0,pool-1024)&~1,pool,2):
                        ins=int.from_bytes(data[pc:pc+2],'little')
                        if ins&0xf000==0xd000 and ((pc+4)&~3)+(ins&255)*4==pool:
                            users.append({'instruction_file_offset':pc,'register':(ins>>8)&15})
                    anchor['references'].append({'pointer_value':pointer,'literal_file_offset':pool,'candidate_movl_users':users})
            report['anchors'].append(anchor)
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('image',type=Path);a=p.parse_args();r=index(a.image.read_bytes());out=a.image.parent/'anchors.json';out.write_text(json.dumps(r,indent=2)+'\n')
    print(out)
    for x in r['anchors']:
        users=[u['instruction_file_offset'] for ref in x['references'] for u in ref['candidate_movl_users']]
        print(f"{x['file_offset']:08x} {x['term']}: "+', '.join(f'{u:08x}' for u in users))
