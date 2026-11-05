/* Synthetic keys and deterministic time only. Never attaches to the game. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
static ULONGLONG simulated_time;
static ULONGLONG fake_clock(void) { return simulated_time; }
#define GetTickCount64 fake_clock
#include "baseline_filter_core.h"
#undef GetTickCount64
#include <assert.h>
#include <stdio.h>
#ifdef NDEBUG
#error "Assertions must be enabled; this test must execute checked expressions."
#endif
static int queue_calls, set_calls, last_show;
static void queued(void* entity,void* queue,void* camera,const void* lod) {
    (void)entity;(void)queue;(void)camera;(void)lod;queue_calls++;
}
static void shown(void* entity,unsigned char show) {
    (void)entity;set_calls++;last_show=show;
}
int main(void) {
    queue_update=queued;visible_set=shown;
    void* clothes=(void*)(uintptr_t)0x100010;
    void* replacement=(void*)(uintptr_t)0x100020;
    void* sword=(void*)(uintptr_t)0x100030;
    void* gun=(void*)(uintptr_t)0x100040;
    Record* r=&records[0];r->appearance=(void*)(uintptr_t)0x900000;
    r->count=3;r->snaps[0]=(Snap){NULL,clothes,0,1};
    r->snaps[1]=(Snap){NULL,sword,2,1};r->snaps[2]=(Snap){NULL,gun,107,1};
    simulated_time=1000;cache_filter(r,0);
    assert(suppressed(clothes));assert(!suppressed(sword));assert(!suppressed(gun));
    filtered_visible(clothes,1);assert(last_show==0&&set_calls==1);
    filtered_queue(clothes,NULL,NULL,NULL);assert(queue_calls==0);
    /* Replacement equipment is unregistered even before any expiry. */
    assert(!suppressed(replacement));
    filtered_visible(replacement,1);assert(last_show==1);
    filtered_queue(replacement,NULL,NULL,NULL);assert(queue_calls==1);
    /* A GUI dispatch gap reaches the exact existing two-second boundary. */
    simulated_time=2999;assert(suppressed(clothes));
    simulated_time=3000;assert(!suppressed(clothes));
    filtered_visible(clothes,1);assert(last_show==1);
    filtered_queue(clothes,NULL,NULL,NULL);assert(queue_calls==2);
    /* Re-registration reproduces recovery after the next stable scan. */
    r->snaps[0].entity=replacement;cache_filter(r,0);
    assert(suppressed(replacement));assert(!suppressed(clothes));
    filtered_visible(replacement,1);assert(last_show==0);
    filtered_queue(replacement,NULL,NULL,NULL);assert(queue_calls==2);
    assert(!suppressed(sword));assert(!suppressed(gun));
    cache_filter(r,1);assert(!suppressed(replacement));
    puts("{\"synthetic_only\":true,\"assertions_enabled\":true,\"ttl_gap_reproduced\":true,\"new_entity_gap_reproduced\":true,\"stable_scan_recovery\":true,\"weapon_categories_preserved\":true,\"live_fix_verified\":false}");
    return 0;
}
