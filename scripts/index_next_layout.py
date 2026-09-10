#!/usr/bin/env python3
"""Read-only stock anchors and arithmetic for a packed INFO + wide row.
No patch or claim that the stock pointer propagation already uses this layout.
"""
import hashlib
import json
from pathlib import Path
from index_jpeg_manager import analyze as jpeg_index

ROOT=Path(__file__).resolve().parents[1]
SHA='9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'
ANCHORS={
    0x1412724:'12e81848a878',
    0x1412732:'736e8c3eea1f0f7e492ee62f',
    0x152083c:'6be6fd5418464ae5d276',
    0x15207a8:'12e218428072cc36cc35bc31d78f2c37',
    0x1520766:'52622822018901a07226d22651522822158915a01116',
    0x14126c6:'70de936570d0707570dca61f0b4cee04',
}

def analyze(data):
    if hashlib.sha256(data).hexdigest()!=SHA: raise ValueError('Stock SHA changed')
    for pc,expected in ANCHORS.items():
        if data[pc:pc+len(expected)//2].hex()!=expected:
            raise ValueError(f'Anchor changed at FILE {pc:#x}')
    cache=jpeg_index(data)['cache_static']
    base=cache['base']['pointer_value'];stride=cache['entry_stride_bytes'];entries=cache['entries']
    # Decoded MOV/SHLL8/ADD sequence at FILE 0x1412724 and 0x152083c.
    b_offset=(18<<8)-88
    destination_capacity=(107<<8)-46
    source_capacity=13104*2 # conservative documented B pixel area, not slot remainder
    info_bytes=290*28*2
    plans=[]
    for width in (80,120,160):
        used=info_bytes+width*28*2
        min_remaining=min(base+(i+1)*stride-
            (((base+i*stride+b_offset+15)&~15)+used) for i in range(entries))
        if min_remaining<0 or used>source_capacity or used>destination_capacity:
            raise ValueError('Packed surfaces exceed a bound')
        plans.append({'row_width':width,'row_height':28,'info_bytes':info_bytes,
            'row_offset_in_B_bytes':info_bytes,'combined_bytes':used,
            'source_B_unused_bytes':source_capacity-used,
            'destination_B_unused_bytes':destination_capacity-used,
            'minimum_end_margin_in_any_cache_entry_bytes':min_remaining,
            'cache_entries_checked':entries,
            'extra_cache_allocation_bytes_for_packing':0})
    return {'reference_application_sha256':SHA,
        'address_space':'FILE offsets in decompressed MAIN; CODE=FILE+0x08000000; cache base is RAM',
        'method':'static instruction anchors and arithmetic, no firmware execution',
        'anchor_bytes':{hex(pc):value for pc,value in ANCHORS.items()},
        'stock_cache_base_ram':base,'stock_cache_entry_bytes':stride,
        'source_B_bytes':source_capacity,'destination_B_bytes':destination_capacity,
        'plans':plans,
        'confirmed':'Pixel payloads fit the existing conservative B capacities and every cache entry.',
        'inferred':'A packed INFO + row scheme can avoid expanding all 512 cache allocations.',
        'unknown':['consumer A pointer rebinding across every response/copy/cache-hit path',
                   'fallback for missing B while A is present',
                   'note/title position and clipping in all browse modes',
                   'graphics allocation for wider visible surfaces',
                   'scheduler and lifetime correctness'],
        'important':'Current BETA 11 still copies only 16240 B bytes and points A at its old storage. Arithmetic is not an implemented wide player UI.'}

if __name__=='__main__':
    report=analyze((ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
    output=ROOT/'evidence/next-layout-v144.json'
    output.write_text(json.dumps(report,indent=2)+'\n');print(output)
