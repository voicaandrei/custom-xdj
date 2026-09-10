/* Test 14: the stock INFO surface is reused at 500,284, size 288x28.
 * Binding: stock MAIN SHA 9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0.
 * CODE pointers below; the descriptor is an independently identified RAM pointer.
 * No allocation, database access or additional rendering from these UI wrappers.
 */
#include <stdint.h>
#include <stddef.h>

#ifndef INFO_DESCRIPTOR
#define INFO_DESCRIPTOR ((uintptr_t)0x13bca510u)
#endif
#ifndef STOCK_CREATE
#define STOCK_CREATE ((int (*)(void *, void *))0x0935ae78u)
#define STOCK_ACCESS ((int (*)(void *, void *, void *))0x0935a24cu)
#define STOCK_RELEASE ((int (*)(void *))0x0935a2ecu)
#define STOCK_RESOURCE ((const void *(*)(int))0x0946e148u)
#endif
#define WIDTH 288u
#define HEIGHT 28u

static void geometry(uint8_t *d)
{
    *(uint32_t *)(d + 4) = 500;
    *(uint32_t *)(d + 8) = 284;
    *(uint16_t *)(d + 12) = WIDTH;
    *(uint16_t *)(d + 14) = WIDTH;
    *(uint16_t *)(d + 16) = HEIGHT;
}

int xdj_beta_info_create(void *descriptor, void *settings)
{
    if ((uintptr_t)descriptor == INFO_DESCRIPTOR) {
        uint8_t *s = settings;
        geometry(descriptor);
        *(uint16_t *)(s + 8) = WIDTH;
        *(uint16_t *)(s + 10) = HEIGHT;
        *(uint32_t *)(s + 28) = 500;
        *(uint32_t *)(s + 32) = 284;
    }
    return STOCK_CREATE(descriptor, settings);
}

/* A successful own transfer returns nonzero to skip the old artwork copy
 * and its release. We release the stock access exactly once ourselves.
 * Non-INFO retains the original access/copy/release contract unchanged.
 */
int xdj_beta_info_access(void *handle, void *pixels, void *pitch,
                         void *descriptor, const uint16_t *source)
{
    int result;
    uint16_t *destination;
    uint32_t stride_bytes;
    unsigned x, y;
    if ((uintptr_t)descriptor != INFO_DESCRIPTOR)
        return STOCK_ACCESS(handle, pixels, pitch);
    geometry(descriptor);
    result = STOCK_ACCESS(handle, pixels, pitch);
    if (result != 0) return result;
    destination = *(uint16_t **)pixels;
    stride_bytes = *(uint32_t *)pitch;
    /* Exact allocated dimensions are known from our matching create wrapper.
     * Reject unexpected pitch instead of deriving capacity from it.
     */
    if (source && destination && stride_bytes == WIDTH * 2u) {
        for (y = 0; y < HEIGHT; ++y)
            for (x = 0; x < WIDTH; ++x)
                destination[y * WIDTH + x] = source[y * WIDTH + x];
    }
    STOCK_RELEASE(handle);
    return 1;
}

static const uint16_t blank[WIDTH * HEIGHT] = {0};
/* Only +12 is read by this exact caller. Never handed to a generic decoder. */
static const struct { uint32_t reserved[3]; const uint16_t *pixels; }
    empty_resource = {{0, 0, 0}, blank};
#if defined(__sh__)
typedef char xdj_resource_pointer_at_12[(offsetof(__typeof__(empty_resource), pixels)==12) ? 1 : -1];
#endif

const void *xdj_beta_info_fallback(int resource, void *descriptor)
{
    if ((uintptr_t)descriptor == INFO_DESCRIPTOR)
        return &empty_resource;
    return STOCK_RESOURCE(resource);
}
