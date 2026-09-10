#include "waveform_prepare_fast.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static uint8_t payload[7200];
static xdj_wave_column reference[2][1202], result[2][1202];
typedef struct { unsigned calls; uint32_t rgb[4800]; } trace;
static trace old_trace, new_trace;
static unsigned cases;
static uint32_t seed = 0x12345678u;
static uint32_t random_word(void) {
    seed ^= seed << 13; seed ^= seed >> 17; seed ^= seed << 5; return seed;
}
static uint16_t pack(uint8_t r, uint8_t g, uint8_t b, void *context) {
    trace *t = context;
    assert(t->calls < 4800);
    t->rgb[t->calls++] = ((uint32_t)r << 16) | ((uint32_t)g << 8) | b;
    return (uint16_t)t->calls;
}
static void reset(void) {
    memset(reference,0xa5,sizeof reference); memset(result,0xa5,sizeof result);
    memset(&old_trace,0,sizeof old_trace); memset(&new_trace,0,sizeof new_trace);
}
static void equal(void) {
    assert(memcmp(reference,result,sizeof reference)==0);
    assert(memcmp(&old_trace,&new_trace,sizeof old_trace)==0);
    ++cases;
}
static void single(int mode,unsigned width,unsigned height) {
    size_t bytes=mode ? 7200 : 400;
    reset();
    assert((mode ? xdj_prepare_pwv4_scaled : xdj_prepare_pwav_scaled)(
        payload,bytes,reference[0]+1,width,height,pack,&old_trace)==1);
    assert((mode ? xdj_fast_prepare_pwv4_scaled : xdj_fast_prepare_pwav_scaled)(
        payload,bytes,result[0]+1,width,height,pack,&new_trace)==1);
    equal();
}
static void pair(int mode,unsigned width,unsigned height) {
    size_t bytes=mode ? 7200 : 400;
    xdj_prepare_target t[2]={{result[0]+1,290,27},{result[1]+1,width,height}};
    reset();
    assert((mode ? xdj_prepare_pwv4_scaled : xdj_prepare_pwav_scaled)(
        payload,bytes,reference[0]+1,290,27,pack,&old_trace)==1);
    assert((mode ? xdj_prepare_pwv4_scaled : xdj_prepare_pwav_scaled)(
        payload,bytes,reference[1]+1,width,height,pack,&old_trace)==1);
    assert(xdj_fast_prepare_pair(payload,bytes,mode,t,pack,&new_trace)==1);
    equal();
}
static void malformed(void) {
    unsigned mode,index;
    for(mode=0;mode<2;mode++) for(index=0;index<10;index++) {
        xdj_prepare_target t[2]={{result[0]+1,290,27},{result[1]+1,160,27}};
        size_t bytes=mode?7200:400;
        int m=(int)mode;
        const uint8_t *source=payload;
        const xdj_prepare_target *targets=t;
        xdj_pack_rgb8 callback=pack;
        reset();
        switch(index) {
        case 0: t[1].count=0; break;
        case 1: t[1].count=1201; break;
        case 2: t[1].amplitude_height=0; break;
        case 3: t[1].amplitude_height=256; break;
        case 4: t[1].columns=NULL; break;
        case 5: --bytes; break;
        case 6: m=2; break;
        case 7: source=NULL; break;
        case 8: targets=NULL; break;
        case 9: callback=NULL; break;
        }
        assert(xdj_fast_prepare_pair(source,bytes,m,targets,callback,&new_trace)==-1);
        equal(); /* No writes to either target, no callbacks. */
    }
}
int main(int argc,char **argv) {
    unsigned mode,pattern,width,height,i;
    const unsigned widths[]={1,80,120,160,290,400};
    if(argc==2) {
        FILE *f=fopen(argv[1],"rb"); int ch; assert(f);
        while((ch=fgetc(f))!=EOF) {
            size_t bytes=ch?7200:400; assert(ch==0 || ch==1);
            assert(fread(payload,1,bytes,f)==bytes);
            for(i=0;i<sizeof widths/sizeof widths[0];i++) {
                single(ch,widths[i],27); pair(ch,widths[i],27);
            }
        }
        assert(!ferror(f)); fclose(f);
    } else {
        assert(argc==1);
        for(mode=0;mode<2;mode++) for(pattern=0;pattern<4;pattern++) {
            for(i=0;i<sizeof payload;i++)
                payload[i]=pattern==0?0:pattern==1?255:
                    pattern==2?(uint8_t)random_word():(uint8_t)((i%6>=3)?((i/6)%3)*63:0);
            for(width=1;width<=(mode?1200u:400u);width++) {
                single((int)mode,width,(width%3)==0?1:(width%3)==1?27:255);
                pair((int)mode,width,27);
            }
        }
        for(mode=0;mode<2;mode++) for(height=1;height<=255;height++)
            for(i=0;i<sizeof widths/sizeof widths[0];i++) {
                single((int)mode,widths[i],height); pair((int)mode,widths[i],height);
            }
        malformed();
    }
    printf("{\"pixel_and_callback_parity_cases\":%u}\n",cases);
    return 0;
}
