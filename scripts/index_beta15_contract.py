"""Read-only, hash-locked static contracts for Test 15, not hardware proof."""
import json
from pathlib import Path
from index_beta14_contract import inspect as previous
ROOT=Path(__file__).resolve().parents[1]
def inspect():
    old=previous()
    b=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    anchors={
      0x152c244:'862f962fa62fb62fc62fd62f',0x152c01c:'962fa62fb62fc62fd62fe62f',
      0x12c0eec:'68d92b09',0x12c1188:'68d92b09',
      0x152e8f4:'accb5209',0x152c524:'02225209',0x152c2b8:'02225209',
      0x152c024:'d62fe62f',0x152c24c:'c62fd62f',
      0x128fe3c:'bd840820028900e0bd8001ec',
    }
    anchors.update({21418158: '51604c8151854d8152854e8153854f81', 22202228: '75522e8503612c85f0e20831', 22168264: '53674d6571e22335288d636174d6606008c90e622822028913600188118928221e8918211c8b6ed66352282218896150028815896bd6536000405c3000401fa06d02536004880b895e880989648807892f880589658803896888018910a0ffe273600188068960d4536000405c30004006a04d025dd6536000405c3000406d020b002360', 19463886: '01e0bd80'})
    for at,expected in anchors.items():
        assert b[at:at+len(bytes.fromhex(expected))].hex()==expected,(hex(at),b[at:at+len(bytes.fromhex(expected))].hex())
    import struct
    ram=lambda a:a-0x13b96e0c+0x15c0bdc
    assert struct.unpack_from('<14h',b,ram(0x13bca0ce))==(61,57,53,49,45,41,37,32,29,26,23,20,16,13)
    assert struct.unpack_from('<14h',b,ram(0x13bca0ea))==(59,55,51,47,43,39,35,31,28,25,22,18,15,12)
    return {'stock_application_sha256' :old['stock_application_sha256'],
      'address_space':old['address_space'],
      'anchors':dict(old['anchors'],**{hex(k):v for k,v in anchors.items()}),
      'C_static':{'stock_preview_cancellation_enable':13,'stock_cancel_latch':12,
         'row_icon_table_ram':'0x13bc877c','row_descriptors_ram':'0x13bca44c',
         'root_object_pointer_ram':'0x13bca0b8','view_flags_ram':'0x0da77d90',
         'info_view_bit':8,'info_footer_controls':[12,13],
         'row_left_setter_code':'0x09522202','row_right_edge_offset':28,
         'row_source_capacity_bytes':4480,'row_output_bytes':8960,
         'info_width':288,'info_height':28},
      'I':['Draining the added preview before outer cancellation avoids nested cancellation handling.',
           'Hiding the INFO final metadata controls prevents comment overlap.',
           'Fresh row flag plus explicit green resource selection covers stale type and neutral variants.'],
      'U':['Scroll failure elimination','Master-change refresh for all sources','160px layout on hardware','Comment suppression on hardware']}
if __name__=='__main__':
 r=inspect();(ROOT/'evidence/beta15-stock-contract.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
