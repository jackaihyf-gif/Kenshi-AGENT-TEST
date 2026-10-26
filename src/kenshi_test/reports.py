"""Self-contained reports; only complete report directories participate in --latest."""

import json
import os
from datetime import UTC
from pathlib import Path
from uuid import uuid4

from .errors import KenshiTestError
from .models import RunReport


def new_run_id() -> str:
    from datetime import datetime

    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ-") + uuid4().hex[:8]


def _atomic_write(path: Path, content: str) -> None:
    temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temp.write_text(content, encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


class ReportGenerator:
    def __init__(self, root: Path):
        self.root = root

    def create_run_directory(self, run_id: str) -> Path:
        directory = self.root / run_id
        directory.mkdir(parents=True, exist_ok=False)
        return directory

    def write(self, report: RunReport, directory: Path) -> None:
        # JSON is the completion marker, written last. No racy shared latest pointer.
        _atomic_write(directory / "report.md", self.markdown(report))
        _atomic_write(directory / "report.json", json.dumps(
            report.to_dict(), ensure_ascii=False, indent=2, allow_nan=False
        ) + "\n")

    @staticmethod
    def markdown(report: RunReport) -> str:
        rows = [
            "# Kenshi Test Report", "", f"- Run: `{report.run_id}`",
            f"- Suite: `{report.suite}`", f"- Adapter: `{report.adapter}`",
            f"- Evidence: **{report.evidence_kind}**",
            "- Real Kenshi verified: **NO**",
            f"- Result: **{report.status.upper()}** (exit {report.exit_code})",
            f"- Started (UTC): {report.started_at}", f"- Finished (UTC): {report.finished_at}", "",
            "This report does not establish real-game compatibility or visual correctness.", "",
            "| Check | Status | Code | Details |", "| --- | --- | --- | --- |",
        ]
        rows.extend(
            f"| {_cell(c.name)} | {c.status} | {c.error_code or ''} | {_cell(c.message)} |"
            for c in report.checks
        )
        if report.artifacts:
            rows.extend(["", "## Evidence", ""])
            for item in report.artifacts:
                label = "MOCK SIMULATED FRAME" if item.simulated else "Capture"
                rows.append(f"![{label}]({item.path})")
        if report.limitations:
            rows.extend(["", "## Limits", ""])
            rows.extend(f"- {item}" for item in report.limitations)
        return "\n".join(rows) + "\n"

    def latest(self) -> tuple[Path, dict]:
        if not self.root.is_dir():
            raise KenshiTestError(f"No reports found in {self.root}; run a suite first")
        # Names use UTC timestamps and unique suffixes. Incomplete runs are ignored.
        candidates = sorted(self.root.glob("*/report.json"), reverse=True)
        candidates = [p for p in candidates if p.with_suffix(".md").is_file()]
        if not candidates:
            raise KenshiTestError(f"No complete reports found in {self.root}")
        path = candidates[0]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            required = {"schema_version", "run_id", "status", "adapter", "evidence_kind", "checks"}
            if not isinstance(data, dict) or not required <= data.keys():
                raise ValueError("missing required report fields")
            if data["schema_version"] != 1:
                raise ValueError("unsupported report schema")
        except (OSError, ValueError) as exc:
            raise KenshiTestError(f"Cannot read latest report {path}: {exc}") from exc
        return path, data
