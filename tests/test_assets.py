import json

import pytest

from kenshi_test.assets import MAX_MANIFEST_BYTES, AssetChecker


@pytest.mark.parametrize(("suffix", "version"), [
    (".mesh", "[MeshSerializer_v1.8]"), (".skeleton", "[Serializer_v1.80]"),
])
@pytest.mark.parametrize("header", [b"\x00\x10", b"\x10\x00"])
def test_synthetic_headers_only(tmp_path, suffix, version, header):
    asset = tmp_path / f"synthetic{suffix}"
    content = header + version.encode() + b"\nnot a real mesh or skeleton"
    asset.write_bytes(content)
    result = AssetChecker().check_file(asset)
    assert result.status == "passed"
    assert result.details["scope"] == "header_only"
    assert result.details["payload_validated"] is False
    assert result.details["compatibility"] == "unknown"
    assert asset.read_bytes() == content


@pytest.mark.parametrize(("content", "code"), [
    (b"", "asset_empty"), (b"bad", "invalid_ogre_header"),
    (b"\x00\x10[MeshSerializer_v1.8]", "invalid_ogre_version"),
    (b"\x00\x10[Serializer_v1.8]\npayload", "invalid_ogre_version"),
    (b"\x00\x10\xff\nbody", "invalid_ogre_version"),
    (b"\x00\x10" + b"X" * 300 + b"\nbody", "invalid_ogre_version"),
    (b"\x00\x10[MeshSerializer_v1.8]\n", "missing_ogre_payload"),
])
def test_malformed_assets(tmp_path, content, code):
    path = tmp_path / "invalid.mesh"
    path.write_bytes(content)
    result = AssetChecker().check_file(path)
    assert result.status == "failed"
    assert result.error_code == code


def test_missing_and_unsupported_assets(tmp_path):
    checker = AssetChecker()
    assert checker.check_file(tmp_path / "missing.mesh").error_code == "asset_missing"
    opaque = tmp_path / "opaque.mod"
    opaque.write_bytes(b"synthetic opaque data")
    assert checker.check_file(opaque).status == "skipped"


def test_manifest_dependencies(tmp_path):
    (tmp_path / "a.mesh").write_bytes(b"\x00\x10[MeshSerializer_v1.8]\nsynthetic")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "assets": [
        {"path": "a.mesh", "references": ["missing.skeleton", "material.material"]}
    ]}), encoding="utf-8")
    (tmp_path / "material.material").write_text("synthetic", encoding="utf-8")
    results = AssetChecker().check_manifest(manifest)
    assert [r.status for r in results] == ["passed", "failed", "passed"]
    assert results[1].error_code == "reference_missing"


@pytest.mark.parametrize("value", [
    "../outside.mesh", "/absolute.mesh", "D:/model.mesh", "a\\b", "",
])
def test_manifest_paths_stay_portable_and_contained(tmp_path, value):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "assets": [{"path": value}]}), "utf-8")
    result = AssetChecker().check_manifest(manifest)[0]
    assert result.error_code == "invalid_manifest"


@pytest.mark.parametrize("data", [
    [], {}, {"schema_version": True, "assets": []}, {"schema_version": 1, "assets": []},
    {"schema_version": 1, "assets": [3]},
    {"schema_version": 1, "assets": [{"path": "a.mesh", "references": "oops"}]},
    {"schema_version": 1, "assets": [{"path": "a.mesh"}, {"path": "a.mesh"}]},
])
def test_invalid_manifest_schema(tmp_path, data):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert AssetChecker().check_manifest(path)[0].error_code == "invalid_manifest"


def test_large_and_malformed_manifest(tmp_path):
    path = tmp_path / "manifest.json"
    for raw in (b"x" * (MAX_MANIFEST_BYTES + 1), b"{", b"\xff"):
        path.write_bytes(raw)
        assert AssetChecker().check_manifest(path)[0].error_code == "invalid_manifest"
