# T60 private material normal binding consistency

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
