#!/usr/bin/env python3
"""Host-only probes, width budgets and immutable Test 11 hash verification."""
import hashlib
import json
import platform
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATE = ROOT / 'private/browser-waveform-beta-v144-test11/XDJ1KMK2.UPD'
UPDATE_SHA = '51bbf8885bde90128b807a23127e65022fbd0ae401db79ee1f821a43f1111255'
SOURCES = ['native/beta_runtime_band.c', 'native/waveform_prepare.c',
           'native/waveform_cell.c', 'native/pixel_channels.c',
           'scripts/probes/beta11_runtime_review.c']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review():
    frozen = json.loads((ROOT/'evidence/browser-waveform-beta-v144-test11.json').read_text())
    def verify_frozen_sources():
        for name, expected in frozen['source_sha256'].items():
            if sha(ROOT/name) != expected:
                raise ValueError(f'Test 11 source changed: {name}')
    verify_frozen_sources()
    if sha(UPDATE) != UPDATE_SHA:
        raise ValueError('Test 11 candidate changed; refusing this review anchor')
    outputs = {}
    with tempfile.TemporaryDirectory() as tmp:
        for mode in ('ubsan', 'release'):
            binary = Path(tmp) / mode
            flags = ['-O2'] if mode == 'release' else [
                '-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all']
            subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                *flags, '-I', str(ROOT/'native'),
                *[str(ROOT/s) for s in SOURCES], '-o', str(binary)],
                check=True, capture_output=True, timeout=30)
            outputs[mode] = json.loads(subprocess.run([str(binary)], check=True,
                capture_output=True, text=True, timeout=30).stdout)
    # Verify an inexpensive alternative to one software division per bucket:
    # exact quotient/remainder stepping for EVERY supported width and bucket.
    checked = 0
    for samples in (400, 1200):
        for width in range(1, samples+1):
            step, extra = divmod(samples, width)
            end = remainder = 0
            for x in range(width):
                end += step
                remainder += extra
                if remainder >= width:
                    end += 1
                    remainder -= width
                if end != (x+1)*samples//width:
                    raise AssertionError('Bucket boundary mismatch')
                checked += 1
    if sha(UPDATE) != UPDATE_SHA:
        raise ValueError('Test 11 candidate changed during review')
    verify_frozen_sources()
    return {
        'scope': 'host-only project C; no firmware execution, USB writes or player access',
        'candidate_update_sha256': UPDATE_SHA,
        'candidate_unchanged': True,
        'all_frozen_build_sources_unchanged': True,
        'source_sha256': {s: sha(ROOT/s) for s in SOURCES},
        'host': platform.platform(),
        'compiler': subprocess.run(['cc','--version'], check=True,
            capture_output=True,text=True).stdout.splitlines()[0],
        'probes': {k: v for k,v in outputs['ubsan'].items()
                   if not k.startswith('host_median')},
        'ubsan_passed': True,
        'host_timings': outputs['release']['host_median_cpu_us_per_prepare_draw_pair'],
        'timing_limits': 'Synthetic payloads, 7 rounds x 500 pairs, median CPU time; excludes firmware, IO, JPEG, handoff copies, scheduler and compositor. Not SH-4 timings or FPS.',
        'bucket_boundary_equivalence_checks': checked,
        'width_budgets': [{
            'width': w, 'height': 28, 'row_bytes': w*28*2,
            'extra_row_bytes': (w-80)*28*2,
            'pair_bytes': (w+290)*28*2,
            'pair_pixel_increase_percent': round((w-80)/370*100,2),
            'seven_surface_extra_bytes': 7*(w-80)*28*2,
            'fits_current_row_copy': w == 80,
            'hypothetical_512_slot_extra_bytes': 512*(w-80)*28*2,
        } for w in (80,120,160)],
        'limits': [
            'The probe sequences do not prove the player permits overlapping requests.',
            'The current assembly resets before preparation; invalid-input probe isolates the C API.',
            'Pixel/copy budgets exclude alignment, graphics allocation and other replicas.',
            '512-slot expansion is a hypothetical cost, not a recommended memory layout.',
            'No wider on-device layout or new firmware was implemented by this audit.',
        ],
    }


if __name__ == '__main__':
    destination = ROOT / 'evidence/beta11-performance-review.json'
    destination.write_text(json.dumps(review(), indent=2)+'\n')
    print(destination)
