#!/usr/bin/env python3
"""Build Custom XDJ v1 locally from the owner's official MK2 1.44 update.
No download, USB staging, player access or firmware redistribution.
"""
import argparse,hashlib,json,sys,zipfile
from pathlib import Path
from extract_upd import extract
from unpack_main import unpack
from build_beta16 import build as build_base,FOLDER as BASE_FOLDER
from build_custom_v1 import build as build_final,FOLDER as FINAL_FOLDER,BASE_APP_SHA,BASE_UPD_SHA
ROOT=Path(__file__).resolve().parents[1]
STOCK_UPD='b21d499d8964986216b6a235cff5849300d966d3801b522c17461a42a1ff1448'
STOCK_APP='9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'
FINAL_UPD='ce23b4f3d198f5066bc6861223d249d9c66d979b5f0af54a0d32e8e2cb0671f6'
FINAL_APP='7043737b5a8e1c2d42b1435486871a686f1edf53e1c0fef79c7e0eec58ecebe3'
def digest(data):return hashlib.sha256(data).hexdigest()
def save_exact(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=data:raise ValueError(f'Refusing to replace different local file: {path}')
    else:
        with path.open('xb') as f:f.write(data)
def read_official(path):
    if path.stat().st_size>32*1024*1024:raise ValueError('Input is too large for the frozen 1.44 update')
    if path.suffix.lower()=='.zip':
        with zipfile.ZipFile(path) as z:
            if z.namelist()!=['XDJ1KMK2.UPD'] or z.getinfo('XDJ1KMK2.UPD').file_size!=25391319:
                raise ValueError('Not the supported manufacturer ZIP layout')
            data=z.read('XDJ1KMK2.UPD')
    else:data=path.read_bytes()
    if len(data)!=25391319 or digest(data)!=STOCK_UPD:
        raise ValueError('Unsupported firmware. Only the exact official XDJ-1000MK2 1.44 hash is accepted.')
    return data

def verify_folder(folder,expected_update,expected_app):
    if digest((folder/'XDJ1KMK2.UPD').read_bytes())!=expected_update:raise ValueError('Output update hash mismatch')
    if digest((folder/'application.bin').read_bytes())!=expected_app:raise ValueError('Output application hash mismatch')
    manifest=json.loads((folder/'manifest.json').read_text())
    for name,expected in manifest['source_sha256'].items():
        if digest((ROOT/name).read_bytes())!=expected:raise ValueError(f'Frozen source changed: {name}')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--firmware',required=True,type=Path)
    a=p.parse_args()
    if not __debug__:p.error('Do not use Python -O: low-level research assertions must stay enabled')
    try:
        data=read_official(a.firmware)
        components=extract(data);main_image=components[0][1]
        app,_=unpack(main_image,0x40000)
        if digest(app)!=STOCK_APP:raise ValueError('Unexpected MAIN application')
        save_exact(ROOT/'private/originals/v144/XDJ1KMK2.UPD',data)
        for name,image,_ in components:save_exact(ROOT/f'private/extracted/v144/{name}.bin',image)
        for off in (0x10000,0x40000):
            image,_=unpack(main_image,off)
            save_exact(ROOT/f'private/extracted/v144/main-{off:06x}-unpacked.bin',image)
        print('Official 1.44 input verified; preparing the frozen FINAL16 base.',flush=True)
        if not BASE_FOLDER.exists():build_base()
        verify_folder(BASE_FOLDER,BASE_UPD_SHA,BASE_APP_SHA)
        print('Accepted base matches. Preparing Custom XDJ v1.',flush=True)
        if not FINAL_FOLDER.exists():build_final()
        verify_folder(FINAL_FOLDER,FINAL_UPD,FINAL_APP)
        # No developer-only reports or fixtures are needed for this public entry point.
        print(f'Verified output: {FINAL_FOLDER / "XDJ1KMK2.UPD"}')
        print(f'SHA-256: {FINAL_UPD}')
        print('Nothing was copied to USB or installed. Read docs/installation.md before proceeding.')
    except (OSError,ValueError,AssertionError,zipfile.BadZipFile) as e:
        p.exit(1,f'Build refused: {e}\n')
if __name__=='__main__':main()
