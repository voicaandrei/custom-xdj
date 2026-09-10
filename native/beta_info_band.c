/* Test 11: the stock INFO surface is reused at 500,284, size 290x28.
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
#define STOCK_RESOURCE ((const void *(*)(int))0x0946e148u)
#endif
#define WIDTH 290u
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

int xdj_beta_info_access(void *handle, void *pixels, void *pitch, void *descriptor)
{
    /* Stock resets INFO's source stride to 113 or 120 on each draw. */
    if ((uintptr_t)descriptor == INFO_DESCRIPTOR)
        geometry(descriptor);
    return STOCK_ACCESS(handle, pixels, pitch);
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
