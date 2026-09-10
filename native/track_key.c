#include "track_key.h"
static void store32(uint8_t *out, uint32_t value) {
    out[0]=(uint8_t)(value>>24); out[1]=(uint8_t)(value>>16);
    out[2]=(uint8_t)(value>>8); out[3]=(uint8_t)value;
}
int xdj_make_track_key(const xdj_track_identity *id, uint8_t out[XDJ_KEY_BYTES]) {
    if (!id || !out || !id->track_id || id->source_player<1 ||
        id->source_player>4 || id->source_slot!=3 || id->track_type!=1 ||
        !(id->media_epoch_hi | id->media_epoch_lo)) return 0;
    out[0]=id->source_player; out[1]=id->source_slot;
    out[2]=id->track_type; out[3]=0;
    store32(out+4,id->track_id);
    store32(out+8,id->media_epoch_hi);
    store32(out+12,id->media_epoch_lo);
    return 1;
}
