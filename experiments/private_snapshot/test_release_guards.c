/* Reuse only the synthetic fixture, never its reset-based scenario runner. */
#define main previous_release_tests
#include "test_release.c"
#undef main

static int allocationMode, constructorCalls, readerMode, pairAliasMode;
static char names[3][64], sharedName[64];
static void *fault_alloc(size_t n) {
    if (allocationMode == 1) return NULL;
    if (allocationMode == 2 && ai == 1) return NULL;
    return allocate(n);
}
static void *counted_ctor(void *p) { constructorCalls++; return construct(p); }
static unsigned char guarded_copy(void *d, const void *s, unsigned char flag) {
    if (readerMode) slots[0].readers = 1;
    unsigned char ok = copy(d, s, flag);
    if (pairAliasMode) {
        NativeString *id = (void *)((char *)d + 0x28);
        const NativeString *sourceId = (const void *)((const char *)s + 0x28);
        char *buffer = slots[0].state == 4 ? sharedName : names[d == objs[1] ? 1 : 2];
        /* Memmove also permits a repeated clear/copy into the same fake backing. */
        memmove(buffer, sourceId->storage.data, (size_t)sourceId->length + 1);
        id->storage.data = buffer;
    }
    return ok;
}
static void setup(void) {
    init(objs[0], 0);
    *(void **)(app + 0xf0) = &character;
    *(void **)(app + 0x148) = objs[0];
    gui = GetCurrentThreadId(); ready = completeReady = 1;
    allocfn = fault_alloc; ctor = counted_ctor; update = guarded_copy; epochfn = ep;
    boolIndex = indexer; boolErase = eraser; refList = reflist; clearData = clear;
    privateDeleter = fakeDelete;
}
int main(int argc, char **argv) {
    assert(argc == 2);
    setup();
    unsigned long long out[9], stats[9];
    if (!strcmp(argv[1], "budget")) {
        objectAttempts = 15;
        assert(T60_private_release_trial(app, &character, objs[0], epoch, 1, out, 9) == -4);
        assert(next_id == 0 && attempts == 0 && ai == 0 && objectAttempts == 15);
    } else if (!strcmp(argv[1], "alloc-null")) {
        allocationMode = 1;
        assert(T60_private_release_trial(app, &character, objs[0], epoch, 1, out, 9) == -5);
        assert(objects == 0 && privateCreated == 0 && privateRetained == 0);
        assert(objectAttempts == 1 && constructorCalls == 0 && deleteCalls == 0);
        assert(releaseStopped);
    } else if (!strcmp(argv[1], "scratch-null")) {
        allocationMode = 2;
        assert(T60_private_release_trial(app, &character, objs[0], epoch, 1, out, 9) == -5);
        assert(objects == 1 && privateCreated == 1 && privateRetained == 1);
        assert(objectAttempts == 2 && deleteCalls == 0 && releaseStopped);
    } else if (!strcmp(argv[1], "readers")) {
        readerMode = 1;
        assert(T60_private_release_trial(app, &character, objs[0], epoch, 1, out, 9) == -20);
        assert(deleteCalls == 0 && privateRetained == 2 && releaseStopped);
    } else if (!strcmp(argv[1], "pair-alias")) {
        pairAliasMode = 1;
        strcpy(names[0], "synthetic_long_object_identifier");
        NativeString *id = (void *)(objs[0] + 0x28);
        id->storage.data = names[0]; id->length = strlen(names[0]); id->capacity = 63;
        assert(T60_private_release_trial(app, &character, objs[0], epoch, 1, out, 9) == -26);
        assert(deleteCalls == 0 && privateRetained == 2 && releaseStopped);
        assert(!strcmp(names[0], "synthetic_long_object_identifier"));
    } else if (!strcmp(argv[1], "exception-stop")) {
        deleteMode = 2;
        assert(T60_private_release_trial(app, &character, objs[0], epoch, 1, out, 9) == -24);
        assert(deleteCalls == 2 && privateDeleted == 1 && privateRetained == 1);
        assert(releaseStopped && !trialBusy);
        unsigned long long oldId = next_id;
        epoch++; /* A different epoch must not bypass a prior destructor failure. */
        assert(T60_private_release_trial(app, &character, objs[0], epoch, 1, out, 9) == -25);
        assert(deleteCalls == 2 && next_id == oldId && privateQuarantine == 1);
    } else { assert(!"unknown synthetic case"); }
    assert(!T60_private_release_stats(stats, 9));
    assert(privateCreated == privateDeleted + privateRetained);
    assert(objects == privateRetained && !trialBusy);
    assert(*(void **)(app + 0x148) == objs[0]);
    printf("private release guard passed: %s (synthetic only)\n", argv[1]);
    return 0;
}
