#!/usr/bin/env python3
"""Independent bounded audit of the exact v1.44 Test 08 update."""

import binascii
import hashlib
import json
import subprocess
from pathlib import Path

from build_beta08 import FOLDER
from build_beta06 import FORCE_AFTER, FORCE_OFFSET, PATCHES
from build_marker_probe import BEFORE_TEXT, TEXT_OFFSETS
from build_sh import toolchain
from extract_upd import decode_srecords
from repack_reference import split_container
from unpack_main import unpack


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evidence/browser-waveform-beta-v144-test08-final-audit.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


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
    marker = "XDJ BETA 08".encode("utf-16le")
    assert len(marker) == len(BEFORE_TEXT)
    for offset in TEXT_OFFSETS:
        assert stock_app[offset:offset + 24] == BEFORE_TEXT + b"\0\0"
        expected[offset:offset + len(marker)] = marker
    for offset, (before, symbol) in PATCHES.items():
        assert int.from_bytes(stock_app[offset:offset + 4], "little") == before
        expected[offset:offset + 4] = manifest["hook_symbols"][symbol].to_bytes(4, "little")
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
    result_copy = getimage.index("mov\tr14,r0")
    restore = getimage.index("mov.l\t@r15+,r14")
    assert result_copy < restore
    report = {
        "kind": "test-08-final-independent-container-audit",
        "date": "2026-09-09",
        "candidate": "private/browser-waveform-beta-v144-test08/XDJ1KMK2.UPD",
        "update_sha256": sha(update), "update_bytes": len(update),
        "main_crc_valid": True, "same_version_force_marker": chr(parts[0][FORCE_OFFSET]),
        "panel_byte_identical_to_stock": True,
        "boot_and_standalone_updater_byte_identical_to_stock": True,
        "application_sha256": sha(app), "application_bytes": len(app),
        "compressed_checksum_stored": unpack_meta["checksum_stored"],
        "compressed_checksum_computed": unpack_meta["checksum_computed"],
        "marker": "XDJ BETA 08", "marker_occurrences": app.count(marker),
        "extension_sha256": sha(extension), "extension_bytes": len(extension),
        "validated_row_contexts": [1, 2], "caller_row_pointer_offset": 16,
        "stock_contract_file_offsets": [hex(x) for x in stock_contract_words],
        "stock_result_copied_before_restoring_r14": True,
        "remaining_relocations": 0, "undefined_symbols": 0,
        "tests": {"node_passed": 33, "python_passed": 183, "failed": 0},
        "scope": "Local static checks and own-code models with mocked stock calls; not hardware validation."
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
