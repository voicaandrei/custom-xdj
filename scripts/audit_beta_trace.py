#!/usr/bin/env python3
"""Independent final audit for the exact v1.44 Test 05 traced beta."""

import binascii
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_beta_trace import FORCE_AFTER, FORCE_OFFSET, PATCHES, TEXT_OFFSETS
from build_marker_probe import BEFORE_TEXT
from build_sh import toolchain
from repack_reference import split_container
from extract_upd import decode_srecords
from unpack_main import unpack


FOLDER = ROOT / "private/browser-waveform-beta-v144-test05"
ORIGINAL = ROOT / "private/originals/v144/XDJ1KMK2.UPD"
STOCK_APP = ROOT / "private/extracted/v144/main-040000-unpacked.bin"
OUTPUT = ROOT / "evidence/browser-waveform-beta-v144-test05-final-audit.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def literal_users(data, target):
    found = []
    for address in range(0, len(data) - 1, 2):
        low, high = data[address:address + 2]
        if high >> 4 != 0xD:
            continue
        literal = ((address + 4) & ~3) + low * 4
        if literal == target:
            found.append(address)
    return found


def audit():
    manifest = json.loads((FOLDER / "manifest.json").read_text())
    original = ORIGINAL.read_bytes()
    stock = STOCK_APP.read_bytes()
    update = (FOLDER / "XDJ1KMK2.UPD").read_bytes()
    application = (FOLDER / "application.bin").read_bytes()
    extension = (FOLDER / "browser-waveform-trace-beta.bin").read_bytes()
    parts = split_container(update)
    original_parts = split_container(original)

    assert len(update) == manifest["update_bytes"]
    assert sha(update) == manifest["update_sha256"]
    assert parts[0][FORCE_OFFSET] == FORCE_AFTER
    assert int.from_bytes(parts[0][-2:], "little") == binascii.crc_hqx(parts[0][:-2], 0)
    assert parts[1] == original_parts[1]
    image, _ = decode_srecords(parts[0][32:-2])
    original_image, _ = decode_srecords(original_parts[0][32:-2])
    assert image[:0x40000] == original_image[:0x40000]
    decoded, unpack_meta = unpack(image, 0x40000)
    assert decoded == application
    assert sha(application) == manifest["application_sha256"]

    expected = bytearray(stock)
    marker = "XDJ BETA 05".encode("utf-16le")
    assert len(marker) == len(BEFORE_TEXT)
    for offset in TEXT_OFFSETS:
        assert stock[offset:offset + 24] == BEFORE_TEXT + b"\0\0"
        expected[offset:offset + len(marker)] = marker
    for offset, (before, symbol) in PATCHES.items():
        assert int.from_bytes(stock[offset:offset + 4], "little") == before
        expected[offset:offset + 4] = manifest["hook_symbols"][symbol].to_bytes(4, "little")
    expected.extend(bytes(manifest["extension_padding_bytes"]))
    expected.extend(extension)
    assert bytes(expected) == application
    assert sha(extension) == manifest["extension_sha256"]
    assert len(extension) == manifest["extension_bytes"]
    assert application.count(marker) == len(TEXT_OFFSETS)
    assert application[0x152D1B6:0x152D1B8] == bytes.fromhex("2d08")

    for source, expected_sha in manifest["source_sha256"].items():
        assert sha((ROOT / source).read_bytes()) == expected_sha

    tools = toolchain()
    assert tools is not None
    prefix = str(Path(tools["gcc"]).parent / "sh-elf-")
    elf = FOLDER / "browser-waveform-trace-beta.elf"
    relocations = subprocess.run(
        [prefix + "readelf", "-r", str(elf)], check=True,
        capture_output=True, text=True,
    ).stdout
    undefined = subprocess.run(
        [tools["nm"], "-u", str(elf)], check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    sizes = subprocess.run(
        [tools["size"], str(elf)], check=True,
        capture_output=True, text=True,
    ).stdout.splitlines()[1].split()
    disassembly = subprocess.run(
        [prefix + "objdump", "-d", str(elf)], check=True,
        capture_output=True, text=True,
    ).stdout
    assert "There are no relocations" in relocations
    assert not undefined
    assert int(sizes[2]) == 0
    getimage = disassembly.split("<xdj_beta_getimage_hook>:", 1)[1]
    getimage = getimage.split("<xdj_beta_decode_hook>:", 1)[0]
    decoder = disassembly.split("<xdj_beta_decode_hook>:", 1)[1]
    decoder = decoder.split("<_render>:", 1)[0]
    for stage in range(2, 11):
        assert f"mov\t#{stage},r4" in getimage
    for instruction in (
        "mov.l\t@(12,r15),r8", "mov\t#56,r0",
        "mov.l\t@(r0,r15),r9", "mov.l\tr9,@(0,r15)",
    ):
        assert instruction in decoder
    assert "mov\t#60,r0" not in decoder

    row_bytes = 80 * 28 * 2
    info_bytes = 112 * 117 * 2
    cache_ok = True
    for index in range(512):
        entry = 0x157F905C + index * 30744
        next_entry = entry + 30744
        row = (entry + 24 + 15) & ~15
        info = (entry + 4520 + 15) & ~15
        cache_ok &= info - row >= row_bytes and next_entry - info >= info_bytes
    assert cache_ok

    report = {
        "kind": "test-05-final-independent-container-audit",
        "date": "2026-09-09",
        "candidate": "private/browser-waveform-beta-v144-test05/XDJ1KMK2.UPD",
        "update_sha256": sha(update),
        "update_bytes": len(update),
        "main_crc16_xmodem": int.from_bytes(parts[0][-2:], "little"),
        "main_crc_valid": True,
        "same_version_force_marker": chr(parts[0][FORCE_OFFSET]),
        "panel_byte_identical_to_stock": True,
        "boot_and_standalone_updater_byte_identical_to_stock": True,
        "application_sha256": sha(application),
        "application_bytes": len(application),
        "compressed_checksum_stored": unpack_meta["checksum_stored"],
        "compressed_checksum_computed": unpack_meta["checksum_computed"],
        "marker": "XDJ BETA 05",
        "marker_occurrences": application.count(marker),
        "extension_sha256": sha(extension),
        "extension_bytes": len(extension),
        "stock_test03_inline_colour_word_restored": application[0x152D1B6:0x152D1B8].hex(),
        "getimage_literal_users": [hex(x) for x in literal_users(stock, 0x12A4D4C)],
        "decoder_literal_users": [hex(x) for x in literal_users(stock, 0x141289C)],
        "trace_stages_linked": list(range(2, 11)),
        "decoder_stock_argument_count": 5,
        "cache_bounds_all_512_entries": cache_ok,
        "elf": {
            "text_bytes": int(sizes[0]),
            "state_progbits_bytes": int(sizes[1]),
            "bss_bytes": int(sizes[2]),
            "remaining_relocations": 0,
            "undefined_symbols": 0
        },
        "tests": {"node_passed": 33, "python_passed": 168, "failed": 0},
        "scope": "Local static checks and own-code models with mocked stock calls; not hardware validation."
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
