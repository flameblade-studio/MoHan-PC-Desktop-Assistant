"""Source-pinned approved exasperated portrait and speech mouth assets."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap


SCHEMA = "mohan.exasperated-runtime-candidate.v1"
FORMAL_INSTALL_SCHEMA = "mohan.source-bound-exasperated-default-install.v1"
FORMAL_ASSET_RELATIVE_DIR = "assets/expressions/source-bound-exasperated"
APPROVED_SOURCE_SHA256 = "0bb3d74affef4d2df831cf45d7f6d756b69cb58aee3693aea14f38f5d47996df"
DIMENSION = 1254
SHA256_HEX_LENGTH = 64
MOUTH_BOUNDS = (480, 505, 627, 612)
PART_ORDER = (
    "visible_core_hair",
    "visible_head_neck_chest_skin",
    "visible_upper_garment",
    "visible_right_arm",
    "visible_left_arm",
    "visible_right_hand",
    "visible_left_hand",
)
MOUTH_VARIANTS = ("mid", "open", "round")
EXPRESSION_VARIANTS = {
    "exasperated_front_speech_mid": "mid",
    "exasperated_front_speech_i": "mid",
    "exasperated_front_speech_open": "open",
    "exasperated_front_speech_round": "round",
    "exasperated_front_speech_u": "round",
}


class ExasperatedAppearanceOverlay(Protocol):
    """Source-bound garment and makeup applied after the native mouth patch."""

    def apply(
        self,
        frame: QPixmap,
        silhouette: str,
        *,
        mouth_expression: str | None,
    ) -> QPixmap: ...


@dataclass(frozen=True, slots=True)
class ExasperatedCandidateAssets:
    """Validated PNG bytes stay immutable after loading, even if files drift."""

    parts: dict[str, bytes]
    mouths: dict[str, bytes]

    def compose(self, *, hidden: frozenset[str] = frozenset()) -> QPixmap:
        if not hidden <= set(PART_ORDER):
            raise ValueError("Unknown exasperated part.")
        frame = QPixmap(DIMENSION, DIMENSION)
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        try:
            for role in PART_ORDER:
                if role in hidden:
                    continue
                part = QPixmap()
                if not part.loadFromData(self.parts[role], "PNG"):
                    raise ValueError(f"Cannot decode exasperated part: {role}")
                painter.drawPixmap(0, 0, part)
        finally:
            painter.end()
        return frame

    def patch(self, expression: str) -> QPixmap | None:
        variant = EXPRESSION_VARIANTS.get(expression)
        if variant is None:
            if expression == "exasperated_front":
                return None
            raise ValueError(f"Unsupported exasperated mouth expression: {expression}")
        patch = QPixmap()
        if not patch.loadFromData(self.mouths[variant], "PNG"):
            raise ValueError(f"Cannot decode exasperated mouth: {variant}")
        return patch


def validate_candidate_png(root: Path, record: object, expected_path: str, *, mouth: bool = False) -> bytes:
    if not isinstance(record, dict) or record.get("path") != expected_path:
        raise ValueError(f"Invalid exasperated candidate path: {expected_path}")
    digest = record.get("sha256")
    if not isinstance(digest, str) or len(digest) != SHA256_HEX_LENGTH or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"Invalid exasperated candidate digest: {expected_path}")
    path = root / expected_path
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Exasperated candidate path escapes its root: {expected_path}")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError(f"Exasperated candidate digest mismatch: {expected_path}")
    if payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[24:26] != b"\x08\x06":
        raise ValueError(f"Exasperated candidate must be 8-bit RGBA PNG: {expected_path}")
    image = QImage.fromData(payload, "PNG")
    if image.isNull() or (image.width(), image.height()) != (DIMENSION, DIMENSION):
        raise ValueError(f"Invalid exasperated candidate dimensions: {expected_path}")
    if mouth:
        _validate_mouth_alpha(image, expected_path)
    return payload


def _validate_mouth_alpha(image: QImage, name: str) -> None:
    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = rgba.bits()
    stride = rgba.bytesPerLine()
    left, top, right, bottom = MOUTH_BOUNDS
    visible = False
    for y in range(DIMENSION):
        row = pixels[y * stride:y * stride + DIMENSION * 4]
        if top <= y < bottom:
            outside = any(row[3:left * 4:4]) or any(row[right * 4 + 3:DIMENSION * 4:4])
            visible = visible or any(row[left * 4 + 3:right * 4:4])
        else:
            outside = any(row[3:DIMENSION * 4:4])
        if outside:
            raise ValueError(f"Exasperated mouth paints outside its source-bound ROI: {name}")
    if not visible:
        raise ValueError(f"Exasperated mouth is empty: {name}")


def load_exasperated_candidate_assets(root: Path) -> ExasperatedCandidateAssets:
    """Load a source-bound asset root; invalid input fails closed."""
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise ValueError("Invalid exasperated candidate manifest schema.")
    if manifest.get("approved_source_sha256") != APPROVED_SOURCE_SHA256:
        raise ValueError("Exasperated candidate is not bound to the approved source.")
    if set(manifest.get("parts", {})) != set(PART_ORDER) or set(manifest.get("mouths", {})) != set(MOUTH_VARIANTS):
        raise ValueError("Incomplete exasperated candidate parts or mouths.")
    parts = {
        role: validate_candidate_png(root, manifest["parts"][role], f"parts/{role}.rgba.png")
        for role in PART_ORDER
    }
    mouths = {
        variant: validate_candidate_png(root, manifest["mouths"][variant], f"mouths/{variant}.rgba.png", mouth=True)
        for variant in MOUTH_VARIANTS
    }
    return ExasperatedCandidateAssets(parts, mouths)


def validate_formal_exasperated_install(root: Path) -> None:
    """Verify the installed default receipt and every pinned packaged file."""
    root = Path(root).resolve()
    receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema") != FORMAL_INSTALL_SCHEMA
        or receipt.get("approved_source_sha256") != APPROVED_SOURCE_SHA256
        or receipt.get("owner_default_replacement_authorized_in_current_session") is not True
    ):
        raise ValueError("Exasperated default installation receipt is invalid.")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    appearance = json.loads((root / "appearance" / "manifest.json").read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema") != SCHEMA
        or manifest.get("approved_source_sha256") != APPROVED_SOURCE_SHA256
        or set(manifest.get("parts", {})) != set(PART_ORDER)
        or set(manifest.get("mouths", {})) != set(MOUTH_VARIANTS)
        or not isinstance(appearance, dict)
        or appearance.get("source_sha256") != APPROVED_SOURCE_SHA256
        or appearance.get("garment_owner_approval", {}).get("path") != "approval/garment-approval.json"
        or appearance.get("garment_owner_approval", {}).get("path_base") != "install_root"
    ):
        raise ValueError("Exasperated default manifests are incomplete.")
    owner_approval = receipt.get("owner_approval")
    if (
        not isinstance(owner_approval, dict)
        or not isinstance(owner_approval.get("statement"), str)
        or not owner_approval["statement"]
        or not isinstance(owner_approval.get("review_page"), dict)
        or not isinstance(owner_approval["review_page"].get("sha256"), str)
    ):
        raise ValueError("Exasperated default approval evidence is incomplete.")
    expected = {"manifest.json", "appearance/manifest.json", "approval/garment-approval.json"}
    expected.update(f"parts/{role}.rgba.png" for role in PART_ORDER)
    expected.update(f"mouths/{variant}.rgba.png" for variant in MOUTH_VARIANTS)
    layers = appearance.get("layers", {})
    if not isinstance(layers, dict):
        raise ValueError("Exasperated default appearance layers are invalid.")
    expected.update(f"appearance/{name}.rgba.png" for name in layers)
    if appearance.get("cosmetic_status") != "not_approved":
        cosmetic_approval = appearance.get("cosmetic_owner_approval", {})
        if (
            not isinstance(cosmetic_approval, dict)
            or cosmetic_approval.get("path") != "approval/makeup-palette-approval.json"
            or cosmetic_approval.get("path_base") != "install_root"
        ):
            raise ValueError("Installed cosmetics need their owner palette approval.")
        expected.add("approval/makeup-palette-approval.json")
    records = receipt.get("installed_files_sha256")
    if not isinstance(records, dict) or set(records) != expected:
        raise ValueError("Exasperated default receipt does not cover every file.")
    for relative, digest in records.items():
        if not isinstance(digest, str) or len(digest) != SHA256_HEX_LENGTH or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"Invalid installed exasperated digest: {relative}")
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Installed exasperated asset drifted: {relative}")
    if receipt.get("garment_owner_approval_sha256") != records["approval/garment-approval.json"]:
        raise ValueError("Installed garment approval is unbound.")
    if appearance.get("cosmetic_status") != "not_approved" and (
        appearance["cosmetic_owner_approval"].get("sha256")
        != records["approval/makeup-palette-approval.json"]
    ):
        raise ValueError("Installed cosmetic approval is unbound.")
