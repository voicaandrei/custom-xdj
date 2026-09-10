    .section .text.xdj_beta_hooks,"ax",@progbits
    .balign 4
    .global _xdj_beta_title_original
_xdj_beta_title_original:
    mov.l r8,@-r15
    mov.l r9,@-r15
    mov.l r10,@-r15
    mov.l r11,@-r15
    mov.l r12,@-r15
    mov.l r13,@-r15
    mov.l .Ltitle_resume,r1
    jmp @r1
    nop
    .balign 4
.Ltitle_resume: .long 0x0952c250
    .global _xdj_beta_note_original
_xdj_beta_note_original:
    mov.l r9,@-r15
    mov.l r10,@-r15
    mov.l r11,@-r15
    mov.l r12,@-r15
    mov.l r13,@-r15
    mov.l r14,@-r15
    mov.l .Lnote_resume,r1
    jmp @r1
    nop
    .balign 4
.Lnote_resume: .long 0x0952c028

    /* Final row serialization: row+17 is the current stock match flag.
     * It can change independently of the cached icon type at row+4. */
    .global xdj_beta_serialize_note
xdj_beta_serialize_note:
    sts.l pr,@-r15
    mov.l r4,@-r15
    mov.l r6,@-r15
    mov.l r7,@-r15
    mov r5,r4
    mov #17,r0
    mov.b @(r0,r14),r5
    mov.l .Ldecorate,r1
    jsr @r1
    nop
    mov r0,r5
    mov.l @r15+,r7
    mov.l @r15+,r6
    mov.l @r15+,r4
    lds.l @r15+,pr
    mov.l .Lserialize,r1
    jmp @r1
    nop
    .balign 4
.Ldecorate: .long _xdj_beta_key_note
.Lserialize: .long 0x092bd968
