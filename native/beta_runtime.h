#ifndef XDJ_BETA_RUNTIME_H
#define XDJ_BETA_RUNTIME_H

#include <stddef.h>
#include <stdint.h>

/* Runtime bridge for firmware 1.44 only. The assembly hooks own all stock ABI
 * calls; this unit validates and converts borrowed dbserver payloads, then
 * copies a completed frame into the two stock JPEG cache surfaces. */
void xdj_beta_invalidate(void);
int xdj_beta_prepare_rgb(const uint8_t *blob, uint32_t bytes, uint32_t track_id);
int xdj_beta_prepare_blue(const uint8_t *blob, uint32_t bytes, uint32_t track_id);
int xdj_beta_apply_surfaces(uint16_t *row_surface, uint16_t *info_surface);

extern const char xdj_beta_pwv4_tag[5];
extern const char xdj_beta_ext_name[4];

#endif
