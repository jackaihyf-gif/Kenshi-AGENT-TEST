import pytest

from kenshi_test.config import load_config
from kenshi_test.errors import ConfigError


def test_defaults_need_no_game(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = load_config()
    assert config.game_executable is None
    assert config.adapter == "mock"
    assert config.reports_dir == tmp_path / "reports"


@pytest.mark.parametrize("content", [
    "[unknown]\nx = 1", '[run]\nadapter = "oops"', '[mock]\nscenario = "oops"',
    "[run]\ntimeout = true", "[run]\ntimeout = nan", "[run]\ntimeout = inf",
    "[run]\npoll_interval = 0", "[mock]\nload_delay = -1", "run = 3",
    '[run]\nreports_dir = ""', "[assets]\npaths = 4", "[assets]\npaths = [3]",
    "[game]\nexecutable = 123", "[run]\ntimeout_seconds = 3",
    '[game]\nexecutable = ""', "[game]\nexecutable = false",
    "[run]\ntimeout = " + "9" * 400,
    '[run]\nreports_dir = "$KENSHI_MISSING_VARIABLE_12345/path"',
])
def test_invalid_config(content, tmp_path):
    path = tmp_path / "bad.toml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_config_paths_and_environment(tmp_path, monkeypatch):
    path = tmp_path / "settings.toml"
    path.write_text(
        '[run]\nreports_dir = "results"\n[game]\nexecutable = "local-game/game.exe"\n'
        '[assets]\npaths = ["local-assets/armor.mesh"]\nmanifest = "local-assets/manifest.json"',
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.game_executable == tmp_path / "local-game" / "game.exe"
    assert config.asset_paths == (tmp_path / "local-assets" / "armor.mesh",)
    monkeypatch.setenv("KENSHI_TEST_REPORTS_DIR", "override")
    monkeypatch.setenv("KENSHI_TEST_GAME_EXECUTABLE", "different.exe")
    monkeypatch.setenv("KENSHI_TEST_CONFIG", str(path))
    updated = load_config()
    assert updated.reports_dir == tmp_path / "override"
    assert updated.game_executable == tmp_path / "different.exe"
