#ifndef XDJ_WAVEFORM_CELL_H
#define XDJ_WAVEFORM_CELL_H

#include <stddef.h>
#include <stdint.h>

/* Portable rendering core, not a firmware hook or a device ABI declaration.
 * Each height is already resampled/scaled to pixels, before repaint.
 * Colors are opaque native 16-bit words: no RGB565/RGB555 assumption here.
 *
 * Two geometries are known statically in 1.44: the list row cell, 80 x 28, and
 * the INFO panel cell, 128 x 121. The core takes the rectangle as arguments so
 * neither is baked in; the constants below only name the row cell.
 */
#define XDJ_CELL_WIDTH 80u
#define XDJ_CELL_HEIGHT 28u
#define XDJ_CELL_AMPLITUDE_HEIGHT (XDJ_CELL_HEIGHT - 1u)

typedef struct {
    uint8_t back_height;
    uint8_t front_height;
    uint16_t back_color;
    uint16_t front_color;
} xdj_wave_column;

typedef enum {
    XDJ_CELL_INVALID = -1,
    XDJ_CELL_SKIPPED = 0,
    XDJ_CELL_DRAWN = 1
} xdj_cell_result;

/* Draw into rows [top_row, top_row + height) of the destination, leaving every
 * other row untouched. That is what makes a strip at the bottom of a taller
 * cell possible without disturbing whatever is above it.
 *
 * The last row of the region is the baseline; the remaining height - 1 rows
 * carry amplitude, drawn upward from it. height must be at least 2 and every
 * column height at most height - 1.
 *
 * Caller owns the destination and must acquire/release its surface correctly.
 * destination_words is capacity from destination, not total allocation size.
 * pitch_words is row stride in uint16_t units, never bytes.
 * columns must not overlap destination. No allocations, parsing, resampling,
 * device access, global state, or stock-firmware calls occur here. Disabled or
 * missing preview leaves the destination untouched; the caller retains stock
 * artwork handling. Invalid geometry or heights also cause no writes.
 */
xdj_cell_result xdj_waveform_cell_draw_region(
    uint16_t *destination, size_t destination_words, size_t pitch_words,
    size_t top_row, size_t width, size_t height,
    const xdj_wave_column *columns, size_t column_count,
    uint16_t background, uint16_t baseline, int enabled);

/* The list row cell: the whole 80 x 28 rectangle, starting at row 0. */
xdj_cell_result xdj_waveform_cell_draw(
    uint16_t *destination, size_t destination_words, size_t pitch_words,
    const xdj_wave_column *columns, size_t column_count,
    uint16_t background, uint16_t baseline, int enabled);

#endif
