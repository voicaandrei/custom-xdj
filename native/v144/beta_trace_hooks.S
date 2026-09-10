/* XDJ-1000MK2 MAIN 1.44 only, Test 05 trace build.
 *
 * xdj_beta_getimage_hook replaces the dbcl_GetImage literal inside
 * DbReqJpegData. It derives main track ID from the caller's already validated
 * 276-byte row, requests PWV4 synchronously on the same connection, prepares
 * project-owned pixels, releases that result, then calls stock GetImage.
 * Blue is attempted only when PWV4 is unavailable.
 *
 * xdj_beta_decode_hook replaces the stock JPEG decoder literal. It calls the
 * decoder first, then overwrites the cache entry's A/B pixel buffers only when
 * a matching preparation completed immediately before this response.
 */
    .section .text.xdj_beta_hooks,"ax"
    .balign 4

    .global xdj_beta_getimage_hook
    .type xdj_beta_getimage_hook,@function
xdj_beta_getimage_hook:
    mov.l r8,@-r15
    mov.l r9,@-r15
    mov.l r10,@-r15
    mov.l r11,@-r15
    mov.l r12,@-r15
    mov.l r13,@-r15
    mov.l r14,@-r15
    sts.l pr,@-r15
    add #-32,r15
    mov.l r4,@(0,r15)       /* stock connection */
    mov.l r5,@(4,r15)       /* stock artwork ID */
    mov.l r6,@(8,r15)       /* stock length output */
    mov.l r7,@(12,r15)      /* stock blob output */
    mov #0,r0
    mov.l r0,@(16,r15)      /* waveform bytes */
    mov.l r0,@(20,r15)      /* waveform blob */
    mov.l r0,@(24,r15)      /* metadata */
    mov.l .Lbeta_trace_reset,r1
    jsr @r1
    nop

    /* The shared GetImage literal is also used by a non-local responder branch
     * where caller local +16 was never initialized. DbReqJpegData keeps its
     * context in callee-saved r13 and only the local-browser branch has type 1. */
    tst r13,r13
    bt .Lstock_image
    mov.l @r13,r0
    cmp/eq #1,r0
    bf .Lstock_image

    mov #2,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop

    /* Caller locals start 64 bytes above our SP. Its +16 is the validated row. */
    mov #80,r0
    mov.l @(r0,r15),r8
    tst r8,r8
    bt .Lstock_image
    mov #3,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop
    mov.l @r8,r9            /* row +0: main track ID */
    tst r9,r9
    bt .Lstock_image
    mov #4,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop

    /* The handler has already set connection +8 to the selected row source
     * kind. These are the same two bounded values consumed by the stock
     * waveform-colour getter. */
    mov.l @(0,r15),r4
    mov.l @(8,r4),r5
    mov.l @(4,r4),r4
    mov.l .Lcolour_getter,r1
    jsr @r1
    nop
    cmp/eq #3,r0
    bf .Ltry_blue

    mov #5,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop

    /* dbcl_GetParWaveData(connection, track, "PWV4", "EXT",
     *                     &bytes, &blob, &metadata) */
    add #-12,r15
    mov r15,r10
    add #28,r10             /* original local +16 after temporary stack */
    mov.l r10,@(0,r15)
    mov r15,r10
    add #32,r10             /* original local +20 */
    mov.l r10,@(4,r15)
    mov r15,r10
    add #36,r10             /* original local +24 */
    mov.l r10,@(8,r15)
    mov.l @(12,r15),r4      /* original local +0 */
    mov r9,r5
    mov.l .Lpwv4,r6
    mov.l .Lext,r7
    mov.l .Lget_par_wave,r10
    jsr @r10
    nop
    add #12,r15
    cmp/pz r0
    bf .Lrelease_rgb
    tst r0,r0
    bt .Lrelease_rgb
    mov.l @(20,r15),r4
    tst r4,r4
    bt .Lrelease_rgb
    mov #6,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop
    mov.l @(20,r15),r4
    mov.l @(16,r15),r5
    mov r9,r6
    mov.l .Lprepare_rgb,r1
    jsr @r1
    nop
    tst r0,r0
    bf .Lrelease_rgb_success
.Lrelease_rgb:
    mov #0,r11
    bra .Lrelease_rgb_common
    nop
.Lrelease_rgb_success:
    mov #7,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop
    mov #1,r11
.Lrelease_rgb_common:
    mov.l @(20,r15),r4
    tst r4,r4
    bt .Lafter_rgb_release
    mov.l .Lrelease_blob,r1
    jsr @r1
    nop
.Lafter_rgb_release:
    tst r11,r11
    bf .Lstock_image

    /* No usable PWV4: ask for the stock Blue preview. Selector/optional fields
     * are zero, the conservative default used by the inspected API contract. */
.Ltry_blue:
    mov #8,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop
    mov #0,r0
    mov.l r0,@(16,r15)
    mov.l r0,@(20,r15)
    mov.l r0,@(24,r15)
    add #-12,r15
    mov.l r0,@(0,r15)
    mov.l r0,@(4,r15)
    mov.l r0,@(8,r15)
    mov r15,r10
    add #28,r10
    mov r15,r11
    add #32,r11
    mov.l @(12,r15),r4
    mov r9,r5
    mov r10,r6
    mov r11,r7
    mov.l .Lget_blue_wave,r1
    jsr @r1
    nop
    add #12,r15
    cmp/pz r0
    bf .Lrelease_blue
    tst r0,r0
    bt .Lrelease_blue
    mov.l @(20,r15),r4
    tst r4,r4
    bt .Lrelease_blue
    mov #9,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop
    mov.l @(20,r15),r4
    mov.l @(16,r15),r5
    mov r9,r6
    mov.l .Lprepare_blue,r1
    jsr @r1
    nop
    tst r0,r0
    bt .Lrelease_blue
    mov #10,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop
.Lrelease_blue:
    mov.l @(20,r15),r4
    tst r4,r4
    bt .Lstock_image
    mov.l .Lrelease_blob,r1
    jsr @r1
    nop

    bra .Lstock_image
    nop

.Lstock_image:
    mov.l @(0,r15),r4
    mov.l @(4,r15),r5
    mov.l @(8,r15),r6
    mov.l @(12,r15),r7
    mov.l .Lstock_get_image,r1
    jsr @r1
    nop
    mov r0,r14
    cmp/pz r0
    bf .Lstock_image_failed
    tst r0,r0
    bf .Lstock_image_return
.Lstock_image_failed:
    mov.l .Lbeta_invalidate,r1
    jsr @r1
    nop
.Lstock_image_return:
    add #32,r15
    lds.l @r15+,pr
    mov.l @r15+,r14
    mov.l @r15+,r13
    mov.l @r15+,r12
    mov.l @r15+,r11
    mov.l @r15+,r10
    mov.l @r15+,r9
    mov r14,r0
    rts
    mov.l @r15+,r8

    .balign 4
.Lstock_get_image: .long 0x09293bb0
.Lget_par_wave:    .long 0x0929626c
.Lget_blue_wave:   .long 0x09293d76
.Lcolour_getter:   .long 0x09445274
.Lrelease_blob:    .long 0x09382a9a
.Lbeta_invalidate: .long _xdj_beta_invalidate
.Lbeta_trace_reset: .long _xdj_beta_trace_reset
.Lbeta_trace:      .long _xdj_beta_trace
.Lprepare_rgb:     .long _xdj_beta_prepare_rgb
.Lprepare_blue:    .long _xdj_beta_prepare_blue
.Lpwv4:            .long _xdj_beta_pwv4_tag
.Lext:             .long _xdj_beta_ext_name
    .size xdj_beta_getimage_hook,.-xdj_beta_getimage_hook

    .balign 4
    .global xdj_beta_decode_hook
    .type xdj_beta_decode_hook,@function
xdj_beta_decode_hook:
    mov.l r8,@-r15
    mov.l r9,@-r15
    mov.l r10,@-r15
    mov.l r11,@-r15
    mov.l r12,@-r15
    mov.l r13,@-r15
    mov.l r14,@-r15
    sts.l pr,@-r15
    add #-24,r15
    mov.l r4,@(0,r15)
    mov.l r5,@(4,r15)
    mov.l r6,@(8,r15)
    mov.l r7,@(12,r15)
    /* The stock decoder has exactly five arguments. Surface A is original r7;
     * surface B is argument 5 at original caller SP. After 32 bytes of saved
     * registers and 24 local bytes, that stack argument is current SP +56. */
    mov.l @(12,r15),r8      /* row A surface: saved original r7 */
    mov #56,r0
    mov.l @(r0,r15),r9      /* INFO B surface: original argument 5 */
    add #-4,r15
    mov.l r9,@(0,r15)       /* forward the only stack argument */
    mov.l @(4,r15),r4       /* saved original r4 after SP adjustment */
    mov.l @(8,r15),r5
    mov.l @(12,r15),r6
    mov.l @(16,r15),r7
    mov.l .Lstock_decode,r1
    jsr @r1
    nop
    add #4,r15
    mov r0,r10
    cmp/pz r0
    bf .Ldecode_failed
    mov r8,r4
    mov r9,r5
    mov.l .Lapply_or_trace_surfaces,r1
    jsr @r1
    nop
    bra .Ldecode_return
    nop
.Ldecode_failed:
    mov.l .Ldecode_invalidate,r1
    jsr @r1
    nop
.Ldecode_return:
    mov r10,r0
    add #24,r15
    lds.l @r15+,pr
    mov.l @r15+,r14
    mov.l @r15+,r13
    mov.l @r15+,r12
    mov.l @r15+,r11
    mov.l @r15+,r10
    mov.l @r15+,r9
    rts
    mov.l @r15+,r8

    .balign 4
.Lstock_decode:   .long 0x09304066
.Lapply_or_trace_surfaces: .long _xdj_beta_apply_or_trace_surfaces
.Ldecode_invalidate: .long _xdj_beta_invalidate
    .size xdj_beta_decode_hook,.-xdj_beta_decode_hook
