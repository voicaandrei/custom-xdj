#include "browser_row.h"
#include <assert.h>
#include <string.h>
int main(void) {
    uint8_t row[276]; uint32_t out; unsigned kind;
    memset(row,0,sizeof(row));row[0]=0x3e;row[1]=0x0f; /* 3902 */
    row[8]=99; /* artwork cannot become track ID */
    for(kind=0;kind<65536u;++kind) {
        int allowed=kind==4 || kind==0x404 || kind==0x4004 || kind==0x4404;
        row[4]=(uint8_t)kind;row[5]=(uint8_t)(kind>>8);out=0xdeadbeef;
        assert(xdj_browser_row_track_id(row,sizeof(row),&out)==allowed);
        assert(out==(allowed?3902u:0xdeadbeefu));
    }
    row[4]=4;row[5]=0;row[8]=0;
    assert(xdj_browser_row_track_id(row,sizeof(row),&out) && out==3902);
    out=123;
    assert(!xdj_browser_row_track_id(row,275,&out));
    assert(!xdj_browser_row_track_id(row,277,&out));
    assert(!xdj_browser_row_track_id(0,276,&out));
    assert(!xdj_browser_row_track_id(row,276,0));
    row[0]=row[1]=0;
    assert(!xdj_browser_row_track_id(row,276,&out));assert(out==123);
    return 0;
}
