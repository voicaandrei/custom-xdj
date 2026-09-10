#!/usr/bin/env python3
"""Offline diagnostic 02: unchanged v1 colour probe plus a fixed-size UI marker.

No device writes. No firmware version spoofing. Original string slots and NUL
terminators are preserved. Visibility is a hardware hypothesis, not a build fact.
"""
import hashlib
import json
import tempfile
from pathlib import Path
from build_inline_probe import patch as colour_patch, SHA, OFFSET, AFTER
from check_lzss_encoder import encoder
from repack_reference import repackage_verified_application, validate

ROOT = Path(__file__).resolve().parents[1]
TEXT_OFFSETS = (
    0x92f3a, 0x1b8e722, 0x1b91d2e, 0x1b96530, 0x1b9b76c,
    0x1ba0850, 0x1ba58d0, 0x1baa9fe, 0x1bafa62, 0x1bb4bb2,
    0x1bb9c5a, 0x1bbe1a4, 0x1bc20a6, 0x1bc60f2, 0x1bcafc4,
    0x1bd00fe, 0x1bd5184, 0x1bda056, 0x1bdf270,
)
BEFORE_TEXT = 'Not Loaded.'.encode('utf-16le')
AFTER_TEXT = 'XDJ TEST 02'.encode('utf-16le')
FOLDER = ROOT / 'private/marker-probe-v144-02'


def patch(reference):
    candidate = bytearray(colour_patch(reference))  # verifies exact stock SHA
    if len(BEFORE_TEXT) != len(AFTER_TEXT):
        raise ValueError('Marker length changed')
    for offset in TEXT_OFFSETS:
        if reference[offset:offset+24] != BEFORE_TEXT + b'\0\0':
            raise ValueError('Unexpected terminated string slot')
        candidate[offset:offset+22] = AFTER_TEXT
    return bytes(candidate)


def verify_patch(reference, candidate):
    if candidate != patch(reference):
        raise ValueError('Only fixed marker slots and original colour probe allowed')


def build():
    reference = (ROOT/'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    original = (ROOT/'private/originals/v144/XDJ1KMK2.UPD').read_bytes()
    candidate = patch(reference)
    verify_patch(reference, candidate)
    FOLDER.mkdir(exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp:
        packed = encoder(tmp)(candidate)
    update = repackage_verified_application(original, packed, candidate)
    extraction = validate(update, original, candidate)
    (FOLDER/'application.bin').write_bytes(candidate)
    (FOLDER/'XDJ1KMK2.UPD').write_bytes(update)
    report = {
        'kind': 'diagnostic-02-ui-marker-and-original-artwork-colour-probe',
        'reference_application_sha256': SHA,
        'reference_upd_sha256': hashlib.sha256(original).hexdigest(),
        'address_space': 'FILE offsets in decompressed MAIN application',
        'text_offsets': list(TEXT_OFFSETS),
        'before_text': 'Not Loaded.', 'after_text': 'XDJ TEST 02',
        'encoding': 'UTF-16LE', 'slot_bytes': 24,
        'terminators_and_string_addresses_unchanged': True,
        'colour_file_offset': OFFSET, 'colour_bytes': AFTER.hex(),
        'application_sha256': hashlib.sha256(candidate).hexdigest(),
        'update_sha256': hashlib.sha256(update).hexdigest(),
        'update_bytes': len(update), 'packed_bytes': len(packed),
        'extraction': extraction,
        'version_label_unchanged': True,
        'boot_updater_panel_byte_identical': True,
        'additional_ram_bytes': 0, 'additional_stack_bytes': 0,
        'contains_waveform': False, 'hardware_visibility_verified': False,
        'device_tested': False, 'copied_to_usb': False,
    }
    payload = json.dumps(report, indent=2)+'\n'
    (FOLDER/'manifest.json').write_text(payload)
    (ROOT/'evidence/marker-probe-v144-02.json').write_text(payload)
    return report


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
