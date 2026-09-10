/* Covers the geometry the INFO panel needs: an arbitrary rectangle, a strip
 * inside a taller cell, and column counts other than the 80 of a list row. */
#include "waveform_prepare.h"

#include <assert.h>

/* The INFO cell source buffer as the stock copy fills it: 109 visible pixels
 * per row over a 113-word stride, 117 rows. The surface itself is 128 x 121,
 * but only the stride and the filled area are ours to write. */
#define INFO_WIDTH 109u
#define INFO_HEIGHT 117u
#define PITCH 113u
#define SURFACE (INFO_HEIGHT * PITCH)
#define SENTINEL 0x5a5au

static uint16_t surface[SURFACE + 2];
static xdj_wave_column columns[XDJ_PWV4_SAMPLES];
static uint8_t pwav[XDJ_PWAV_BYTES];
static uint8_t pwv4[XDJ_PWV4_BYTES];
static unsigned int pack_calls;

static uint16_t pack(uint8_t r, uint8_t g, uint8_t b, void *context)
{
    (void)context;
    ++pack_calls;
    return (uint16_t)((r >> 3 << 11) | (g >> 2 << 5) | (b >> 3));
}

static void fill_surface(void)
{
    size_t i;
    for (i = 0; i < SURFACE + 2; ++i)
        surface[i] = SENTINEL;
}

static void flat_columns(size_t count, uint8_t height)
{
    size_t i;
    for (i = 0; i < count; ++i) {
        columns[i].back_height = height;
        columns[i].front_height = 0;
        columns[i].back_color = 0x1234;
        columns[i].front_color = 0;
    }
}

static void test_strip_leaves_the_rest_of_the_cell_alone(void)
{
    /* A 109 x 24 strip at the bottom of the filled area, pitch 113 words.
     * Only the strip may change; the cover above it must survive untouched. */
    const size_t strip = 24u, top = INFO_HEIGHT - strip;
    size_t row, x;
    fill_surface();
    flat_columns(INFO_WIDTH, (uint8_t)(strip - 1u));
    assert(xdj_waveform_cell_draw_region(surface + 1, SURFACE, PITCH, top,
                                         INFO_WIDTH, strip, columns, INFO_WIDTH,
                                         0, 1, 1) == XDJ_CELL_DRAWN);
    assert(surface[0] == SENTINEL);
    assert(surface[SURFACE + 1] == SENTINEL);
    for (row = 0; row < top; ++row)
        for (x = 0; x < PITCH; ++x)
            assert(surface[1 + row * PITCH + x] == SENTINEL);
    /* Inside the strip the drawn columns changed and the padding did not. */
    for (row = top; row < INFO_HEIGHT; ++row) {
        for (x = 0; x < INFO_WIDTH && 1 + row * PITCH + x < SURFACE + 1; ++x)
            assert(surface[1 + row * PITCH + x] != SENTINEL);
        for (x = INFO_WIDTH; x < PITCH; ++x)
            assert(surface[1 + row * PITCH + x] == SENTINEL);
    }
    /* The last row of the strip is the baseline. */
    for (x = 0; x < INFO_WIDTH; ++x)
        assert(surface[1 + (INFO_HEIGHT - 1u) * PITCH + x] == 1);
}

static void test_region_refuses_bad_rectangles(void)
{
    fill_surface();
    flat_columns(INFO_WIDTH, 1);
    /* height below two leaves no amplitude row at all. */
    assert(xdj_waveform_cell_draw_region(surface + 1, SURFACE, PITCH, 0, INFO_WIDTH,
                                         1, columns, INFO_WIDTH, 0, 1, 1)
           == XDJ_CELL_INVALID);
    assert(xdj_waveform_cell_draw_region(surface + 1, SURFACE, PITCH, 0, 0,
                                         4, columns, 0, 0, 1, 1) == XDJ_CELL_INVALID);
    /* column_count must equal width. */
    assert(xdj_waveform_cell_draw_region(surface + 1, SURFACE, PITCH, 0, INFO_WIDTH,
                                         4, columns, INFO_WIDTH - 1u, 0, 1, 1)
           == XDJ_CELL_INVALID);
    /* pitch narrower than the rectangle. */
    assert(xdj_waveform_cell_draw_region(surface + 1, SURFACE, INFO_WIDTH - 1u, 0,
                                         INFO_WIDTH, 4, columns, INFO_WIDTH, 0, 1, 1)
           == XDJ_CELL_INVALID);
    /* The strip would run past the end of the destination. */
    assert(xdj_waveform_cell_draw_region(surface + 1, SURFACE, PITCH,
                                         INFO_HEIGHT - 3u, INFO_WIDTH, 4, columns,
                                         INFO_WIDTH, 0, 1, 1) == XDJ_CELL_INVALID);
    /* A column taller than the strip. */
    flat_columns(INFO_WIDTH, 4);
    assert(xdj_waveform_cell_draw_region(surface + 1, SURFACE, PITCH, 0, INFO_WIDTH,
                                         4, columns, INFO_WIDTH, 0, 1, 1)
           == XDJ_CELL_INVALID);
    /* Disabled and absent preview both leave everything alone. */
    assert(xdj_waveform_cell_draw_region(surface + 1, SURFACE, PITCH, 0, INFO_WIDTH,
                                         8, columns, INFO_WIDTH, 0, 1, 0)
           == XDJ_CELL_SKIPPED);
    assert(xdj_waveform_cell_draw_region(surface + 1, SURFACE, PITCH, 0, INFO_WIDTH,
                                         8, 0, INFO_WIDTH, 0, 1, 1) == XDJ_CELL_SKIPPED);
    {
        size_t i;
        for (i = 0; i < SURFACE + 2; ++i)
            assert(surface[i] == SENTINEL);
    }
}

/* Every sample must land in exactly one column: a single impulse anywhere in
 * the payload must light exactly one column, whatever the column count. */
static void test_every_sample_is_covered_once(void)
{
    const size_t counts[] = {1u, 7u, 80u, 109u, 128u, 400u};
    size_t index, sample, x;
    for (index = 0; index < sizeof counts / sizeof counts[0]; ++index) {
        const size_t count = counts[index];
        for (sample = 0; sample < XDJ_PWAV_SAMPLES; ++sample) {
            size_t lit = 0;
            for (x = 0; x < XDJ_PWAV_BYTES; ++x) pwav[x] = 0;
            pwav[sample] = 31u;
            assert(xdj_prepare_pwav_scaled(pwav, sizeof pwav, columns, count,
                                           27u, pack, 0) == XDJ_PREVIEW_PREPARED);
            for (x = 0; x < count; ++x)
                if (columns[x].back_height != 0) ++lit;
            assert(lit == 1u);
        }
    }
}

static void test_scaled_bounds_and_heights(void)
{
    size_t i, x;
    for (i = 0; i < XDJ_PWV4_BYTES; ++i)
        pwv4[i] = (uint8_t)((i * 37u + 11u) & 255u);
    /* Heights honour the requested amplitude, not the row-cell constant. */
    assert(xdj_prepare_pwv4_scaled(pwv4, sizeof pwv4, columns, INFO_WIDTH,
                                   INFO_HEIGHT - 1u, pack, 0) == XDJ_PREVIEW_PREPARED);
    for (x = 0; x < INFO_WIDTH; ++x) {
        assert(columns[x].back_height <= INFO_HEIGHT - 1u);
        assert(columns[x].front_height <= INFO_HEIGHT - 1u);
    }
    /* No upsampling: more columns than samples is refused, and so is zero. */
    pack_calls = 0;
    assert(xdj_prepare_pwv4_scaled(pwv4, sizeof pwv4, columns,
                                   XDJ_PWV4_SAMPLES + 1u, 27u, pack, 0)
           == XDJ_PREVIEW_INVALID);
    assert(xdj_prepare_pwav_scaled(pwav, sizeof pwav, columns, 0, 27u, pack, 0)
           == XDJ_PREVIEW_INVALID);
    assert(xdj_prepare_pwav_scaled(pwav, sizeof pwav, columns, 80u, 0, pack, 0)
           == XDJ_PREVIEW_INVALID);
    assert(xdj_prepare_pwav_scaled(pwav, sizeof pwav, columns, 80u, 256u, pack, 0)
           == XDJ_PREVIEW_INVALID);
    assert(pack_calls == 0u);
    /* One column per sample is the identity case and must still work. */
    assert(xdj_prepare_pwv4_scaled(pwv4, sizeof pwv4, columns, XDJ_PWV4_SAMPLES,
                                   27u, pack, 0) == XDJ_PREVIEW_PREPARED);
    /* The row-cell wrappers still refuse any other column count. */
    assert(xdj_prepare_pwv4(pwv4, sizeof pwv4, columns, INFO_WIDTH, pack, 0)
           == XDJ_PREVIEW_INVALID);
}

int main(void)
{
    test_strip_leaves_the_rest_of_the_cell_alone();
    test_region_refuses_bad_rectangles();
    test_every_sample_is_covered_once();
    test_scaled_bounds_and_heights();
    return 0;
}
