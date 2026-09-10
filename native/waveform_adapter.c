#include "waveform_adapter.h"

/* Compare the full project-owned source/track/media-incarnation identity. */
static int same_key(const uint8_t *left, const uint8_t *right)
{
    size_t index;
    for (index = 0; index < XDJ_KEY_BYTES; ++index)
        if (left[index] != right[index])
            return 0;
    return 1;
}

static int usable(const xdj_wave_cache *cache)
{
    return cache != 0 && cache->entries != 0 && cache->order != 0
           && cache->count > 0 && cache->count <= 255;
}

static int known_mode(xdj_preview_mode mode)
{
    return mode == XDJ_PREVIEW_BLUE || mode == XDJ_PREVIEW_RGB;
}

/* A layout must fit the reserved columns and leave one baseline row. */
static int known_layout(const xdj_cell_layout *layout)
{
    return layout != 0 && layout->columns >= 1u
           && layout->columns <= XDJ_ADAPTER_COLUMNS && layout->height >= 2u;
}

/* Position in the recency order of the matching entry, or count when absent.
 * Every index read from order is bounds-checked: a corrupted order array must
 * not become an out-of-range access. */
static size_t position_of(const xdj_wave_cache *cache, const uint8_t *key,
                          xdj_preview_mode mode, const xdj_cell_layout *layout,
                          int *valid_order)
{
    size_t position;
    *valid_order = 1;
    for (position = 0; position < cache->count; ++position) {
        const size_t index = cache->order[position];
        const xdj_wave_entry *entry;
        if (index >= cache->count) {
            *valid_order = 0;
            return cache->count;
        }
        entry = &cache->entries[index];
        if (!entry->valid || entry->mode != (uint8_t)mode || !same_key(entry->key, key))
            continue;
        /* An entry prepared for another rectangle must not be drawn into this
         * one, so it does not match. Passing no layout matches any. */
        if (layout != 0 && (entry->columns != layout->columns
                            || entry->amplitude != layout->height - 1u))
            continue;
        return position;
    }
    return cache->count;
}

xdj_adapter_result xdj_adapter_reset(xdj_wave_cache *cache)
{
    size_t index;
    if (!usable(cache))
        return XDJ_ADAPTER_INVALID;
    for (index = 0; index < cache->count; ++index) {
        cache->entries[index].valid = 0;
        cache->entries[index].mode = 0;
        cache->entries[index].columns = 0;
        cache->entries[index].amplitude = 0;
        cache->order[index] = (uint8_t)index;
    }
    return XDJ_ADAPTER_PREPARED;
}

xdj_adapter_result xdj_adapter_lookup(const xdj_wave_cache *cache,
                                      const uint8_t *key, xdj_preview_mode mode,
                                      const xdj_cell_layout *layout)
{
    int valid_order;
    size_t position;
    if (!usable(cache) || key == 0 || !known_mode(mode))
        return XDJ_ADAPTER_INVALID;
    if (layout != 0 && !known_layout(layout))
        return XDJ_ADAPTER_INVALID;
    position = position_of(cache, key, mode, layout, &valid_order);
    if (!valid_order)
        return XDJ_ADAPTER_INVALID;
    return position < cache->count ? XDJ_ADAPTER_HIT : XDJ_ADAPTER_MISS;
}

xdj_adapter_result xdj_adapter_invalidate(xdj_wave_cache *cache,
                                          const uint8_t *key, xdj_preview_mode mode)
{
    int valid_order;
    size_t position;
    if (!usable(cache) || key == 0 || !known_mode(mode))
        return XDJ_ADAPTER_INVALID;
    /* No layout: drop the entry for this key and mode whatever it was made for. */
    position = position_of(cache, key, mode, 0, &valid_order);
    if (!valid_order)
        return XDJ_ADAPTER_INVALID;
    if (position == cache->count)
        return XDJ_ADAPTER_MISS;
    cache->entries[cache->order[position]].valid = 0;
    return XDJ_ADAPTER_HIT;
}

/* Move the entry at `position` to the front of the recency order. */
static void promote(xdj_wave_cache *cache, size_t position)
{
    const uint8_t index = cache->order[position];
    while (position > 0) {
        cache->order[position] = cache->order[position - 1];
        --position;
    }
    cache->order[0] = index;
}

xdj_adapter_result xdj_adapter_prepare(xdj_wave_cache *cache,
                                       const uint8_t *key, xdj_preview_mode mode,
                                       const xdj_cell_layout *layout,
                                       const uint8_t *payload, size_t bytes,
                                       xdj_pack_rgb8 pack, void *context)
{
    int valid_order;
    size_t position, slot, index;
    xdj_wave_entry *entry;
    xdj_prepare_result prepared;
    if (!usable(cache) || key == 0 || payload == 0 || pack == 0
        || !known_mode(mode) || !known_layout(layout))
        return XDJ_ADAPTER_INVALID;
    /* Reuse this key's entry whatever layout it holds, so a layout change
     * rewrites it instead of consuming a second slot. */
    position = position_of(cache, key, mode, 0, &valid_order);
    if (!valid_order)
        return XDJ_ADAPTER_INVALID;
    if (position == cache->count) {
        position = cache->count - 1;
        if (cache->order[position] >= cache->count)
            return XDJ_ADAPTER_INVALID;
    }
    slot = cache->order[position];
    entry = &cache->entries[slot];
    /* Nothing may observe this entry as valid while it is being rewritten. */
    entry->valid = 0;
    prepared = mode == XDJ_PREVIEW_RGB
        ? xdj_prepare_pwv4_scaled(payload, bytes, entry->column, layout->columns,
                                  (unsigned int)(layout->height - 1u), pack, context)
        : xdj_prepare_pwav_scaled(payload, bytes, entry->column, layout->columns,
                                  (unsigned int)(layout->height - 1u), pack, context);
    if (prepared != XDJ_PREVIEW_PREPARED)
        return XDJ_ADAPTER_INVALID;
    for (index = 0; index < XDJ_KEY_BYTES; ++index)
        entry->key[index] = key[index];
    entry->mode = (uint8_t)mode;
    entry->columns = layout->columns;
    entry->amplitude = (uint16_t)(layout->height - 1u);
    entry->valid = 1;
    promote(cache, position);
    return XDJ_ADAPTER_PREPARED;
}

xdj_adapter_result xdj_adapter_draw(const xdj_wave_cache *cache,
                                    const uint8_t *key, xdj_preview_mode mode,
                                    const xdj_cell_layout *layout,
                                    uint16_t *destination, size_t destination_words,
                                    size_t pitch_words, uint16_t background,
                                    uint16_t baseline, int enabled)
{
    int valid_order;
    size_t position;
    xdj_cell_result drawn;
    if (!enabled)
        return XDJ_ADAPTER_SKIPPED;
    if (!usable(cache) || key == 0 || !known_mode(mode) || !known_layout(layout))
        return XDJ_ADAPTER_INVALID;
    position = position_of(cache, key, mode, layout, &valid_order);
    if (!valid_order)
        return XDJ_ADAPTER_INVALID;
    /* No preview for this row and rectangle: leave the destination alone so the
     * caller keeps the stock artwork it already put there. */
    if (position == cache->count)
        return XDJ_ADAPTER_SKIPPED;
    drawn = xdj_waveform_cell_draw_region(destination, destination_words, pitch_words,
                                          layout->top_row, layout->columns,
                                          layout->height,
                                          cache->entries[cache->order[position]].column,
                                          layout->columns, background, baseline, 1);
    if (drawn != XDJ_CELL_DRAWN)
        return XDJ_ADAPTER_INVALID;
    return XDJ_ADAPTER_HIT;
}
