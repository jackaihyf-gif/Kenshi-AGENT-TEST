import json
from pathlib import Path

import pytest

from kenshi_test.adapters.base import Deadline
from kenshi_test.adapters.kenshi import KenshiAdapter
from kenshi_test.bridge import LuaBridge
from kenshi_test.errors import AdapterError, ConfigError, OperationTimeout


@pytest.mark.parametrize(
    "row",
    [
        None,
        {},
        {"detail": None},
        {"detail": {"wardrobe": None}},
        {"upper": "650-JACK_T60_WearLab.mod"},
        {"detail": {"wardrobe": {"14": {"id": "650-JACK_T60_WearLab.mod"}}}},
        {"detail": {"wardrobe": {"14": {"id": "other", "equipped": True}}}},
    ],
)
def test_missing_or_wrong_belt_never_reports_equipped(row, monkeypatch):
    adapter = KenshiAdapter(None)
    monkeypatch.setattr(adapter, "_status", lambda d: {"characters": {"actor": row}})
    state = adapter.get_state(Deadline(1))
    assert not state.armor_equipped and state.phase == "unknown"


def test_empty_ready_is_not_loaded(monkeypatch):
    adapter = KenshiAdapter(None)
    monkeypatch.setattr(adapter, "_status", lambda d: {"phase": "ready", "characters": {}})
    assert adapter.get_state(Deadline(1)).phase != "ready"


def test_observe_records_characters_without_claiming_visual_acceptance(tmp_path, monkeypatch):
    from kenshi_test.config import Config
    from kenshi_test.runner import TestRunner

    exe = tmp_path / "kenshi_x64.exe"
    exe.write_bytes(b"synthetic")
    adapter = KenshiAdapter(exe, tmp_path)
    observation = {"phase": "ready", "characters": {"fixture": {"detail": {}}}}

    def status(deadline):
        adapter.observation = observation
        return observation

    monkeypatch.setattr(adapter, "_status", status)
    report, _ = TestRunner(Config(reports_dir=tmp_path / "reports")).run(adapter, "observe")
    assert report.exit_code == 0
    assert report.game_verified is False
    assert report.checks[1].details["observation"] == observation


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    (tmp_path / "bridge-config.json").write_text(json.dumps({"token": "a" * 64}))
    original = LuaBridge.call

    def call(self, command, deadline, **kwargs):
        if command == "status":
            return {"session": "expected"}
        return original(self, command, deadline, **kwargs)

    monkeypatch.setattr(LuaBridge, "call", call)
    return LuaBridge(tmp_path)


def test_expired_budget_publishes_no_action(bridge):
    with pytest.raises(OperationTimeout):
        bridge.call("wear", Deadline(-1))
    assert not (bridge.root / "request.ini").exists()
    assert not (bridge.root / "client.lock").exists()


def test_caller_cannot_override_session(bridge):
    with pytest.raises(ConfigError, match="Reserved"):
        bridge.call("wear", Deadline(1), session="wrong")


def test_wrong_response_session_rejected(bridge, monkeypatch):
    read = Path.read_text

    def response(path, *args, **kwargs):
        if path.name != "response.json":
            return read(path, *args, **kwargs)
        fields = dict(line.split("=", 1) for line in read(bridge.root / "request.ini").splitlines())
        return json.dumps(
            {"id": fields["id"], "protocol": 1, "simulated": False, "ok": True, "session": "wrong"}
        )

    monkeypatch.setattr(Path, "read_text", response)
    with pytest.raises(AdapterError, match="session changed"):
        bridge.call("wear", Deadline(1))
    assert not (bridge.root / "client.lock").exists()
