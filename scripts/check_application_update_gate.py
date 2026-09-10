#!/usr/bin/env python3
"""Verify the v1.44 MAIN same-version gate from exact SH instructions.

This is bounded static analysis. It neither executes firmware nor proves which
path the physical player took.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHA = "9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0"
ROUTINE_START = 0x15571EA
MAIN_BRANCH = 0x15572F8
FORCE_BRANCH = 0x1557308
RETURN_JOIN = 0x155734A


def parse_numeric_version(label: bytes) -> int:
    if len(label) != 32:
        raise ValueError("Component label must be exactly 32 bytes")
    digits = []
    for offset in (19, 21, 22, 23):
        value = label[offset]
        digits.append(value - 48 if 48 <= value <= 57 else 0)
    return digits[0] * 1000 + digits[1] * 100 + digits[2] * 10 + digits[3]


def main_gate(label: bytes, installed_version: int, runtime_flag: int = 0) -> int:
    """Model the normal return values: 2=skip, 3=process."""
    candidate = parse_numeric_version(label)
    if installed_version < candidate:
        return 3
    if label[23] == 43 or label[24] == 43:
        return 3
    return 3 if runtime_flag == 1 else 2


def verify(data: bytes) -> dict:
    if hashlib.sha256(data).hexdigest() != SHA:
        raise ValueError("Wrong v1.44 MAIN application")

    exact = {
        # Dispatch component kind 3 to the MAIN gate.
        0x1557296: bytes.fromhex("03882e89"),
        # Get installed MAIN version, compare installed >= candidate.
        0x15572F8: bytes.fromhex("49d10b4109000d64e234018921a003e0"),
        # Fixed offsets 23 and 24; either '+' reaches process return 3.
        0x1557326: bytes.fromhex(
            "17e0dc002b88038918e0dc002b88038b08a003e0"
        ),
        # Default return 2 unless runtime flag equals 1; shared return tail.
        0x155733E: bytes.fromhex(
            "3ad661500188018f02e003e0047f164f264ff66e0b00f66d"
        ),
        # Caller: result 2 clears the component and decrements pending count;
        # any other result sets component state 3.
        0x15586A6: bytes.fromhex(
            "7cd30b43b3646a020288e9220c8f6a4279d802e4411d00e0"
            "d68185521542018bff72251803a064e503e2211d01e5"
        ),
    }
    for offset, expected in exact.items():
        actual = data[offset : offset + len(expected)]
        if actual != expected:
            raise ValueError(f"Gate bytes changed at FILE {offset:#x}")

    installed_getter_pointer = int.from_bytes(data[0x1557420:0x1557424], "little")
    runtime_flag_pointer = int.from_bytes(data[0x1557428:0x155742C], "little")
    if installed_getter_pointer != 0x09446A3A:
        raise ValueError("Unexpected installed-version getter")
    if runtime_flag_pointer != 0x0D5C4930:
        raise ValueError("Unexpected runtime-force flag")

    stock = b"XDJ-1000MK2 MAINVer1.44\0       0"
    forced = bytearray(stock)
    forced[24] = ord("+")
    if parse_numeric_version(stock) != parse_numeric_version(bytes(forced)):
        raise ValueError("Force marker changed numeric version")
    if main_gate(stock, 1440, 0) != 2:
        raise ValueError("Stock same-version case must skip in the model")
    if main_gate(bytes(forced), 1440, 0) != 3:
        raise ValueError("Padding force marker must process in the model")

    return {
        "application_sha256": SHA,
        "address_space": "FILE offsets in decompressed v1.44 MAIN application",
        "routine_start": ROUTINE_START,
        "main_branch": MAIN_BRANCH,
        "force_branch": FORCE_BRANCH,
        "return_join": RETURN_JOIN,
        "installed_version_getter_code_pointer": installed_getter_pointer,
        "runtime_force_flag_data_pointer": runtime_flag_pointer,
        "component_label_force_offset": 24,
        "component_label_force_byte": "+",
        "numeric_version_before": 1440,
        "numeric_version_after": 1440,
        "same_version_default_result": 2,
        "same_version_forced_result": 3,
        "caller_result_2_semantics": "clear component and decrement pending count",
        "caller_other_result_semantics": "set component state 3 for processing",
        "hardware_path_observed": False,
    }


if __name__ == "__main__":
    report = verify(
        (ROOT / "private/extracted/v144/main-040000-unpacked.bin").read_bytes()
    )
    (ROOT / "evidence/application-update-gate-v144.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))
