"""Read-only installation check for reviewed skeleton/cache-gate pairs."""

import argparse
import hashlib
import json
from pathlib import Path

# The deployed native gate was inspected against its author source: its -31
# path rejects any skeleton other than this original digest, before loading Ogre.
# Add another pair only after the corresponding native gate is reviewed/tested.
REVIEWED_PAIRS = {
    "ecccbfebb61a689a8cd870d68e0fe913513ea04a9c2926c59b37e46a37702e9a": {
        "37246540fc1c985f6b95041595688463acc82bca23d0b05e248e5e9ead711609"
    }
}


def validate_hashes(skeleton_sha256, cache_gate_sha256):
    allowed = REVIEWED_PAIRS.get(cache_gate_sha256)
    if allowed is None:
        raise ValueError("Unreviewed cache-gate DLL: installation refused")
    if skeleton_sha256 not in allowed:
        raise ValueError(
            "Cache-gate/skeleton mismatch: native startup would reject this asset; "
            "a reviewed paired gate update is required before installation"
        )


def inspect_pair(skeleton, cache_gate):
    hashes = {
        "skeleton_sha256": hashlib.sha256(skeleton.read_bytes()).hexdigest(),
        "cache_gate_sha256": hashlib.sha256(cache_gate.read_bytes()).hexdigest(),
    }
    validate_hashes(hashes["skeleton_sha256"], hashes["cache_gate_sha256"])
    return {**hashes, "pair_reviewed": True, "engine_loaded": False, "files_written": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-skeleton", required=True, type=Path)
    parser.add_argument("--cache-gate", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = inspect_pair(args.candidate_skeleton, args.cache_gate)
    except (OSError, ValueError) as error:
        parser.exit(2, json.dumps({"pair_reviewed": False, "error": str(error)}) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
