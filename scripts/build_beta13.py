#!/usr/bin/env python3
"""Test 13: aligned INFO allocation and deferred artwork dispatch while scrolling."""
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'private/browser-waveform-beta-v144-test13'
spec=importlib.util.spec_from_file_location('_beta13_base',ROOT/'scripts/build_beta11.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
base.MARKER_TEXT='XDJ BETA 13'.encode('utf-16le')
base.core.MARKER_TEXT=base.MARKER_TEXT
base.core.SOURCES=tuple(
    ROOT/'native/beta_runtime_next.c' if p.name=='beta_runtime_band.c' else
    ROOT/'native/waveform_prepare_fast.c' if p.name=='waveform_prepare.c' else
    ROOT/'native/beta_info_band_aligned.c' if p.name=='beta_info_band.c' else p
    for p in base.core.SOURCES)
base.core.SOURCES += (ROOT/'native/beta_browse_settle.c',)
base.PATCHES[0x154a5ac] = (0x09514c7c, '_xdj_beta_browse_prepare')
base.core.HASH_SOURCES=tuple(dict.fromkeys((*base.core.HASH_SOURCES,*base.core.SOURCES,
    ROOT/'native/waveform_prepare_fast.h',ROOT/'scripts/build_beta13.py',
    ROOT/'scripts/index_beta13_contract.py')))
PATCHES=base.PATCHES
COPY_OFFSET,COPY_BEFORE=base.COPY_OFFSET,base.COPY_BEFORE
KEY_ENTRY_OFFSET,KEY_ENTRY_BEFORE=base.KEY_ENTRY_OFFSET,base.KEY_ENTRY_BEFORE
link_beta=base.link_beta
patch_application=base.patch_application

def build(destination=FOLDER):
    from index_beta13_contract import inspect
    contract=inspect()
    report=base.build(destination)
    report['kind']='test-13-aligned-info-and-browse-settle'
    report['text_marker']='XDJ BETA 13'
    report['info_band']['surface_width']=292
    report['info_band']['source_stride_bytes']=580
    report['info_band']['destination_stride_bytes']=584
    report['info_band']['position_status']='Owner confirms position in Test 12; aligned surface requires Test 13 validation.'
    report['browse_settle']={'quiet_ticks':250, 'scope':'UI artwork dispatch before stock preparation', 'no_sleep':True, 'pending_state_untouched_while_deferred':True, 'hardware_validated':False}
    report['stock_contract']=contract
    report['preparation']={
        'shared_rgb_normalization':True,'incremental_bucket_boundaries':True,
        'invalidate_before_rejecting_payload':True,
        'row_width':80,'row_height':28,'info_width':290,'info_height':28,
        'task_identity_and_serialization_changed':False,
        'pixel_parity_with_test11_verified_locally':True}
    report['limits'][0]='Owner Test 12: INFO placement correct but skewed; fast scroll still fails with INFO open and closed. Test 13 is an unvalidated fix candidate.'
    report['limits'].append('160px layout is not included. Preparation optimization is not a proven fix for task concurrency.')
    (destination/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    report=build()
    (ROOT/'evidence/browser-waveform-beta-v144-test13.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
