"""Render offline product-compositor evidence for the seven installed half-body poses."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy from pathlib import Path
lazy from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy from PIL import Image, ImageDraw
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.companion_animation_contract import EXPRESSION_SPEECH_MOUTH_RECTS
lazy from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.detachable_halfbody_assets import POSES, load_detachable_halfbody_assets
lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer
lazy from presentation.companion_face_assets import CompanionFaceAssetMethods
lazy from presentation.companion_visual_physics import CompanionVisualPhysicsMethods


ROOT = Path(__file__).resolve().parents[2]
EXPRESSION_ROOT = ROOT / "assets" / "expressions"
PREVIEW_SIZE = 465
POSE_CASES = (
    ("front-crossed", FacePose.FRONT, "idle_front", "_front"),
    ("left-neutral", FacePose.LEAN, "idle_lean", "_lean"),
    ("cheek-rest", FacePose.CHEEK, "idle", ""),
    ("front-mock-scold", FacePose.FRONT, "mock_scold", "_front"),
    ("front-mock-hit", FacePose.FRONT, "mock_hit_front", "_front"),
    ("front-eureka", FacePose.FRONT, "eureka_front", "_front"),
    ("front-exasperated", FacePose.FRONT, "exasperated_front", "_front"),
)
STATES = ("rest", "half", "closed", "speech", "physics")
MASK_STEPS = ((0, 42), (1, 76), (2, 132), (3, 255))


def _asset(name: str) -> QPixmap:
    source = QPixmap(str(EXPRESSION_ROOT / f"{name}.png"))
    if source.isNull():
        raise FileNotFoundError(name)
    return source.scaled(PREVIEW_SIZE, PREVIEW_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _mask(rects) -> QPixmap:
    return CompanionFaceAssetMethods._soft_rounded_mask(rects, MASK_STEPS, 10)


def _eye_frame(renderer, frame: QPixmap, pose: FacePose, suffix: str, state: str) -> QPixmap:
    if state == "half":
        # No authored half-eye source exists in the installed expression set.
        return QPixmap(frame)
    regions = CompanionFaceAssetMethods._blink_regions()[pose.value]
    patch = CompanionFaceAssetMethods._masked_region(_asset(f"blink{suffix}"), _mask(regions))
    return renderer.render_overlay(frame, patch, eye_state="closed")


def _speech_frame(renderer, base: QPixmap, pose: FacePose, expression: str, suffix: str) -> QPixmap:
    source = f"{expression}_speech_open" if expression in {
        "mock_scold", "mock_hit_front", "eureka_front", "exasperated_front"
    } else f"speaking{suffix}"
    rect = (
        EXPRESSION_SPEECH_MOUTH_RECTS[expression]
        if expression in EXPRESSION_SPEECH_MOUTH_RECTS
        else CompanionFaceAssetMethods._mouth_clip_regions()[suffix]
    )
    layers = SimpleNamespace(mouth_source=_asset(source), mouth_mask=_mask((rect,)))
    motion = FaceMotionFrame(pose, source, Viseme.A, MouthShape(aperture=1.0), ExpressionShape())
    return renderer.render(base, motion, layers, aperture=1.0)


def _physics_frame(frame: QPixmap, suffix: str) -> QPixmap:
    result = QPixmap(frame)
    painter = QPainter(result)
    try:
        for side in ("left", "right"):
            source = _asset(f"v120_sleeve_{side}{suffix}")
            painter.drawPixmap(0, 0, CompanionVisualPhysicsMethods._sleeve_texture_only(source, side))
        for side in ("left", "right"):
            source = _asset(f"v120_hair_{side}{suffix}")
            painter.drawPixmap(0, 0, CompanionVisualPhysicsMethods._hair_texture_only(source))
        painter.drawPixmap(0, 0, _asset(f"v120_ornament{suffix}"))
    finally:
        painter.end()
    return result


def run(output: Path) -> Path:
    QApplication.instance() or QApplication([])
    assets = load_detachable_halfbody_assets(EXPRESSION_ROOT / "detachable")
    if assets is None or set(assets.payloads) != POSES:
        raise ValueError("Formal seven-pose detachable rig is missing.")
    output.mkdir(parents=True, exist_ok=False)
    overlay = ActiveOutfitOverlay(output / "store", ROOT)
    renderer = LayeredParametricFaceRenderer(outfit_overlay=overlay)
    base = QPixmap(PREVIEW_SIZE, PREVIEW_SIZE)
    base.fill(Qt.transparent)
    entries = []
    sheet = Image.new("RGB", (PREVIEW_SIZE * len(STATES), PREVIEW_SIZE * len(POSE_CASES)), "#77797e")
    drawing = ImageDraw.Draw(sheet)
    for row, (silhouette, pose, expression, suffix) in enumerate(POSE_CASES):
        motion = FaceMotionFrame(pose, expression, Viseme.CLOSED, MouthShape(), ExpressionShape())
        rest = renderer.render(base, motion, None)
        frames = {
            "rest": rest,
            "half": _eye_frame(renderer, rest, pose, suffix, "half"),
            "closed": _eye_frame(renderer, rest, pose, suffix, "closed"),
            "speech": _speech_frame(renderer, base, pose, expression, suffix),
            "physics": _physics_frame(rest, suffix),
        }
        for column, state in enumerate(STATES):
            path = output / f"{silhouette}-{state}.png"
            if not frames[state].save(str(path)):
                raise RuntimeError(f"Cannot write {path}")
            source = Image.open(path).convert("RGBA")
            background = Image.new("RGBA", source.size, "#77797e")
            background.alpha_composite(source)
            sheet.paste(background.convert("RGB"), (column * PREVIEW_SIZE, row * PREVIEW_SIZE))
            drawing.rectangle(
                (column * PREVIEW_SIZE, row * PREVIEW_SIZE,
                 (column + 1) * PREVIEW_SIZE, row * PREVIEW_SIZE + 28),
                fill="#212328",
            )
            drawing.text((column * PREVIEW_SIZE + 8, row * PREVIEW_SIZE + 6),
                         f"{silhouette} / {state}", fill="white")
            entries.append({"pose": silhouette, "state": state,
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    contact = output / "contact-sheet.jpg"
    sheet.save(contact, quality=93)
    (output / "receipt.json").write_text(json.dumps({
        "schema": "mohan.detachable-runtime-offline-audit.v1",
        "frames": entries,
        "contact_sha256": hashlib.sha256(contact.read_bytes()).hexdigest(),
        "limits": "Product renderer, official outfit, authored eye/mouth masks and zero-angle legacy physics sources; not a full Companion UI session or owner visual approval.",
    }, indent=2) + "\n", encoding="utf-8")
    return contact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(run(args.output))


if __name__ == "__main__":
    main()
