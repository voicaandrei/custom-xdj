#!/usr/bin/env python3
"""Independent bounded audit of the exact v1.44 Test 12 update."""

import binascii
import hashlib
import json
import subprocess
from pathlib import Path

from build_beta12 import FOLDER, PATCHES, COPY_OFFSET, COPY_BEFORE, KEY_ENTRY_OFFSET, KEY_ENTRY_BEFORE
from index_key_note import inspect as inspect_key_note
from build_beta06 import FORCE_AFTER, FORCE_OFFSET
from build_marker_probe import BEFORE_TEXT, TEXT_OFFSETS
from build_sh import toolchain
from extract_upd import decode_srecords
from repack_reference import split_container
from unpack_main import unpack


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evidence/browser-waveform-beta-v144-test12-final-audit.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def extension_contains_lookup(app, manifest):
    payload = app[manifest["extension_file_offset"]:]
    assert (0x09548738).to_bytes(4, "little") in payload
    assert (0x095487a0).to_bytes(4, "little") not in payload
    return True


def audit():
    manifest = json.loads((FOLDER / "manifest.json").read_text())
    update = (FOLDER / "XDJ1KMK2.UPD").read_bytes()
    app = (FOLDER / "application.bin").read_bytes()
    stock_app = (ROOT / "private/extracted/v144/main-040000-unpacked.bin").read_bytes()
    original = (ROOT / "private/originals/v144/XDJ1KMK2.UPD").read_bytes()
    assert sha(stock_app) == '9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'
    # Forwarded message is zero-filled for 112 bytes before payload writes;
    # both indexed responder branches validate and publish caller SP+16.
    stock_contract_words = {
        0x14121ec: '30d7', 0x14121ee: '70e6', 0x14121f2: '0b47',
        0x14121f4: '00e5', 0x12a4b58: '114e', 0x12a4b62: '233e',
        0x12a4b78: '441f', 0x12a4c74: '114e', 0x12a4c7c: '233e',
        0x12a4c8e: '441f', 0x12a4c90: '425e',
        0x12b4442: '1266', 0x12b4448: '6152', 0x12b444a: '2822',
        0x12b444c: '018d', 0x12b444e: '1155', 0x12b4450: '6254',
        0x12b4452: '40dd', 0x12b4454: '0b4d',
        # Stock task resets cancellation once per command, dispatcher enables
        # it for JPEG, waiter sets it, caller suppresses obsolete responses.
        0x129c144: 'ec80', 0x12bcc3a: 'dd80',
        0x128fbb0: 'ac80', 0x12a4cdc: 'dc84',
    }
    for offset, word in stock_contract_words.items():
        assert stock_app[offset:offset+2].hex() == word
    assert int.from_bytes(stock_app[0x14122b0:0x14122b4], 'little') == 0x095a6be4
    parts = split_container(update)
    stock_parts = split_container(original)
    assert sha(update) == manifest["update_sha256"]
    assert parts[0][FORCE_OFFSET] == FORCE_AFTER
    assert int.from_bytes(parts[0][-2:], "little") == binascii.crc_hqx(parts[0][:-2], 0)
    assert parts[1] == stock_parts[1]
    main, _ = decode_srecords(parts[0][32:-2])
    stock_main, _ = decode_srecords(stock_parts[0][32:-2])
    assert main[:0x40000] == stock_main[:0x40000]
    decoded, unpack_meta = unpack(main, 0x40000)
    assert decoded == app
    assert sha(app) == manifest["application_sha256"]
    expected = bytearray(stock_app)
    marker = "XDJ BETA 12".encode("utf-16le")
    assert len(marker) == len(BEFORE_TEXT)
    for offset in TEXT_OFFSETS:
        assert stock_app[offset:offset + 24] == BEFORE_TEXT + b"\0\0"
        expected[offset:offset + len(marker)] = marker
    for offset, (before, symbol) in PATCHES.items():
        assert int.from_bytes(stock_app[offset:offset + 4], "little") == before
        expected[offset:offset + 4] = manifest["hook_symbols"][symbol].to_bytes(4, "little")
    assert stock_app[COPY_OFFSET:COPY_OFFSET+len(COPY_BEFORE)] == COPY_BEFORE
    inline = bytes.fromhex(manifest['info_band']['inline_copy_after'])
    assert len(inline) == len(COPY_BEFORE)
    assert inline.hex() == '09006a0189216a41fd54f855fb522c3552653fe61846707604d10b4109006a0189216a4106a00900090070655a09000000000000'
    expected[COPY_OFFSET:COPY_OFFSET+len(inline)] = inline
    assert stock_app[KEY_ENTRY_OFFSET:KEY_ENTRY_OFFSET+12] == KEY_ENTRY_BEFORE
    expected[KEY_ENTRY_OFFSET:KEY_ENTRY_OFFSET+6] = bytes.fromhex('01d12b410900')
    expected[KEY_ENTRY_OFFSET+10:KEY_ENTRY_OFFSET+12] = bytes.fromhex('0900')
    key_evidence = inspect_key_note()
    extension = (FOLDER / "browser-waveform-beta06.bin").read_bytes()
    expected.extend(bytes(manifest["extension_padding_bytes"]))
    expected.extend(extension)
    assert bytes(expected) == app
    assert app.count(marker) == len(TEXT_OFFSETS)
    for source, digest in manifest["source_sha256"].items():
        assert sha((ROOT / source).read_bytes()) == digest
    tools = toolchain()
    prefix = str(Path(tools["gcc"]).parent / "sh-elf-")
    elf = FOLDER / "browser-waveform-beta06.elf"
    relocs = subprocess.run([prefix + "readelf", "-r", str(elf)], check=True, capture_output=True, text=True).stdout
    undefined = subprocess.run([tools["nm"], "-u", str(elf)], check=True, capture_output=True, text=True).stdout.strip()
    dis = subprocess.run([prefix + "objdump", "-d", str(elf)], check=True, capture_output=True, text=True).stdout
    assert "There are no relocations" in relocs and not undefined
    getimage = dis.split("<xdj_beta_getimage_hook>:", 1)[1].split("<xdj_beta_decode_hook>:", 1)[0]
    assert "mov.l\t@(40,r11),r0" not in getimage
    assert "cmp/eq\t#2,r0" in getimage
    assert "mov\t#80,r0" in getimage
    assert "mov\t#11,r4" in getimage
    colour = getimage.split("mov.l\t@r1,r6", 1)[1].split("cmp/eq\t#3,r0", 1)[0]
    assert "mov.l\t@(4,r1),r5" in colour
    assert "mov.l\t@(4,r6),r2" in colour
    assert "mov.l\t@(8,r6),r4" in colour
    assert "mov\t#0,r4" in colour
    assert "mov.b\t@(12,r13),r0" in getimage
    assert "mov.b\t@(13,r13),r0" in getimage
    assert "mov.b\tr0,@(12,r13)" not in getimage
    # Lookup is non-consuming; token removal API is deliberately absent.
    assert extension_contains_lookup(app, manifest)
    result_copy = getimage.index("mov\tr14,r0")
    restore = getimage.index("mov.l\t@r15+,r14")
    assert result_copy < restore
    report = {
        "kind": "test-12-final-independent-container-audit",
        "date": "2026-09-09",
        "candidate": "private/browser-waveform-beta-v144-test12/XDJ1KMK2.UPD",
        "update_sha256": sha(update), "update_bytes": len(update),
        "main_crc_valid": True, "same_version_force_marker": chr(parts[0][FORCE_OFFSET]),
        "panel_byte_identical_to_stock": True,
        "boot_and_standalone_updater_byte_identical_to_stock": True,
        "application_sha256": sha(app), "application_bytes": len(app),
        "compressed_checksum_stored": unpack_meta["checksum_stored"],
        "compressed_checksum_computed": unpack_meta["checksum_computed"],
        "marker": "XDJ BETA 12", "marker_occurrences": app.count(marker),
        "extension_sha256": sha(extension), "extension_bytes": len(extension),
        "colour_arguments": "local 0 or remote source+8, media slot connection+4",
        "cancellation_handling": "stock context+12 is preserved; cancelled preview is released without another DB call",
        "max_preview_calls_per_request": 1,
        "fallback": "stock row artwork; blank horizontal INFO band",
        "validated_row_contexts": [1, 2], "caller_row_pointer_offset": 16,
        "stock_contract_file_offsets": [hex(x) for x in stock_contract_words],
        "stock_result_copied_before_restoring_r14": True,
        "remaining_relocations": 0, "undefined_symbols": 0,
        "tests": json.loads((ROOT/"evidence/test12-validation.json").read_text()),
        "key_note_stock_evidence": key_evidence,
        "info_band": manifest["info_band"],
        "scope": "Local static checks and own-code models with mocked stock calls; not hardware validation."
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
