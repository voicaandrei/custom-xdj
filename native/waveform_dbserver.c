#include "waveform_dbserver.h"
static uint32_t be32(const uint8_t *p) {
    return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];
}
xdj_adapter_result xdj_adapter_prepare_dbserver(
    xdj_wave_cache *cache, const uint8_t *key, xdj_preview_mode mode,
    const xdj_cell_layout *layout, const uint8_t *blob, size_t bytes,
    uint8_t *scratch, size_t scratch_bytes, xdj_pack_rgb8 pack, void *context) {
    size_t i;
    if (!blob) return XDJ_ADAPTER_INVALID;
    if (mode==XDJ_PREVIEW_BLUE) {
        if (bytes!=900u || !scratch || scratch_bytes<XDJ_PWAV_BYTES)
            return XDJ_ADAPTER_INVALID;
        for (i=0;i<800u;i+=2u)
            if (blob[i]>31u || blob[i+1u]>7u) return XDJ_ADAPTER_INVALID;
        for (i=0;i<XDJ_PWAV_BYTES;++i)
            scratch[i]=(uint8_t)(blob[2u*i]|(blob[2u*i+1u]<<5));
        return xdj_adapter_prepare(cache,key,mode,layout,scratch,XDJ_PWAV_BYTES,pack,context);
    }
    if (mode==XDJ_PREVIEW_RGB) {
        if (bytes!=7228u || blob[0]!=0x38u || blob[1]!=0x1cu || blob[2] || blob[3] ||
            blob[4]!='P' || blob[5]!='W' || blob[6]!='V' || blob[7]!='4' ||
            be32(blob+8)!=24u || be32(blob+12)!=7224u ||
            be32(blob+16)!=6u || be32(blob+20)!=1200u) return XDJ_ADAPTER_INVALID;
        return xdj_adapter_prepare(cache,key,mode,layout,blob+28,XDJ_PWV4_BYTES,pack,context);
    }
    return XDJ_ADAPTER_INVALID;
}
