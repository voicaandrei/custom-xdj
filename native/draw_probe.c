#include "draw_probe.h"

xdj_cell_result xdj_draw_probe(uint16_t *destination, size_t capacity_words,
    size_t pitch_words, xdj_probe_stage stage, xdj_channel_order order, int enabled)
{
    xdj_wave_column columns[XDJ_CELL_WIDTH];
    size_t x;
    uint16_t red, green, blue, white;
    if (!enabled)
        return XDJ_CELL_SKIPPED;
    if ((stage != XDJ_PROBE_RED && stage != XDJ_PROBE_CHANNELS &&
         stage != XDJ_PROBE_GEOMETRY) ||
        (order != XDJ_CHANNEL_ORDER_RGB && order != XDJ_CHANNEL_ORDER_BGR))
        return XDJ_CELL_INVALID;
    red = xdj_pack_rgb8_ordered(255, 0, 0, order);
    green = xdj_pack_rgb8_ordered(0, 255, 0, order);
    blue = xdj_pack_rgb8_ordered(0, 0, 255, order);
    white = xdj_pack_rgb8_ordered(255, 255, 255, order);
    for (x = 0; x < XDJ_CELL_WIDTH; ++x) {
        columns[x].back_height = XDJ_CELL_AMPLITUDE_HEIGHT;
        columns[x].front_height = 0;
        columns[x].front_color = 0;
        columns[x].back_color = stage == XDJ_PROBE_RED ? red :
            (x < 26 ? red : (x < 53 ? green : blue));
        if (stage == XDJ_PROBE_GEOMETRY) {
            /* Four distinct heights. Lower edge is always the baseline. */
            columns[x].back_height = x < 20 ? 3 : (x < 40 ? 9 : (x < 60 ? 18 : 27));
            columns[x].back_color = white;
        }
    }
    return xdj_waveform_cell_draw(destination, capacity_words, pitch_words,
        columns, XDJ_CELL_WIDTH, 0, stage == XDJ_PROBE_RED ? red : white, 1);
}
