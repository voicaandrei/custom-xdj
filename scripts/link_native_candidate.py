#!/usr/bin/env python3
"""Link own native code at an UNVERIFIED candidate address. Never patches UPD.

Checks disjointness against known startup/RTOS regions, not all runtime writers.
Firmware contributes only its hash and length; no firmware bytes in linked code.
"""
import hashlib,json,subprocess
from pathlib import Path
from build_sh import build,toolchain
from build_probe_hook import SHA
ROOT=Path(__file__).resolve().parents[1]

def link(folder):
    data=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    if hashlib.sha256(data).hexdigest()!=SHA:raise ValueError('Wrong application')
    u32=lambda offset:int.from_bytes(data[offset:offset+4],'little')
    config=0xd073c
    regions=[{'name':name,'start':u32(base),'bytes':u32(config+size)}
        for name,base,size in [('OS_SYSMEM',0xd07a4,64),('OS_MPLMEM',0xd07a8,68),
                               ('OS_STKMEM',0xd07ac,72)]]
    regions.extend([
        {'name':'startup_zeroed','start':u32(0xce2c8),'bytes':u32(0xce2cc)-u32(0xce2c8)},
        {'name':'startup_initialized_data','start':u32(0x9d8),'bytes':u32(0x9d0)-u32(0x9d4)}])
    address=(0x08000000+len(data)+15)&~15
    report=build(folder);tools=toolchain();prefix=str(Path(tools['gcc']).parent/'sh-elf-')
    script=folder/'candidate.ld'
    script.write_text('''ENTRY(_xdj_adapter_draw)
SECTIONS {
 . = '''+hex(address)+''';
 .text : { *(.text .text.*) *(.rodata .rodata.*) }
 .data : { *(.data .data.*) }
 .bss : { *(.bss .bss.*) *(COMMON) }
 /DISCARD/ : { *(.comment .note* .stack) }
 ASSERT(SIZEOF(.data) == 0, "Unexpected initialized state")
 ASSERT(SIZEOF(.bss) == 0, "Unexpected global state")
}
''')
    elf=folder/'native-candidate.elf';raw=folder/'native-candidate.bin'
    def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout
    run([prefix+'ld','-EL','-T',str(script),'-Map='+str(folder/'native-candidate.map'),
         '-o',str(elf),str(folder/'xdj-native-core.o')])
    if run([tools['nm'],'-u',str(elf)]).strip():raise ValueError('Unresolved symbols')
    sections=run([prefix+'objdump','-h',str(elf)])
    lines=sections.splitlines()
    for i,line in enumerate(lines[:-1]):
        fields=line.split()
        if fields and fields[0].isdigit() and 'ALLOC' in lines[i+1]:
            if fields[1] not in ('.text','.data','.bss'):raise ValueError('Unexpected allocated section')
    run([prefix+'objcopy','-j','.text','-O','binary',str(elf),str(raw)])
    size=raw.stat().st_size
    if not 0<size<65536:raise ValueError('Unexpected code size')
    end=address+size
    for region in regions:
        if address<region['start']+region['bytes'] and region['start']<end:
            raise ValueError('Overlaps known runtime region')
    if end>u32(0xce2c8):raise ValueError('Beyond startup gap')
    result={'reference_application_sha256':SHA,'address_space':'SH cached code pointers / RTOS data pointers',
        'application_image_end_code_pointer':0x08000000+len(data),
        'candidate_code_pointer':address,'candidate_end_exclusive':end,
        'linked_text_bytes':size,'linked_binary_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
        'known_regions':regions,'disjoint_from_known_regions':True,
        'placement_verified_on_player':False,'all_runtime_writers_excluded':False,
        'modified_firmware':False,'ready_for_player':False,
        'core_build':report}
    return result

if __name__=='__main__':
    folder=ROOT/'private/native-linked-candidate-v144';folder.mkdir(exist_ok=False)
    result=link(folder)
    (ROOT/'evidence/native-linked-candidate-v144.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='core_build'},indent=2))
