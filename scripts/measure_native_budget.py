#!/usr/bin/env python3
"""Count the deterministic work of one 80x28 cell, on the owner's real PWV4 data.

Counts only; no timing. Host timings would say nothing about SH7724, but the
number of divisions, compares and stores is a property of the algorithm and
carries over. Reads private copies read-only and verifies every SHA-256 first.
"""
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'private/owner/andrei-sample'
WIDTH = 80
AMPLITUDE_HEIGHT = 27
PWV4_RECORDS = 1200
PWV4_BYTES = PWV4_RECORDS * 6


def sections(buffer):
    """Walk an ANLZ envelope exactly as the host parser does, refusing drift."""
    if buffer[:4] != b'PMAI' or len(buffer) < 12:
        raise ValueError('Not a PMAI envelope')
    header, total = struct.unpack_from('>II', buffer, 4)
    position = header
    while position + 12 <= min(total, len(buffer)):
        tag = buffer[position:position + 4]
        section_header, size = struct.unpack_from('>II', buffer, position + 4)
        if section_header < 12 or size < section_header or position + size > len(buffer):
            raise ValueError('Malformed section')
        yield tag, buffer[position + section_header:position + size]
        position += size


def divide_iterations(numerator, denominator):
    """Iterations of the shift-and-subtract division in native/waveform_prepare.c."""
    if denominator == 0:
        raise ValueError('Zero denominator')
    count, divisor, shift = 0, denominator, 0
    while divisor <= (numerator >> 1):
        divisor <<= 1
        shift += 1
        count += 1
    while shift >= 0:
        count += 1
        divisor >>= 1
        shift -= 1
    return count


def measure(payload):
    """Replicate xdj_prepare_pwv4 and count its work for one cell."""
    if len(payload) != PWV4_BYTES:
        raise ValueError('Expected exactly 1200 six-byte records')
    counts = {'divisions': 0, 'divide_iterations': 0,
              'global_max_records': PWV4_RECORDS, 'inner_compares': 0}
    maximum = 1
    for index in range(PWV4_RECORDS):
        value = max(payload[index * 6 + 3:index * 6 + 6])
        if value > maximum:
            maximum = value
    start = 0
    for column in range(WIDTH):
        # One division per column computes the end of its disjoint interval.
        counts['divisions'] += 1
        counts['divide_iterations'] += divide_iterations(
            (column + 1) * PWV4_RECORDS, WIDTH)
        end = (column + 1) * PWV4_RECORDS // WIDTH
        back = payload[start * 6 + 3:start * 6 + 6]
        front = back
        for index in range(start + 1, end):
            rgb = payload[index * 6 + 3:index * 6 + 6]
            counts['inner_compares'] += 4
            if max(rgb) > max(back):
                back = rgb
            if rgb[2] > front[2]:
                front = rgb
        for value in (max(back), front[2]):
            counts['divisions'] += 1
            counts['divide_iterations'] += divide_iterations(
                value * AMPLITUDE_HEIGHT + (maximum >> 1), maximum)
        for source, level in ((back, 191), (front, 255)):
            layer_maximum = max(source)
            if layer_maximum == 0:
                continue
            for channel in source:
                counts['divisions'] += 1
                counts['divide_iterations'] += divide_iterations(
                    channel * level, layer_maximum)
        start = end
    return counts


def analyze():
    manifest = json.loads((SAMPLE / 'color-manifest.json').read_text())
    totals, files = {}, 0
    for record in manifest['records']:
        if not record['relative'].endswith('.EXT'):
            continue
        buffer = (SAMPLE / record['relative']).read_bytes()
        if hashlib.sha256(buffer).hexdigest() != record['sha256']:
            raise ValueError('Private copy changed since the manifest was written')
        payload = next((body for tag, body in sections(buffer)
                        if tag == b'PWV4' and len(body) >= PWV4_BYTES), None)
        if payload is None:
            continue
        counts = measure(payload[-PWV4_BYTES:])
        files += 1
        for key, value in counts.items():
            totals[key] = totals.get(key, 0) + value
    if not files:
        raise ValueError('No PWV4 payloads measured')
    return {
        'method': 'Operation counts only, replicating native/waveform_prepare.c. '
                  'No timing: host timings do not answer the SH7724 question.',
        'source': 'Owner colour sample, verified by SHA-256 before reading.',
        'files_measured': files,
        'geometry': {'width': WIDTH, 'amplitude_height': AMPLITUDE_HEIGHT,
                     'cell_height': AMPLITUDE_HEIGHT + 1},
        'per_cell_average': {key: round(value / files, 1) for key, value in totals.items()},
        'per_cell_draw': {'pixel_decisions': WIDTH * AMPLITUDE_HEIGHT,
                          'stores': WIDTH * (AMPLITUDE_HEIGHT + 1)},
        'memory_bytes': {
            'prepared_columns_per_row': WIDTH * 6,
            'destination_per_row': WIDTH * (AMPLITUDE_HEIGHT + 1) * 2,
            'pwv4_payload_transient': PWV4_BYTES,
        },
        'not_measured': ['SH7724 cycles', 'cache and memory behaviour on the player',
                         'scheduler impact', 'playback or scrolling'],
    }


if __name__ == '__main__':
    destination = ROOT / 'evidence/native-budget.json'
    destination.write_text(json.dumps(analyze(), indent=2) + '\n')
    print(destination)
