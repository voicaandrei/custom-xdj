#!/usr/bin/env python3
"""Build only project extension in private/, with next preparation/runtime.

Uses existing hash-locked linker/ABI; does not rebuild, patch or package MAIN,
create an UPD, copy anything to USB, or execute any firmware.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
from build_sh import toolchain

ROOT=Path(__file__).resolve().parents[1]

def check(folder):
    frozen=json.loads((ROOT/'evidence/browser-waveform-beta-v144-test11.json').read_text())
    update=ROOT/'private/browser-waveform-beta-v144-test11/XDJ1KMK2.UPD'
    if hashlib.sha256(update.read_bytes()).hexdigest()!=frozen['update_sha256']:
        raise ValueError('Frozen BETA 11 UPD changed')
    for name,sha in frozen['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha:
            raise ValueError(f'Frozen BETA 11 source changed: {name}')
    spec=importlib.util.spec_from_file_location('_next_beta11_linker',ROOT/'scripts/build_beta11.py')
    linker=importlib.util.module_from_spec(spec);spec.loader.exec_module(linker)
    linker.core.SOURCES=tuple(
        ROOT/'native/beta_runtime_next.c' if p.name=='beta_runtime_band.c' else
        ROOT/'native/waveform_prepare_fast.c' if p.name=='waveform_prepare.c' else p
        for p in linker.core.SOURCES)
    linker.core.HASH_SOURCES=linker.core.SOURCES+tuple(ROOT/p for p in (
        'native/waveform_prepare_fast.h','native/waveform_prepare.h','native/beta_runtime.h',
        'native/waveform_cell.h','native/pixel_channels.h','scripts/check_next_runtime.py'))
    # Same placement as the frozen image; this is a local extension only.
    linked=linker.link_beta(folder,0x1bea1d4)
    tools=toolchain()
    elf=folder/'browser-waveform-beta06.elf'
    symbols=linker.core.run([tools['nm'],'-u',str(elf)]).strip()
    if symbols: raise ValueError(f'Unresolved symbols: {symbols}')
    report={
        'scope':'local next extension only, not a firmware update or device validation',
        'frozen_test11_update_sha256':frozen['update_sha256'],
        'frozen_sources_unchanged':True,
        'frozen_update_unchanged':True,
        'remaining_relocations':linked['remaining_relocations'],
        'extension_bytes':len(linked['payload']),
        'extension_sha256':linked['payload_sha256'],
        'frozen_test11_extension_bytes':frozen['extension_bytes'],
        'extension_size_delta':len(linked['payload'])-frozen['extension_bytes'],
        'unresolved_symbols':[],
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in linker.core.HASH_SOURCES},
        'changes':['exact bucket stepping','shared RGB normalization for INFO and row',
                   'invalidate before rejecting malformed payloads'],
        'limits':['task handoff identity and serialization unchanged',
                  'BROWSE still 80x28; 160px requires surface/copy/layout work',
                  'no SH7724 execution timing measured','not an installable update'],
    }
    return report

if __name__=='__main__':
    import tempfile
    with tempfile.TemporaryDirectory(prefix='next-extension-',dir=ROOT/'private') as tmp:
        report=check(Path(tmp))
    output=ROOT/'evidence/next-runtime-build.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(output)
