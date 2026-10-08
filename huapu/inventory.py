"""Config-driven inventory construction with no product path assumptions."""

from __future__ import annotations

lazy import json
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from huapu.hashing import digest_file
lazy from huapu.schema import SchemaVersion


@dataclass(frozen=True, slots=True)
class AssetInventoryConfig:
    """Identity and extension policy for one character inventory."""

    schema: SchemaVersion
    character_id: str
    media_types: Mapping[str, str]

    def __post_init__(self) -> None:
        if not self.character_id or self.character_id != self.character_id.strip():
            raise ValueError("character_id must be non-empty trimmed text")
        if not self.media_types:
            raise ValueError("media_types must not be empty")
        if any(not suffix.startswith(".") or not media_type for suffix, media_type in self.media_types.items()):
            raise ValueError("media_types requires non-empty dotted suffix mappings")


@dataclass(frozen=True, slots=True)
class AssetSpec:
    """Config-owned classification for one package-relative asset."""

    path: str
    category: str
    scope: str
    reader: str | None = None

    def __post_init__(self) -> None:
        for label, value in (("category", self.category), ("scope", self.scope)):
            if not value or value != value.strip():
                raise ValueError(f"asset {label} must be non-empty trimmed text")


def build_asset_inventory(
    root: Path,
    config: AssetInventoryConfig,
    assets: Sequence[AssetSpec],
) -> dict[str, object]:
    """Measure exactly the assets named by caller-owned character settings."""
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for asset in sorted(assets, key=lambda item: item.path):
        measured = digest_file(root, asset.path)
        if measured.path in seen:
            raise ValueError(f"inventory repeats an asset path: {measured.path}")
        seen.add(measured.path)
        suffix = Path(measured.path).suffix.lower()
        media_type = config.media_types.get(suffix)
        if media_type is None:
            raise ValueError(f"inventory has no media type for: {measured.path}")
        row = {
            **measured.to_document(),
            "media_type": media_type,
            "category": asset.category,
            "scope": asset.scope,
        }
        if asset.reader is not None:
            row["reader"] = asset.reader
        rows.append(row)
    return {
        "schema": config.schema.name,
        "schema_version": config.schema.version,
        "character_id": config.character_id,
        "files": rows,
    }


def render_asset_inventory(inventory: Mapping[str, object]) -> str:
    """Render a deterministic UTF-8 JSON inventory with a trailing LF."""
    return json.dumps(
        inventory,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    ) + "\n"
