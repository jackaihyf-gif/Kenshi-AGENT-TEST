import argparse
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from . import __version__
from .adapters import KenshiAdapter, MockAdapter
from .assets import AssetChecker
from .bridge import LuaBridge, validate_control
from .config import SCENARIOS, Config, load_config, number, resolve_path
from .errors import ConfigError, KenshiTestError
from .models import RunReport, utc_now
from .motion_audit import audit_motion
from .reports import ReportGenerator, new_run_id
from .runner import TestRunner


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="kenshi-test", description="Offline-first Kenshi mod tests")
    root.add_argument("--version", action="version", version=__version__)

    # Accept shared options before or after the subcommand without overwriting earlier values.
    def common(target: argparse.ArgumentParser) -> None:
        target.add_argument("--config", type=Path, default=argparse.SUPPRESS)
        target.add_argument("--reports-dir", type=Path, default=argparse.SUPPRESS)

    common(root)
    sub = root.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="Check offline environment; game is optional")
    common(doctor)
    doctor.add_argument("--adapter", choices=("mock", "kenshi"))
    doctor.add_argument("--json", action="store_true")
    run = sub.add_parser("run", help="Run a suite and save JSON + Markdown reports")
    common(run)
    run.add_argument("--adapter", choices=("mock", "kenshi"))
    run.add_argument("--suite", choices=("armor", "observe"), default="armor")
    run.add_argument("--timeout", type=float)
    run.add_argument("--mock-scenario", choices=SCENARIOS)
    report = sub.add_parser("report", help="Read a completed report")
    common(report)
    report.add_argument("--latest", action="store_true", required=True)
    report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    assets = sub.add_parser("check-assets", help="Offline header and declared-reference checks")
    common(assets)
    assets.add_argument("paths", nargs="*", type=Path)
    assets.add_argument("--manifest", type=Path)
    motion = sub.add_parser("audit-motion", help="Audit real captured KenshiLua MotionAudit logs")
    common(motion)
    motion.add_argument("--log", type=Path, required=True)
    motion.add_argument("--fingerprints", type=Path, required=True)
    motion.add_argument("--expected-version", required=True)
    motion.add_argument(
        "--require-gaits",
        nargs="*",
        choices=("walk", "jog", "run", "block"),
        default=["walk", "jog", "run", "block"],
    )
    live = sub.add_parser("live", help="Direct in-game KenshiLua control; no desktop input")
    common(live)
    live.add_argument(
        "action",
        choices=(
            "status",
            "gait",
            "move",
            "halt",
            "sheathe",
            "release",
            "new-test",
            "finish-editor",
            "capture",
            "pause",
            "resume",
            "camera",
            "overlays",
            "close-overlay",
            "nearby",
            "autosave",
            "spar",
            "end-spar",
            "wear",
            "sources",
            "mounts",
            "motion-trace",
            "weapon",
        ),
    )
    live.add_argument("--owner")
    live.add_argument("--gait", choices=("walk", "jog", "run"), default="walk")
    live.add_argument("--dx", type=float, default=0.0)
    live.add_argument("--dz", type=float, default=0.0)
    live.add_argument("--duration", type=float, default=10.0)
    live.add_argument("--timeout", type=float, default=5.0)
    live.add_argument("--zoom", type=float, default=55.0)
    live.add_argument("--enabled", type=int, choices=(0, 1), default=0)
    live.add_argument("--target")
    start = sub.add_parser("start", help="Start Kenshi and confirm its settings dialog natively")
    common(start)
    start.add_argument("--attach-launcher", action="store_true")
    start.add_argument("--inspect-launcher", action="store_true")
    start.add_argument("--skip-mod-warnings", action="store_true")
    start.add_argument("--timeout", type=float, default=30.0)
    return root


def doctor(config: Config) -> dict:
    config.reports_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=config.reports_dir) as stream:
        stream.write(b"write probe")
        stream.flush()
    game_present = bool(config.game_executable and config.game_executable.is_file())
    bridge_configured = bool(
        config.game_bridge_dir and (config.game_bridge_dir / "bridge-config.json").is_file()
    )
    code = (
        0 if config.adapter == "mock" else ((0 if bridge_configured else 6) if game_present else 5)
    )
    return {
        "python": sys.version.split()[0],
        "adapter": config.adapter,
        "offline_ready": True,
        "reports_writable": True,
        "game": "configured_file_exists" if game_present else "not_configured_or_missing",
        "game_required_for_mock": False,
        "real_adapter": "lua_bridge_configured_not_connected"
        if bridge_configured
        else "not_implemented",
        "game_verified": False,
        "exit_code": code,
        "message": ("Offline checks ready. Mock testing does not require Kenshi."),
    }


def run_assets(args: argparse.Namespace, config: Config) -> int:
    started_at = utc_now()
    paths = tuple(p.resolve() for p in args.paths) or config.asset_paths
    manifest = args.manifest.resolve() if args.manifest else config.asset_manifest
    if not paths and manifest is None:
        raise ConfigError("Specify asset files, --manifest, or [assets] in config")
    checker = AssetChecker()
    checks = [checker.check_file(path) for path in paths]
    if manifest:
        checks.extend(checker.check_manifest(manifest))
    status = (
        "error"
        if any(c.status == "error" for c in checks)
        else (
            "failed"
            if any(c.status == "failed" for c in checks)
            else ("passed" if any(c.status == "passed" for c in checks) else "skipped")
        )
    )
    code = {"passed": 0, "failed": 1, "error": 3, "skipped": 6}[status]
    report = RunReport(
        run_id=new_run_id(),
        suite="assets",
        adapter="offline",
        evidence_kind="static_only",
        started_at=started_at,
        finished_at=utc_now(),
        status=status,
        exit_code=code,
        checks=checks,
        limitations=[
            ("Only stream header, serializer syntax and payload presence are checked."),
            ("OGRE chunks, geometry, bones, weights, animation and compatibility are unknown."),
            ("References are user-declared; .material, .mod/FCS and binary links are not parsed."),
            "No real game was launched or verified.",
        ],
    )
    generator = ReportGenerator(config.reports_dir)
    directory = generator.create_run_directory(report.run_id)
    generator.write(report, directory)
    print(f"{status.upper()} [static_only] - {directory / 'report.json'}")
    return code


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = parser().parse_args(argv)
    try:
        config = load_config(getattr(args, "config", None))
        if hasattr(args, "reports_dir"):
            config = replace(
                config, reports_dir=resolve_path(str(args.reports_dir), Path.cwd(), "--reports-dir")
            )
        if getattr(args, "adapter", None):
            config = replace(config, adapter=args.adapter)
        if args.command == "doctor":
            data = doctor(config)
            print(
                json.dumps(data, indent=2)
                if args.json
                else "\n".join(f"{k}: {v}" for k, v in data.items())
            )
            return data["exit_code"]
        if args.command == "report":
            path, data = ReportGenerator(config.reports_dir).latest()
            print(
                json.dumps(data, ensure_ascii=False, indent=2)
                if args.format == "json"
                else path.with_suffix(".md").read_text(encoding="utf-8"),
                end="\n",
            )
            return 0  # Reading a failed test report successfully is still a successful read.
        if args.command == "check-assets":
            return run_assets(args, config)
        if args.command == "start":
            from .adapters.base import Deadline
            from .launcher import start_game

            if not config.game_executable:
                raise ConfigError("Configure game.executable before startup")
            result = start_game(
                config.game_executable,
                Deadline(number(args.timeout, "--timeout")),
                attach=args.attach_launcher or args.inspect_launcher,
                inspect=args.inspect_launcher,
                skip_mod_warnings=args.skip_mod_warnings,
                bridge_dir=config.game_bridge_dir,
            )
            if not args.inspect_launcher:
                config.reports_dir.mkdir(parents=True, exist_ok=True)
                (config.reports_dir / (new_run_id() + "-startup.json")).write_text(
                    json.dumps(result, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "live":
            from .adapters.base import Deadline

            if config.game_bridge_dir is None:
                raise ConfigError("Configure game.bridge_dir before direct in-game control")
            action = args.action.replace("-", "_")
            parameters = validate_control(
                action, args.owner, args.gait, args.dx, args.dz, args.duration
            )
            if action == "camera":
                parameters["zoom"] = number(args.zoom, "--zoom")
            if action in {"autosave", "wear", "mounts", "motion_trace"}:
                parameters["enabled"] = args.enabled
            if action == "weapon":
                choice = args.target or "status"
                if choice not in {
                    "status",
                    "draw",
                    "original",
                    "reset-health",
                    "heavy",
                    "katana",
                    "sabre",
                    "polearm",
                    "blunt",
                    "hacker",
                }:
                    raise ConfigError(
                        "Choose status, draw, original, heavy, katana,"
                        " sabre, polearm, blunt or hacker"
                    )
                parameters["target"] = choice
            if action == "spar":
                if not args.target or any(c not in "0123456789-" for c in args.target):
                    raise ConfigError("Sparring requires an exact NPC handle from live nearby")
                parameters["target"] = args.target
            result = LuaBridge(config.game_bridge_dir).call(
                action,
                Deadline(number(args.timeout, "--timeout")),
                **parameters,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "audit-motion":
            report, directory = audit_motion(
                args.log.resolve(),
                args.fingerprints.resolve(),
                args.expected_version,
                args.require_gaits,
                config.reports_dir,
            )
            print(f"{report.status.upper()} [{report.evidence_kind}] - {directory / 'report.json'}")
            return report.exit_code
        if args.timeout is not None:
            config = replace(config, timeout=number(args.timeout, "--timeout"))
        if args.mock_scenario:
            if config.adapter != "mock":
                raise ConfigError("--mock-scenario only applies to --adapter mock")
            config = replace(config, mock=replace(config.mock, scenario=args.mock_scenario))
        adapter = (
            MockAdapter(config.mock)
            if config.adapter == "mock"
            else KenshiAdapter(config.game_executable, config.game_bridge_dir)
        )
        report, directory = TestRunner(config).run(adapter, args.suite)
        print(f"{report.status.upper()} [{report.evidence_kind}] - {directory / 'report.json'}")
        return report.exit_code
    except KenshiTestError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        return exc.exit_code
    except (OSError, ValueError) as exc:
        print(f"io_error: {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
