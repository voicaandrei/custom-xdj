#ifndef XDJ_DRAW_PROBE_H
#define XDJ_DRAW_PROBE_H
#include "waveform_cell.h"
#include "pixel_channels.h"

/* Host-testable input for the first controlled drawing experiment. No loader,
 * addresses, firmware calls, allocation, persistence, or surface ownership.
 * Caller must establish valid buffer lifetime and exclusive access first. */
typedef enum {
    XDJ_PROBE_RED = 0,
    XDJ_PROBE_CHANNELS = 1,
    XDJ_PROBE_GEOMETRY = 2
} xdj_probe_stage;

xdj_cell_result xdj_draw_probe(uint16_t *destination, size_t capacity_words,
    size_t pitch_words, xdj_probe_stage stage, xdj_channel_order order, int enabled);
#endif
