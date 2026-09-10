#include "beta_runtime.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define ROW_WORDS (80u * 28u)
#define INFO_VISIBLE_WIDTH 109u
#define INFO_STRIDE 112u
#define INFO_HEIGHT 117u
#define INFO_WORDS (INFO_STRIDE * INFO_HEIGHT)

static uint8_t rgb[7228];
static uint8_t blue[900];
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

static void check_frame(void)
{
    size_t x;
    assert(row[0] == 0x5a5au && row[ROW_WORDS + 1u] == 0x5a5au);
    assert(info[0] == 0x5a5au && info[INFO_WORDS + 1u] == 0x5a5au);
    for (x = 0; x < 80u; ++x)
        assert(row[1u + 27u * 80u + x] == 0xffffu);
    for (x = 0; x < INFO_VISIBLE_WIDTH; ++x)
        assert(info[1u + (INFO_HEIGHT - 1u) * INFO_STRIDE + x] == 0xffffu);
    for (x = INFO_VISIBLE_WIDTH; x < INFO_STRIDE; ++x)
        assert(info[1u + (INFO_HEIGHT - 1u) * INFO_STRIDE + x] == 0u);
}

int main(int argc, char **argv)
{
    assert(argc == 3);
    read_exact(argv[1], rgb, sizeof rgb);
    read_exact(argv[2], blue, sizeof blue);

    reset_surfaces();
    assert(xdj_beta_prepare_rgb(rgb, sizeof rgb, 3902u) == 1);
    assert(xdj_beta_apply_surfaces(row + 1, info + 1) == 1);
    check_frame();
    assert(xdj_beta_apply_surfaces(row + 1, info + 1) == 0);

    reset_surfaces();
    assert(xdj_beta_prepare_blue(blue, sizeof blue, 3902u) == 1);
    assert(xdj_beta_apply_surfaces(row + 1, info + 1) == 1);
    check_frame();

    reset_surfaces();
    xdj_beta_invalidate();
    assert(xdj_beta_apply_surfaces(row + 1, info + 1) == 0);
    assert(row[1] == 0x5a5au && info[1] == 0x5a5au);
    assert(xdj_beta_prepare_rgb(rgb, sizeof rgb - 1u, 3902u) == 0);
    assert(xdj_beta_prepare_blue(blue, sizeof blue, 0u) == 0);
    rgb[20] ^= 1u;
    assert(xdj_beta_prepare_rgb(rgb, sizeof rgb, 3902u) == 0);
    rgb[20] ^= 1u;
    blue[0] = 32u;
    assert(xdj_beta_prepare_blue(blue, sizeof blue, 3902u) == 0);
    return 0;
}
