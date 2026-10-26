import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    for key in ("KENSHI_TEST_CONFIG", "KENSHI_TEST_GAME_EXECUTABLE", "KENSHI_TEST_REPORTS_DIR"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def cli(tmp_path):
    executable = Path(sys.executable).parent / (
        "kenshi-test.exe" if os.name == "nt" else "kenshi-test"
    )
    assert executable.is_file(), "Install this package first: python -m pip install -e '.[dev]'"

    def invoke(*args, timeout=15):
        return subprocess.run(
            [str(executable), *map(str, args)], cwd=tmp_path,
            capture_output=True, text=True, encoding="utf-8", timeout=timeout,
        )

    return invoke
