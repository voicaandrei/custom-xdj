#include "waveform_adapter.h"

#include <assert.h>
#include <string.h>

#define ENTRIES 3
#define SENTINEL 0xa5a5u
#define SURFACE_WORDS (XDJ_CELL_WIDTH * XDJ_CELL_HEIGHT)

static const xdj_cell_layout row = {XDJ_CELL_WIDTH, 0, XDJ_CELL_HEIGHT};
static const xdj_cell_layout info_strip = {109, 93, 24};

static xdj_wave_entry storage[ENTRIES];
static uint8_t order[ENTRIES];
static uint8_t pwav[XDJ_PWAV_BYTES];
static uint8_t pwv4[XDJ_PWV4_BYTES];
static uint16_t guarded[SURFACE_WORDS + 2];

static uint16_t pack(uint8_t r, uint8_t g, uint8_t b, void *context)
{
    (void)context;
    return (uint16_t)((r >> 3 << 11) | (g >> 2 << 5) | (b >> 3));
}

static void fill_destination(void)
{
    size_t index;
    for (index = 0; index < SURFACE_WORDS + 2; ++index)
        guarded[index] = SENTINEL;
}

static int destination_untouched(void)
{
    size_t index;
    for (index = 0; index < SURFACE_WORDS + 2; ++index)
        if (guarded[index] != SENTINEL)
            return 0;
    return 1;
}

static xdj_wave_cache make_cache(void)
{
    xdj_wave_cache cache;
    cache.entries = storage;
    cache.order = order;
    cache.count = ENTRIES;
    assert(xdj_adapter_reset(&cache) == XDJ_ADAPTER_PREPARED);
    return cache;
}

static const uint8_t key_a[XDJ_KEY_BYTES] = {1, 2, 3, 4, 5, 6, 7, 8};
static const uint8_t key_b[XDJ_KEY_BYTES] = {9, 9, 9, 9, 9, 9, 9, 9};
static const uint8_t key_c[XDJ_KEY_BYTES] = {7, 7, 7, 7, 7, 7, 7, 7};
static const uint8_t key_d[XDJ_KEY_BYTES] = {3, 3, 3, 3, 3, 3, 3, 3};
/* Same as key_a except byte 3, which the firmware's own comparison ignores. */
static const uint8_t key_a_byte3[XDJ_KEY_BYTES] = {1, 2, 3, 99, 5, 6, 7, 8};

static void test_rejects_bad_arguments(void)
{
    xdj_wave_cache cache = make_cache();
    xdj_wave_cache broken = cache;
    assert(xdj_adapter_reset(0) == XDJ_ADAPTER_INVALID);
    broken.entries = 0;
    assert(xdj_adapter_reset(&broken) == XDJ_ADAPTER_INVALID);
    broken = cache;
    broken.order = 0;
    assert(xdj_adapter_lookup(&broken, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_INVALID);
    broken = cache;
    broken.count = 0;
    assert(xdj_adapter_lookup(&broken, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_INVALID);
    broken = cache;
    broken.count = 256;
    assert(xdj_adapter_lookup(&broken, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_INVALID);
    assert(xdj_adapter_lookup(&cache, 0, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_INVALID);
    assert(xdj_adapter_lookup(&cache, key_a, (xdj_preview_mode)7, &row) == XDJ_ADAPTER_INVALID);
    assert(xdj_adapter_invalidate(&cache, 0, XDJ_PREVIEW_BLUE) == XDJ_ADAPTER_INVALID);
    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_BLUE, &row, 0, sizeof pwav, pack, 0)
           == XDJ_ADAPTER_INVALID);
    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav, 0, 0)
           == XDJ_ADAPTER_INVALID);
}

static void test_corrupted_order_is_refused(void)
{
    xdj_wave_cache cache = make_cache();
    order[1] = ENTRIES; /* out of range */
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_INVALID);
    assert(xdj_adapter_invalidate(&cache, key_a, XDJ_PREVIEW_BLUE) == XDJ_ADAPTER_INVALID);
    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav, pack, 0)
           == XDJ_ADAPTER_INVALID);
    fill_destination();
    assert(xdj_adapter_draw(&cache, key_a, XDJ_PREVIEW_BLUE, &row, guarded + 1, SURFACE_WORDS,
                            XDJ_CELL_WIDTH, 0, 1, 1) == XDJ_ADAPTER_INVALID);
    assert(destination_untouched());
}

static void test_prepare_and_lookup(void)
{
    xdj_wave_cache cache = make_cache();
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_MISS);
    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav, pack, 0)
           == XDJ_ADAPTER_PREPARED);
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_HIT);
    /* The mode is part of the identity, so the other mode is still a miss. */
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_RGB, &row) == XDJ_ADAPTER_MISS);
    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_RGB, &row, pwv4, sizeof pwv4, pack, 0)
           == XDJ_ADAPTER_PREPARED);
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_RGB, &row) == XDJ_ADAPTER_HIT);
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_HIT);
    /* All sixteen bytes matter, including the media incarnation tail. */
    assert(xdj_adapter_lookup(&cache, key_a_byte3, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_MISS);
    {
        uint8_t other_epoch[XDJ_KEY_BYTES];
        memcpy(other_epoch, key_a, sizeof other_epoch);
        other_epoch[XDJ_KEY_BYTES - 1] ^= 1;
        assert(xdj_adapter_lookup(&cache, other_epoch, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_MISS);
    }
    assert(xdj_adapter_invalidate(&cache, key_a, XDJ_PREVIEW_BLUE) == XDJ_ADAPTER_HIT);
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_MISS);
    assert(xdj_adapter_invalidate(&cache, key_a, XDJ_PREVIEW_BLUE) == XDJ_ADAPTER_MISS);
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_RGB, &row) == XDJ_ADAPTER_HIT);
}

static void test_failed_prepare_leaves_no_entry(void)
{
    xdj_wave_cache cache = make_cache();
    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav, pack, 0)
           == XDJ_ADAPTER_PREPARED);
    /* A wrong payload length must drop the entry, not keep the stale columns. */
    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav - 1,
                               pack, 0) == XDJ_ADAPTER_INVALID);
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_MISS);
    /* An RGB payload offered as Blue is refused the same way. */
    assert(xdj_adapter_prepare(&cache, key_b, XDJ_PREVIEW_BLUE, &row, pwv4, sizeof pwv4, pack, 0)
           == XDJ_ADAPTER_INVALID);
    assert(xdj_adapter_lookup(&cache, key_b, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_MISS);
}

static void test_eviction_and_promotion(void)
{
    xdj_wave_cache cache = make_cache();
    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav, pack, 0)
           == XDJ_ADAPTER_PREPARED);
    assert(xdj_adapter_prepare(&cache, key_b, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav, pack, 0)
           == XDJ_ADAPTER_PREPARED);
    assert(xdj_adapter_prepare(&cache, key_c, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav, pack, 0)
           == XDJ_ADAPTER_PREPARED);
    /* Re-preparing the oldest key moves it out of the eviction slot. */
    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav, pack, 0)
           == XDJ_ADAPTER_PREPARED);
    assert(xdj_adapter_prepare(&cache, key_d, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav, pack, 0)
           == XDJ_ADAPTER_PREPARED);
    assert(xdj_adapter_lookup(&cache, key_b, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_MISS);
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_HIT);
    assert(xdj_adapter_lookup(&cache, key_c, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_HIT);
    assert(xdj_adapter_lookup(&cache, key_d, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_HIT);
    /* Re-preparing an existing key must not consume a second slot. */
    assert(xdj_adapter_prepare(&cache, key_d, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav, pack, 0)
           == XDJ_ADAPTER_PREPARED);
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_HIT);
    assert(xdj_adapter_lookup(&cache, key_c, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_HIT);
    /* A source change drops everything. */
    assert(xdj_adapter_reset(&cache) == XDJ_ADAPTER_PREPARED);
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_MISS);
    assert(xdj_adapter_lookup(&cache, key_d, XDJ_PREVIEW_BLUE, &row) == XDJ_ADAPTER_MISS);
}

static void test_draw_paths(void)
{
    xdj_wave_cache cache = make_cache();
    unsigned char before[sizeof storage + sizeof order];
    size_t x;

    /* Feature off: nothing is written, whatever the cache holds. */
    fill_destination();
    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_BLUE, &row, pwav, sizeof pwav, pack, 0)
           == XDJ_ADAPTER_PREPARED);
    assert(xdj_adapter_draw(&cache, key_a, XDJ_PREVIEW_BLUE, &row, guarded + 1, SURFACE_WORDS,
                            XDJ_CELL_WIDTH, 0, 1, 0) == XDJ_ADAPTER_SKIPPED);
    assert(destination_untouched());

    /* No preview for this row: the stock artwork already there stays. */
    assert(xdj_adapter_draw(&cache, key_b, XDJ_PREVIEW_BLUE, &row, guarded + 1, SURFACE_WORDS,
                            XDJ_CELL_WIDTH, 0, 1, 1) == XDJ_ADAPTER_SKIPPED);
    assert(destination_untouched());

    /* Invalid geometry is refused before the first write. */
    assert(xdj_adapter_draw(&cache, key_a, XDJ_PREVIEW_BLUE, &row, guarded + 1,
                            SURFACE_WORDS - 1, XDJ_CELL_WIDTH, 0, 1, 1)
           == XDJ_ADAPTER_INVALID);
    assert(destination_untouched());

    /* A hit draws, and the repaint leaves the cache byte-identical. */
    memcpy(before, storage, sizeof storage);
    memcpy(before + sizeof storage, order, sizeof order);
    assert(xdj_adapter_draw(&cache, key_a, XDJ_PREVIEW_BLUE, &row, guarded + 1, SURFACE_WORDS,
                            XDJ_CELL_WIDTH, 0, 1, 1) == XDJ_ADAPTER_HIT);
    assert(memcmp(before, storage, sizeof storage) == 0);
    assert(memcmp(before + sizeof storage, order, sizeof order) == 0);
    assert(guarded[0] == SENTINEL);
    assert(guarded[SURFACE_WORDS + 1] == SENTINEL);
    /* The baseline row is written for every column. */
    for (x = 0; x < XDJ_CELL_WIDTH; ++x)
        assert(guarded[1 + XDJ_CELL_AMPLITUDE_HEIGHT * XDJ_CELL_WIDTH + x] == 1);
}

/* A cache entry made for one rectangle must never be drawn into another. */
static void test_layout_is_part_of_the_match(void)
{
    static uint16_t wide[117 * 113 + 2];
    xdj_wave_cache cache = make_cache();
    size_t index;
    for (index = 0; index < sizeof wide / sizeof wide[0]; ++index)
        wide[index] = SENTINEL;

    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_RGB, &row,
                               pwv4, sizeof pwv4, pack, 0) == XDJ_ADAPTER_PREPARED);
    /* Prepared for the row cell, so the INFO strip does not match it. */
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_RGB, &info_strip)
           == XDJ_ADAPTER_MISS);
    assert(xdj_adapter_draw(&cache, key_a, XDJ_PREVIEW_RGB, &info_strip, wide + 1,
                            117u * 113u, 113u, 0, 1, 1) == XDJ_ADAPTER_SKIPPED);
    for (index = 0; index < sizeof wide / sizeof wide[0]; ++index)
        assert(wide[index] == SENTINEL);

    /* Re-preparing for the strip replaces the entry instead of taking a slot. */
    assert(xdj_adapter_prepare(&cache, key_a, XDJ_PREVIEW_RGB, &info_strip,
                               pwv4, sizeof pwv4, pack, 0) == XDJ_ADAPTER_PREPARED);
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_RGB, &info_strip)
           == XDJ_ADAPTER_HIT);
    assert(xdj_adapter_lookup(&cache, key_a, XDJ_PREVIEW_RGB, &row) == XDJ_ADAPTER_MISS);
    assert(xdj_adapter_draw(&cache, key_a, XDJ_PREVIEW_RGB, &info_strip, wide + 1,
                            117u * 113u, 113u, 0, 1, 1) == XDJ_ADAPTER_HIT);
    /* Only the strip rows changed; everything above the cover area is intact. */
    for (index = 0; index < 1u + info_strip.top_row * 113u; ++index)
        assert(wide[index] == SENTINEL);
    assert(wide[sizeof wide / sizeof wide[0] - 1u] == SENTINEL);

    /* A layout the reserved columns cannot hold is refused, not truncated. */
    {
        const xdj_cell_layout too_wide = {XDJ_ADAPTER_COLUMNS + 1u, 0, 8};
        const xdj_cell_layout too_short = {8, 0, 1};
        assert(xdj_adapter_prepare(&cache, key_b, XDJ_PREVIEW_RGB, &too_wide,
                                   pwv4, sizeof pwv4, pack, 0) == XDJ_ADAPTER_INVALID);
        assert(xdj_adapter_prepare(&cache, key_b, XDJ_PREVIEW_RGB, &too_short,
                                   pwv4, sizeof pwv4, pack, 0) == XDJ_ADAPTER_INVALID);
        assert(xdj_adapter_prepare(&cache, key_b, XDJ_PREVIEW_RGB, 0,
                                   pwv4, sizeof pwv4, pack, 0) == XDJ_ADAPTER_INVALID);
    }
}

int main(void)
{
    size_t index;
    for (index = 0; index < XDJ_PWAV_BYTES; ++index)
        pwav[index] = (uint8_t)((index * 53u + 7u) & 255u);
    for (index = 0; index < XDJ_PWV4_BYTES; ++index)
        pwv4[index] = (uint8_t)((index * 37u + 11u) & 255u);

    test_rejects_bad_arguments();
    test_corrupted_order_is_refused();
    test_prepare_and_lookup();
    test_failed_prepare_leaves_no_entry();
    test_eviction_and_promotion();
    test_draw_paths();
    test_layout_is_part_of_the_match();
    return 0;
}
