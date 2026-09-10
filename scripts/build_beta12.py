#!/usr/bin/env python3
"""Test 12: package tested next runtime on the unchanged Test 11 hook contract."""
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'private/browser-waveform-beta-v144-test12'
spec=importlib.util.spec_from_file_location('_beta12_base',ROOT/'scripts/build_beta11.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
base.MARKER_TEXT='XDJ BETA 12'.encode('utf-16le')
base.core.MARKER_TEXT=base.MARKER_TEXT
base.core.SOURCES=tuple(
    ROOT/'native/beta_runtime_next.c' if p.name=='beta_runtime_band.c' else
    ROOT/'native/waveform_prepare_fast.c' if p.name=='waveform_prepare.c' else p
    for p in base.core.SOURCES)
base.core.HASH_SOURCES=tuple(dict.fromkeys((*base.core.HASH_SOURCES,*base.core.SOURCES,
    ROOT/'native/waveform_prepare_fast.h',ROOT/'scripts/build_beta12.py')))
PATCHES=base.PATCHES
COPY_OFFSET,COPY_BEFORE=base.COPY_OFFSET,base.COPY_BEFORE
KEY_ENTRY_OFFSET,KEY_ENTRY_BEFORE=base.KEY_ENTRY_OFFSET,base.KEY_ENTRY_BEFORE
link_beta=base.link_beta
patch_application=base.patch_application

def build(destination=FOLDER):
    report=base.build(destination)
    report['kind']='test-12-optimized-preparation-waveform-beta'
    report['text_marker']='XDJ BETA 12'
    report['preparation']={
        'shared_rgb_normalization':True,'incremental_bucket_boundaries':True,
        'invalidate_before_rejecting_payload':True,
        'row_width':80,'row_height':28,'info_width':290,'info_height':28,
        'task_identity_and_serialization_changed':False,
        'pixel_parity_with_test11_verified_locally':True}
    report['limits'][0]='Test 09 RGB/audio confirmed by owner; Test 11/12 scroll, note and INFO changes await hardware validation.'
    report['limits'].append('160px layout is not included. Preparation optimization is not a proven fix for task concurrency.')
    (destination/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    report=build()
    (ROOT/'evidence/browser-waveform-beta-v144-test12.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
