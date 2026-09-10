#include <stdint.h>
#include <assert.h>
#include <string.h>
static uint32_t ticks, nav[5];
static int calls;
static void *last_index, *last_identifier;
static int prepare(void *a, void *b) {
    ++calls; last_index=a; last_identifier=b;
    if (a && b) { *(uint32_t *)a=7; *(uint32_t *)b=123; }
    return -9;
}
static uint32_t clock_now(void) { return ticks; }
static uint32_t top(int i) { assert(i==0 || i==1); return nav[1+i]; }
static uint32_t selection(int i) { assert(i==0 || i==1); return nav[3+i]; }
static uint32_t mode(void) { return nav[0]; }
static int pending_result;
static int pending(void *p) { assert(p); return pending_result; }
#define STOCK_LIST_PENDING pending
#define STOCK_PREPARE prepare
#define STOCK_CLOCK clock_now
#define STOCK_TOP top
#define STOCK_SELECTION selection
#define STOCK_MODE mode
#include "beta_browse_observed.c"
static void reset(void) {
    memset(&settle,0,sizeof settle); memset(nav,0,sizeof nav);
    calls=0; ticks=0;
}
int main(void) {
    uint32_t index, id; unsigned i, field;
    reset(); index=0xa5; id=0x5a;
    assert(xdj_beta_browse_prepare(&index,&id)==0);
    for(ticks=1;ticks<250;++ticks) assert(xdj_beta_browse_prepare(&index,&id)==0);
    assert(calls==0 && index==0xa5 && id==0x5a);
    assert(xdj_beta_browse_prepare(&index,&id)==-9);
    assert(calls==1 && index==7 && id==123);
    assert(last_index==&index && last_identifier==&id);
    /* Stable list must refill immediately, not delay each individual row. */
    for(i=0;i<8;++i) assert(xdj_beta_browse_prepare(&index,&id)==-9);
    assert(calls==9);
    /* Both lists, both selections and mode independently restart the timer. */
    for(field=0;field<5;++field) {
        reset(); xdj_beta_browse_prepare(&index,&id);
        for(i=0;i<1000;++i) {
            ticks+=30; ++nav[field]; index=0xa5; id=0x5a;
            assert(xdj_beta_browse_prepare(&index,&id)==0);
            assert(index==0xa5 && id==0x5a);
        }
        assert(calls==0); ticks+=249;
        assert(xdj_beta_browse_prepare(&index,&id)==0);
        ++ticks; assert(xdj_beta_browse_prepare(&index,&id)==-9);
        assert(calls==1);
    }
    reset(); ticks=UINT32_MAX-100;
    assert(xdj_beta_browse_prepare(&index,&id)==0);
    ticks+=249; assert(xdj_beta_browse_prepare(&index,&id)==0);
    ++ticks; assert(xdj_beta_browse_prepare(&index,&id)==-9);
    assert(xdj_beta_browse_prepare(0,&id)==-9 && last_index==0);
    assert(xdj_beta_browse_prepare(&index,0)==-9 && last_identifier==0);
    /* Navigation away and back while artwork was pending used to be missed.
     * The earlier observation must reset quiet time despite identical final state. */
    reset(); ticks=0; xdj_beta_browse_observe(&index);
    ticks=300; assert(xdj_beta_browse_prepare(&index,&id)==-9);
    ticks=310; nav[3]=1; assert(xdj_beta_browse_observe(&index)==0);
    ticks=320; nav[3]=0; assert(xdj_beta_browse_observe(&index)==0);
    ticks=400; assert(xdj_beta_browse_prepare(&index,&id)==0);
    ticks=570; assert(xdj_beta_browse_prepare(&index,&id)==-9);
    /* Pending metadata extends the pause but retains the original predicate. */
    pending_result=7; ticks=600;
    assert(xdj_beta_browse_observe(&index)==7);
    ticks=700; assert(xdj_beta_browse_observe(&index)==7);
    pending_result=0; ticks=800;
    assert(xdj_beta_browse_observe(&index)==0);
    assert(xdj_beta_browse_prepare(&index,&id)==0);
    ticks=950; assert(xdj_beta_browse_prepare(&index,&id)==-9);
    return 0;
}
