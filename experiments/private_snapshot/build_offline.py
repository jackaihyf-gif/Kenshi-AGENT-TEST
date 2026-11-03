"""Build and run only standalone native mocks; never load the game or build a DLL."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def bounded_run(command, *, timeout, env=None):
    """Preserve a timed-out build/test as failed evidence instead of losing the row."""
    try:
        return subprocess.run(command, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(command, 124, "", f"Timed out after {timeout}s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Native mock execution is Windows-only; other platforms are unverified")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parent
    source_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(source.iterdir()) if path.suffix in {".c", ".h", ".py"}
    }
    env = os.environ.copy()
    env["ZIG_GLOBAL_CACHE_DIR"] = str(out / "zig-global")
    env["ZIG_LOCAL_CACHE_DIR"] = str(out / "zig-local")
    sentinel = out / "assert_sentinel.c"
    sentinel.write_text(
        "#include <assert.h>\nstatic int n;\n"
        "int main(void){assert(++n==1);return n==1?0:91;}\n", encoding="utf-8",
    )
    rows = []
    for name, file in (("assert_sentinel", sentinel),
                       ("complete", source / "test_complete.c"),
                       ("release", source / "test_release.c"),
                       ("id_ownership", source / "test_id_ownership.c"),
                       ("release_guards", source / "test_release_guards.c")):
        executable = out / (name + ".exe")
        command = [str(args.compiler.resolve()), "cc", "-std=c11", "-fms-extensions",
                   "-O1", "-UNDEBUG", str(file), "-ladvapi32", "-o", str(executable)]
        built = bounded_run(command, env=env, timeout=180)
        row = {"test": name, "compile_exit": built.returncode,
               "compile_stdout": built.stdout, "compile_stderr": built.stderr}
        if built.returncode == 0:
            cases = (["budget", "alloc-null", "scratch-null", "readers", "pair-alias",
                      "exception-stop"]
                     if name == "release_guards" else [None])
            row["cases"] = []
            for case in cases:
                command = [str(executable)] + ([case] if case else [])
                ran = bounded_run(command, timeout=60)
                row["cases"].append({"case": case, "exit_code": ran.returncode,
                                     "stdout": ran.stdout, "stderr": ran.stderr})
            row["exit_code"] = int(any(case["exit_code"] for case in row["cases"]))
        rows.append(row)
        (out / "results.json").write_text(json.dumps({
            "evidence_kind": "native_mock", "game_verified": False, "tests": rows,
            "source_sha256": source_hashes,
        }, indent=2), encoding="utf-8")
        if built.returncode or row.get("exit_code") != 0:
            print(f"FAILED: {name}; see {out / 'results.json'}")
            return 1
    print("PASSED: assertion sentinel and native mocks; not a real-game test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
