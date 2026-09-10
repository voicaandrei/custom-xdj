#include "track_key.h"
#include <assert.h>
#include <string.h>
int main(void) {
    xdj_track_identity id={3902,0,1,4,3,1};
    uint8_t original[XDJ_KEY_BYTES],changed[XDJ_KEY_BYTES],sentinel[XDJ_KEY_BYTES];
    memset(sentinel,0xa5,sizeof sentinel);memcpy(changed,sentinel,sizeof changed);
    assert(xdj_make_track_key(&id,original));
    assert(original[0]==4 && original[4]==0 && original[6]==15 && original[7]==62);
    assert(original[15]==1);
    id.track_id++;assert(xdj_make_track_key(&id,changed));assert(memcmp(original,changed,sizeof original));
    id.track_id--;id.media_epoch_lo++;assert(xdj_make_track_key(&id,changed));assert(memcmp(original,changed,sizeof original));
    id.media_epoch_lo--;id.media_epoch_hi=1;assert(xdj_make_track_key(&id,changed));assert(memcmp(original,changed,sizeof original));
    id.media_epoch_hi=0;id.source_player=3;assert(xdj_make_track_key(&id,changed));assert(memcmp(original,changed,sizeof original));
    for (int test=0;test<5;test++) {
        id=(xdj_track_identity){3902,0,1,4,3,1};
        if (test==0) id.track_id=0;
        if (test==1) id.media_epoch_lo=0;
        if (test==2) id.source_slot=4;
        if (test==3) id.track_type=2;
        if (test==4) id.source_player=5;
        memcpy(changed,sentinel,sizeof changed);
        assert(!xdj_make_track_key(&id,changed));assert(!memcmp(changed,sentinel,sizeof changed));
    }
    assert(!xdj_make_track_key(0,changed));assert(!xdj_make_track_key(&id,0));
    return 0;
}
