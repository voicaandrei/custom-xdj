#!/usr/bin/env python3
"""Hash-locked Test 10 builder; no USB operations or historical report writes."""
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'private/browser-waveform-beta-v144-test10'
MARKER_TEXT = 'XDJ BETA 10'.encode('utf-16le')
spec = importlib.util.spec_from_file_location('_beta10_primitives', ROOT / 'scripts/build_beta06.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
core.MARKER_TEXT = MARKER_TEXT
core.SOURCES = tuple(ROOT / p for p in (
    'native/beta_runtime_scroll.c', 'native/waveform_prepare.c',
    'native/waveform_cell.c', 'native/pixel_channels.c', 'native/v144/beta10_hooks.S'))
core.HASH_SOURCES = core.SOURCES + tuple(ROOT / p for p in (
    'native/beta_runtime.c', 'native/beta_runtime.h', 'native/waveform_prepare.h',
    'native/waveform_cell.h', 'native/pixel_channels.h',
    'scripts/build_beta10.py', 'scripts/build_beta06.py'))
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
        'kind': 'test-10-validated-row-waveform-beta', 'numeric_version': '1.44',
        'text_marker': 'XDJ BETA 10', 'text_marker_offsets': list(core.TEXT_OFFSETS),
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
        'colour_source': {'player': '0 if source+4 is zero else source+8',
                          'media_slot': 'connection+4',
                          'source_handle': 'connection[0]',
                          'stock_caller_file_offset': '0x12b4442',
                          'null_source': 'Blue fallback'},
        'identity': {'accepted_context_types': [1, 2], 'caller_row_pointer_stack_offset': 16,
                     'row_main_id_offset': 0, 'row_artwork_id_offset': 8,
                     'require_artwork_id_match': True, 'context_zero_reads_row': False},
        'visual_trace_enabled': False,
        'stock_getimage_return_preserved': True,
        'scroll_protection': {'stock_cancel_byte': 12, 'never_clear_stock_cancel': True,
                              'preflight_lookup_code': '0x09548738', 'lookup_consumes_token': False,
                              'max_preview_requests_per_artwork_request': 1,
                              'after_cancel': 'release waveform, clear JPEG outputs, return 0; no more DB requests',
                              'fallback_pixels': 'unchanged stock artwork, no diagnostic strip'},
        'validation': validation,
        'hardware_tested': False, 'copied_to_usb': False,
        'limits': ['Blue/RGB worked in owner Test 09; fast scrolling regressed. Test 10 fix is not yet hardware validated.',
                   'Context 0 keeps stock artwork; no speculative track requests.',
                   'Stock artwork cache still limits coverage to artwork-eligible rows.',
                   'Feature toggle, request concurrency and performance are not validated.',
                   'Recovery from checksum-valid application hang remains unverified.']}
    (destination / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    report = build()
    (ROOT / 'evidence/browser-waveform-beta-v144-test10.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
