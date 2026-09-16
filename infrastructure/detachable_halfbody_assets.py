"""Validated, detachable seven-part half-body portraits for runtime composition."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap


SCHEMA = "mohan.detachable-halfbody.v1"
DIMENSION = 1254
SHA256_HEX_LENGTH = 64
PART_ORDER = (
    "torso", "head", "hair", "arm_left", "hand_left", "arm_right", "hand_right",
)
POSES = frozenset({
    "front-crossed", "left-neutral", "cheek-rest", "front-mock-scold",
    "front-mock-hit", "front-eureka", "front-exasperated",
})


@dataclass(frozen=True, slots=True)
class DetachableHalfbodyAssets:
    root: Path
    payloads: dict[str, dict[str, bytes]]

    def compose(self, pose: str, *, hidden: frozenset[str] = frozenset()) -> QPixmap:
        """Paint individual parts in the same order as the reviewed assembly."""
        if pose not in self.payloads or not hidden <= set(PART_ORDER):
            raise ValueError("Unknown detachable half-body pose or part.")
        result = QPixmap(DIMENSION, DIMENSION)
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        try:
            for part in PART_ORDER:
                if part in hidden:
                    continue
                layer = QPixmap()
                layer.loadFromData(self.payloads[pose][part], "PNG")
                if layer.isNull() or layer.size() != result.size():
                    raise ValueError(f"Cannot decode detachable half-body part: {pose}/{part}")
                painter.drawPixmap(0, 0, layer)
        finally:
            painter.end()
        return result


def load_detachable_halfbody_assets(root: Path) -> DetachableHalfbodyAssets | None:
    """Return None only when uninstalled; an invalid installation fails closed."""
    root = Path(root)
    manifest_path = root / "manifest.json"
    if not root.exists():
        return None
    if not manifest_path.is_file():
        raise ValueError("Installed detachable half-body directory lacks manifest.json.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA or set(manifest.get("poses", {})) != POSES:
        raise ValueError("Invalid detachable half-body manifest or pose inventory.")
    payloads: dict[str, dict[str, bytes]] = {}
    for pose, parts in manifest["poses"].items():
        if set(parts) != set(PART_ORDER):
            raise ValueError(f"Incomplete detachable half-body pose: {pose}")
        payloads[pose] = {}
        for part, record in parts.items():
            expected = f"{pose}/{part}.rgba.png"
            if not isinstance(record, dict) or record.get("path") != expected:
                raise ValueError(f"Invalid detachable half-body path: {pose}/{part}")
            expected_hash = record.get("sha256")
            if not isinstance(expected_hash, str) or len(expected_hash) != SHA256_HEX_LENGTH:
                raise ValueError(f"Invalid detachable half-body digest: {expected}")
            path = root / expected
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != expected_hash:
                raise ValueError(f"Detachable half-body digest mismatch: {expected}")
            if payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[24:26] != b"\x08\x06":
                raise ValueError(f"Detachable half-body part must be 8-bit RGBA: {expected}")
            image = QImage.fromData(payload, "PNG")
            if image.isNull() or image.width() != DIMENSION or image.height() != DIMENSION:
                raise ValueError(f"Invalid detachable half-body PNG: {expected}")
            payloads[pose][part] = payload
    return DetachableHalfbodyAssets(root, payloads)
