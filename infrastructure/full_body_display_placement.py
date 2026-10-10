"""Owner-approved, source-bound display scale for the V5 full-body ring."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import math
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap

lazy from domain.character_runtime import character_rig_manifest
lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id


SCHEMA = "mohan.v5-full-body-display-placement.v1"
FILENAME = "DISPLAY-PLACEMENT.json"
_RIG_MANIFEST = character_rig_manifest()
EXPECTED_CANVAS = (
    _RIG_MANIFEST.full_body_canvas.width,
    _RIG_MANIFEST.full_body_canvas.height,
)
SHA256_LENGTH = 64
MIN_APPROVED_SCALE = 0.5
MAX_APPROVED_SCALE = 1.5


@dataclass(frozen=True, slots=True)
class ViewPlacement:
    view_id: str
    scale: float
    offset_x: float
    offset_y: float


class FullBodyDisplayPlacement:
    """Apply one pinned uniform transform after all character layers compose."""

    def __init__(self, source_root: Path) -> None:
        root = Path(source_root).resolve()
        manifest = json.loads((root / FILENAME).read_text(encoding="utf-8"))
        if manifest.get("schema") != SCHEMA or manifest.get("status") != "owner_approved":
            raise ValueError("Unsupported V5 display placement manifest")
        canvas = manifest.get("canvas")
        if not isinstance(canvas, dict) or (canvas.get("width"), canvas.get("height")) != EXPECTED_CANVAS:
            raise ValueError("V5 display placement canvas changed")
        if manifest.get("mode") != "height_normalised":
            raise ValueError("V5 display placement must use the approved mode")
        views = manifest.get("views")
        if not isinstance(views, list) or len(views) != len(CANONICAL_YAWS):
            raise ValueError("V5 display placement requires all 24 views")
        placements: dict[str, ViewPlacement] = {}
        for entry in views:
            if not isinstance(entry, dict):
                raise ValueError("Malformed V5 display placement view")
            view_id = entry.get("view_id")
            if view_id not in {canonical_view_id(yaw) for yaw in CANONICAL_YAWS} or view_id in placements:
                raise ValueError("Unknown or repeated V5 display placement view")
            expected_sha = entry.get("native_png_sha256")
            if not isinstance(expected_sha, str) or len(expected_sha) != SHA256_LENGTH:
                raise ValueError("Missing V5 display placement source digest")
            source = root / f"{view_id}.png"
            with source.open("rb") as stream:
                actual_sha = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual_sha != expected_sha:
                raise ValueError(f"V5 display placement source drift: {view_id}")
            transform: list[float] = []
            for key in ("scale", "offset_x", "offset_y"):
                value = entry.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f"Invalid V5 display placement transform: {view_id}")
                transform.append(float(value))
            scale, offset_x, offset_y = transform
            if not MIN_APPROVED_SCALE <= scale <= MAX_APPROVED_SCALE or abs(offset_x) > EXPECTED_CANVAS[0] or abs(offset_y) > EXPECTED_CANVAS[1]:
                raise ValueError(f"Out-of-range V5 display placement transform: {view_id}")
            placements[view_id] = ViewPlacement(view_id, float(scale), float(offset_x), float(offset_y))
        if set(placements) != {canonical_view_id(yaw) for yaw in CANONICAL_YAWS}:
            raise ValueError("Incomplete V5 display placement ring")
        self._placements = placements

    def apply(self, frame: QPixmap, view_id: str) -> QPixmap:
        """Return a new transparent canvas; never stretch x and y differently."""
        if frame.isNull():
            return frame
        if frame.width() != EXPECTED_CANVAS[0] or frame.height() != EXPECTED_CANVAS[1]:
            raise ValueError("Unexpected V5 full-body frame dimensions")
        try:
            placement = self._placements[view_id]
        except KeyError as error:
            raise ValueError(f"Unapproved V5 display placement view: {view_id}") from error
        scaled = frame.scaled(
            round(frame.width() * placement.scale),
            round(frame.height() * placement.scale),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        canvas = QPixmap(*EXPECTED_CANVAS)
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.drawPixmap(round(placement.offset_x), round(placement.offset_y), scaled)
        painter.end()
        return canvas


def load_full_body_display_placement(source_root: Path) -> FullBodyDisplayPlacement:
    """Read the pinned placement from the same packaged root as V5 authority."""
    return FullBodyDisplayPlacement(source_root)
