#!/usr/bin/env python3
"""Build the v1.44 traced browser-waveform beta used as physical Test 05.

The beta extends the decompressed MAIN application with two SH-4A wrappers and
the tested PWV4/PWAV renderer. It patches only two stock function-pointer
literals plus fixed-size diagnostic text slots, then uses the stock same-version
force marker in the outer MAIN component header.
"""

import binascii
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from build_force_probe import AFTER as FORCE_AFTER
from build_force_probe import FORCE_OFFSET, apply_force_marker
from build_marker_probe import BEFORE_TEXT, TEXT_OFFSETS
from build_probe_hook import SHA as APPLICATION_SHA
from build_sh import FLAGS, toolchain
from check_lzss_encoder import encoder
from extract_upd import decode_srecords, extract
from repack_reference import repackage_verified_application, split_container, validate
from unpack_main import unpack


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "private/browser-waveform-beta-v144-test05"
CODE_BASE = 0x08000000
ALIGNMENT = 16
MARKER_TEXT = "XDJ BETA 05".encode("utf-16le")
PATCHES = {
    0x12A4D4C: (0x09293BB0, "xdj_beta_getimage_hook"),
    0x141289C: (0x09304066, "xdj_beta_decode_hook"),
}
SOURCES = (
    ROOT / "native/beta_runtime_trace.c",
    ROOT / "native/waveform_prepare.c",
    ROOT / "native/waveform_cell.c",
    ROOT / "native/pixel_channels.c",
    ROOT / "native/v144/beta_trace_hooks.S",
)
HASH_SOURCES = SOURCES + (ROOT / "native/beta_runtime.c",)


def aligned(value: int) -> int:
    return (value + ALIGNMENT - 1) & -ALIGNMENT


def run(command) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def link_beta(folder: Path, application_length: int) -> dict:
    tools = toolchain()
    if tools is None:
        raise FileNotFoundError("SH toolchain absent")
    prefix = str(Path(tools["gcc"]).parent / "sh-elf-")
    file_offset = aligned(application_length)
    code_pointer = CODE_BASE + file_offset
    objects = []
    for source in SOURCES:
        obj = folder / (source.name.replace(".", "_") + ".o")
        run([
            tools["gcc"], *FLAGS, "-fdata-sections", "-ffunction-sections",
            "-I", str(ROOT / "native"), "-c", str(source), "-o", str(obj),
        ])
        objects.append(obj)

    linker = folder / "beta.ld"
    linker.write_text(
        "SECTIONS\n{\n"
        f"  . = 0x{code_pointer:08x};\n"
        "  .text : { KEEP(*(.text.xdj_beta_hooks)) *(.text*) }\n"
        "  .rodata ALIGN(4) : { *(.rodata*) }\n"
        "  .xdj_beta_state ALIGN(16) : { KEEP(*(.xdj_beta_state)) }\n"
        "  /DISCARD/ : { *(.comment*) *(.stack*) *(.eh_frame*) }\n"
        "}\n"
    )
    elf = folder / "browser-waveform-trace-beta.elf"
    raw = folder / "browser-waveform-trace-beta.bin"
    map_file = folder / "browser-waveform-trace-beta.map"
    run([
        prefix + "ld", "-EL", "-T", str(linker),
        "--entry=xdj_beta_getimage_hook", "-Map", str(map_file), "-o", str(elf),
        *[str(obj) for obj in objects],
    ])
    relocations = run([prefix + "readelf", "-r", str(elf)])
    if "There are no relocations" not in relocations:
        raise ValueError("Linked beta retains relocations")
    undefined = run([tools["nm"], "-u", str(elf)]).splitlines()
    if undefined:
        raise ValueError("Linked beta has undefined symbols")
    section_table = run([prefix + "readelf", "-S", str(elf)])
    if ".bss" in section_table or ".data" in section_table:
        raise ValueError("Unexpected startup-dependent data or BSS section")
    wanted = {entry[1] for entry in PATCHES.values()}
    symbols = {}
    for line in run([tools["nm"], "-n", str(elf)]).splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] in wanted:
            symbols[fields[2]] = int(fields[0], 16)
    if set(symbols) != wanted:
        raise ValueError("Hook symbols missing from linked beta")
    if any(pointer < code_pointer for pointer in symbols.values()):
        raise ValueError("Hook linked before extension base")
    run([prefix + "objcopy", "-O", "binary", str(elf), str(raw)])
    payload = raw.read_bytes()
    if not payload or len(payload) > 128 * 1024:
        raise ValueError("Implausible beta extension size")
    size_fields = run([tools["size"], str(elf)]).splitlines()[1].split()
    if int(size_fields[2]) != 0:
        raise ValueError("Beta has nonzero BSS")
    return {
        "payload": payload,
        "file_offset": file_offset,
        "code_pointer": code_pointer,
        "padding_bytes": file_offset - application_length,
        "symbols": symbols,
        "text_bytes": int(size_fields[0]),
        "data_bytes": int(size_fields[1]),
        "bss_bytes": int(size_fields[2]),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "elf_sha256": hashlib.sha256(elf.read_bytes()).hexdigest(),
        "source_sha256": {
            str(source.relative_to(ROOT)): hashlib.sha256(source.read_bytes()).hexdigest()
            for source in HASH_SOURCES
        },
        "undefined_symbols": [], "remaining_relocations": [],
    }


def patch_application(reference: bytes, linked: dict) -> bytes:
    if hashlib.sha256(reference).hexdigest() != APPLICATION_SHA:
        raise ValueError("Wrong application reference")
    if len(MARKER_TEXT) != len(BEFORE_TEXT):
        raise ValueError("Diagnostic marker length changed")
    candidate = bytearray(reference)
    for offset in TEXT_OFFSETS:
        if reference[offset:offset + 24] != BEFORE_TEXT + b"\0\0":
            raise ValueError("Unexpected stock text slot")
        candidate[offset:offset + len(MARKER_TEXT)] = MARKER_TEXT
    for offset, (stock_pointer, symbol) in PATCHES.items():
        if int.from_bytes(reference[offset:offset + 4], "little") != stock_pointer:
            raise ValueError("Unexpected stock function pointer literal")
        candidate[offset:offset + 4] = linked["symbols"][symbol].to_bytes(4, "little")
    if linked["file_offset"] != aligned(len(reference)):
        raise ValueError("Extension placement mismatch")
    candidate.extend(bytes(linked["padding_bytes"]))
    candidate.extend(linked["payload"])
    return bytes(candidate)


def verify_application(reference: bytes, candidate: bytes, linked: dict) -> None:
    if candidate != patch_application(reference, linked):
        raise ValueError("Application differs from the exact Test 04 beta image")
    if candidate[linked["file_offset"]:] != linked["payload"]:
        raise ValueError("Beta extension payload mismatch")


def validate_forced_candidate(candidate_update: bytes, base_update: bytes,
                              original_update: bytes,
                              expected_application: bytes) -> dict:
    parts = split_container(candidate_update)
    base_parts = split_container(base_update)
    original_parts = split_container(original_update)
    if parts[1] != original_parts[1]:
        raise ValueError("PANEL changed")
    expected_label = bytearray(original_parts[0][:32])
    expected_label[FORCE_OFFSET] = FORCE_AFTER
    if parts[0][:32] != bytes(expected_label):
        raise ValueError("MAIN force label mismatch")
    if parts[0][32:-2] != base_parts[0][32:-2]:
        raise ValueError("S-record stream changed while adding force marker")
    if int.from_bytes(parts[0][-2:], "little") != binascii.crc_hqx(parts[0][:-2], 0):
        raise ValueError("Forced MAIN component CRC mismatch")
    image, meta = decode_srecords(parts[0][32:-2])
    base_image, base_meta = decode_srecords(base_parts[0][32:-2])
    stock_image, stock_meta = extract(original_update)[0][1:]
    if image != base_image or meta != base_meta:
        raise ValueError("Force marker changed reconstructed MAIN")
    for field in ("base_address", "end_address_exclusive", "entry_record",
                  "ranges", "record_types"):
        if meta[field] != stock_meta[field]:
            raise ValueError("MAIN S-record topology changed")
    if image[:0x40000] != stock_image[:0x40000]:
        raise ValueError("Boot or standalone updater changed")
    decoded, unpack_meta = unpack(image, 0x40000)
    if decoded != expected_application:
        raise ValueError("Test 04 application mismatch after extraction")
    return {
        "panel_byte_identical": True,
        "srecord_stream_identical_before_and_after_force_marker": True,
        "reconstructed_main_identical_before_and_after_force_marker": True,
        "boot_and_standalone_updater_identical_to_stock": True,
        "main_component_crc16": int.from_bytes(parts[0][-2:], "little"),
        "application": unpack_meta,
    }


def build(destination: Path = FOLDER) -> dict:
    reference = (ROOT / "private/extracted/v144/main-040000-unpacked.bin").read_bytes()
    original = (ROOT / "private/originals/v144/XDJ1KMK2.UPD").read_bytes()
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir()
    linked = link_beta(destination, len(reference))
    application = patch_application(reference, linked)
    verify_application(reference, application, linked)
    with tempfile.TemporaryDirectory() as temporary:
        packed = encoder(temporary)(application)
    base_update = repackage_verified_application(original, packed, application)
    validate(base_update, original, application)
    update = apply_force_marker(base_update, original)
    validation = validate_forced_candidate(update, base_update, original, application)
    (destination / "application.bin").write_bytes(application)
    (destination / "XDJ1KMK2.UPD").write_bytes(update)
    report = {
        "kind": "test-05-browser-waveform-trace-beta-v1",
        "reference_application_sha256": APPLICATION_SHA,
        "reference_update_sha256": hashlib.sha256(original).hexdigest(),
        "address_space": "FILE offsets in decompressed MAIN; CODE pointers use 0x08000000 + FILE offset; MAIN component header is separate",
        "stock_application_bytes": len(reference),
        "candidate_application_bytes": len(application),
        "application_sha256": hashlib.sha256(application).hexdigest(),
        "extension_file_offset": linked["file_offset"],
        "extension_code_pointer": linked["code_pointer"],
        "extension_padding_bytes": linked["padding_bytes"],
        "extension_bytes": len(linked["payload"]),
        "extension_sha256": linked["payload_sha256"],
        "extension_text_bytes": linked["text_bytes"],
        "extension_data_bytes": linked["data_bytes"],
        "extension_bss_bytes": linked["bss_bytes"],
        "hook_symbols": linked["symbols"],
        "hook_undefined_symbols": linked["undefined_symbols"],
        "hook_remaining_relocations": linked["remaining_relocations"],
        "source_sha256": linked["source_sha256"],
        "stock_pointer_patches": [
            {"file_offset": offset, "before_code_pointer": before,
             "after_code_pointer": linked["symbols"][symbol], "symbol": symbol}
            for offset, (before, symbol) in PATCHES.items()
        ],
        "text_marker_offsets": list(TEXT_OFFSETS), "text_marker": "XDJ BETA 05",
        "numeric_version": "1.44", "same_version_force_header_offset": FORCE_OFFSET,
        "same_version_force_byte": "+", "packed_bytes": len(packed),
        "update_bytes": len(update), "update_sha256": hashlib.sha256(update).hexdigest(),
        "rendering": {
            "row": {"width": 80, "height": 28, "baseline": "bottom"},
            "info_cache_source": {
                "visible_width": 109, "stride_words": 112,
                "height": 117, "baseline": "bottom",
            },
            "pixel_format": "RGB565 confirmed by owner observation in Test 03",
            "preferred_data": "stock colour getter: PWV4 RGB for 3, PWAV Blue for 1",
            "fallback_data": "stock artwork when selected preview is unavailable or invalid",
            "missing_or_invalid_data": "stock artwork retained",
        },
        "visual_trace": {
            "when_waveform_is_ready": "The real waveform replaces both surfaces; no diagnostic strip is drawn.",
            "when_waveform_is_not_ready": "Bottom blue strip with one white bar per completed stage.",
            "stages": {
                "0": "decoder hook only; no matching GetImage hook entry",
                "1": "GetImage hook entered",
                "2": "local browser context accepted",
                "3": "row pointer present",
                "4": "main track ID nonzero",
                "5": "RGB/PWV4 selected",
                "6": "PWV4 response returned a non-null blob",
                "7": "PWV4 validated and rendered",
                "8": "Blue fallback selected",
                "9": "Blue response returned a non-null blob",
                "10": "Blue payload validated and rendered"
            },
            "trace_is_bounded": True,
            "row_trace_region": {"top": 21, "height": 7, "width": 80},
            "info_trace_region": {"top": 106, "height": 11, "width": 109}
        },
        "stock_behaviour": {
            "jpeg_request_retained": True, "jpeg_decoder_runs_before_overlay": True,
            "no_io_in_repaint": True, "panel_component_identical": True,
            "boot_and_standalone_updater_identical": True,
        },
        "hardware_evidence_before_test05": {
            "main_modified_application_observed_running": True,
            "test03_pixel_0x001f_observed": "blue in list and INFO",
            "test04_marker_observed": "XDJ BETA 04",
            "test04_waveform_observed": False,
            "source": "owner report, 2026-09-09",
        },
        "validation": validation, "contains_real_waveform_path": True,
        "copied_to_usb": False, "hardware_tested": False,
        "ready_for_first_beta_hardware_test": True,
        "local_verification": {
            "node_tests_passed": 33,
            "python_tests_passed": 168,
            "failures": 0,
            "independent_full_container_audit": True,
        },
        "known_beta_limits": [
            "Rows without an artwork request retain stock appearance in this traced beta.",
            "A blue strip with white bars is diagnostic output, not a waveform.",
            "The number of white bars records the last completed stage from 0 through 10.",
            "Blue uses selector zero; this exact selector still needs device validation.",
            "The feature is always enabled in Test 05; the optional toggle follows device validation.",
            "Recovery from a checksum-valid application hang remains unverified.",
        ],
    }
    payload = json.dumps(report, indent=2) + "\n"
    (destination / "manifest.json").write_text(payload)
    (ROOT / "evidence/browser-waveform-beta-v144-test05.json").write_text(payload)
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
