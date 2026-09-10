    .section .text.xdj_beta_hooks,"ax",@progbits
    .balign 4
    .global xdj_beta_info_create_hook
xdj_beta_info_create_hook:
    mov.l .Lcreate,r1
    jmp @r1
    nop
    .balign 4
.Lcreate: .long _xdj_beta_info_create

    .global xdj_beta_info_access_hook
xdj_beta_info_access_hook:
    mov.l .Laccess,r1
    jmp @r1
    mov r9,r7
    .balign 4
.Laccess: .long _xdj_beta_info_access

    .global xdj_beta_info_fallback_hook
xdj_beta_info_fallback_hook:
    mov.l .Lfallback,r1
    jmp @r1
    mov r9,r5
    .balign 4
.Lfallback: .long _xdj_beta_info_fallback
