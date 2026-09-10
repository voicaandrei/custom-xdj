#include <assert.h>
#include <stdint.h>
#include <string.h>
static uint32_t rows[7][7];
static uint8_t flags;
static int16_t icons[113*3];
static uintptr_t objects[2][12],vtable[6];
static void *root=rows;
static int final_left, left_calls, hidden, title_calls,note_calls;
static void *get_object(void *r,int id) { assert(r==root && (id==12||id==13)); return objects[id-12]; }
static int set_left(void *r,int id,int left) { (void)r; (void)id; ++left_calls; final_left=left; return -3; }
static int get_icon(unsigned type,int selected,int group) {
    if(type>=113) return -1;
    if(group==1 && type!=4 && type!=47 && type!=101 && type!=104) return -1;
    return icons[type*3+(selected==1?1:2)];
}
static int hide(void *o,int visible) { assert((o==objects[0]||o==objects[1])&&!visible); ++hidden; return 1; }
#define STOCK_OBJECT get_object
#define STOCK_LEFT set_left
#define STOCK_ICON get_icon
#define BROWSE_ROOT root
#define BROWSE_FLAGS flags
#define ROW_DESCRIPTORS ((uintptr_t)rows)
#define ICON_TABLE icons
#include "beta_ui15.c"
int xdj_beta_title_original(int group,int row) { (void)group;(void)row; ++title_calls; return 7; }
int xdj_beta_note_original(int group,int row) { (void)group;(void)row; ++note_calls; return 8; }
int main(void) {
    unsigned i,t; int selected,group;
    vtable[5]=(uintptr_t)hide; objects[0][0]=objects[1][0]=(uintptr_t)vtable;
    for(i=0;i<339;++i) icons[i]=(int16_t)(1000+i);
    for(t=0;t<120;++t) for(group=0;group<2;++group) for(selected=0;selected<2;++selected) {
        int got=xdj_beta_icon_resource(t,selected,group);
        if(green_type(t)) {
            unsigned normal=t==91?4:t==96?47:t-1;
            assert(got==(get_icon(normal,selected,group)<0?get_icon(t,selected,group):icons[t*3+selected]));
        } else assert(got==get_icon(t,selected,group));
    }
    for(i=0;i<7;++i) {
        rows[i][0]=123; ((uint16_t *)rows[i])[6]=160; flags=0;
        assert(xdj_beta_row_left(root,note_ids[i],194)==-3 && final_left==274);
        assert(xdj_beta_row_left(root,title_ids[i],224)==-3 && final_left==304);
        flags=8; xdj_beta_row_left(root,title_ids[i],224); assert(final_left==224);
        flags=0; rows[i][0]=0; xdj_beta_row_left(root,title_ids[i],224); assert(final_left==224);
        rows[i][0]=123; ((uint16_t *)rows[i])[6]=80;
        xdj_beta_row_left(root,title_ids[i],224); assert(final_left==224);
    }
    xdj_beta_row_left(root,12,224); assert(final_left==224);
    xdj_beta_row_left(objects,59,224); assert(final_left==224);
    for(flags=0;flags<16;++flags) for(group=0;group<3;++group) for(i=0;i<8;++i) {
        hidden=title_calls=note_calls=0;
        t=(flags&8)&&group==1&&i==6;
        assert(xdj_beta_title(group,i)==(t?1:7));
        assert(xdj_beta_note(group,i)==(t?1:8));
        assert(hidden==(t?4:0) && title_calls==!t && note_calls==!t);
    }
    return 0;
}
