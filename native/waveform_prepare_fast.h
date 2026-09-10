#ifndef XDJ_WAVEFORM_PREPARE_FAST_H
#define XDJ_WAVEFORM_PREPARE_FAST_H
#include "waveform_prepare.h"

/* Next-candidate preparation, not linked into frozen BETA 11.
 * Same pixel and callback-order contract as waveform_prepare.h. No IO,
 * allocation, global storage, or changes to source samples. */
typedef struct {
    xdj_wave_column *columns;
    size_t count;
    unsigned int amplitude_height;
} xdj_prepare_target;

xdj_prepare_result xdj_fast_prepare_pwav_scaled(const uint8_t *, size_t,
    xdj_wave_column *, size_t, unsigned int, xdj_pack_rgb8, void *);
xdj_prepare_result xdj_fast_prepare_pwv4_scaled(const uint8_t *, size_t,
    xdj_wave_column *, size_t, unsigned int, xdj_pack_rgb8, void *);

/* Both targets are validated before any callback or output write. Targets,
 * payload and output arrays must be disjoint and remain valid for the call.
 * Output order is targets[0], then targets[1]. RGB global normalization is
 * scanned once, but each width is reduced directly from the original data.
 * Publication and serialization belong to the caller, not this pure unit. */
xdj_prepare_result xdj_fast_prepare_pair(const uint8_t *payload, size_t bytes,
    int rgb, const xdj_prepare_target targets[2], xdj_pack_rgb8 pack, void *context);
#endif
