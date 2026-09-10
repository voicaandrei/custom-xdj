#!/usr/bin/env python3
"""Discover PLAYER 4, then ask only for the stock database port and greeting.
No virtual-player announcement, database context, track control or firmware write.
Protocol: Deep-Symmetry/beat-link ConnectionManager.java; track_metadata.html.
"""
import argparse
import datetime
import json
import socket
import time
from pathlib import Path

PORT_QUERY = b'\0\0\0\x0fRemoteDBServer\0'
GREETING = b'\x11\0\0\0\x01'


def announcement(data):
    if len(data) != 54 or data[:11] != b'Qspt1WmJOL\x06':
        return None
    try:
        model = data[12:32].rstrip(b'\0 ').decode('ascii')
    except UnicodeDecodeError:
        return None
    return {'model': model, 'player_number': data[36]}


def receive_exact(sock, length):
    result = bytearray()
    deadline = time.monotonic() + 3
    while len(result) < length:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Response deadline exceeded')
        sock.settimeout(remaining)
        chunk = sock.recv(length - len(result))
        if not chunk:
            raise EOFError('Truncated response')
        result.extend(chunk)
    return bytes(result)


def discover(seconds=6):
    devices = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('', 50000))
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            sock.settimeout(max(0.01, deadline-time.monotonic()))
            try:
                data, peer = sock.recvfrom(2048)
            except socket.timeout:
                break
            info = announcement(data)
            if info:
                devices[peer[0]] = info
    return devices


def probe():
    report = {'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'target_player': 4, 'mode': 'stock_port_and_greeting_only', 'stages': [],
              'virtual_player_announcements_sent': 0, 'database_queries_sent': 0}
    try:
        devices = discover()
        report['observed_devices'] = devices
        candidates = [ip for ip, info in devices.items() if info['player_number'] == 4]
        if len(candidates) != 1 or devices[candidates[0]]['model'] != 'XDJ-1000MK2':
            raise ValueError('PLAYER 4 absent, duplicated, or unexpected model; no TCP connection made')
        address = candidates[0]
        with socket.create_connection((address, 12523), timeout=3) as sock:
            sock.sendall(PORT_QUERY)
            report['stages'].append('port_query_sent')
            port = int.from_bytes(receive_exact(sock, 2), 'big')
        report['database_port'] = port
        if port in (0, 65535):
            raise ValueError('Database server unavailable')
        with socket.create_connection((address, port), timeout=3) as sock:
            sock.sendall(GREETING)
            report['stages'].append('greeting_sent')
            if receive_exact(sock, 5) != GREETING:
                raise ValueError('Unexpected database greeting')
        report['stages'].append('greeting_verified')
        report['result'] = 'stock_database_greeting_verified'
    except (OSError, ValueError, EOFError) as exc:
        report['result'] = 'not_verified'
        report['error'] = str(exc)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-player-4', action='store_true', required=True)
    parser.parse_args()
    result = probe()
    root = Path(__file__).resolve().parents[1]
    output = root / 'private/owner/player4-db-probe.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'observed_devices'}, indent=2))
    raise SystemExit(0 if result['result'] == 'stock_database_greeting_verified' else 1)
