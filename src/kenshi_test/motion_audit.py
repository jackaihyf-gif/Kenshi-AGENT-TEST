"""Read captured KenshiLua observations; never turn input delivery into proof."""

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .errors import ConfigError
from .models import CheckResult, RunReport, utc_now
from .reports import ReportGenerator, new_run_id

SOURCE = re.compile(r"^(.+?) tracks=(\d+)((?: b\d+=\([^\r\n]+\))*)$")
STATE = re.compile(r"([^;]+?)\[w=([\d.eE+-]+),t=([\d.eE+-]+)\]")
PLAYING = re.compile(r"PLAYING owner=(\S+) speed=(\S+) order=(\S+) (.*)")
WEAR_VERSION = re.compile(r"\[JACK T60 WearLab v([\d.]+)\] Ready\.")


@dataclass
class Capture:
    owner: str
    sources: dict[str, str]


def parse_log(text: str) -> dict:
    # Multiple launches may share a file. Never combine old motion with a new startup.
    sessions = text.split("KenshiLua logger initialized")
    text = sessions[-1]
    captures: list[Capture] = []
    samples = []
    current = None
    for line in text.splitlines():
        if "[JACK T60 MotionAudit] SOURCES owner=" in line:
            owner = line.split("SOURCES owner=", 1)[1].split()[0]
            current = Capture(owner, {})
            captures.append(current)
        elif match := SOURCE.fullmatch(line.strip()):
            if current is not None:
                current.sources[match[1]] = line.strip()
        else:
            current = None
        if match := PLAYING.search(line):
            states = {name.strip(): float(weight) for name, weight, _ in STATE.findall(match[4])}
            samples.append({"owner": match[1], "speed": match[2], "order": match[3],
                            "states": states})
    versions = WEAR_VERSION.findall(text)
    return {"version": versions[-1] if versions else None,
            "sources": [asdict(c) for c in captures], "samples": samples,
            "has_startup": len(sessions) > 1,
            "runtime_errors": [line for line in text.splitlines() if any(
                marker in line for marker in ("READ_EXCEPTION", "MotionAudit] STOPPED",
                                              "Unable to found a bound vertex"))]}


def read_bounded(path: Path) -> bytes:
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ConfigError(f"Log exceeds 32 MiB; provide a single captured session: {path}")
    return path.read_bytes()


def audit_motion(log: Path, fingerprints: Path, expected_version: str,
                 required_gaits: list[str], reports_dir: Path) -> tuple[RunReport, Path]:
    raw = read_bounded(log)
    reference = read_bounded(fingerprints)
    expected = {}
    for line in reference.decode("utf-8-sig").splitlines():
        if match := SOURCE.fullmatch(line.strip()):
            expected[match[1]] = line.strip()
    if not expected:
        raise ConfigError("Fingerprint reference contains no MotionAudit source records")
    observation = parse_log(raw.decode("utf-8-sig", errors="replace"))
    report = RunReport(
        run_id=new_run_id(), suite="motion-observation", adapter="kenshi-log",
        evidence_kind="game_log_observation", started_at=utc_now(),
        limitations=[
            "This is a read-only audit of captured logs; no game control is implemented.",
            "The log may be historical; capture time and hashes are retained as evidence.",
            "Source track counts and selected first keys are partial fingerprints, not full poses.",
            "Reported animation weights prove activation only, not correct rendering or motion.",
            "Screenshots, weapon orientation, clipping and visual acceptance remain unverified.",
        ],
    )
    checks = report.checks
    checks.append(CheckResult(
        "input_provenance", "passed", "Captured inputs copied into this report",
        details={"log_sha256": hashlib.sha256(raw).hexdigest(),
                 "reference_sha256": hashlib.sha256(reference).hexdigest(),
                 "log_modified_utc_seconds": log.stat().st_mtime,
                 "log_path": str(log), "reference_path": str(fingerprints)},
    ))
    version_ok = observation["version"] == expected_version
    checks.append(CheckResult("loaded_version", "passed" if version_ok else "failed",
                              f"Expected {expected_version}; observed {observation['version']}"))
    mismatches = []
    missing = []
    captures = observation["sources"]
    for index, capture in enumerate(captures):
        for name, value in expected.items():
            if name not in capture["sources"]:
                missing.append({"capture": index, "owner": capture["owner"], "clip": name})
            elif capture["sources"][name] != value:
                mismatches.append({"capture": index, "owner": capture["owner"], "clip": name,
                                   "expected": value, "actual": capture["sources"][name]})
    source_status = ("failed" if mismatches or missing else "passed") if captures else "skipped"
    checks.append(CheckResult(
        "loaded_source_fingerprints", source_status,
        f"{len(captures)} captures; {len(mismatches)} mismatches; {len(missing)} missing clips",
        details={"mismatches": mismatches, "missing": missing},
    ))
    coverage = {}
    for gait in ("walk", "jog", "run", "block"):
        owners = set()
        count = 0
        for sample in observation["samples"]:
            states = sample["states"]
            if gait == "block":
                active = any(name.startswith(("blk ", "block ")) and w > .5
                             for name, w in states.items())
            else:
                active = states.get(gait + " lower", 0) > .5
            if active:
                owners.add(sample["owner"])
                count += 1
        coverage[gait] = {"active_samples": count, "owners": sorted(owners)}
        checks.append(CheckResult(
            f"activation_{gait}", "passed" if count else "skipped",
            f"{count} samples with lower-body weight > 0.5" if gait != "block"
            else f"{count} samples with blocking weight > 0.5",
            details=coverage[gait],
        ))
    errors = observation["runtime_errors"]
    checks.append(CheckResult(
        "runtime_errors", "failed" if errors else "passed",
        f"{len(errors)} recognized diagnostic errors", details={"lines": errors},
    ))
    if not observation["samples"]:
        checks.append(CheckResult("motion_samples", "skipped", "No live motion samples observed"))
    if any(check.status == "failed" for check in checks):
        report.status, report.exit_code = "failed", 1
    elif not captures or not observation["samples"] or any(
        not coverage[gait]["active_samples"] for gait in required_gaits
    ):
        report.status, report.exit_code = "skipped", 6
    report.finished_at = utc_now()
    generator = ReportGenerator(reports_dir)
    directory = generator.create_run_directory(report.run_id)
    (directory / "captured-kenshilua.log").write_bytes(raw)
    (directory / "expected-source-fingerprints.txt").write_bytes(reference)
    generator.write(report, directory)
    return report, directory
