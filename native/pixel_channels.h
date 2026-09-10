#ifndef XDJ_PIXEL_CHANNELS_H
#define XDJ_PIXEL_CHANNELS_H

#include <stdint.h>

/* Reproduces the inspected stock channel bit placement: byte 0 -> high 5,
 * byte 1 -> middle 6, byte 2 -> low 5. No alpha bit in this word.
 * Channel semantic order (RGB versus BGR) is not proven by the bit operations.
 * Do not automatically bind this to the RGB8 preparation callback until that
 * order and the target surface contract have been independently verified.
 * Pure original arithmetic, no firmware calls, addresses or device writes.
 */
uint16_t xdj_pack_channels565(uint8_t c0, uint8_t c1, uint8_t c2);

/* Which semantic channel the stock word carries in its high five bits.
 * Both orders remain possible from the inspected bit operations alone; the
 * value is a parameter precisely so a single controlled observation can settle
 * it without touching the rendering core. Neither value is a claim. */
typedef enum {
    XDJ_CHANNEL_ORDER_RGB = 0, /* high 5 bits carry red, low 5 carry blue */
    XDJ_CHANNEL_ORDER_BGR = 1  /* high 5 bits carry blue, low 5 carry red */
} xdj_channel_order;

/* Pack an RGB8 triplet under an explicit order. Total for every input. */
uint16_t xdj_pack_rgb8_ordered(uint8_t red, uint8_t green, uint8_t blue,
                               xdj_channel_order order);

/* Matches the xdj_pack_rgb8 callback of waveform_prepare.h. context must point
 * to one xdj_channel_order and stays owned and alive by the caller. An unknown
 * order value is treated as XDJ_CHANNEL_ORDER_RGB so the callback stays total,
 * as its contract requires; it is not a statement about the hardware. */
uint16_t xdj_pack_rgb8_context(uint8_t red, uint8_t green, uint8_t blue,
                               void *context);

#endif
