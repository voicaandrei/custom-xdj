#include <stdint.h>
#include <assert.h>
#include <string.h>
static uint32_t d[7], s[13], other[7];
static int create_count, access_count, resource_count;
static int create(void *a, void *b) { assert(a && b); ++create_count; return -7; }
static int access(void *a,void *b,void *c) { assert(a && b && c); ++access_count; return 5; }
static const void *get_resource(int id) { assert(id==3); ++resource_count; return other; }
#define INFO_DESCRIPTOR ((uintptr_t)d)
#define STOCK_CREATE create
#define STOCK_ACCESS access
#define STOCK_RESOURCE get_resource
#include "beta_info_band.c"
int main(void)
{
    uint32_t before[13];
    unsigned i;
    memset(d, 0x5a, sizeof d); memset(s, 0x6b, sizeof s);
    memcpy(before,s,sizeof s);
    assert(xdj_beta_info_create(other,s)==-7);
    assert(memcmp(before,s,sizeof s)==0);
    assert(xdj_beta_info_create(d,s)==-7);
    assert(d[0]==0x5a5a5a5a && d[1]==500 && d[2]==284);
    assert(((uint16_t *)d)[6]==290 && ((uint16_t *)d)[7]==290);
    assert(((uint16_t *)d)[8]==28 && ((uint16_t *)d)[9]==0x5a5a);
    assert(d[5]==0x5a5a5a5a && d[6]==0x5a5a5a5a);
    assert(s[7]==500 && s[8]==284 && s[2]==((28u<<16)|290u));
    for(i=0;i<13;i++) if(i!=2 && i!=7 && i!=8) assert(s[i]==before[i]);
    ((uint16_t *)d)[7]=120;
    assert(xdj_beta_info_access(s,s,s,d)==5 && ((uint16_t *)d)[7]==290);
    assert(xdj_beta_info_fallback(3,other)==other && resource_count==1);
    assert(xdj_beta_info_fallback(3,d)==&empty_resource && resource_count==1);
    for(i=0;i<290*28;i++) assert(empty_resource.pixels[i]==0);
    assert(create_count==2 && access_count==1);
    return 0;
}
