#include "waveform_prepare.h"

/* SH-4A has no integer divide instruction, so a compiler targeting it turns a
 * variable divisor into a libgcc helper call. A freestanding adapter has no
 * libgcc, so every division below is done with shift and subtract instead.
 * Exact floor division; the divisor is never zero at any call site here. */
static unsigned int divide(unsigned int numerator, unsigned int denominator)
{
    unsigned int quotient = 0, divisor = denominator;
    int shift = 0;
    while (divisor <= (numerator >> 1)) {
        divisor <<= 1;
        ++shift;
    }
    while (shift-- >= 0) {
        quotient <<= 1;
        if (numerator >= divisor) {
            numerator -= divisor;
            quotient |= 1u;
        }
        divisor >>= 1;
    }
    return quotient;
}

static uint8_t pixels(unsigned int value, unsigned int maximum,
                      unsigned int amplitude_height)
{
    return (uint8_t)divide(value * amplitude_height + (maximum >> 1), maximum);
}

static uint8_t magnitude(const uint8_t *rgb)
{
    uint8_t value = rgb[0] > rgb[1] ? rgb[0] : rgb[1];
    return value > rgb[2] ? value : rgb[2];
}

static uint16_t color(const uint8_t *rgb, unsigned int level,
                      xdj_pack_rgb8 pack, void *context)
{
    unsigned int maximum = magnitude(rgb);
    if (maximum == 0u)
        return pack(0, 0, 0, context);
    return pack((uint8_t)divide(rgb[0] * level, maximum),
                (uint8_t)divide(rgb[1] * level, maximum),
                (uint8_t)divide(rgb[2] * level, maximum), context);
}

/* Common argument checks. Downsampling only, and heights must fit a byte. */
static int usable(const uint8_t *payload, size_t bytes, size_t expected,
                  const xdj_wave_column *output, size_t count,
                  unsigned int amplitude_height, size_t samples,
                  xdj_pack_rgb8 pack)
{
    return payload != 0 && output != 0 && pack != 0 && bytes == expected
           && count >= 1u && count <= samples
           && amplitude_height >= 1u && amplitude_height <= 255u;
}

xdj_prepare_result xdj_prepare_pwav_scaled(
    const uint8_t *payload, size_t bytes, xdj_wave_column *output, size_t count,
    unsigned int amplitude_height, xdj_pack_rgb8 pack, void *context)
{
    size_t x, start = 0;
    if (!usable(payload, bytes, XDJ_PWAV_BYTES, output, count, amplitude_height,
                XDJ_PWAV_SAMPLES, pack))
        return XDJ_PREVIEW_INVALID;
    for (x = 0; x < count; ++x) {
        const size_t end = divide((unsigned int)((x + 1u) * XDJ_PWAV_SAMPLES),
                                  (unsigned int)count);
        size_t i, best = start;
        for (i = start + 1u; i < end; ++i)
            if ((payload[i] & 31u) > (payload[best] & 31u)) best = i;
        output[x].back_height = pixels(payload[best] & 31u, 31u, amplitude_height);
        output[x].front_height = 0;
        output[x].back_color = (payload[best] >> 5) >= 5u
            ? pack(116, 246, 244, context) : pack(43, 89, 255, context);
        output[x].front_color = 0; /* Unused when front_height is zero. */
        start = end;
    }
    return XDJ_PREVIEW_PREPARED;
}

xdj_prepare_result xdj_prepare_pwv4_scaled(
    const uint8_t *payload, size_t bytes, xdj_wave_column *output, size_t count,
    unsigned int amplitude_height, xdj_pack_rgb8 pack, void *context)
{
    size_t x, i, start = 0;
    unsigned int maximum = 1;
    if (!usable(payload, bytes, XDJ_PWV4_BYTES, output, count, amplitude_height,
                XDJ_PWV4_SAMPLES, pack))
        return XDJ_PREVIEW_INVALID;
    for (i = 0; i < XDJ_PWV4_SAMPLES; ++i) {
        unsigned int value = magnitude(payload + i * 6u + 3u);
        if (value > maximum) maximum = value;
    }
    for (x = 0; x < count; ++x) {
        const size_t end = divide((unsigned int)((x + 1u) * XDJ_PWV4_SAMPLES),
                                  (unsigned int)count);
        const uint8_t *back = payload + start * 6u + 3u, *front = back;
        for (i = start + 1u; i < end; ++i) {
            const uint8_t *rgb = payload + i * 6u + 3u;
            if (magnitude(rgb) > magnitude(back)) back = rgb;
            if (rgb[2] > front[2]) front = rgb;
        }
        output[x].back_height = pixels(magnitude(back), maximum, amplitude_height);
        output[x].front_height = pixels(front[2], maximum, amplitude_height);
        output[x].back_color = color(back, 191u, pack, context);
        output[x].front_color = color(front, 255u, pack, context);
        start = end;
    }
    return XDJ_PREVIEW_PREPARED;
}

xdj_prepare_result xdj_prepare_pwav(
    const uint8_t *payload, size_t bytes, xdj_wave_column *output, size_t count,
    xdj_pack_rgb8 pack, void *context)
{
    if (count != XDJ_CELL_WIDTH)
        return XDJ_PREVIEW_INVALID;
    return xdj_prepare_pwav_scaled(payload, bytes, output, count,
                                   XDJ_CELL_AMPLITUDE_HEIGHT, pack, context);
}

xdj_prepare_result xdj_prepare_pwv4(
    const uint8_t *payload, size_t bytes, xdj_wave_column *output, size_t count,
    xdj_pack_rgb8 pack, void *context)
{
    if (count != XDJ_CELL_WIDTH)
        return XDJ_PREVIEW_INVALID;
    return xdj_prepare_pwv4_scaled(payload, bytes, output, count,
                                   XDJ_CELL_AMPLITUDE_HEIGHT, pack, context);
}
