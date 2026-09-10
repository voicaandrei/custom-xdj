#!/usr/bin/env python3
"""Hash-locked static map of the stock local artwork responder. No execution."""
import hashlib
import json
from pathlib import Path

from index_browser_path import immediate, pc_literal
from index_hid_dispatch import SHA
from index_row_request import built_word

ROOT = Path(__file__).resolve().parents[1]


def bsr_target(data, pc):
    if pc < 0 or pc % 2 or pc + 2 > len(data):
        raise ValueError('Invalid BSR offset')
    opcode = int.from_bytes(data[pc:pc + 2], 'little')
    if opcode & 0xf000 != 0xb000:
        raise ValueError('Expected BSR')
    displacement = opcode & 0xfff
    if displacement & 0x800:
        displacement -= 0x1000
    return pc + 4 + 2 * displacement


def analyze(data):
    if hashlib.sha256(data).hexdigest() != SHA:
        raise ValueError('Unexpected 1.44 application SHA-256')
    return {
        'firmware_version': '1.44', 'image_sha256': SHA,
        'image': 'main-040000-unpacked.bin',
        'address_space': 'Code and string offsets are FILE offsets. RAM literals are observations only.',
        'method': 'Static inspection only. No firmware execution, patch or player access.',
        'task': {
            'name': data[0xceca0:0xcecab].rstrip(b'\0').decode('ascii'),
            'name_file_offset': 0xceca0,
            'entry_pointer_file_offset': 0xcec4c,
            'entry_pointer': int.from_bytes(data[0xcec4c:0xcec50], 'little'),
            'state_literal': pc_literal(data, 0x1411db2),
            'receive_file_offset': 0x1411dbc,
            'message_dispatch_file_offset': 0x1411dd0,
            'request_number': built_word(data, 0x1411d98, 0x1411da0, 0x1411dac),
            'request_handler': bsr_target(data, 0x1411dde),
            'completion_handler': bsr_target(data, 0x1411dea),
        },
        'cache_static': {
            'entries': immediate(data, 0x141234a)['signed_value'] << 8,
            'entry_stride_bytes': built_word(data, 0x1412396, 0x1412398, 0x141239a),
            'base': pc_literal(data, 0x1412354),
            'key_compare_literal': pc_literal(data, 0x1412366),
            'state_ready': 1, 'state_pending': 2,
            'hit_response_constructor': bsr_target(data, 0x14123f0),
            'miss_request_constructor': bsr_target(data, 0x1412428),
            'key_caveat': 'Artwork key; not proven to uniquely identify a track or ANLZ preview.',
        },
        'miss_forwarding': {
            'builder': 0x14121a0,
            'message_number': built_word(data, 0x14121fc, 0x1412200, 0x1412202),
            'payload_bytes': immediate(data, 0x1412220)['signed_value'],
            'total_bytes': 152,
            'payload_fields_u16': {'112': '3', '114': 'original request +44',
                                   '116': 'original request +48', '118': 'original request +52'},
            'destination_mailbox_literal': pc_literal(data, 0x1412282),
            'send_file_offset': 0x1412286,
            'still_unknown': 'Three field semantics, track identity and safe preview retrieval.',
        },
        'downstream': {
            'mailbox_alias_a': pc_literal(data, 0x129c04a),
            'mailbox_alias_b': pc_literal(data, 0x129c04c),
            'jpeg_request_handler_literal': pc_literal(data, 0x12bcc34),
            'get_image_literal': pc_literal(data, 0x12a4bc0),
            'get_image_call_file_offset': 0x12a4bcc,
            'get_image_diagnostic_literal': pc_literal(data, 0x1293c7a),
            'get_image_diagnostic': data[0x91728:0x91728 + 13].decode('ascii'),
            'image_request_number': built_word(data, 0x1293c14, 0x1293c18, 0x1293c1e),
            'image_response_number': built_word(data, 0x1293c3c, 0x1293c44, 0x1293c4c),
            'scope': 'Positive local artwork path; does not establish waveform retrieval or track identity.',
        },
        'not_proven': ['need for new message number', 'preview availability for arbitrary selection',
                       'safe replacement of JPEG payload with waveform', 'runtime loader or recovery'],
    }


if __name__ == '__main__':
    report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
    output = ROOT / 'evidence/jpeg-manager-v144.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(output)
