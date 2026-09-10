#!/usr/bin/env python3
"""Build ONE hash-locked diagnostic instruction change, offline, in private/.

No added code, allocation, stack, waveform lookup, or device operations.
The original renderer's pixel load is replaced by MOV #31,R8 (word 0x001f).
This affects every artwork copy passing this shared loop, including INFO.
"""
import hashlib
import json
from pathlib import Path
import tempfile
from build_probe_hook import SHA
from check_lzss_encoder import encoder
from repack_reference import repackage_verified_application, validate

ROOT=Path(__file__).resolve().parents[1]
OFFSET=0x152d1b6
BEFORE=bytes.fromhex('2d08')
AFTER=bytes.fromhex('1fe8')


def patch(reference):
    if hashlib.sha256(reference).hexdigest()!=SHA:
        raise ValueError('Wrong application reference')
    if reference[OFFSET:OFFSET+2]!=BEFORE:
        raise ValueError('Unexpected pixel load')
    return reference[:OFFSET]+AFTER+reference[OFFSET+2:]


def verify_patch(reference,candidate):
    if candidate!=patch(reference):
        raise ValueError('Only the exact two-byte diagnostic is allowed')


def build():
    folder=ROOT/'private/inline-probe-v144'
    folder.mkdir(exist_ok=False)
    reference=(ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    original=(ROOT/'private/originals/v144/XDJ1KMK2.UPD').read_bytes()
    candidate=patch(reference)
    verify_patch(reference,candidate)
    with tempfile.TemporaryDirectory() as tmp:
        packed=encoder(tmp)(candidate)
    update=repackage_verified_application(original,packed,candidate)
    extracted=validate(update,original,candidate)
    (folder/'application.bin').write_bytes(candidate)
    (folder/'XDJ1KMK2.UPD').write_bytes(update)
    report={
        'kind':'inline-artwork-color-diagnostic-only',
        'reference_application_sha256':SHA,
        'reference_upd_sha256':hashlib.sha256(original).hexdigest(),
        'address_space':'file offsets in decompressed MAIN application',
        'file_offset':OFFSET,'code_pointer':0x08000000+OFFSET,
        'before_hex':BEFORE.hex(),'after_hex':AFTER.hex(),
        'before_instruction':'mov.w @(r0,r2),r8',
        'after_instruction':'mov #31,r8',
        'pixel_word':31,
        'affected_surfaces':'all artwork copies through this loop; normal rows and INFO',
        'application_sha256':hashlib.sha256(candidate).hexdigest(),
        'update_sha256':hashlib.sha256(update).hexdigest(),
        'update_bytes':len(update),'packed_bytes':len(packed),
        'extraction':extracted,
        'application_changed_bytes':2,'application_size_unchanged':True,
        'additional_stack_bytes':0,'additional_ram_bytes':0,
        'stock_control_flow_preserved':True,'panel_identical':True,
        'boot_and_updater_identical':True,
        'contains_waveform':False,'device_tested':False,
        'recovery_after_valid_but_failing_application_verified':False,
        'installation_acceptance_verified':False,
    }
    report_text=json.dumps(report,indent=2)+'\n'
    (folder/'manifest.json').write_text(report_text)
    (ROOT/'evidence/inline-probe-v144.json').write_text(report_text)
    return report


if __name__=='__main__':
    print(json.dumps(build(),indent=2))
