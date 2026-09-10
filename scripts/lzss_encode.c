/* Original host-only encoder for the already established MK2 LZSS format.
 * No firmware execution. Window 4096, lengths 3..18, cursor initially 4078.
 * Previous input positions are indexed by three-byte hashes; overlap allowed. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#define NIL SIZE_MAX
static size_t find_match(const uint8_t *input,size_t length,size_t pos,
                         const size_t *heads,const size_t *previous,size_t *match) {
    size_t best=0,candidate;unsigned h,scans=0;
    if(length-pos<3)return 0;
    h=((unsigned)input[pos]*251u+(unsigned)input[pos+1]*31u+input[pos+2])&65535u;
    candidate=heads[h];
    while(candidate!=NIL && pos-candidate<=4096 && scans++<4096) {
        size_t count=0;
        while(count<18 && count<length-pos && input[candidate+count]==input[pos+count])count++;
        if(count>=3 && count>best){best=count;*match=candidate;if(best==18)break;}
        candidate=previous[candidate];
    }
    return best;
}
size_t xdj_lzss_encode(const uint8_t *input,size_t length,uint8_t *output,size_t capacity) {
    size_t *previous,*heads,pos=0,out=0,i;
    if (!input || !output || length>SIZE_MAX/sizeof(size_t) ||
        length>SIZE_MAX-length/8-1 || capacity<length+length/8+1) return 0;
    previous=malloc((length?length:1)*sizeof(size_t));
    heads=malloc(65536*sizeof(size_t));
    if (!previous || !heads) {free(previous);free(heads);return 0;}
    for(i=0;i<65536;i++) heads[i]=NIL;
    while(pos<length) {
        size_t flag_at=out++;unsigned bit;
        output[flag_at]=0;
        for(bit=0;bit<8 && pos<length;bit++) {
            size_t best,match=0,start=pos;
            best=find_match(input,length,pos,heads,previous,&match);
            /* Lazy match: one literal can expose a substantially longer run. */
            if(best>=3 && best<18 && length-pos>1) {
                size_t next_match=0;
                size_t next=find_match(input,length,pos+1,heads,previous,&next_match);
                if(next>best)best=0;
            }
            if(best>=3) {
                size_t index=(4078+match)&4095;
                output[out++]=(uint8_t)index;
                output[out++]=(uint8_t)(((index>>4)&240)|(best-3));
                pos+=best;
            } else {output[flag_at]|=(uint8_t)(1u<<bit);output[out++]=input[pos++];}
            for(i=start;i<pos;i++) {
                if(length-i>=3) {
                    unsigned h=((unsigned)input[i]*251u+(unsigned)input[i+1]*31u+input[i+2])&65535u;
                    previous[i]=heads[h];heads[h]=i;
                } else previous[i]=NIL;
            }
        }
    }
    free(previous);free(heads);return out;
}
