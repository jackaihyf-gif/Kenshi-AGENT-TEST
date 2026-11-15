"""Build and run only standalone native mocks; never load the game or build a DLL."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


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
                       ("release", source / "test_release.c")):
        executable = out / (name + ".exe")
        command = [str(args.compiler.resolve()), "cc", "-std=c11", "-fms-extensions",
                   "-O1", "-UNDEBUG", str(file), "-ladvapi32", "-o", str(executable)]
        built = subprocess.run(command, env=env, capture_output=True, text=True, timeout=180)
        row = {"test": name, "compile_exit": built.returncode,
               "compile_stdout": built.stdout, "compile_stderr": built.stderr}
        if built.returncode == 0:
            ran = subprocess.run([str(executable)], capture_output=True, text=True, timeout=60)
            row.update(exit_code=ran.returncode, stdout=ran.stdout, stderr=ran.stderr)
        rows.append(row)
        (out / "results.json").write_text(json.dumps({
            "evidence_kind": "native_mock", "game_verified": False, "tests": rows,
        }, indent=2), encoding="utf-8")
        if built.returncode or row.get("exit_code") != 0:
            print(f"FAILED: {name}; see {out / 'results.json'}")
            return 1
    print("PASSED: assertion sentinel and two native mocks; not a real-game test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
