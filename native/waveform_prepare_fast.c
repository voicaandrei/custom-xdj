#include "waveform_prepare_fast.h"

static unsigned int divide(unsigned int n, unsigned int d)
{
    unsigned int result = 0, divisor = d;
    int shift = 0;
    while (divisor <= (n >> 1)) { divisor <<= 1; ++shift; }
    while (shift-- >= 0) {
        result <<= 1;
        if (n >= divisor) { n -= divisor; result |= 1u; }
        divisor >>= 1;
    }
    return result;
}

typedef struct { unsigned int end, remainder, step, extra, width; } buckets;
static buckets begin(unsigned int samples, unsigned int width)
{
    buckets b;
    b.end = b.remainder = 0;
    b.step = divide(samples, width);
    b.extra = samples - b.step * width;
    b.width = width;
    return b;
}
static unsigned int advance(buckets *b)
{
    b->end += b->step;
    b->remainder += b->extra;
    if (b->remainder >= b->width) {
        ++b->end;
        b->remainder -= b->width;
    }
    return b->end;
}
static uint8_t magnitude(const uint8_t *rgb)
{
    uint8_t m = rgb[0] > rgb[1] ? rgb[0] : rgb[1];
    return m > rgb[2] ? m : rgb[2];
}
static unsigned int maximum(const uint8_t *payload)
{
    unsigned int i, m = 1;
    for (i = 0; i < XDJ_PWV4_SAMPLES; ++i) {
        unsigned int value = magnitude(payload + i * 6u + 3u);
        if (value > m) m = value;
    }
    return m;
}
static uint8_t pixels(unsigned int value, unsigned int max, unsigned int height)
{
    return (uint8_t)divide(value * height + (max >> 1), max);
}
static uint16_t color(const uint8_t *rgb, unsigned int level,
                     xdj_pack_rgb8 pack, void *context)
{
    unsigned int m = magnitude(rgb);
    if (!m) return pack(0, 0, 0, context);
    return pack((uint8_t)divide(rgb[0] * level, m),
                (uint8_t)divide(rgb[1] * level, m),
                (uint8_t)divide(rgb[2] * level, m), context);
}
static int valid(const xdj_prepare_target *t, size_t samples)
{
    return t && t->columns && t->count >= 1u && t->count <= samples
        && t->amplitude_height >= 1u && t->amplitude_height <= 255u;
}
static void blue(const uint8_t *payload, const xdj_prepare_target *t,
                 xdj_pack_rgb8 pack, void *context)
{
    unsigned int x, start = 0;
    buckets b = begin(XDJ_PWAV_SAMPLES, (unsigned int)t->count);
    for (x = 0; x < t->count; ++x) {
        unsigned int end = advance(&b), i, best = start;
        xdj_wave_column *out = t->columns + x;
        for (i = start + 1u; i < end; ++i)
            if ((payload[i] & 31u) > (payload[best] & 31u)) best = i;
        out->back_height = pixels(payload[best] & 31u, 31u, t->amplitude_height);
        out->front_height = 0;
        out->back_color = (payload[best] >> 5) >= 5u
            ? pack(116, 246, 244, context) : pack(43, 89, 255, context);
        out->front_color = 0;
        start = end;
    }
}
static void rgb(const uint8_t *payload, const xdj_prepare_target *t,
                unsigned int max, xdj_pack_rgb8 pack, void *context)
{
    unsigned int x, start = 0;
    buckets b = begin(XDJ_PWV4_SAMPLES, (unsigned int)t->count);
    for (x = 0; x < t->count; ++x) {
        unsigned int end = advance(&b), i;
        const uint8_t *back = payload + start * 6u + 3u, *front = back;
        xdj_wave_column *out = t->columns + x;
        for (i = start + 1u; i < end; ++i) {
            const uint8_t *p = payload + i * 6u + 3u;
            if (magnitude(p) > magnitude(back)) back = p;
            if (p[2] > front[2]) front = p;
        }
        out->back_height = pixels(magnitude(back), max, t->amplitude_height);
        out->front_height = pixels(front[2], max, t->amplitude_height);
        out->back_color = color(back, 191u, pack, context);
        out->front_color = color(front, 255u, pack, context);
        start = end;
    }
}
xdj_prepare_result xdj_fast_prepare_pwav_scaled(const uint8_t *payload,
    size_t bytes, xdj_wave_column *out, size_t count, unsigned int height,
    xdj_pack_rgb8 pack, void *context)
{
    xdj_prepare_target t = {out, count, height};
    if (!payload || bytes != XDJ_PWAV_BYTES || !pack || !valid(&t, XDJ_PWAV_SAMPLES))
        return XDJ_PREVIEW_INVALID;
    blue(payload, &t, pack, context);
    return XDJ_PREVIEW_PREPARED;
}
xdj_prepare_result xdj_fast_prepare_pwv4_scaled(const uint8_t *payload,
    size_t bytes, xdj_wave_column *out, size_t count, unsigned int height,
    xdj_pack_rgb8 pack, void *context)
{
    xdj_prepare_target t = {out, count, height};
    if (!payload || bytes != XDJ_PWV4_BYTES || !pack || !valid(&t, XDJ_PWV4_SAMPLES))
        return XDJ_PREVIEW_INVALID;
    rgb(payload, &t, maximum(payload), pack, context);
    return XDJ_PREVIEW_PREPARED;
}
xdj_prepare_result xdj_fast_prepare_pair(const uint8_t *payload, size_t bytes,
    int is_rgb, const xdj_prepare_target targets[2], xdj_pack_rgb8 pack, void *context)
{
    size_t samples = is_rgb ? XDJ_PWV4_SAMPLES : XDJ_PWAV_SAMPLES;
    size_t expected = is_rgb ? XDJ_PWV4_BYTES : XDJ_PWAV_BYTES;
    if ((is_rgb != 0 && is_rgb != 1) || !payload || bytes != expected || !pack
        || !targets || !valid(targets, samples) || !valid(targets+1, samples))
        return XDJ_PREVIEW_INVALID;
    if (is_rgb) {
        unsigned int max = maximum(payload);
        rgb(payload, targets, max, pack, context);
        rgb(payload, targets+1, max, pack, context);
    } else {
        blue(payload, targets, pack, context);
        blue(payload, targets+1, pack, context);
    }
    return XDJ_PREVIEW_PREPARED;
}
