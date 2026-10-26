import json

import pytest

from kenshi_test.adapters import MockAdapter
from kenshi_test.config import Config, MockConfig
from kenshi_test.errors import AdapterError, ConfigError
from kenshi_test.runner import TestRunner


def test_unexpected_exception_is_reported_and_cleanup_runs(tmp_path):
    class BrokenAdapter(MockAdapter):
        def press_key(self, key, deadline):
            raise RuntimeError("unexpected backend failure")

    adapter = BrokenAdapter()
    report, directory = TestRunner(Config(reports_dir=tmp_path)).run(adapter)
    assert report.exit_code == 3
    assert not adapter.state.running
    assert any(c.error_code == "unexpected_error" for c in report.checks)
    assert (directory / "report.json").exists()
    assert any(c.status == "skipped" for c in report.checks)


def test_cleanup_failure_changes_success_to_error(tmp_path):
    class BrokenCleanup(MockAdapter):
        def stop(self, deadline):
            raise AdapterError("cleanup failed")

    report, _ = TestRunner(Config(reports_dir=tmp_path)).run(BrokenCleanup())
    assert report.exit_code == 3
    assert report.checks[-1].name == "cleanup"
    assert report.checks[-1].status == "error"


def test_cleanup_failure_preserves_primary_failure(tmp_path):
    class BrokenCleanup(MockAdapter):
        def stop(self, deadline):
            raise AdapterError("cleanup failed")

    report, _ = TestRunner(Config(reports_dir=tmp_path)).run(
        BrokenCleanup(MockConfig(scenario="failure"))
    )
    assert report.exit_code == 1
    assert report.checks[-1].error_code == "adapter_error"


def test_keyboard_interrupt_preserves_partial_report(tmp_path):
    class Interrupting(MockAdapter):
        def press_key(self, key, deadline):
            raise KeyboardInterrupt

    adapter = Interrupting()
    report, directory = TestRunner(Config(reports_dir=tmp_path)).run(adapter)
    assert report.exit_code == 130
    assert report.status == "interrupted"
    assert not adapter.state.running
    assert json.loads((directory / "report.json").read_text("utf-8"))["exit_code"] == 130


def test_failure_screenshot_is_simulated_and_relative(tmp_path):
    report, directory = TestRunner(Config(reports_dir=tmp_path)).run(
        MockAdapter(MockConfig(scenario="failure"))
    )
    assert report.artifacts[0].path == "failure.svg"
    assert report.artifacts[0].simulated
    assert (directory / "failure.svg").is_file()


def test_runner_rejects_unknown_suite(tmp_path):
    with pytest.raises(ConfigError):
        TestRunner(Config(reports_dir=tmp_path)).run(MockAdapter(), "bogus")
