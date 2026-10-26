"""Read-only, bounded offline checks. Header checks are NOT OGRE compatibility tests."""

import json
import re
from pathlib import Path

from .models import CheckResult

MAX_MANIFEST_BYTES = 1024 * 1024


class AssetChecker:
    """Extension seam: add version-specific validators behind check_file later."""

    def check_file(self, path: Path) -> CheckResult:
        try:
            if not path.is_file():
                return CheckResult(str(path), "failed", "Asset file is missing", "asset_missing")
            size = path.stat().st_size
            if size == 0:
                return CheckResult(str(path), "failed", "Asset is empty", "asset_empty")
            if path.suffix.lower() not in {".mesh", ".skeleton"}:
                return CheckResult(str(path), "skipped", "No parser for this asset type",
                                   details={"size_bytes": size, "scope": "existence_only"})
            with path.open("rb") as stream:
                header = stream.read(2)
                if header not in (b"\x00\x10", b"\x10\x00"):
                    return CheckResult(str(path), "failed", "Invalid OGRE stream header",
                                       "invalid_ogre_header")
                version_bytes = stream.readline(256)
                if not version_bytes.endswith(b"\n"):
                    return CheckResult(str(path), "failed", "Missing or excessive version line",
                                       "invalid_ogre_version")
                try:
                    version = version_bytes[:-1].decode("ascii")
                except UnicodeDecodeError:
                    version = ""
                # Skeleton serializer uses [Serializer_v...] rather than MeshSerializer.
                prefix = "MeshSerializer" if path.suffix.lower() == ".mesh" else "Serializer"
                if not re.fullmatch(rf"\[{prefix}_v[0-9]+(?:\.[0-9]+)*\]", version):
                    return CheckResult(str(path), "failed", "Unexpected serializer version syntax",
                                       "invalid_ogre_version")
                if not stream.read(1):
                    return CheckResult(str(path), "failed", "Header has no payload",
                                       "missing_ogre_payload")
            return CheckResult(
                str(path), "passed", "Basic OGRE header and nonempty payload checks passed",
                details={"size_bytes": size, "serializer": version,
                         "endianness": "little" if header == b"\x00\x10" else "big",
                         "scope": "header_only", "payload_validated": False,
                         "compatibility": "unknown"},
            )
        except OSError as exc:
            return CheckResult(str(path), "error", str(exc), "asset_io_error")

    def check_manifest(self, path: Path) -> list[CheckResult]:
        """Project-defined JSON manifest, not Kenshi FCS / .mod data.

        References are explicit and relative to the manifest; they must stay within
        its directory, including symlink resolution. Binary dependencies aren't inferred.
        """
        try:
            with path.open("rb") as stream:
                raw = stream.read(MAX_MANIFEST_BYTES + 1)
            if len(raw) > MAX_MANIFEST_BYTES:
                raise ValueError("Manifest exceeds 1 MiB")
            data = json.loads(raw)
            if not isinstance(data, dict) or set(data) != {"schema_version", "assets"}:
                raise ValueError("Expected schema_version and assets only")
            if type(data["schema_version"]) is not int or data["schema_version"] != 1:
                raise ValueError("schema_version must be 1")
            if not isinstance(data["assets"], list) or not data["assets"]:
                raise ValueError("assets must be a nonempty array")
            results = []
            base = path.parent.resolve()
            seen = set()
            for entry in data["assets"]:
                if not isinstance(entry, dict) or set(entry) - {"path", "references"}:
                    raise ValueError("Each asset allows only path and references")
                asset = self._reference(entry.get("path"), base)
                if asset in seen:
                    raise ValueError(f"Duplicate asset: {entry['path']}")
                seen.add(asset)
                results.append(self.check_file(asset))
                refs = entry.get("references", [])
                if not isinstance(refs, list):
                    raise ValueError("references must be an array")
                for ref in refs:
                    target = self._reference(ref, base)
                    present = target.is_file() and target.stat().st_size > 0
                    results.append(CheckResult(
                        f"{entry['path']} -> {ref}", "passed" if present else "failed",
                        "Declared reference exists and is nonempty" if present
                        else "Declared reference is missing or empty",
                        None if present else "reference_missing",
                        details={"scope": "declared_reference_existence_only"},
                    ))
            return results
        except (OSError, ValueError, RecursionError) as exc:
            return [CheckResult(str(path), "failed", f"Invalid asset manifest: {exc}",
                                "invalid_manifest")]

    @staticmethod
    def _reference(value: object, base: Path) -> Path:
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise ValueError("Asset references must be nonempty relative paths")
        # One portable spelling across Windows and Linux; no drive or UNC paths.
        if "\\" in value or ":" in value or Path(value).is_absolute():
            raise ValueError("Use forward-slash relative paths in manifests")
        result = (base / value).resolve()
        if not result.is_relative_to(base):
            raise ValueError("Asset reference escapes manifest directory")
        return result
