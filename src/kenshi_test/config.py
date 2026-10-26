"""Strict TOML config. Relative paths are anchored to the config file directory."""

import math
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigError

SCENARIOS = ("success", "failure", "timeout", "missing", "crash", "screenshot-error")


@dataclass(frozen=True)
class MockConfig:
    scenario: str = "success"
    launch_delay: float = 0.0
    load_delay: float = 0.0


@dataclass(frozen=True)
class Config:
    reports_dir: Path
    adapter: str = "mock"
    timeout: float = 5.0
    poll_interval: float = 0.01
    game_executable: Path | None = None
    asset_paths: tuple[Path, ...] = ()
    asset_manifest: Path | None = None
    mock: MockConfig = field(default_factory=MockConfig)


def number(value: Any, name: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a number")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ConfigError(f"{name} is too large") from exc
    if not math.isfinite(value) or value < 0 or (value == 0 and not allow_zero):
        sign = "nonnegative" if allow_zero else "positive"
        raise ConfigError(f"{name} must be finite and {sign}")
    return value


def _table(value: Any, name: str, allowed: set[str]) -> dict:
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a TOML table")
    if unknown := set(value) - allowed:
        raise ConfigError(f"Unknown {name} keys: {', '.join(sorted(unknown))}")
    return value


def resolve_path(value: Any, base: Path, name: str) -> Path:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ConfigError(f"{name} must be a nonempty path string")
    expanded = os.path.expandvars(value)
    if "$" in expanded or ("%" in expanded and expanded.count("%") >= 2):
        raise ConfigError(f"Unresolved environment variable in {name}")
    path = Path(expanded).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def load_config(path: Path | None = None) -> Config:
    explicit = path is not None or bool(os.environ.get("KENSHI_TEST_CONFIG"))
    source = path or Path(os.environ.get("KENSHI_TEST_CONFIG", "kenshi-test.toml"))
    source = source.resolve()
    data: dict = {}
    if explicit or source.exists():
        try:
            with source.open("rb") as stream:
                data = tomllib.load(stream)
        except (OSError, ValueError) as exc:
            raise ConfigError(f"Cannot read config {source}: {exc}") from exc
    base = source.parent
    _table(data, "root", {"run", "game", "mock", "assets"})
    run = _table(data.get("run", {}), "run", {"adapter", "timeout", "poll_interval", "reports_dir"})
    game = _table(data.get("game", {}), "game", {"executable"})
    mock = _table(data.get("mock", {}), "mock", {"scenario", "launch_delay", "load_delay"})
    assets = _table(data.get("assets", {}), "assets", {"paths", "manifest"})
    adapter = run.get("adapter", "mock")
    if adapter not in ("mock", "kenshi"):
        raise ConfigError("run.adapter must be mock or kenshi")
    scenario = mock.get("scenario", "success")
    if scenario not in SCENARIOS:
        raise ConfigError(f"mock.scenario must be one of {SCENARIOS}")
    paths = assets.get("paths", [])
    if not isinstance(paths, list):
        raise ConfigError("assets.paths must be an array of path strings")
    executable = os.environ.get("KENSHI_TEST_GAME_EXECUTABLE", game.get("executable"))
    reports = os.environ.get("KENSHI_TEST_REPORTS_DIR", run.get("reports_dir", "reports"))
    return Config(
        reports_dir=resolve_path(reports, base, "reports_dir"),
        adapter=adapter,
        timeout=number(run.get("timeout", 5.0), "run.timeout"),
        poll_interval=number(run.get("poll_interval", 0.01), "run.poll_interval"),
        game_executable=resolve_path(executable, base, "game.executable")
        if executable is not None else None,
        asset_paths=tuple(resolve_path(p, base, "assets.paths") for p in paths),
        asset_manifest=resolve_path(assets["manifest"], base, "assets.manifest")
        if "manifest" in assets else None,
        mock=MockConfig(
            scenario=scenario,
            launch_delay=number(mock.get("launch_delay", 0), "mock.launch_delay", allow_zero=True),
            load_delay=number(mock.get("load_delay", 0), "mock.load_delay", allow_zero=True),
        ),
    )
