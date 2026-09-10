/* Test 13. Defer NEW artwork work until navigation settles, in its UI task.
 * Stock MAIN SHA256 9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0.
 * FILE 0x154a5ac is the sole patched caller literal. All pointers below are CODE.
 * Existing pending checks and completion handling run before this call.
 * Returning zero here precedes any stock row-state or request mutation.
 * There is no sleep, allocation, IO, cancellation-table mutation or second task.
 */
#include <stdint.h>

#ifndef STOCK_PREPARE
#define STOCK_PREPARE ((int (*)(void *, void *))0x09514c7cu)
#define STOCK_CLOCK ((uint32_t (*)(void))0x0944692eu)
#define STOCK_TOP ((uint32_t (*)(int))0x0951970au)
#define STOCK_SELECTION ((uint32_t (*)(int))0x0951963eu)
#define STOCK_MODE ((uint32_t (*)(void))0x0951958eu)
#endif

#define QUIET_TICKS 250u
#if defined(__sh__)
#define SETTLE_STORAGE __attribute__((section(".xdj_beta_state"), aligned(4)))
#else
#define SETTLE_STORAGE
#endif
/* Explicit nonzero initializer keeps state in the appended PROGBITS payload.
 * Stock startup does not know about an extension BSS. Only the UI task uses it.
 */
static struct {
    uint32_t initialized, changed_at, signature[5];
} settle SETTLE_STORAGE =
    {0, 0, {0xffffffffu, 0, 0, 0, 0}};

int xdj_beta_browse_prepare(void *row_index, void *identifier)
{
    uint32_t current[5], now;
    unsigned i;
    int changed;
    if (!row_index || !identifier)
        return STOCK_PREPARE(row_index, identifier);
    current[0] = STOCK_MODE();
    current[1] = STOCK_TOP(0);
    current[2] = STOCK_TOP(1);
    current[3] = STOCK_SELECTION(0);
    current[4] = STOCK_SELECTION(1);
    now = STOCK_CLOCK();
    changed = !settle.initialized;
    for (i = 0; i < 5; ++i)
        if (current[i] != settle.signature[i]) changed = 1;
    if (changed) {
        for (i = 0; i < 5; ++i) settle.signature[i] = current[i];
        settle.changed_at = now;
        settle.initialized = 1;
        return 0;
    }
    /* Wrap-safe unsigned clock difference, like the stock timeout helper. */
    if ((uint32_t)(now - settle.changed_at) < QUIET_TICKS)
        return 0;
    return STOCK_PREPARE(row_index, identifier);
}
