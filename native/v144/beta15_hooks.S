/* XDJ-1000MK2 MAIN 1.44 only, Test 15: validated row branches 1 and 2.
 *
 * xdj_beta_getimage_hook replaces the dbcl_GetImage literal inside
 * DbReqJpegData. It derives main track ID from the caller's already validated
 * 276-byte row, requests PWV4 synchronously on the same connection, prepares
 * project-owned pixels, releases that result, then calls stock GetImage.
 * Test 15 never issues a second preview request after an RGB failure.
 * Cancellation byte context+12 belongs to stock and is never cleared here.
 *
 * xdj_beta_decode_hook replaces the stock JPEG decoder literal. It calls the
 * decoder first, then overwrites the cache entry's A/B pixel buffers only when
 * a matching preparation completed immediately before this response.
 */
    /* FILE 0x128fbb0 sets context+12 on cancellation; DbReqJpegData
     * checks it at 0x12a4cdc. It is cleared by the task at 0x129c144.
     * Test 09 incorrectly started further transactions after this signal. */
    .macro CANCEL_GUARD target
    tst r13,r13
    bt 991f
    mov.b @(12,r13),r0
    tst r0,r0
    bf \target
991:
    .endm
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
    mov.l r0,@(28,r15)      /* preview cancellation scope, inactive */
    /* FILE 0x12a4b78 and 0x12a4c8e both publish a validated row at
     * caller SP+16 before the shared GetImage call. Branch 0 never does.
     * Locked stock MAIN SHA: 9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0.
     * Forwarded request +40 is zero and is NOT a track identifier. */
    mov.l .Lbeta_trace_reset,r1
    jsr @r1
    nop
    tst r13,r13
    bt .Lstock_image
    mov.l @r13,r0
    cmp/eq #1,r0
    bt .Lrow_context
    cmp/eq #2,r0
    bt .Lrow_context
    /* Explicit unsupported context: no speculative row dereference. */
    mov #11,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop
    bra .Lstock_image
    nop
.Lrow_context:
    mov #2,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop

    /* Caller locals start 64 bytes above our SP. Its +16 is the validated row. */
    mov #80,r0
    mov.l @(r0,r15),r8
    tst r8,r8
    bt .Lstock_image
    /* Require the same artwork identity already passed to stock GetImage. */
    mov.l @(8,r8),r0
    mov.l @(4,r15),r1
    cmp/eq r1,r0
    bf .Lstock_image
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

    CANCEL_GUARD .Lcancelled_image
    /* Non-consuming lookup in the stock cancellation registry. Unlike
     * 0x092be064, 0x09548738 does not remove the token. An obsolete request
     * goes directly to stock GetImage, which handles cancellation normally. */
    mov.b @(13,r13),r0
    tst r0,r0
    bt .Lpreview_not_obsolete
    mov #180-256,r0
    extu.b r0,r0
    mov.l @(r0,r13),r4
    mov.l .Lcancel_lookup,r1
    jsr @r1
    nop
    cmp/pz r0
    bt .Lstock_image
.Lpreview_not_obsolete:
    /* Stock WAVEFORM COLOR caller FILE 0x12b4442..0x12b4456:
     * connection[0] is source handle, connection+4 is media slot.
     * source+4 == 0 selects local player 0, else source+8 is player id.
     * connection+8 is database type and must NOT index the colour table.
     * See docs/diagnostic-09.md for stock SHA and address space. */
    mov.l @(0,r15),r1
    mov.l @r1,r6
    tst r6,r6
    bt .Ltry_blue
    mov #0,r4
    mov.l @(4,r1),r5
    mov.l @(4,r6),r2
    tst r2,r2
    bt .Lcolour_source_ready
    mov.l @(8,r6),r4
.Lcolour_source_ready:
    mov.l .Lcolour_getter,r1
    jsr @r1
    nop
    cmp/eq #3,r0
    bf .Ltry_blue

    mov #5,r4
    mov.l .Lbeta_trace,r1
    jsr @r1
    nop

    CANCEL_GUARD .Lcancelled_image
    mov r13,r4
    mov.l .Lpreview_enter,r1
    jsr @r1
    nop
    mov.l r0,@(28,r15)
    /* GetSpecifiedAtomInfo(connection, track, "PWV4", "EXT",
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
    mov r0,r12
    mov.b @(12,r13),r0
    tst r0,r0
    bf .Lrelease_rgb
    mov r12,r0
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
    /* Whether success, absence, malformed data, timeout or cancellation:
     * never chain another preview transaction. Preserve RGB preference. */
    bra .Lstock_image
    nop

    /* Blue is requested only for the Blue preference or missing source. */
.Ltry_blue:
    CANCEL_GUARD .Lcancelled_image
    mov r13,r4
    mov.l .Lpreview_enter,r1
    jsr @r1
    nop
    mov.l r0,@(28,r15)
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
    mov r0,r12
    mov.b @(12,r13),r0
    tst r0,r0
    bf .Lrelease_blue
    mov r12,r0
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
    mov r13,r4
    mov.l @(28,r15),r5
    mov.l .Lpreview_leave,r1
    jsr @r1
    nop
    mov #0,r0
    mov.l r0,@(28,r15)
    CANCEL_GUARD .Lcancelled_image
    mov.l @(0,r15),r4
    mov.l @(4,r15),r5
    mov.l @(8,r15),r6
    mov.l @(12,r15),r7
    mov.l .Lstock_get_image,r1
    jsr @r1
    nop
    mov r0,r14
    CANCEL_GUARD .Lstock_image_failed
    mov r14,r0
    cmp/pz r0
    bf .Lstock_image_failed
    tst r0,r0
    bf .Lstock_image_return
.Lstock_image_failed:
    mov.l .Lbeta_invalidate,r1
    jsr @r1
    nop
    bra .Lstock_image_return
    nop
.Lcancelled_image:
    /* Do not restart the source transaction (it clears cancellation state).
     * Return the stock GetImage failure contract; caller owns cancellation
     * cleanup and deliberately suppresses its obsolete JPEG response. */
    mov #0,r14
    mov.l @(8,r15),r1
    mov.l r14,@r1
    mov.l @(12,r15),r1
    mov.l r14,@r1
    mov.l .Lbeta_invalidate,r1
    jsr @r1
    nop
.Lstock_image_return:
    mov r14,r0             /* copy result BEFORE restoring caller r14 */
    add #32,r15
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
.Lpreview_enter: .long _xdj_beta_preview_enter
.Lpreview_leave: .long _xdj_beta_preview_leave
.Lcancel_lookup:   .long 0x09548738
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
