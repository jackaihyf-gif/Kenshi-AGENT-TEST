"""A changed observer must change the startup identity and preserve the old file."""

import hashlib
import json
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock


def test_observer_install_identity_and_backup(tmp_path, monkeypatch):
    import ctypes

    project = tmp_path / "project"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    source = Path(__file__).parents[1]
    installer = scripts / "install_lua_bridge.py"
    shutil.copy2(source / "scripts/install_lua_bridge.py", installer)
    shutil.copytree(source / "integration/kenshilua", project / "integration/kenshilua")
    game = tmp_path / "game"
    mod = game / "mods/JACK_T60_WearLab"
    mod.mkdir(parents=True)
    (game / "kenshi_x64.exe").write_bytes(b"not an executable; installer fixture only")
    (mod / "JACK_T60_WearLab.mod").write_bytes(b"fixture")
    monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **kw: Mock(), raising=False)
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, "", "")
    )
    monkeypatch.setattr(sys, "argv", [str(installer), "--game", str(game), "--install"])
    runpy.run_path(str(installer), run_name="__main__")
    bridge = project / "local-game/bridge"
    installed = bridge / "single_telemetry.lua"
    original = installed.read_bytes()
    init = mod / "scripts/init/agent_test_bridge.lua"
    first_init = init.read_bytes()
    change = project / "integration/kenshilua/single_telemetry.lua"
    change.write_bytes(original + b"\n-- observer revision for upgrade test\n")
    runpy.run_path(str(installer), run_name="__main__")
    manifest = json.loads((bridge / "installation.json").read_text("utf-8"))
    assert installed.read_bytes() == change.read_bytes()
    assert manifest["telemetry_tools_sha256"] == hashlib.sha256(installed.read_bytes()).hexdigest()
    assert init.read_bytes() != first_init
    backup = Path(manifest["backup"])
    assert (backup / "single_telemetry.lua").read_bytes() == original
    assert (backup / "agent_test_bridge.lua").read_bytes() == first_init
