#include "preview_queue.h"
#include "blue_request.h"
#include "pixel_channels.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static xdj_preview_queue queue;
static xdj_track_identity ids[7];
static uint8_t eligible[7]={1,1,1,1,1,1,1};
static xdj_cell_layout layout={80,0,28};
static uint8_t blob[900];
static int action,released,queried;
static int query(void *ctx,uint32_t id,uint32_t *length,uint8_t **output,
                 uint32_t selector,const void *resource,uint32_t kind) {
    assert(ctx==&queue && id && selector==0 && !resource && !kind);
    ++queried;*length=900;*output=blob;
    if(action==1)ids[0].track_id=999; /* same visible slot, different piece */
    if(action==2)ids[0].media_epoch_lo++; /* same ID, newly inserted medium */
    if(action==1 || action==2)assert(xdj_preview_queue_set(&queue,ids,eligible,1,0,
        XDJ_PREVIEW_BLUE,&layout,1));
    if(action==3)assert(xdj_preview_queue_set(&queue,ids,eligible,1,0,
        XDJ_PREVIEW_RGB,&layout,1));
    if(action==4)assert(xdj_preview_queue_set(&queue,ids,eligible,1,0,
        XDJ_PREVIEW_BLUE,&layout,0));
    return action==5?0:1;
}
static void release(void *p) {assert(p==blob);++released;}
int main(int argc,char **argv) {
    xdj_wave_entry entries[7];uint8_t order[7],scratch[400],key[16];
    xdj_wave_cache cache={entries,order,7};xdj_preview_job job,next;
    xdj_channel_order channels=XDJ_CHANNEL_ORDER_RGB;
    xdj_blue_source source={query,release,&queue,0,xdj_preview_queue_current,&queue};
    FILE *f;unsigned i;uint32_t old_token;
    assert(argc==2);f=fopen(argv[1],"rb");assert(f);
    assert(fread(blob,1,900,f)==900);fclose(f);
    for(i=0;i<7;++i) {
        ids[i].track_id=100+i;ids[i].media_epoch_hi=0;ids[i].media_epoch_lo=1;
        ids[i].source_player=4;ids[i].source_slot=3;ids[i].track_type=1;
    }
    xdj_preview_queue_reset(&queue);assert(xdj_adapter_reset(&cache)==XDJ_ADAPTER_PREPARED);
    assert(xdj_preview_queue_set(&queue,ids,eligible,7,3,XDJ_PREVIEW_BLUE,&layout,1));
    for(i=0;i<7;++i) {
        unsigned expected=i==0?3:(i<=3?i-1:i);
        assert(xdj_preview_queue_next(&queue,&cache,&job)==1);
        assert(job.identity.track_id==100+expected);
        assert(xdj_preview_queue_next(&queue,&cache,&next)==0);
        assert(!xdj_preview_queue_finish(&queue,job.token+1,XDJ_ADAPTER_HIT));
        assert(xdj_blue_request_prepare(&source,&job.identity,&cache,&job.layout,
            scratch,400,xdj_pack_rgb8_context,&channels,1)==XDJ_ADAPTER_PREPARED);
        assert(xdj_preview_queue_finish(&queue,job.token,XDJ_ADAPTER_PREPARED));
        assert(!xdj_preview_queue_finish(&queue,job.token,XDJ_ADAPTER_PREPARED));
    }
    assert(queried==7 && released==7);
    assert(xdj_preview_queue_next(&queue,&cache,&next)==0);
    /* Moving cached pieces between slots must not cause IO. */
    ids[0].track_id=106;ids[6].track_id=100;
    assert(xdj_preview_queue_set(&queue,ids,eligible,7,0,XDJ_PREVIEW_BLUE,&layout,1));
    assert(xdj_preview_queue_next(&queue,&cache,&next)==0);
    /* Eviction must be detected even after a successful completion. */
    assert(xdj_make_track_key(&ids[0],key));
    assert(xdj_adapter_invalidate(&cache,key,XDJ_PREVIEW_BLUE)!=XDJ_ADAPTER_INVALID);
    assert(xdj_preview_queue_next(&queue,&cache,&job)==1);
    assert(job.identity.track_id==106);
    assert(xdj_preview_queue_finish(&queue,job.token,XDJ_ADAPTER_INVALID));
    /* Duplicate tracks share the cache; selected non-track row emits nothing. */
    xdj_preview_queue_reset(&queue);assert(xdj_adapter_reset(&cache)==XDJ_ADAPTER_PREPARED);
    ids[1].track_id=106;eligible[0]=0;queried=released=0;
    assert(xdj_preview_queue_set(&queue,ids,eligible,2,0,XDJ_PREVIEW_BLUE,&layout,1));
    assert(xdj_preview_queue_next(&queue,&cache,&job)==1);
    assert(xdj_blue_request_prepare(&source,&job.identity,&cache,&job.layout,
        scratch,400,xdj_pack_rgb8_context,&channels,1)==XDJ_ADAPTER_PREPARED);
    assert(xdj_preview_queue_finish(&queue,job.token,XDJ_ADAPTER_PREPARED));
    eligible[0]=1;
    assert(xdj_preview_queue_set(&queue,ids,eligible,2,0,XDJ_PREVIEW_BLUE,&layout,1));
    assert(xdj_preview_queue_next(&queue,&cache,&job)==0 && queried==1 && released==1);
    for(action=1;action<=5;++action) {
        xdj_adapter_result result;
        xdj_preview_queue_reset(&queue);assert(xdj_adapter_reset(&cache)==XDJ_ADAPTER_PREPARED);
        ids[0].track_id=100;ids[0].media_epoch_lo=1;
        assert(xdj_preview_queue_set(&queue,ids,eligible,1,0,XDJ_PREVIEW_BLUE,&layout,1));
        assert(xdj_preview_queue_next(&queue,&cache,&job)==1);
        old_token=job.token;assert(xdj_make_track_key(&job.identity,key));
        result=xdj_blue_request_prepare(&source,&job.identity,&cache,&job.layout,
            scratch,400,xdj_pack_rgb8_context,&channels,1);
        assert(result==(action==5?XDJ_ADAPTER_INVALID:XDJ_ADAPTER_SKIPPED));
        assert(xdj_adapter_lookup(&cache,key,XDJ_PREVIEW_BLUE,&layout)==XDJ_ADAPTER_MISS);
        assert(xdj_preview_queue_finish(&queue,old_token,result));
        if(action==5) {
            assert(xdj_preview_queue_next(&queue,&cache,&next)==0);
            xdj_preview_queue_retry(&queue);
            assert(xdj_preview_queue_next(&queue,&cache,&next)==1);
        } else if(action!=4)assert(xdj_preview_queue_next(&queue,&cache,&next)==1);
        if(action!=4)assert(!xdj_preview_queue_finish(&queue,old_token,XDJ_ADAPTER_HIT));
    }
    xdj_preview_queue_reset(&queue);
    assert(xdj_preview_queue_set(&queue,ids,eligible,1,0,XDJ_PREVIEW_BLUE,&layout,1));
    queue.serial=UINT32_MAX;
    assert(xdj_preview_queue_next(&queue,&cache,&job)==-1 && !queue.busy);
    assert(!xdj_preview_queue_set(&queue,ids,eligible,8,0,XDJ_PREVIEW_BLUE,&layout,1));
    assert(queue.count==1 && queue.serial==UINT32_MAX);
    assert(xdj_preview_queue_set(&queue,0,0,0,0,XDJ_PREVIEW_BLUE,&layout,1));
    assert(xdj_preview_queue_next(&queue,&cache,&job)==0);
    return 0;
}
