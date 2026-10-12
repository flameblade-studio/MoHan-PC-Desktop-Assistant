"""Config-driven inventory construction with no product path assumptions."""

from __future__ import annotations

lazy import json
lazy from collections import Counter
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path, PurePosixPath

lazy from huapu.hashing import digest_file
lazy from huapu.schema import SchemaVersion

_EXACT_CHARACTER_ASSET_CATEGORIES = {
    "LICENSE.md": "character_license_notice",
    "appearance/defaults.json": "character_appearance_defaults",
    "persona/ui-identifiers.json": "character_ui_identifier_data",
    "dialogue/runtime.json": "character_runtime_dialogue_data",
    "rig/runtime-bindings.json": "character_runtime_binding_data",
}
_PREFIX_CHARACTER_ASSET_CATEGORIES = (
    ("persona/", "character_persona_data"),
    ("dialogue/", "character_dialogue_data"),
    ("voice/", "character_voice_data"),
    ("rig/", "character_rig_data"),
    ("expressions/", "character_expression_catalog"),
)


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


def classify_character_asset_path(
    path: str,
    *,
    characters_root: str,
) -> str | None:
    """Return the neutral category for one configured character-data path."""
    candidate = PurePosixPath(path)
    root = PurePosixPath(characters_root)
    if (
        candidate.is_absolute()
        or root.is_absolute()
        or "\\" in path
        or "\\" in characters_root
        or not candidate.parts
        or not root.parts
        or candidate.as_posix() != path
        or root.as_posix() != characters_root
        or any(part in {"", ".", ".."} for part in (*candidate.parts, *root.parts))
    ):
        raise ValueError("character asset paths must be canonical relative POSIX paths")
    root_size = len(root.parts)
    if (
        candidate.parts[:root_size] != root.parts
        or len(candidate.parts) < root_size + 2
    ):
        return None
    relative = "/".join(candidate.parts[root_size + 1 :])
    exact = _EXACT_CHARACTER_ASSET_CATEGORIES.get(relative)
    if exact is not None:
        return exact
    for prefix, category in _PREFIX_CHARACTER_ASSET_CATEGORIES:
        if relative.startswith(prefix):
            return category
    return None


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


def build_owned_character_inventory(
    inventory: Mapping[str, object],
    *,
    profile: str,
    prefix: str,
    purpose: str,
) -> dict[str, object]:
    """Select a release index by the caller's exclusive character namespace."""
    rows = [row for row in inventory["files"] if row["path"].startswith(prefix)]
    return {
        "schema": "flameblade.character-pack-inventory.v1",
        "schema_version": 1,
        "profile": profile,
        "purpose": purpose,
        "scope_counts": dict(sorted(Counter(row["scope"] for row in rows).items())),
        "files": rows,
    }


def build_character_inventory_with_makeup_dependencies(
    inventory: Mapping[str, object], *, repo_root: Path, source: Mapping[str, object],
    profile: str, prefix: str, regions_path: str, purpose: str,
) -> dict[str, object]:
    """Select owned files and the source's declared makeup safety dependencies."""
    selected = build_owned_character_inventory(
        inventory, profile=profile, prefix=prefix, purpose=purpose,
    )
    makeup_paths: set[str] = set()
    for field in ("components", "approval_refs", "source_refs"):
        makeup_paths.update(row["path"] for row in source[field] if "makeup" in row["path"])
    if regions_path in makeup_paths:
        regions = json.loads((repo_root / regions_path).read_text(encoding="utf-8"))
        for region in regions["silhouettes"].values():
            for field in ("foundation_masks", "eye_aperture_masks"):
                makeup_paths.update(row["path"] for row in region.get(field, {}).values())
            for layer in (
                "iris_left", "iris_right", "eyelid_left", "eyelid_right",
                "oral_cavity", "teeth_tongue", "lip_upper", "lip_lower",
            ):
                path = f"{region['rig']}_{layer}.png"
                if (repo_root / path).is_file():
                    makeup_paths.add(path)
    shared = [
        {**row, "scope": "runtime_data",
         "reason": "Declared runtime makeup component, approval or safety dependency."}
        for row in inventory["files"] if row["path"] in makeup_paths
    ]
    selected["files"] = sorted([*selected["files"], *shared], key=lambda row: row["path"])
    selected["scope_counts"] = dict(sorted(Counter(row["scope"] for row in selected["files"]).items()))
    return selected


def build_lin_keyun_release_inventory(
    inventory: dict[str, object], repo_root: Path,
) -> dict[str, object]:
    """Select Lin Keyun files and the declared shared makeup support assets."""
    source = json.loads(
        (repo_root / "assets/characters/lin-keyun/pack-source.json").read_text(encoding="utf-8")
    )
    return build_character_inventory_with_makeup_dependencies(
        inventory, repo_root=repo_root, source=source,
        profile="lin-keyun", prefix="assets/characters/lin-keyun/",
        regions_path="assets/makeup-safe-regions.json",
        purpose=(
            "Release payload inventory includes Lin Keyun-owned files and declared "
            "shared makeup dependencies; shared full-frame assets are excluded."
        ),
    )


def render_lin_keyun_release_inventory(inventory: dict[str, object], repo_root: Path) -> str:
    """Serialize the dedicated Lin Keyun release inventory deterministically."""
    return json.dumps(
        build_lin_keyun_release_inventory(inventory, repo_root),
        ensure_ascii=False, sort_keys=True, indent=2,
    ) + "\n"
