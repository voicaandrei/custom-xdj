#ifndef XDJ_WAVEFORM_ADAPTER_H
#define XDJ_WAVEFORM_ADAPTER_H

#include "waveform_prepare.h"

/* Orchestration between preview data and one cell: cache, invalidation and a
 * repaint-time draw that never touches the destination unless it has data.
 *
 * This is project-owned glue, NOT a firmware hook. It contains no firmware
 * address, no assumed ABI, no loader, no transport and no call into stock code.
 * It performs no allocation, no IO, no ANLZ parsing and keeps no global state:
 * the caller owns every buffer and decides when each entry point runs.
 */

#include "track_key.h"

/* Columns reserved per cache entry. The list row cell needs 80; the INFO panel
 * cell needs 109. Capacity 325 also admits the proposed INFO strip shapes;
 * this does not choose their location or change any stock descriptor. */
#ifndef XDJ_ADAPTER_COLUMNS
#define XDJ_ADAPTER_COLUMNS 325u
#endif

typedef enum {
    XDJ_PREVIEW_BLUE = 0, /* PWAV payload, one layer */
    XDJ_PREVIEW_RGB = 1   /* PWV4 payload, two layers */
} xdj_preview_mode;

/* Where the strip goes inside the destination. top_row lets a waveform sit at
 * the bottom of a taller cell without disturbing what is above it. */
typedef struct {
    uint16_t columns;
    uint16_t top_row;
    uint16_t height;
} xdj_cell_layout;

typedef struct {
    uint8_t key[XDJ_KEY_BYTES];
    uint8_t mode;
    uint8_t valid;
    uint16_t columns;
    uint16_t amplitude;
    xdj_wave_column column[XDJ_ADAPTER_COLUMNS];
} xdj_wave_entry;

/* Caller-owned storage. entries and order both hold `count` elements, and order
 * is a permutation of 0..count-1 with the most recently prepared entry first.
 * Only xdj_adapter_reset may establish it; nothing else may write to it. */
typedef struct {
    xdj_wave_entry *entries;
    uint8_t *order;
    size_t count;
} xdj_wave_cache;

typedef enum {
    XDJ_ADAPTER_INVALID = -1,
    XDJ_ADAPTER_MISS = 0,
    XDJ_ADAPTER_HIT = 1,
    XDJ_ADAPTER_SKIPPED = 2,
    XDJ_ADAPTER_PREPARED = 3
} xdj_adapter_result;

/* Initialise every entry as empty and the recency order as identity. Required
 * before any other call, and the correct response to a source change. */
xdj_adapter_result xdj_adapter_reset(xdj_wave_cache *cache);

/* Drop one entry. Missing entries are not an error. */
xdj_adapter_result xdj_adapter_invalidate(xdj_wave_cache *cache,
                                          const uint8_t *key, xdj_preview_mode mode);

/* Read-only probe; never mutates the cache. A stored entry prepared for a
 * different layout is reported as a miss, so it can never be drawn. */
xdj_adapter_result xdj_adapter_lookup(const xdj_wave_cache *cache,
                                      const uint8_t *key, xdj_preview_mode mode,
                                      const xdj_cell_layout *layout);

/* Reduce a validated payload into `layout->columns` columns and store them.
 * Call this OUTSIDE repaint. payload is the payload of an already validated
 * ANLZ tag: exactly XDJ_PWAV_BYTES for Blue, XDJ_PWV4_BYTES for RGB. The target
 * entry is marked invalid before any write and valid only after the reduction
 * succeeds, so a failed call can never leave a half-prepared entry visible.
 * That ordering is not a substitute for real synchronisation between tasks. */
xdj_adapter_result xdj_adapter_prepare(xdj_wave_cache *cache,
                                       const uint8_t *key, xdj_preview_mode mode,
                                       const xdj_cell_layout *layout,
                                       const uint8_t *payload, size_t bytes,
                                       xdj_pack_rgb8 pack, void *context);

/* Repaint-time draw. Does not mutate the cache: repaint must not write shared
 * state. Returns SKIPPED without touching destination when the feature is off,
 * the key is absent, or the stored layout differs, so the caller keeps the
 * stock artwork path in all three cases. pitch_words is in 16-bit units. */
xdj_adapter_result xdj_adapter_draw(const xdj_wave_cache *cache,
                                    const uint8_t *key, xdj_preview_mode mode,
                                    const xdj_cell_layout *layout,
                                    uint16_t *destination, size_t destination_words,
                                    size_t pitch_words, uint16_t background,
                                    uint16_t baseline, int enabled);

#endif
