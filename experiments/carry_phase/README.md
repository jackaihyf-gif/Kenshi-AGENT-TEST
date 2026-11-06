# T60 left-carry torso phase correction

The user's live left-carry jog enabled `jog carrying left-21` at about .95 weight
and `jog lower-11` at about 1.0. Eight read-only samples retained a half-cycle
offset. The current FCS left-carry record has `synch offset=.5`; ordinary jog and
right carry use zero. Existing left-carry spine/neck/head tracks are byte-identical
to the new coherent ordinary jog upper tracks, which compensate the lower body at
zero offset. The old left-specific offset was not accounted for during adaptation.

Offline forward kinematics of the installed 82-bone asset, 120 samples per cycle,
reproduced the excessive torso motion: Spine2 angular peak-to-peak 54.15 degrees
with the current half offset, versus 21.23 at zero. Head range was 40.35 versus
11.49 degrees. These are authored-skeleton calculations, not live renderer or
visual acceptance; runtime blend masks and the remaining small walk contribution
are not fully reconstructed. A later live sample had returned to idle.

The candidate shifts only five torso/head tracks by half a cycle in the T60-owned
`jog carrying left` and its `-21` alias. The unchanged engine offset then aligns
them with the lower body. Support-arm, hand, weapon/socket, pauldron, lower-body,
right-carry, pickup, carried-person and other animation tracks remain byte exact.
Bind hierarchy and durations stay exact. No global FCS animation record, ordinary
race asset, DLL, script tick, resource budget or movement speed changes.

```powershell
python experiments/carry_phase/build_candidate.py --input <local-author-skeleton> --expected-sha256 <verified-hash> --output <new-local-candidate.skeleton>
```

The builder is offline, refuses an unexpected hash/layout, missing aliases,
nonfinite/nonunit/unordered keys or open loops, and never installs or talks to the
game. Synthetic tests cover phase compensation, exact unaffected bytes and
rejections. No skeleton or game asset is shared in this repository. Full repository
gates and exact-head CI must pass before any backed-up cold-start installation.
The player explicitly deferred restarting; do not hot reload assets or control
their character. Live corrected carrying motion remains unverified until the
next normal cold start and user observation.
