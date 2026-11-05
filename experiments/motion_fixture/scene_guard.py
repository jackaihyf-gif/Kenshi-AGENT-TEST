"""Validate a noncombat observation; this module never controls the game."""

import math


def ammo_signature(detail):
    """Ignore row order while retaining ammunition quantity and charge changes."""
    raw = detail.get("ammo")
    if not isinstance(raw, (dict, list)) or len(raw) > 256:
        raise AssertionError("Missing, malformed or oversized ammunition observation")
    rows = raw.values() if isinstance(raw, dict) else raw
    result = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise AssertionError("Malformed ammunition item")
        if not 1 <= len(row["id"]) <= 160:
            raise AssertionError("Invalid ammunition ID")
        values = [row.get(key) for key in ("quantity", "charges", "full")]
        if any(type(value) not in (int, float) for value in values):
            raise AssertionError("Missing or nonnumeric ammunition observation")
        if any(not math.isfinite(value) or not 0 <= value <= 1_000_000 for value in values):
            raise AssertionError("Invalid ammunition quantity or charge")
        if not float(values[0]).is_integer():
            raise AssertionError("Fractional ammunition quantity")
        result.append((row["id"], *values))
    return tuple(sorted(result))


def guard_noncombat(detail, baseline_ammo):
    """Reject unknown scene state as well as combat, injury and ammunition use."""
    for key in ("dead", "unconscious", "injured", "combat"):
        if type(detail.get(key)) is not bool:
            raise AssertionError(f"Missing or non-boolean scene field: {key}")
    if detail["dead"] or detail["unconscious"] or detail["injured"]:
        raise AssertionError("Motion fixture became dead/unconscious/injured")
    attack = detail.get("attacking")
    if type(attack) not in (int, float) or not math.isfinite(attack):
        raise AssertionError("Missing or invalid attack observation")
    if detail["combat"] or attack != 0:
        raise AssertionError("Unplanned combat invalidates motion-only observation")
    if ammo_signature(detail) != baseline_ammo:
        raise AssertionError("Ammunition changed during motion-only observation")
