"""Double ammo-item charges and reduce laser damage 15%; preserve all other content."""

import argparse
import ast
import copy
import hashlib
import json
import pathlib
import struct

SOURCE_HASH = "e85dbe46581ff0d7f424d745d862a0394ec969914e1701675a09f05b279e3bb2"
AMMO = ("200-JACK_EnergyWeapons.mod", "210-JACK_EnergyWeapons.mod")
LASER = "100-JACK_EnergyWeapons.mod"
LASER_DAMAGE = {
    "pierce damage": (30.0, 25.5),
    "pierce damage min 0": (75.0, 63.75),
    "pierce damage max 0": (105.0, 89.25),
    "pierce damage min 1": (110.0, 93.5),
    "pierce damage max 1": (150.0, 127.5),
}


def definitions(path, namespace):
    tree = ast.parse(path.read_text("utf8"))
    body = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), namespace)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", required=True, type=pathlib.Path)
    parser.add_argument("--reader", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    ns = {"struct": struct, "hashlib": hashlib}
    definitions(args.reader, ns)
    definitions(pathlib.Path(__file__).parents[1] / "station_split/build_candidate_local.py", ns)
    reader, merge, encode = ns["Reader"], ns["merge"], ns["encode"]
    root = args.game_root
    source = root / "mods/JACK_EnergyWeapons/JACK_EnergyWeapons.mod"
    if sha(source) != SOURCE_HASH:
        raise ValueError("Installed Energy source changed; review before rebuilding")
    rd = reader(source)
    if rd.val("i") != 16:
        raise ValueError("Expected lossless version 16 source")
    rd.val("i")
    for _ in range(4):
        rd.s()
    rd.val("i")
    prefix = rd.b[:rd.o]
    original = list(reader(source).records())
    if encode(original, prefix) != source.read_bytes():
        raise ValueError("Source byte roundtrip failed")
    rows = copy.deepcopy(original)
    for sid in AMMO:
        row = next(row for row in rows if row["id"] == sid)
        if row["fields"]["charges"] != 1.0 or row["field_types"]["charges"] != 1:
            raise ValueError("Expected float ammo charges=1")
        row["fields"]["charges"] = 2.0
    laser = next(row for row in rows if row["id"] == LASER)
    for field, (old, new) in LASER_DAMAGE.items():
        if laser["fields"][field] != old or laser["field_types"][field] != 1:
            raise ValueError(f"Unexpected laser damage source: {field}")
        laser["fields"][field] = new
    candidate = args.output / "JACK_EnergyWeapons.mod.candidate"
    candidate.write_bytes(encode(rows, prefix))
    if list(reader(candidate).records()) != rows:
        raise ValueError("Candidate readback failed")
    files = [root / "data" / name
             for name in ("gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod")]
    enabled = [name for name in (root / "data/mods.cfg").read_text("utf-8-sig").splitlines()
               if name.strip()]
    available = {p.name: p for p in (root / "../../workshop/content/233860").rglob("*.mod")}
    available.update({p.name: p for p in (root / "mods").rglob("*.mod")})
    if missing := set(enabled) - set(available):
        raise ValueError(f"Missing enabled mods: {sorted(missing)}")
    files += [available[name] for name in enabled]
    before, after = {}, {}
    for path in files:
        content = list(reader(path).records())
        merge(before, copy.deepcopy(content), path.name)
        merge(after, copy.deepcopy(rows if path == source else content), path.name)
    expected = copy.deepcopy(before)
    for sid in AMMO:
        expected[sid]["fields"]["charges"] = 2.0
    for field, (_, new) in LASER_DAMAGE.items():
        expected[LASER]["fields"][field] = new
    if after != expected:
        raise ValueError("Active load order does not contain exactly the intended seven changes")
    report = {
        "source_sha256": SOURCE_HASH, "candidate_sha256": sha(candidate),
        "craft_sha256": sha(root / "mods/JACK_WastelandCraft/JACK_WastelandCraft.mod"),
        "records_before": len(original), "records_after": len(rows),
        "enabled_mods": len(enabled), "loaded_files": len(files),
        "changes": {sid: {"charges": [1.0, 2.0]} for sid in AMMO},
        "laser_damage_changes": LASER_DAMAGE,
        "all_other_fields_and_refs_unchanged": True,
        "byte_roundtrip_and_readback": True,
        "full_load_order_exact_seven_field_changes": True,
        "gauss_damage_magazines_speed_stack_recipes_unchanged": True,
        "old_save_existing_items_and_runtime_charge_use": "unverified",
        "gameplay": "unverified; player session not controlled",
    }
    (args.output / "validation.json").write_text(json.dumps(report, indent=2), "utf8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
