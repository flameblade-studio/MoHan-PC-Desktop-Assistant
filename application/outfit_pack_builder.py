from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import zipfile
lazy from pathlib import Path

lazy from domain.outfit_pack import (
    MANIFEST,
    OutfitPackError,
    inspect_outfit_pack,
)
lazy from domain.outfit_pack_assets import validated_asset_dimensions
lazy from domain.outfit_pack_makeup import verify_makeup_layers


def _asset_entries(value: object) -> tuple[dict[str, object], ...]:
    found: list[dict[str, object]] = []
    if isinstance(value, dict):
        if "path" in value and "slot" in value:
            found.append(value)
        for child in value.values():
            found.extend(_asset_entries(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_asset_entries(child))
    return tuple(found)


def _asset_bytes(asset_root: Path, archive_path: str) -> bytes:
    relative = Path(*archive_path.split("/"))
    source = (asset_root / relative).resolve()
    root = asset_root.resolve()
    try:
        source.relative_to(root)
    except ValueError:
        raise OutfitPackError("Outfit asset escapes its source directory.") from None
    if not source.is_file():
        raise OutfitPackError(f"Missing outfit asset: {archive_path}")
    return source.read_bytes()


def _sealed_manifest(
    source_manifest: Path,
    asset_root: Path,
) -> tuple[dict[str, object], dict[str, bytes]]:
    try:
        manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise OutfitPackError("Invalid UTF-8 outfit authoring manifest.") from None
    if not isinstance(manifest, dict):
        raise OutfitPackError("Outfit authoring manifest must be an object.")
    assets: dict[str, bytes] = {}
    for entry in _asset_entries(manifest):
        path = entry.get("path")
        if not isinstance(path, str):
            raise OutfitPackError("Every outfit asset requires a path.")
        data = assets.setdefault(path, _asset_bytes(asset_root, path))
        width, height = validated_asset_dimensions(path, data)
        entry["sha256"] = hashlib.sha256(data).hexdigest()
        entry["width"] = width
        entry["height"] = height
    return manifest, assets


def _write_deterministic_archive(
    output: Path,
    manifest: dict[str, object],
    assets: dict[str, bytes],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.building")
    if temporary.exists():
        raise OutfitPackError("A prior outfit build has not completed safely.")
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            members = {
                MANIFEST: json.dumps(
                    manifest,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ).encode("utf-8"),
                **assets,
            }
            for name in sorted(members):
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, members[name])
        inspect_outfit_pack(temporary)
        # A sealed pack must already pass the makeup pixel gate the importer applies.
        verify_makeup_layers(temporary)
        os.replace(temporary, output)
    except BaseException:
        if temporary.is_file():
            temporary.unlink()
        raise


def build_outfit_pack(
    source_manifest: Path,
    asset_root: Path,
    output: Path,
) -> Path:
    """Seal, validate and atomically create one complete v2 outfit pack."""

    output = Path(output)
    if output.suffix != ".mohan-outfit":
        raise OutfitPackError("The output must use the .mohan-outfit extension.")
    if output.exists():
        raise OutfitPackError("Refusing to overwrite an existing outfit pack.")
    manifest, assets = _sealed_manifest(Path(source_manifest), Path(asset_root))
    _write_deterministic_archive(output, manifest, assets)
    return output
