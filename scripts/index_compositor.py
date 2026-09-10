#!/usr/bin/env python3
"""Hash-locked offline index of the 1.44 graphics layer and window model.

Answers what the structure is: how many layers exist, where windows live, how
one is attached to a layer. It does NOT answer which window composites above
which; that stays reported as unknown. Static inspection only.
"""
import hashlib
import json
from pathlib import Path

from index_browser_path import immediate, pc_literal
from index_hid_dispatch import SHA, pointer_users
from index_stock_data import ascii_at

ROOT = Path(__file__).resolve().parents[1]
CODE_BASE = 0x08000000


def call_sites(data, pointer):
    return sorted({pc for entry in pointer_users(data, pointer)
                   for pc in entry['candidate_movl_file_offsets']})


def third_argument(data, call_pc, window=60):
    """Nearest preceding MOV #imm,R6 before an inspected call, or None."""
    value = None
    for pc in range(max(0, call_pc - window) & ~1, call_pc + 6, 2):
        opcode = int.from_bytes(data[pc:pc + 2], 'little')
        if opcode & 0xf000 == 0xe000 and (opcode >> 8) & 15 == 6:
            value = opcode & 255
    return value


def analyze(data):
    if hashlib.sha256(data).hexdigest() != SHA:
        raise ValueError('Unexpected 1.44 application SHA-256')
    inserts = [{'call_file_offset': pc, 'third_argument': third_argument(data, pc)}
               for pc in call_sites(data, 0x0935b85e)]
    return {
        'firmware_version': '1.44', 'image_sha256': SHA,
        'image': 'main-040000-unpacked.bin',
        'address_space': 'File offsets in this exact image. Literal pointer values are '
                         'observations, never authorised write or call addresses.',
        'method': 'Offline inspection. No firmware execution, no device, no patch.',
        'layers': {
            'array_pointer': pc_literal(data, 0x135aed4)['pointer_value'],
            'entry_stride_bytes': 48,
            'count': immediate(data, 0x135aeba)['signed_value'],
            'count_check_file_offset': 0x135aebc,
            'reject_message': ascii_at(data, pc_literal(data, 0x135a54a)['pointer_value'], 32),
            'init_file_offset': 0x1359428,
            'init_fields_inferred': {'20': 'layer id', '24': 'valid marker 0x40000000',
                                     '28': 'window pointer array', '32': 'byte array',
                                     '36': 'occupancy array', '40': 'capacity'},
            'capacity': (immediate(data, 0x135949e)['signed_value'] << 8),
            'capacity_build_file_offsets': [0x135949e, 0x13594a2],
        },
        'window_pool': {
            'pool_pointer': pc_literal(data, 0x135b0ec)['pointer_value'],
            'entry_stride_bytes': 64,
            'in_use_flag': 0x40000000,
            'allocation': 'first free slot, scanning the pool',
            'exhausted_message': ascii_at(data, pc_literal(data, 0x135b120)['pointer_value'], 32),
            'literal_users': call_sites(data, 0x0b5f6640),
        },
        'window_constructor': {
            'entry_file_offset': 0x135ae78,
            'layer_field_in_params_bytes': 16,
            'artwork_layer_argument': 0,
            'artwork_layer_store_file_offset': 0x152cff6,
            'call_sites': len(call_sites(data, 0x0935ae78)),
        },
        'layer_attach': {
            'entry_file_offset': 0x135b85e,
            'contract': 'attach(list, window, value): find the window, or take the first '
                        'free slot; mark occupancy, store the window pointer, store the '
                        'third argument into the byte array at list +4.',
            'sites': inserts,
            'distinct_third_arguments': sorted({site['third_argument'] for site in inserts
                                                if site['third_argument'] is not None}),
        },
        'window_property_setter': {
            'entry_file_offset': 0x135903e,
            'properties_inferred': {'1': 'window +32, bounded by the window size',
                                    '2': 'move the window to another layer'},
        },
        'screen': {
            'width': (immediate(data, 0x135d198)['signed_value'] << 8)
                     + immediate(data, 0x135d1a0, 'add')['signed_value'],
            'height': immediate(data, 0x135d1a4)['signed_value'] << 2,
            'build_file_offsets': [0x135d198, 0x135d19c, 0x135d1a0, 0x135d1a4, 0x135d1aa],
            'store_file_offsets': {'width': 0x135d1a2, 'height': 0x135d1ac},
            'origin_stores': [0x135d1a6, 0x135d1a8],
            'corroboration': 'The same pair also appears as adjacent 16-bit values in '
                             'display tables at 0x15cce2c and 0x160d920.',
        },
        'stacking_order': {
            'status': 'UNKNOWN',
            'why': 'The attach helper takes a byte that could order windows, but every '
                   'inspected call site passes the same value, so nothing differentiates '
                   'them. The pool itself has only four literal users, all in graphics '
                   'init and the constructor, so no compositor iterates it. The consumer '
                   'of the per-layer arrays was not located.',
            'consequence': 'Whether a repointed artwork window would cover the INFO panel '
                           'text is not established by this analysis.',
        },
        'not_proven': [
            'which window composites above which',
            'whether the two layers are hardware planes and in what order',
            'that the panel text is drawn into a window at all',
        ],
    }


if __name__ == '__main__':
    report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
    destination = ROOT / 'evidence/compositor-v144.json'
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(destination)
