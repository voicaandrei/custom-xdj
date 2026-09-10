/* XDJ-1000MK2 MAIN 1.44 only, Test 07.
 *
 * The stock artwork request already carries the normalized eight-byte row
 * identity at +36/+40.  The second word is the numeric row/track id.  Test 06
 * incorrectly attempted to recover it from a context-type-1-only row table.
 *
 * Reuse the fully audited Test 06 implementation behind a narrow adapter:
 * provide its context guard and caller-row slot from request +40.  The stock
 * connection and all four GetImage arguments remain unchanged.
 */
#define xdj_beta_getimage_hook xdj_beta_getimage_hook06
#include "beta06_hooks.S"
#undef xdj_beta_getimage_hook

    .section .text.xdj_beta_hooks,"ax"
    .balign 4
    .global xdj_beta_getimage_hook
    .type xdj_beta_getimage_hook,@function
xdj_beta_getimage_hook:
    mov.l r8,@-r15
    mov.l r13,@-r15
    sts.l pr,@-r15
    add #-20,r15
    mov r15,r8
    add #4,r8
    mov #1,r0
    mov.l r0,@r15             /* synthetic accepted context type */
    mov.l @(40,r11),r0        /* normalized identifier word 2: numeric ID */
    mov.l r0,@(4,r15)         /* synthetic row +0: main track ID */
    mov.l r8,@(16,r15)        /* Test 06 caller local +16: row pointer */
    mov r15,r13
    mov.l .Lbeta06_getimage,r1
    jsr @r1
    nop
    mov r0,r8
    add #20,r15
    lds.l @r15+,pr
    mov.l @r15+,r13
    mov r8,r0
    rts
    mov.l @r15+,r8

    .balign 4
.Lbeta06_getimage: .long xdj_beta_getimage_hook06
    .size xdj_beta_getimage_hook,.-xdj_beta_getimage_hook
