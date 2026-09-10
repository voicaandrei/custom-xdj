#ifndef XDJ_PREVIEW_QUEUE_H
#define XDJ_PREVIEW_QUEUE_H
#include "waveform_adapter.h"
#define XDJ_VISIBLE_ROWS 7u
/* Project-owned state, never overlaid onto firmware structures. Caller owns
 * storage and serializes all calls. Reset only before use, or once no worker
 * can still return. Network IO is performed elsewhere, outside repaint. */
typedef struct { uint8_t key[XDJ_KEY_BYTES]; uint8_t eligible, failed; } xdj_visible_row;
typedef struct {
    xdj_visible_row rows[XDJ_VISIBLE_ROWS];
    uint8_t pending_key[XDJ_KEY_BYTES];
    xdj_cell_layout layout, pending_layout;
    uint32_t serial, active_token;
    uint8_t count, selected, enabled, busy, mode, pending_mode;
} xdj_preview_queue;
typedef struct {
    uint32_t token;
    xdj_track_identity identity;
    xdj_cell_layout layout;
    xdj_preview_mode mode;
} xdj_preview_job;
void xdj_preview_queue_reset(xdj_preview_queue *queue);
/* identities/eligible have count elements; input does not alias queue. Caller
 * obtains eligibility from browser_row and source/epoch from the real owner.
 * Invalid inputs leave queue unchanged. count=0 clears the visible list.
 * Updating rows does NOT free the pending worker slot or reset its token. */
int xdj_preview_queue_set(xdj_preview_queue *queue,
    const xdj_track_identity *identities,const uint8_t *eligible,size_t count,
    size_t selected,xdj_preview_mode mode,const xdj_cell_layout *layout,int enabled);
/* 1: job returned; 0: busy/no work; -1: invalid cache/state or token exhaustion.
 * Checks cache before issuing work, including eviction since the previous view.
 * Requires capacity >= visible row count. Failures are suppressed until retry.
 * Only one worker may be dispatched per queue. Job output must be disjoint. */
int xdj_preview_queue_next(xdj_preview_queue *queue,const xdj_wave_cache *cache,
                           xdj_preview_job *job);
/* Matches request_current callback. Safe only under caller's serialization.
 * Validity follows key/mode/layout, so a piece moving to another row is valid. */
int xdj_preview_queue_current(void *queue,const uint8_t *key);
/* Must be called exactly once after query adapter returns, including failures.
 * Rejects wrong/duplicate token. A stale completion cannot mark new rows failed.
 * No cache/surface mutation is performed here. */
int xdj_preview_queue_finish(xdj_preview_queue *queue,uint32_t token,
                             xdj_adapter_result result);
void xdj_preview_queue_retry(xdj_preview_queue *queue);
#endif
