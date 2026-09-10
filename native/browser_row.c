#include "browser_row.h"
int xdj_browser_row_track_id(const uint8_t *row, size_t bytes, uint32_t *track_id) {
    uint32_t id;
    uint16_t kind;
    if (!row || bytes!=276u || !track_id) return 0;
    kind=(uint16_t)(row[4]|((uint16_t)row[5]<<8));
    if ((kind & (uint16_t)~0x4400u)!=4u) return 0;
    id=(uint32_t)row[0]|((uint32_t)row[1]<<8)|((uint32_t)row[2]<<16)|((uint32_t)row[3]<<24);
    if (!id) return 0;
    *track_id=id;
    return 1;
}
