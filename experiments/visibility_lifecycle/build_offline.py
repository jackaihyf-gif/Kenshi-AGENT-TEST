"""Build only synthetic tests; no game, production DLL, or installation."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).with_name("test_visibility_lifecycle.c")
    env = os.environ.copy()
    for name, folder in (
        ("TEMP", "tmp"),
        ("TMP", "tmp"),
        ("ZIG_LOCAL_CACHE_DIR", "zig-local"),
        ("ZIG_GLOBAL_CACHE_DIR", "zig-global"),
    ):
        path = out / folder
        path.mkdir(exist_ok=True)
        env[name] = str(path)
    common = [str(args.compiler), "cc", "-std=c11", "-fms-extensions", "-O1", "-UNDEBUG"]
    executable = out / "visibility-mock.exe"
    subprocess.run(
        common + [str(source), "-ladvapi32", "-o", str(executable)],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    negative = subprocess.run(
        common + ["-DNDEBUG", "-c", str(source), "-o", str(out / "must-not-build.obj")],
        env=env,
        capture_output=True,
        text=True,
    )
    assert negative.returncode != 0 and "Tests require active assertions" in negative.stderr
    run = subprocess.run([str(executable)], check=True, capture_output=True, text=True, timeout=30)
    result = {
        "result": "passed",
        "game_launched": False,
        "production_dll_built": False,
        "ndebug_build_rejected": True,
        "assertion_sentinel_executed": True,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "stdout": run.stdout.strip(),
    }
    (out / "results.json").write_text(json.dumps(result, indent=2) + "\n", "utf8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
