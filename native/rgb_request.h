#ifndef XDJ_RGB_REQUEST_H
#define XDJ_RGB_REQUEST_H
#include "blue_request.h"
/* v1.44 GetSpecifiedAtomInfo convention, distinct from GetWaveData.
 * Third output is retained as opaque response metadata until fully mapped.
 * Strings must remain alive through the synchronous call. No addresses bound.
 */
typedef int (*xdj_rgb_query)(void *connection, uint32_t track_id,
    const char *atom, const char *extension, uint32_t *length,
    uint8_t **blob, uint32_t *response_metadata);
typedef struct {
    xdj_rgb_query query;
    xdj_blue_release release;
    void *connection;
    xdj_request_current current;
    void *current_context;
} xdj_rgb_source;
/* Same serialized-worker and generation contract as blue_request. There is
 * no RGB-to-Blue fallback hidden here. No scratch array required for RGB. */
xdj_adapter_result xdj_rgb_request_prepare(const xdj_rgb_source *source,
    const xdj_track_identity *identity, xdj_wave_cache *cache,
    const xdj_cell_layout *layout, xdj_pack_rgb8 pack, void *pack_context,
    int enabled);
#endif
