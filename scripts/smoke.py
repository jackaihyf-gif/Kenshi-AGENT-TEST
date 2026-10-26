"""Run acceptance commands against the installed CLI in an empty directory, without Kenshi."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    executable = Path(sys.executable).parent / (
        "kenshi-test.exe" if os.name == "nt" else "kenshi-test"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("KENSHI_TEST_")}
    with tempfile.TemporaryDirectory(prefix="kenshi-cli-smoke-") as temporary:
        cwd = Path(temporary)

        def run(*args: str, expected: int = 0) -> subprocess.CompletedProcess:
            result = subprocess.run(
                [str(executable), *args], cwd=cwd, env=env,
                capture_output=True, text=True, encoding="utf-8", timeout=15,
            )
            if result.returncode != expected:
                raise RuntimeError(
                    f"{args}: exit {result.returncode}\n{result.stdout}\n{result.stderr}"
                )
            print(f"OK exit={expected}: kenshi-test {' '.join(args)}")
            return result

        run("doctor")
        run("run", "--adapter", "mock", "--suite", "armor")
        run("report", "--latest")
        data = json.loads(run("report", "--latest", "--format", "json").stdout)
        if data["game_verified"] or data["evidence_kind"] != "mock_simulation":
            raise RuntimeError("Invalid evidence boundary in report")
        screenshot = cwd / "reports" / data["run_id"] / data["artifacts"][0]["path"]
        if "MOCK / SIMULATED FRAME" not in screenshot.read_text("utf-8"):
            raise RuntimeError("Mock screenshot is missing its visible label")
        run("run", "--mock-scenario", "failure", expected=1)
        run("run", "--mock-scenario", "timeout", "--timeout", "0.05", expected=4)
        run("run", "--mock-scenario", "missing", expected=5)
        run("run", "--adapter", "kenshi", expected=5)
        print("PASS: installed CLI acceptance; no game launched or verified")


if __name__ == "__main__":
    main()
