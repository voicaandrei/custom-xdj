#ifndef XDJ_BLUE_REQUEST_H
#define XDJ_BLUE_REQUEST_H
#include "waveform_dbserver.h"

/* Signature traced in v1.44 dbcl_GetWaveData and its caller. The last two
 * arguments select an optional alternate resource; this adapter passes 0, 0.
 * selector is an opaque stock request field: the integration MUST derive it
 * from the correct browser source, not from the display's player number.
 * No absolute address is installed by this module. */
typedef int (*xdj_blue_query)(void *connection, uint32_t track_id,
    uint32_t *length, uint8_t **blob, uint32_t selector,
    const void *optional_resource, uint32_t optional_kind);
typedef void (*xdj_blue_release)(void *blob);
typedef int (*xdj_request_current)(void *context, const uint8_t *key);

typedef struct {
    xdj_blue_query query;
    xdj_blue_release release;
    void *connection;
    uint32_t selector;
    xdj_request_current current;
    void *current_context;
} xdj_blue_source;

/* Synchronous WORKER operation, never a paint callback. Caller serializes all
 * cache operations and keeps source, layout, scratch and pack context alive.
 * current is mandatory and checks the media/source incarnation before and
 * after the potentially blocking request. Output memory is borrowed only until
 * release; no pointer into it is stored. Scratch must be disjoint, >=400 bytes.
 * Positive stock query result is success; NULL/invalid payload never publishes.
 */
xdj_adapter_result xdj_blue_request_prepare(const xdj_blue_source *source,
    const xdj_track_identity *identity, xdj_wave_cache *cache,
    const xdj_cell_layout *layout, uint8_t *scratch, size_t scratch_bytes,
    xdj_pack_rgb8 pack, void *pack_context, int enabled);
#endif
