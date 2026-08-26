"""Load and validate the 24-view × 25-layer full-body parametric assets.

Codex authored 600 transparent PNG layers (24 yaw views × 25 layers) under
``assets/pose-atlas/v4-layered/``. This module loads them into an immutable,
Qt-independent manifest so the full-body renderer can compose a continuously
controlled full-body portrait and replace the legacy PoseAtlas static photo +
procedural mouth.

Back-facing views intentionally leave the facial-feature layers transparent
(the face is not visible from behind); the loader therefore only requires the
body/clothing layers to be present on every view, and treats a missing facial
layer as an empty (transparent) layer rather than a hard failure.
"""

from __future__ import annotations

lazy import struct
lazy import json
lazy import math
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from domain.constants import FULL_BODY_LAYER_Z_ORDER

FULL_BODY_DIMENSION_WIDTH = 1024
FULL_BODY_DIMENSION_HEIGHT = 1536
PNG_HEADER_LENGTH = 24

# The 24 authored yaw views, in canonical ascending order.
VIEW_IDS = (
    "yaw-180-pitch+00", "yaw-165-pitch+00", "yaw-150-pitch+00", "yaw-135-pitch+00",
    "yaw-120-pitch+00", "yaw-105-pitch+00", "yaw-090-pitch+00", "yaw-075-pitch+00",
    "yaw-060-pitch+00", "yaw-045-pitch+00", "yaw-030-pitch+00", "yaw-015-pitch+00",
    "yaw+000-pitch+00", "yaw+015-pitch+00", "yaw+030-pitch+00", "yaw+045-pitch+00",
    "yaw+060-pitch+00", "yaw+075-pitch+00", "yaw+090-pitch+00", "yaw+105-pitch+00",
    "yaw+120-pitch+00", "yaw+135-pitch+00", "yaw+150-pitch+00", "yaw+165-pitch+00",
)

# Layers that must be present on every view (body + clothing). Facial-feature
# layers may be absent on back-facing views.
REQUIRED_LAYERS = frozenset(
    {
        "body",
        "hair_back",
        "hair_left",
        "hair_right",
        "sleeve_left",
        "sleeve_right",
        "ornament",
    }
)


@dataclass(frozen=True, slots=True)
class LayeredFullBodyView:
    """One view's complete set of 25 transparent layers."""

    view_id: str
    layers: frozendict[str, Path]
    mouth_center_x: float | None = None

    def path(self, layer: str) -> Path | None:
        return self.layers.get(layer)


@dataclass(frozen=True, slots=True)
class LayeredFullBodyManifest:
    """The complete 24-view full-body layered asset set."""

    views: frozendict[str, LayeredFullBodyView]

    def view(self, view_id: str) -> LayeredFullBodyView:
        return self.views[view_id]


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as source:
        header = source.read(PNG_HEADER_LENGTH)
    if len(header) != PNG_HEADER_LENGTH or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"invalid full-body PNG: {path.name}")
    return struct.unpack(">II", header[16:24])


def load_layered_full_body_assets(root: Path) -> LayeredFullBodyManifest:
    """Load and validate all 600 full-body layers, failing closed on gaps."""

    authority_centers = _load_authority_mouth_centers(root)
    views: dict[str, LayeredFullBodyView] = {}
    for view_id in VIEW_IDS:
        layers: dict[str, Path] = {}
        for layer in FULL_BODY_LAYER_Z_ORDER:
            path = root / f"{view_id}_{layer}.png"
            if not path.is_file():
                if layer in REQUIRED_LAYERS:
                    raise FileNotFoundError(
                        f"missing full-body asset: {view_id}_{layer}.png"
                    )
                continue
            if _png_dimensions(path) != (
                FULL_BODY_DIMENSION_WIDTH,
                FULL_BODY_DIMENSION_HEIGHT,
            ):
                raise ValueError(
                    f"unexpected full-body dimensions: {view_id}_{layer}.png"
                )
            layers[layer] = path
        views[view_id] = LayeredFullBodyView(
            view_id,
            frozendict(layers),
            authority_centers.get(view_id),
        )
    return LayeredFullBodyManifest(frozendict(views))


def _load_authority_mouth_centers(root: Path) -> dict[str, float]:
    """Load only explicitly trusted centers; malformed data fails closed."""

    path = root / "mouth_authority_manifest.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if payload.get("schema_version") != 1:
        return {}
    centers: dict[str, float] = {}
    for view_id, record in payload.get("views", {}).items():
        if view_id not in VIEW_IDS or not isinstance(record, dict):
            continue
        if record.get("trusted") is not True:
            continue
        value = record.get("mouth_center_x")
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            centers[view_id] = float(value)
    return centers
