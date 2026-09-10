# Compatibility

## Hardware and firmware

| Target | Status | Action |
|---|---|---|
| XDJ-1000MK2, firmware 1.44, tested LSYXJ unit | Owner accepted the FINAL16 functionality | Exact target of this release; still experimental |
| Other XDJ-1000MK2 units on 1.44 | Not independently tested | Do not generalize one-unit acceptance into universal support |
| XDJ-1000MK2 on 1.45 or other versions | Unsupported | Do not flash this patch or assume downgrading is safe |
| XDJ-1000, without MK2 | Incompatible target | Do not install |
| XDJ-RX/RX2/RX3, CDJ-2000/NXS/NXS2, CDJ-3000 or any other model | Incompatible target | Do not install |

The tested unit's exterior designation is **XDJ-1000MK2/LSYXJ**, manufactured in December 2017. The PCB revision was not established; the enclosure was not opened. Neither the product suffix nor manufacture date is a substitute for a PCB revision. No unit serial or USB identifier is published.

The installed version must be checked on the player at **MENU/UTILITY → VERSION No.** A matching file hash does not identify the connected hardware. A USB computer connection does not provide a verified firmware-dump or rescue route in this project.

## Frozen inputs

| Item | SHA-256 |
|---|---|
| Official 1.44 `.UPD` | `b21d499d8964986216b6a235cff5849300d966d3801b522c17461a42a1ff1448` |
| Decompressed stock MAIN application | `9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0` |
| Accepted FINAL16 `.UPD` | `322364190bacee1c3439809ac3979058b3202f7407d1b4028acd29522bad0e78` |
| Custom XDJ v1 `.UPD` | `ce23b4f3d198f5066bc6861223d249d9c66d979b5f0af54a0d32e8e2cb0671f6` |

The official and modified updates are each 25,391,319 bytes. **Size alone is not an integrity check.** All binary offsets in the project apply to the stated stock MAIN hash and their explicitly named address space.

## Data and browsing

- Uses a rekordbox export and existing analysis. No on-player audio analysis is added.
- Blue and RGB preview requests follow the existing preference. Three-band is outside scope.
- The final browser preview replaces artwork on the existing artwork-capable row path. Not every database category, unanalysed track or missing-artwork case has guaranteed coverage.
- INFO is a horizontal band at the bottom of the panel. The final metadata/comment row is hidden on screen; the comment stored on the USB is not edited.
- Key coloring reuses stock compatibility state. Incomplete or old replies can lack the needed match flag; no match is invented. The complete refresh behavior across all master changes and LINK sources remains unverified.
- USB/local export and a LINK-master setup were used during owner testing. This is not a network topology certification or a supported-device list for other players.
- Normal loading/playback continued in reported tests. Loop, hot-cue, search/sort, every file format, every source switch and long-duration audio behavior do not have an exhaustive acceptance matrix.

## Persistence and disabling

This is a **persistent MAIN application update**, not a RAM-only mod. Power cycling does not remove it. There is no dedicated installed feature toggle. Stock return uses an official manufacturer update where the stock updater remains reachable; [recovery from an application hang is not proven](recovery.md).

The desktop demo's toggle and alternate widths do not establish corresponding player features.
