"""Immutable declarations for character layer composition."""
from __future__ import annotations

lazy import re
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass
lazy from types import MappingProxyType
lazy from typing import cast


DEFAULT_CHARACTER_LAYER_ORDER = (
    "hair-back",
    "base",
    "body-fix",
    "garment",
    "makeup",
    "hair-front",
    "ornament",
)
CHARACTER_LAYER_KINDS = frozenset(
    {"hair-back", "body-fix", "garment", "hair-front", "ornament", "makeup"}
)
_ORDER_KINDS = frozenset((*CHARACTER_LAYER_KINDS, "base"))
ANCHOR_COORDINATES = 2
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_VIEW_FIELDS = frozenset({"order", "layers", "base_hide"})
_LAYER_FIELDS = frozenset({"kind", "path", "sha256", "anchor"})
_MASK_FIELDS = frozenset({"path", "sha256", "anchor"})


class CharacterLayerPlanError(ValueError):
    """A character layer plan violates its immutable rendering contract."""


@dataclass(frozen=True, slots=True)
class CharacterLayerAsset:
    """One full-canvas layer whose decoded image is supplied by an adapter."""

    kind: str
    path: str
    sha256: str
    anchor: tuple[int, int]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or self.kind not in CHARACTER_LAYER_KINDS:
            raise CharacterLayerPlanError(f"Unsupported character layer kind: {self.kind!r}.")
        _validate_asset_fields(self.path, self.sha256, self.anchor)


@dataclass(frozen=True, slots=True)
class CharacterLayerMask:
    """Full-canvas alpha mask used to clear the base before composition."""

    path: str
    sha256: str
    anchor: tuple[int, int]

    def __post_init__(self) -> None:
        _validate_asset_fields(self.path, self.sha256, self.anchor)


@dataclass(frozen=True, slots=True)
class CharacterLayerPlan:
    """Per-view paint order and assets for one body-pack composition."""

    order: tuple[str, ...]
    layers: tuple[CharacterLayerAsset, ...]
    base_hide: CharacterLayerMask | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.order, tuple) or not self.order:
            raise CharacterLayerPlanError("Character layer order must be a non-empty tuple.")
        if any(not isinstance(kind, str) or kind not in _ORDER_KINDS for kind in self.order):
            raise CharacterLayerPlanError("Character layer order contains an unsupported stage.")
        if self.order.count("base") != 1 or len(set(self.order)) != len(self.order):
            raise CharacterLayerPlanError(
                "Character layer order must include base once and contain no duplicates."
            )
        if not isinstance(self.layers, tuple):
            raise CharacterLayerPlanError("Character layers must be an immutable tuple.")
        for layer in self.layers:
            if not isinstance(layer, CharacterLayerAsset):
                raise CharacterLayerPlanError(
                    "Character layers must contain CharacterLayerAsset values."
                )
            if layer.kind not in self.order:
                raise CharacterLayerPlanError(
                    f"Layer kind {layer.kind!r} is missing from the declared order."
                )
        if self.base_hide is not None and not isinstance(self.base_hide, CharacterLayerMask):
            raise CharacterLayerPlanError("Base hide must be a CharacterLayerMask value.")


def parse_character_layer_views(value: object) -> Mapping[str, CharacterLayerPlan]:
    """Parse view-keyed declarations; an absent declaration keeps the caller's existing route."""
    if value is None:
        return MappingProxyType({})
    raw_views = _as_mapping(value, "character layer views")
    plans: dict[str, CharacterLayerPlan] = {}
    for view_id, raw_plan in raw_views.items():
        if not isinstance(view_id, str) or not view_id.strip():
            raise CharacterLayerPlanError(
                "Character layer view identifiers must be non-empty strings."
            )
        if raw_plan is None:
            continue
        view = _as_mapping(raw_plan, f"character layer view {view_id!r}")
        unknown_fields = set(view) - _VIEW_FIELDS
        if unknown_fields:
            raise CharacterLayerPlanError(
                f"Character layer view {view_id!r} contains unsupported fields: "
                + ", ".join(sorted(unknown_fields))
                + "."
            )

        order = _parse_order(view.get("order", list(DEFAULT_CHARACTER_LAYER_ORDER)), view_id)
        raw_layers = view.get("layers", [])
        if not isinstance(raw_layers, list):
            raise CharacterLayerPlanError(f"Character layers for view {view_id!r} must be a list.")
        layers = tuple(_parse_layer(layer, view_id) for layer in raw_layers)

        raw_mask = view.get("base_hide")
        base_hide = None if raw_mask is None else _parse_mask(raw_mask, view_id)
        plans[view_id] = CharacterLayerPlan(order, layers, base_hide)
    return MappingProxyType(plans)


def _parse_order(value: object, view_id: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or any(not isinstance(kind, str) for kind in value):
        raise CharacterLayerPlanError(
            f"Character layer order for view {view_id!r} must be a non-empty string list."
        )
    return tuple(value)


def _parse_layer(value: object, view_id: str) -> CharacterLayerAsset:
    record = _as_mapping(value, f"character layer for view {view_id!r}")
    if set(record) != _LAYER_FIELDS:
        raise CharacterLayerPlanError(
            f"Character layer for view {view_id!r} must declare kind, path, sha256, and anchor."
        )
    kind = record["kind"]
    if not isinstance(kind, str):
        raise CharacterLayerPlanError(
            f"Character layer kind for view {view_id!r} must be a string."
        )
    return CharacterLayerAsset(
        kind,
        _string(record["path"], f"layer path for view {view_id!r}"),
        _string(record["sha256"], f"layer SHA-256 for view {view_id!r}"),
        _parse_anchor(record["anchor"], view_id),
    )


def _parse_mask(value: object, view_id: str) -> CharacterLayerMask:
    record = _as_mapping(value, f"base hide mask for view {view_id!r}")
    if set(record) != _MASK_FIELDS:
        raise CharacterLayerPlanError(
            f"Base hide mask for view {view_id!r} must declare path, sha256, and anchor."
        )
    return CharacterLayerMask(
        _string(record["path"], f"base hide mask path for view {view_id!r}"),
        _string(record["sha256"], f"base hide mask SHA-256 for view {view_id!r}"),
        _parse_anchor(record["anchor"], view_id),
    )


def _parse_anchor(value: object, view_id: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != ANCHOR_COORDINATES
        or any(type(coordinate) is not int for coordinate in value)
    ):
        raise CharacterLayerPlanError(
            f"Character layer anchor for view {view_id!r} must be an integer pair."
        )
    anchor = cast(tuple[int, int], tuple(value))
    if anchor != (0, 0):
        raise CharacterLayerPlanError(
            f"Character layer anchor for view {view_id!r} must be [0, 0]."
        )
    return anchor


def _as_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise CharacterLayerPlanError(f"{label.capitalize()} must be an object with string keys.")
    return cast(Mapping[str, object], value)


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CharacterLayerPlanError(f"{label.capitalize()} must be a non-empty string.")
    return value


def _validate_asset_fields(path: str, digest: str, anchor: tuple[int, int]) -> None:
    _string(path, "character asset path")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise CharacterLayerPlanError(
            "Character asset SHA-256 must be 64 lowercase hexadecimal characters."
        )
    if (
        not isinstance(anchor, tuple)
        or len(anchor) != ANCHOR_COORDINATES
        or any(type(coordinate) is not int for coordinate in anchor)
        or anchor != (0, 0)
    ):
        raise CharacterLayerPlanError("Character asset anchor must be the immutable pair (0, 0).")
