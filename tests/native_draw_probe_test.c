#include "draw_probe.h"
#include <assert.h>
#include <stdint.h>

int main(void) {
    uint16_t buffer[30 * 83 + 2];
    size_t i, x, y;
    int stage, order;
    for (order = 0; order <= 1; ++order) {
        for (stage = 0; stage <= 2; ++stage) {
            for (i = 0; i < sizeof(buffer)/sizeof(buffer[0]); ++i) buffer[i] = 0x1234;
            assert(xdj_draw_probe(buffer+1, 28*83, 83, stage, order, 1) == XDJ_CELL_DRAWN);
            assert(buffer[0] == 0x1234);
            for (y=0; y<28; ++y) {
                for (x=80; x<83; ++x) assert(buffer[1+y*83+x] == 0x1234);
                for (x=0; x<80; ++x) {
                    uint16_t want;
                    if (stage == 0) want = order == 0 ? 0xf800 : 0x001f;
                    else if (y == 27) want = 0xffff;
                    else if (stage == 1) want = x<26 ? (order==0 ? 0xf800 : 0x001f) :
                        (x<53 ? 0x07e0 : (order==0 ? 0x001f : 0xf800));
                    else {
                        size_t first = x<20 ? 24 : (x<40 ? 18 : (x<60 ? 9 : 0));
                        want = y >= first ? 0xffff : 0;
                    }
                    assert(buffer[1+y*83+x] == want);
                }
            }
            for (i=1+28*83; i<sizeof(buffer)/sizeof(buffer[0]); ++i) assert(buffer[i]==0x1234);
        }
    }
    for (i=0; i<sizeof(buffer)/sizeof(buffer[0]); ++i) buffer[i]=0x1234;
    assert(xdj_draw_probe(buffer, 2239, 80, 0, 0, 1)==XDJ_CELL_INVALID);
    assert(xdj_draw_probe(buffer, 2240, 79, 0, 0, 1)==XDJ_CELL_INVALID);
    assert(xdj_draw_probe(buffer, 2240, 80, 99, 0, 1)==XDJ_CELL_INVALID);
    assert(xdj_draw_probe(buffer, 2240, 80, 0, 99, 1)==XDJ_CELL_INVALID);
    assert(xdj_draw_probe(buffer, 2240, 80, 0, 0, 0)==XDJ_CELL_SKIPPED);
    for (i=0; i<sizeof(buffer)/sizeof(buffer[0]); ++i) assert(buffer[i]==0x1234);
    return 0;
}
