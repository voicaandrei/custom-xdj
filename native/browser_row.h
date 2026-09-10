#ifndef XDJ_BROWSER_ROW_H
#define XDJ_BROWSER_ROW_H
#include <stddef.h>
#include <stdint.h>
/* v1.44 decompressed MAIN SHA:
 * 9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0.
 * Reads a caller-provided snapshot of ONE 276-byte local list row, never RAM
 * through a hardcoded address. Only normal Track Title kind 4 and observed
 * flags 0x400/0x4000 are admitted. Special/unknown kinds stay stock.
 * This does NOT prove source, media generation, database type, or row lifetime.
 * Success: writes main ID at +0; artwork ID at +8 is deliberately irrelevant.
 * Failure: returns zero, leaves output untouched. Input/output must be disjoint.
 */
int xdj_browser_row_track_id(const uint8_t *row, size_t bytes, uint32_t *track_id);
#endif
