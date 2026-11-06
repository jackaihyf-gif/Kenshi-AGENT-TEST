import hashlib
import json
import os
import subprocess
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
OUT = Path(os.environ["KENSHI_LIFECYCLE_BUILD_OUT"]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
(OUT / "tmp").mkdir(exist_ok=True)
env["TEMP"] = env["TMP"] = str(OUT / "tmp")
env["ZIG_LOCAL_CACHE_DIR"] = str(OUT / "zig-local")
env["ZIG_GLOBAL_CACHE_DIR"] = str(OUT / "zig-global")
zig = os.environ["KENSHI_TEST_ZIG"]
common = [zig, "cc", "-std=c11", "-fms-extensions", "-O1", "-UNDEBUG"]
targets = [
    ("T60OriginalSave_reader.dll", ["-shared", str(SOURCE / "save_reader.c")]),
    ("test_save_reader.exe", [str(SOURCE / "test_save_reader.c")]),
    (
        "T60ResetGuard_20261105.dll",
        ["-shared", str(SOURCE / "reset_guard.c"), str(SOURCE / "reset_guard.S")],
    ),
    (
        "test_reset_guard.exe",
        ["-DRESET_GUARD_TEST", str(SOURCE / "test_reset_guard.c"), str(SOURCE / "reset_guard.S")],
    ),
]
for name, args in targets:
    r = subprocess.run(
        common + args + ["-ladvapi32", "-o", str(OUT / name)],
        env=env,
        capture_output=True,
        text=True,
    )
    print(name, r.returncode, r.stdout, r.stderr, flush=True)
    assert r.returncode == 0
tests = []
for name in ["test_save_reader.exe", "test_reset_guard.exe"]:
    r = subprocess.run([str(OUT / name)], capture_output=True, text=True)
    print(name, r.returncode, r.stdout, r.stderr, flush=True)
    assert r.returncode == 0
    tests.append({"name": name, "exit_code": r.returncode, "stdout": r.stdout.strip()})
r = subprocess.run(
    [str(OUT / "test_save_reader.exe"), "generation_quarantine"], capture_output=True, text=True
)
assert r.returncode == 0, r.stderr
tests.append(
    {
        "name": "generation_quarantine",
        "exit_code": r.returncode,
        "assertion": "quarantine returns -3 and output zero",
    }
)
result = {
    "native_mock": tests,
    "assertions": "explicit -UNDEBUG, compile rejects NDEBUG, reset test sentinel executed",
    "sha256": {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name, _ in targets},
}
(OUT / "offline-result.json").write_text(json.dumps(result, indent=2), "utf8")
print(json.dumps(result), flush=True)
