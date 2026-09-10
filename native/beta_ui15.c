/* MAIN 1.44 SHA 9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0.
 * Pointers explicitly CODE/RAM. Geometry uses rectangle edges (not width),
 * confirmed at FILE 0x146d0ae..bc and 0x152c774..80.
 * Helpers run in the existing browser UI task only; no DB/IO/allocation.
 */
#include <stdint.h>
#ifndef STOCK_OBJECT
#define STOCK_OBJECT ((void *(*)(void *,int))0x09521e92u)
#define STOCK_LEFT ((int (*)(void *,int,int))0x09522202u)
#define STOCK_ICON ((int (*)(unsigned,int,int))0x095242c8u)
#define BROWSE_ROOT (*(void **)0x13bca0b8u)
#define BROWSE_FLAGS (*(volatile uint8_t *)0x0da77d90u)
#define ROW_DESCRIPTORS ((uintptr_t)0x13bca44cu)
#define ICON_TABLE ((const int16_t *)0x13bc877cu)
#endif
/* Group 0 row controls, verified initialized tables at RAM 13bca0ce/0ea. */
static const int16_t note_ids[7]={61,57,53,49,45,41,37};
static const int16_t title_ids[7]={59,55,51,47,43,39,35};
int xdj_beta_row_left(void *root,int id,int left)
{
    unsigned i;
    if (!(BROWSE_FLAGS & 8u) && root==BROWSE_ROOT && left>=190 && left<240) {
        for (i=0;i<7;++i)
            if (id==note_ids[i] || id==title_ids[i]) {
                const uint8_t *d=(const uint8_t *)(ROW_DESCRIPTORS+i*28u);
                if (*(const uint32_t *)d && *(const uint16_t *)(d+12)==160)
                    left+=80;
                break;
            }
    }
    return STOCK_LEFT(root,id,left);
}
static int green_type(unsigned type)
{
    return type==91 || type==96 || type==102 || type==105 || type==108 || type==111;
}
int xdj_beta_icon_resource(unsigned item,int selected,int group)
{
    int result=STOCK_ICON(item,selected,group);
    unsigned normal;
    item &= 0xffffu; /* same extu.w normalization as stock getter */
    if (!green_type(item)) return result;
    /* Green families are absent from the stock secondary-group whitelist.
     * Check visibility using the corresponding normal type first. */
    switch(item) {
    case 91:normal=4;break; case 96:normal=47;break;
    default:normal=item-1;break;
    }
    if (STOCK_ICON(normal,selected,group)<0) return result;
    return ICON_TABLE[item*3u+(selected==1?1u:0u)];
}
/* Hooked entry trampolines replay original pushes, never recurse into hook. */
extern int xdj_beta_title_original(int group,int row);
extern int xdj_beta_note_original(int group,int row);
static int suppress_comment(int group,int row)
{
    unsigned i;
    if (group!=1 || row!=6 || !(BROWSE_FLAGS & 8u) || !BROWSE_ROOT) return 0;
    /* INFO's last metadata row is replaced by the waveform band. Both text
     * and icon must be hidden; leaving marquee initialization running would
     * allow the text to reappear. Owner explicitly requested its removal. */
    for(i=12;i<=13;++i) {
        void *o=STOCK_OBJECT(BROWSE_ROOT,(int)i);
        if(o) {
            uintptr_t *v=*(uintptr_t **)o;
            ((int (*)(void *,int))v[5])(o,0);
        }
    }
    return 1;
}
int xdj_beta_title(int group,int row)
{
    if(suppress_comment(group,row)) return 1;
    return xdj_beta_title_original(group,row);
}
int xdj_beta_note(int group,int row)
{
    if(suppress_comment(group,row)) return 1;
    return xdj_beta_note_original(group,row);
}
