#!/usr/bin/env python3
"""Bounded static control-flow proof, not firmware execution."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHA='a85b616ee2c5958bebb7a59216fa8bc574e9f6f7606120468e89263700e2f8d4'
START, JOIN, END=0x2e1ac,0x2e26c,0x2e274


def prove_routine(code):
    if len(code)!=END-START: raise ValueError('Wrong routine size')
    def word(a):
        if a<START or a+2>END or a%2: raise ValueError('Target outside routine')
        return int.from_bytes(code[a-START:a-START+2],'little')
    def control(w):
        return w>>12 in (0xa,0xb) or w>>8 in (0x89,0x8b,0x8d,0x8f) or w in (0xb,0x2b) or w&0xf0ff in (0x400b,0x402b,0x0003,0x0023)
    if code[JOIN-START:]!=bytes.fromhex('03e0047f0b00164f'):
        raise ValueError('Return tail must set r0=3 then restore stack/MACL')
    visiting=set();done=set();branches=[]
    def walk(a):
        if a==JOIN: return
        if a>JOIN: raise ValueError('Path bypasses r0=3')
        if a in done:return
        if a in visiting:raise ValueError('Cycle: termination not proved')
        visiting.add(a);w=word(a)
        if w>>12==0xa:
            d=w&4095;d=d-4096 if d&2048 else d
            if control(word(a+2)):raise ValueError('Control in delay slot')
            successors=[a+4+d*2]
        elif w>>8 in (0x89,0x8b,0x8d,0x8f):
            d=w&255;d=d-256 if d&128 else d
            delayed=w>>8 in (0x8d,0x8f)
            if delayed and control(word(a+2)):raise ValueError('Control in delay slot')
            successors=[a+4+d*2,a+(4 if delayed else 2)]
        elif control(w):
            raise ValueError('Unexpected call/return/indirect control before join')
        else:successors=[a+2]
        if len(successors)>1 or w>>12==0xa:branches.append({'file_offset':a,'successors':successors})
        for target in successors:walk(target)
        visiting.remove(a);done.add(a)
    walk(START)
    return {'reachable_instruction_sites_before_join':len(done),'branches':sorted(branches,key=lambda x:x['file_offset']), 'every_structural_path_reaches_constant_return':True,'return_value':3}


def inspect(data):
    if hashlib.sha256(data).hexdigest()!=SHA:raise ValueError('Wrong updater SHA')
    report=prove_routine(data[START:END])
    report.update({'updater_sha256':SHA,'address_space':'FILE in decompressed updater','start':START,'join':JOIN,'end_exclusive':END,'hardware_execution_verified':False,'scope':'Normal control flow only; memory faults, interrupts and other update gates excluded'})
    return report

if __name__=='__main__':
    report=inspect((ROOT/'private/extracted/v144/main-010000-unpacked.bin').read_bytes())
    (ROOT/'evidence/update-classifier-v144.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
