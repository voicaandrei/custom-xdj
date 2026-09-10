#!/usr/bin/env python3
"""Build the candidate hook, without changing a byte of firmware."""
import hashlib
import json
from pathlib import Path
import subprocess
from build_sh import FLAGS,toolchain
ROOT=Path(__file__).resolve().parents[1]
SHA='9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'


def build(folder):
    data=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    if hashlib.sha256(data).hexdigest()!=SHA:raise ValueError('Wrong reference firmware')
    literal=0x152d21c
    if int.from_bytes(data[literal:literal+4],'little')!=0x0935a2ec:raise ValueError('Wrong release pointer')
    users=[]
    for pc in range(literal-1024,literal,2):
        w=int.from_bytes(data[pc:pc+2],'little')
        if w&0xf000==0xd000 and ((pc+4)&~3)+(w&255)*4==literal:users.append(pc)
    if users!=[0x152d1d0,0x152d1da]:raise ValueError('Unexpected literal users')
    tools=toolchain()
    if tools is None:raise FileNotFoundError('SH toolchain absent')
    def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout
    sources=[ROOT/'native/v144/draw_probe_hook.S']
    objects=[]
    for source in sources:
        obj=folder/(source.stem+'.o');objects.append(obj)
        run([tools['gcc'],*FLAGS,'-fstack-usage','-I',str(ROOT/'native'),'-c',str(source),'-o',str(obj)])
    combined=folder/'probe-with-hook.o'
    run([tools['gcc'],'-m4a-nofpu','-ml','-nostdlib','-Wl,-r',*[str(o) for o in objects],'-o',str(combined)])
    undefined=run([tools['nm'],'-u',str(combined)]).splitlines()
    if undefined:raise ValueError('Unresolved hook symbols: '+repr(undefined))
    sizes=run([tools['size'],str(combined)]).splitlines()[1].split()
    if int(sizes[1]) or int(sizes[2]):raise ValueError('Unexpected writable static state')
    return {'reference_sha256':SHA,'address_space':'file offsets in decompressed MAIN unless labeled pointer',
        'candidate_literal_file_offset':literal,'original_code_pointer':0x0935a2ec,
        'literal_users_file_offsets':users,'target_descriptor_data_pointer':0x13bca44c,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        'combined_object_sha256':hashlib.sha256(combined.read_bytes()).hexdigest(),
        'combined_text_bytes':int(sizes[0]),'undefined_symbols':[],
        'additional_stack_bytes':0,'probe_pixel_word':0xf800,'probe_pixel_count':2240,
        'modified_firmware':False,'ready_for_player':False,
        'remaining':['RAM placement and relocation',
                     'runtime descriptor and surface allocation','final image and installation/recovery plan']}


if __name__=='__main__':
    folder=ROOT/'private/probe-hook-v144';folder.mkdir(exist_ok=True)
    report=build(folder)
    (ROOT/'evidence/probe-hook-v144.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
