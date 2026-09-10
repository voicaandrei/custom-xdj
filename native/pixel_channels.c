#include "pixel_channels.h"

uint16_t xdj_pack_channels565(uint8_t c0, uint8_t c1, uint8_t c2)
{
    return (uint16_t)(((uint16_t)(c0 >> 3) << 11) |
                      ((uint16_t)(c1 >> 2) << 5) | (uint16_t)(c2 >> 3));
}

uint16_t xdj_pack_rgb8_ordered(uint8_t red, uint8_t green, uint8_t blue,
                               xdj_channel_order order)
{
    if (order == XDJ_CHANNEL_ORDER_BGR)
        return xdj_pack_channels565(blue, green, red);
    return xdj_pack_channels565(red, green, blue);
}

uint16_t xdj_pack_rgb8_context(uint8_t red, uint8_t green, uint8_t blue,
                               void *context)
{
    xdj_channel_order order = XDJ_CHANNEL_ORDER_RGB;
    if (context != 0 && *(const xdj_channel_order *)context == XDJ_CHANNEL_ORDER_BGR)
        order = XDJ_CHANNEL_ORDER_BGR;
    return xdj_pack_rgb8_ordered(red, green, blue, order);
}
