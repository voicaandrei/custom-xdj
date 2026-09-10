#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define ROW_WIDTH 80u
#define ROW_HEIGHT 28u
#define ROW_WORDS (ROW_WIDTH * ROW_HEIGHT)
#define INFO_WIDTH 109u
#define INFO_STRIDE 112u
#define INFO_HEIGHT 117u
#define INFO_WORDS (INFO_STRIDE * INFO_HEIGHT)

void xdj_beta_trace_reset(void);
void xdj_beta_trace(uint32_t stage);
int xdj_beta_prepare_rgb(const uint8_t *blob, uint32_t bytes,
                         uint32_t track_id);
int xdj_beta_apply_or_trace_surfaces(uint16_t *row_surface,
                                     uint16_t *info_surface);

static uint8_t rgb[7228];
static uint16_t row[ROW_WORDS + 2u];
static uint16_t info[INFO_WORDS + 2u];

static void read_exact(const char *path, void *destination, size_t bytes)
{
    FILE *file = fopen(path, "rb");
    assert(file != NULL);
    assert(fread(destination, 1, bytes, file) == bytes);
    assert(fgetc(file) == EOF);
    fclose(file);
}

static void reset_surfaces(void)
{
    size_t i;
    for (i = 0; i < ROW_WORDS + 2u; ++i)
        row[i] = 0x5a5au;
    for (i = 0; i < INFO_WORDS + 2u; ++i)
        info[i] = 0x5a5au;
}

static void check_trace(unsigned int stage)
{
    size_t bar;
    assert(row[0] == 0x5a5au && row[ROW_WORDS + 1u] == 0x5a5au);
    assert(info[0] == 0x5a5au && info[INFO_WORDS + 1u] == 0x5a5au);
    assert(row[1u + 21u * ROW_WIDTH] == 0x001fu);
    assert(info[1u + 106u * INFO_STRIDE] == 0x001fu);
    for (bar = 0; bar < stage; ++bar) {
        size_t x = 2u + bar * 7u;
        assert(row[1u + 22u * ROW_WIDTH + x] == 0xffffu);
        assert(info[1u + 107u * INFO_STRIDE + x] == 0xffffu);
    }
    assert(row[1u + 20u * ROW_WIDTH] == 0x5a5au);
    assert(info[1u + 105u * INFO_STRIDE] == 0x5a5au);
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    read_exact(argv[1], rgb, sizeof rgb);

    reset_surfaces();
    xdj_beta_trace_reset();
    assert(xdj_beta_apply_or_trace_surfaces(row + 1, info + 1) == 2);
    check_trace(1u);

    reset_surfaces();
    xdj_beta_trace(4u);
    assert(xdj_beta_apply_or_trace_surfaces(row + 1, info + 1) == 2);
    check_trace(4u);

    reset_surfaces();
    xdj_beta_trace(99u);
    assert(xdj_beta_apply_or_trace_surfaces(row + 1, info + 1) == 2);
    check_trace(4u);

    reset_surfaces();
    assert(xdj_beta_prepare_rgb(rgb, sizeof rgb, 3902u) == 1);
    xdj_beta_trace(7u);
    assert(xdj_beta_apply_or_trace_surfaces(row + 1, info + 1) == 1);
    assert(row[1u + 27u * ROW_WIDTH] == 0xffffu);
    assert(info[1u + 116u * INFO_STRIDE] == 0xffffu);
    assert(row[ROW_WORDS + 1u] == 0x5a5au);
    assert(info[INFO_WORDS + 1u] == 0x5a5au);

    assert(xdj_beta_apply_or_trace_surfaces(NULL, info + 1) == 0);
    return 0;
}
