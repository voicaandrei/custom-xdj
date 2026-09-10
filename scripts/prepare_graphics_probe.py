#!/usr/bin/env python3
"""Build own drawing code and exact input fixtures. Never a firmware installer."""
import ctypes
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from build_sh import FLAGS, toolchain

ROOT=Path(__file__).resolve().parents[1]
DESTINATION=ROOT/'private/first-graphics-v144'
NAMES=('draw_probe','waveform_cell','pixel_channels')
APP_SHA='9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args):
    return subprocess.run(args,check=True,capture_output=True,text=True).stdout


def preview(words, order):
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="280" viewBox="0 0 80 28" shape-rendering="crispEdges">']
    for y in range(28):
        x=0
        for pixel,group in itertools.groupby(words[y*80:(y+1)*80]):
            count=sum(1 for _ in group)
            hi=((pixel>>11)&31)*255//31
            green=((pixel>>5)&63)*255//63
            lo=(pixel&31)*255//31
            red,blue=(hi,lo) if order==0 else (lo,hi)
            parts.append(f'<rect x="{x}" y="{y}" width="{count}" height="1" fill="#{red:02x}{green:02x}{blue:02x}"/>')
            x+=count
    return '\n'.join(parts+['</svg>'])


def prepare():
    if DESTINATION.exists():
        raise FileExistsError('Probe package already exists; do not overwrite reviewed artifacts')
    if digest(ROOT/'private/extracted/v144/main-040000-unpacked.bin')!=APP_SHA:
        raise ValueError('Unexpected reference application SHA')
    tools=toolchain()
    if not tools:
        raise FileNotFoundError('SH toolchain required')
    sources=[ROOT/'native'/f'{name}.c' for name in NAMES]
    with tempfile.TemporaryDirectory(prefix='graphics-probe-',dir=ROOT/'private') as tmp:
        folder=Path(tmp)
        shared=folder/'host-probe.dylib'
        run(['cc','-shared','-fPIC','-std=c99','-O2','-Wall','-Wextra','-Werror',
             '-I',str(ROOT/'native'),*[str(p) for p in sources],'-o',str(shared)])
        library=ctypes.CDLL(str(shared))
        draw=library.xdj_draw_probe
        draw.argtypes=[ctypes.POINTER(ctypes.c_uint16),ctypes.c_size_t,ctypes.c_size_t,
                       ctypes.c_int,ctypes.c_int,ctypes.c_int]
        draw.restype=ctypes.c_int
        artifacts=[]
        for order,label in enumerate(('rgb','bgr')):
            for stage,name in enumerate(('red','channels','geometry')):
                buffer=(ctypes.c_uint16*2240)()
                if draw(buffer,2240,80,stage,order,1)!=1:
                    raise ValueError('Probe did not draw')
                raw=folder/f'{stage+1}-{name}-{label}.rgb565'
                raw.write_bytes(struct.pack('<2240H',*buffer))
                raw.with_suffix('.svg').write_text(preview(list(buffer),order))
                artifacts.append({'file':raw.name,'bytes':raw.stat().st_size,
                                  'sha256':digest(raw),'stage':stage,'channel_order':label,
                                  'word_endianness':'little','pitch_words':80})
        objects=[]
        for source in sources:
            obj=folder/(source.stem+'.o')
            run([tools['gcc'],*FLAGS,'-fstack-usage','-I',str(ROOT/'native'),
                 '-c',str(source),'-o',str(obj)])
            objects.append(obj)
        linked=folder/'draw-probe-sh4a-relocatable.o'
        run([tools['gcc'],'-m4a-nofpu','-ml','-nostdlib','-Wl,-r',
             *[str(p) for p in objects],'-o',str(linked)])
        unresolved=run([tools['nm'],'-u',str(linked)]).strip()
        if unresolved:
            raise ValueError('Unresolved symbols: '+unresolved)
        sizes=run([tools['size'],str(linked)]).splitlines()[1].split()
        if int(sizes[1]) or int(sizes[2]):
            raise ValueError('Unexpected writable static state')
        shared.unlink()  # host library is build machinery, not part of the kit
        manifest={'target_reference_sha256':APP_SHA,'dimensions':[80,28],
            'fixtures':artifacts,'source_sha256':{str(p.relative_to(ROOT)):digest(p)
                for p in [*sources,*[ROOT/'native'/f'{n}.h' for n in NAMES]]},
            'relocatable_object':{'file':linked.name,'sha256':digest(linked),
                'text_bytes':int(sizes[0]),'data_bytes':int(sizes[1]),'bss_bytes':int(sizes[2]),
                'undefined_symbols':[]},
            'ready_for_player':False,
            'missing':['verified execution transport','stock adapter and surface ownership',
                       'exact-unit recovery','runtime placement and relocation','owner authorization of concrete operation'],
            'notice':'Own code and pixel fixtures only. Not an UPD, executable image, or USB loader.'}
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (folder/'TEST.md').write_text((ROOT/'docs/first-graphics-test.md').read_text())
        Path(folder).rename(DESTINATION)
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    prepare()
