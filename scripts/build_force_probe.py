#!/usr/bin/env python3
"""Build diagnostic 03 with the stock MAIN same-version force marker.

The application is exactly diagnostic 02. Only MAIN component header padding
byte 24 changes from space to '+'. The numeric version remains 1.44.
"""

import binascii
import hashlib
import json
import tempfile
from pathlib import Path

from build_marker_probe import patch as marker_patch
from check_application_update_gate import verify as verify_gate
from check_lzss_encoder import encoder
from extract_upd import decode_srecords, extract
from repack_reference import (
    repackage_verified_application,
    split_container,
    validate,
)
from unpack_main import unpack


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "private/force-probe-v144-03"
FORCE_OFFSET = 24
BEFORE = ord(" ")
AFTER = ord("+")


def apply_force_marker(base_update: bytes, original: bytes) -> bytes:
    parts = split_container(base_update)
    original_parts = split_container(original)
    if parts[1] != original_parts[1]:
        raise ValueError("PANEL differs before force marker")
    if parts[0][:32] != original_parts[0][:32]:
        raise ValueError("Unexpected MAIN label before force marker")
    if parts[0][FORCE_OFFSET] != BEFORE:
        raise ValueError("Unexpected MAIN padding byte")

    main = bytearray(parts[0])
    main[FORCE_OFFSET] = AFTER
    main[-2:] = binascii.crc_hqx(main[:-2], 0).to_bytes(2, "little")
    return (
        str(len(main)).encode()
        + b"\r\n"
        + str(len(parts[1])).encode()
        + b"\r\n"
        + bytes(main)
        + parts[1]
    )


def validate_forced(
    candidate: bytes, base_update: bytes, original: bytes, expected_application: bytes
) -> dict:
    parts = split_container(candidate)
    base_parts = split_container(base_update)
    original_parts = split_container(original)
    if parts[1] != original_parts[1]:
        raise ValueError("PANEL changed")
    expected_label = bytearray(original_parts[0][:32])
    expected_label[FORCE_OFFSET] = AFTER
    if parts[0][:32] != bytes(expected_label):
        raise ValueError("MAIN force label mismatch")
    if parts[0][32:-2] != base_parts[0][32:-2]:
        raise ValueError("S-record stream changed after force marker")
    if int.from_bytes(parts[0][-2:], "little") != binascii.crc_hqx(
        parts[0][:-2], 0
    ):
        raise ValueError("Forced MAIN component CRC mismatch")

    image, meta = decode_srecords(parts[0][32:-2])
    stock_image = extract(original)[0][1]
    stock_meta = extract(original)[0][2]
    for field in (
        "base_address",
        "end_address_exclusive",
        "entry_record",
        "ranges",
        "record_types",
    ):
        if meta[field] != stock_meta[field]:
            raise ValueError("MAIN S-record topology changed")
    decoded, unpack_meta = unpack(image, 0x40000)
    if decoded != expected_application:
        raise ValueError("Forced update application mismatch")
    if image != decode_srecords(base_parts[0][32:-2])[0]:
        raise ValueError("Force marker changed reconstructed MAIN image")
    if image[:0x40000] != stock_image[:0x40000]:
        raise ValueError("Boot or updater changed")
    return {
        "main_component_label_hex": parts[0][:32].hex(),
        "main_component_crc16": int.from_bytes(parts[0][-2:], "little"),
        "panel_byte_identical": True,
        "srecord_stream_identical_to_diagnostic_02": True,
        "reconstructed_main_identical_to_diagnostic_02": True,
        "boot_and_updater_identical_to_stock": True,
        "application": unpack_meta,
    }


def build() -> dict:
    reference = (
        ROOT / "private/extracted/v144/main-040000-unpacked.bin"
    ).read_bytes()
    original = (ROOT / "private/originals/v144/XDJ1KMK2.UPD").read_bytes()
    expected_application = marker_patch(reference)
    verify_gate(reference)
    FOLDER.mkdir(exist_ok=False)
    with tempfile.TemporaryDirectory() as temporary:
        packed = encoder(temporary)(expected_application)
    base_update = repackage_verified_application(
        original, packed, expected_application
    )
    validate(base_update, original, expected_application)
    candidate = apply_force_marker(base_update, original)
    validation = validate_forced(
        candidate, base_update, original, expected_application
    )
    (FOLDER / "application.bin").write_bytes(expected_application)
    (FOLDER / "XDJ1KMK2.UPD").write_bytes(candidate)
    report = {
        "kind": "diagnostic-03-forced-same-version-main-install",
        "reference_application_sha256": hashlib.sha256(reference).hexdigest(),
        "reference_update_sha256": hashlib.sha256(original).hexdigest(),
        "address_space": "MAIN component header byte offset; outer container FILE offset",
        "main_component_header_offset": FORCE_OFFSET,
        "outer_container_file_offset": 17 + FORCE_OFFSET,
        "before_hex": f"{BEFORE:02x}",
        "after_hex": f"{AFTER:02x}",
        "force_marker": "+ in header padding after preserved NUL terminator",
        "numeric_version_before": "1.44",
        "numeric_version_after": "1.44",
        "version_spoofed": False,
        "application_sha256": hashlib.sha256(expected_application).hexdigest(),
        "application_identical_to_diagnostic_02": True,
        "update_sha256": hashlib.sha256(candidate).hexdigest(),
        "update_bytes": len(candidate),
        "packed_bytes": len(packed),
        "validation": validation,
        "contains_waveform": False,
        "hardware_tested": False,
        "copied_to_usb": False,
        "expected_observation": "update takes real write time; XDJ TEST 02 replaces Not Loaded.",
        "recovery_after_valid_but_failing_application_verified": False,
    }
    payload = json.dumps(report, indent=2) + "\n"
    (FOLDER / "manifest.json").write_text(payload)
    (ROOT / "evidence/force-probe-v144-03.json").write_text(payload)
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
