#!/usr/bin/env python3
"""Bounded read-only LZSS candidate verification for this exact MK2 image."""
import argparse
import hashlib
import json
from pathlib import Path

MAIN_SHA = '27109e16082ab444f726547f3188577dafd4f55c7de23ea9ee658532dd9373da'

MAIN_TARGETS={MAIN_SHA:'1.45','4d7d55fe7c905c511aaef54fdeddc7f7f5ec2c935a8c9f59404d3dff4dac1f21':'1.44'}

def lzss(source, limit=64*1024*1024):
    # Standard Okumura-style 4096-byte ring, 18-byte lookahead, LSB flags.
    ring=bytearray(b' '*(4096-18)+b'\0'*18); cursor=4096-18; out=bytearray(); p=0
    while p<len(source):
        flags=source[p];p+=1
        if p==len(source):raise ValueError('Flags without token')
        for bit in range(8):
            if p==len(source):break
            if flags & (1<<bit):
                values=[source[p]];p+=1
                out.extend(values);ring[cursor]=values[0];cursor=(cursor+1)%4096
            else:
                if p+2>len(source):raise ValueError('Truncated back-reference')
                low,high=source[p:p+2];p+=2; pos=low|((high&240)<<4);length=(high&15)+3
                for k in range(length):
                    value=ring[(pos+k)%4096];out.append(value);ring[cursor]=value;cursor=(cursor+1)%4096
            if len(out)>limit:raise ValueError('Decompression exceeds bound')
    return bytes(out)

def unpack(image, offset):
    if offset<0 or offset+6>len(image):raise ValueError('Offset out of bounds')
    size=int.from_bytes(image[offset:offset+4],'little'); end=offset+4+size
    if not size or end+2>len(image):raise ValueError('Packed region out of bounds')
    stored=int.from_bytes(image[end:end+2],'little');actual=sum(image[offset:end])&65535
    if stored!=actual:raise ValueError('Packed checksum mismatch')
    result=lzss(image[offset+4:end])
    return result,{'image_offset':offset,'packed_bytes':size,'checksum_stored':stored,'checksum_computed':actual,'unpacked_bytes':len(result),'sha256':hashlib.sha256(result).hexdigest(),'runtime_load_address':'unknown; do not treat file offsets as runtime addresses'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('main',type=Path);a=p.parse_args();data=a.main.read_bytes()
    if hashlib.sha256(data).hexdigest() not in MAIN_TARGETS:p.error('Unexpected MAIN SHA-256')
    root=Path(__file__).resolve().parents[1]/'private'
    if root not in a.main.resolve().parents:p.error('Keep images in private/')
    report={'main_sha256':hashlib.sha256(data).hexdigest(),'firmware_version':MAIN_TARGETS[hashlib.sha256(data).hexdigest()],'algorithm':'candidate Okumura LZSS; supported by exact packed checksums and coherent decoded data','regions':[]}
    # These two headers were observed in this MK2 image; checksums verified here.
    for offset in (0x10000,0x40000):
        out,meta=unpack(data,offset);(a.main.parent/f'main-{offset:06x}-unpacked.bin').write_bytes(out);report['regions'].append(meta)
    (a.main.parent/'unpack.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
