#!/usr/bin/env python3
"""Cross-compile the project's own C units for SH-4A and report what they need.

Compiles and combines relocatable project objects. It never links a firmware image, never produces
an update container and never touches a player. The result answers two
questions: does our code build for the target at all, and does it need anything
the target has no library for.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNITS = ('waveform_cell', 'waveform_prepare', 'pixel_channels', 'waveform_adapter', 'track_key', 'waveform_dbserver', 'surface_adapter', 'blue_request', 'rgb_request', 'browser_row', 'preview_queue')
# SH7724 is SH-4A with an FPU, but none of our code uses floating point. Building
# without it means the adapter never has to save or restore FPU state.
FLAGS = ('-m4a-nofpu', '-ml', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
         '-ffreestanding', '-fno-builtin')
PREFIX = 'sh-elf-'
LOCAL_BIN = Path.home() / '.local/sh-elf/bin'


def toolchain():
    """Locate the cross toolchain, preferring an explicit local install."""
    search = os.environ.get('PATH', '')
    if LOCAL_BIN.is_dir():
        search = f'{LOCAL_BIN}{os.pathsep}{search}'
    found = {name: shutil.which(PREFIX + name, path=search)
             for name in ('gcc', 'nm', 'size')}
    return None if any(value is None for value in found.values()) else found


def build(destination):
    tools = toolchain()
    if tools is None:
        raise FileNotFoundError(f'{PREFIX}gcc, {PREFIX}nm and {PREFIX}size are required')
    version = subprocess.run([tools['gcc'], '--version'], check=True,
                             capture_output=True, text=True).stdout.splitlines()[0]
    units = []
    for name in UNITS:
        obj = destination / (name + '.o')
        subprocess.run([tools['gcc'], *FLAGS, '-I', str(ROOT / 'native'),
                        str(ROOT / 'native' / (name + '.c')), '-c', '-o', str(obj)],
                       check=True, capture_output=True, text=True)
        # nm prints "<type> <name>" per line; take the name and drop the
        # object-format underscore prefix so the comparison is on our own names.
        undefined = [line.split()[-1].lstrip('_')
                     for line in subprocess.run([tools['nm'], '-u', str(obj)], check=True,
                                                capture_output=True, text=True
                                                ).stdout.splitlines() if line.split()]
        sizes = subprocess.run([tools['size'], str(obj)], check=True,
                               capture_output=True, text=True).stdout.splitlines()
        columns = sizes[1].split() if len(sizes) > 1 else []
        units.append({
            'unit': name,
            'undefined_symbols': sorted(undefined),
            'text_bytes': int(columns[0]) if columns else None,
            'data_bytes': int(columns[1]) if len(columns) > 1 else None,
            'bss_bytes': int(columns[2]) if len(columns) > 2 else None,
        })
    combined = destination / 'xdj-native-core.o'
    subprocess.run([tools['gcc'], '-m4a-nofpu', '-ml', '-nostdlib', '-Wl,-r',
                    *[str(destination / (name + '.o')) for name in UNITS],
                    '-o', str(combined)], check=True, capture_output=True, text=True)
    linked_undefined = subprocess.run([tools['nm'], '-u', str(combined)], check=True,
                                     capture_output=True, text=True).stdout.splitlines()
    if linked_undefined:
        raise ValueError('Combined native core has unresolved symbols: ' + repr(linked_undefined))
    external = sorted({symbol for unit in units for symbol in unit['undefined_symbols']
                       if not symbol.startswith('xdj_')})
    return {
        'target': 'sh-elf',
        'compiler': version,
        'flags': list(FLAGS),
        'method': 'Compilation and relocatable link of own C units. No firmware image or device access.',
        'combined_undefined_symbols': linked_undefined,
        'units': units,
        'total_text_bytes': sum(unit['text_bytes'] or 0 for unit in units),
        'symbols_outside_this_project': external,
        'needs_compiler_runtime': bool(external),
        'not_proven': [
            'that this code is correct on the device',
            'that these sizes hold inside a firmware image with its own ABI',
            'anything about timing on SH7724',
        ],
    }


if __name__ == '__main__':
    import tempfile
    with tempfile.TemporaryDirectory(prefix='xdj-sh-build-') as temporary:
        report = build(Path(temporary))
    target = ROOT / 'evidence/sh-build.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(target)
