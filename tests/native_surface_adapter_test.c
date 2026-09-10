#include "surface_adapter.h"
#include "pixel_channels.h"
#include <assert.h>
#include <string.h>

typedef struct { uint16_t buffer[28*83+2]; int accesses, releases, access_error, release_error;
    int null_pointer; size_t pitch; } fixture;
static int access_surface(void *context, void *handle, void **pixels, size_t *pitch) {
    fixture *f=context; assert(handle==f); f->accesses++;
    *pixels=f->null_pointer ? 0 : f->buffer+1; *pitch=f->pitch; return f->access_error;
}
static int release_surface(void *context, void *handle) {
    fixture *f=context; assert(handle==f); f->releases++; return f->release_error;
}
static void reset(fixture *f) {
    size_t i; memset(f,0,sizeof(*f)); f->pitch=166;
    for(i=0;i<sizeof(f->buffer)/sizeof(f->buffer[0]);i++) f->buffer[i]=0x1234;
}
int main(void) {
    fixture f; uint8_t key[XDJ_KEY_BYTES]={1}, order[1], payload[XDJ_PWAV_BYTES];
    xdj_wave_entry entries[1]; xdj_wave_cache cache={entries,order,1};
    xdj_cell_layout layout={80,0,28};
    xdj_surface_ops ops={access_surface,release_surface,&f};
    xdj_channel_order channels=XDJ_CHANNEL_ORDER_RGB;
    size_t i,y;
    assert(xdj_adapter_reset(&cache)==XDJ_ADAPTER_PREPARED);
    reset(&f);
#define DRAW(cap, enabled) xdj_surface_draw_cached(&cache,key,XDJ_PREVIEW_BLUE,&layout,&ops,&f,cap,0,0xffff,enabled)
    assert(DRAW(28*166,1)==XDJ_SURFACE_SKIPPED);
    assert(f.accesses==0 && f.releases==0);
    memset(payload,31,sizeof(payload));
    assert(xdj_adapter_prepare(&cache,key,XDJ_PREVIEW_BLUE,&layout,payload,sizeof(payload),
        xdj_pack_rgb8_context,&channels)==XDJ_ADAPTER_PREPARED);
    assert(DRAW(28*166,0)==XDJ_SURFACE_SKIPPED);
    assert(f.accesses==0 && f.releases==0);
    assert(DRAW(28*166,1)==XDJ_SURFACE_DRAWN);
    assert(f.accesses==1 && f.releases==1);
    assert(f.buffer[0]==0x1234 && f.buffer[28*83+1]==0x1234);
    for(y=0;y<28;y++) for(i=80;i<83;i++) assert(f.buffer[1+y*83+i]==0x1234);
    for(i=0;i<80;i++) assert(f.buffer[1+27*83+i]==0xffff);
    reset(&f); f.access_error=-1;
    assert(DRAW(28*166,1)==XDJ_SURFACE_ACCESS_FAILED);
    assert(f.accesses==1 && f.releases==0);
    reset(&f); f.null_pointer=1;
    assert(DRAW(28*166,1)==XDJ_SURFACE_INVALID);
    assert(f.accesses==1 && f.releases==1);
    reset(&f); f.pitch=165;
    assert(DRAW(28*166,1)==XDJ_SURFACE_INVALID);
    assert(f.releases==1);
    reset(&f);
    assert(DRAW(100,1)==XDJ_SURFACE_INVALID);
    assert(f.releases==1);
    for(i=0;i<sizeof(f.buffer)/sizeof(f.buffer[0]);i++) assert(f.buffer[i]==0x1234);
    reset(&f); f.release_error=-1;
    assert(DRAW(28*166,1)==XDJ_SURFACE_RELEASE_FAILED);
    assert(f.accesses==1 && f.releases==1);
    return 0;
}
