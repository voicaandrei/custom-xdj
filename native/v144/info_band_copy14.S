/* Replacement for FILE 0x152084c..0x152087d in the hash-locked reference.
 * Prior memset keeps its stock 27346-byte bound. Source cache B is 26208 bytes.
 * Copy only 288*28*2=16128 bytes, once, to the START of the destination.
 * No preview: decoder wrapper publishes a blank B, avoiding stretched artwork.
 */
    .text
    .word 0x016a /* sts fpscr,r1: preserve exact stock FPSCR handling */
    and r8,r1
    .word 0x416a /* lds r1,fpscr */
    mov.l @(52,r15),r4
    mov.l @(32,r15),r5
    mov.l @(44,r15),r2
    add r2,r5
    mov.l @r5,r5
    mov #63,r6
    shll8 r6
    add #0,r6
    mov.l .Lcopy,r1
    jsr @r1
    nop
    .word 0x016a
    and r8,r1
    .word 0x416a
    bra .Lend
    nop
    .balign 4
.Lcopy: .long 0x095a6570
    .org 50
.Lend:
