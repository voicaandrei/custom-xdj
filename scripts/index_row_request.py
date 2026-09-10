#!/usr/bin/env python3
"""Hash-locked offline index of the browser's own per-row resource request path.

The local browser issues a numbered message; the JPEG worker routes it to the
stock database client. This maps browser-side scheduling and completion.
Static inspection only: no firmware execution, no device access, no patch.
"""
import hashlib
import json
from pathlib import Path

from index_browser_path import immediate, pc_literal
from index_hid_dispatch import SHA, pointer_users
from index_stock_data import ascii_at

ROOT = Path(__file__).resolve().parents[1]
CODE_BASE = 0x08000000


def built_word(data, load, shift, add):
    """Recompute a message number built as MOV #7, SHLL8, ADD #n."""
    high = immediate(data, load)['signed_value']
    if int.from_bytes(data[shift:shift + 2], 'little') & 0xf0ff != 0x4018:
        raise ValueError('Expected inspected SHLL8')
    return (high << 8) + immediate(data, add, 'add')['signed_value']


def shift_jis_at(data, pointer):
    """Resolve a Shift-JIS diagnostic pointer, or None."""
    if not 0xa8000000 <= pointer < 0xa8000000 + len(data):
        return None
    offset = pointer - 0xa8000000
    end = data.find(b'\x00', offset)
    if end < 0 or end - offset > 64:
        return None
    try:
        return data[offset:end].decode('shift_jis')
    except UnicodeDecodeError:
        return None


def message_kinds(data):
    """The numbered requests the browser tracks, with the label it prints."""
    kinds = []
    for label_literal, load, shift, add, fields in (
        (0x1512040, 0x1511e2c, 0x1511e32, 0x1511e38, [20, 24, 28, 32]),
        (0x1512048, 0x1511e64, 0x1511e6a, 0x1511e70, [36, 40, 41, 42, 44]),
        (0x1512050, 0x1511e8a, 0x1511e8e, 0x1511e90, [48, 52]),
    ):
        pointer = int.from_bytes(data[label_literal:label_literal + 4], 'little')
        kinds.append({
            'message_number': built_word(data, load, shift, add),
            'label': shift_jis_at(data, pointer),
            'label_pointer': pointer,
            'build_file_offsets': [load, shift, add],
            'tracking_fields_bytes': fields,
        })
    return kinds


def artwork_eligibility(data):
    expected={0x151335a:0xc840,0x151335c:0x8d01,
              0x151335e:0xe201,0x1513360:0xe202,0x151336a:0x2622,
              0x1514dbe:0x8802,0x1514dc2:0x8d06}
    for pc,word in expected.items():
        if int.from_bytes(data[pc:pc+2],'little')!=word:
            raise ValueError('Unexpected artwork eligibility instruction at '+hex(pc))
    return {'initialization_file_offset':0x1513358,
            'flag_test_file_offset':0x151335a,'flag_byte_mask':64,
            'flag_halfword_mask':0x4000,
            'state_without_flag':immediate(data,0x151335e)['signed_value'],
            'state_with_flag':immediate(data,0x1513360)['signed_value'],
            'state_store_file_offset':0x151336a,
            'queue_scan_state_test_file_offset':0x1514dbe,
            'queue_scan_match_branch_file_offset':0x1514dc2,
            'state_2_alone_means_request_sent':False,
            'interpretation':'Initialization makes artwork-bearing rows eligible (2), others 1. One actual in-flight request is tracked separately. Special priority paths can also force state 2.'}


def analyze(data):
    if hashlib.sha256(data).hexdigest() != SHA:
        raise ValueError('Unexpected 1.44 application SHA-256')
    eligibility=artwork_eligibility(data)
    kinds = message_kinds(data)
    return {
        'artwork_eligibility':eligibility,
        'firmware_version': '1.44', 'image_sha256': SHA,
        'image': 'main-040000-unpacked.bin',
        'address_space': 'File offsets in this exact image. Literal pointer values are '
                         'observations, never authorised write or call addresses.',
        'method': 'Offline inspection. No firmware execution, no device, no patch.',
        'message_kinds': kinds,
        'bookkeeping': {
            'record_outstanding_file_offset': 0x1511e00,
            'predicates': [
                {'file_offset': 0x1511eca, 'guards_message_number': kinds[0]['message_number'],
                 'returns': '1 while that request is outstanding'},
                {'file_offset': 0x1511efa, 'guards_message_number': kinds[1]['message_number'],
                 'returns': '1 while that request is outstanding'},
                {'file_offset': 0x1511f26, 'guards_message_number': None,
                 'fields_bytes': [80, 81, 82, 84],
                 'returns': '1 while the fourth tracked slot is outstanding'},
            ],
            'meaning_inferred': 'One outstanding request per kind, tracked in one object. '
                                'A per-row preview would need its own slot here or would '
                                'serialise behind an existing one.',
        },
        'request_preparer': {
            'entry_file_offset': 0x1514c7c,
            'auxiliary_getter_call_file_offset': 0x1514d12,
            'skip_when_pending_file_offset': 0x1514d20,
            'skip_when_pending_opcode': int.from_bytes(data[0x1514d20:0x1514d22], 'little'),
            'skip_when_complete_file_offset': 0x1514d24,
            'skip_when_complete_opcode': int.from_bytes(data[0x1514d24:0x1514d26], 'little'),
            'pending_state_value': immediate(data, 0x1514d28)['signed_value'],
            'pending_state_store_file_offset': 0x1514d2a,
            'second_site_file_offsets': [0x1514dfe, 0x1514e00],
            'returns': '1 when the caller must issue a request',
        },
        'request_validator_file_offset': 0x1514e20,
        'request_builder': {
            'entry_file_offset': 0x1411fe8,
            'message_bytes': immediate(data, 0x1412028)['signed_value'],
            'marker': ascii_at(data, pc_literal(data, 0x141202e)['pointer_value'], 8),
            'message_number': built_word(data, 0x1412036, 0x1412038, 0x141203e),
            'message_number_store_file_offset': 0x1412040,
            'identifier_helpers': [pc_literal(data, 0x141205c)['pointer_value'],
                                   pc_literal(data, 0x1412068)['pointer_value']],
            'identifier_fields_bytes': [36, 40],
            'halfword_fields_bytes': [44, 48, 52],
            'send_call_pointer': pc_literal(data, 0x14120b2)['pointer_value'],
        },
        'list_request_sites': {
            'constructor_file_offset': 0x151898a,
            'log_pointer': int.from_bytes(data[0x1518f00:0x1518f04], 'little'),
            'log_text': shift_jis_at(data, int.from_bytes(data[0x1518f00:0x1518f04], 'little')),
            'sites': [{'bsr_file_offset': site, 'mode': mode, 'rows': rows}
                      for site, mode, rows in (
                          (0x15179de, 10, 8), (0x1517a54, 5, 8), (0x1517ac8, 5, 8),
                          (0x1517b2c, 3, 8), (0x1517b90, 9, 8), (0x1517f0a, 14, 8),
                          (0x1517f96, 13, 8), (0x1518026, 18, 8), (0x1518072, 15, 8),
                          (0x15180c2, 19, 8))],
            'meaning_inferred': 'Every inspected request asks for 8 rows, which is the '
                                'slot capacity of a group, not a per-panel field count. '
                                'The browser chooses a mode and takes what comes back, '
                                'so it does not select which fields the INFO panel shows.',
        },
        'completion_file_offset': 0x1514eb8,
        'dispatcher': {
            'file_offset_range': [0x154a3a0, 0x154a4c8],
            'order': ['list-request predicate', 'fourth-slot predicate then completion',
                      'artwork predicate', 'prepare', 'validate', 'build and send'],
            'callers_of_preparer': sorted({pc for entry in pointer_users(data, CODE_BASE + 0x1514c7c)
                                           for pc in entry['candidate_movl_file_offsets']}),
            'callers_of_completion': sorted({pc for entry in pointer_users(data, CODE_BASE + 0x1514eb8)
                                             for pc in entry['candidate_movl_file_offsets']}),
        },
        'not_proven': [
            'what the responder does with the message, and whether it can return anything '
            'but artwork',
            'the cost of an additional request per row',
            'that the browser task may issue a new message kind safely',
            'the meaning of the three halfword fields',
        ],
    }


if __name__ == '__main__':
    report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
    destination = ROOT / 'evidence/row-request-v144.json'
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(destination)
