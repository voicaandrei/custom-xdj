/* Candidate for MAIN application SHA256:
 * 9ca3a6bab97bb1d32a85ff740791f06b828e96cb4a1d3660a911bb72062f1db0.
 * Original literal FILE 0x152d21c = CODE POINTER 0x0935a2ec.
 * Inspected callers FILE 0x152d1d2 and 0x152d1dc, both same frame.
 * This assembly alone does not patch or install firmware.
 * Requires SH-4A little endian and the inspected stock frame.
 * Leaf probe: no stack use, no C call; tail-jumps to original release.
 */
    .section .text.xdj_v144_probe,"ax"
    .balign 4
    .global xdj_v144_probe_hook
    .type xdj_v144_probe_hook,@function
xdj_v144_probe_hook:
    mov r15,r3              /* unchanged original caller frame */
    mov.l .Lfirst_descriptor,r0
    cmp/eq r0,r9
    bf .Lrelease             /* all other cells retain stock drawing */
    mov.w @(12,r9),r0
    cmp/eq #80,r0
    bf .Lrelease
    mov.w @(16,r9),r0
    cmp/eq #28,r0
    bf .Lrelease
    mov #68,r0
    mov.l @(r0,r3),r4         /* acquired pixel pointer */
    tst r4,r4
    bt .Lrelease             /* stock null-buffer path also uses this hook */
    mov #64,r0
    mov.l @(r0,r3),r6         /* now WORD pitch on the non-null path */
    mov #80,r0
    cmp/eq r0,r6
    bf .Lrelease             /* no guessing capacity of other surface layouts */
    mov r4,r0
    tst #1,r0
    bf .Lrelease
    mov #35,r5
    shll2 r5
    shll2 r5
    shll2 r5                 /* exactly 2240 words */
    mov #-8,r0
    shll8 r0                 /* 0xf800 in low 16 bits: RGB red / BGR blue */
.Lfill:
    mov.w r0,@r4
    add #2,r4
    dt r5
    bf .Lfill
.Lrelease:
    mov.l .Lstock_release,r0
    jmp @r0                  /* retain caller PR; no extra release frame */
    mov.l @r9,r4             /* original delay-slot argument */
    .balign 4
.Lfirst_descriptor:
    .long 0x13bca44c          /* literal DATA pointer, not a file offset */
.Lstock_release:
    .long 0x0935a2ec          /* original CODE pointer */
    .size xdj_v144_probe_hook,.-xdj_v144_probe_hook
