import argparse
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from . import __version__
from .adapters import KenshiAdapter, MockAdapter
from .assets import AssetChecker
from .config import SCENARIOS, Config, load_config, number, resolve_path
from .errors import ConfigError, KenshiTestError
from .models import RunReport, utc_now
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
    run.add_argument("--suite", choices=("armor",), default="armor")
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
    return root


def doctor(config: Config) -> dict:
    config.reports_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=config.reports_dir) as stream:
        stream.write(b"write probe")
        stream.flush()
    game_present = bool(config.game_executable and config.game_executable.is_file())
    code = 0 if config.adapter == "mock" else (6 if game_present else 5)
    return {
        "python": sys.version.split()[0], "adapter": config.adapter,
        "offline_ready": True, "reports_writable": True,
        "game": "configured_file_exists" if game_present else "not_configured_or_missing",
        "game_required_for_mock": False, "real_adapter": "not_implemented",
        "game_verified": False, "exit_code": code,
        "message": "Offline checks ready. Mock testing does not require Kenshi.",
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
    status = "error" if any(c.status == "error" for c in checks) else (
        "failed" if any(c.status == "failed" for c in checks) else (
            "passed" if any(c.status == "passed" for c in checks) else "skipped"
        )
    )
    code = {"passed": 0, "failed": 1, "error": 3, "skipped": 6}[status]
    report = RunReport(
        run_id=new_run_id(), suite="assets", adapter="offline", evidence_kind="static_only",
        started_at=started_at, finished_at=utc_now(), status=status, exit_code=code, checks=checks,
        limitations=[
            "Only stream header, serializer syntax and payload presence are checked.",
            "OGRE chunks, geometry, bones, weights, animation and compatibility are unknown.",
            "References are user-declared; .material, .mod/FCS and binary links are not parsed.",
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
            config = replace(config, reports_dir=resolve_path(
                str(args.reports_dir), Path.cwd(), "--reports-dir"
            ))
        if getattr(args, "adapter", None):
            config = replace(config, adapter=args.adapter)
        if args.command == "doctor":
            data = doctor(config)
            print(json.dumps(data, indent=2) if args.json else "\n".join(
                f"{k}: {v}" for k, v in data.items()
            ))
            return data["exit_code"]
        if args.command == "report":
            path, data = ReportGenerator(config.reports_dir).latest()
            print(json.dumps(data, ensure_ascii=False, indent=2) if args.format == "json"
                  else path.with_suffix(".md").read_text(encoding="utf-8"), end="\n")
            return 0  # Reading a failed test report successfully is still a successful read.
        if args.command == "check-assets":
            return run_assets(args, config)
        if args.timeout is not None:
            config = replace(config, timeout=number(args.timeout, "--timeout"))
        if args.mock_scenario:
            if config.adapter != "mock":
                raise ConfigError("--mock-scenario only applies to --adapter mock")
            config = replace(config, mock=replace(config.mock, scenario=args.mock_scenario))
        adapter = MockAdapter(config.mock) if config.adapter == "mock" else KenshiAdapter(
            config.game_executable
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
