#!/usr/bin/env python3
"""Hash-locked offline index of the 1.44 stock data surface the integration needs.

Three questions: how the player reads the active Blue/RGB setting, what named
database-client entry points exist, and how an ANLZ section is fetched by tag.
Static inspection only: no firmware execution, no device access, no patch.
"""
import hashlib
import json
import re
from pathlib import Path

from index_browser_path import immediate, pc_literal
from index_hid_dispatch import SHA, pointer_users

ROOT = Path(__file__).resolve().parents[1]
DATA_BASE = 0xa8000000
CODE_BASE = 0x08000000
# Instructions that begin an inspected function in this image.
PROLOGUE = (0x4f22, 0x4f12, 0x4f02)


def ascii_at(data, pointer, limit=64):
    """Resolve a data pointer to its NUL-terminated ASCII string, or None."""
    if not DATA_BASE <= pointer < DATA_BASE + len(data):
        return None
    offset = pointer - DATA_BASE
    end = data.find(b'\x00', offset)
    if end < 0 or end - offset > limit:
        return None
    try:
        return data[offset:end].decode('ascii')
    except UnicodeDecodeError:
        return None


def entry_of(data, pc):
    """Candidate function entry for an instruction: after the preceding RTS.

    Reports None unless the candidate starts with a recognised prologue, so a
    wrong guess is visible instead of being presented as a symbol.
    """
    address = pc & ~1
    while address >= 2:
        address -= 2
        if int.from_bytes(data[address:address + 2], 'little') == 0x000b:
            start = address + 4
            word = int.from_bytes(data[start:start + 2], 'little')
            if word in PROLOGUE or (word & 0xff0f) == 0x2f06:
                return start
            return None
    return None


def named_api(data):
    """Every database-client name in the image, with its diagnostic offset."""
    names = {}
    for pattern in (rb'dbcl_[A-Za-z0-9_]{2,40}', rb'DbReq[A-Za-z0-9_]{2,40}',
                    rb'DbCli[A-Za-z0-9_]{2,40}'):
        for match in re.finditer(pattern, data):
            names.setdefault(match.group().decode(), match.start())
    return [{'name': name, 'string_file_offset': offset}
            for name, offset in sorted(names.items())]


def resolve(data, string_offset, name):
    """Tie one diagnostic string to the function that prints it."""
    users = [pc for entry in pointer_users(data, DATA_BASE + string_offset)
             for pc in entry['candidate_movl_file_offsets']]
    entries = sorted({entry_of(data, pc) for pc in users} - {None})
    return {'name': name, 'string_file_offset': string_offset,
            'diagnostic_movl_file_offsets': sorted(users),
            'entry_file_offset_candidates': entries,
            'callers': sorted({pc for entry in entries
                               for reference in pointer_users(data, CODE_BASE + entry)
                               for pc in reference['candidate_movl_file_offsets']})}


def section_lookup(data):
    """Call sites of the inspected 'give me this ANLZ tag from this file kind'."""
    sites = []
    for jsr in (0x12ac35c, 0x12ac53c, 0x12ac8f0, 0x12acca2, 0x12ad060,
                0x12cbcfe, 0x12cbf94):
        found = {}
        for pc in range(jsr - 24, jsr + 8, 2):
            if pc < 0 or int.from_bytes(data[pc:pc + 2], 'little') & 0xf000 != 0xd000:
                continue
            text = ascii_at(data, pc_literal(data, pc)['pointer_value'], 8)
            if text:
                found[(int.from_bytes(data[pc:pc + 2], 'little') >> 8) & 15] = text
        sites.append({'call_file_offset': jsr,
                      'tag': found.get(6), 'file_kind': found.get(7)})
    return sites


def colour_setting(data):
    """The inspected getter that returns the stored waveform colour preference."""
    return {
        'entry_file_offset': 0x1445274,
        'first_argument_upper_bound': immediate(data, 0x1445276)['signed_value'],
        'first_argument_compare_file_offset': 0x1445278,
        'second_argument_upper_bound_exclusive': immediate(data, 0x1445280)['signed_value'],
        'second_argument_compare_file_offset': 0x1445282,
        'second_argument_rejects_zero_file_offset': 0x144527c,
        'first_argument_stride_bytes': (immediate(data, 0x14452a4)['signed_value'] << 8)
                                       + immediate(data, 0x14452a8, 'add')['signed_value'],
        'second_argument_stride_bytes': immediate(data, 0x14452ac)['signed_value'] & 0xff,
        'table_pointer': pc_literal(data, 0x14452b2)['pointer_value'],
        'state_pointer': pc_literal(data, 0x1445286)['pointer_value'],
        'accepted_values': [1, 3],
        'accept_opcodes': [int.from_bytes(data[0x14452c0:0x14452c2], 'little'),
                           int.from_bytes(data[0x14452c4:0x14452c6], 'little')],
        'default_value': immediate(data, 0x14452ca)['signed_value'],
        'out_of_range_value': immediate(data, 0x14452cc)['signed_value'],
        'callers': sorted({pc for entry in pointer_users(data, CODE_BASE + 0x1445274)
                           for pc in entry['candidate_movl_file_offsets']}),
        'meaning_inferred': 'byte at table + a * 1044 + b * 168, kept only when it is '
                            '1 or 3 and otherwise reported as 1. Value 3 is the RGB '
                            'preference DEVSETTING.DAT also stores as 3.',
    }


def analyze(data):
    if hashlib.sha256(data).hexdigest() != SHA:
        raise ValueError('Unexpected 1.44 application SHA-256')
    resolved = [resolve(data, offset, name) for name, offset in (
        ('dbcl_GetWaveData', 0x917b0), ('dbcl_GetParWaveData', 0x9216c),
        ('dbcl_GetImage', 0x91728), ('dbcl_GetImage2', 0x9176c),
        ('dbcl_RegSdUsbWave', 0x917fc), ('dbcl_GetDecodeInfo', 0x91e14))]
    return {
        'firmware_version': '1.44', 'image_sha256': SHA,
        'image': 'main-040000-unpacked.bin',
        'address_space': 'File offsets in this exact image. Literal pointer values are '
                         'observations, never authorised write or call addresses.',
        'method': 'Offline inspection. No firmware execution, no device, no patch.',
        'colour_setting_getter': colour_setting(data),
        'named_api': named_api(data),
        'resolved_api': resolved,
        'section_lookup': {
            'entry_file_offset': 0x129626c,
            'sites': section_lookup(data),
            'meaning_inferred': 'Resolves one ANLZ tag from one file kind. Every '
                                'inspected site asks the EXT file.',
        },
        'not_proven': [
            'that the local browser row path may call any of these',
            'the calling contract, task, locking and cost of the colour getter',
            'the meaning of the two getter arguments beyond their bounds',
            'that a per-row preview exists in the browser today',
        ],
    }


if __name__ == '__main__':
    report = analyze((ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes())
    destination = ROOT / 'evidence/stock-data-v144.json'
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(destination)
