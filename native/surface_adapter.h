#ifndef XDJ_SURFACE_ADAPTER_H
#define XDJ_SURFACE_ADAPTER_H
#include "waveform_adapter.h"

/* Project-owned callback contract, NOT declarations of the firmware ABI.
 * A future stock binding must map and validate these operations on the owning
 * UI task. Access returns zero on success and a borrowed pointer/byte pitch.
 * Release returns zero on success, matching the inspected outer stock status.
 * The backend release returning 1 is NOT the same interface.
 * The supplied capacity is independently established by the caller; pitch is
 * not evidence of allocation capacity. No ownership of the handle is taken. */
typedef struct {
    int (*access)(void *context, void *handle, void **pixels, size_t *pitch_bytes);
    int (*release)(void *context, void *handle);
    void *context;
} xdj_surface_ops;

typedef enum {
    XDJ_SURFACE_INVALID = -1,
    XDJ_SURFACE_ACCESS_FAILED = -2,
    XDJ_SURFACE_RELEASE_FAILED = -3,
    XDJ_SURFACE_SKIPPED = 0,
    XDJ_SURFACE_DRAWN = 1
} xdj_surface_result;

/* Requires stable cache and exclusive valid surface access for this call.
 * Never acquires a surface on disabled/cache miss. Every successful acquisition
 * is released once, even if output validation fails. RELEASE_FAILED can mean
 * pixels were already drawn: caller must not blindly reacquire or retry.
 * No stock addresses, firmware patch, allocations, data IO or async jobs. */
xdj_surface_result xdj_surface_draw_cached(
    const xdj_wave_cache *cache, const uint8_t *key, xdj_preview_mode mode,
    const xdj_cell_layout *layout, const xdj_surface_ops *ops, void *handle,
    size_t capacity_bytes, uint16_t background, uint16_t baseline, int enabled);
#endif
