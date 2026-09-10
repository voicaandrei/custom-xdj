#include "pixel_channels.h"
#include <assert.h>

int main(void)
{
    unsigned int value, other;
    assert(xdj_pack_channels565(0, 0, 0) == 0);
    assert(xdj_pack_channels565(255, 255, 255) == 0xffff);
    assert(xdj_pack_channels565(255, 0, 0) == 0xf800);
    assert(xdj_pack_channels565(0, 255, 0) == 0x07e0);
    assert(xdj_pack_channels565(0, 0, 255) == 0x001f);
    /* Check every channel value, quantization error, isolation and ordering. */
    for (value = 0; value < 256; ++value) {
        uint16_t high = xdj_pack_channels565((uint8_t)value, 0, 0);
        uint16_t mid = xdj_pack_channels565(0, (uint8_t)value, 0);
        uint16_t low = xdj_pack_channels565(0, 0, (uint8_t)value);
        assert((high & 0x07ff) == 0 && (mid & 0xf81f) == 0 && (low & 0xffe0) == 0);
        assert(value - (high / 2048u) * 8u < 8u);
        assert(value - (mid / 32u) * 4u < 4u);
        assert(value - low * 8u < 8u);
        for (other = 0; other < 256; ++other) {
            uint16_t mixed = xdj_pack_channels565((uint8_t)value, (uint8_t)other, (uint8_t)(255-value));
            assert((mixed & 0xf800) == high);
            assert((mixed & 0x07e0) == xdj_pack_channels565(0, (uint8_t)other, 0));
            assert((mixed & 0x001f) == xdj_pack_channels565(0, 0, (uint8_t)(255-value)));
        }
    }
    /* The order adapter only relabels the arguments; it never changes packing. */
    for (value = 0; value < 256; ++value) {
        for (other = 0; other < 256; ++other) {
            uint8_t r = (uint8_t)value, g = (uint8_t)other, b = (uint8_t)(255 - value);
            xdj_channel_order rgb = XDJ_CHANNEL_ORDER_RGB;
            xdj_channel_order bgr = XDJ_CHANNEL_ORDER_BGR;
            xdj_channel_order unknown = (xdj_channel_order)7;
            assert(xdj_pack_rgb8_ordered(r, g, b, XDJ_CHANNEL_ORDER_RGB)
                   == xdj_pack_channels565(r, g, b));
            assert(xdj_pack_rgb8_ordered(r, g, b, XDJ_CHANNEL_ORDER_BGR)
                   == xdj_pack_channels565(b, g, r));
            assert(xdj_pack_rgb8_context(r, g, b, &rgb)
                   == xdj_pack_rgb8_ordered(r, g, b, XDJ_CHANNEL_ORDER_RGB));
            assert(xdj_pack_rgb8_context(r, g, b, &bgr)
                   == xdj_pack_rgb8_ordered(r, g, b, XDJ_CHANNEL_ORDER_BGR));
            /* The callback must stay total: no context and no unknown order fail. */
            assert(xdj_pack_rgb8_context(r, g, b, 0)
                   == xdj_pack_rgb8_ordered(r, g, b, XDJ_CHANNEL_ORDER_RGB));
            assert(xdj_pack_rgb8_context(r, g, b, &unknown)
                   == xdj_pack_rgb8_ordered(r, g, b, XDJ_CHANNEL_ORDER_RGB));
        }
    }
    /* A pure primary distinguishes the two orders; this is what a single
     * controlled observation on the player would settle. */
    assert(xdj_pack_rgb8_ordered(255, 0, 0, XDJ_CHANNEL_ORDER_RGB) == 0xf800);
    assert(xdj_pack_rgb8_ordered(255, 0, 0, XDJ_CHANNEL_ORDER_BGR) == 0x001f);
    return 0;
}
