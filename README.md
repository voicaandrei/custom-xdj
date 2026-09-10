# Custom XDJ v1

[![Source checks](https://github.com/voicaandrei/custom-xdj/actions/workflows/checks.yml/badge.svg)](https://github.com/voicaandrei/custom-xdj/actions/workflows/checks.yml)

**Full-track waveform previews for the Pioneer DJ XDJ-1000MK2.** See a track's structure while browsing, keep a wider preview in INFO, and spot stock key compatibility with a green indicator.

This independent project brings a small part of the waveform-oriented browsing workflow associated with newer players to the XDJ-1000MK2. It is an original modification of the MK2 application, not a port of CDJ-3000 firmware.

**Target: XDJ-1000MK2, official firmware 1.44 only.** The final functional build was tested and accepted by one owner on one unit. This is experimental, persistent firmware modification; recovery from an application hang is not proven. Read [compatibility](docs/compatibility.md) and [recovery limits](docs/recovery.md) before building or installing.

## What it adds

| Feature | Custom XDJ v1 behavior |
|---|---|
| Browser waveform | An 80 × 28 px, one-sided preview of the whole track in the artwork slot |
| Color | Uses the stock Blue/RGB preference and existing rekordbox analysis |
| INFO preview | A 288 × 28 px horizontal waveform at the bottom of INFO |
| INFO layout | Hides the final comment row so text does not cover the waveform; USB metadata is unchanged |
| Key compatibility | Makes the existing stock match indicator visible through green note resources; follows available stock row data |
| Fast navigation | Defers preview preparation while browsing moves and finishes the extra preview transaction before restoring JPEG cancellation |
| Empty deck label | `Custom XDJ v1`; the numeric firmware version remains `1.44` |

The 160 px browser experiment was reverted because it overlapped the note and title. The release uses **80 px** both with and without INFO.

The host demo has extra width controls and a toggle. **Those controls are not installed player settings.** A dedicated on-player enable/disable switch is not implemented.

## What it does not add

No Touch Preview or Touch Cue, audio auditioning/scrubbing, three-band waveforms, stacked waveforms, Key Sync/Key Shift, stems, or streaming. A green key indicator does not change the pitch of the audio. The [official CDJ-3000 feature page](https://www.pioneerdj.com/en/product/dj-players-turntables/cdj-3000/) describes those separate features; this project does not claim feature parity.

## Start here

1. [Check your model and firmware](docs/compatibility.md).
2. [Build locally from your own official 1.44 update](docs/building.md).
3. [Read installation and stock-return instructions](docs/installation.md), including the recovery limitations.
4. After installation, [perform the short acceptance check](docs/testing.md#on-player-acceptance).

**No manufacturer firmware or ready-to-flash `.UPD` is distributed here.** The repository contains original source, patch logic, tests, and documentation. You supply the official firmware locally; the builder checks exact SHA-256 values and refuses mismatches. It never accesses or writes a player.

```sh
python3 scripts/build_release.py --firmware /path/to/XDJ1000MK2_v144.zip
```

Requires the pinned SH toolchain described in [Building](docs/building.md). A verified build produces:

```text
private/custom-xdj-v1-v144/XDJ1KMK2.UPD
SHA-256 ce23b4f3d198f5066bc6861223d249d9c66d979b5f0af54a0d32e8e2cb0671f6
```

Do not install a file with a different hash for this release. Do not use firmware from this project on a different model or installed firmware version.

## Validation status

- **Owner-reported:** FINAL16 works correctly on the tested MK2 after restoring the 80 px layout. Earlier RGB, INFO and fast-scroll issues were addressed during testing.
- **Local:** the final `Custom XDJ v1` package changes only the empty-track text and its data references. Its runtime extension is byte-identical to accepted FINAL16; boot, standalone updater and PANEL remain identical to stock.
- **Not yet observed in the recorded session:** the final custom-label package installed on the player. Its transfer was blocked by an unrelated host volume-mount failure.
- **Not claimed:** broad hardware compatibility, multi-hour soak coverage, every LINK source/key-refresh combination, or guaranteed recovery from a bad application.

See [public evidence](evidence/release-v1.json), [testing](docs/testing.md), and [release history](CHANGELOG.md). Private device captures, music exports and raw owner records are excluded.

## Explore without a player

The local web demo uses synthetic tracks and can read your ANLZ files in the browser. Nothing is uploaded and no audio or player connection is opened.

```sh
npm start
# Open http://127.0.0.1:8765
npm test
python3 -m unittest discover -s tests -p 'test_*.py'
```

Node.js 22+, Python 3.9+ and a host C compiler are used for the public checks. Firmware-dependent checks explicitly skip when their private prerequisites are absent. See [Testing](docs/testing.md).

## Project layout

- `native/`: original C renderer, caches, protocol adapters, SH wrappers and historical experiments.
- `scripts/build_release.py`: supported local build entry point.
- `scripts/build_beta*.py`: frozen historical implementation steps; use the release entry point instead of choosing a beta.
- `scripts/audit_*.py`: byte-level and container audits; historical audits may require local evidence.
- `web/`: desktop waveform explorer and ANLZ parsing.
- `tests/`: synthetic/native checks and optional private-reference checks.
- `docs/`: English user and engineering documentation.
- `private/`, `output/`: ignored local artifacts. Never upload their contents.

## Contributing and license

Read [Contributing](CONTRIBUTING.md) and [Security](SECURITY.md). Reports from additional units are welcome, with exact model/firmware and a clear separation between observed behavior and assumptions. Do not attach firmware, tracks, databases, serial numbers or unredacted captures.

Original project code is available under the [MIT license](LICENSE). Manufacturer firmware and third-party material are not covered by that license. See [notices and acknowledgments](NOTICE.md).

Custom XDJ is not affiliated with or endorsed by AlphaTheta, Pioneer DJ or rekordbox.
