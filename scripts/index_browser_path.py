#!/usr/bin/env python3
"""Hash-locked offline browser data-path index; never accesses a player."""
import hashlib
import json
from pathlib import Path

from index_hid_dispatch import SHA, pointer_users, relative_switch

ROOT = Path(__file__).resolve().parents[1]


def pc_literal(data, pc):
    """Resolve a previously inspected SH MOV.L @(disp,PC),Rn instruction."""
    if pc < 0 or pc % 2 or pc + 2 > len(data):
        raise ValueError('Invalid instruction offset')
    opcode = int.from_bytes(data[pc:pc + 2], 'little')
    if opcode & 0xf000 != 0xd000:
        raise ValueError('Expected PC-relative MOV.L')
    pool = ((pc + 4) & ~3) + (opcode & 255) * 4
    if pool + 4 > len(data):
        raise ValueError('Literal outside image')
    return {'movl_file_offset': pc, 'literal_file_offset': pool,
            'pointer_value': int.from_bytes(data[pool:pool + 4], 'little')}


def immediate(data, pc, operation='mov'):
    """Resolve one inspected SH 8-bit immediate instruction, refusing any other."""
    if pc < 0 or pc % 2 or pc + 2 > len(data):
        raise ValueError('Invalid instruction offset')
    opcode = int.from_bytes(data[pc:pc + 2], 'little')
    expected = {'mov': 0xe000, 'add': 0x7000, 'tst': 0xc800}.get(operation)
    if expected is None:
        raise ValueError('Unsupported inspected immediate operation')
    if operation == 'tst':
        if opcode & 0xff00 != expected:
            raise ValueError('Expected inspected TST #imm,R0')
        return {'file_offset': pc, 'operation': operation, 'register': 0,
                'signed_value': opcode & 255}
    if opcode & 0xf000 != expected:
        raise ValueError('Expected inspected immediate instruction')
    value = opcode & 255
    return {'file_offset': pc, 'operation': operation, 'register': (opcode >> 8) & 15,
            'signed_value': value if value < 128 else value - 256}


def analyze(data):
    if hashlib.sha256(data).hexdigest() != SHA:
        raise ValueError('Unexpected 1.44 application SHA-256')
    switches = [
        {'label_inferred': name, 'table_file_offset': table,
         'braf_file_offset': branch,
         'entries': relative_switch(data, table, branch, first, count)}
        for name, table, branch, first, count in (
            ('browser command', 0x150ef30, 0x150ef1e, 1, 51),
            ('UI message', 0x154a5dc, 0x154a574, 0x1001, 46),
            ('UPDATE_LIST mode', 0x154c0fc, 0x154c0a2, 1, 11),
        )
    ]
    sites = (
        ('command storage', 0x15102f0),
        ('send UI message', 0x150f166),
        ('primary record consumer', 0x154d0c2),
        ('secondary record consumer', 0x154d590),
        ('primary consumer in mode 10', 0x154d81e),
        ('slot base', 0x1519522),
        ('auxiliary slot base', 0x1519548),
        ('identifier low-word setter', 0x1512efa),
        ('identifier high-word setter', 0x1512f06),
        ('identifier comparison in completion', 0x1514eda),
        ('intermediate model base', 0x151a9ac),
        ('intermediate group base', 0x1520744),
        ('display-facing group base', 0x1520754),
        ('resource A copy storage', 0x1520750),
        ('resource B copy storage', 0x1520730),
    )
    # Interpretations stay separate from mechanically extracted instructions.
    return {
        'firmware_version': '1.44', 'image_sha256': SHA,
        'image': 'main-040000-unpacked.bin',
        'address_space': 'All *_file_offset fields are offsets in this exact file. '
                         'pointer_value is a literal from the image, not a write address. '
                         'Candidate code mapping subtracts 0x08000000; not valid for data.',
        'method': 'Offline static inspection, SH4A little-endian; no firmware execution.',
        'limitations': 'No complete producer-to-consumer transport proof, draw hook, '
                       'runtime ABI, safe memory lifetime, loader, or recovery. '
                       'Pointer scan matches are candidates, including possible data.',
        'switches': switches,
        'inspected_literals': [{'label_inferred': name, **pc_literal(data, pc)}
                               for name, pc in sites],
        'consumer_file_offsets': {'primary': 0x1512e4c, 'secondary': 0x15135c6,
                                  'completion_candidate': 0x1514eb8},
        'slot_contract_static': {
            'getter_file_offset': 0x151950c,
            'base_pointer_value': pc_literal(data, 0x1519522)['pointer_value'],
            'group_stride_bytes': 0x110c, 'slot_stride_bytes': 0x220,
            'group_upper_bound_exclusive': 2, 'slot_upper_bound_exclusive': 8,
            'bounds_caveat': 'Group check is signed < 2 with no observed lower bound; '
                             'slot check is unsigned < 8. Intended groups 0 and 1.',
            'fields': [
                {'offset': 0, 'bytes': 1, 'meaning_inferred': 'flags'},
                {'offset': 4, 'bytes': 4, 'meaning_inferred': 'classification'},
                {'offset': 8, 'bytes': 2, 'meaning_inferred': 'record first-word low byte; remapped by mode'},
                {'offset': 10, 'bytes': 2, 'meaning_inferred': 'record first-word high byte & 0x3f'},
                {'offset': 12, 'bytes': 2, 'meaning_inferred': 'record second word; may change by mode'},
                {'offset': 16, 'bytes': 4, 'meaning_inferred': 'resource presence/state'},
                {'offset': 20, 'bytes': 4, 'meaning_inferred': 'resource result A, representation unknown'},
                {'offset': 24, 'bytes': 4, 'meaning_inferred': 'resource result B, representation unknown'},
                {'offset': 28, 'bytes': 2, 'meaning_inferred': 'text length in 16-bit units'},
                {'offset': 30, 'bytes': 512, 'meaning_inferred': 'text buffer cleared before copy'},
            ],
            'unknown': 'Groups are not proven double buffers or columns; eight slots '
                       'are not eight visible track rows. Final two bytes unspecified.',
        },
        'auxiliary_contract_static': {
            'getter_file_offset': 0x151953e,
            'base_pointer_value': pc_literal(data, 0x1519548)['pointer_value'],
            'stride_bytes': 20, 'slot_upper_bound_exclusive': 8,
            'fields_inferred': {'0': 'state', '4': 'eight-byte normalized identifier',
                                '12': 'result A', '16': 'result B'},
        },
        'identifier_normalization_static': {
            'low_setter_file_offset': 0x1445c98,
            'high_setter_file_offset': 0x1445cb8,
            'comparison_file_offset': 0x1445cbc,
            'operation': 'First 32-bit word masked to 24 bits; second word copied. '
                         'Comparison checks bytes 0..2 and word at +4; byte 3 ignored.',
        },
        'model_copy_static': {
            'producer_file_offset': 0x151a994,
            'group_copy_call_file_offset': 0x151ac00,
            'group_copy_bytes': 4364,
            'intermediate_model_pointer_value': 0x0da71808,
            'intermediate_group_pointer_value': 0x0da7185c,
            'display_group_pointer_value': 0x0da77de4,
            'resource_A_copy_call_file_offset': 0x1520828,
            'resource_A_copy_bytes': 4480,
            'resource_B_copy_call_file_offset': 0x152086a,
            'resource_B_copy_bytes_per_iteration': 218,
            'resource_B_iterations': 117,
            'resource_B_source_stride_bytes': 224,
            'resource_B_destination_stride_bytes': 226,
            'limitations': 'Copy extents are not established bitmap dimensions or '
                           'pixel format. Display-facing is an inferred role. '
                           'Resource copies are conditional on group flags and non-null source.',
        },
        'resource_A_destination_static': {
            'purpose': 'Where the 4480-byte resource A copy lands, and how often. '
                       'Mechanically extracted; roles below are marked as inferred.',
            'pointer_setup_loop_file_offsets': {'start': 0x1520754, 'end': 0x15207b6},
            'copy_loop_file_offsets': {'start': 0x15207ea, 'end': 0x15208d2},
            'destination_base_literal': pc_literal(data, 0x1520750),
            'destination_slot_stride_bytes': (immediate(data, 0x1520880)['signed_value'] << 8)
                                             + immediate(data, 0x152088c, 'add')['signed_value'],
            'destination_group_stride_literal': pc_literal(data, 0x15208c0),
            'slot_stride_bytes': (immediate(data, 0x1520732)['signed_value'] << 8)
                                 + immediate(data, 0x1520746, 'add')['signed_value'],
            'slots_per_group': 8, 'groups': 2,
            'store_resource_A_pointer_file_offset': 0x152076e,
            'store_zero_when_source_missing_file_offset': 0x1520770,
            'copy_gate': {
                'read_group_flags_file_offset': 0x15207ec,
                'test_instruction': immediate(data, 0x15207ee, 'tst'),
                'skip_target_file_offset': 0x15208aa,
                'meaning_inferred': 'The 4480-byte copy runs only when group flag bit '
                                    '0x10 is set, not on every repaint.',
            },
            'literal_users_of_destination_base': pointer_users(data, 0x0daacb68),
            'destination_address_expression_inferred':
                'destination_base + group * group_stride + slot * 4480; the renderer '
                'reads the same address back through display group slot +20.',
            'limitations': 'Only literal users can be enumerated; indirect readers of '
                           'the array cannot be found by a pointer scan. Ownership, '
                           'lifetime, other browser modes, locking and the meaning of '
                           'each flag bit remain unverified. This is not an authorised '
                           'write address and no injection has been performed.',
        },
        'pointers': [{'pointer_value': p, 'references': pointer_users(data, p)}
                     for p in (0x09512e4c, 0x095135c6, 0x0951950c,
                               0x0951953e, 0x09514eb8, 0x0951a994,
                               0x0da71808, 0x0da77de4, 0x0daacb68, 0x0dabe368)],
    }


if __name__ == '__main__':
    data = (ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    target = ROOT / 'evidence/browser-path-v144.json'
    target.write_text(json.dumps(analyze(data), indent=2) + '\n')
    print(target)
