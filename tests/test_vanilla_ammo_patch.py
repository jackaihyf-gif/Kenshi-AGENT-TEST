"""Synthetic data only: catch broad station overrides and dependency/recipe loss."""

import copy
import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).parents[1] / "experiments/vanilla_ammo/patch.py"
SPEC = importlib.util.spec_from_file_location("vanilla_ammo_patch", MODULE)
patch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patch)


def fixture():
    rows = [{"id": "500-owned.mod", "fields": {"production mult": 2.0}}]
    vanilla = {
        sid: {
            "type": 62, "name": "synthetic arrow smith",
            "fields": {"function": 10, "overrides ingredients": False, "production mult": 1.0},
            "refs": {"item crafts": {"synthetic-arrow": [5, 0, 0]}},
        }
        for sid in patch.FUNCTIONS
    }
    return rows, vanilla


def test_sparse_patch_preserves_old_recipes_speed_and_owned_content():
    rows, vanilla = fixture()
    before = copy.deepcopy((rows, vanilla))
    result = patch.add_vanilla_ammo(rows, vanilla)
    assert (rows, vanilla) == before
    assert result[:len(rows)] == rows
    for record in result[len(rows):]:
        assert record["fields"] == record["field_types"] == {}
        assert record["flags"] == 16
        assert set(record["refs"]) == {"item crafts"}
        assert record["refs"]["item crafts"] == {a: [50, 0, 0] for a in patch.AMMO}
        merged = vanilla[record["id"]]["refs"]["item crafts"] | record["refs"]["item crafts"]
        assert merged["synthetic-arrow"] == [5, 0, 0]
    result[0]["fields"]["production mult"] = 99
    assert rows == before[0]


@pytest.mark.parametrize("problem", ["duplicate", "already_patched", "wrong_type", "ingredients"])
def test_rejects_ambiguous_or_unsafe_source(problem):
    rows, vanilla = fixture()
    if problem == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif problem == "already_patched":
        rows.append({"id": patch.FUNCTIONS[0]})
    elif problem == "wrong_type":
        vanilla[patch.FUNCTIONS[0]]["type"] = 0
    else:
        vanilla[patch.FUNCTIONS[0]]["fields"]["overrides ingredients"] = True
    with pytest.raises(ValueError):
        patch.add_vanilla_ammo(rows, vanilla)
