"""Read-only, hash-locked stock evidence for key-compatible note icons."""
import hashlib
import json
import struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHA='9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'
PAIRS={4:91,47:96,101:102,104:105,107:108,110:111}

def inspect():
    b=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    assert hashlib.sha256(b).hexdigest()==SHA
    u32=lambda off:struct.unpack_from('<I',b,off)[0]
    assert (u32(0x9d4),u32(0x9d0),u32(0x9d8))==(0x095c0bdc,0x0960f17c,0x13b96e0c)
    ram=lambda addr:addr-0x13b96e0c+0x15c0bdc
    assert u32(ram(0x13bc6d6c))==0x08120000
    icons=[]
    for normal,green in PAIRS.items():
        normal_ids=struct.unpack_from('<hhh',b,ram(0x13bc877c)+6*normal)
        green_ids=struct.unpack_from('<hhh',b,ram(0x13bc877c)+6*green)
        resources=[]
        for n,ids in enumerate((normal_ids,green_ids)):
            for selected,resource in enumerate(ids[:2]):
                descriptor=0x120000+44*resource
                assert struct.unpack_from('<HH',b,descriptor+4)==(24,24)
                assert b[descriptor+24]==2
                offset=0x120000+u32(descriptor+32)
                pixels=struct.unpack_from('<576H',b,offset)
                if n==1: assert set(pixels)=={0xf81f,0x0400 if selected else 0x3ae8}
                resources.append({'resource':resource,'file_offset':hex(offset),
                    'sha256':hashlib.sha256(b[offset:offset+1152]).hexdigest(),
                    'colours_rgb565':list(map(hex,sorted(set(pixels))))})
        # All variants preserve the exact magenta transparency silhouette.
        masks=[]
        for r in resources:
            pixels=struct.unpack_from('<576H',b,int(r['file_offset'],16))
            masks.append(tuple(p==0xf81f for p in pixels))
        assert all(mask==masks[0] for mask in masks)
        icons.append({'normal_type':normal,'matching_type':green,'resources':resources})
    words={
        0x1292112:'28e6',  # stock clears 40-byte record
        0x129221e:'40e0',  # twelfth response field at +64
        0x1292236:'0c88',  # matching selector 12
        0x1292244:'5352',0x129224a:'5452',0x1292250:'5552',0x1292256:'5652',
        0x129225c:'01e0',0x1292264:'26e0',0x1292268:'240a',
        0x12be160:'0ce1', # default matching selector
    }
    for off,expected in words.items():
        assert b[off:off+2].hex()==expected,(hex(off),b[off:off+2].hex(),expected)
    calls=[]
    for off in range(0,len(b)-1,2):
        word=b[off]|b[off+1]<<8
        if word>>12!=11: continue
        disp=word&4095
        if disp&2048: disp-=4096
        if off+4+2*disp==0x12b92a6: calls.append(off)
    assert calls==[0x12b8ba0,0x12b8cf6,0x12b8e6e,0x12b95d8]
    return {'reference_application_sha256':SHA,'address_space':'FILE in decompressed MAIN; CODE=0x08000000+FILE; RAM separately labelled',
        'record_match_byte':38,'record_bytes':40,'row_match_byte':17,
        'record_reader':'0x12920e4','key_predicate':['0x129221e','0x1292268'],
        'info_key_predicate':['0x12c8216','0x12c826a'],
        'master_key_refresh':'0x12c884a','mapper':'0x12b92a6',
        'mapper_direct_calls':list(map(hex,calls)),'stock_default_matching_selector':12,
        'asserted_instruction_words':{hex(k):v for k,v in words.items()},
        'icons':icons,'hardware_note_feature_validated':False,
        'limits':['Older server replies without field 12 yield no match.',
                  'Master-change refresh timing and all browse-mode coverage require a hardware test.']}

if __name__=='__main__':
    report=inspect()
    (ROOT/'evidence/key-note-v144.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
