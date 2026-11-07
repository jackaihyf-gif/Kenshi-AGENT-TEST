/* Synthetic data only: content equality does not establish private ownership. */
#include "private_snapshot_complete.c"
#undef NDEBUG
#include <assert.h>

int main(void) {
    unsigned char source[0x300] = {0}, copy[0x300] = {0};
    char shared[64] = "synthetic_long_object_identifier";
    char independent[64];
    memcpy(independent, shared, sizeof shared);
    *(unsigned *)(source + 0x50) = *(unsigned *)(copy + 0x50) = 66;
    NativeString *a = (void *)(source + 0x28), *b = (void *)(copy + 0x28);
    a->length = b->length = strlen(shared);
    a->capacity = b->capacity = 63;
    a->storage.data = b->storage.data = shared;
    assert(!same_content_shape(source, copy));
    b->storage.data = independent;
    assert(same_content_shape(source, copy));
    assert(!same_content_shape(source, source));
    puts("object ID ownership regression passed (synthetic only)");
    return 0;
}
