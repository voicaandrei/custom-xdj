#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "beta_preview_scope15.c"
int main(void) {
    uint8_t context[256],before[256]; unsigned i,j; uint32_t saved;
    assert(xdj_beta_preview_enter(0)==0); xdj_beta_preview_leave(0,0x101);
    for(i=0;i<256;++i) {
        memset(context,0xa5,sizeof context); context[13]=(uint8_t)i;
        memcpy(before,context,sizeof context);
        for(j=0;j<100;++j) {
            saved=xdj_beta_preview_enter(context); assert(saved==(0x100u|i));
            assert(context[13]==0 && context[12]==0xa5);
            xdj_beta_preview_leave(context,saved);
            assert(!memcmp(context,before,sizeof context));
        }
        xdj_beta_preview_leave(context,0); assert(!memcmp(context,before,sizeof context));
    }
    return 0;
}
