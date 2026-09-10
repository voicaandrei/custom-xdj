"""Final owner label only, derived from the hash-frozen, accepted FINAL16.
FILE in decompressed MAIN; data pointers preserve CODE 08000000 or P2 a8000000.
No USB writes; never alters the previous candidate or compiles new runtime code.
"""
import hashlib,json,tempfile
from pathlib import Path
from build_marker_probe import TEXT_OFFSETS, BEFORE_TEXT
from build_beta06 import validate_forced_candidate
from build_force_probe import apply_force_marker
from check_lzss_encoder import encoder
from repack_reference import repackage_verified_application,validate
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'private/browser-waveform-beta-v144-test16'
FOLDER=ROOT/'private/custom-xdj-v1-v144'
BASE_APP_SHA='365a4c1644d6eaa28243c9d089350fd46350c7f3a1acb33da4d08fc3315702ae'
BASE_UPD_SHA='322364190bacee1c3439809ac3979058b3202f7407d1b4028acd29522bad0e78'
STOCK_SHA='9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'
LABEL='Custom XDJ v1'
OLD='XDJ FINAL16'.encode('utf-16le')
DIRECT=(0x12a1874,0x12a1b08,0x12bab44,0x12c5c24)
sha=lambda b:hashlib.sha256(b).hexdigest()

def patch(base,stock):
    assert sha(base)==BASE_APP_SHA and sha(stock)==STOCK_SHA
    output=bytearray(base)
    for at in TEXT_OFFSETS:
        assert stock[at:at+24]==BEFORE_TEXT+b'\0\0'
        assert base[at:at+24]==OLD+b'\0\0'
        output[at:at+22]=BEFORE_TEXT
    start=(len(base)+3)&~3
    pointer_changes=[]
    for i,old_at in enumerate(TEXT_OFFSETS[1:]):
        at=0x1be3cf4+i*0x5a0
        before=0x08000000+old_at
        assert int.from_bytes(base[at:at+4],'little')==before
        assert base[at:at+4]==stock[at:at+4]
        after=0x08000000+start
        output[at:at+4]=after.to_bytes(4,'little')
        pointer_changes.append({'file_offset':at,'before':before,'after':after,'space':'CODE data pointer'})
    for at in DIRECT:
        before=0xa8000000+TEXT_OFFSETS[0]
        assert int.from_bytes(base[at:at+4],'little')==before
        assert base[at:at+4]==stock[at:at+4]
        after=0xa8000000+start
        output[at:at+4]=after.to_bytes(4,'little')
        pointer_changes.append({'file_offset':at,'before':before,'after':after,'space':'P2 data alias, original segment preserved'})
    # Reject undiscovered absolute references, including either segment alias.
    for i,old_at in enumerate(TEXT_OFFSETS):
        for segment in (0x08000000,0xa8000000):
            token=(segment+old_at).to_bytes(4,'little');pos=0;hits=[]
            while (pos:=base.find(token,pos))>=0:hits.append(pos);pos+=1
            expected=list(DIRECT) if i==0 and segment==0xa8000000 else [0x1be3cf4+(i-1)*0x5a0] if i>0 and segment==0x08000000 else []
            assert hits==expected,(hex(old_at),hex(segment),hits)
    output.extend(bytes(start-len(base)))
    output.extend(LABEL.encode('utf-16le')+b'\0\0')
    assert len(output)==start+28 # 13 characters plus terminator
    return bytes(output),{'label_file_offset':start,'pointer_changes':pointer_changes,'restored_original_string_slots':list(TEXT_OFFSETS)}

def build(destination=FOLDER):
    base=(BASE/'application.bin').read_bytes();stock=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    assert sha((BASE/'XDJ1KMK2.UPD').read_bytes())==BASE_UPD_SHA
    prior=json.loads((BASE/'manifest.json').read_text())
    for path,digest in prior['source_sha256'].items():assert sha((ROOT/path).read_bytes())==digest,path
    app,changes=patch(base,stock)
    original=(ROOT/'private/originals/v144/XDJ1KMK2.UPD').read_bytes()
    with tempfile.TemporaryDirectory() as temp:packed=encoder(temp)(app)
    plain=repackage_verified_application(original,packed,app)
    validate(plain,original,app)
    update=apply_force_marker(plain,original)
    validation=validate_forced_candidate(update,plain,original,app)
    destination.mkdir(exist_ok=False)
    (destination/'application.bin').write_bytes(app);(destination/'XDJ1KMK2.UPD').write_bytes(update)
    report={'kind':'owner-final-label-custom-xdj-v1','label':LABEL,'numeric_firmware':'1.44',
      'accepted_base_application_sha256':BASE_APP_SHA,'accepted_base_update_sha256':BASE_UPD_SHA,
      'stock_application_sha256':STOCK_SHA,'application_sha256':sha(app),'application_bytes':len(app),
      'update_sha256':sha(update),'update_bytes':len(update),'changes':changes,'validation':validation,
      'runtime_extension_unchanged':True,'features_unchanged_from_final16':True,
      'source_sha256':{p:sha((ROOT/p).read_bytes()) for p in ['scripts/build_custom_v1.py','scripts/build_beta16.py','scripts/build_beta06.py','scripts/build_force_probe.py','scripts/check_lzss_encoder.py','scripts/repack_reference.py','scripts/build_marker_probe.py']},
      'owner_accepted_base':True,'label_package_installed':False,'copied_to_usb':False}
    (destination/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
if __name__=='__main__':
    report=build();(ROOT/'evidence/custom-xdj-v1.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
