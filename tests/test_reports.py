import json

import pytest

from kenshi_test.errors import KenshiTestError
from kenshi_test.models import RunReport, utc_now
from kenshi_test.reports import ReportGenerator, new_run_id


def test_latest_ignores_incomplete_run_and_report_is_portable(tmp_path):
    generator = ReportGenerator(tmp_path)
    report = RunReport(new_run_id(), "armor", "mock", "mock_simulation", utc_now())
    directory = generator.create_run_directory(report.run_id)
    generator.write(report, directory)
    incomplete = generator.create_run_directory("99999999-incomplete")
    (incomplete / "report.md").write_text("partial", encoding="utf-8")
    path, loaded = generator.latest()
    assert path.parent == directory
    assert loaded == report.to_dict()
    assert not list(directory.glob("*.tmp"))
    assert "Real Kenshi verified: **NO**" in (directory / "report.md").read_text("utf-8")


def test_corrupt_latest_is_not_silently_hidden(tmp_path):
    generator = ReportGenerator(tmp_path)
    folder = generator.create_run_directory("broken")
    (folder / "report.md").write_text("text", encoding="utf-8")
    for content in ("{", "[]", json.dumps({"schema_version": 2})):
        (folder / "report.json").write_text(content, encoding="utf-8")
        with pytest.raises(KenshiTestError, match="Cannot read latest report"):
            generator.latest()


def test_new_run_ids_do_not_collide():
    assert len({new_run_id() for _ in range(100)}) == 100
