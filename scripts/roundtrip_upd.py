#!/usr/bin/env python3
"""Re-serialize the original 1.44 container only. No patching or device access."""
import binascii
import hashlib
import json
from pathlib import Path
from extract_upd import extract

ROOT=Path(__file__).resolve().parents[1]
SHA='b21d499d8964986216b6a235cff5849300d966d3801b522c17461a42a1ff1448'
ADDRESS_BYTES={'0':2,'1':2,'2':3,'3':4,'5':2,'6':3,'7':4,'8':3,'9':2}


def encode_record(kind,address,payload):
    n=ADDRESS_BYTES[kind]
    body=address.to_bytes(n,'big')+payload
    if len(body)>254: raise ValueError('Record too long')
    raw=bytes([len(body)+1])+body
    return b'S'+kind.encode()+ (raw+bytes([255-(sum(raw)&255)])).hex().upper().encode()+b'\r\n'


def rebuild(data):
    if hashlib.sha256(data).hexdigest()!=SHA:
        raise ValueError('Only pristine official 1.44 accepted')
    before=extract(data)  # independent checksum/range validation
    first,second,tail=data.split(b'\r\n',2)
    components=[];offset=0
    for length in (int(first),int(second)):
        component=tail[offset:offset+length];offset+=length
        records=[]
        for line in component[32:-2].splitlines():
            kind=chr(line[1]);raw=bytes.fromhex(line[2:].decode());n=ADDRESS_BYTES[kind]
            records.append(encode_record(kind,int.from_bytes(raw[1:1+n],'big'),raw[1+n:-1]))
        encoded=component[:32]+b''.join(records)
        encoded+=binascii.crc_hqx(encoded,0).to_bytes(2,'little')
        components.append(encoded)
    result=b''.join(str(len(c)).encode()+b'\r\n' for c in components)+b''.join(components)
    if result!=data: raise ValueError('Round-trip not byte-identical; no artifact accepted')
    after=extract(result)
    if [(n,i) for n,i,_ in before]!=[(n,i) for n,i,_ in after]:
        raise ValueError('Reconstructed component mismatch')
    return result


if __name__=='__main__':
    source=ROOT/'private/originals/v144/XDJ1KMK2.UPD'
    result=rebuild(source.read_bytes())
    target=ROOT/'private/container-roundtrip-v144.UPD'
    with target.open('xb') as f:f.write(result)
    report={'original_sha256':SHA,'roundtrip_sha256':hashlib.sha256(result).hexdigest(),
            'bytes':len(result),'byte_identical':True,'modified_firmware':False,
            'device_test':False,'purpose':'Serialization validation only; not a waveform update.'}
    (ROOT/'evidence/container-roundtrip-v144.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
