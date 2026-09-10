#!/usr/bin/env python3
"""Static artwork and console candidates; never executes firmware or commands."""
import hashlib,json
from pathlib import Path
import index_firmware as scanner
ROOT=Path(__file__).resolve().parents[1]
SHA='9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'
b=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
if hashlib.sha256(b).hexdigest()!=SHA:raise ValueError('Wrong target')
scanner.TERMS=[b'CreateArtworkID_List():Parameter Error',b'CreateArtworkID_Info():Remote Info NULL',b'UI: $$$ Artwork Dump ON $$$',b'console: not initialized.',b'115200 B8 PN S1 FN',b'shcon',b'dump memory    (usage:',b'@Ui_Browse> BROWSE_CMD UPDATE_LIST',b'dbcl_GetWaveData(): rmif=NULL']
r=scanner.index(b)
r['limitations']='Static candidates only. Console inclusion does not prove reachability or initialization. Artwork ID routines do not establish drawing. No network or device commands sent.'
(ROOT/'evidence/player-integration-v144.json').write_text(json.dumps(r,indent=2)+'\n')
for a in r['anchors']:
 print(hex(a['file_offset']),a['term'],[hex(u['instruction_file_offset']) for ref in a['references'] for u in ref['candidate_movl_users']])
