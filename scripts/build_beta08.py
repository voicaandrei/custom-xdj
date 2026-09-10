#!/usr/bin/env python3
"""Hash-locked Test 08 builder; no USB operations or historical report writes."""
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'private/browser-waveform-beta-v144-test08'
MARKER_TEXT = 'XDJ BETA 08'.encode('utf-16le')
spec = importlib.util.spec_from_file_location('_beta08_primitives', ROOT / 'scripts/build_beta06.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
core.MARKER_TEXT = MARKER_TEXT
core.SOURCES = tuple(ROOT / p for p in (
    'native/beta_runtime_trace.c', 'native/waveform_prepare.c',
    'native/waveform_cell.c', 'native/pixel_channels.c', 'native/v144/beta08_hooks.S'))
core.HASH_SOURCES = core.SOURCES + tuple(ROOT / p for p in (
    'native/beta_runtime.c', 'native/beta_runtime.h', 'native/waveform_prepare.h',
    'native/waveform_cell.h', 'native/pixel_channels.h',
    'scripts/build_beta08.py', 'scripts/build_beta06.py'))
link_beta = core.link_beta
PATCHES = core.PATCHES


def build(destination=FOLDER):
    reference = (ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    original = (ROOT / 'private/originals/v144/XDJ1KMK2.UPD').read_bytes()
    if hashlib.sha256(reference).hexdigest() != core.APPLICATION_SHA:
        raise ValueError('Wrong stock application')
    destination.mkdir(exist_ok=False)
    linked = link_beta(destination, len(reference))
    application = core.patch_application(reference, linked)
    core.verify_application(reference, application, linked)
    with tempfile.TemporaryDirectory() as temporary:
        packed = core.encoder(temporary)(application)
    base = core.repackage_verified_application(original, packed, application)
    core.validate(base, original, application)
    update = core.apply_force_marker(base, original)
    validation = core.validate_forced_candidate(update, base, original, application)
    (destination / 'application.bin').write_bytes(application)
    (destination / 'XDJ1KMK2.UPD').write_bytes(update)
    report = {
        'kind': 'test-08-validated-row-waveform-beta', 'numeric_version': '1.44',
        'text_marker': 'XDJ BETA 08', 'text_marker_offsets': list(core.TEXT_OFFSETS),
        'reference_application_sha256': core.APPLICATION_SHA,
        'reference_update_sha256': hashlib.sha256(original).hexdigest(),
        'address_space': 'FILE in decompressed MAIN; CODE = 0x08000000 + FILE; caller stack offsets are relative',
        'application_sha256': hashlib.sha256(application).hexdigest(),
        'application_bytes': len(application),
        'update_sha256': hashlib.sha256(update).hexdigest(), 'update_bytes': len(update),
        'extension_file_offset': linked['file_offset'],
        'extension_code_pointer': linked['code_pointer'],
        'extension_padding_bytes': linked['padding_bytes'],
        'extension_bytes': len(linked['payload']), 'extension_sha256': linked['payload_sha256'],
        'source_sha256': linked['source_sha256'], 'hook_symbols': linked['symbols'],
        'identity': {'accepted_context_types': [1, 2], 'caller_row_pointer_stack_offset': 16,
                     'row_main_id_offset': 0, 'row_artwork_id_offset': 8,
                     'require_artwork_id_match': True, 'context_zero_reads_row': False},
        'trace_stages': {'0': 'decoder without request', '1': 'request, null context',
                         '2': 'context 1/2, row absent or artwork mismatch',
                         '3': 'row and artwork match, numeric ID zero',
                         '4': 'nonzero numeric ID', '5': 'RGB request',
                         '6': 'RGB blob received', '7': 'RGB prepared but not applied',
                         '8': 'Blue request', '9': 'Blue blob received',
                         '10': 'Blue prepared but not applied', '11': 'unsupported context (including 0)'},
        'stock_getimage_return_preserved': True,
        'validation': validation,
        'hardware_tested': False, 'copied_to_usb': False,
        'limits': ['Waveform retrieval and row association on hardware remain unverified.',
                   'Context 0 is diagnosed, not used to issue speculative track requests.',
                   'Stock artwork cache still limits coverage to artwork-eligible rows.',
                   'Feature toggle, request concurrency and performance are not validated.',
                   'Recovery from checksum-valid application hang remains unverified.']}
    (destination / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    report = build()
    (ROOT / 'evidence/browser-waveform-beta-v144-test08.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
