#ifndef XDJ_TRACK_KEY_H
#define XDJ_TRACK_KEY_H
#include <stdint.h>
#define XDJ_KEY_BYTES 16u
/* Project-owned identity, not a firmware structure. The integration must
 * normalize the source and supply a nonzero media incarnation. Increment it
 * on eject/reinsert/database replacement; never reuse it with a live cache.
 * This v1 contract admits analyzed tracks on USB from players 1..4 only.
 * No artwork identifier participates in this key. */
typedef struct {
    uint32_t track_id;
    uint32_t media_epoch_hi;
    uint32_t media_epoch_lo;
    uint8_t source_player;
    uint8_t source_slot;
    uint8_t track_type;
} xdj_track_identity;
/* Returns 1 on success, 0 with output untouched for invalid inputs.
 * Input/output storage must not overlap. No IO, allocation or global state. */
int xdj_make_track_key(const xdj_track_identity *identity,
                       uint8_t output[XDJ_KEY_BYTES]);
#endif
