from __future__ import annotations

lazy from dataclasses import dataclass
lazy from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppearanceAsset:
    slot: str
    path: str
    sha256: str
    width: int
    height: int
    anchor_x: int
    anchor_y: int
    z_order: int
    occludes_makeup: bool = False


@dataclass(frozen=True, slots=True)
class AppearanceVariant:
    variant_id: str
    display_names: frozendict[str, str]
    poses: frozendict[str, tuple[AppearanceAsset, ...]]
    fabric_behavior: str | None = None
    body_visibility: frozendict[str, frozendict[str, str]] | None = None
    face_masks: frozendict[str, str] | None = None
    hand_rules: frozendict[str, str] | None = None
    garment_rules: frozendict[str, str] | None = None
    placements: frozendict[str, str] | None = None
    hair_rules: frozendict[str, str] | None = None
    attachment_contracts: frozendict[str, str] | None = None
    intensity: float = 1.0
    eye_states: frozendict[str, frozendict[str, tuple[AppearanceAsset, ...]]] = frozendict()
    foundation_silhouettes: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class AppearanceItem:
    category: str
    item_id: str
    display_names: frozendict[str, str]
    variants: tuple[AppearanceVariant, ...]
    attachment_point: str | None = None
    safe_mask: str | None = None


@dataclass(frozen=True, slots=True)
class OutfitPack:
    pack_id: str
    pack_version: str
    app_range: str
    display_names: frozendict[str, str]
    source_kind: str
    author: str
    license_name: str
    compatible_body_profile: str
    items: tuple[AppearanceItem, ...]
    ensembles: tuple[AppearanceEnsemble, ...]

    @property
    def looks(self) -> tuple[AppearanceItem, ...]:
        return tuple(item for item in self.items if item.category == "garment")


@dataclass(frozen=True, slots=True)
class InstalledSelection:
    category: str
    pack_id: str
    item_id: str
    variant_id: str
    pack_display_names: frozendict[str, str]
    item_display_names: frozendict[str, str]
    variant_display_names: frozendict[str, str]


@dataclass(frozen=True, slots=True)
class EnsembleSelection:
    category: str
    item_id: str | None
    variant_id: str | None


@dataclass(frozen=True, slots=True)
class AutonomousStyleProfile:
    thermal_bands: frozenset[str]
    weather: frozenset[str]
    moods: frozenset[str]
    occasions: frozenset[str]
    priority: int


@dataclass(frozen=True, slots=True)
class AppearanceEnsemble:
    ensemble_id: str
    display_names: frozendict[str, str]
    selections: tuple[EnsembleSelection, ...]
    autonomous_profile: AutonomousStyleProfile


@dataclass(frozen=True, slots=True)
class InstalledEnsemble:
    pack_id: str
    ensemble_id: str
    pack_display_names: frozendict[str, str]
    ensemble_display_names: frozendict[str, str]
    selections: tuple[EnsembleSelection, ...]
    autonomous_profile: AutonomousStyleProfile


@dataclass(frozen=True, slots=True)
class RemovalResult:
    pack_id: str
    removed_path: Path


@dataclass(frozen=True, slots=True)
class SelectionResolution:
    category: str
    status: str
    requested_pack_id: str
    requested_item_id: str
    requested_variant_id: str
    effective_pack_id: str
    effective_item_id: str
    effective_variant_id: str


@dataclass(frozen=True, slots=True)
class PoseAppearanceResolution:
    requested_view_id: str
    resolved_silhouette: str | None
    assets: tuple[AppearanceAsset, ...]
    exact_pose_atlas_match: bool
