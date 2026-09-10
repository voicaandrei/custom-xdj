/* Test 05 adds visual tracing around the unchanged Test 04 renderer. Keeping
 * the renderer included here lets the Test 04 source remain byte-reproducible. */
#include "beta_runtime.c"

#define XDJ_TRACE_MAX_STAGE 11u
#define XDJ_TRACE_ROW_TOP 21u
#define XDJ_TRACE_INFO_TOP 106u
#define XDJ_TRACE_BAR_WIDTH 4u
#define XDJ_TRACE_BAR_STEP 7u
#define XDJ_TRACE_BLUE 0x001fu
#define XDJ_TRACE_WHITE 0xffffu

#if defined(__sh__)
__attribute__((section(".xdj_beta_state"), aligned(4), used))
#endif
static volatile uint32_t trace_stage = 0;

void xdj_beta_trace_reset(void)
{
    xdj_beta_invalidate();
    trace_stage = 1u;
}

void xdj_beta_trace(uint32_t stage)
{
    if (stage <= XDJ_TRACE_MAX_STAGE)
        trace_stage = stage;
}

static void trace_strip(uint16_t *surface, size_t words, size_t stride,
                        size_t width, size_t top, size_t height,
                        uint32_t stage)
{
    size_t x;
    size_t y;
    size_t bars = stage;
    if (bars > XDJ_TRACE_MAX_STAGE)
        bars = XDJ_TRACE_MAX_STAGE;
    if (!surface || !stride || width > stride || top + height > words / stride)
        return;
    for (y = top; y < top + height; ++y) {
        for (x = 0; x < width; ++x)
            surface[y * stride + x] = XDJ_TRACE_BLUE;
    }
    for (x = 0; x < bars; ++x) {
        size_t left = 2u + x * XDJ_TRACE_BAR_STEP;
        size_t right = left + XDJ_TRACE_BAR_WIDTH;
        size_t column;
        if (left >= width)
            break;
        if (right > width)
            right = width;
        for (y = top + 1u; y + 1u < top + height; ++y) {
            for (column = left; column < right; ++column)
                surface[y * stride + column] = XDJ_TRACE_WHITE;
        }
    }
}

int xdj_beta_apply_or_trace_surfaces(uint16_t *row_surface,
                                     uint16_t *info_surface)
{
    uint32_t stage;
    int applied = xdj_beta_apply_surfaces(row_surface, info_surface);
    if (applied)
        return 1;
    if (!row_surface || !info_surface)
        return 0;
    stage = trace_stage;
    trace_strip(row_surface, XDJ_BETA_ROW_WORDS, XDJ_BETA_ROW_WIDTH,
                XDJ_BETA_ROW_WIDTH, XDJ_TRACE_ROW_TOP,
                XDJ_BETA_ROW_HEIGHT - XDJ_TRACE_ROW_TOP, stage);
    trace_strip(info_surface, XDJ_BETA_INFO_WORDS, XDJ_BETA_INFO_STRIDE,
                XDJ_BETA_INFO_VISIBLE_WIDTH, XDJ_TRACE_INFO_TOP,
                XDJ_BETA_INFO_HEIGHT - XDJ_TRACE_INFO_TOP, stage);
    return 2;
}
