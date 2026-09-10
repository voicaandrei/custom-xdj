#ifndef XDJ_WAVEFORM_PREPARE_H
#define XDJ_WAVEFORM_PREPARE_H

#include "waveform_cell.h"

#define XDJ_PWAV_BYTES 400u
#define XDJ_PWV4_BYTES 7200u
#define XDJ_PWAV_SAMPLES 400u
#define XDJ_PWV4_SAMPLES 1200u

/* Application-owned conversion, not an inferred firmware ABI. Must be pure,
 * total for all RGB8 inputs, and return the surface's verified native word.
 * No default RGB565 assumption. No device implementation is supplied yet. */
typedef uint16_t (*xdj_pack_rgb8)(uint8_t r, uint8_t g, uint8_t b, void *context);

typedef enum {
    XDJ_PREVIEW_INVALID = -1,
    XDJ_PREVIEW_PREPARED = 1
} xdj_prepare_result;

/* Input is the payload of an already validated ANLZ tag, not a file/header.
 * PWAV: 400 packed bytes. PWV4: 1200 records of 6 bytes, RGB at +3/+4/+5.
 *
 * The scaled forms take the target rectangle: `count` columns and heights in
 * 0..amplitude_height. Column x covers samples [x*n/count, (x+1)*n/count),
 * the same disjoint-interval rule the host resampler uses, so no sample is
 * dropped or counted twice. Downsampling only: count must not exceed the
 * sample count. Bucket maximum, first sample wins ties, independent layers.
 *
 * RGB normalization uses the whole track. These are our preview choices, not
 * proven stock MK2 pixel parity. Call before repaint; no allocation, file IO
 * or cache/global state. Caller provides valid disjoint input/output storage
 * and owns its lifetime. Invalid arguments leave the output unchanged and do
 * not invoke pack. Caller must not publish it until the call returns.
 */
xdj_prepare_result xdj_prepare_pwav_scaled(
    const uint8_t *payload, size_t bytes, xdj_wave_column *output, size_t count,
    unsigned int amplitude_height, xdj_pack_rgb8 pack, void *context);

xdj_prepare_result xdj_prepare_pwv4_scaled(
    const uint8_t *payload, size_t bytes, xdj_wave_column *output, size_t count,
    unsigned int amplitude_height, xdj_pack_rgb8 pack, void *context);

/* The list row cell: 80 columns, heights 0..27. */
xdj_prepare_result xdj_prepare_pwav(
    const uint8_t *payload, size_t bytes, xdj_wave_column *output, size_t count,
    xdj_pack_rgb8 pack, void *context);

xdj_prepare_result xdj_prepare_pwv4(
    const uint8_t *payload, size_t bytes, xdj_wave_column *output, size_t count,
    xdj_pack_rgb8 pack, void *context);

#endif
