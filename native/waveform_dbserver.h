#ifndef XDJ_WAVEFORM_DBSERVER_H
#define XDJ_WAVEFORM_DBSERVER_H
#include "waveform_adapter.h"
/* Consume only the raw binary argument of a verified dbserver response.
 * Caller validates transaction/type/source and retains ownership through return.
 * This function does not inspect firmware response structures, free memory,
 * perform IO or provide inter-task synchronization. Call outside repaint.
 * Blue needs 400 bytes of caller scratch, disjoint from payload and cache.
 * RGB borrows the validated 7200-byte PWV4 region during preparation only.
 */
xdj_adapter_result xdj_adapter_prepare_dbserver(
    xdj_wave_cache *cache, const uint8_t *key, xdj_preview_mode mode,
    const xdj_cell_layout *layout, const uint8_t *blob, size_t bytes,
    uint8_t *scratch, size_t scratch_bytes, xdj_pack_rgb8 pack, void *context);
#endif
