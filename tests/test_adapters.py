import time
import xml.etree.ElementTree as ET

import pytest

from kenshi_test.adapters import KenshiAdapter, MockAdapter
from kenshi_test.adapters.base import Deadline
from kenshi_test.config import MockConfig
from kenshi_test.errors import AdapterError, FeatureUnavailable, GameMissing, OperationTimeout


def test_mock_lifecycle_and_input(tmp_path):
    adapter = MockAdapter()
    deadline = Deadline(2)
    assert not adapter.get_state(deadline).running
    with pytest.raises(AdapterError):
        adapter.press_key("I", deadline)
    adapter.launch(deadline)
    with pytest.raises(AdapterError):
        adapter.launch(deadline)
    assert adapter.get_state(deadline).phase == "ready"
    with pytest.raises(AdapterError):
        adapter.press_key("E", deadline)
    with pytest.raises(AdapterError):
        adapter.press_key("F99", deadline)
    adapter.press_key("i", deadline)
    adapter.press_key("e", deadline)
    state = adapter.get_state(deadline)
    assert state.armor_equipped and state.inventory_open
    assert state.keys[-2:] == ("I", "E")
    shot = adapter.screenshot(tmp_path / "frame", deadline)
    assert shot.simulated is True
    root = ET.parse(shot.path).getroot()
    assert "MOCK" in root.attrib["aria-label"]
    adapter.press_key("ESC", deadline)
    assert not adapter.get_state(deadline).inventory_open
    adapter.stop(deadline)
    adapter.stop(deadline)
    assert adapter.get_state(deadline).phase == "stopped"
    with pytest.raises(AdapterError):
        adapter.screenshot(tmp_path / "stopped", deadline)
    adapter.launch(deadline)
    assert not adapter.get_state(deadline).armor_equipped
    assert adapter.get_state(deadline).keys == ()


def test_loading_and_deadline(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    adapter = MockAdapter(MockConfig(load_delay=0.01))
    deadline = Deadline(2)
    adapter.launch(deadline)
    assert adapter.get_state(deadline).phase == "loading"
    with pytest.raises(AdapterError):
        adapter.press_key("I", deadline)
    clock[0] += 0.02
    assert adapter.get_state(deadline).phase == "ready"


def test_launch_delay_honors_timeout():
    adapter = MockAdapter(MockConfig(launch_delay=10))
    started = time.monotonic()
    with pytest.raises(OperationTimeout):
        adapter.launch(Deadline(0.02))
    assert time.monotonic() - started < 2
    assert not adapter.state.running


def test_missing_is_explicitly_simulated():
    with pytest.raises(GameMissing, match="Simulated"):
        MockAdapter(MockConfig(scenario="missing")).launch(Deadline(1))


def test_real_interface_cannot_emit_fake_evidence(tmp_path):
    adapter = KenshiAdapter(None)
    deadline = Deadline(2)
    with pytest.raises(GameMissing):
        adapter.launch(deadline)
    for action in (
        lambda: adapter.press_key("I", deadline),
        lambda: adapter.get_state(deadline),
        lambda: adapter.screenshot(tmp_path / "real.png", deadline),
    ):
        with pytest.raises(FeatureUnavailable, match="NOT IMPLEMENTED"):
            action()
    adapter.stop(deadline)
    assert not (tmp_path / "real.png").exists()
