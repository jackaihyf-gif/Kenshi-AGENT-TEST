# T60 private material normal binding consistency

## 2026-11-07 isolated-normal candidate, not deployed

The v1 periodic repair produced a new user-visible flicker: normal play alternated
between repaired and race-skin appearance, while pausing stabilized it. The live
v1 bridge had five retained slots and 364 cumulative repairs. A short paused
capture kept the dedicated texture throughout; it did not capture alternating
phases. The engine/mod write competition remains the working explanation.

Local exact-build analysis found `normalMap` lookups through the public
`Pass::getTextureUnitState(name)` API, with a downstream null-unit guard in a
shared update helper. Raw executable snippets are not distributed. This supports
testing semantic isolation but does not prove every live update path is covered.

This candidate gives only the cloned normal unit a private name, preserving its
index 1, unit count/order, texture, and HLSL explicit `register(s1)`. It uses the
already ABI-exercised public `TextureUnitState::setName` method. Original material
and ordinary races are untouched. Stable ticks check the private unit without
writing. Unexpected private-name/texture/index drift disables the candidate;
it is not repaired periodically. No extra unit, shader change, poller, clone,
compilation, capacity increase or counter reset is introduced.

Cold-only DLL: `T60MaterialBridge_v091_isolatednormal_20261107.dll`. Native binding
rejects both previously deployed bridges. The paired loader retains either
already-loaded original or v1 bridge on file-watch reload, selecting isolation
only in a cold process. No live installation is allowed.

Actual-C synthetic tests include initial unit name/texture readback, 1000 simulated
name-based human/Shek updates without additional writes/clone/compile/growth,
stable day/night, both prior-bridge guards and unexpected drift failing closed.
These tests are not live game acceptance. A bounded independent cold session must
verify real updates, private bindings, stable appearance and no unexpected drift
before replacing a player's active version. The carry skeleton remains rolled
back to its original hash; this candidate does not alter skeleton/cache gates.

--- The remainder documents the v1 investigation and historical periodic repair. ---

An authorized read-only capture of two live bodies found the same T60 mesh, diffuse
map and private day shader, but `normalMap` had become `human_male_n.dds` and
`bone_male_n.dds`. Each current material still matched its owner's retained private
material pointer. The former pointer-only fast path returned without checking the
texture. The original setter had selected `t60_eye_emission_n_v091.dds`.

The candidate checks the private main pass and normal unit on the existing GUI
material tick. It rebinds the dedicated normal only on drift and verifies the
result. It does not clone/copy materials, compile/load shaders, add a poller, alter
the original material, or refund/grow the 32-slot pool. Thread, target body, single
submesh, executable/Ogre ABI and owner/female gates remain. Unsupported shader
state, duplicate/missing unit or failed readback disables the candidate through the
existing fail-safe path. Unit/technique/pass traversal has explicit bounds.

The source capsule starts from the author's v091 bridge SHA256
`315e7673c38c8c65175ef1abf6476ab017c18f41fac15f112844a93759ce2496`.
The installed original DLL was SHA256
`39438e348e7a419c1400d904e6d103b29d70b00709ce642e41a68b95ff15a563`.
`t60_ogre_symbols.h` contains public export names and the already verified hash,
not game headers or binaries. No game resources are included here.

```powershell
python experiments/material_binding/build_offline.py --compiler <zig.exe> --out <new-mock-directory>
python experiments/material_binding/build_local.py --compiler <zig.exe> --out <new-build-directory>
```

The first command compiles actual bridge source against synthetic API callbacks,
runs assertion/sentinel cases and requires a `-DNDEBUG` compile failure. Windows CI
executes it without loading Ogre or a game. The second only builds a DLL and source
hash manifest, without installing or launching. Full repository gates are required
before installation; a passing Mock is not live render acceptance.

Cold-start DLL name: `T60MaterialBridge_v091_bindingfix_20261106.dll`.
Use the paired `material_native.lua`; preserve the original loader/DLL for rollback.
The candidate refuses binding if the original v091 DLL is already loaded in the
same process, preventing a hot replacement of its retained pool/resource group.
Do not overwrite loaded DLLs or inject into a player session.

KenshiLua watches Lua files and may reload this loader even when the game remains
open. The loader must therefore select the original DLL before `ffi.load` when
that module is already present. This retains the active bridge and its night-state
global; the cached diagnostic reports `restart_required` instead of calling a new
ABI on the original library. A cold process selects the candidate. A real LuaJIT
synthetic regression covers repeated watch reloads and cold selection.

The first installation exposed this watch behavior: the new DLL was mapped but
its native cold guard kept it unbound, disabled, with zero slots. The original
bridge remained active. The corrected loader restores globals to that original
bridge; it does not unload either module or claim the running process was updated.

Read-only cached diagnostic interface:

- native `T60_material_binding_status(char*, size_t)` requires a buffer >=256 bytes;
  returns JSON `checks`, `repairs`, `slots`, `limit`, `enabled`.
- Lua `_G.JACK_T60_MATERIAL_BINDING_STATUS()` returns that cached JSON, without
  looking up characters or modifying engine state. It is not a generic RPC action.

After a normal cold start, compare actual body bindings on both supported races,
then after the loading/body/appearance transitions. Expected normal remains
`t60_eye_emission_n_v091.dds`, private day/night FP is retained, no normal write on
an already-correct binding, no slot/clone growth. Also measure whether the engine
overwrites it repeatedly; the candidate has not proven the frequency or exact
upstream write site. Roll back or refine rather than claim success if rendering
still flickers or repairs run continuously.
