#!/usr/bin/env python3
"""Reproducible bounded SH4A inspection; requires requirements-analysis.txt."""
import argparse,hashlib,json
from pathlib import Path
import capstone
ROOT=Path(__file__).resolve().parents[1]
CASES={
'scroll-cancel':('main-040000-unpacked.bin','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0',[(0x128fb1c,0x128fee0),(0x12905e0,0x1290736),(0x129111c,0x1291284),(0x129c0f8,0x129c21e),(0x12bcc2c,0x12bcc44),(0x12a4cdc,0x12a4d28),(0x12be064,0x12be096),(0x1548738,0x15487de)]),
'row-record':('main-040000-unpacked.bin','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0',[(19494550, 19495446), (19501542, 19502438), (19501678, 19502574), (19502588, 19503484), (19522408, 19523304), (19522766, 19523662), (19526196, 19527092), (19526598, 19527494), (19529366, 19530262), (19529430, 19530326), (19529724, 19530620), (19530556, 19531452), (19532824, 19533720), (19540612, 19541508), (19541100, 19541996), (19541518, 19542414), (19545874, 19546770), (19547426, 19548322), (19559282, 19560178), (19569610, 19570506), (19571626, 19572522), (19572754, 19573650), (19573654, 19574550), (19578626, 19579522), (19585456, 19586352), (19589742, 19590638), (19591688, 19592584), (19592210, 19593106), (19594510, 19595406), (19607084, 19607980), (19609056, 19609952), (19617126, 19618022), (19630674, 19631570), (19631036, 19631932), (19631384, 19632280), (19631738, 19632634), (19633424, 19634320), (19635944, 19636840), (19637312, 19638208), (19637782, 19638678), (19667360, 19668256), (19670768, 19671664), (19671836, 19672732), (19691834, 19692730), (19706676, 19707572)]),
'artwork-render':('main-040000-unpacked.bin','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0',[(0x152f000,0x152f740),(0x1523d90,0x15242c8),(0x1535bd0,0x1535c80),(0x1537af0,0x1537c10),(0x152e650,0x152e8d0),(0x152cbac,0x152d220),(0x135a24c,0x135a340),(0x135ac82,0x135b3a0),(0x1363918,0x1363bb0),(0x135e000,0x135ea30),(0x135d800,0x135dbe0),(0x135bf72,0x135c130),(0x161059a,0x161082a),(0x135c324,0x135c800),(0x135a2ec,0x135a3c0),(0x1361176,0x1361570),(0x13633e0,0x1363580),(0x1363740,0x1363830),(0x13586b6,0x13587c0)]),
'row-consumer':('main-040000-unpacked.bin','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0',[
    (0x1510290,0x1510400),
    (0x150edc0,0x150ef60),
    (0x15116d0,0x15118f0),
    (0x150f100,0x150f250),
    (0x151191a,0x1511e40),
    (0x1549fb0,0x154a080),
    (0x154a3d0,0x154a490),
    (0x154a490,0x154a638),
    (0x154c072,0x154c212),
    (0x1517668,0x15178b0),
    (0x1517b12,0x1517ca0),
    (0x1515544,0x1515680),
    (0x151513c,0x1515290),
    (0x15194d0,0x1519570),
    (0x151898a,0x1518ac2),
    (0x15124e0,0x1512700),
    (0x154d140,0x154d360),
    (0x15531d0,0x15533a0),
    (0x1512e30,0x15135c6),
    (0x1513580,0x1513aa0),
    (0x1445c80,0x1445cf0),
    (0x154d020,0x154d140),
    (0x154d500,0x154d620),
    (0x154d7a0,0x154d8c0),
    (0x1514700,0x15151a0),
    (0x151b100,0x151b280),
    (0x1548b40,0x1548d80),
    (0x1552e30,0x1553090),
    (0x151f170,0x151f460),
    (0x151a940,0x151b020),
    (0x1520700,0x1520950),
    (0x15a4e1c,0x15a4ef0),
    (0x152ad60,0x152b040),
    (0x152b260,0x152b3a0),
    (0x152c0f0,0x152c2a0),
    (0x152c2b0,0x152d7f0)
]),
'hid-dispatch':('main-040000-unpacked.bin','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0',[(0x155c06c,0x155e100),(0x155fad0,0x1560190),(0x14e79d0,0x14e7f20),(0x155bdc0,0x155c06c),(0x1444b20,0x1444c20),(0x155e7d0,0x155e844),(0x15438b0,0x1543990),(0x155a880,0x155aa20)]),
'artwork':('main-040000-unpacked.bin','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0',[(0x12bd968,0x12bde00),(0x12c09a0,0x12c0c20)]),
'usb':('main-040000-unpacked.bin','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0',[(0x155995a,0x15599c2),(0x1559a28,0x1559bc0),(0x1559e9c,0x1559f0a),(0x155c06c,0x155c164)]),
'integration':('main-040000-unpacked.bin','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0',[(0x126afe8,0x126b0e0),(0x1256308,0x1256378),(0x13f2060,0x13f20c0),(0x14b910c,0x14b9186),(0x12c0dc0,0x12c0f90),(0x1293e70,0x1293f60)]),
'color':('main-040000-unpacked.bin','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0',[(0x12b4430,0x12b44c0),(0x1445274,0x14452d8)]),
'row-request':('main-040000-unpacked.bin','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0',[(0x12905e0,0x12908e0),(0x129626c,0x1296420),(0x12b92a6,0x12b9378),(0x12c24c0,0x12c2700),(0x12c19a0,0x12c1b00),(0x129f200,0x129f460),(0x129e340,0x129e640),(0x1291600,0x1292480),(0x12cb300,0x12cbadc),(0x12bd968,0x12bdbb0),(0x12c2f3e,0x12c3080),(0x1295914,0x1295b60),(0x1511e00,0x1511f60),(0x1514c7c,0x1514e20),(0x1514e20,0x1514e7a),(0x1411fe8,0x14120c4),(0x12bd200,0x12bd968),(0x12bdae8,0x12bdf40),(0x1382a9a,0x1382d00),(0x12bdf40,0x12be080),(0x1402c20,0x1402ce0),(0x1411c00,0x1411fe8),(0x14120c4,0x1412180),(0x1412270,0x1412598),(0x1412614,0x1412b90),(0x12a4a90,0x12a510a),(0x12bc418,0x12bcc90),(0x127c3e0,0x127c560),(0x127c000,0x127c160),(0x129bf00,0x129c5c0),(0x1293bb0,0x1293c98),(0x1412180,0x1412270),(0x1516a80,0x1516b50),(0x154a3a0,0x154a4d0)]),
'stock-data':('main-040000-unpacked.bin','9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0',[(0x1445274,0x14452e0),(0x12b4430,0x12b44a0),(0x1293d76,0x1293ed0),(0x1295914,0x1295a40),(0x1293c98,0x1293d76),(0x12cbf56,0x12cc0c0),(0x12cbadc,0x12cbc80),(0x12caa82,0x12cad80)]),
'boot':('main.bin','27109e16082ab444f726547f3188577dafd4f55c7de23ea9ee658532dd9373da',[(0,0xc40)]),
'boot-update':('main-010000-unpacked.bin','a85b616ee2c5958bebb7a59216fa8bc574e9f6f7606120468e89263700e2f8d4',[(0x2f722,0x2f7b0),(0x2ed78,0x2ee20),(0x2e7a0,0x2e960),(0x2e994,0x2e9fe),(0x2ebbc,0x2ec40),(0x1eaf8,0x1ec90),(0x1ec90,0x1ed00),(0x16a2e,0x16aa0)]),
'anchors':('main-040000-unpacked.bin','46aaaed98179157c523cd2797ecd3223862387a8baec21c9d4dffba87a1237df',[(0x12cbf70,0x12cc060),(0x144d940,0x144d9e0),(0x1454020,0x1454090),(0x15102e0,0x1510330)])}
p=argparse.ArgumentParser(description=__doc__);p.add_argument('case',choices=CASES);p.add_argument('--version',choices=('1.44','1.45'),default='1.45');a=p.parse_args()
LOCKED_144=('scroll-cancel','row-record','color','integration','usb','hid-dispatch','artwork','row-consumer','artwork-render','boot-update','stock-data','row-request')
if a.case in LOCKED_144 and a.version!='1.44':p.error('This analysis is locked to 1.44')
filename,digest,ranges=CASES[a.case]
if a.version=='1.44' and a.case not in LOCKED_144:
    digest={'boot':'4d7d55fe7c905c511aaef54fdeddc7f7f5ec2c935a8c9f59404d3dff4dac1f21','anchors':'9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'}[a.case]
    if a.case=='anchors': ranges=[(0x12cbf70,0x12cc060),(0x144d940,0x144d9e0),(0x1454020,0x1454090),(0x15102d0,0x1510320)]
image=ROOT/'private/extracted'/('v'+a.version.replace('.',''))/filename;b=image.read_bytes()
if hashlib.sha256(b).hexdigest()!=digest:raise ValueError('Unexpected image SHA-256')
cs=capstone.Cs(capstone.CS_ARCH_SH,capstone.CS_MODE_SH4A|capstone.CS_MODE_SHFPU);cs.skipdata=True
out=[f'SHA256 {digest}; Capstone {capstone.__version__}; SH4A little-endian. FILE OFFSETS, not runtime addresses.', 'Linear disassembly includes embedded literal pools; not all decoded words are executable instructions.']
for start,end in ranges:
    out.append(f'\nRANGE {start:#x}..{end:#x}')
    for i in cs.disasm(b[start:end],start):
        extra=''
        if len(i.bytes)==2 and i.bytes[1]&240==208:
            off=((i.address+4)&~3)+i.bytes[0]*4
            if off+4<=len(b):extra=f' ; literal pool {off:#x}, value {int.from_bytes(b[off:off+4],"little"):#010x}'
        out.append(f'{i.address:08x} {i.mnemonic:10} {i.op_str}{extra}')
target=image.parent/f'{a.case}-disassembly.txt';target.write_text('\n'.join(out)+'\n');print(target)
