#include "blue_request.h"
#include "pixel_channels.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static uint8_t payload[900], original[900];
static int queries, releases, checks, status, stale, null_blob;
static uint32_t reply_bytes;
static int connection;
static uint8_t expected_key[XDJ_KEY_BYTES];
static int query(void *ctx,uint32_t id,uint32_t *length,uint8_t **blob,
                 uint32_t selector,const void *optional,uint32_t kind) {
    assert(ctx==&connection && id==3902 && selector==0x12345678u);
    assert(!optional && !kind && !*length && !*blob);
    ++queries; *length=reply_bytes; *blob=null_blob?0:payload; return status;
}
static void release(void *ptr) {
    assert(ptr==payload); ++releases;
    memset(payload,0xff,sizeof(payload)); /* detect retained payload pointers */
}
static int current(void *ctx,const uint8_t *key) {
    assert(ctx==&connection && !memcmp(key,expected_key,XDJ_KEY_BYTES));
    ++checks; return !(stale && checks>1);
}
int main(int argc,char **argv) {
    xdj_wave_entry entry; uint8_t order[1],scratch[400];
    xdj_wave_cache cache={&entry,order,1};
    xdj_cell_layout layout={80,0,28};
    xdj_track_identity id={3902,0,1,4,3,1};
    xdj_channel_order channels=XDJ_CHANNEL_ORDER_RGB;
    xdj_blue_source source={query,release,&connection,0x12345678u,current,&connection};
    uint16_t pixels[80*28]; FILE *file; int scenario;
    assert(argc==2);file=fopen(argv[1],"rb");assert(file);
    assert(fread(original,1,900,file)==900);assert(fgetc(file)==EOF);fclose(file);
    assert(xdj_make_track_key(&id,expected_key));
    for (scenario=0;scenario<7;++scenario) {
        xdj_adapter_result result;
        memcpy(payload,original,900); queries=releases=checks=0;
        status=1;stale=null_blob=0;reply_bytes=900;
        assert(xdj_adapter_reset(&cache)==XDJ_ADAPTER_PREPARED);
        if(scenario==1)status=0; /* failed query can still transfer a buffer */
        if(scenario==2)stale=1;
        if(scenario==3)reply_bytes=899;
        if(scenario==4)null_blob=1;
        if(scenario==5)payload[0]=255;
        result=xdj_blue_request_prepare(&source,&id,&cache,&layout,scratch,400,
              xdj_pack_rgb8_context,&channels,scenario!=6);
        assert(queries==(scenario==6?0:1));
        assert(releases==((scenario==4 || scenario==6)?0:1));
        if(scenario==0) {
            assert(result==XDJ_ADAPTER_PREPARED);
            assert(xdj_adapter_draw(&cache,expected_key,XDJ_PREVIEW_BLUE,&layout,
                pixels,80*28,80,0,0xffff,1)==XDJ_ADAPTER_HIT);
            assert(xdj_blue_request_prepare(&source,&id,&cache,&layout,scratch,400,
                xdj_pack_rgb8_context,&channels,1)==XDJ_ADAPTER_HIT);
            assert(queries==1 && releases==1);
        } else {
            assert(result==((scenario==2 || scenario==6)?XDJ_ADAPTER_SKIPPED:XDJ_ADAPTER_INVALID));
            assert(!entry.valid);
        }
    }
    source.current=0;
    assert(xdj_blue_request_prepare(&source,&id,&cache,&layout,scratch,400,
        xdj_pack_rgb8_context,&channels,1)==XDJ_ADAPTER_INVALID);
    assert(queries==0 && releases==0);
    return 0;
}
