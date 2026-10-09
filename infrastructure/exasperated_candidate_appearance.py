"""Native garment and state-specific cosmetics for the approved portrait."""

from __future__ import annotations

lazy import json
lazy from dataclasses import dataclass, field
lazy from itertools import product
lazy from math import isfinite
lazy from pathlib import Path

lazy from PySide6.QtGui import QPainter, QPixmap

lazy from domain.companion_animation_contract import outfit_silhouette
lazy from domain.constants import CHARACTER_EXPRESSION_ROLES
lazy from domain.outfit_pack import OFFICIAL_PACK_ROOT, FOUNDATION_SLOT, resolve_active_selection
lazy from domain.outfit_pack_makeup import read_makeup_intensity, read_makeup_slot_intensities
lazy from domain import outfit_pack_official
lazy from domain.qt_image_io import load_pixmap_png
lazy from infrastructure.exasperated_candidate_assets import (
    APPROVED_SOURCE_SHA256,
    DIMENSION,
    EXPRESSION_VARIANTS,
    validate_candidate_png,
)

# Resolve the official identities now: tests reach them through a lazily imported
# module object, and a lazily bound name there would surface as an unresolved proxy.
BUILTIN_MAKEUP_PACK_ID = outfit_pack_official.BUILTIN_MAKEUP_PACK_ID
BUILTIN_MAKEUP_VARIANTS = outfit_pack_official.BUILTIN_MAKEUP_VARIANTS
OFFICIAL_OUTFIT_PACK_ID = outfit_pack_official.OFFICIAL_OUTFIT_PACK_ID

SCHEMA = "mohan.exasperated-candidate-appearance.v1"
FOUNDATION_SCHEMA = "mohan.exasperated-candidate-appearance.v2"
VARIANT_SCHEMA = "mohan.exasperated-candidate-appearance.v3"
STATES = ("rest", "mid", "open", "round")
SLOTS = ("eyes", "cheeks", "lips")
SLOTS_V2 = (FOUNDATION_SLOT, *SLOTS)
LOOK_VARIANTS = BUILTIN_MAKEUP_VARIANTS
REQUIRED_LOOK_VARIANTS = ("classic", "light")
SUPPORTED_LOOK_VARIANTS = frozenset(BUILTIN_MAKEUP_VARIANTS)
LIGHT_VARIANT_OPACITY = 0.55
_EXASPERATED_EXPRESSION = CHARACTER_EXPRESSION_ROLES["exasperation"]
_EXASPERATED_SILHOUETTE = outfit_silhouette(_EXASPERATED_EXPRESSION, "front")


@dataclass(slots=True)
class ExasperatedCandidateAppearance:
    """Keep clothing removable and cosmetics tied to the currently painted mouth."""

    layers: dict[str, bytes]
    garment_enabled: bool = True
    makeup_intensities: dict[str, float] = field(default_factory=dict)
    store: Path | None = None
    official_pack_root: Path = OFFICIAL_PACK_ROOT
    schema: str = SCHEMA
    cosmetic_slots: tuple[str, ...] = SLOTS
    look_variants: tuple[str, ...] = LOOK_VARIANTS
    _pixmaps: dict[str, QPixmap] = field(default_factory=dict, init=False, repr=False)
    _selected_variant: str | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.makeup_intensities:
            self.makeup_intensities = dict.fromkeys(self.cosmetic_slots, 0.0)
        if self.schema == VARIANT_SCHEMA:
            self._selected_variant = self.look_variants[0]

    @classmethod
    def load(
        cls, root: Path, *, official_pack_root: Path = OFFICIAL_PACK_ROOT,
    ) -> ExasperatedCandidateAppearance:
        root = Path(root)
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("Appearance must bind the approved exasperated source.")
        schema = manifest.get("schema")
        if schema not in {SCHEMA, FOUNDATION_SCHEMA, VARIANT_SCHEMA}:
            raise ValueError("Appearance must bind the approved exasperated source.")
        if manifest.get("source_sha256") != APPROVED_SOURCE_SHA256:
            raise ValueError("Appearance must bind the approved exasperated source.")
        if schema == VARIANT_SCHEMA:
            raw_variants = manifest.get("variants")
            if not isinstance(raw_variants, list) or any(
                not isinstance(variant, str) for variant in raw_variants
            ):
                raise ValueError("Appearance requires the classic and light variants.")
            declared_variants = tuple(
                variant for variant in raw_variants if isinstance(variant, str)
            )
            if (
                len(declared_variants) != len(set(declared_variants))
                or not set(REQUIRED_LOOK_VARIANTS).issubset(declared_variants)
                or not set(declared_variants).issubset(SUPPORTED_LOOK_VARIANTS)
            ):
                raise ValueError("Appearance requires the classic and light variants.")
            cosmetic_slots = SLOTS_V2
        else:
            declared_variants = LOOK_VARIANTS
            cosmetic_slots = SLOTS_V2 if schema == FOUNDATION_SCHEMA else SLOTS
        records = manifest.get("layers")
        required = {"garment", "replace_mask"}
        if schema == VARIANT_SCHEMA:
            required |= {
                f"{variant}/{state}/{slot}"
                for variant, state, slot in product(declared_variants, STATES, cosmetic_slots)
            }
        elif schema == FOUNDATION_SCHEMA or manifest.get("cosmetic_status") != "not_approved":
            required |= {f"{state}/{slot}" for state, slot in product(STATES, cosmetic_slots)}
        if not isinstance(records, dict) or set(records) != required:
            raise ValueError("Appearance requires clothing and all mouth-specific cosmetics.")
        layers = {
            name: validate_candidate_png(root, records[name], f"{name}.rgba.png")
            for name in sorted(required)
        }
        return cls(
            layers,
            official_pack_root=official_pack_root,
            schema=schema,
            cosmetic_slots=cosmetic_slots,
            look_variants=declared_variants,
            makeup_intensities=dict.fromkeys(cosmetic_slots, 0.0),
        )

    @property
    def cosmetics_available(self) -> bool:
        if self.schema == VARIANT_SCHEMA:
            return all(
                f"{variant}/{state}/{slot}" in self.layers
                for variant in self.look_variants
                for state in STATES
                for slot in self.cosmetic_slots
            )
        return all(
            f"{state}/{slot}" in self.layers
            for state in STATES
            for slot in self.cosmetic_slots
        )

    def set_makeup_intensities(self, values: dict[str, float]) -> None:
        """Replace all configured intensities atomically after range validation."""
        if set(values) != set(self.cosmetic_slots) or any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not isfinite(value) or not 0 <= value <= 1
            for value in values.values()
        ):
            raise ValueError(
                "Cosmetic intensities require the configured slots with finite values from zero to one."
            )
        self.makeup_intensities = dict(values)

    def _pixmap(self, name: str) -> QPixmap:
        if name in self._pixmaps:
            return self._pixmaps[name]
        result = QPixmap()
        if not load_pixmap_png(result, self.layers[name]):
            raise ValueError(f"Cannot decode candidate appearance: {name}")
        self._pixmaps[name] = result
        return result

    def _cosmetic_layer_name(self, state: str, slot: str) -> str:
        if self.schema != VARIANT_SCHEMA:
            return f"{state}/{slot}"
        if self._selected_variant not in self.look_variants:
            raise ValueError("Selected makeup variant is unavailable in the candidate appearance.")
        return f"{self._selected_variant}/{state}/{slot}"

    def _refresh_selection(self) -> None:
        if self.store is None:
            return
        garment = resolve_active_selection(
            self.store, "garment", official_pack_root=self.official_pack_root,
        )
        makeup = resolve_active_selection(
            self.store, "makeup", official_pack_root=self.official_pack_root,
        )
        active_outfit_pack_id = outfit_pack_official.official_outfit_pack_id()
        active_makeup_pack_id = outfit_pack_official.builtin_makeup_pack_id()
        if garment.effective_pack_id not in {"builtin", active_outfit_pack_id}:
            raise ValueError("Selected garment has no source-bound exasperated candidate.")
        if makeup.effective_pack_id not in {"builtin", active_makeup_pack_id}:
            raise ValueError("Selected cosmetics have no source-bound exasperated candidate.")
        if self.schema == VARIANT_SCHEMA:
            if makeup.effective_pack_id == "builtin":
                self._selected_variant = None
            elif makeup.effective_variant_id not in self.look_variants:
                raise ValueError("Selected makeup variant is unavailable in the candidate appearance.")
            else:
                self._selected_variant = makeup.effective_variant_id
        else:
            if (
                makeup.effective_pack_id == active_makeup_pack_id
                and makeup.effective_variant_id not in REQUIRED_LOOK_VARIANTS
            ):
                raise ValueError("Selected makeup variant is unavailable in the candidate appearance.")
            self._selected_variant = None
        intensity = (
            read_makeup_intensity(self.store)
            if self.cosmetics_available
            and makeup.effective_pack_id == active_makeup_pack_id
            else 0.0
        )
        if self.schema != VARIANT_SCHEMA and makeup.effective_variant_id == "light":
            intensity *= LIGHT_VARIANT_OPACITY
        slots = read_makeup_slot_intensities(self.store, slots=frozenset(self.cosmetic_slots))
        self.set_makeup_intensities(
            {slot: intensity * slots[slot] for slot in self.cosmetic_slots}
        )
        self.garment_enabled = garment.effective_pack_id == active_outfit_pack_id

    def apply(
        self, frame: QPixmap, silhouette: str, *, mouth_expression: str | None = None,
    ) -> QPixmap:
        if silhouette != _EXASPERATED_SILHOUETTE:
            return frame
        self._refresh_selection()
        if (frame.width(), frame.height()) != (DIMENSION, DIMENSION):
            raise ValueError("Candidate appearance requires its native canvas.")
        if (
            mouth_expression not in {None, _EXASPERATED_EXPRESSION}
            and mouth_expression not in EXPRESSION_VARIANTS
        ):
            raise ValueError("Unrecognized candidate cosmetic mouth state.")
        state = (
            "rest"
            if mouth_expression is None
            else EXPRESSION_VARIANTS.get(mouth_expression, "rest")
        )
        result = frame.copy()
        painter = QPainter(result)
        try:
            if self.garment_enabled:
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
                painter.drawPixmap(0, 0, self._pixmap("replace_mask"))
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                painter.drawPixmap(0, 0, self._pixmap("garment"))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
            for slot in self.cosmetic_slots:
                intensity = self.makeup_intensities[slot]
                if intensity and self.cosmetics_available:
                    painter.setOpacity(intensity)
                    painter.drawPixmap(0, 0, self._pixmap(self._cosmetic_layer_name(state, slot)))
        finally:
            painter.end()
        return result
