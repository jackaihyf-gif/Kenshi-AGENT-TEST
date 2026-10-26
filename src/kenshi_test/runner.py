import time
from pathlib import Path

from .adapters import GameAdapter
from .adapters.base import Deadline
from .config import Config
from .errors import ConfigError, KenshiTestError, OperationTimeout, TestFailure
from .models import CheckResult, RunReport, Screenshot, utc_now
from .reports import ReportGenerator, new_run_id
from .suites import armor_steps


def failure_result(name: str, exc: Exception, duration: float = 0.0) -> CheckResult:
    status = "timeout" if isinstance(exc, OperationTimeout) else (
        "failed" if isinstance(exc, TestFailure) else "error"
    )
    return CheckResult(
        name, status, str(exc) or type(exc).__name__,
        getattr(exc, "code", "unexpected_error"), round(duration, 6),
        {"exception_type": type(exc).__name__},
    )


def _set_failure(report: RunReport, result: CheckResult, exc: Exception) -> None:
    report.status = result.status
    report.exit_code = exc.exit_code if isinstance(exc, KenshiTestError) else 3


class TestRunner:
    __test__ = False

    def __init__(self, config: Config):
        self.config = config
        self.reports = ReportGenerator(config.reports_dir)

    def run(self, adapter: GameAdapter, suite: str = "armor") -> tuple[RunReport, Path]:
        if suite != "armor":
            raise ConfigError(f"Unknown suite: {suite}")
        report = RunReport(
            run_id=new_run_id(), suite=suite, adapter=adapter.name,
            evidence_kind="mock_simulation" if adapter.simulated else "unverified_game_attempt",
            started_at=utc_now(),
            limitations=[
                "Real Kenshi launch, input, state observation and screenshots are not implemented.",
                "The armor suite checks a synthetic inventory/equipment workflow only.",
                "No clipping, skin weights, animation or in-game rendering was verified.",
            ],
        )
        directory = self.reports.create_run_directory(report.run_id)
        deadline = Deadline(self.config.timeout)
        blocked = False
        try:
            for name, action in armor_steps(
                adapter, deadline, self.config.poll_interval, directory, report
            ):
                if blocked:
                    report.checks.append(CheckResult(name, "skipped", "Earlier step did not pass"))
                    continue
                started = time.monotonic()
                try:
                    deadline.remaining()
                    details = action()
                    deadline.remaining()
                    report.checks.append(CheckResult(
                        name, "passed", "Step completed", duration_seconds=round(
                            time.monotonic() - started, 6
                        ), details=details,
                    ))
                except Exception as exc:
                    result = failure_result(name, exc, time.monotonic() - started)
                    report.checks.append(result)
                    _set_failure(report, result, exc)
                    blocked = True
            if blocked:
                try:
                    shot = adapter.screenshot(directory / "failure", Deadline(1.0))
                    report.artifacts.append(Screenshot(
                        Path(shot.path).relative_to(directory).as_posix(),
                        shot.simulated, shot.media_type,
                    ))
                except Exception as exc:
                    report.checks.append(CheckResult(
                        "failure_screenshot", "skipped", f"Unavailable: {exc}"
                    ))
        except KeyboardInterrupt:
            report.status, report.exit_code = "interrupted", 130
            report.checks.append(CheckResult("run", "interrupted", "Interrupted by user"))
        finally:
            try:
                adapter.stop(Deadline(2.0))
                report.checks.append(CheckResult("cleanup", "passed", "Owned session cleaned up"))
            except Exception as exc:
                result = failure_result("cleanup", exc)
                report.checks.append(result)
                if report.exit_code == 0:
                    _set_failure(report, result, exc)
            report.finished_at = utc_now()
            self.reports.write(report, directory)
        return report, directory
