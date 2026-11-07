"""Synthetic serializer/phase regressions; no game assets or engine calls."""

import importlib.util
import math
import struct
from pathlib import Path

import pytest

path = Path(__file__).parents[1] / "experiments/carry_phase/build_candidate.py"
spec = importlib.util.spec_from_file_location("carry_phase", path)
phase = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase)


def chunk(kind, payload):
    return struct.pack("<HI", kind, len(payload) + 6) + payload


def track(handle, amplitude=0.3):
    keys = []
    for i in range(5):
        t = i / 4
        angle = math.sin(t * math.tau) * amplitude
        keys.append(struct.pack("<HI8f", 0x4110, 38, t, 0, math.sin(angle / 2), 0,
                                math.cos(angle / 2), math.sin(t * math.tau), 0, 0))
    return chunk(0x4100, struct.pack("<H", handle) + b"".join(keys))


def animation(name):
    return chunk(0x4000, name.encode() + b"\n" + struct.pack("<f", 1)
                 + b"".join(track(h) for h in range(6)))


def skeleton():
    names = sorted(phase.TORSO) + [f"Unchanged bone {i}" for i in range(77)]
    bones = []
    for h, name in enumerate(names):
        bones.append(struct.pack("<HI", 0x2000, 36) + name.encode() + b"\n"
                     + struct.pack("<H7f", h, 0, 0, 0, 0, 0, 0, 1))
    return (b"\x00\x10[Serializer_v1.80]\n" + b"".join(bones)
            + chunk(0x3000, struct.pack("<HH", 1, 0))
            + b"".join(animation(n) for n in sorted(phase.TARGETS | {"jog carrying right"})))


def test_half_phase_preserves_loop_and_compensates_engine_offset():
    original = track(7)
    result = phase.shift_half(original, 1)
    keys = phase.read_keys(result)
    assert result[6:8] == original[6:8]
    assert keys[0][0] == 0 and keys[-1][0] == 1
    assert keys[0][1:] == keys[-1][1:]
    old_keys = phase.read_keys(original)
    for i in range(100):
        t = i / 100
        expected = phase.sample(old_keys, t)
        actual = phase.sample(keys, (t + 0.5) % 1)
        assert actual == pytest.approx(expected, abs=1e-6)


def test_patch_keeps_bind_right_carry_arms_and_other_chunks_byte_exact():
    original = skeleton()
    result, edited = phase.patch(original)
    assert edited == {name: 5 for name in phase.TARGETS}
    header, before = phase.roots(original)
    after_header, after = phase.roots(result)
    assert after_header == header and len(before) == len(after)
    changed = 0
    for (kind, raw), (new_kind, new) in zip(before, after, strict=True):
        assert kind == new_kind
        if raw == new:
            continue
        assert kind == 0x4000
        nl = raw.index(b"\n", 6)
        assert raw[6:nl].decode() in phase.TARGETS
        assert raw[6:nl + 5] == new[6:nl + 5]
        # The synthetic sixth track represents a held arm. It must stay exact.
        assert new.endswith(track(5))
        changed += 1
    assert changed == 2


@pytest.mark.parametrize("problem", ["open", "nonfinite", "nonunit", "unordered", "duration"])
def test_rejects_bad_track_before_writing(problem):
    raw = bytearray(track(0))
    duration = 1
    if problem == "open":
        struct.pack_into("<f", raw, 8 + 4 * 38 + 26, 123)
    elif problem == "nonfinite":
        struct.pack_into("<f", raw, 8 + 10, float("nan"))
    elif problem == "nonunit":
        struct.pack_into("<f", raw, 8 + 22, 3)
    elif problem == "unordered":
        struct.pack_into("<f", raw, 8 + 38 + 6, 0)
    elif problem == "duration":
        duration = 2
    with pytest.raises(ValueError):
        phase.shift_half(bytes(raw), duration)


def test_rejects_other_serializer_and_missing_target_alias():
    with pytest.raises(ValueError):
        phase.patch(skeleton().replace(b"[Serializer_v1.80]", b"[Serializer_v1.90]"))
    with pytest.raises(ValueError, match="Missing target"):
        phase.patch(skeleton().replace(b"jog carrying left-21", b"jog carrying left-22"))
