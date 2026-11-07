"""Build the cold-start material candidate only; never install or launch Kenshi."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parent
    output = args.out / "T60MaterialBridge_v091_isolatednormal_20261107.dll"
    command = [str(args.compiler), "cc", "-std=c11", "-fms-extensions", "-O1", "-g",
               "-UNDEBUG", "-shared", str(root / "material_bridge.c"), "-ladvapi32",
               "-o", str(output)]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    (args.out / "build.log").write_text(result.stdout + result.stderr, "utf8")
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
              for name in ("material_bridge.c", "binding_consistency.h", "t60_ogre_symbols.h",
                           "material_native.lua")}
    report = {"source_hashes": hashes,
              "dll_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
              "installed": False, "game_verified": False, "requires_cold_restart": True}
    (args.out / "build.json").write_text(json.dumps(report, indent=2), "utf8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
