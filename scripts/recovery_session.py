#!/usr/bin/env python3
"""Local recovery preparation/evidence journal. No device, network or flash access."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'private'
STOCK = PRIVATE / 'originals/v144/XDJ1KMK2.UPD'
STOCK_SHA = 'b21d499d8964986216b6a235cff5849300d966d3801b522c17461a42a1ff1448'
KINDS = ('version_screen', 'stock_update_prompt', 'stock_boot_after_prompt',
         'board_identification', 'diagnostic_access', 'recovery_trial')


def sha(path):
    with path.open('rb') as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
        return digest.hexdigest()


def confined(path):
    path = Path(path).resolve()
    if not path.is_relative_to(PRIVATE.resolve()) or path == PRIVATE.resolve():
        raise ValueError('Session must remain inside project private/')
    return path


def save(path, value):
    # Exclusive creation: never overwrite an earlier observation.
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def initialize(destination):
    destination = confined(destination)
    if sha(STOCK) != STOCK_SHA:
        raise ValueError('Official 1.44 firmware identity mismatch')
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'stock-reference').mkdir()
    target = destination / 'stock-reference/XDJ1KMK2.UPD'
    shutil.copyfile(STOCK, target)
    if sha(target) != STOCK_SHA:
        raise ValueError('Copied stock reference failed verification; session incomplete')
    target.chmod(0o444)
    (destination / 'observations').mkdir()
    shutil.copyfile(ROOT / 'docs/recovery-procedure.md', destination / 'PROCEDURA.md')
    save(destination / 'session.json', {
        'schema': 1, 'model': 'XDJ-1000MK2', 'player': 4,
        'version_owner_reported': '1.44', 'pcb_revision': None,
        'stock_sha256': STOCK_SHA,
        'notice': 'Stock reference only. Do not copy to USB during the no-write probe.',
    })
    return inspect(destination)


def record(destination, kind, evidence, note):
    destination = confined(destination)
    if kind not in KINDS:
        raise ValueError('Unknown observation kind')
    inspect(destination)  # refuse incomplete or altered stock reference
    source = Path(evidence).resolve()
    if not source.is_file():
        raise ValueError('Evidence must be a regular file')
    folder = destination / 'observations'
    # Exact evidence bytes retained privately, with no overwrite.
    digest = sha(source)
    attachment = folder / (kind + '-' + digest + '.attachment')
    with source.open('rb') as src, attachment.open('xb') as dst:
        shutil.copyfileobj(src, dst)
    if sha(attachment) != digest:
        raise ValueError('Evidence changed while copying')
    save(folder / (kind + '-' + digest + '.json'), {
        'kind': kind, 'file': attachment.name, 'sha256': digest,
        'note_owner_or_operator': note, 'review': 'not_reviewed',
        'claim': 'An attachment is not proof of successful recovery.',
    })
    return inspect(destination)


def inspect(destination):
    destination = confined(destination)
    manifest = json.loads((destination / 'session.json').read_text())
    if manifest.get('schema') != 1 or manifest.get('stock_sha256') != STOCK_SHA:
        raise ValueError('Unexpected session identity')
    if sha(destination / 'stock-reference/XDJ1KMK2.UPD') != STOCK_SHA:
        raise ValueError('Stock reference corrupted')
    observations = []
    for path in sorted((destination / 'observations').glob('*.json')):
        value = json.loads(path.read_text())
        attachment = (path.parent / value['file']).resolve()
        if attachment.parent != path.parent.resolve() or sha(attachment) != value['sha256']:
            raise ValueError('Evidence integrity mismatch')
        observations.append({'kind': value['kind'], 'review': 'not_reviewed'})
    return {'stock_integrity': 'verified', 'observations': observations,
            'ready_for_player_patch': False,
            'reason': 'This journal cannot certify recovery. Exact-unit recovery and '
                      'execution route require technical review and owner authorization.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('init', 'record', 'inspect'))
    parser.add_argument('--session', type=Path, default=PRIVATE / 'recovery/player4-v144')
    parser.add_argument('--kind', choices=KINDS)
    parser.add_argument('--file', type=Path)
    parser.add_argument('--note', default='')
    args = parser.parse_args()
    try:
        if args.action == 'init':
            result = initialize(args.session)
        elif args.action == 'record':
            if not args.kind or not args.file:
                parser.error('record requires --kind and --file')
            result = record(args.session, args.kind, args.file, args.note)
        else:
            result = inspect(args.session)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
