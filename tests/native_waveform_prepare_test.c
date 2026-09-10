#include "waveform_prepare.h"
#include <assert.h>
#include <string.h>

static unsigned int calls;
static uint16_t pack(uint8_t r, uint8_t g, uint8_t b, void *context)
{
    assert(context == &calls);
    ++calls;
    /* Test token only; deliberately not a device pixel format. */
    return (uint16_t)(r * 251u + g * 17u + b);
}

int main(void)
{
    uint8_t wav[XDJ_PWAV_BYTES] = {0}, rgb[XDJ_PWV4_BYTES] = {0};
    struct { uint16_t before; xdj_wave_column columns[80]; uint16_t after; } guarded;
    xdj_wave_column saved[80];
    uint16_t surface[80 * 28];
    size_t i;
    memset(&guarded, 0xa5, sizeof guarded);
    memcpy(saved, guarded.columns, sizeof saved);
    assert(xdj_prepare_pwav(wav, 399, guarded.columns, 80, pack, &calls) == -1);
    assert(xdj_prepare_pwv4(rgb, 7201, guarded.columns, 80, pack, &calls) == -1);
    assert(xdj_prepare_pwav(NULL, 400, guarded.columns, 80, pack, &calls) == -1);
    assert(xdj_prepare_pwv4(rgb, 7200, NULL, 80, pack, &calls) == -1);
    assert(xdj_prepare_pwav(wav, 400, guarded.columns, 79, pack, &calls) == -1);
    assert(xdj_prepare_pwv4(rgb, 7200, guarded.columns, 80, NULL, &calls) == -1);
    assert(calls == 0 && memcmp(saved, guarded.columns, sizeof saved) == 0);
    wav[0] = 31; wav[1] = 255; /* Equal peak, first shade must win. */
    wav[399] = 255; /* Last source sample is included. */
    assert(xdj_prepare_pwav(wav, 400, guarded.columns, 80, pack, &calls) == 1);
    assert(calls == 80);
    assert(guarded.columns[0].back_height == 27);
    assert(guarded.columns[0].back_color == (uint16_t)(43u*251u+89u*17u+255u));
    assert(guarded.columns[79].back_height == 27);
    assert(guarded.columns[79].back_color == (uint16_t)(116u*251u+246u*17u+244u));
    for (i = 1; i < 79; ++i) assert(guarded.columns[i].back_height == 0);
    assert(xdj_prepare_pwv4(rgb, 7200, guarded.columns, 80, pack, &calls) == 1);
    for (i = 0; i < 80; ++i) {
        assert(guarded.columns[i].back_height == 0 && guarded.columns[i].front_height == 0);
        assert(guarded.columns[i].back_color == 0 && guarded.columns[i].front_color == 0);
    }
    rgb[3] = 200; /* Back peak and front peak are different source records. */
    rgb[6+5] = 100;
    rgb[12+4] = 200; /* Back tie must preserve the first (red) source. */
    rgb[7199] = 255; /* Global scale, last bucket. */
    assert(xdj_prepare_pwv4(rgb, 7200, guarded.columns, 80, pack, &calls) == 1);
    assert(guarded.columns[0].back_height == 21 && guarded.columns[0].front_height == 11);
    assert(guarded.columns[0].back_color == (uint16_t)(191u * 251u));
    assert(guarded.columns[0].front_color == 255);
    assert(guarded.columns[79].front_height == 27);
    assert(guarded.before == 0xa5a5 && guarded.after == 0xa5a5);
    assert(xdj_waveform_cell_draw(surface, 80*28, 80, guarded.columns, 80, 0, 42, 1) == 1);
    assert(surface[0] == 0 && surface[79] == 255);
    assert(surface[27*80] == 42);
    return 0;
}
