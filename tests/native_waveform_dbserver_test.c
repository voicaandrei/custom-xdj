#include "waveform_dbserver.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned calls;
static uint16_t pack(uint8_t r,uint8_t g,uint8_t b,void *ctx) {
    (void)ctx;calls++;return (uint16_t)((r>>3<<11)|(g>>2<<5)|(b>>3));
}
static unsigned char blue[900],rgb[7228],scratch[402],raw_blue[400],raw_rgb[7200];
static xdj_wave_entry entries[2];
static uint8_t order[2],key[XDJ_KEY_BYTES]={4,3,1,0,0,0,15,62,0,0,0,0,0,0,0,1};
static uint16_t surface[13673+2];
static xdj_wave_column expected[325];
static void read_exact(const char *name,void *out,size_t size) {
    FILE *f=fopen(name,"rb");assert(f);assert(fread(out,1,size,f)==size);assert(fgetc(f)==EOF);fclose(f);
}
int main(int argc,char **argv) {
    xdj_wave_cache cache={entries,order,2};
    const xdj_cell_layout shapes[]={{80,0,28},{325,0,42},{290,0,47},{256,0,53}};
    assert(argc==5);read_exact(argv[1],blue,sizeof blue);read_exact(argv[2],rgb,sizeof rgb);
    read_exact(argv[3],raw_blue,sizeof raw_blue);read_exact(argv[4],raw_rgb,sizeof raw_rgb);
    for (unsigned shape=0;shape<4;shape++) for (unsigned mode=0;mode<2;mode++) {
        const xdj_cell_layout *layout=&shapes[shape];
        xdj_adapter_reset(&cache);memset(scratch,0xa5,sizeof scratch);
        assert(xdj_adapter_prepare_dbserver(&cache,key,(xdj_preview_mode)mode,layout,
            mode?rgb:blue,mode?sizeof rgb:sizeof blue,scratch+1,400,pack,0)==XDJ_ADAPTER_PREPARED);
        assert(scratch[0]==0xa5 && scratch[401]==0xa5);
        if (mode) assert(xdj_prepare_pwv4_scaled(raw_rgb,sizeof raw_rgb,expected,layout->columns,layout->height-1,pack,0)==XDJ_PREVIEW_PREPARED);
        else {
            assert(!memcmp(scratch+1,raw_blue,400));
            assert(xdj_prepare_pwav_scaled(raw_blue,sizeof raw_blue,expected,layout->columns,layout->height-1,pack,0)==XDJ_PREVIEW_PREPARED);
        }
        assert(!memcmp(entries[order[0]].column,expected,layout->columns*sizeof expected[0]));
        for (unsigned i=0;i<13675;i++)surface[i]=0x5a5a;
        assert(xdj_adapter_draw(&cache,key,(xdj_preview_mode)mode,layout,surface+1,13673,
            layout->columns,0,0xffff,1)==XDJ_ADAPTER_HIT);
        assert(surface[0]==0x5a5a && surface[13674]==0x5a5a);
        for (unsigned i=layout->columns*layout->height+1;i<13675;i++)assert(surface[i]==0x5a5a);
    }
    calls=0;rgb[20]^=1;
    assert(xdj_adapter_prepare_dbserver(&cache,key,XDJ_PREVIEW_RGB,&shapes[0],rgb,sizeof rgb,0,0,pack,0)==XDJ_ADAPTER_INVALID);
    assert(calls==0);rgb[20]^=1;blue[0]=32;
    assert(xdj_adapter_prepare_dbserver(&cache,key,XDJ_PREVIEW_BLUE,&shapes[0],blue,sizeof blue,scratch+1,400,pack,0)==XDJ_ADAPTER_INVALID);
    assert(calls==0);
    return 0;
}
