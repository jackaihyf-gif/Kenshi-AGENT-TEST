import ast
import copy
import hashlib
import json
import pathlib
import struct

G = pathlib.Path(r"D:\steam\steamapps\common\Kenshi")
output_dir = pathlib.Path(__file__).parent
rp = pathlib.Path(r"D:\JACK\kenshi_armour_audit\read_data.py")
tr = ast.parse(rp.read_text())
ns = {"struct": struct}
exec(
    compile(
        ast.Module(
            body=[x for x in tr.body if isinstance(x, (ast.ClassDef, ast.FunctionDef))],
            type_ignores=[],
        ),
        str(rp),
        "exec",
    ),
    ns,
)
Reader = ns["Reader"]
merge = ns["merge"]
wp = pathlib.Path(r"D:\JACK\KenshiArmorMod\research\storage_native_20261104\integrate_storage.py")
tr = ast.parse(wp.read_text())
ns2 = {"struct": struct}
exec(
    compile(
        ast.Module(
            body=[
                x
                for x in tr.body
                if isinstance(x, ast.FunctionDef) and x.name in ("uint", "string", "encode")
            ],
            type_ignores=[],
        ),
        str(wp),
        "exec",
    ),
    ns2,
)
encode = ns2["encode"]
source = G / "mods/JACK_WastelandCraft/JACK_WastelandCraft.mod"
energy = G / "mods/JACK_EnergyWeapons/JACK_EnergyWeapons.mod"
assert (
    hashlib.sha256(source.read_bytes()).hexdigest()
    == "75525fd1027535c0306913742aacfc0c88f7e2fa60b41dda615fc56a82602def"
)
assert (
    hashlib.sha256(energy.read_bytes()).hexdigest()
    == "e85dbe46581ff0d7f424d745d862a0394ec969914e1701675a09f05b279e3bb2"
)
files = {
    p.name: p for p in pathlib.Path(r"D:\steam\steamapps\workshop\content\233860").rglob("*.mod")
}
files.update({p.name: p for p in (G / "mods").rglob("*.mod")})
enabled = [
    n.strip()
    for n in (G / "data/mods.cfg").read_text(encoding="utf-8-sig").splitlines()
    if n.strip()
]
missing = [n for n in enabled if n not in files]
assert not missing, missing
paths = [
    G / "data" / n for n in ("gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod")
] + [files[n] for n in enabled]
db = {}
for p in paths:
    merge(db, list(Reader(p).records()), p.name)
targets = {f"{i}-JACK_WastelandCraft.mod" for i in (400, 410, 420, 430, 440, 450, 460)} | {
    f"{i}-JACK_EnergyWeapons.mod" for i in (100, 110, 200, 210)
}
refs = []
for r in db.values():
    for k, v in r["refs"].items():
        if "craft" in k:
            hit = sorted(set(v) & targets)
            if hit:
                refs.append((r["id"], k, hit))
print("craft references", refs)
assert all(x[0] == "110-JACK_WastelandCraft.mod" for x in refs), refs
original = list(Reader(source).records())
rows = copy.deepcopy(original)
d = {r["id"]: r for r in rows}
reader = Reader(source)
assert reader.val("i") == 16
reader.val("i")
for _ in range(4):
    reader.s()
reader.val("i")
prefix = reader.b[: reader.o]
assert encode(original, prefix) == source.read_bytes()
changes = []


def change(sid, key, old, new, typ):
    r = d[sid]
    assert r["field_types"][key] == typ and r["fields"][key] == old, (
        sid,
        key,
        r["fields"].get(key),
    )
    r["fields"][key] = new
    changes.append([sid, key, old, new])


change("110-JACK_WastelandCraft.mod", "production mult", 1.0, 2.0, 1)
for i, v in [(400, 6), (410, 6), (420, 3), (430, 8), (440, 8), (450, 1), (460, 1)]:
    change(f"{i}-JACK_WastelandCraft.mod", "production time", v, v * 2, 2)
for i, v in [(100, 12.0), (110, 14.0)]:
    change(f"{i}-JACK_EnergyWeapons.mod", "craft time hrs", v, v * 2, 1)
for r in original:
    if r["id"] in targets:
        eff = db[r["id"]]
        if r["id"].endswith("JACK_WastelandCraft.mod"):
            assert eff["fields"]["production time"] == r["fields"]["production time"]
        elif r["id"].startswith(("100-", "110-")):
            assert eff["fields"]["craft time hrs"] == r["fields"]["craft time hrs"]
        else:
            assert eff["fields"]["production time"] == 1
candidate = output_dir / "JACK_WastelandCraft.mod.candidate"
assert not candidate.exists()
candidate.write_bytes(encode(rows, prefix))
assert list(Reader(candidate).records()) == rows
expected = copy.deepcopy(original)
ed = {r["id"]: r for r in expected}
for sid, k, _old, new in changes:
    ed[sid]["fields"][k] = new
assert expected == rows
report = {
    "enabled_mod_count": len(enabled),
    "input_count": len(paths),
    "missing": missing,
    "craft_references": refs,
    "changes": changes,
    "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
    "static_only": (
        "Multiplier linearity, gun time application, a"
        "nd actual throughput/ingredients require in-g"
        "ame measurement; no deployment."
    ),
}
(output_dir / "validation.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
)
print(json.dumps(report, ensure_ascii=False))
