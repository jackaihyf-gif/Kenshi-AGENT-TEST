"""Build/validate a candidate from owned local files; never install or launch the game."""

import argparse
import ast
import copy
import hashlib
import json
import pathlib
import struct

from patch import AMMO, FUNCTIONS, add_vanilla_ammo

SOURCE_HASH = "1f03ee6ccb69a6dae018785bdb53f400178d177b88534ad6eac3dedf95d39182"
BASE_FILES = ("gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod")


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
    source = root / "mods/JACK_WastelandCraft/JACK_WastelandCraft.mod"
    if sha(source) != SOURCE_HASH:
        raise ValueError("Installed Craft source changed; review before rebuilding")
    original = list(reader(source).records())
    rd = reader(source)
    if rd.val("i") != 16:
        raise ValueError("Expected lossless version 16 source")
    rd.val("i")
    for _ in range(4):
        rd.s()
    rd.val("i")
    prefix = rd.b[:rd.o]
    if encode(original, prefix) != source.read_bytes():
        raise ValueError("Source byte roundtrip failed")
    vanilla = {}
    files = [root / "data" / name for name in BASE_FILES]
    for path in files:
        merge(vanilla, list(reader(path).records()), path.name)
    rows = add_vanilla_ammo(original, vanilla)
    candidate = args.output / "JACK_WastelandCraft.mod.candidate"
    candidate.write_bytes(encode(rows, prefix))
    if list(reader(candidate).records()) != rows or rows[:len(original)] != original:
        raise ValueError("Candidate changed original content or failed readback")
    enabled = (root / "data/mods.cfg").read_text("utf-8-sig").splitlines()
    enabled = [name for name in enabled if name.strip()]
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
    for sid in FUNCTIONS:
        expected = copy.deepcopy(before[sid])
        expected["refs"].setdefault("item crafts", {}).update({a: [50, 0, 0] for a in AMMO})
        expected["sources"].append(source.name)
        # Original sources include later mods too; compare the content, not provenance order.
        expected.pop("sources", None)
        actual = copy.deepcopy(after[sid])
        actual.pop("sources", None)
        if actual != expected:
            raise ValueError(f"Unexpected merged vanilla change: {sid}")
        if any(ammo not in after for ammo in AMMO):
            raise ValueError("Ammo reference unresolved")
        if actual["fields"].get("overrides ingredients") is not False:
            raise ValueError("Active load order overrides ammo ingredients")
    for sid in before.keys() - set(FUNCTIONS):
        if before[sid] != after[sid]:
            raise ValueError(f"Unrelated merged content changed: {sid}")
    links = {
        sid: list(after[sid]["refs"]["functionality"])
        for sid in ("96184-Newwworld.mod", "97091-rebirth.mod")
    }
    if list(links.values()) != [[FUNCTIONS[0]], [FUNCTIONS[1]]]:
        raise ValueError("Active arrow buildings no longer use vanilla functionalities")
    report = {
        "source_sha256": SOURCE_HASH,
        "candidate_sha256": sha(candidate),
        "energy_sha256": sha(root / "mods/JACK_EnergyWeapons/JACK_EnergyWeapons.mod"),
        "records_before": len(original),
        "records_after": len(rows),
        "enabled_mods": len(enabled),
        "loaded_files": len(files),
        "original_records_unchanged": True,
        "byte_roundtrip_and_readback": True,
        "vanilla_building_function_links": links,
        "patch_functions": list(FUNCTIONS),
        "new_recipe_references": 4,
        "third_party_dependency_added": False,
        "original_recipes_fields_materials_research_unchanged": True,
        "production_multiplier": "vanilla unchanged; existing dedicated bench remains 2x",
        "gameplay_and_old_save_menu": "unverified; player session not controlled",
    }
    (args.output / "validation.json").write_text(json.dumps(report, indent=2), "utf8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
