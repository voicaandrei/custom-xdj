/* Local next-candidate experiment, not linked into BETA 11.
 * Optimized preparation and invalid-input hardening only; task handoff
 * identity and real synchronization remain separate integration work. */
#include "beta_runtime.h"
#include "pixel_channels.h"
#include "waveform_cell.h"
#include "waveform_prepare_fast.h"

#define XDJ_BETA_ROW_WIDTH 80u
#define XDJ_BETA_ROW_HEIGHT 28u
#define XDJ_BETA_ROW_WORDS (XDJ_BETA_ROW_WIDTH * XDJ_BETA_ROW_HEIGHT)
#define XDJ_BETA_INFO_VISIBLE_WIDTH 290u
#define XDJ_BETA_INFO_STRIDE 290u
#define XDJ_BETA_INFO_HEIGHT 28u
#define XDJ_BETA_INFO_WORDS (XDJ_BETA_INFO_STRIDE * XDJ_BETA_INFO_HEIGHT)

typedef struct {
    volatile uint32_t valid;
    uint32_t track_id;
    uint16_t row[XDJ_BETA_ROW_WORDS];
    uint16_t info[XDJ_BETA_INFO_WORDS];
    xdj_wave_column columns[XDJ_BETA_INFO_VISIBLE_WIDTH];
    xdj_wave_column row_columns[XDJ_BETA_ROW_WIDTH];
    uint8_t blue[XDJ_PWAV_BYTES];
} xdj_beta_state;

/* A named PROGBITS section makes the zeroed state part of the decompressed
 * extension. The stock startup knows nothing about this new storage. */
#if defined(__sh__)
__attribute__((section(".xdj_beta_state"), aligned(16), used))
#endif
static xdj_beta_state state = {0};

const char xdj_beta_pwv4_tag[5] = "PWV4";
const char xdj_beta_ext_name[4] = "EXT";

static uint32_t be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16)
        | ((uint32_t)p[2] << 8) | p[3];
}

static int render(const uint8_t *payload, size_t bytes, int rgb,
                  uint32_t track_id)
{
    xdj_prepare_result prepared;
    xdj_cell_result drawn;
    xdj_channel_order order = XDJ_CHANNEL_ORDER_RGB;

    xdj_prepare_target targets[2] = {
        {state.columns, XDJ_BETA_INFO_VISIBLE_WIDTH, XDJ_BETA_INFO_HEIGHT - 1u},
        {state.row_columns, XDJ_BETA_ROW_WIDTH, XDJ_BETA_ROW_HEIGHT - 1u}
    };
    state.valid = 0;
    prepared = xdj_fast_prepare_pair(payload, bytes, rgb, targets,
                                     xdj_pack_rgb8_context, &order);
    if (prepared != XDJ_PREVIEW_PREPARED)
        return 0;
    drawn = xdj_waveform_cell_draw_region(
        state.info, XDJ_BETA_INFO_WORDS, XDJ_BETA_INFO_STRIDE,
        0, XDJ_BETA_INFO_VISIBLE_WIDTH, XDJ_BETA_INFO_HEIGHT,
        state.columns, XDJ_BETA_INFO_VISIBLE_WIDTH,
        0x0000u, 0xffffu, 1);
    if (drawn != XDJ_CELL_DRAWN)
        return 0;

    drawn = xdj_waveform_cell_draw_region(
        state.row, XDJ_BETA_ROW_WORDS, XDJ_BETA_ROW_WIDTH,
        0, XDJ_BETA_ROW_WIDTH, XDJ_BETA_ROW_HEIGHT,
        state.row_columns, XDJ_BETA_ROW_WIDTH, 0x0000u, 0xffffu, 1);
    if (drawn != XDJ_CELL_DRAWN)
        return 0;

    state.track_id = track_id;
    state.valid = 1;
    return 1;
}

void xdj_beta_invalidate(void)
{
    state.valid = 0;
}

int xdj_beta_prepare_rgb(const uint8_t *blob, uint32_t bytes, uint32_t track_id)
{
    state.valid = 0;
    if (!blob || !track_id || bytes != 7228u
        || blob[0] != 0x38u || blob[1] != 0x1cu || blob[2] || blob[3]
        || blob[4] != 'P' || blob[5] != 'W' || blob[6] != 'V'
        || blob[7] != '4' || be32(blob + 8) != 24u
        || be32(blob + 12) != 7224u || be32(blob + 16) != 6u
        || be32(blob + 20) != 1200u)
        return 0;
    return render(blob + 28, XDJ_PWV4_BYTES, 1, track_id);
}

int xdj_beta_prepare_blue(const uint8_t *blob, uint32_t bytes,
                          uint32_t track_id)
{
    size_t i;
    state.valid = 0;
    if (!blob || !track_id || bytes != 900u)
        return 0;
    for (i = 0; i < 800u; i += 2u) {
        if (blob[i] > 31u || blob[i + 1u] > 7u)
            return 0;
    }
    for (i = 0; i < XDJ_PWAV_BYTES; ++i)
        state.blue[i] = (uint8_t)(blob[2u * i]
            | (uint8_t)(blob[2u * i + 1u] << 5));
    return render(state.blue, XDJ_PWAV_BYTES, 0, track_id);
}

int xdj_beta_apply_surfaces(uint16_t *row_surface, uint16_t *info_surface)
{
    size_t i;
    if (!state.valid || !row_surface || !info_surface)
        return 0;
    /* One-shot consumption only. Caller must serialize producer/consumer;
     * this flag does not protect against a producer overwriting during copy. */
    state.valid = 0;
    for (i = 0; i < XDJ_BETA_ROW_WORDS; ++i)
        row_surface[i] = state.row[i];
    for (i = 0; i < XDJ_BETA_INFO_WORDS; ++i)
        info_surface[i] = state.info[i];
    return 1;
}

void xdj_beta_trace_reset(void) { xdj_beta_invalidate(); }
void xdj_beta_trace(uint32_t stage) { (void)stage; }
int xdj_beta_apply_or_trace_surfaces(uint16_t *row, uint16_t *info)
{
    int applied = xdj_beta_apply_surfaces(row, info);
    if (!applied && info) {
        size_t i;
        for (i = 0; i < XDJ_BETA_INFO_WORDS; ++i) info[i] = 0;
    }
    return applied;
}
