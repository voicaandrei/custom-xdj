"""Independent final label-only audit, no firmware execution or USB writes."""
import binascii,hashlib,json
from pathlib import Path
from extract_upd import decode_srecords
from unpack_main import unpack
from repack_reference import split_container
from build_marker_probe import TEXT_OFFSETS,BEFORE_TEXT
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'private/custom-xdj-v1-v144'
sha=lambda b:hashlib.sha256(b).hexdigest()
def audit():
    manifest=json.loads((FOLDER/'manifest.json').read_text())
    base=(ROOT/'private/browser-waveform-beta-v144-test16/application.bin').read_bytes()
    app=(FOLDER/'application.bin').read_bytes();upd=(FOLDER/'XDJ1KMK2.UPD').read_bytes()
    assert sha(base)=='365a4c1644d6eaa28243c9d089350fd46350c7f3a1acb33da4d08fc3315702ae'
    start=(len(base)+3)&~3
    assert len(app)==start+28
    assert app[start:]==('Custom XDJ v1'+'\0').encode('utf-16le')
    assert not any(app[len(base):start])
    expected=bytearray(base)
    for off in TEXT_OFFSETS:
        assert base[off:off+24]==('XDJ FINAL16'+'\0').encode('utf-16le')
        expected[off:off+22]=BEFORE_TEXT
        assert app[off+24:off+48]==base[off+24:off+48]
    for i in range(18):
        at=0x1be3cf4+i*1440
        assert int.from_bytes(base[at:at+4],'little')==0x08000000+TEXT_OFFSETS[i+1]
        expected[at:at+4]=(0x08000000+start).to_bytes(4,'little')
    for at in (0x12a1874,0x12a1b08,0x12bab44,0x12c5c24):
        assert base[at:at+4]==bytes.fromhex('3a2f09a8')
        expected[at:at+4]=(0xa8000000+start).to_bytes(4,'little')
    expected.extend(bytes(start-len(base)));expected.extend(('Custom XDJ v1'+'\0').encode('utf-16le'))
    assert app==expected
    assert ('XDJ FINAL16').encode('utf-16le') not in app
    m16=json.loads((ROOT/'private/browser-waveform-beta-v144-test16/manifest.json').read_text())
    ext=m16['extension_file_offset']
    assert app[ext:len(base)]==base[ext:]
    stock_parts=split_container((ROOT/'private/originals/v144/XDJ1KMK2.UPD').read_bytes())
    parts=split_container(upd)
    assert parts[1]==stock_parts[1]
    assert int.from_bytes(parts[0][-2:],'little')==binascii.crc_hqx(parts[0][:-2],0)
    main,_=decode_srecords(parts[0][32:-2]);stock_main,_=decode_srecords(stock_parts[0][32:-2])
    assert main[:0x40000]==stock_main[:0x40000]
    decoded,meta=unpack(main,0x40000);assert decoded==app
    assert sha(upd)==manifest['update_sha256'] and sha(app)==manifest['application_sha256']
    for name,digest in manifest['source_sha256'].items():assert sha((ROOT/name).read_bytes())==digest
    r={'kind':'custom-xdj-v1-label-only-independent-audit','label':'Custom XDJ v1','update_bytes':len(upd),
      'update_sha256':sha(upd),'application_sha256':sha(app),'label_file_offset':hex(start),
      'text_characters':13,'new_text_bytes_including_terminator':28,
      'language_table_pointers':18,'direct_p2_pointers':4,'neighbor_strings_unchanged':True,
      'runtime_extension_byte_identical_to_accepted_final16':True,'only_expected_text_and_data_pointer_changes':True,
      'main_crc_valid':True,'panel_byte_identical_to_stock':True,'boot_updater_byte_identical_to_stock':True,
      'tests':json.loads((ROOT/'evidence/custom-xdj-v1-validation.json').read_text()),
      'scope':'Container and exact byte-diff checks only. FINAL16 accepted by owner; new label not yet observed on player.'}
    (ROOT/'evidence/custom-xdj-v1-final-audit.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':print(json.dumps(audit(),indent=2))
