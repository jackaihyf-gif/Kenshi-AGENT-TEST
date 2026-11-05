# Attachment lifecycle visibility candidate

User-authorized local fix, installed and tested in one isolated cold game session on 2026-11-05. Full zone streaming and first-frame visual acceptance remain unverified. The installed artifact, source and tested instrument commit are recorded in provenance.json and ../../docs/handoffs/local-fixes-20261105.md.

The old 2000ms render-filter lease is replaced by native attachment registration and destruction invalidation. AppearanceBase::attachEntity registers and hides non-weapon entities before the engine attaches them to a scene node; this includes its asynchronous createEntityCallback path. Native setVisible requests update saved intent while filtering rendering. Entity destruction removes all indexed references, including inactive restoration records; AppearanceBase destruction and world forget retire records. A monotonic serial rejects stale collected entries after address reuse. Serials do not pin object lifetime.

Rendering uses the bounded hash index. Unrelated visibility/destruction calls take a shared lookup fast path; unrelated appearance destruction checks at most16 owners. Index rebuilding occurs on relevant membership changes, not every unrelated destructor or repeated attach. Existing16-owner/128-attachment bounds remain. Overflow latches a fault reported by tick, and setup failure latches without reinstall attempts. Setup validates the exact executable, target addresses and prologues before installing hooks and pins the module. No callback calls Lua.

The native method's live receiver/argument contract protects operations inside attach; existing GUI/epoch/body-stability admission protects collection and restoration. These are explicitly required engine contracts, not claims that a serial or snapshot is a lifetime lock. Do not call exported operations on arbitrary addresses or from a worker. Do not load old and new hooking DLLs together; only replace the existing DLL in a cold process.

Build on the validated Windows AMD64 toolchain:

```powershell
zig cc -std=c11 -fms-extensions -O1 -shared visibility_lifecycle.c -ladvapi32 -o "$env:TEMP/T60VisibilityCandidate.dll"
zig cc -std=c11 -fms-extensions -O1 -UNDEBUG test_visibility_lifecycle.c -ladvapi32 -o "$env:TEMP/T60VisibilityTest.exe"
& "$env:TEMP/T60VisibilityTest.exe"
```

The test uses synthetic objects and stubs; it never attaches to a game. `NDEBUG` is a compile-time error. Earlier subagent test output without explicit -UNDEBUG was invalid and was superseded by assertion-enabled runs. Assertions cover attach/intent, weapons, >2s persistence, destruction/address reuse, unrelated fast paths, duplicate attach, two owners, inactive destruction, destruction during end, and epoch forget. Source checkout normalization and debug build paths may change DLL hashes; record the artifact actually tested.

Live evidence: five clothing/backpack entities remain filtered after each of two native reloads; both weapon categories2/107 remain visible. Registrations/unregistrations progress11/6→16/11→21/16→21/21 after unequip, faults0 and no unregistered clothing while armored. Original eight entity categories/visibility and nine actor fields restore. This does not prove a real zone unload/return, every race or a long-running session. The bounded status formatter returns an error on insufficient output space rather than overflowing.

2026-11-05质量审计补记：生产visibility_lifecycle.c与已安装DLL未改；测试文件新增volatile断言sentinel，由build_offline.py验证-DNDEBUG编译拒绝并执行全部合成场景，已接Windows CI。旧provenance.json保留原历史测试哈希，新测试哈希以各次合成results.json为准，不能把旧记录当新测试字节校验。
