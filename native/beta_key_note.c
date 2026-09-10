#include <stdint.h>

/* The input flag is stock record+38, calculated at FILE 0x129221e..0x1292268
 * against the same four key IDs used by INFO. Do not recompute musical rules.
 * Preserve stock high flags and all non-track types. For note families, green
 * now means key compatibility; title styling remains owned by stock.
 * IDs below index the verified stock icon table, not raw bitmap addresses.
 */
uint32_t xdj_beta_key_note(uint32_t item, uint32_t compatible)
{
    uint32_t normal, green;
    switch (item & 255u) {
    case 4: case 5: case 91: normal=(item & 255u)==5u ? 5u : 4u; green=91; break;
    case 47: case 48: case 96: normal=(item & 255u)==48u ? 48u : 47u; green=96; break;
    case 101: case 102: normal=101; green=102; break;
    case 104: case 105: normal=104; green=105; break;
    case 107: case 108: normal=107; green=108; break;
    case 110: case 111: normal=110; green=111; break;
    default: return item;
    }
    return (item & ~255u) | (compatible == 1u ? green : normal);
}
