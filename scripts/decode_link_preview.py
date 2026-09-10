#!/usr/bin/env python3
"""Convert the verified dbserver preview framing to native parser inputs.
No socket use. Blue returns 400 packed PWAV bytes; RGB returns 1200x6 PWV4 bytes.
"""
import hashlib
import json
from pathlib import Path


def blue_to_pwav(data):
    if len(data)!=900:raise ValueError('Expected 900-byte stock blue preview')
    pairs=data[:800]
    if any(v>31 for v in pairs[::2]) or any(v>7 for v in pairs[1::2]):
        raise ValueError('Invalid height/shade pair')
    return bytes(pairs[i] | pairs[i+1]<<5 for i in range(0,800,2))


def rgb_to_pwv4(data):
    if len(data)!=7228 or data[4:8]!=b'PWV4':raise ValueError('Expected framed PWV4 preview')
    prefix=int.from_bytes(data[:4],'little')
    header,total,size,count=[int.from_bytes(data[i:i+4],'big') for i in (8,12,16,20)]
    if (prefix,header,total,size,count)!=(7224,24,7224,6,1200):
        raise ValueError('Unexpected PWV4 framing')
    return data[28:]


if __name__=='__main__':
    base=Path(__file__).resolve().parents[1]/'private/owner'
    result={}
    for name,fn in [('blue',blue_to_pwav),('rgb',rgb_to_pwv4)]:
        payload=fn((base/f'link-preview-{name}.bin').read_bytes())
        (base/f'link-preview-{name}-native.bin').write_bytes(payload)
        result[name]={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
    (base/'link-preview-native.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
