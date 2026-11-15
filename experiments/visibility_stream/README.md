# Loading visibility regression fixture

This is an offline reproduction of two existing filter gaps, not a fix or a live-game acceptance test. It does not load a DLL, attach to Kenshi, read memory or dereference any synthetic entity/appearance key. The player's game remains untouched. No game installation is required to run it on Windows.

`baseline/` contains the authored source captured from the installed version and its existing indexed build source; see `source-provenance.json` for SHA-256. The live DLL and archived built DLL both hash to `4b3ed988f6ba8f24e78b047c8f31cb8a2c70e7744169301fee09a37240842735`. This establishes the archived build matches the installed binary, not a fresh reproducible build of all dependencies.

The full baseline C file is reference material; do not compile/load it into a game. `extract_filter_core.py` verifies the baseline SHA and extracts verbatim filter structs, membership, expiry, queue and visibility logic into `baseline_filter_core.h`. It omits all engine address binding, setup/hooks, appearance traversal and exported native operations. The test redirects only the clock and renderer to deterministic stubs. The generated header is tracked so reviewers can inspect precisely what executes.

From this directory, using Python 3 and a Windows C compiler:

```powershell
python extract_filter_core.py
zig cc -std=c11 -O1 -UNDEBUG test_loading_gap.c -o "$env:TEMP/kenshi-loading-gap-test.exe"
& "$env:TEMP/kenshi-loading-gap-test.exe"
```

Assertions are required. `NDEBUG` causes a compile-time error. Test steps:

1. At simulated time1000ms, register clothing and both weapon categories2/107. Clothing is blocked; weapons remain eligible for rendering.
2. A replacement clothing key is unregistered and reaches the renderer even while the old key's lease remains valid.
3. The registered old key is suppressed at2999ms, then passes both show and queue paths at3000ms: exactly the2000ms lease boundary.
4. A simulated later stable scan registers the replacement, after which it is hidden again. Removing its filter restores rendering eligibility.

`synthetic-result.json` records the successful execution of these assertions. Success means the old gaps were reproduced; it does not mean the product is fixed. No claim that an arbitrary unregistered pointer is really clothing in a game is made; the fixture's category/ownership is explicitly assigned by the test.

Fixes must also cover owner/epoch invalidation, entity destruction/address reuse, load/unload and first-draw ordering. The existing two-second expiry cannot simply be removed or extended; it limits stale-address suppression and extending it cannot register new entities. Do not remove identity/loading gates or use the global attachment flag without proving weapons remain unaffected. The analysis machine should work on an independent fix branch and supply a precise SHA. This fixture currently reproduces known gaps and does not implement that lifecycle protocol.
