/* Exact-build reset-only null-result guard. Never edits objects or frees data. */
#include "../visibility_lifecycle/t60_attachment_compat_v083.c"
#include <intrin.h>

typedef int (*AddHook)(void*, void*, void**);
typedef void (*ClearFactions)(void*);
void* reset_guard_original;
void* reset_guard_continue;
volatile LONG64 reset_guard_calls, reset_guard_nulls;
volatile LONG reset_guard_thread, reset_guard_depth;
static ClearFactions clear_original;
static volatile LONG64 clear_calls, foreign_clears;
static int installed, attempted;
static SRWLOCK install_lock = SRWLOCK_INIT;
extern void reset_guard_midpoint(void);

static void clear_factions(void* self) {
    LONG tid = (LONG)GetCurrentThreadId();
    LONG owner = InterlockedCompareExchange(&reset_guard_thread, tid, 0);
    int ours = owner == 0 || owner == tid;
    InterlockedIncrement64(&clear_calls);
    if (ours) InterlockedIncrement(&reset_guard_depth);
    else InterlockedIncrement64(&foreign_clears);
    __try { clear_original(self); }
    __finally {
        if (ours && InterlockedDecrement(&reset_guard_depth) == 0)
            InterlockedExchange(&reset_guard_thread, 0);
    }
}

static int install_once(AddHook hook, void* midpoint, void* continuation, void* clear) {
    int result = -4;
    AcquireSRWLockExclusive(&install_lock);
    if (installed) result = 0;
    else if (!attempted) {
        attempted = 1; /* partial hook failure permanently latches */
        reset_guard_continue = continuation;
        int a = hook(clear, (void*)clear_factions, (void**)&clear_original);
        if (a == 0 && clear_original) {
            int b = hook(midpoint, (void*)reset_guard_midpoint, &reset_guard_original);
            if (b == 0 && reset_guard_original) { installed = 1; result = 0; }
        }
    }
    ReleaseSRWLockExclusive(&install_lock);
    return result;
}

API int T60_reset_guard_ready(void) {
    if (installed) return 0;
    if (bind() != 1) return -1;
    /* Assembly reads only this exact Windows x64 TEB thread-id field. */
    if ((DWORD)__readgsdword(0x48) != GetCurrentThreadId()) return -6;
    char* image = (char*)GetModuleHandleA(NULL);
    const unsigned char expected[] = {0x48,0x8d,0x88,0xd0,0x03,0,0,0x48,0x8b,0xd6,0xe8,0x07,0xf4,0x89,0xff};
    const unsigned char clear_bytes[] = {0x48,0x89,0x5c,0x24,0x20,0x55,0x56,0x57,0x48,0x83};
    if (memcmp(image + 0x7990db, expected, sizeof expected) ||
        memcmp(image + 0x8013c0, clear_bytes, sizeof clear_bytes)) return -2;
    HMODULE lib = GetModuleHandleA("KenshiLib.dll"), self;
    AddHook hook = (AddHook)(uintptr_t)GetProcAddress(lib,
        "?AddHook@KenshiLib@@YA?AW4HookStatus@1@PEAX0PEAPEAX@Z");
    if (!hook) return -3;
    if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
        (const char*)&T60_reset_guard_ready, &self)) return -3;
    return install_once(hook, image + 0x7990db, image + 0x7990ea, image + 0x8013c0);
}

API int T60_reset_guard_status(char* out, size_t capacity) {
    if (!out || capacity < 512) return -1;
    return snprintf(out, capacity,
        "{\"installed\":%d,\"checks\":%lld,\"null_skips\":%lld,\"faction_clears\":%lld,\"foreign_clears\":%lld,\"active_depth\":%ld}",
        installed, (long long)reset_guard_calls, (long long)reset_guard_nulls,
        (long long)clear_calls, (long long)foreign_clears, (long)reset_guard_depth);
}
