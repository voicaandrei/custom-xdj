#!/usr/bin/env python3
"""Offline packaging experiment: recompress unchanged stock application.

Preserves original S-record topology, component labels and all bytes outside the
original compressed application block. Never installs, downloads or runs firmware.
"""
import binascii
import hashlib
import json
from pathlib import Path
from roundtrip_upd import SHA,ADDRESS_BYTES,encode_record
from extract_upd import extract,decode_srecords
from unpack_main import unpack,lzss
ROOT=Path(__file__).resolve().parents[1]
START=0x40000


def split_container(data):
    a,b,tail=data.split(b'\r\n',2)
    sizes=[int(a),int(b)]
    if any(n<34 for n in sizes) or sum(sizes)!=len(tail):raise ValueError('Bad lengths')
    return [tail[:sizes[0]],tail[sizes[0]:]]


def validate(candidate, original, expected_application):
    stock=extract(original)
    parts=split_container(candidate);original_parts=split_container(original)
    images=[]
    for i,part in enumerate(parts):
        if part[:32]!=original_parts[i][:32]:raise ValueError('Component identity changed')
        if int.from_bytes(part[-2:],'little')!=binascii.crc_hqx(part[:-2],0):raise ValueError('CRC mismatch')
        image,meta=decode_srecords(part[32:-2]);old_meta=stock[i][2]
        for field in ('base_address','end_address_exclusive','entry_record','ranges','record_types'):
            if meta[field]!=old_meta[field]:raise ValueError('Address topology changed')
        images.append(image)
    if parts[1]!=original_parts[1]:raise ValueError('PANEL changed')
    main=stock[0][1];old_size=int.from_bytes(main[START:START+4],'little')
    end=START+4+old_size+2
    if images[0][:START]!=main[:START] or images[0][end:]!=main[end:]:
        raise ValueError('Change outside application block')
    new_size=int.from_bytes(images[0][START:START+4],'little')
    if new_size>old_size:raise ValueError('Compressed block expanded')
    decoded,meta=unpack(images[0],START)
    if decoded!=expected_application:raise ValueError('Application mismatch after extraction')
    return meta


def repackage(original,packed):
    if hashlib.sha256(original).hexdigest()!=SHA:raise ValueError('Wrong stock reference')
    stock=extract(original);main=stock[0][1]
    expected,_=unpack(main,START)
    if lzss(packed,limit=len(expected))!=expected:
        raise ValueError('This tool accepts unchanged stock application only')
    return repackage_verified_application(original,packed,expected)


def repackage_verified_application(original,packed,expected):
    """Internal container writer; caller must validate its exact application patch."""
    if hashlib.sha256(original).hexdigest()!=SHA:raise ValueError('Wrong stock reference')
    stock=extract(original);main=stock[0][1]
    if lzss(packed,limit=len(expected))!=expected:raise ValueError('Packed/application mismatch')
    old_size=int.from_bytes(main[START:START+4],'little')
    if len(packed)>old_size:raise ValueError('Compressed block exceeds original span')
    block=len(packed).to_bytes(4,'little')+packed
    block+=(sum(block)&65535).to_bytes(2,'little')
    parts=split_container(original);encoded=[];covered=0
    for line in parts[0][32:-2].splitlines():
        kind=chr(line[1]);raw=bytes.fromhex(line[2:].decode());n=ADDRESS_BYTES[kind]
        address=int.from_bytes(raw[1:1+n],'big');payload=bytearray(raw[1+n:-1])
        if kind in '123':
            first=max(address,START);last=min(address+len(payload),START+len(block))
            if last>first:
                payload[first-address:last-address]=block[first-START:last-START];covered+=last-first
        encoded.append(encode_record(kind,address,bytes(payload)))
    if covered!=len(block):raise ValueError('Replacement spans sparse/unrepresented bytes')
    first=parts[0][:32]+b''.join(encoded)
    first+=binascii.crc_hqx(first,0).to_bytes(2,'little')
    result=str(len(first)).encode()+b'\r\n'+str(len(parts[1])).encode()+b'\r\n'+first+parts[1]
    validate(result,original,expected)
    return result


if __name__=='__main__':
    report=json.loads((ROOT/'evidence/lzss-encoder-v144.json').read_text())
    packed_path=ROOT/('private/recompressed-reference-v144-'+report['packed_sha256'][:12]+'.lzss')
    packed=packed_path.read_bytes()
    if hashlib.sha256(packed).hexdigest()!=report['packed_sha256']:raise ValueError('Packed input mismatch')
    original=(ROOT/'private/originals/v144/XDJ1KMK2.UPD').read_bytes()
    result=repackage(original,packed)
    target=ROOT/'private/stock-recompressed-validation-v144.UPD'
    with target.open('xb') as f:f.write(result)
    summary={'original_sha256':SHA,'candidate_sha256':hashlib.sha256(result).hexdigest(),
      'candidate_bytes':len(result),'application_unchanged':True,'panel_byte_identical':True,
      'outside_original_application_block_unchanged':True,'record_topology_preserved':True,
      'packed_headroom_bytes':report['original_packed_bytes']-len(packed),
      'contains_waveform_modification':False,'device_validation':False,'ready_to_install':False}
    (ROOT/'evidence/stock-recompressed-validation-v144.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
