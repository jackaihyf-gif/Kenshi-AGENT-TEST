"""Offline, hash-bound phase correction for the authored T60 skeleton only."""

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

TARGETS = {"jog carrying left", "jog carrying left-21"}
TORSO = {"Bip01 Spine", "Bip01 Spine1", "Bip01 Spine2", "Bip01 Neck", "Bip01 Head"}


def roots(data):
    if not data.startswith(b"\x00\x10[Serializer_v1.80]\n"):
        raise ValueError("Unsupported skeleton serializer")
    cursor = data.index(b"\n", 2) + 1
    header = data[:cursor]
    rows = []
    while cursor < len(data):
        tag, size = struct.unpack_from("<HI", data, cursor)
        if size < 6:
            raise ValueError("Invalid chunk size")
        end = cursor + size
        if tag == 0x2000:
            if size not in (36, 48):
                raise ValueError("Unsupported bone layout")
            end += data.index(b"\n", cursor + 6) + 1 - (cursor + 6)
        elif tag not in (0x1010, 0x3000, 0x4000):
            raise ValueError("Unsupported chunk")
        if end > len(data):
            raise ValueError("Truncated chunk")
        rows.append((tag, data[cursor:end]))
        cursor = end
    return header, rows


def read_keys(track):
    keys = []
    cursor = 8
    while cursor < len(track):
        tag, size = struct.unpack_from("<HI", track, cursor)
        if tag != 0x4110 or size != 38 or cursor + size > len(track):
            raise ValueError("Unsupported keyframe layout")
        values = struct.unpack_from("<8f", track, cursor + 6)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("Nonfinite key")
        if abs(sum(v * v for v in values[1:5]) - 1) > 1e-4:
            raise ValueError("Nonunit rotation")
        if keys and values[0] <= keys[-1][0]:
            raise ValueError("Unordered key times")
        keys.append(values)
        cursor += size
    if len(keys) < 2:
        raise ValueError("Insufficient keys")
    return keys


def sample(keys, time):
    for left, right in zip(keys, keys[1:], strict=False):
        if left[0] <= time <= right[0]:
            u = (time - left[0]) / (right[0] - left[0])
            sign = 1 if sum(a * b for a, b in zip(left[1:5], right[1:5], strict=True)) >= 0 else -1
            q = [a * (1 - u) + b * u * sign
                 for a, b in zip(left[1:5], right[1:5], strict=True)]
            norm = math.sqrt(sum(v * v for v in q))
            if norm < 1e-8:
                raise ValueError("Degenerate interpolation")
            p = [a * (1 - u) + b * u for a, b in zip(left[5:], right[5:], strict=True)]
            return [v / norm for v in q] + p
    raise ValueError("Time outside track")


def shift_half(track, duration):
    keys = read_keys(track)
    if duration <= 0 or abs(keys[0][0]) > 1e-7 or abs(keys[-1][0] - duration) > 1e-6:
        raise ValueError("Track does not cover loop")
    first, last = keys[0], keys[-1]
    dot = abs(sum(a * b for a, b in zip(first[1:5], last[1:5], strict=True)))
    if dot < 1 - 1e-5 or max(abs(a - b) for a, b in zip(first[5:], last[5:], strict=True)) > 1e-5:
        raise ValueError("Open animation loop")
    half = duration / 2
    seam = sample(keys, half)
    shifted = [(0.0, *seam), (duration, *seam)]
    for key in keys[:-1]:
        time = (key[0] - half) % duration
        if 1e-7 < time < duration - 1e-7:
            shifted.append((time, *key[1:]))
    shifted.sort()
    payload = track[6:8] + b"".join(struct.pack("<HI8f", 0x4110, 38, *k) for k in shifted)
    result = struct.pack("<HI", 0x4100, len(payload) + 6) + payload
    read_keys(result)
    return result


def patch(data):
    header, rows = roots(data)
    bones = {}
    for tag, raw in rows:
        if tag == 0x2000:
            nl = raw.index(b"\n", 6)
            bones[raw[6:nl].decode()] = struct.unpack_from("<H", raw, nl + 1)[0]
    if len(bones) != 82 or not TORSO <= bones.keys():
        raise ValueError("Not the supported 82-bone T60 skeleton")
    handles = {bones[name] for name in TORSO}
    edited = {}
    output = [header]
    for tag, raw in rows:
        if tag != 0x4000:
            output.append(raw)
            continue
        nl = raw.index(b"\n", 6)
        name = raw[6:nl].decode()
        if name not in TARGETS:
            output.append(raw)
            continue
        duration = struct.unpack_from("<f", raw, nl + 1)[0]
        if not math.isfinite(duration):
            raise ValueError("Nonfinite duration")
        cursor = nl + 5
        children = []
        found = set()
        while cursor < len(raw):
            kind, size = struct.unpack_from("<HI", raw, cursor)
            if kind not in (0x4010, 0x4100) or size < 6 or cursor + size > len(raw):
                raise ValueError("Invalid animation child")
            child = raw[cursor:cursor + size]
            if kind == 0x4100:
                handle = struct.unpack_from("<H", child, 6)[0]
                if handle in handles:
                    if handle in found:
                        raise ValueError("Duplicate torso track")
                    found.add(handle)
                    child = shift_half(child, duration)
            children.append(child)
            cursor += size
        if found != handles or name in edited:
            raise ValueError("Missing or duplicate target tracks")
        payload = raw[6:nl + 5] + b"".join(children)
        output.append(struct.pack("<HI", 0x4000, len(payload) + 6) + payload)
        edited[name] = len(found)
    if edited.keys() != TARGETS:
        raise ValueError("Missing target animation aliases")
    return b"".join(output), edited


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = args.input.read_bytes()
    baseline = hashlib.sha256(data).hexdigest()
    if baseline != args.expected_sha256:
        raise SystemExit("Baseline hash mismatch")
    result, edited = patch(data)
    report = {"baseline_sha256": baseline, "candidate_sha256": hashlib.sha256(result).hexdigest(),
              "edited_tracks": edited, "torso_bones": sorted(TORSO), "phase_shift": 0.5,
              "scope": "T60 private asset only; no FCS/global animation changes",
              "installed": False, "game_verified": False}
    with args.output.open("xb") as stream:
        stream.write(result)
    with args.output.with_suffix(".json").open("x", encoding="utf8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
