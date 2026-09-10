#include "beta_runtime.h"
#include <assert.h>
#include <stdio.h>

void xdj_beta_trace_reset(void);
void xdj_beta_trace(uint32_t stage);
int xdj_beta_apply_or_trace_surfaces(uint16_t *, uint16_t *);
static uint8_t rgb[7228];
static uint16_t row[2242], info[13106];

static void reset(void)
{
    size_t i;
    for (i=0;i<2242;i++) row[i]=0x5a5a;
    for (i=0;i<13106;i++) info[i]=0x6b6b;
}
static void unchanged(void)
{
    size_t i;
    for (i=0;i<2242;i++) assert(row[i]==0x5a5a);
    for (i=0;i<13106;i++) assert(info[i]==0x6b6b);
}
int main(int argc, char **argv)
{
    unsigned i;
    FILE *f;
    assert(argc==2);
    f=fopen(argv[1],"rb"); assert(f);
    assert(fread(rgb,1,sizeof rgb,f)==sizeof rgb);
    assert(fgetc(f)==EOF); fclose(f);
    reset();
    for (i=0;i<12;i++) {
        xdj_beta_trace_reset(); xdj_beta_trace(i);
        assert(xdj_beta_apply_or_trace_surfaces(row+1,info+1)==0);
        unchanged();
    }
    assert(xdj_beta_prepare_rgb(rgb,sizeof rgb,3902)==1);
    xdj_beta_invalidate();
    assert(xdj_beta_apply_or_trace_surfaces(row+1,info+1)==0);
    unchanged();
    assert(xdj_beta_prepare_rgb(rgb,sizeof rgb,3902)==1);
    assert(xdj_beta_apply_or_trace_surfaces(row+1,info+1)==1);
    assert(row[1+27*80]==0xffff && info[1+116*112]==0xffff);
    assert(row[0]==0x5a5a && row[2241]==0x5a5a);
    assert(info[0]==0x6b6b && info[13105]==0x6b6b);
    reset();
    assert(xdj_beta_apply_or_trace_surfaces(row+1,info+1)==0);
    unchanged();
    return 0;
}
