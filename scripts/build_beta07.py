#!/usr/bin/env python3
"""Build Test 07 using the normalized track ID already in the artwork request."""

import json
from pathlib import Path

import build_beta06 as base


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "private/browser-waveform-beta-v144-test07"
MARKER_TEXT = "XDJ BETA 07".encode("utf-16le")
SOURCES = (
    ROOT / "native/beta_runtime_trace.c",
    ROOT / "native/waveform_prepare.c",
    ROOT / "native/waveform_cell.c",
    ROOT / "native/pixel_channels.c",
    ROOT / "native/v144/beta07_hooks.S",
)
HASH_SOURCES = SOURCES + (
    ROOT / "native/beta_runtime.c",
    ROOT / "native/v144/beta06_hooks.S",
)


def configure():
    base.FOLDER = FOLDER
    base.MARKER_TEXT = MARKER_TEXT
    base.SOURCES = SOURCES
    base.HASH_SOURCES = HASH_SOURCES


def link_beta(destination, application_length):
    saved = (base.FOLDER, base.MARKER_TEXT, base.SOURCES, base.HASH_SOURCES)
    try:
        configure()
        return base.link_beta(destination, application_length)
    finally:
        base.FOLDER, base.MARKER_TEXT, base.SOURCES, base.HASH_SOURCES = saved


def build(destination=FOLDER):
    saved = (base.FOLDER, base.MARKER_TEXT, base.SOURCES, base.HASH_SOURCES)
    try:
        configure()
        report = base.build(destination)
    finally:
        base.FOLDER, base.MARKER_TEXT, base.SOURCES, base.HASH_SOURCES = saved
    report["kind"] = "test-07-request-identity-waveform-beta-v1"
    report["text_marker"] = "XDJ BETA 07"
    report["identity_source"] = {
        "request_offsets": [36, 40],
        "numeric_track_id_offset": 40,
        "evidence": "stock helpers 0x1445c90/0x1445c94 read the two words; the second word is the numeric identifier",
        "test06_correction": "no dependency on DbReqJpegData context type or its branch-specific row table",
    }
    report["hardware_evidence_before_test07"] = {
        "test05": "decoder and both bounded surface writes confirmed; retained trace stage 1",
        "test06": "blue strip with zero white bars; relevant request did not use context type 1",
    }
    report["known_beta_limits"] = [
        "Rows without an artwork request retain stock appearance.",
        "A blue strip with white bars is diagnostic output, not a waveform.",
        "The normalized request identifier is confirmed structurally; its numeric word as main track ID still needs this device test.",
        "Blue uses selector zero; this exact selector still needs device validation.",
        "The feature is always enabled in Test 07; the optional toggle follows data-path validation.",
        "Recovery from a checksum-valid application hang remains unverified.",
    ]
    payload = json.dumps(report, indent=2) + "\n"
    (destination / "manifest.json").write_text(payload)
    (ROOT / "evidence/browser-waveform-beta-v144-test07.json").write_text(payload)
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
