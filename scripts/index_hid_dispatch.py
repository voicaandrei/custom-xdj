#!/usr/bin/env python3
"""Offline, hash-locked HID control-flow index. No device I/O or packet generation."""
import hashlib
import json
from pathlib import Path

from index_firmware import locations

ROOT = Path(__file__).resolve().parents[1]
SHA = '9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0'


def relative_switch(data, table, branch, first, count):
    """Decode an inspected SH MOV.W/BRAF r0 table; displacement is signed bytes.

    BRAF uses its own PC + 4, NOT the table address. Does not infer a switch
    from arbitrary data, execute instructions, or follow computed destinations.
    """
    if (table < 0 or branch < 0 or table % 2 or branch % 2 or count <= 0
            or table + 2 * count > len(data) or branch + 4 > len(data)):
        raise ValueError('Invalid switch bounds/alignment')
    if int.from_bytes(data[branch:branch + 2], 'little') != 0x0023:
        raise ValueError('Expected inspected BRAF r0')
    entries = []
    for index in range(count):
        offset = table + 2 * index
        displacement = int.from_bytes(data[offset:offset + 2], 'little', signed=True)
        target = branch + 4 + displacement
        if target < 0 or target + 2 > len(data) or target % 2:
            raise ValueError('Invalid switch destination')
        entries.append({'selector': first + index, 'entry_file_offset': offset,
                        'target_file_offset': target})
    return entries


def pointer_users(data, pointer):
    """Candidate literal users only. Data can resemble instructions."""
    refs = []
    for pool in locations(data, pointer.to_bytes(4, 'little')):
        if pool % 4:
            continue
        users = []
        for pc in range(max(0, pool - 1024) & ~1, pool, 2):
            instruction = int.from_bytes(data[pc:pc + 2], 'little')
            if (instruction & 0xf000 == 0xd000
                    and ((pc + 4) & ~3) + (instruction & 255) * 4 == pool):
                users.append(pc)
        refs.append({'literal_file_offset': pool, 'candidate_movl_file_offsets': users})
    return refs


def analyze(data):
    if hashlib.sha256(data).hexdigest() != SHA:
        raise ValueError('Unexpected 1.44 application SHA-256')
    switches = []
    for name, table, branch, count in (
        ('resource selection', 0x155d2c8, 0x155d29a, 38),
        ('resource accumulation', 0x155d89c, 0x155d86c, 31),
        ('resource completion', 0x155dc34, 0x155dbc0, 31),
    ):
        switches.append({'name_inferred': name, 'table_file_offset': table,
                         'braf_file_offset': branch,
                         'entries': relative_switch(data, table, branch, 0x2a, count)})
    pointers = [
        ('state gate', 0x0eb23ad4),
        ('field buffer A', 0x0eb29baa), ('field buffer B', 0x0eb29cac),
        ('field buffer C', 0x0eb29dae), ('status report storage', 0x0eb2aac8),
        ('resource 0x2a staging', 0x0ed4c7b8),
        ('resource 0x2a decoded copy', 0x0eb2b354),
        ('resource 0x2b state', 0x0eb2bb84),
        ('resource 0x2e descriptor', 0x0ec2cc94),
        ('field A getter code candidate', 0x0955fb58),
        ('field B getter code candidate', 0x0955fbc6),
        ('field C getter code candidate', 0x0955fc34),
        ('resource 0x2e getter code candidate', 0x0955e7be),
        ('ExWave flag helper code candidate', 0x09444b48),
    ]
    return {
        'image_sha256': SHA, 'firmware_version': '1.44',
        'address_space': 'Offsets are file offsets in main-040000-unpacked.bin. '
                         'pointer_value is an observed literal, not a writable address. '
                         'Code pointer minus 0x08000000 is a candidate mapping; '
                         'do not apply it to data pointers.',
        'method': 'Offline SH4A little-endian static analysis; no firmware execution.',
        'limitations': 'Names are inferred, switch destinations are structural facts. '
                       'Literal scans can match data; no claim of complete call graph, '
                       'safe packet protocol, native browser hook or recovery.',
        'switches': switches,
        'pointers': [{'label_inferred': name, 'pointer_value': pointer,
                      'references': pointer_users(data, pointer)} for name, pointer in pointers],
    }


if __name__ == '__main__':
    data = (ROOT / 'private/extracted/v144/main-040000-unpacked.bin').read_bytes()
    report = analyze(data)
    destination = ROOT / 'evidence/hid-dispatch-v144.json'
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(destination)
