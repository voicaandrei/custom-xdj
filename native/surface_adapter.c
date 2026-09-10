#include "surface_adapter.h"

xdj_surface_result xdj_surface_draw_cached(
    const xdj_wave_cache *cache, const uint8_t *key, xdj_preview_mode mode,
    const xdj_cell_layout *layout, const xdj_surface_ops *ops, void *handle,
    size_t capacity_bytes, uint16_t background, uint16_t baseline, int enabled)
{
    void *pixels = 0;
    size_t pitch_bytes = 0;
    xdj_adapter_result found;
    xdj_surface_result result = XDJ_SURFACE_INVALID;
    if (!enabled)
        return XDJ_SURFACE_SKIPPED;
    found = xdj_adapter_lookup(cache, key, mode, layout);
    if (found == XDJ_ADAPTER_MISS)
        return XDJ_SURFACE_SKIPPED;
    if (found != XDJ_ADAPTER_HIT || ops == 0 || ops->access == 0 ||
        ops->release == 0 || handle == 0 || capacity_bytes == 0 ||
        (capacity_bytes & 1u) != 0)
        return XDJ_SURFACE_INVALID;
    if (ops->access(ops->context, handle, &pixels, &pitch_bytes) != 0)
        return XDJ_SURFACE_ACCESS_FAILED;
    if (pixels != 0 && ((uintptr_t)pixels & 1u) == 0 &&
        pitch_bytes != 0 && (pitch_bytes & 1u) == 0) {
        xdj_adapter_result drawn = xdj_adapter_draw(cache, key, mode, layout,
            (uint16_t *)pixels, capacity_bytes / 2u, pitch_bytes / 2u,
            background, baseline, 1);
        if (drawn == XDJ_ADAPTER_HIT)
            result = XDJ_SURFACE_DRAWN;
        else if (drawn == XDJ_ADAPTER_SKIPPED)
            result = XDJ_SURFACE_SKIPPED;
    }
    if (ops->release(ops->context, handle) != 0)
        return XDJ_SURFACE_RELEASE_FAILED;
    return result;
}
