#!/usr/bin/env python3
"""Read-only index of inspected native artwork rendering sites, exact 1.44 only."""
import hashlib
import json
from pathlib import Path

from index_browser_path import pc_literal
from index_hid_dispatch import SHA, pointer_users

ROOT = Path(__file__).resolve().parents[1]


def mov_immediate(data, pc, operation='mov'):
    if pc < 0 or pc % 2 or pc + 2 > len(data):
        raise ValueError('Invalid instruction offset')
    opcode = int.from_bytes(data[pc:pc + 2], 'little')
    expected = {'mov': 0xe000, 'add': 0x7000}.get(operation)
    if expected is None or opcode & 0xf000 != expected:
        raise ValueError('Expected inspected immediate instruction')
    value = opcode & 255
    return {'file_offset': pc, 'operation': operation, 'register': (opcode >> 8) & 15,
            'signed_value': value if value < 128 else value - 256}


def analyze(data):
    if hashlib.sha256(data).hexdigest() != SHA:
        raise ValueError('Unexpected 1.44 application SHA-256')
    initializers = {name: mov_immediate(data, pc) for name, pc in (
        ('x', 0x152cee2), ('first_y', 0x152cede),
        ('second_y_before_extu_b', 0x152ced2),
        ('width_and_source_stride_words', 0x152cee4),
        ('height', 0x152cee6), ('pair_count', 0x152ceda),
    )}
    initializers.update({name: mov_immediate(data, pc, 'add') for name, pc in (
        ('pair_y_step', 0x152cef2), ('pair_descriptor_step', 0x152cf12))})
    width = initializers['width_and_source_stride_words']['signed_value']
    height = initializers['height']['signed_value']
    sites = [
        ('row artwork call', 0x152e852),
        ('display group base', 0x152cbc4),
        ('surface constructor', 0x152cc30),
        ('surface rectangle operation', 0x152d126),
        ('surface access', 0x152d140),
        ('surface release', 0x152d1d0),
        ('fallback resource lookup', 0x152cd30),
        ('descriptor table base', 0x152ced0),
        ('surface access wrapper callback', 0x136393c),
        ('surface access backend', 0x1363918),
        ('surface release wrapper', 0x135a37e),
        ('surface release backend', 0x1363966),
        ('artwork rectangle wrapper', 0x135acec),
        ('rectangle wrapper callback', 0x1363aca),
        ('rectangle callback backend', 0x1363a96),
        ('rectangle backend fill', 0x135e78e),
        ('fill color state', 0x135c344),
    ]
    return {
        'firmware_version': '1.44', 'image_sha256': SHA,
        'image': 'main-040000-unpacked.bin',
        'address_space': 'All file offsets refer to this exact decompressed image. '
                         'Literal pointer values are observations, not write addresses.',
        'method': 'Offline inspection; no firmware or device execution.',
        'initializers': initializers,
        'special_descriptor_stores': [
            {'field': name, 'file_offset': pc,
             'opcode': int.from_bytes(data[pc:pc + 2], 'little'),
             'kind': 'register store, NOT an immediate constant',
             'patch_status': 'Unknown: trace producers and all register uses before designing a patch'}
            for name, pc in [('x', 0x152cf62), ('y', 0x152cf6c),
                             ('width', 0x152cf74), ('source_stride', 0x152cf7a),
                             ('height', 0x152cf7e)]
        ],
        'inspected_literals': [{'label_inferred': label, **pc_literal(data, pc)}
                               for label, pc in sites],
        'normal_surface_static': {
            'width': width, 'height': height, 'bytes_per_copied_element': 2,
            'source_bytes': width * height * 2,
            'descriptor_stride_bytes': 28,
            'descriptor_fields_inferred': {'0': 'surface handle', '4': 'x', '8': 'y',
                '12': 'surface width u16', '14': 'source stride u16 words',
                '16': 'height u16', '20': 'constructor ID', '24': 'fallback resource ID'},
            'normal_destinations': list(range(7)),
            'normal_model_slot_expression': 'source row argument + 1',
            'normal_resource_field': 'slot +20 (A)',
            'special_destination': 7,
            'special_resource_field': 'slot +24 (B), different geometry',
            'limits': 'Only the inspected list path. Not every browser mode. '
                      'Coordinate units/pixel presentation and clipping await hardware validation.',
        },
        'special_surface_static': {
            'destination': 7,
            'purpose_inferred': 'The INFO panel artwork for the selected track, not a list row.',
            'x': (mov_immediate(data, 0x152cf16)['signed_value'] << 8)
                 + mov_immediate(data, 0x152cf22, 'add')['signed_value'],
            'y': 200 + mov_immediate(data, 0x152cf6a, 'add')['signed_value'] + 4,
            'width': mov_immediate(data, 0x152cf54)['signed_value'] & 0xff,
            'source_stride_words': mov_immediate(data, 0x152cf5c)['signed_value'],
            'height': mov_immediate(data, 0x152cf34)['signed_value'],
            'store_file_offsets': {'x': 0x152cf62, 'y': 0x152cf6c, 'width': 0x152cf74,
                                   'source_stride': 0x152cf7a, 'height': 0x152cf7e},
            'resource_field': 'slot +24 (B)',
            'copy_visible_pixels_per_row': 109,
            'copy_rows': 117,
            'copy_source_stride_pixels': 112,
            'copy_destination_stride_pixels': 113,
            'limits': 'Geometry only. Screen coordinates are not validated on hardware, '
                      'and one owner photograph is consistent with this rectangle but '
                      'does not measure it.',
        },
        'surface_flag_calls': {
            'wrapper_file_offset': 0x1358628,
            'call_sites': [
                {'file_offset': 0x152d016, 'argument_r5': 1, 'argument_r6': 8},
                {'file_offset': 0x152d026, 'argument_r5': 1, 'argument_r6': 1},
            ],
            'backend_file_offset': 0x135df1a,
            'backend_contract': 'backend(object, mask, operation) where the wrapper '
                                'swaps the two: mask is the caller argument r6 and '
                                'operation is r5.',
            'operations': {'1': 'object[+4] |= mask', '2': 'object[+4] &= ~mask',
                           '3': 'object[+4] = 0', 'other': "reports 'Unknown arg'"},
            'effect_inferred': 'Creation sets bits 0x8 then 0x1 of the object flags. '
                               'These are flag writes, NOT a stacking order. Nothing '
                               'here establishes whether the surface composites above '
                               'or below the panel text.',
        },
        'descriptor_table_capacity': {
            'table_pointer': pc_literal(data, 0x152ced0)['pointer_value'],
            'entry_stride_bytes': 28,
            'entries': 8,
            'table_bytes': 8 * 28,
            'next_used_pointer_literal_file_offset': 0x152e39c,
            'next_used_pointer': int.from_bytes(data[0x152e39c:0x152e3a0], 'little'),
            'literal_users_of_table': sorted({pc for entry in pointer_users(data, 0x13bca44c)
                                              for pc in entry['candidate_movl_file_offsets']}),
            'meaning_inferred': 'The next data pointer the image uses sits exactly at '
                                'table + 8 * 28, so the table has no spare entry. A ninth '
                                'surface cannot be appended in place; it would need the '
                                'table relocated and every literal repointed.',
        },
        'special_surface_budget': {
            'resource_b_fill_bytes_per_slot': 27346,
            'resource_b_words_per_slot': 27346 // 2,
            'declared_stride_words': 113,
            'declared_height': 121,
            'meaning_inferred': 'The resource B source buffer is exactly 113 * 121 words. '
                                'Any rectangle this descriptor is repointed at must satisfy '
                                'width * height <= 13673 with stride equal to width.',
        },
        'copy_loop_static': {
            'function_file_offset': 0x152cbac,
            'read_resource_A_file_offset': 0x152cbd6,
            'read_resource_B_file_offset': 0x152cd50,
            'presence_read_file_offset': 0x152cd26,
            'surface_access_call_file_offset': 0x152d14e,
            'pixel_load_file_offset': 0x152d1b6,
            'pixel_store_file_offset': 0x152d1b8,
            'surface_release_call_file_offset': 0x152d1d2,
            'source_index_words': 'y * descriptor.source_stride + x',
            'destination_index_bytes': 'y * pitch_bytes + 2 * x',
            'caveat': 'Return zero from access is followed by a non-null pointer check. '
                      'Surface flags and locking require complete lifetime analysis.',
        },
        'pixel_format': {'status': 'PARTIALLY_CONFIRMED_STATIC', 'confirmed_transfer_bits': 16,
                         'constructor_format_immediate': mov_immediate(data, 0x152cc24),
                         'constructor_format_store_file_offset': 0x152cc3c,
                         'unknown': 'Semantic order RGB/BGR, full transparency behavior and hardware appearance',
                         'channel_packing_static': {
                             'function_file_offset': 0x135c324,
                             'conversion_start_file_offset': 0x135c350,
                             'conversion_end_exclusive_file_offset': 0x135c3a4,
                             'formula': '((c0 >> 3) << 11) | ((c1 >> 2) << 5) | (c2 >> 3)',
                             'channel_masks': [0xf800, 0x07e0, 0x001f],
                             'middle_clear_mask_file_offset': 0x135c438,
                             'middle_clear_mask_value': int.from_bytes(data[0x135c438:0x135c43a], 'little'),
                             'rectangle_descriptor_field_bytes': 152,
                             'rectangle_descriptor_load_file_offset': 0x135e792,
                             'color_source': 'backend object +40 copied into shared color state',
                             'alpha_note': 'Packed word has no alpha bit. Fourth state byte is set to 255 separately; do not infer all transparency behavior.',
                         }},
        'surface_outer_status': {
            'access_entry_file_offset': 0x135a24c,
            'release_entry_file_offset': 0x135a2ec,
            'access_returns': {name: mov_immediate(data, pc) for name, pc in (
                ('success', 0x135a2e0), ('uninitialized', 0x135a264),
                ('null_handle', 0x135a28a), ('missing_valid_flag', 0x135a2a2),
                ('already_accessed', 0x135a2b8))},
            'release_returns': {name: mov_immediate(data, pc) for name, pc in (
                ('success', 0x135a39c), ('uninitialized', 0x135a2fc),
                ('null_handle', 0x135a322), ('missing_valid_flag', 0x135a366),
                ('not_accessed', 0x135a37c))},
            'warning': 'Outer success is 0, distinct from backend return 1. '
                       'Backend return is not propagated on the inspected success path. '
                       'Zero does not certify non-null pixels or lifetime/exclusive access.',
        },
        'surface_access_static': {
            'callback_dispatch': 'Immediate function call in inspected wrapper, not queued here',
            'backend_file_offset': 0x135e182,
            'descriptor_pointer_load_file_offset': 0x135e186,
            'descriptor_pointer_field_bytes': 152,
            'buffer_pointer_field_bytes': 12,
            'pitch_words_field_bytes': 4,
            'pitch_double_file_offset': 0x135e190,
            'backend_release_file_offset': 0x135e196,
            'backend_release_behavior': 'Returns 1, no buffer manipulation in this function',
            'outer_release_flag_clear_file_offset': 0x135a38e,
            'outer_release_mask': pc_literal(data, 0x135a388),
            'ownership_limit': 'Outer access sets flag 0x01000000 and unlocks before caller copies. '
                               'Outer release clears flag under lock. Complete protection against '
                               'other writers, destruction and stale handles remains unverified.',
        },
        'candidate_callers': pointer_users(data, 0x0952cbac),
        'not_proven': ['safe patch ABI', 'SH build and execution of our core',
                       'RAM loader', 'recovery', 'playback or scrolling performance'],
    }


if __name__ == '__main__':
    report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
    destination = ROOT / 'evidence/artwork-render-v144.json'
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(destination)
