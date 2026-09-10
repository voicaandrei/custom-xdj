#!/usr/bin/env python3
"""Archive official research releases locally. Does not install firmware."""
import argparse
import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

RELEASES = {
    '1.45': (11838058, '535d2d424380d68c5c9f5903fb28001fbfcfc3cc42b190410a542b3f294c0b17',
             25396389, '6fd2a5002b297b86fb8a5931d3debf1b607ff6abaf9d49cd737d3a530002dbcd'),
    '1.44': (11835761, '9fd3da352c0708222cc77d581b4f2cbe3c57cab8d8fbde09929b57ca394936dc',
             25391319, 'b21d499d8964986216b6a235cff5849300d966d3801b522c17461a42a1ff1448'),
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=RELEASES, default='1.45')
    args = parser.parse_args()
    zip_size, zip_sha, upd_size, upd_sha = RELEASES[args.version]
    filename = f'XDJ1000MK2_v{args.version.replace(".", "")}.zip'
    url = f'https://downloads.support.alphatheta.com/firmwares/dj-players/XDJ-1000MK2/{filename}'
    root = Path(__file__).resolve().parents[1]
    dest = root / 'private/originals'
    if args.version != '1.45':
        dest /= 'v' + args.version.replace('.', '')
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / filename
    data = archive.read_bytes() if archive.exists() else urllib.request.urlopen(url, timeout=60).read()
    if len(data) != zip_size or hashlib.sha256(data).hexdigest() != zip_sha:
        raise ValueError('Archive differs from frozen research reference')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if z.namelist() != ['XDJ1KMK2.UPD']:
            raise ValueError('Unexpected archive members')
        info = z.getinfo('XDJ1KMK2.UPD')
        if info.file_size != upd_size:
            raise ValueError('Unexpected UPD size')
        upd = z.read(info)
    if hashlib.sha256(upd).hexdigest() != upd_sha:
        raise ValueError('UPD differs from research reference')
    for name, value in [(filename, data), ('XDJ1KMK2.UPD', upd)]:
        path = dest / name
        if path.exists():
            if path.read_bytes() != value:
                raise ValueError('Refusing overwrite of different original')
        else:
            path.write_bytes(value)
        path.chmod(0o444)
    print(f'Official v{args.version} verified and archived read-only. No player access or firmware installation.')

if __name__ == '__main__':
    main()
