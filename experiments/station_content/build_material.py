import io
import json
import struct
from pathlib import Path

from PIL import Image, ImageOps

p = Path("D:/JACK/KenshiArmorMod")
o = p / "research/station_candidate_20261103"
src = p / ("construct/Meshy_AI_Aircraft_Maintenance__1027112231_texture.glb")
raw = src.read_bytes()
n = struct.unpack_from("<I", raw, 12)[0]
d = json.loads(raw[20 : 20 + n])
offset = 20 + n
bn = struct.unpack_from("<I", raw, offset)[0]
binary = raw[offset + 8 : offset + 8 + bn]
imgs = []
for im in d["images"]:
    v = d["bufferViews"][im["bufferView"]]
    s = v.get("byteOffset", 0)
    imgs.append(Image.open(io.BytesIO(binary[s : s + v["byteLength"]])).convert("RGB"))
mat = d["materials"][0]
tex = d["textures"]
pbr = mat["pbrMetallicRoughness"]
color = imgs[tex[pbr["baseColorTexture"]["index"]]["source"]].copy()
orm = imgs[tex[pbr["metallicRoughnessTexture"]["index"]]["source"]]
normal = imgs[tex[mat["normalTexture"]["index"]]["source"]]
color.putalpha(ImageOps.invert(orm.getchannel("G")))
normal = Image.merge(
    "RGBA",
    (
        normal.getchannel("R"),
        ImageOps.invert(normal.getchannel("G")),
        normal.getchannel("B"),
        Image.new("L", normal.size, 255),
    ),
)
metal = Image.merge("RGBA", (orm.getchannel("B"),) * 3 + (Image.new("L", orm.size, 255),))
for name, im in [("station_d", color), ("station_n", normal), ("station_m", metal)]:
    f = o / (name + ".dds")
    assert not f.exists()
    im.save(f, format="DDS")
    assert Image.open(f).size == (2048, 2048)
(o / "jack_station_candidate.material").write_text(
    "material JACK_Station_Candidate\n{\n technique\n"
    " {\n  shadow_caster_material standardShadowCas"
    "ter\n  pass\n  {\n   vertex_program_ref Object_V"
    "P {}\n   fragment_program_ref Object_FP {}\n   "
    "cull_hardware none\n   cull_software none\n   t"
    "exture_unit diffuseMap { texture station_d.dd"
    "s }\n   texture_unit normalMap { texture stati"
    "on_n.dds }\n   texture_unit metalnessMap { tex"
    "ture station_m.dds }\n  }\n }\n}\n"
)
print("TEXTURES_CREATED")
