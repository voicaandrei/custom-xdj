#include "beta_runtime.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int reference_prepare_blue(const uint8_t *,uint32_t,uint32_t);
int reference_prepare_rgb(const uint8_t *,uint32_t,uint32_t);
int reference_apply_surfaces(uint16_t *,uint16_t *);
int xdj_beta_apply_or_trace_surfaces(uint16_t *,uint16_t *);
static uint8_t blue[900], rgb[7228];
static uint16_t old_row[2242],new_row[2242],old_info[8122],new_info[8122];
static void reset(void) {
    memset(old_row,0x3c,sizeof old_row);memset(new_row,0x3c,sizeof new_row);
    memset(old_info,0x5a,sizeof old_info);memset(new_info,0x5a,sizeof new_info);
}
static void equal(void) {
    assert(memcmp(old_row,new_row,sizeof old_row)==0);
    assert(memcmp(old_info,new_info,sizeof old_info)==0);
    assert(new_row[0]==0x3c3c && new_row[2241]==0x3c3c);
    assert(new_info[0]==0x5a5a && new_info[8121]==0x5a5a);
}
static void rejected(void) {
    unsigned i; reset();
    assert(xdj_beta_apply_or_trace_surfaces(new_row+1,new_info+1)==0);
    for(i=0;i<2242;i++) assert(new_row[i]==0x3c3c);
    for(i=1;i<=8120;i++) assert(new_info[i]==0);
    assert(new_info[0]==0x5a5a && new_info[8121]==0x5a5a);
}
int main(int argc,char **argv) {
    unsigned i,pass;FILE *f;
    assert(argc==2);f=fopen(argv[1],"rb");assert(f);
    assert(fread(rgb,1,sizeof rgb,f)==sizeof rgb);assert(fgetc(f)==EOF);fclose(f);
    for(pass=0;pass<64;pass++) {
        for(i=0;i<400;i++) {blue[i*2]=(uint8_t)((pass+i)%32);blue[i*2+1]=(uint8_t)((i+pass)%8);}
        reset();
        assert(reference_prepare_blue(blue,sizeof blue,pass+1)==1);
        assert(xdj_beta_prepare_blue(blue,sizeof blue,pass+1)==1);
        assert(reference_apply_surfaces(old_row+1,old_info+1)==1);
        assert(xdj_beta_apply_surfaces(new_row+1,new_info+1)==1);equal();
        assert(xdj_beta_apply_surfaces(new_row+1,new_info+1)==0);
    }
    reset();
    assert(reference_prepare_rgb(rgb,sizeof rgb,3902)==1);
    assert(xdj_beta_prepare_rgb(rgb,sizeof rgb,3902)==1);
    assert(reference_apply_surfaces(old_row+1,old_info+1)==1);
    assert(xdj_beta_apply_surfaces(new_row+1,new_info+1)==1);equal();
    for(pass=0;pass<6;pass++) {
        assert(xdj_beta_prepare_rgb(rgb,sizeof rgb,3902)==1);
        switch(pass) {
        case 0: assert(xdj_beta_prepare_rgb(NULL,sizeof rgb,1)==0);break;
        case 1: assert(xdj_beta_prepare_rgb(rgb,sizeof rgb-1,1)==0);break;
        case 2: assert(xdj_beta_prepare_rgb(rgb,sizeof rgb,0)==0);break;
        case 3: blue[0]=32;assert(xdj_beta_prepare_blue(blue,sizeof blue,1)==0);blue[0]=0;break;
        case 4: assert(xdj_beta_prepare_blue(blue,0,1)==0);break;
        case 5: rgb[4]='X';assert(xdj_beta_prepare_rgb(rgb,sizeof rgb,1)==0);rgb[4]='P';break;
        }
        rejected();
    }
    assert(xdj_beta_prepare_rgb(rgb,sizeof rgb,3902)==1);
    xdj_beta_invalidate();rejected();
    puts("65 frame pairs identical; six invalid-preparation cases reject stale frames; cancellation and bounds pass");
    return 0;
}
