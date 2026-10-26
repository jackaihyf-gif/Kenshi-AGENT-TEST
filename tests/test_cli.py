import json

import pytest


def latest_report(tmp_path):
    return json.loads(sorted((tmp_path / "reports").glob("*/report.json"))[-1].read_text("utf-8"))


def test_three_acceptance_commands_without_game(cli, tmp_path):
    health = cli("doctor")
    assert health.returncode == 0, health.stderr
    assert "game_verified: False" in health.stdout
    result = cli("run", "--adapter", "mock", "--suite", "armor")
    assert result.returncode == 0, result.stderr
    assert "mock_simulation" in result.stdout
    report = cli("report", "--latest")
    assert report.returncode == 0, report.stderr
    assert "Real Kenshi verified: **NO**" in report.stdout
    data = latest_report(tmp_path)
    assert data["status"] == "passed"
    assert data["game_verified"] is False
    assert data["adapter"] == "mock"
    assert data["evidence_kind"] == "mock_simulation"
    assert all(c["status"] == "passed" for c in data["checks"])
    assert data["artifacts"][0]["simulated"] is True
    image = tmp_path / "reports" / data["run_id"] / data["artifacts"][0]["path"]
    assert "MOCK / SIMULATED FRAME" in image.read_text("utf-8")
    assert "NOT KENSHI" in image.read_text("utf-8")
    assert image.suffix == ".svg"


@pytest.mark.parametrize(("scenario", "code", "status", "error"), [
    ("failure", 1, "failed", "assertion_failed"),
    ("timeout", 4, "timeout", "timeout"),
    ("missing", 5, "error", "game_missing"),
    ("crash", 3, "error", "adapter_error"),
    ("screenshot-error", 3, "error", "adapter_error"),
])
def test_failed_runs_have_reports_and_cleanup(cli, tmp_path, scenario, code, status, error):
    result = cli("run", "--mock-scenario", scenario, "--timeout", "0.2")
    assert result.returncode == code, result.stderr
    data = latest_report(tmp_path)
    assert data["status"] == status
    assert data["exit_code"] == code
    assert any(c["error_code"] == error for c in data["checks"])
    assert data["checks"][-1]["name"] == "cleanup"
    assert data["checks"][-1]["status"] == "passed"
    assert data["game_verified"] is False
    assert "Traceback" not in result.stderr
    assert cli("report", "--latest").returncode == 0


def test_real_adapter_missing_game_without_launch(cli, tmp_path):
    result = cli("run", "--adapter", "kenshi")
    assert result.returncode == 5
    data = latest_report(tmp_path)
    assert data["evidence_kind"] == "unverified_game_attempt"
    assert data["checks"][0]["error_code"] == "game_missing"
    assert data["artifacts"] == []
    assert cli("doctor", "--adapter", "kenshi").returncode == 5


def test_existing_executable_does_not_claim_real_support(cli, tmp_path):
    fake = tmp_path / "not-a-game.exe"
    fake.write_text("synthetic placeholder, never executable", encoding="utf-8")
    config = tmp_path / "real.toml"
    config.write_text('[game]\nexecutable = "not-a-game.exe"\n', encoding="utf-8")
    result = cli("run", "--config", config, "--adapter", "kenshi")
    assert result.returncode == 6
    assert latest_report(tmp_path)["checks"][0]["error_code"] == "not_implemented"
    assert cli("doctor", "--config", config, "--adapter", "kenshi").returncode == 6


def test_unicode_paths_and_config_base(cli, tmp_path):
    folder = tmp_path / "配置 with spaces"
    folder.mkdir()
    config = folder / "settings.toml"
    config.write_text('[run]\nreports_dir = "输出 results"\n', encoding="utf-8")
    assert cli("--config", config, "run").returncode == 0
    assert list((folder / "输出 results").glob("*/report.json"))
    output = cli("report", "--config", config, "--latest", "--format", "json")
    assert output.returncode == 0
    assert json.loads(output.stdout)["status"] == "passed"


def test_cli_overrides_config_and_environment(cli, tmp_path, monkeypatch):
    config = tmp_path / "settings.toml"
    config.write_text('[run]\nadapter = "kenshi"\ntimeout = 100\n', encoding="utf-8")
    monkeypatch.setenv("KENSHI_TEST_CONFIG", str(config))
    monkeypatch.setenv("KENSHI_TEST_REPORTS_DIR", str(tmp_path / "env-output"))
    output = cli("run", "--adapter", "mock", "--reports-dir", "override")
    assert output.returncode == 0
    assert list((tmp_path / "override").glob("*/report.json"))
    assert not (tmp_path / "env-output").exists()


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf"])
def test_invalid_timeout_is_config_error(cli, timeout):
    result = cli("run", "--timeout", timeout)
    assert result.returncode == 2
    assert "invalid_config" in result.stderr


def test_bad_config_and_unknown_suite(cli, tmp_path):
    assert cli("run", "--config", "missing.toml").returncode == 2
    assert cli("run", "--suite", "nonexistent").returncode == 2
    (tmp_path / "kenshi-test.toml").write_text("[run\n", encoding="utf-8")
    assert cli("doctor").returncode == 2


def test_empty_report_store_is_actionable(cli):
    result = cli("report", "--latest")
    assert result.returncode == 3
    assert "No reports" in result.stderr
    assert "Traceback" not in result.stderr


def test_unwritable_report_location_is_not_success(cli, tmp_path):
    (tmp_path / "file").write_text("not a directory", encoding="utf-8")
    assert cli("run", "--reports-dir", "file").returncode == 3
    assert cli("doctor", "--reports-dir", "file").returncode == 3


def test_check_assets_cli_and_report(cli, tmp_path):
    mesh = tmp_path / "synthetic.mesh"
    mesh.write_bytes(b"\x00\x10[MeshSerializer_v1.8]\nsynthetic payload")
    result = cli("check-assets", mesh)
    assert result.returncode == 0
    data = latest_report(tmp_path)
    assert data["evidence_kind"] == "static_only"
    assert data["checks"][0]["details"]["compatibility"] == "unknown"
    assert data["game_verified"] is False
    assert cli("check-assets", "missing.mesh").returncode == 1
    assert cli("check-assets").returncode == 2


def test_unsupported_assets_do_not_produce_pass(cli, tmp_path):
    (tmp_path / "opaque.mod").write_bytes(b"synthetic")
    assert cli("check-assets", "opaque.mod").returncode == 6
    assert latest_report(tmp_path)["status"] == "skipped"


def test_mock_option_rejected_for_real_adapter(cli):
    result = cli("run", "--adapter", "kenshi", "--mock-scenario", "success")
    assert result.returncode == 2
