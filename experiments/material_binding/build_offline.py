"""Compile/run synthetic native tests only; no game installation or game DLL loading."""

import argparse
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).with_name("test_binding.c")
    command = [str(args.compiler), "cc", "-std=c11", "-fms-extensions", "-O1"]
    executable = args.out / "material-binding-mock.exe"
    subprocess.run(command + ["-UNDEBUG", str(source), "-ladvapi32", "-o", str(executable)],
                   check=True, capture_output=True, text=True)
    result = subprocess.run([str(executable)], check=True, capture_output=True, text=True)
    assert "MATERIAL_BINDING_MOCK_PASS" in result.stdout
    negative = subprocess.run(command + ["-DNDEBUG", str(source), "-ladvapi32", "-o",
                                         str(args.out / "must-not-build.exe")],
                              capture_output=True, text=True)
    assert negative.returncode != 0 and "require active assertions" in negative.stderr
    report = {"synthetic_native_mock": "pass", "assertion_sentinel": "pass",
              "ndebug_compile_rejected": True, "game_loaded": False,
              "stdout": result.stdout.strip()}
    (args.out / "results.json").write_text(json.dumps(report, indent=2), "utf8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
