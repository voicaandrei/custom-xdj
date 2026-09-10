#!/usr/bin/env python3
"""Offline compressor validation against the existing independent decoder."""
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from unpack_main import lzss
ROOT=Path(__file__).resolve().parents[1]
SHA='9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'

def encoder(folder):
    lib=Path(folder)/'lzss-encoder.dylib'
    subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
        str(ROOT/'scripts/lzss_encode.c'),'-o',str(lib)],check=True,capture_output=True)
    handle=ctypes.CDLL(str(lib));fn=handle.xdj_lzss_encode
    fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t]
    fn.restype=ctypes.c_size_t
    def compress(data):
        source=ctypes.create_string_buffer(data)
        output=ctypes.create_string_buffer(len(data)+len(data)//8+1)
        count=fn(source,len(data),output,len(output))
        if data and not count: raise ValueError('Compression failed')
        return output.raw[:count]
    return compress

if __name__=='__main__':
    data=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    if hashlib.sha256(data).hexdigest()!=SHA: raise ValueError('Wrong reference image')
    with tempfile.TemporaryDirectory() as tmp:
        packed=encoder(tmp)(data)
    decoded=lzss(packed,limit=len(data))
    if decoded!=data: raise ValueError('Encoder round-trip failed')
    target=ROOT/('private/recompressed-reference-v144-'+hashlib.sha256(packed).hexdigest()[:12]+'.lzss')
    with target.open('xb') as f:f.write(packed)
    original=(ROOT/'private/extracted/v144/main.bin').read_bytes()
    old_length=int.from_bytes(original[0x40000:0x40004],'little')
    report={'input_sha256':SHA,'input_bytes':len(data),'packed_bytes':len(packed),
      'packed_sha256':hashlib.sha256(packed).hexdigest(),'original_packed_bytes':old_length,
      'fits_original_packed_length':len(packed)<=old_length,'roundtrip_byte_identical':True,
      'compression_byte_identical':packed==original[0x40004:0x40004+old_length],
      'device_execution':False,'installable_update':False}
    (ROOT/'evidence/lzss-encoder-v144.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
