"""Regress real motion-fixture contamination without invoking a game or DLL."""

import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

path = Path(__file__).parents[1] / "experiments/motion_fixture/scene_guard.py"
spec = importlib.util.spec_from_file_location("motion_scene_guard", path)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def observation():
    return {
        "dead": False, "unconscious": False, "injured": False, "combat": False,
        "attacking": 0,
        "ammo": [{"id": "cell", "quantity": 1, "charges": 10, "full": 10}],
    }


def test_no_mutation_and_row_order_independence():
    detail = observation()
    detail["ammo"].append({"id": "bolt", "quantity": 3, "charges": 0, "full": 0})
    before = deepcopy(detail)
    baseline = guard.ammo_signature(detail)
    detail["ammo"] = dict(enumerate(reversed(detail["ammo"])))
    guard.guard_noncombat(detail, baseline)
    assert list(reversed(list(detail["ammo"].values()))) == before["ammo"]


@pytest.mark.parametrize("field", ["combat", "injured", "unconscious", "dead"])
def test_rejects_scene_contamination(field):
    detail = observation()
    baseline = guard.ammo_signature(detail)
    detail[field] = True
    with pytest.raises(AssertionError):
        guard.guard_noncombat(detail, baseline)


@pytest.mark.parametrize("change", ["remove", "quantity", "charges"])
def test_rejects_ammunition_use_even_if_combat_sample_was_missed(change):
    detail = observation()
    baseline = guard.ammo_signature(detail)
    if change == "remove":
        detail["ammo"] = []
    else:
        detail["ammo"][0][change] -= 1
    with pytest.raises(AssertionError, match="Ammunition changed"):
        guard.guard_noncombat(detail, baseline)


@pytest.mark.parametrize("field", ["combat", "attacking", "ammo"])
def test_missing_observations_do_not_pass(field):
    detail = observation()
    baseline = guard.ammo_signature(detail)
    del detail[field]
    with pytest.raises(AssertionError):
        guard.guard_noncombat(detail, baseline)


@pytest.mark.parametrize("value", [float("nan"), -1, True, "10"])
def test_rejects_invalid_ammunition_observation(value):
    detail = observation()
    detail["ammo"][0]["charges"] = value
    with pytest.raises(AssertionError):
        guard.ammo_signature(detail)
