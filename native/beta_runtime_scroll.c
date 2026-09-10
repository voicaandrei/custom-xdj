/* Test 10: reuse the validated renderer; failures retain stock artwork.
 * Historical Test 05-09 tracing runtime stays unchanged and reproducible. */
#include "beta_runtime.c"

void xdj_beta_trace_reset(void) { xdj_beta_invalidate(); }
void xdj_beta_trace(uint32_t stage) { (void)stage; }
int xdj_beta_apply_or_trace_surfaces(uint16_t *row, uint16_t *info)
{
    return xdj_beta_apply_surfaces(row, info);
}

