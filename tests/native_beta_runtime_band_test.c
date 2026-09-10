#include "beta_runtime.h"
#include <assert.h>
#include <stdio.h>
int xdj_beta_apply_or_trace_surfaces(uint16_t *, uint16_t *);
static uint8_t rgb[7228];
static uint16_t row[2242], info[13106];
static void reset(void) {
    unsigned i;
    for(i=0;i<2242;i++) row[i]=0x5a5a;
    for(i=0;i<13106;i++) info[i]=0x6b6b;
}
static void bounds(void) {
    unsigned i;
    assert(row[0]==0x5a5a && row[2241]==0x5a5a && info[0]==0x6b6b);
    for(i=8121;i<13106;i++) assert(info[i]==0x6b6b);
}
int main(int argc,char **argv) {
    unsigned i; FILE *f;
    assert(argc==2); f=fopen(argv[1],"rb"); assert(f);
    assert(fread(rgb,1,sizeof rgb,f)==sizeof rgb); assert(fgetc(f)==EOF); fclose(f);
    reset();
    assert(xdj_beta_apply_or_trace_surfaces(row+1,info+1)==0);
    for(i=0;i<2242;i++) assert(row[i]==0x5a5a);
    for(i=1;i<=8120;i++) assert(info[i]==0);
    bounds(); reset();
    assert(xdj_beta_prepare_rgb(rgb,sizeof rgb,3902)==1);
    assert(xdj_beta_apply_or_trace_surfaces(row+1,info+1)==1);
    for(i=0;i<290;i++) assert(info[1+27*290+i]==0xffff);
    for(i=0;i<80;i++) assert(row[1+27*80+i]==0xffff);
    bounds(); reset();
    assert(xdj_beta_prepare_rgb(rgb,sizeof rgb,3902)==1);
    xdj_beta_invalidate();
    assert(xdj_beta_apply_or_trace_surfaces(row+1,info+1)==0);
    for(i=1;i<=8120;i++) assert(info[i]==0);
    bounds(); return 0;
}
