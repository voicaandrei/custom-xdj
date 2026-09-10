/* Host-only diagnostic. Calls project C, never firmware, USB or stock ABI.
 * Demonstrates API sequences; does not simulate the player scheduler. */
#include "beta_runtime.h"
#include "waveform_prepare.h"
#include "waveform_cell.h"
#include "pixel_channels.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

static uint8_t a[900], b[900], rgb[7200];
static uint16_t row[2240], info[8120], expected[2240], pixels[8122];
static xdj_wave_column columns[290];
static volatile unsigned witness;

static double bench(unsigned width, int is_rgb) {
    unsigned round, repeat;
    double times[7];
    xdj_channel_order order = XDJ_CHANNEL_ORDER_RGB;
    for (round=0; round<7; ++round) {
        clock_t start=clock();
        for (repeat=0; repeat<500; ++repeat) {
            unsigned pass;
            for (pass=0; pass<2; ++pass) {
                unsigned w=pass ? 290 : width;
                assert((is_rgb
                    ? xdj_prepare_pwv4_scaled(rgb,sizeof rgb,columns,w,27,xdj_pack_rgb8_context,&order)
                    : xdj_prepare_pwav_scaled(a,400,columns,w,27,xdj_pack_rgb8_context,&order))
                    == XDJ_PREVIEW_PREPARED);
                pixels[0]=0x1234; pixels[w*28+1]=0x5678;
                assert(xdj_waveform_cell_draw_region(pixels+1,w*28,w,0,w,28,
                    columns,w,0,0xffff,1)==XDJ_CELL_DRAWN);
                assert(pixels[0]==0x1234 && pixels[w*28+1]==0x5678);
                witness+=pixels[1+repeat%(w*27)];
            }
        }
        times[round]=(double)(clock()-start)/CLOCKS_PER_SEC*1e6/500;
    }
    for(round=0;round<7;round++) {
        unsigned j;
        for(j=round+1;j<7;j++) if(times[j]<times[round]) {
            double t=times[j];times[j]=times[round];times[round]=t;
        }
    }
    return times[3];
}

int main(void) {
    unsigned i;
    int stale, reset, overwritten;
    for(i=0;i<400;i++) { a[2*i]=5; b[2*i]=25; }
    for(i=0;i<1200;i++) {
        rgb[6*i+3]=(uint8_t)(i*17u);
        rgb[6*i+4]=(uint8_t)(i*31u);
        rgb[6*i+5]=(uint8_t)(i*7u);
    }
    assert(xdj_beta_prepare_blue(a,sizeof a,1)==1);
    assert(xdj_beta_prepare_blue(NULL,0,2)==0);
    stale=xdj_beta_apply_surfaces(row,info);
    assert(stale==1); /* Invalid prepare alone leaves the preceding frame. */
    assert(xdj_beta_prepare_blue(a,sizeof a,1)==1);
    xdj_beta_invalidate();
    assert(xdj_beta_prepare_blue(NULL,0,2)==0);
    reset=xdj_beta_apply_surfaces(row,info);
    assert(reset==0); /* Current assembly's explicit reset protects this sequence. */

    assert(xdj_beta_prepare_blue(b,sizeof b,2)==1);
    assert(xdj_beta_apply_surfaces(expected,info)==1);
    assert(xdj_beta_prepare_blue(a,sizeof a,1)==1);
    assert(xdj_beta_prepare_blue(b,sizeof b,2)==1);
    assert(xdj_beta_apply_surfaces(row,info)==1);
    overwritten=memcmp(row,expected,sizeof row)==0;
    assert(overwritten); /* apply has no expected identity argument. */
    printf("{\"invalid_prepare_retains_previous_frame\":%s,"
           "\"explicit_reset_rejects_previous_frame\":%s,"
           "\"second_prepare_replaces_first_without_consumer_identity\":%s,"
           "\"host_median_cpu_us_per_prepare_draw_pair\":[",
           stale?"true":"false",reset==0?"true":"false",overwritten?"true":"false");
    for(i=0;i<3;i++) {
        unsigned width=80+40*i;
        double blue=bench(width,0), color=bench(width,1);
        printf("%s{\"row_width\":%u,\"info_width\":290,\"blue\":%.3f,\"rgb\":%.3f}",
               i?",":"",width,blue,color);
    }
    puts("]}");
    return 0;
}
