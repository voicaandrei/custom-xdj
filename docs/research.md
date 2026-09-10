# Research and evidence boundaries

[C] means directly confirmed by an identified source or test; [I] is an inference; [U] remains unknown. Owner observations establish behavior on one unit, not universal compatibility.

## Confirmed implementation

- [C, local binary/build checks] The frozen target is the official MK2 1.44 update and decompressed MAIN application identified in [compatibility](compatibility.md). Original extensions compile for little-endian SH-4A without the FPU. Do not reuse these addresses on another image.
- [C, static analysis and owner tests] Artwork paths provide a usable browser drawing route. The release extends that path with cached preview data, preserves the stock overview, and adds a separate INFO band.
- [C, host regression checks] PWAV magnitudes use the low five bits. Bucket maxima preserve narrow peaks while reducing the whole timeline. RGB preparation uses the existing color preview representation.
- [C, owner report] RGB display, the corrected INFO band and the restored narrow browser column worked on the tested unit. The owner accepted FINAL16 after previous scrolling failures.
- [C, local comparison] Custom XDJ v1 preserves FINAL16 runtime code; it changes the empty-deck string and its references. Installation of that final label package remains unobserved.

## Address contract

Unless explicitly marked otherwise in a script, patch sites are file offsets in the decompressed MAIN application with SHA-256 `9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0`. CODE addresses use base `0x08000000`; P2 aliases use `0xa8000000`. They are not offsets in the compressed UPD. The builders and contract indexers carry expected bytes, address-space conversions and source hashes. Generated manifests belong in `private/`.

Read `scripts/build_beta16.py`, its `index_beta*_contract.py` dependencies, and `scripts/build_custom_v1.py` for the frozen release chain. Older beta scripts are research history, not alternate supported releases. Never execute code extracted from firmware during analysis.

## Architecture

Visible stock rows supply identities and artwork requests. The extension requests an existing full-track preview, prepares a bounded representation once, and draws it into the artwork surface. Fast movement postpones preparation. The extra preview transaction is drained before normal JPEG cancellation resumes, avoiding premature protocol reuse. This does not prove freedom from every device timeout.

INFO uses a separate 288 × 28 surface. Its copy code respects the compositor row stride; merely widening a square artwork allocation caused the historical skew. The final comment row is hidden to prevent a later metadata paint from covering the band. Key highlighting reuses stock compatibility information rather than implementing an independent harmonic-key algorithm.

## Open limits

[U] Other hardware revisions, firmware versions, all remote-source and master-change combinations, prolonged soak behavior, and recovery when the application cannot enter the updater. [U] A safe runtime-only loader and an installed feature toggle. Do not infer these from successful normal updates.

## References

- [Deep Symmetry ANLZ documentation](https://djl-analysis.deepsymmetry.org/rekordbox-export-analysis/anlz.html): preview formats.
- [crate-digger format specification](https://github.com/Deep-Symmetry/crate-digger/blob/main/src/main/kaitai/rekordbox_anlz.ksy): independent machine-readable format reference.
- [pyrekordbox ANLZ documentation](https://pyrekordbox.readthedocs.io/en/latest/formats/anlz.html): format cross-check.
- [Renesas SH7724](https://www.renesas.com/en/products/sh7724): processor documentation.
- [AlphaTheta firmware page](https://support.alphatheta.com/en-US/articles/4404821857945): manufacturer distribution information; the latest download is not necessarily the supported 1.44 input.

Reference work on other Pioneer models informed methodology only. Their processors, update formats, offsets and recovery routes are not evidence for this device.
