#include "preview_queue.h"
static void key_copy(uint8_t *to,const uint8_t *from) {
    size_t i;for(i=0;i<XDJ_KEY_BYTES;++i)to[i]=from[i];
}
static int equal(const uint8_t *a,const uint8_t *b) {
    size_t i;for(i=0;i<XDJ_KEY_BYTES;++i)if(a[i]!=b[i])return 0;return 1;
}
static uint32_t word(const uint8_t *p) {
    return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];
}
static void layout_copy(xdj_cell_layout *a,const xdj_cell_layout *b) {
    a->columns=b->columns;a->height=b->height;a->top_row=b->top_row;
}
static int same_layout(const xdj_cell_layout *a,const xdj_cell_layout *b) {
    return a->columns==b->columns && a->height==b->height && a->top_row==b->top_row;
}
void xdj_preview_queue_reset(xdj_preview_queue *q) {
    size_t i;if(!q)return;
    q->count=q->selected=q->enabled=q->busy=q->mode=q->pending_mode=0;
    q->serial=q->active_token=0;
    q->layout.columns=q->layout.height=q->layout.top_row=0;
    q->pending_layout.columns=q->pending_layout.height=q->pending_layout.top_row=0;
    for(i=0;i<XDJ_KEY_BYTES;++i)q->pending_key[i]=0;
    for(i=0;i<XDJ_VISIBLE_ROWS;++i) {q->rows[i].eligible=0;q->rows[i].failed=0;}
}
int xdj_preview_queue_set(xdj_preview_queue *q,
    const xdj_track_identity *ids,const uint8_t *eligible,size_t count,
    size_t selected,xdj_preview_mode mode,const xdj_cell_layout *layout,int enabled) {
    xdj_visible_row next[XDJ_VISIBLE_ROWS];size_t i,j;int same;
    if(!q || q->count>XDJ_VISIBLE_ROWS || count>XDJ_VISIBLE_ROWS ||
       (count && (!ids || !eligible || selected>=count)) || !layout ||
       !layout->columns || layout->columns>XDJ_ADAPTER_COLUMNS || layout->height<2 ||
       (mode!=XDJ_PREVIEW_BLUE && mode!=XDJ_PREVIEW_RGB))return 0;
    same=q->mode==(uint8_t)mode && same_layout(&q->layout,layout);
    for(i=0;i<count;++i) {
        next[i].eligible=0;next[i].failed=0;
        if(!eligible[i])continue;
        if(!xdj_make_track_key(&ids[i],next[i].key))return 0;
        next[i].eligible=1;
        if(same)for(j=0;j<q->count;++j)
            if(q->rows[j].eligible && equal(next[i].key,q->rows[j].key))
                next[i].failed=(uint8_t)(next[i].failed|q->rows[j].failed);
    }
    for(i=0;i<count;++i) {
        q->rows[i].eligible=next[i].eligible;q->rows[i].failed=next[i].failed;
        if(next[i].eligible)key_copy(q->rows[i].key,next[i].key);
    }
    q->count=(uint8_t)count;q->selected=(uint8_t)(count?selected:0);
    q->enabled=(uint8_t)(enabled!=0);q->mode=(uint8_t)mode;layout_copy(&q->layout,layout);
    return 1;
}
int xdj_preview_queue_next(xdj_preview_queue *q,const xdj_wave_cache *cache,
                           xdj_preview_job *job) {
    size_t k,index;
    if(!q || !job || q->count>XDJ_VISIBLE_ROWS || (q->count && q->selected>=q->count))return -1;
    if(q->busy || !q->enabled || !q->count)return 0;
    if(!cache || cache->count<q->count)return -1;
    for(k=0;k<q->count;++k) {
        xdj_adapter_result result;
        /* Selected first, then all other rows in display order, no modulo. */
        index=k==0?q->selected:(k<=q->selected?k-1:k);
        if(!q->rows[index].eligible || q->rows[index].failed)continue;
        result=xdj_adapter_lookup(cache,q->rows[index].key,(xdj_preview_mode)q->mode,&q->layout);
        if(result==XDJ_ADAPTER_HIT)continue;
        if(result!=XDJ_ADAPTER_MISS || q->serial==UINT32_MAX)return -1;
        q->active_token=++q->serial;q->busy=1;q->pending_mode=q->mode;
        key_copy(q->pending_key,q->rows[index].key);layout_copy(&q->pending_layout,&q->layout);
        job->token=q->active_token;job->mode=(xdj_preview_mode)q->mode;
        layout_copy(&job->layout,&q->layout);
        job->identity.source_player=q->pending_key[0];job->identity.source_slot=q->pending_key[1];
        job->identity.track_type=q->pending_key[2];job->identity.track_id=word(q->pending_key+4);
        job->identity.media_epoch_hi=word(q->pending_key+8);
        job->identity.media_epoch_lo=word(q->pending_key+12);
        return 1;
    }
    return 0;
}
int xdj_preview_queue_current(void *context,const uint8_t *key) {
    xdj_preview_queue *q=(xdj_preview_queue *)context;size_t i;
    if(!q || !key || !q->busy || !q->enabled || q->count>XDJ_VISIBLE_ROWS ||
       q->mode!=q->pending_mode || !same_layout(&q->layout,&q->pending_layout) ||
       !equal(key,q->pending_key))return 0;
    for(i=0;i<q->count;++i)if(q->rows[i].eligible && equal(key,q->rows[i].key))return 1;
    return 0;
}
int xdj_preview_queue_finish(xdj_preview_queue *q,uint32_t token,xdj_adapter_result result) {
    size_t i;
    if(!q || !q->busy || token!=q->active_token)return 0;
    if(xdj_preview_queue_current(q,q->pending_key) &&
       result!=XDJ_ADAPTER_PREPARED && result!=XDJ_ADAPTER_HIT)
        for(i=0;i<q->count;++i)if(q->rows[i].eligible && equal(q->rows[i].key,q->pending_key))
            q->rows[i].failed=1;
    q->busy=0;q->active_token=0;return 1;
}
void xdj_preview_queue_retry(xdj_preview_queue *q) {
    size_t i;if(q && q->count<=XDJ_VISIBLE_ROWS)for(i=0;i<q->count;++i)q->rows[i].failed=0;
}
