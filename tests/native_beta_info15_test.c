#include <stdint.h>
#include <assert.h>
#include <string.h>
static uint32_t d[7],s[13],other[7];
static uint16_t src[8066],dst[8066];
static uint32_t supplied_pitch;
static uint16_t *supplied_pixels;
static int access_result,release_count,access_count;
static int create(void *a,void *b) { assert(a && b); return -7; }
static int access_pixels(void *a,void *b,void *c) {
    assert(a && b && c); ++access_count;
    *(uint16_t **)b=supplied_pixels; *(uint32_t *)c=supplied_pitch;
    return access_result;
}
static int release_pixels(void *a) { assert(a==s); ++release_count; return 0; }
static const void *get_resource(int id) { assert(id==3); return other; }
#define INFO_DESCRIPTOR ((uintptr_t)d)
#define STOCK_CREATE create
#define STOCK_ACCESS access_pixels
#define STOCK_RELEASE release_pixels
#define STOCK_RESOURCE get_resource
static uint32_t rows[7][7];
static uint8_t browse_flags;
static int destroy_count,draw_count;
static int destroy(void *d) { ++destroy_count; *(uint32_t *)d=0; return 1; }
static int draw(int row,int destination) { assert(row>=0 && destination>=0); ++draw_count; return 9; }
#define ROW_DESCRIPTORS ((uintptr_t)rows)
#define BROWSE_FLAGS browse_flags
#define STOCK_DESTROY destroy
#define STOCK_ARTWORK draw
#include "beta_info_band15.c"
int main(void) {
    unsigned i,scenario; uint16_t *pixels=0; uint32_t pitch=0;
    uint32_t before[13];
    memset(d,0x5a,sizeof d); memset(s,0x6b,sizeof s); memcpy(before,s,sizeof s);
    assert(xdj_beta_info_create(other,s)==-7 && memcmp(s,before,sizeof s)==0);
    assert(xdj_beta_info_create(d,s)==-7);
    assert(d[1]==500 && d[2]==284 && s[7]==500 && s[8]==284);
    assert(((uint16_t *)d)[6]==288 && ((uint16_t *)d)[7]==288);
    assert(((uint16_t *)d)[8]==28 && s[2]==((28u<<16)|288u));
    for(i=0;i<13;++i) if(i!=2 && i!=7 && i!=8) assert(s[i]==before[i]);
    for(i=0;i<8066;++i) src[i]=(uint16_t)(i*7u+1u);
    for(scenario=0;scenario<7;++scenario) {
        memset(dst,0xa5,sizeof dst); supplied_pixels=dst+1; supplied_pitch=576;
        access_result=0; release_count=0;
        if(scenario==1) supplied_pitch=580;
        if(scenario==2) supplied_pitch=575;
        if(scenario==3) supplied_pixels=0;
        if(scenario==4) access_result=5;
        if(scenario==5) supplied_pitch=574;
        ((uint16_t *)d)[7]=113;
        assert(xdj_beta_info_access(s,&pixels,&pitch,d,scenario==6?0:src+1)==(scenario==4?5:1));
        assert(((uint16_t *)d)[7]==288);
        assert(release_count==(scenario==4?0:1));
        assert(dst[0]==0xa5a5 && dst[8065]==0xa5a5);
        for(i=1;i<=8064;++i) assert(dst[i]==(scenario==0?src[i]:0xa5a5));
    }
    release_count=0; access_result=0; supplied_pixels=dst+1; supplied_pitch=160;
    assert(xdj_beta_info_access(s,&pixels,&pitch,other,src+1)==0);
    assert(release_count==0 && pitch==160 && pixels==dst+1);
    assert(xdj_beta_info_fallback(3,other)==other);
    assert(xdj_beta_info_fallback(3,d)==&empty_resource);
    for(i=0;i<8064;++i) assert(empty_resource.pixels[i]==0);
    for (scenario=0;scenario<7;++scenario) {
        uint16_t *dims=(uint16_t *)rows[scenario];
        browse_flags=0; rows[scenario][0]=123; dims[6]=80;
        assert(xdj_beta_artwork_draw(scenario,scenario)==9);
        assert(rows[scenario][0]==0 && destroy_count==(int)scenario+1);
        assert(xdj_beta_info_create(rows[scenario],s)==-7 && dims[6]==160 && dims[7]==80);
        supplied_pixels=dst+1; supplied_pitch=320; release_count=0;
        memset(dst,0xa5,sizeof dst);
        assert(xdj_beta_info_access(s,&pixels,&pitch,rows[scenario],src+1)==1);
        assert(release_count==1 && dst[0]==0xa5a5 && dst[4481]==0xa5a5);
        for(i=0;i<4480;++i) assert(dst[i+1]==src[(i/160)*80+(i%160)/2+1]);
        supplied_pitch=322; memset(dst,0xa5,sizeof dst); release_count=0;
        assert(xdj_beta_info_access(s,&pixels,&pitch,rows[scenario],src+1)==1 && release_count==1);
        for(i=0;i<8066;++i) assert(dst[i]==0xa5a5);
        browse_flags=8;
        assert(xdj_beta_info_create(rows[scenario],s)==-7 && dims[6]==80 && dims[7]==80);
        release_count=0;
        assert(xdj_beta_info_access(s,&pixels,&pitch,rows[scenario],src+1)==0 && !release_count);
    }
    return 0;
}
