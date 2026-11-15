"""Install only reviewed content into closed game; preserve rollback evidence."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

output_dir = Path(__file__).resolve().parent
G = Path("D:/steam/steamapps/common/Kenshi")
v = json.loads((output_dir / "validation.json").read_text("utf8"))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


assert (
    subprocess.check_output(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "@(Get-Process -Name kenshi_x64,kenshi -ErrorAction SilentlyContinue).Count",
        ],
        text=True,
    ).strip()
    == "0"
), "Existing game must not be touched"
assert not Path("D:/JACK/Kenshi-Single-Observer-20261103/local-game/bridge/client.lock").exists()
for name, key in [
    ("JACK_EnergyWeapons", "energy_before_sha256"),
    ("JACK_WastelandCraft", "craft_before_sha256"),
]:
    assert sha(G / "mods" / name / (name + ".mod")) == v[key], ("Baseline changed", name)
for name, digest in v["files"].items():
    source = output_dir / "candidate" / name
    dest = G / "mods" / name
    assert source.is_file() and sha(source) == digest
    assert dest.resolve().is_relative_to((G / "mods").resolve())
    assert name.split("/")[0] in ["JACK_EnergyWeapons", "JACK_WastelandCraft"]
    if dest.suffix != ".mod":
        assert not dest.exists(), ("Existing new-asset path", name)
copied = []
try:
    for name in sorted(v["files"], key=lambda n: n.endswith(".mod")):
        dest = G / "mods" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output_dir / "candidate" / name, dest)
        copied.append(name)
    assert all(sha(G / "mods" / name) == digest for name, digest in v["files"].items())
except Exception:
    for name in reversed(copied):
        dest = G / "mods" / name
        assert sha(dest) == v["files"][name]
        if dest.suffix == ".mod":
            shutil.copy2(output_dir / "backup" / dest.name, dest)
        else:
            dest.unlink()
    raise
(output_dir / "installation.json").write_text(
    json.dumps(
        {
            "installed": True,
            "files": v["files"],
            "game_verified": False,
            "backup": "backup",
            "existing_game": False,
        },
        indent=2,
    ),
    encoding="utf8",
)
print("STATION_AND_STACK_CONTENT_INSTALLED", len(copied), "files; game verification pending")
