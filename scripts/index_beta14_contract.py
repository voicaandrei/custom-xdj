"""Additional read-only stock control-flow anchors for Test 14."""
import hashlib
import json
from pathlib import Path
from index_beta13_contract import inspect as previous_contract
ROOT=Path(__file__).resolve().parents[1]
def inspect():
    old=previous_contract()
    b=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    extra={
        0x152d140:'35d1f366f365926440764475d9270b416a476a020820d922428f6a42',
        0x154a59c:'ca1e5109',
        0x152d21c:'eca23509',
    }
    for at,expected in extra.items():
        assert b[at:at+len(bytes.fromhex(expected))].hex()==expected,hex(at)
    return {
        'stock_application_sha256':old['stock_application_sha256'],
        'address_space':old['address_space'],
        'anchors':dict(old['anchors'],**{hex(k):v for k,v in extra.items()}),
        'C_static':{
            'access_args':'r4 handle, r5 pixel output, r6 byte-pitch output; r9 descriptor, r11 source',
            'nonzero_access_return':'FILE 0x152d158 skips copy and release to epilogue 0x152d1e0',
            'stock_release_code':'0x0935a2ec',
            'new_info_width':288,'new_info_height':28,'all_pitch_bytes':576,
            'bytes_per_copy':16128,
            'own_transfer_releases_exactly_once':True,
            'non_info_access_contract_unchanged':True,
            'observer_before_pending_list_and_artwork_exits':True,
        },
        'U':['Device rendering of Test 14','Remaining fast-scroll failure','Full producer/consumer concurrency correctness'],
        'limits':['Test 13 alignment hypothesis was not sufficient on hardware. Own transfer and consistent width are an unvalidated replacement, not proof of the complete previous root cause.'],
    }
if __name__=='__main__':
    report=inspect()
    (ROOT/'evidence/beta14-stock-contract.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
