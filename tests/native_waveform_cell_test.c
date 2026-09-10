#include "waveform_cell.h"
#include <assert.h>
#include <string.h>

#define PITCH 86u
#define WORDS (PITCH * XDJ_CELL_HEIGHT)

int main(void)
{
    uint16_t guarded[WORDS + 2], before[WORDS + 2];
    uint16_t *pixels = guarded + 1;
    xdj_wave_column columns[XDJ_CELL_WIDTH] = {{0}};
    size_t x, y;
    for (x = 0; x < WORDS + 2; ++x) guarded[x] = 0xdead;
    memcpy(before, guarded, sizeof guarded);
    columns[0] = (xdj_wave_column){27, 3, 0x1234, 0xabcd};
    columns[1] = (xdj_wave_column){0, 1, 0x5678, 0x1357};
    columns[79] = (xdj_wave_column){1, 0, 0x2468, 0};

    assert(xdj_waveform_cell_draw(NULL, 0, 0, columns, 80, 0, 0, 0) == XDJ_CELL_SKIPPED);
    assert(xdj_waveform_cell_draw(pixels, WORDS, PITCH, NULL, 0, 0, 0, 1) == XDJ_CELL_SKIPPED);
    assert(xdj_waveform_cell_draw(pixels, WORDS, 79, columns, 80, 0, 0, 1) == XDJ_CELL_INVALID);
    assert(xdj_waveform_cell_draw(pixels, WORDS, SIZE_MAX, columns, 80, 0, 0, 1) == XDJ_CELL_INVALID);
    assert(xdj_waveform_cell_draw(pixels, 27 * PITCH + 79, PITCH, columns, 80, 0, 0, 1) == XDJ_CELL_INVALID);
    assert(xdj_waveform_cell_draw(pixels, WORDS, PITCH, columns, 79, 0, 0, 1) == XDJ_CELL_INVALID);
    assert(xdj_waveform_cell_draw(NULL, WORDS, PITCH, columns, 80, 0, 0, 1) == XDJ_CELL_INVALID);
    columns[79].front_height = 28;
    assert(xdj_waveform_cell_draw(pixels, WORDS, PITCH, columns, 80, 0, 0, 1) == XDJ_CELL_INVALID);
    assert(memcmp(before, guarded, sizeof guarded) == 0);
    columns[79].front_height = 0;
    assert(xdj_waveform_cell_draw(pixels, 27 * PITCH + 80, PITCH, columns, 80,
                                  0x1111, 0xeeee, 1) == XDJ_CELL_DRAWN);
    for (y = 0; y < XDJ_CELL_HEIGHT; ++y) {
        for (x = 0; x < PITCH; ++x) {
            uint16_t expected = 0xdead;
            if (x < 80) {
                expected = y == 27 ? 0xeeee : 0x1111;
                if (y < 27 && x == 0) expected = y >= 24 ? 0xabcd : 0x1234;
                if (y == 26 && x == 1) expected = 0x1357;
                if (y == 26 && x == 79) expected = 0x2468;
            }
            assert(pixels[y * PITCH + x] == expected);
        }
    }
    assert(guarded[0] == 0xdead && guarded[WORDS + 1] == 0xdead);
    memcpy(before, guarded, sizeof guarded);
    assert(xdj_waveform_cell_draw(pixels, WORDS, PITCH, columns, 80, 0, 0, 0) == XDJ_CELL_SKIPPED);
    assert(memcmp(before, guarded, sizeof guarded) == 0);

    /* A second frame must clear prior peaks, including full height and last x. */
    memset(columns, 0, sizeof columns);
    assert(xdj_waveform_cell_draw(pixels, WORDS, PITCH, columns, 80, 7, 9, 1) == XDJ_CELL_DRAWN);
    for (y = 0; y < 28; ++y)
        for (x = 0; x < 80; ++x)
            assert(pixels[y * PITCH + x] == (y == 27 ? 9 : 7));
    return 0;
}
