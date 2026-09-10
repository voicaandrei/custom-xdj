#include "waveform_cell.h"

xdj_cell_result xdj_waveform_cell_draw_region(
    uint16_t *destination, size_t destination_words, size_t pitch_words,
    size_t top_row, size_t width, size_t height,
    const xdj_wave_column *columns, size_t column_count,
    uint16_t background, uint16_t baseline, int enabled)
{
    size_t x, y, amplitude, last_row, needed;
    if (!enabled || columns == NULL)
        return XDJ_CELL_SKIPPED;
    if (destination == NULL || width == 0 || height < 2 || column_count != width ||
        pitch_words < width)
        return XDJ_CELL_INVALID;
    amplitude = height - 1u;
    /* Every product and sum below is checked before it is formed. */
    if (top_row > SIZE_MAX - amplitude)
        return XDJ_CELL_INVALID;
    /* height >= 2 makes amplitude >= 1, so last_row is never zero. */
    last_row = top_row + amplitude;
    if (pitch_words > SIZE_MAX / last_row)
        return XDJ_CELL_INVALID;
    needed = last_row * pitch_words;
    if (needed > SIZE_MAX - width)
        return XDJ_CELL_INVALID;
    needed += width;
    if (destination_words < needed)
        return XDJ_CELL_INVALID;
    /* Validate the entire preview before changing a single destination word. */
    for (x = 0; x < width; ++x) {
        if (columns[x].back_height > amplitude || columns[x].front_height > amplitude)
            return XDJ_CELL_INVALID;
    }
    for (y = 0; y < amplitude; ++y) {
        const size_t level = amplitude - y;
        uint16_t *row = destination + (top_row + y) * pitch_words;
        for (x = 0; x < width; ++x) {
            uint16_t pixel = background;
            if (columns[x].back_height >= level)
                pixel = columns[x].back_color;
            if (columns[x].front_height >= level)
                pixel = columns[x].front_color;
            row[x] = pixel;
        }
    }
    for (x = 0; x < width; ++x)
        destination[last_row * pitch_words + x] = baseline;
    return XDJ_CELL_DRAWN;
}

xdj_cell_result xdj_waveform_cell_draw(
    uint16_t *destination, size_t destination_words, size_t pitch_words,
    const xdj_wave_column *columns, size_t column_count,
    uint16_t background, uint16_t baseline, int enabled)
{
    return xdj_waveform_cell_draw_region(destination, destination_words, pitch_words,
                                         0, XDJ_CELL_WIDTH, XDJ_CELL_HEIGHT,
                                         columns, column_count,
                                         background, baseline, enabled);
}
