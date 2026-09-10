/* Own preview transaction scope. Stock MAIN 1.44 SHA256
 * 9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0.
 * FILE 0x128fe3c..46 already suspends context+13 during source acquisition.
 * Hold it for our whole preview request, allowing its reply to drain before
 * outer JPEG cancellation. Never clear context+12 or consume cancel tokens.
 * Only the owning dbclient task enters/leaves this scope. No IO here.
 */
#include <stdint.h>
uint32_t xdj_beta_preview_enter(uint8_t *context)
{
    uint32_t saved;
    if (!context) return 0;
    saved = 0x100u | context[13];
    context[13] = 0;
    return saved;
}
void xdj_beta_preview_leave(uint8_t *context, uint32_t saved)
{
    if (context && (saved & 0x100u)) context[13] = (uint8_t)saved;
}
