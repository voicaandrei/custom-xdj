#!/usr/bin/env python3
"""Hash-locked Test 14 builder; no USB operations or historical report writes."""
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'private/browser-waveform-beta-v144-test14'
MARKER_TEXT = 'XDJ BETA 14'.encode('utf-16le')
spec = importlib.util.spec_from_file_location('_beta14_primitives', ROOT / 'scripts/build_beta06.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
core.MARKER_TEXT = MARKER_TEXT
core.SOURCES = tuple(ROOT / p for p in (
    'native/beta_runtime_14.c', 'native/waveform_prepare_fast.c',
    'native/waveform_cell.c', 'native/pixel_channels.c', 'native/v144/beta10_hooks.S', 'native/beta_info_band14.c', 'native/v144/info_band_hooks14.S',
    'native/beta_browse_observed.c', 'native/beta_key_note.c', 'native/v144/key_note_hooks.S'))
core.HASH_SOURCES = core.SOURCES + tuple(ROOT / p for p in (
    'native/beta_runtime.c', 'native/beta_runtime.h', 'native/waveform_prepare.h',
    'native/waveform_cell.h', 'native/waveform_prepare_fast.h', 'native/pixel_channels.h',
    'scripts/build_beta14.py', 'scripts/build_beta06.py',
    'scripts/index_beta14_contract.py', 'scripts/index_beta13_contract.py'))
core.PATCHES = dict(core.PATCHES, **{})
core.PATCHES.update({
    0x154a59c: (0x09511eca, '_xdj_beta_browse_observe'),
    0x154a5ac: (0x09514c7c, '_xdj_beta_browse_prepare'),
    0x152cebc: (0x0935ae78, 'xdj_beta_info_create_hook'),
    0x152d204: (0x0935ae78, 'xdj_beta_info_create_hook'),
    0x152d214: (0x0946e148, 'xdj_beta_info_fallback_hook'),
    0x152d218: (0x0935a24c, 'xdj_beta_info_access_hook'),
    0x12b92ac: (0x2fc62fb6, 'xdj_beta_key_note_hook'),
})
core.HASH_SOURCES += (ROOT / 'native/v144/info_band_copy14.S',)
PATCHES = core.PATCHES
COPY_OFFSET = 0x152084a
COPY_BEFORE = bytes.fromhex('75ea6a01fa5ef85200ed9c3efb5989216a412c399265dae6aed1e364dc356c660b417f7e6a02104a7f7d637e89226a42f08f617d')
KEY_ENTRY_OFFSET = 0x12b92a6
KEY_ENTRY_BEFORE = bytes.fromhex('862f962fa62fb62fc62fd62f')
base_patch = core.patch_application
base_link = core.link_beta

def link_beta(folder, application_length):
    linked = base_link(folder, application_length)
    tools = core.toolchain()
    prefix = str(Path(tools['gcc']).parent / 'sh-elf-')
    obj = folder / 'info-copy.o'
    raw = folder / 'info-copy.bin'
    core.run([tools['gcc'], *core.FLAGS, '-c', str(ROOT / 'native/v144/info_band_copy14.S'), '-o', str(obj)])
    core.run([prefix + 'objcopy', '-O', 'binary', str(obj), str(raw)])
    code = raw.read_bytes()
    if len(code) != 52 or code[50:] != bytes.fromhex('0900'):
        raise ValueError('Unexpected inline section alignment')
    linked['inline_copy'] = bytes.fromhex('0900') + code[:50]
    if len(linked['inline_copy']) != len(COPY_BEFORE):
        raise ValueError('INFO copy replacement length changed')
    return linked

def patch_application(reference, linked):
    if reference[COPY_OFFSET:COPY_OFFSET+len(COPY_BEFORE)] != COPY_BEFORE:
        raise ValueError('INFO propagation instructions differ')
    application = bytearray(base_patch(reference, linked))
    application[COPY_OFFSET:COPY_OFFSET+len(COPY_BEFORE)] = linked['inline_copy']
    if reference[KEY_ENTRY_OFFSET:KEY_ENTRY_OFFSET+12] != KEY_ENTRY_BEFORE:
        raise ValueError('Stock note mapper prologue differs')
    # At this address (2 mod 4) the literal is entry+6, PC-relative disp=1.
    application[KEY_ENTRY_OFFSET:KEY_ENTRY_OFFSET+6] = bytes.fromhex('01d12b410900')
    application[KEY_ENTRY_OFFSET+10:KEY_ENTRY_OFFSET+12] = bytes.fromhex('0900')
    return bytes(application)
core.patch_application = patch_application


def build(destination=FOLDER):
    from index_beta14_contract import inspect
    contract=inspect()
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
        'kind': 'test-14-own-info-transfer-and-navigation-observer', 'numeric_version': '1.44',
        'stock_contract':contract,
        'text_marker': 'XDJ BETA 14', 'text_marker_offsets': list(core.TEXT_OFFSETS),
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
                              'fallback_pixels': 'stock row artwork; blank INFO band; no diagnostic strip'},
        'validation': validation,
        'info_band': {'width': 288, 'height': 28, 'x': 500, 'y': 284,
                      'descriptor_ram': '0x13bca510', 'cache_words': 13104,
                      'written_words': 8064, 'destination_words': 13673,
                      'missing_preview': 'blank INFO band; row artwork retained',
                      'inline_copy_offset': COPY_OFFSET,
                      'inline_copy_before': COPY_BEFORE.hex(),
                      'inline_copy_after': linked['inline_copy'].hex(),
                      'position_status': 'position owner-confirmed in 12/13; width 288 and own transfer require Test 14 validation',
                      'surface_width':288, 'source_stride_bytes':576, 'destination_stride_bytes':576,
                      'own_transfer':True, 'stock_copy_skipped_for_info':True},
        'key_icon': {'implemented': True, 'stock_record_flag_offset': 38,
                     'stock_predicate_file_range': ['0x129221e','0x1292268'],
                     'stock_info_predicate_file_range': ['0x12c8216','0x12c826a'],
                     'mapper_entry_file_offset': KEY_ENTRY_OFFSET,
                     'mapper_entry_before': KEY_ENTRY_BEFORE.hex(),
                     'extra_db_requests': 0,
                     'requires_stock_key_match_flag': True,
                     'hardware_coverage_all_browse_modes': False},
        'browse_settle': {'quiet_ticks':250, 'observe_before_pending_exits':True, 'stock_pending_result_unchanged':True},
        'hardware_tested': False, 'copied_to_usb': False,
        'limits': ['Blue/RGB worked in owner Test 09; fast scrolling regressed. Test 14 fix is not yet hardware validated.',
                   'Context 0 keeps stock artwork; no speculative track requests.',
                   'Stock artwork cache still limits coverage to artwork-eligible rows.',
                   'Key notes reuse stock per-row compatibility, with no new database requests. All browse modes and master-change refresh require hardware validation.',
                   'INFO band replaces the square artwork surface. Exact panel overlap and layer order require hardware validation.',
                   'Feature toggle, request concurrency and performance are not validated.',
                   'Recovery from checksum-valid application hang remains unverified.']}
    (destination / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    report = build()
    (ROOT / 'evidence/browser-waveform-beta-v144-test14.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
