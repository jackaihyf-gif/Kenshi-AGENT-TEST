.text
.globl reset_guard_midpoint
reset_guard_midpoint:
    lock incq reset_guard_calls(%rip)
    testq %rax, %rax
    jnz .Lstock
    cmpl $0, reset_guard_depth(%rip)
    jle .Lstock
    movl %gs:0x48, %r11d
    cmpl reset_guard_thread(%rip), %r11d
    jne .Lstock
    lock incq reset_guard_nulls(%rip)
    jmp *reset_guard_continue(%rip)
.Lstock:
    jmp *reset_guard_original(%rip)

#ifdef RESET_GUARD_TEST
.globl reset_guard_probe
reset_guard_probe:
    movq %rcx, %rax
    jmp reset_guard_midpoint
#endif
