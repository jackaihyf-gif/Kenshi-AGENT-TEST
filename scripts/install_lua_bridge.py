"""Install one isolated startup script; never replace the T60 wear controller."""

import argparse
import ctypes
import hashlib
import json
import secrets
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", required=True, type=Path)
    parser.add_argument("--mod", default="JACK_T60_WearLab")
    parser.add_argument("--test-character", default="T-60 穿脱测试员")
    parser.add_argument("--install", action="store_true")
    parser.add_argument(
        "--idle-upgrade",
        action="store_true",
        help="Upgrade only our bridge while the real game has no loaded characters",
    )
    parser.add_argument(
        "--test-upgrade",
        action="store_true",
        help="Upgrade only our bridge in the single-character isolated test",
    )
    parser.add_argument(
        "--stage2-upgrade",
        action="store_true",
        help="Recover exactly the two known stage-2 test handles",
    )
    parser.add_argument(
        "--stage2-running-upgrade",
        action="store_true",
        help="Upgrade bridge in the exact five-person no-autosave fixture",
    )
    parser.add_argument(
        "--migration-proof",
        type=Path,
        help="Upgrade only after matching a captured, bound five-actor native identity proof",
    )
    parser.add_argument(
        "--owned-reload-proof",
        type=Path,
        help="Recover the same five saved handles after an owned test reload",
    )
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project / "src"))
    game = args.game.resolve()
    if Path(args.mod).name != args.mod or args.mod in ("", ".", ".."):
        raise ValueError("mod must be a single directory name")
    mod = (game / "mods" / args.mod).resolve()
    if not mod.is_relative_to(game / "mods"):
        raise ValueError("Mod path escaped game mods directory")
    assert (game / "kenshi_x64.exe").is_file(), "Game executable missing"
    assert (mod / (args.mod + ".mod")).is_file(), "Active test mod missing"
    process = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Process -Name 'kenshi_x64','kenshi' -ErrorAction SilentlyContinue | "
            "ForEach-Object { $_.Id }; exit 0",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    root = project / "local-game" / "bridge"
    # Windows can retain terminated process objects while another tool holds a
    # handle. Enumeration alone must not mistake those objects for live games.
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    active_pids = []
    for identifier in process.stdout.split():
        handle = kernel.OpenProcess(0x1000, False, int(identifier))
        if not handle:
            if ctypes.get_last_error() == 87:  # exited after enumeration
                continue
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                raise ctypes.WinError(ctypes.get_last_error())
            if code.value == 259:  # STILL_ACTIVE
                active_pids.append(int(identifier))
        finally:
            kernel.CloseHandle(handle)
    if active_pids:
        assert (
            args.idle_upgrade
            or args.test_upgrade
            or args.stage2_upgrade
            or args.stage2_running_upgrade
            or args.migration_proof
            or args.owned_reload_proof
        ), "Exit Kenshi or request a bridge upgrade"
        from kenshi_test.adapters.base import Deadline
        from kenshi_test.bridge import LuaBridge

        status = LuaBridge(root).call("status", Deadline(8))["state"]
        chars = list(status["characters"].values())
        empty = status["phase"] == "waiting_for_test_save" and not chars
        isolated = (
            args.test_upgrade
            and len(chars) == 1
            and chars[0]["name"] == args.test_character
            and chars[0]["controllable"]
        )
        expected = {
            "1-2804199168-1-2987182592-1": args.test_character,
            "2-2411865344-1-2987182592-1": "T60_STAGE2_human_female",
            "3-1676391552-1-2987182592-1": "T60_STAGE2_shek_male",
            "4-3972167936-1-2987182592-1": "T60_STAGE2_shek_female",
            "5-3988769536-1-2987182592-1": "T60_STAGE2_human_male",
        }
        stage2 = (
            (args.stage2_upgrade and status["paused"] or args.stage2_running_upgrade)
            and not status["game"]["autosave_enabled"]
            and {k: v["name"] for k, v in status["characters"].items()} == expected
        )
        migration = False
        if args.migration_proof:
            proof = json.loads(args.migration_proof.read_text("utf8"))
            live = LuaBridge(root).call("lifecycle", Deadline(12), target="migration:status")
            assert live["session"] == proof["session"], "Proof belongs to another bridge session"
            assert status["paused"] and not status["game"]["autosave_enabled"], (
                "Pause and disable autosave"
            )
            old, current = proof["action"], live["action"]
            assert len(old["members"]) == len(current["members"]) == 5
            assert current["identity"]["epoch"] == old["identity"]["epoch"]
            assert not current["identity"]["stopped"] and not current["identity"]["deferred"]
            assert current["members"].keys() == old["members"].keys()
            for name, actor in current["members"].items():
                for field in (
                    "handle",
                    "token",
                    "character",
                    "appearance",
                    "inventory",
                    "stats",
                    "logical",
                ):
                    assert actor[field] == old["members"][name][field], (name, field)
            migration = True
        if args.owned_reload_proof:
            proof = json.loads(args.owned_reload_proof.read_text("utf8"))
            assert status["session"] == proof["session"], (
                "Reload proof is from another bridge session"
            )
            expected = {actor["handle"]: name for name, actor in proof["action"]["members"].items()}
            assert len(expected) == len(chars) == 5
            assert not status["game"]["autosave_enabled"] and not status["game"]["loading"]
            assert {
                handle: actor["name"] for handle, actor in status["characters"].items()
            } == expected
            for actor in status["characters"].values():
                assert (
                    actor["detail"]["identity"]["logical_race"]
                    == proof["action"]["members"][actor["name"]]["logical"]
                )
            migration = True
        assert empty or isolated or stage2 or migration, (
            "Bridge upgrade refused: not the isolated test"
        )
    source = project / "integration" / "kenshilua" / "agent_bridge.lua"
    target = mod / "scripts" / "init" / "agent_test_bridge.lua"
    manifest = root / "installation.json"
    if target.exists():
        assert manifest.is_file(), "Unknown existing bridge startup script"
        old = json.loads(manifest.read_text("utf-8"))
        assert hashlib.sha256(target.read_bytes()).hexdigest() == old["init_sha256"]
    print("BRIDGE_PREFLIGHT_PASSED; empty menu or isolated test; bridge startup script only")
    if not args.install:
        return
    root.mkdir(parents=True, exist_ok=True)
    config_path = root / "bridge-config.json"
    config = (
        json.loads(config_path.read_text("utf-8"))
        if config_path.exists()
        else {
            "root": root.as_posix(),
            "token": secrets.token_hex(32),
        }
    )
    config["test_character_name"] = args.test_character
    config["test_start_id"] = "664-JACK_T60_WearLab.mod"
    config["motion_dll"] = (mod / "plugin" / "T60MotionAudit.dll").as_posix()
    backup = root / ("backup-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    backup.mkdir()
    previous = (
        target,
        root / "agent_bridge.lua",
        root / "game_ops.lua",
        root / "weapon_test_controller.lua",
        root / "service_test_controller.lua",
        root / "craft_test_controller.lua",
        root / "power_test_controller.lua",
        config_path,
        manifest,
    )
    for existing in previous:
        if existing.exists():
            shutil.copy2(existing, backup / existing.name)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), "utf-8")
    copied = root / "agent_bridge.lua"
    shutil.copy2(source, copied)
    ops = root / "game_ops.lua"
    shutil.copy2(source.with_name("game_ops.lua"), ops)
    weapon_tools = root / "weapon_test_controller.lua"
    shutil.copy2(source.with_name("weapon_test_controller.lua"), weapon_tools)
    service_tools = root / "service_test_controller.lua"
    shutil.copy2(source.with_name("service_test_controller.lua"), service_tools)
    craft_tools = root / "craft_test_controller.lua"
    shutil.copy2(source.with_name("craft_test_controller.lua"), craft_tools)
    power_tools = root / "power_test_controller.lua"
    shutil.copy2(source.with_name("power_test_controller.lua"), power_tools)

    def q(s):
        return json.dumps(str(s), ensure_ascii=False)

    module_hash = hashlib.sha256(b"".join(
        path.read_bytes() for path in
        (copied, ops, weapon_tools, service_tools, craft_tools, power_tools)
    )).hexdigest()
    init = (
        "-- Kenshi Test CLI: direct game API bridge, no desktop input.\n"
        f"-- Module hash: {module_hash}\n"
        f"local module=dofile({q(copied.as_posix())})\n"
        "local config={"
        f"root={q(root.as_posix())},token={q(config['token'])},"
        f"test_character_name={q(args.test_character)},"
        f"test_start_id={q(config['test_start_id'])},motion_dll={q(config['motion_dll'])}"
        "}\n"
        f"local api=dofile({q(ops.as_posix())}).new(config)\n"
        "local service=module.new(config,api)\n"
        "Events.on('MyGUI::Gui::eventFrameStart',service.tick)\n"
        "print('[Kenshi Agent Bridge] Ready protocol=1; configured test character only')\n"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(init, "utf-8")
    manifest.write_text(
        json.dumps(
            {
                "installed_at": datetime.now(UTC).isoformat(),
                "init": str(target),
                "init_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "module_sha256": hashlib.sha256(copied.read_bytes()).hexdigest(),
                "ops_sha256": hashlib.sha256(ops.read_bytes()).hexdigest(),
                "weapon_tools_sha256": hashlib.sha256(weapon_tools.read_bytes()).hexdigest(),
                "service_tools_sha256": hashlib.sha256(service_tools.read_bytes()).hexdigest(),
                "craft_tools_sha256": hashlib.sha256(craft_tools.read_bytes()).hexdigest(),
                "power_tools_sha256": hashlib.sha256(power_tools.read_bytes()).hexdigest(),
                "backup": str(backup),
                "in_game_verified": False,
            },
            indent=2,
        ),
        "utf-8",
    )
    print("BRIDGE_INSTALLED", target)


if __name__ == "__main__":
    main()
