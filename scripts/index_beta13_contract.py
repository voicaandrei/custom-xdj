"""Read-only stock anchors for aligned INFO storage and UI dispatch backpressure."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHA='9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'
ANCHORS={
    0x1611278:'6d62fe05077211425785fd815885fe815985018dff810772fde120e01c42f36608420042250f',
    0x16111e6:'76501c654bd1582577520f1f5e1f1c0450e04c644702',
    0x16113b8:'44e02d66fe05077611465785fd815885fe815985018dff810776fde120e01c46c36408460046650f',
    0x135e182:'98e00c604e0701e073544225715200420b0022260b0001e00000e88009a8accd3509ffff',
    0x154a5ac:'7c4c5109',
    0x154a08c:'9cd164e6d22cf9550b41c2546a020820e922028d6a42afa10900',
    0x151970a:'124f02e66334078d00e211e12ad618410c7147011a006e0223600b00164f',
    0x151963e:'02e66334048d00e260d6084443606e020b002360',
    0x151958e:'7cd60b006260',
    0x144692e:'224ff87f1ed20b42f364f150087f264f0b000900',
    0x119584:'0001010402',
}
def inspect():
    data=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    assert hashlib.sha256(data).hexdigest()==SHA
    for at,expected in ANCHORS.items():
        assert data[at:at+len(bytes.fromhex(expected))].hex()==expected,hex(at)
    # The literal being replaced must not have another consumer within this function.
    refs=[]
    for at in range(0x1549fc0,0x154a4f0,2):
        word=int.from_bytes(data[at:at+2],'little')
        if word>>12==0xd and ((at+4)&~3)+4*(word&255)==0x154a5ac:
            refs.append(hex(at))
    assert refs==['0x154a45c']
    return {
        'stock_application_sha256':SHA,
        'address_space':'ANCHORS are FILE in decompressed MAIN; CODE = FILE + 0x08000000. Table FILE 0x119584 is accessed via ROM alias 0xa8119584.',
        'anchors':{hex(k):v for k,v in ANCHORS.items()},
        'C_static':{
            'format4_bytes_per_pixel':data[0x119584+4],
            'compositor_pitch_formula':'(width * bytes_per_pixel + 7) & ~7',
            'cpu_access_pitch_formula':'allocated_width * 2',
            'test12_cpu_pitch':580,'test12_compositor_pitch':584,
            'test13_cpu_pitch':584,'test13_compositor_pitch':584,
            'source_width_unchanged':290,'surface_width':292,'height':28,
            'artwork_prepare_literal_consumers_in_ui_loop':refs,
            'gate_precedes_stock_prepare_row_mutation':True,
            'ui_mailbox_poll_timeout_ticks':100,
            'clock_low_word_getter_code':'0x0944692e',
        },
        'I':['The four-byte row-pitch mismatch explains the owner photograph.',
             'Deferring new artwork jobs while selection or list position changes reduces cancellation pressure.'],
        'U':['Actual Test 13 INFO output','Resolution of fast-scroll failure','Clock tick duration in wall-clock time','Concurrent global preview handoff correctness'],
    }
if __name__=='__main__':
    result=inspect()
    (ROOT/'evidence/beta13-stock-contract.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
