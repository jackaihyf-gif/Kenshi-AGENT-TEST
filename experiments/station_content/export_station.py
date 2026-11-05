import hashlib
import json
import sys
import types
from pathlib import Path

import bpy

p = Path("D:/JACK/KenshiArmorMod")
o = p / "research/station_candidate_20261103"
src = p / "construct/Meshy_AI_Aircraft_Maintenance__1027112231_texture.glb"
assert (
    hashlib.sha256(src.read_bytes()).hexdigest()
    == "49716ad9ed9be1ebbb3aebe994947c50d17c5d2b7f3fa15922d2a74e0c059e58"
)
sys.path.insert(0, str(p / "tools/native"))
m = types.ModuleType("station_addon")
m.__path__ = [str(p / "tools/kenshi_io_blender-main/4.4")]
sys.modules["station_addon"] = m


def _load_station_addon():
    from station_addon import ogre_exporter

    return ogre_exporter


ogre_exporter = _load_station_addon()


class Op:
    def report(self, *a):
        print(*a)


bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(src))
ob = next(x for x in bpy.context.scene.objects if x.type == "MESH")
ob.data.transform(ob.matrix_world)
ob.matrix_world.identity()
pts = [v.co for v in ob.data.vertices]
mn = [min(v[i] for v in pts) for i in range(3)]
mx = [max(v[i] for v in pts) for i in range(3)]
t = json.loads((o / "t60_measurement.json").read_text())
height = t["dimensions_xyz"][2]
scale = 1.2 * height / (mx[2] - mn[2])
for v in ob.data.vertices:
    v.co = (
        (v.co.x - (mn[0] + mx[0]) / 2) * scale,
        (v.co.y - (mn[1] + mx[1]) / 2) * scale,
        (v.co.z - mn[2]) * scale,
    )
ob.name = "jack_station_candidate"
ob.data.materials[0].name = "JACK_Station_Candidate"
bpy.ops.object.select_all(action="DESELECT")
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
mesh = o / "jack_station_candidate.mesh"
assert not mesh.exists()
assert ogre_exporter.save(
    Op(), bpy.context, str(mesh), tangent_format="FLIPPED", export_skeleton=False
) == {"FINISHED"}
pts = [v.co for v in ob.data.vertices]
b = [[min(v[i] for v in pts) for i in range(3)], [max(v[i] for v in pts) for i in range(3)]]
report = {
    "t60_reference_height": height,
    "t60_reference_full_width": t["dimensions_xyz"][0],
    "scale": scale,
    "bounds_blender_xyz": b,
    "dimensions_xyz": [b[1][i] - b[0][i] for i in range(3)],
    "triangles": sum(len(f.vertices) - 2 for f in ob.data.polygons),
    "note": (
        "1.2x T60 rest-mesh bbox height; full width is"
        " not shoulder measurement; interior clearance"
        " and gameplay unverified"
    ),
}
(o / "export_measurement.json").write_text(json.dumps(report, indent=2))
print("STATION_EXPORT", report)
