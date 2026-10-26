from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class GameState:
    running: bool = False
    phase: str = "stopped"
    inventory_open: bool = False
    armor_equipped: bool = False
    keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class Screenshot:
    path: str
    simulated: bool
    media_type: str = "image/svg+xml"


@dataclass
class CheckResult:
    name: str
    status: str
    message: str
    error_code: str | None = None
    duration_seconds: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunReport:
    run_id: str
    suite: str
    adapter: str
    evidence_kind: str
    started_at: str
    finished_at: str = ""
    status: str = "passed"
    exit_code: int = 0
    checks: list[CheckResult] = field(default_factory=list)
    artifacts: list[Screenshot] = field(default_factory=list)
    game_verified: bool = False
    schema_version: int = 1
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
