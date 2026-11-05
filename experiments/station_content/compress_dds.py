import hashlib
import json
import math
import struct
from pathlib import Path

from PIL import Image, ImageChops, __version__

p = Path("D:\\JACK\\KenshiArmorMod\\research\\station_candidate_20261103")
o = p / "optimized"
assert not o.exists()
o.mkdir()
results = {}
for name, fmt in [("station_d", "DXT5"), ("station_n", "DXT5"), ("station_m", "DXT1")]:
    src = p / (name + ".dds")
    dst = o / (name + ".dds")
    image = Image.open(src).convert("RGBA")
    alpha = image.getchannel("A").getextrema()
    assert fmt != "DXT1" or alpha == (255, 255)
    image.save(dst, format="DDS", pixel_format=fmt)
    data = dst.read_bytes()
    assert data[:4] == b"DDS " and data[84:88].decode() == fmt
    mip = struct.unpack_from("<I", data, 28)[0]
    assert mip == 0
    decoded = Image.open(dst).convert("RGBA")
    assert image.size == decoded.size == (2048, 2048)
    diff = ImageChops.difference(image, decoded)
    channels = {}
    for channel, band in zip("RGBA", diff.split(), strict=False):
        hist = band.histogram()
        count = sum(hist)
        channels[channel] = {
            "mean_absolute": sum(i * n for i, n in enumerate(hist)) / count,
            "rmse": math.sqrt(sum(i * i * n for i, n in enumerate(hist)) / count),
            "maximum": max(i for i, n in enumerate(hist) if n),
        }
    results[name] = {
        "format": fmt,
        "dimensions": list(image.size),
        "source_bytes": src.stat().st_size,
        "compressed_bytes": len(data),
        "mipmap_count_header": mip,
        "source_alpha_extrema": list(alpha),
        "decoded_error_8bit": channels,
        "sha256": hashlib.sha256(data).hexdigest(),
    }
(o / "compression_audit.json").write_text(
    json.dumps(
        {
            "pillow_version": __version__,
            "method": (
                "Pillow DDS BCn encoder; decoded absolute byte"
                " errors against uncompressed originals"
            ),
            "mipmaps": "not generated",
            "textures": results,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps(results, indent=2))
