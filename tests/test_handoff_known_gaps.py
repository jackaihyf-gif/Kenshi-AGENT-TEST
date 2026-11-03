"""Executable handoff reproducers; these are offline contract gaps, not game tests."""

import json
from pathlib import Path

import pytest

from kenshi_test.adapters.kenshi import KenshiAdapter
from kenshi_test.bridge import LuaBridge


@pytest.mark.xfail(strict=True, reason="T60 is in belt/wardrobe[14], not upper-body armor")
def test_real_adapter_observes_component_in_existing_belt_detail(tmp_path, monkeypatch):
    adapter = KenshiAdapter(tmp_path / "kenshi_x64.exe", tmp_path)
    observed = {
        "phase": "ready",
        "characters": {"fixture": {
            "upper": "ordinary-shirt",
            "detail": {"wardrobe": {
                "14": {"id": "650-JACK_T60_WearLab.mod", "equipped": True},
            }},
        }},
    }
    monkeypatch.setattr(adapter, "_status", lambda deadline: observed)
    assert adapter.get_state(type("DeadlineStub", (), {"remaining": lambda _: 1})()).armor_equipped


@pytest.mark.xfail(strict=True, reason="Action expiry is computed before slow session lookup")
def test_action_is_not_expired_after_slow_session_lookup(tmp_path, monkeypatch):
    import kenshi_test.bridge as bridge_module

    (tmp_path / "bridge-config.json").write_text(json.dumps({"token": "a" * 64}), "utf-8")
    clock = {"now": 100.0}
    monkeypatch.setattr(bridge_module.time, "time", lambda: clock["now"])
    original_call = LuaBridge.call

    def call(self, command, deadline, **parameters):
        if command == "status":
            clock["now"] += 31
            return {"session": "synthetic-session"}
        return original_call(self, command, deadline, **parameters)

    monkeypatch.setattr(LuaBridge, "call", call)
    read_text = Path.read_text

    def response(path, *args, **kwargs):
        if path.name != "response.json":
            return read_text(path, *args, **kwargs)
        fields = dict(line.split("=", 1) for line in
                      read_text(tmp_path / "request.ini", "utf-8").splitlines())
        valid = int(fields["expires"]) >= int(clock["now"])
        return json.dumps({"id": fields["id"], "protocol": 1, "simulated": False,
                           "ok": valid, "error": "synthetic expired request"})

    monkeypatch.setattr(Path, "read_text", response)

    class Budget:
        def remaining(self):
            return 160.0 - clock["now"]

        def sleep(self, seconds):
            raise AssertionError("The synthetic response should be immediate")

    assert LuaBridge(tmp_path).call("wear", Budget(), owner="1-2-3", enabled=1)["ok"]
