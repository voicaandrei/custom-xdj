#!/usr/bin/env python3
"""Hash-locked offline index of the 1.44 boot/update block. No device or flash access.

This script only reads the already decompressed 0x10000 block and re-extracts the
instructions, tables and literals cited in docs/boot-update.md. It never writes to
a player, never builds an update container and never executes firmware.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Decompressed MAIN block from image offset 0x10000. Identical in 1.44 and 1.45.
SHA = 'a85b616ee2c5958bebb7a59216fa8bc574e9f6f7606120468e89263700e2f8d4'
# Reconstructed MAIN for 1.44: the uncompressed first stage lives at its start.
FIRST_STAGE_SHA = '4d7d55fe7c905c511aaef54fdeddc7f7f5ec2c935a8c9f59404d3dff4dac1f21'
DATA_BASE = 0xa8000000
CODE_BASE = 0x08000000
FLASH_BASE = 0xa0000000
SECTOR_BYTES = 0x20000


def string_at(data, offset, expected):
    """Return an inspected NUL-terminated ASCII string, refusing any drift."""
    end = data.find(b'\x00', offset)
    if end < 0:
        raise ValueError('Unterminated string')
    text = data[offset:end].decode('ascii')
    if text != expected:
        raise ValueError(f'Expected {expected!r} at {offset:#x}, found {text!r}')
    return {'file_offset': offset, 'text': text, 'data_pointer': DATA_BASE + offset}


def literal_users(data, pointer):
    """Candidate PC-relative MOV.L users of a literal. Data can resemble code."""
    needle = pointer.to_bytes(4, 'little')
    refs = []
    position = data.find(needle)
    while position != -1:
        if position % 4 == 0:
            users = []
            for pc in range(max(0, position - 1024) & ~1, position, 2):
                instruction = int.from_bytes(data[pc:pc + 2], 'little')
                if (instruction & 0xf000 == 0xd000
                        and ((pc + 4) & ~3) + (instruction & 255) * 4 == position):
                    users.append(pc)
            refs.append({'literal_file_offset': position,
                         'candidate_movl_file_offsets': users})
        position = data.find(needle, position + 1)
    return refs


def opcode(data, pc, expected):
    """Read one 16-bit instruction word and refuse anything but the inspected one."""
    if pc < 0 or pc % 2 or pc + 2 > len(data):
        raise ValueError('Invalid instruction offset')
    value = int.from_bytes(data[pc:pc + 2], 'little')
    if value != expected:
        raise ValueError(f'Expected {expected:#06x} at {pc:#x}, found {value:#06x}')
    return {'file_offset': pc, 'opcode': value}


def immediate_value(data, pc, expected):
    """Signed 8-bit immediate of an inspected MOV/ADD, refusing any other word."""
    opcode(data, pc, expected)
    value = expected & 255
    return value - 256 if value >= 128 else value


def build_constant(data, steps):
    """Recompute a constant the first-stage boot builds from immediates and shifts.

    Every instruction word is checked against the inspected one, so any drift in
    the image fails instead of silently producing a different address.
    """
    value = 0
    for kind, offset, expected in steps:
        opcode(data, offset, expected)
        immediate = expected & 255
        if kind == 'mov':
            value = immediate - 256 if immediate >= 128 else immediate
        elif kind == 'add':
            value += immediate - 256 if immediate >= 128 else immediate
        elif kind == 'shll8':
            value <<= 8
        elif kind == 'shll16':
            value <<= 16
        else:
            raise ValueError('Unsupported inspected step')
        value &= 0xffffffff
    return value


def sector_table(data, offset, count):
    """Decode an inspected array of 32-bit flash offsets, checking sector spacing."""
    if offset % 4 or offset + 4 * count > len(data):
        raise ValueError('Invalid table bounds')
    entries = [int.from_bytes(data[offset + 4 * i:offset + 4 * i + 4], 'little')
               for i in range(count)]
    for index, value in enumerate(entries):
        if value % SECTOR_BYTES or (index and value - entries[index - 1] != SECTOR_BYTES):
            raise ValueError('Table is not a contiguous sector list')
    return {'table_file_offset': offset, 'entry_count': count,
            'first_flash_offset': entries[0],
            'last_flash_offset': entries[-1],
            'end_flash_offset_exclusive': entries[-1] + SECTOR_BYTES,
            'flash_base_pointer': FLASH_BASE,
            'covers_flash_0': entries[0] == 0}


def analyze(data):
    if hashlib.sha256(data).hexdigest() != SHA:
        raise ValueError('Unexpected 1.44 boot block SHA-256')

    # Root initialisation table: 16-byte entries of [code pointer, name pointer, 0, 0],
    # the same shape already documented for the application image.
    boot_tasks = []
    for code_offset, name_offset, name in (
        (0xa14, 0xa18, 'root'), (0xa1c, 0xa20, 'scif_ini'),
        (0xa2c, 0xa30, 'sh_ini'), (0xa3c, 0xa40, 'shcons_ini'),
        (0xa4c, 0xa50, 'ctmalloc_res_ini'), (0xa5c, 0xa60, 'fsys_conf'),
        (0xa6c, 0xa70, 'usbh_ini'), (0xa7c, 0xa80, 'usbh_msc_driver_ini'),
        (0xa8c, 0xa90, 'usbh_load'), (0xa9c, 0xaa0, 'gui_task_init'),
    ):
        pointer = int.from_bytes(data[name_offset:name_offset + 4], 'little')
        if not DATA_BASE <= pointer < DATA_BASE + len(data):
            raise ValueError('Name pointer outside the inspected block')
        entry = string_at(data, pointer - DATA_BASE, name)
        code_pointer = int.from_bytes(data[code_offset:code_offset + 4], 'little')
        boot_tasks.append({
            'name': name, 'name_pointer_file_offset': name_offset,
            'name_string_file_offset': entry['file_offset'],
            'code_pointer': code_pointer,
            'code_file_offset_candidate': (code_pointer - CODE_BASE
                                           if CODE_BASE <= code_pointer < CODE_BASE + len(data)
                                           else None),
        })

    # Five selectable update components. Only the first name and first label have a
    # direct literal; the rest are reached by fixed stride, so the strides are checked.
    names = [string_at(data, 0x13d2c + 14 * index, text) for index, text in enumerate(
        ('XDJ1KM2G.UPD', 'XDJ1KM2D.UPD', 'XDJ1KM2M.UPD', 'XDJ1KM2P.UPD', 'XDJ1KMK2.UPD'))]
    labels = [string_at(data, 0x13d72 + 17 * index, text) for index, text in enumerate(
        ('XDJ-1000MK2  GUI', 'XDJ-1000MK2 DRIV', 'XDJ-1000MK2 MAIN',
         'XDJ-1000MK2 PANL', 'XDJ-1000MK2  ALL'))]

    messages = {key: string_at(data, offset, text) for key, offset, text in (
        ('emergency_boot', 0xcf4, ' EMERGENCY BOOT MODE '),
        ('converted', 0x13de0, 'Complete Converting S Format.\r\n'),
        ('erased', 0x13e00, 'Complete Erase Flash.\r\n'),
        ('written', 0x13e18, 'Complete Write Data.\r\n'),
        ('bad_checksum', 0x13e34, 'Invalided Checksum.\r\n'),
        ('update_end', 0x13e4e, ' *** Update END ! ***\r\n'),
    )}

    return {
        'firmware_version': '1.44',
        'image': 'main-010000-unpacked.bin',
        'image_sha256': SHA,
        'image_identical_in_1_45': True,
        'address_space': 'All *_file_offset fields are offsets in this exact decompressed '
                         'block. Data pointers observed with base 0xa8000000 and code '
                         'pointers with base 0x08000000; flash offsets are offsets from '
                         '0xa0000000. None of these are authorised write addresses.',
        'method': 'Offline inspection only. No firmware execution, no flash access, '
                  'no update container is produced by this project.',
        'boot_tasks': boot_tasks,
        'update_task': {
            'descriptor_file_offset': 0x13d00,
            'entry_code_pointer': int.from_bytes(data[0x13d08:0x13d0c], 'little'),
            'entry_file_offset_candidate': 0x2f722,
            'priority_field': int.from_bytes(data[0x13d0c:0x13d10], 'little'),
            'stack_field': int.from_bytes(data[0x13d10:0x13d14], 'little'),
            'name': string_at(data, 0x13dc8, 'UpDtae_TASK'),
            'pool_name': string_at(data, 0x13dd4, 'UpDate_mpl'),
            'component_slot_bytes': 144,
            'component_slot_count': 5,
            'component_slot_pointer': int.from_bytes(data[0x2f7b8:0x2f7bc], 'little'),
            'run_condition_file_offset': 0x2f776,
            'update_call_file_offset': 0x2f77a,
        },
        'state_machine': {
            'status_word_pointer': int.from_bytes(data[0x2f0ec:0x2f0f0], 'little'),
            'path_buffer_pointer': int.from_bytes(data[0x2f0e8:0x2f0ec], 'little'),
            'dispatch_head_file_offset': 0x2ede2,
            'tail_file_offset': 0x2f714,
            'tail_delay_pointer': int.from_bytes(data[0x2f7dc:0x2f7e0], 'little'),
            'tail_loops_back_to': 0x2ede2,
            'media_wait': {
                'retry_limit': immediate_value(data, 0x2edf4, 0xec1e),
                'compare_opcode': opcode(data, 0x2edf8, 0x32c3),
                'delay_pointer': int.from_bytes(data[0x2ee54:0x2ee58], 'little'),
                'delay_argument': immediate_value(data, 0x2ee0e, 0xe464),
                'status_on_exhaustion': 128,
            },
            'name_scan': {
                'iterations': immediate_value(data, 0x2eed8, 0xeb05),
                'loop_end_file_offset': 0x2ef2e,
                'name_stride_step': immediate_value(data, 0x2ef32, 0x7a0e),
                'slot_stride_steps': [immediate_value(data, 0x2ef30, 0x7c7f),
                                      immediate_value(data, 0x2ef36, 0x7c11)],
                'first_name_pointer': int.from_bytes(data[0x2f0fc:0x2f100], 'little'),
                'slot_base_pointer': int.from_bytes(data[0x2f110:0x2f114], 'little'),
                'match_counter_field_bytes': 16,
                'match_counter_cap': 5,
            },
            'completion': {
                'status_file_offset': 0x2f6d4,
                'status_value': 255,
                'message_pointer': int.from_bytes(data[0x2f7d0:0x2f7d4], 'little'),
            },
            'observed_error_status_values': [128, 133, 134, 135, 137],
            'reset_register_users': {
                'wdt_counter': literal_users(data, 0xa4520000),
                'wdt_control': literal_users(data, 0xa4520004),
            },
            'interpretation': 'INFERRED: without a usable medium the routine sets an error '
                              'status and keeps cycling through its delay. No watchdog or '
                              'reset register is referenced anywhere in this block, so it '
                              'does not reboot the unit. What the graphics task shows for '
                              'each status value was not followed.',
        },
        'components': [
            {'index': index, 'update_filename': names[index], 'label': labels[index]}
            for index in range(5)
        ],
        'component_name_stride_bytes': 14,
        'component_label_stride_bytes': 17,
        'erase_profiles': {
            'selector_0': sector_table(data, 0x1464, 8),
            'selector_1': sector_table(data, 0x128c, 118),
            'selector_2': sector_table(data, 0x1284, 120),
        },
        'erase_entry_file_offset': 0x1eaf8,
        'write_entry_file_offset': 0x1ec90,
        'erase_selector_dispatch_file_offsets': {'0': 0x1eb1a, '1': 0x1eb68, '2': 0x1ebf2},
        'selector_decision': {
            'function_file_offset': 0x2e82e,
            'read_byte_offset_in_record': 31,
            'compare_opcode': opcode(data, 0x2e832, 0x8831),
            'compared_ascii': '1',
            'value_when_equal': 2,
            'value_otherwise': 1,
            # The same test is inlined on the path that actually calls erase/write.
            'inline_site': {
                'record_pointer_literal_load_file_offset': 0x2f448,
                'record_pointer': int.from_bytes(data[0x2f614:0x2f618], 'little'),
                'immediate_31': opcode(data, 0x2f44a, 0xe01f),
                'record_dereference': opcode(data, 0x2f44c, 0x6512),
                'byte_load': opcode(data, 0x2f44e, 0x005c),
                'compare_opcode': opcode(data, 0x2f450, 0x8831),
                'selector_to_stack_file_offset': 0x2f45e,
                'selector_from_stack_file_offset': 0x2f46c,
                'erase_write_dispatch_file_offset': 0x2f472,
            },
            # The same pointer is set from a per-component pointer array, and the
            # CRC is computed over the block it points at.
            'record_pointer_store_file_offset': 0x2f328,
            'record_index_scale_file_offset': 0x2f31a,
            'checksum_call_file_offset': 0x2f346,
            'interpretation': 'INFERRED: the record is the component blob whose CRC is '
                              'verified, so byte 31 is the last byte of its 32-byte '
                              'label. The official 1.44 MAIN label ends with \'0\' and '
                              'PANL with a space, so neither selects profile 2. The '
                              'container filename plays no part: the choice is per '
                              'component label.',
        },
        'checksum': {
            'function_file_offset': 0x2e994,
            'polynomial_literal_file_offset': 0x2eb90,
            'polynomial_literal_value': int.from_bytes(data[0x2eb90:0x2eb94], 'little'),
            'polynomial': 0x1021,
            'test_bit': 1 << 24,
            'trailing_zero_bytes': 2,
            'final_shift_right_bits': 8,
            'equals': 'CRC-16/XMODEM, the same trailer check scripts/extract_upd.py '
                      'already reproduces offline.',
            'mismatch_message_users': literal_users(data, DATA_BASE + 0x13e34),
        },
        'flash_command_addresses': {
            'unlock_1': int.from_bytes(data[0x1ed00:0x1ed04], 'little'),
            'unlock_2': int.from_bytes(data[0x1ed04:0x1ed08], 'little'),
            'note': 'Standard two-cycle NOR unlock addresses observed as literals. '
                    'Not a programming procedure and not executed here.',
        },
        'messages': messages,
        'message_users': {key: literal_users(data, value['data_pointer'])
                          for key, value in messages.items()},
        'not_proven': [
            'the trigger that enters the update or emergency path without the application',
            'that no signature or acceptance check exists outside the inspected path',
            'which component index the stock updater maps to each erase selector',
            'that the flash part on the unit matches this driver',
            'any recovery actually performed or observed on hardware',
        ],
    }


def analyze_first_stage(data):
    """The uncompressed boot in MAIN: which block it loads, and what it does on failure."""
    if hashlib.sha256(data).hexdigest() != FIRST_STAGE_SHA:
        raise ValueError('Unexpected 1.44 reconstructed MAIN SHA-256')
    application_source = build_constant(data, (
        ('mov', 0x824, 0xe4a0), ('shll8', 0x828, 0x4418),
        ('add', 0x82c, 0x7404), ('shll16', 0x830, 0x4428)))
    fallback_source = build_constant(data, (
        ('mov', 0xb82, 0xe4a0), ('shll8', 0xb86, 0x4418),
        ('add', 0xb8a, 0x7401), ('shll16', 0xb92, 0x4428)))
    fallback_bytes = build_constant(data, (
        ('mov', 0xb84, 0xe603), ('shll16', 0xb8e, 0x4628)))
    destinations = [build_constant(data, (
        ('mov', load, 0xe5a8), ('shll8', byte_shift, 0x4518),
        ('shll16', word_shift, 0x4528)))
        for load, byte_shift, word_shift in ((0xb98, 0xb9c, 0xba0),
                                             (0xbb4, 0xbb6, 0xbc4))]
    branch = opcode(data, 0xb7e, 0x8d18)
    branch_target = 0xb7e + 4 + 2 * (branch['opcode'] & 255)
    return {
        'image': 'main.bin',
        'image_sha256': FIRST_STAGE_SHA,
        'address_space': 'File offsets in the reconstructed MAIN image, which is also '
                         'the flash offset space: the component base address is 0 and '
                         'the S-record entry is 0xa0000000.',
        'decompressor': {
            'flash_source': int.from_bytes(data[0x8a0:0x8a4], 'little'),
            'ram_destination': int.from_bytes(data[0x89c:0x8a0], 'little'),
            'copied_bytes': 0x1000,
            'entry_literal_file_offset': 0x8ac,
            'entry_value': int.from_bytes(data[0x8ac:0x8b0], 'little'),
        },
        'early_boot_flow': {
            'gpio_initialization_call': opcode(data, 0x30c, 0xb051),
            'gpio_initialization_returns_zero': opcode(data, 0x4ba, 0x6043),
            'memory_test_call': opcode(data, 0x388, 0xb0c9),
            'loader_tail_branch': opcode(data, 0x3ae, 0xa235),
            'loader_entry_file_offset': 0x81c,
            'argument_forwarding': [opcode(data, pc, word) for pc, word in (
                (0x826, 0x6d63), (0x82e, 0x6c53), (0x864, 0x64c3),
                (0x878, 0x65dc), (0xbe4, 0x6483), (0xbf0, 0x659c))],
            'scope': 'Inspected flow 0x300 -> GPIO setup 0x3b2 -> RAM test '
                     '0x51e -> loader 0x81c. No forced-update decision established '
                     'on this flow. Forwarded arguments are not evidence of a '
                     'button-controlled fallback. Does not exclude other routes.',
        },
        'staging_ram': int.from_bytes(data[0x894:0x898], 'little'),
        'application_block': {
            'flash_source': application_source,
            'source_build_file_offsets': [0x824, 0x828, 0x82c, 0x830],
            'copy_call_file_offset': 0x844,
        },
        'checksum_gate': {
            'stored_checksum_read_file_offsets': [0xb0e, 0xb16],
            'sum_loop_file_offsets': [0xb46, 0xb68],
            'compare_file_offset': 0xb7c,
            'branch_file_offset': 0xb7e,
            'match_target_file_offset': branch_target,
            'kind': '16-bit byte sum over header and packed stream, stored little-endian '
                    'right after the stream. Same block checksum scripts/unpack_main.py '
                    'already verifies offline; not the CRC-16 of the update container.',
        },
        'fallback_block': {
            'flash_source': fallback_source,
            'source_build_file_offsets': [0xb82, 0xb86, 0xb8a, 0xb92],
            'copied_bytes': fallback_bytes,
            'copy_call_file_offset': 0xb90,
            'taken_when': 'the application block checksum does not match',
            'checksum_verified_before_use': False,
        },
        'decompress_destinations': destinations,
        'entry_table': {
            'table_pointer_literal_file_offset': 0xc30,
            'table_pointer_value': int.from_bytes(data[0xc30:0xc34], 'little'),
            'entries': [int.from_bytes(data[offset:offset + 4], 'little')
                        for offset in (0xc34, 0xc38)],
            'dispatch_file_offset': 0xbec,
        },
        'consequence_inferred': 'An application block with a mismatched checksum makes the first stage load '
                               'and run the block at the fallback address instead. That '
                               'block is the updater. No button combination, console or '
                               'working application is involved in this path.',
        'not_proven': [
            'recovery from an application that passes checksum but hangs after launch',
            'behaviour observed on hardware; this is the official image only',
            'that the updater then completes an update without user interaction',
            'that nothing else can leave the unit unbootable',
            'that the fallback block itself is ever validated',
        ],
    }


if __name__ == '__main__':
    report = analyze((ROOT / 'private/extracted/v144/main-010000-unpacked.bin').read_bytes())
    report['first_stage'] = analyze_first_stage(
        (ROOT / 'private/extracted/v144/main.bin').read_bytes())
    destination = ROOT / 'evidence/boot-update-v144.json'
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(destination)
