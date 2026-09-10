    .section .text.xdj_beta_hooks,"ax",@progbits
    .balign 4
    .global xdj_beta_key_note_hook
xdj_beta_key_note_hook:
    mov.l r8,@-r15
    sts.l pr,@-r15
    mov r6,r8
    mov.l .Loriginal,r1
    jsr @r1
    nop
    mov r0,r4
    mov #38,r0
    mov.b @(r0,r8),r5
    mov.l .Ldecorate,r1
    jsr @r1
    nop
    lds.l @r15+,pr
    rts
    mov.l @r15+,r8
    .balign 4
.Loriginal: .long xdj_beta_key_note_original
.Ldecorate: .long _xdj_beta_key_note

    .global xdj_beta_key_note_original
xdj_beta_key_note_original:
    /* Replay precisely the six overwritten stock pushes, then resume stock.
     * FILE 0x12b92a6..0x12b92b1; stock SHA fixed by builder and independent audit.
     */
    mov.l r8,@-r15
    mov.l r9,@-r15
    mov.l r10,@-r15
    mov.l r11,@-r15
    mov.l r12,@-r15
    mov.l r13,@-r15
    mov.l .Lresume,r1
    jmp @r1
    nop
    .balign 4
.Lresume: .long 0x092b92b2
