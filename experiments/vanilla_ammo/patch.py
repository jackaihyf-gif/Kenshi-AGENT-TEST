"""Sparse vanilla workbench recipe additions; no third-party records or assets."""

import copy

FUNCTIONS = ("96451-crafting.mod", "97092-rebirth.mod")
AMMO = ("200-JACK_EnergyWeapons.mod", "210-JACK_EnergyWeapons.mod")


def add_vanilla_ammo(rows, vanilla):
    """Preserve all installed content and append only two recipe reference patches."""
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate source record")
    if any(row["id"] in FUNCTIONS for row in rows):
        raise ValueError("Vanilla arrow patch already present; review before rebuilding")
    patches = []
    for sid in FUNCTIONS:
        target = vanilla[sid]
        if (
            target["type"] != 62
            or target["fields"].get("function") != 10
            or target["fields"].get("overrides ingredients") is not False
        ):
            raise ValueError(f"Unexpected vanilla functionality: {sid}")
        patches.append(
            {
                "id": sid,
                "name": target["name"],
                "type": 62,
                "flags": 16,
                "fields": {},
                "field_types": {},
                "refs": {"item crafts": {ammo: [50, 0, 0] for ammo in AMMO}},
            }
        )
    return copy.deepcopy(rows) + patches
