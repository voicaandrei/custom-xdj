#include "rgb_request.h"
xdj_adapter_result xdj_rgb_request_prepare(const xdj_rgb_source *source,
    const xdj_track_identity *identity, xdj_wave_cache *cache,
    const xdj_cell_layout *layout, xdj_pack_rgb8 pack, void *pack_context,
    int enabled) {
    uint8_t key[XDJ_KEY_BYTES];
    uint8_t *blob=0;
    uint32_t bytes=0,metadata=0,track_id;
    xdj_cell_layout requested;
    xdj_adapter_result result;
    int status;
    if (!enabled) return XDJ_ADAPTER_SKIPPED;
    if (!source || !source->query || !source->release || !source->connection ||
        !source->current || !identity || !layout || !pack ||
        !xdj_make_track_key(identity,key)) return XDJ_ADAPTER_INVALID;
    track_id=identity->track_id;
    requested.columns=layout->columns;
    requested.top_row=layout->top_row;
    requested.height=layout->height;
    if (!source->current(source->current_context,key)) return XDJ_ADAPTER_SKIPPED;
    result=xdj_adapter_lookup(cache,key,XDJ_PREVIEW_RGB,&requested);
    if (result!=XDJ_ADAPTER_MISS) return result;
    status=source->query(source->connection,track_id,"PWV4","EXT",&bytes,&blob,&metadata);
    result=XDJ_ADAPTER_INVALID;
    if (status>0 && blob) {
        if (!source->current(source->current_context,key)) result=XDJ_ADAPTER_SKIPPED;
        else result=xdj_adapter_prepare_dbserver(cache,key,XDJ_PREVIEW_RGB,
            &requested,blob,bytes,0,0,pack,pack_context);
    }
    if (blob) source->release(blob);
    return result;
}
