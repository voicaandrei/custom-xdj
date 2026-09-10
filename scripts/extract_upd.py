#!/usr/bin/env python3
"""Read-only, hash-locked MK2 reference extractor. No updater or writer."""
import argparse
import binascii
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

TARGET_SHA256 = '6fd2a5002b297b86fb8a5931d3debf1b607ff6abaf9d49cd737d3a530002dbcd'
TARGETS = {TARGET_SHA256: '1.45', 'b21d499d8964986216b6a235cff5849300d966d3801b522c17461a42a1ff1448': '1.44'}
MAX_ADDRESS = 32 * 1024 * 1024

def sha(data): return hashlib.sha256(data).hexdigest()

def decode_srecords(data):
    records, types, entry, count_record = [], Counter(), None, None
    for i, line in enumerate(data.splitlines(), 1):
        if not re.fullmatch(rb'S[0-9][0-9A-Fa-f]+', line): raise ValueError(f'Invalid S-record line {i}')
        typ = chr(line[1]); sizes = {'0':2,'1':2,'2':3,'3':4,'5':2,'6':3,'7':4,'8':3,'9':2}
        if typ not in sizes: raise ValueError('Unsupported S-record type')
        raw = bytes.fromhex(line[2:].decode()); size = raw[0]; n = sizes[typ]
        if size != len(raw)-1 or size < n+1: raise ValueError('S-record count mismatch')
        if sum(raw) & 255 != 255: raise ValueError(f'S-record checksum mismatch on line {i}')
        address = int.from_bytes(raw[1:1+n], 'big'); payload = raw[1+n:-1]; types[typ] += 1
        if typ in '123':
            if not payload or address+len(payload)>MAX_ADDRESS: raise ValueError('Data address outside analysis limit')
            records.append((address,payload))
        elif typ in '789':
            if entry is not None or payload: raise ValueError('Invalid termination record')
            entry = address
            if i != len(data.splitlines()): raise ValueError('Data after termination')
        elif typ in '56':
            if count_record is not None or payload: raise ValueError('Invalid count record')
            count_record = address
    if not records or entry is None: raise ValueError('Missing data or entry record')
    if count_record is not None and count_record != len(records): raise ValueError('Incorrect record count')
    records.sort(); end=0; ranges=[]
    for address,payload in records:
        if address < end: raise ValueError('Overlapping S-record data')
        if ranges and address==end: ranges[-1][1]=address+len(payload)
        else: ranges.append([address,address+len(payload)])
        end=address+len(payload)
    base=records[0][0]; image=bytearray(b'\xff'*(end-base))
    for address,payload in records:image[address-base:address-base+len(payload)]=payload
    return bytes(image), {'base_address':base,'end_address_exclusive':end,'entry_record':entry,'data_bytes':sum(len(p) for _,p in records),'gap_fill':'ff (host reconstruction only; gaps not in update)','ranges':ranges,'record_types':dict(types),'record_checksums_valid':True}

def extract(data):
    if sha(data) not in TARGETS: raise ValueError('Unexpected firmware SHA-256; refusing target mismatch')
    a,b,rest=data.split(b'\r\n',2); lengths=[int(a),int(b)]; offset=len(data)-len(rest)
    if offset+sum(lengths)!=len(data):raise ValueError('Container length mismatch')
    result=[]
    for name,size,label in zip(('main','panel'),lengths,(f'XDJ-1000MK2 MAINVer{TARGETS[sha(data)]}'.encode(),b'XDJ-1000MK2 PANLVer1.00')):
        component=data[offset:offset+size]
        if not component[:32].startswith(label):raise ValueError('Component label mismatch')
        image,meta=decode_srecords(component[32:-2])
        crc=binascii.crc_hqx(component[:-2],0)
        if int.from_bytes(component[-2:],'little') != crc: raise ValueError('Component CRC-16/XMODEM mismatch')
        meta.update(name=name,container_offset=offset,container_bytes=size,component_sha256=sha(component),image_sha256=sha(image),image_bytes=len(image),trailer_hex=component[-2:].hex(),trailer_validation='CRC-16/XMODEM init=0 poly=0x1021 over component excluding trailer; stored little-endian',trailer_crc16=crc,label=component[:32].decode('ascii').rstrip())
        result.append((name,image,meta));offset+=size
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--output',type=Path,default=None);a=p.parse_args()
    data=a.input.read_bytes();result=extract(data)
    if a.output is None: a.output=Path('private/extracted')/('v'+TARGETS[sha(data)].replace('.',''))
    private=(Path(__file__).resolve().parents[1]/'private').resolve()
    if private not in a.output.resolve().parents: p.error('Extracted firmware must remain under project private/')
    a.output.mkdir(parents=True,exist_ok=True)
    report={'schema':1,'firmware_version':TARGETS[sha(data)],'update_sha256':sha(data),'update_bytes':len(data),'components':[]}
    for name,image,_ in result:
        existing=a.output/f'{name}.bin'
        if existing.exists() and existing.read_bytes()!=image: p.error('Refusing overwrite of a different extracted image; use a separate output directory')
    for name,image,meta in result:
        (a.output/f'{name}.bin').write_bytes(image); report['components'].append(meta)
    (a.output/'extraction.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))
if __name__=='__main__':main()
