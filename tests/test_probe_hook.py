"""Execute only our small SH hook in a bounded instruction model.

Stock release is mocked; the own pixel-writing loop is interpreted. No firmware instructions are run.
The model checks frame/argument/return handling, not device execution safety.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_sh import toolchain
from build_probe_hook import build
BASE=0x100000
DRAW=0x200000
RELEASE=0x0935a2ec
DESCRIPTOR=0x13bca44c
RETURN=0x300000


def simulate(code, descriptor=DESCRIPTOR, width=80, height=28, pitch=80, pixels=0x400000):
    if len(code)>1024: raise ValueError('Model accepts only the small own hook')
    memory={BASE+i:v for i,v in enumerate(code)}
    def write(address,value,size=4):
        for i,v in enumerate(value.to_bytes(size,'little')):memory[address+i]=v
    def read(address,size=4):
        return int.from_bytes(bytes(memory[address+i] for i in range(size)),'little')
    r=[0x100+i for i in range(16)];r[9]=descriptor;r[15]=0x500000
    original=r.copy();sp=r[15];pr=RETURN;t=False;calls=[];pixel_writes=[]
    write(descriptor,0x600000);write(descriptor+12,width,2);write(descriptor+16,height,2)
    write(sp+64,pitch);write(sp+68,pixels)
    pc=BASE
    def delay(at):
        w=read(at,2)
        if w==0x0009:return
        if w==0x6492:r[4]=read(r[9]);return
        raise AssertionError(f'Unexpected delay slot {w:x}')
    for _ in range(10000):
        w=read(pc,2);n=(w>>8)&15;m=(w>>4)&15;next_pc=pc+2
        if w==0x4f22:r[15]-=4;write(r[15],pr)
        elif w==0x4f26:pr=read(r[15]);r[15]+=4
        elif w&0xf000==0xe000:r[n]=(w&255) if (w&128)==0 else ((w&255)-256)&0xffffffff
        elif w&0xf000==0x7000:r[n]=(r[n]+((w&255) if (w&128)==0 else (w&255)-256))&0xffffffff
        elif w&0xf00f==0x6003:r[n]=r[m]
        elif w&0xf000==0xd000:r[n]=read(((pc+4)&~3)+4*(w&255))
        elif w&0xf00f==0x3000:t=r[n]==r[m]
        elif w&0xff00==0x8800:t=r[0]==((w&255) if not w&128 else ((w&255)-256)&0xffffffff)
        elif w&0xff00 in (0x8900,0x8b00):
            if t==(w&0xff00==0x8900):next_pc=pc+4+2*((w&255) if not w&128 else (w&255)-256)
        elif w&0xff00==0x8500:
            v=read(r[(w>>4)&15]+2*(w&15),2);r[0]=v if v<32768 else (v-65536)&0xffffffff
        elif w&0xf00f==0x000e:r[n]=read(r[0]+r[m])
        elif w&0xf00f==0x2008:t=(r[n]&r[m])==0
        elif w&0xff00==0xc800:t=(r[0]&(w&255))==0
        elif w&0xf00f==0x2006:r[n]-=4;write(r[n],r[m])
        elif w&0xf00f==0x2001:
            pixel_writes.append((r[n],r[m]&65535));write(r[n],r[m]&65535,2)
        elif w&0xf0ff==0x4010:
            r[n]=(r[n]-1)&0xffffffff;t=r[n]==0
        elif w&0xf0ff==0x4018:r[n]=(r[n]<<8)&0xffffffff
        elif w&0xf0ff==0x402b:
            target=r[n];delay(pc+2)
            assert target==RELEASE and pr==RETURN
            calls.append(('release',r[4]))
            assert r[15]==sp and r[8:15]==original[8:15]
            return calls,pixel_writes
        elif w&0xf0ff==0x4008:r[n]=(r[n]<<2)&0xffffffff
        elif w&0xf0ff==0x400b:
            target=r[n];pr=pc+4;delay(pc+2)
            if target==DRAW:
                calls.append(('draw',r[4],r[5],r[6],r[7],read(r[15]),read(r[15]+4)))
            elif target==RELEASE:calls.append(('release',r[4]))
            else:raise AssertionError(f'Unexpected call target {target:x}')
            # Caller-saved registers deliberately destroyed by mocked callees.
            for i in range(8):r[i]=0xdead0000+i
            r[0]=1 if target==DRAW else 0
            next_pc=pr
        elif w==0x000b:
            target=pr;delay(pc+2)
            if target==RETURN:
                assert r[15]==sp and r[8:15]==original[8:15] and r[0]==0
                return calls
            next_pc=target
        else:raise AssertionError(f'Unsupported instruction {w:04x} at {pc:x}')
        pc=next_pc
    raise AssertionError('Hook did not return')


@unittest.skipUnless(toolchain() is not None,'SH toolchain absent')
class ProbeHook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tools=toolchain();prefix=str(Path(tools['gcc']).parent/'sh-elf-')
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);obj=tmp/'hook.o';elf=tmp/'hook.elf';raw=tmp/'hook.bin'
            for command in (
                [tools['gcc'],'-m4a-nofpu','-ml','-c',str(ROOT/'native/v144/draw_probe_hook.S'),'-o',str(obj)],
                [prefix+'ld','-EL','-Ttext=0x100000','--entry=xdj_v144_probe_hook','-o',str(elf),str(obj)],
                [prefix+'objcopy','-j','.text','-O','binary',str(elf),str(raw)]):
                subprocess.run(command,check=True,capture_output=True)
            if raw.stat().st_size>1024: raise ValueError('Unexpected hook size')
            cls.code=raw.read_bytes()

    @unittest.skipUnless((ROOT/'private/extracted/v144/main-040000-unpacked.bin').exists(), 'Private reference absent')
    def test_leaf_hook_links_without_any_external_own_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=build(Path(tmp))
            self.assertEqual(report['undefined_symbols'],[])
            self.assertFalse(report['modified_firmware'])
            self.assertEqual(report['additional_stack_bytes'],0)

    def test_draw_arguments_release_and_register_stack_preservation(self):
        calls,writes=simulate(self.code)
        self.assertEqual(calls,[('release',0x600000)])
        self.assertEqual(writes,[(0x400000+2*i,0xf800) for i in range(2240)])

    def test_excluded_cells_and_invalid_geometry_release_without_drawing(self):
        for arguments in ({'descriptor':DESCRIPTOR+28},{'width':128},{'height':121},
                          {'pitch':128},{'pixels':0},{'pixels':0x400001}):
            with self.subTest(arguments=arguments):
                self.assertEqual(simulate(self.code,**arguments),([('release',0x600000)],[]))
