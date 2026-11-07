#ifdef NDEBUG
#error Assertions must be enabled
#endif
#include "reset_guard.c"
#include <assert.h>
extern int reset_guard_probe(void*);
static int stock_calls, skip_calls, hook_calls, throw_clear;
static int stock(void* value) { (void)value; ++stock_calls; return 17; }
static int skip(void* value) { (void)value; ++skip_calls; return 29; }
static void clear(void* value) {
    (void)value;
    assert(reset_guard_depth > 0 && reset_guard_thread == (LONG)GetCurrentThreadId());
    assert(reset_guard_probe(NULL) == 29);
    assert(reset_guard_probe((void*)0x1234) == 17);
    if (throw_clear) RaiseException(0xe0000002, 0, 0, NULL);
}
static int fail_hook(void* target, void* detour, void** original) {
    (void)target; (void)detour;
    ++hook_calls; *original = clear; return 1;
}
static int partial_hook(void* target, void* detour, void** original) {
    (void)target; (void)detour;
    ++hook_calls;
    *original = hook_calls == 1 ? (void*)clear : (void*)stock;
    return hook_calls == 1 ? 0 : 7;
}
static int null_hook(void* target, void* detour, void** original) {
    (void)target; (void)detour;
    ++hook_calls; *original = NULL; return 0;
}
static DWORD WINAPI foreign(void* unused) {
    (void)unused;
    assert(reset_guard_probe(NULL) == 17);
    return 0;
}
int main(void) {
    volatile int sentinel = 0;
    assert(++sentinel == 1);
    assert((DWORD)__readgsdword(0x48) == GetCurrentThreadId());
    assert(install_once(fail_hook, NULL, NULL, NULL) == -4);
    assert(install_once(fail_hook, NULL, NULL, NULL) == -4 && hook_calls == 1);
    reset_guard_original = stock; reset_guard_continue = skip;
    assert(reset_guard_probe(NULL) == 17); /* outside reset unchanged */
    assert(reset_guard_probe((void*)0x1234) == 17);
    reset_guard_depth = 1; reset_guard_thread = (LONG)GetCurrentThreadId();
    HANDLE thread = CreateThread(NULL, 0, foreign, NULL, 0, NULL);
    assert(thread && WaitForSingleObject(thread, 5000) == WAIT_OBJECT_0);
    CloseHandle(thread);
    reset_guard_depth = 0; reset_guard_thread = 0;
    clear_original = clear;
    clear_factions(NULL);
    assert(reset_guard_depth == 0 && reset_guard_thread == 0);
    assert(skip_calls == 1 && stock_calls == 4);
    assert(reset_guard_calls == 5 && reset_guard_nulls == 1);
    assert(clear_calls == 1 && foreign_clears == 0);
    throw_clear = 1;
    __try { clear_factions(NULL); assert(0); }
    __except (EXCEPTION_EXECUTE_HANDLER) {}
    assert(reset_guard_depth == 0 && reset_guard_thread == 0 && clear_calls == 2);
    attempted = installed = hook_calls = 0; /* test-only fresh installer */
    assert(install_once(partial_hook, NULL, NULL, NULL) == -4);
    assert(install_once(partial_hook, NULL, NULL, NULL) == -4 && hook_calls == 2);
    assert(clear_original == clear && reset_guard_original == (void*)stock);
    attempted = installed = hook_calls = 0;
    assert(install_once(null_hook, NULL, NULL, NULL) == -4);
    assert(install_once(null_hook, NULL, NULL, NULL) == -4 && hook_calls == 1);
    puts("reset guard assembly and fail-latch tests passed; assertions executed");
    return 0;
}
