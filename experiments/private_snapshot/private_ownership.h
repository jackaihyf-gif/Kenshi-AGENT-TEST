#ifndef T60_PRIVATE_OWNERSHIP_H
#define T60_PRIVATE_OWNERSHIP_H

/* Rejection is conservative. This does not prove ownership of the entire graph.
 * NativeString is the already ABI-gated layout used by these research sources. */
static int private_ranges_disjoint(const void *a, size_t an,
                                   const void *b, size_t bn) {
    uintptr_t ap = (uintptr_t)a, bp = (uintptr_t)b;
    if (!a || !b || !an || !bn || an > UINTPTR_MAX - ap || bn > UINTPTR_MAX - bp)
        return 0;
    return ap + an <= bp || bp + bn <= ap;
}

static int private_id_independent(void *a, void *b) {
    if (!private_ranges_disjoint(a, 0x300, b, 0x300)) return 0;
    NativeString *x = (void *)((char *)a + 0x28);
    NativeString *y = (void *)((char *)b + 0x28);
    if (x->length > x->capacity || y->length > y->capacity ||
        x->length > 4096 || y->length > 4096) return 0;
    /* Bound capacity as well as length; overflow must never authorize deletion. */
    if (x->capacity > 1048576 || y->capacity > 1048576) return 0;
    const void *xp = x->capacity < 16 ? x->storage.small : x->storage.data;
    const void *yp = y->capacity < 16 ? y->storage.small : y->storage.data;
    size_t xn = x->capacity < 16 ? 16 : (size_t)x->capacity + 1;
    size_t yn = y->capacity < 16 ? 16 : (size_t)y->capacity + 1;
    if (!private_ranges_disjoint(xp, xn, yp, yn)) return 0;
    if (x->capacity >= 16 &&
        (!private_ranges_disjoint(xp, xn, a, 0x300) ||
         !private_ranges_disjoint(xp, xn, b, 0x300))) return 0;
    if (y->capacity >= 16 &&
        (!private_ranges_disjoint(yp, yn, a, 0x300) ||
         !private_ranges_disjoint(yp, yn, b, 0x300))) return 0;
    return 1;
}
#endif
