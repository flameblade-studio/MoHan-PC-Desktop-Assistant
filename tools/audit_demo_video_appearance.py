"""Collect pixel evidence for the face and official hair/headwear regressions."""

from __future__ import annotations

lazy import json
lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

lazy import cv2
lazy import numpy as np
lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtGui import QImage, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from presentation.companion_window import CompanionWindow
lazy from test_closed_eye_makeup_regression import (
    _bright_residual_pixels,
    _changed_pixels,
    _eye_region,
    _small_dark_residual_components,
    BRIGHT_RESIDUAL_MIN,
    DARK_PIXEL_MAX,
    MAX_BRIGHT_RESIDUAL_PIXELS,
    MAX_RESIDUAL_DARK_COMPONENTS,
    MIN_CLOSED_DIFF_PIXELS,
    POSES as CLOSED_EYE_POSES,
)
lazy from test_mouth_corner_artifact_regression import (
    DARK_EYE_MAX_RGB,
    MOUTH_CORNER_PROBES,
    OPEN_FRAMES,
    POSES as MOUTH_POSES,
    _configure_speech,
    _image,
    _new_dark_eye_pixels,
    _source_backed_residuals,
    _source_expression,
)
lazy from tools.audit_official_pack_quality import (
    DEFAULT_BASE_HAIR,
    DEFAULT_PACK,
    FINE_CHAIN_ROI,
    audit as audit_official_pack,
)

EVIDENCE = ROOT / "docs" / "release-evidence" / "media-generation-coherence"
VIDEO_SAMPLE_FRAME = 70
VIDEO_SAMPLE_TIME = VIDEO_SAMPLE_FRAME / 10
VIDEO_BLINK_FRAME = 24
VIDEO_BLINK_TIME = VIDEO_BLINK_FRAME / 10
VIDEO_MOUTH_ROI = (990, 440, 1140, 555)
PORTRAIT_SIZE = 1254
VIDEO_PANEL_ORIGIN = (888, 121)
VIDEO_CROP_SIZE = (450, 600)
VIDEO_RENDER_SIZE = (350, 466)
MAX_SOLID_HAIR_RGB = 90
RGBA_CHANNELS = 4
OPAQUE_PIXEL_MIN_ALPHA = 250
FOREHEAD_SIDE_ROIS = {
    "left": (455, 280, 530, 450),
    "right": (725, 280, 800, 450),
}


def _rgba(image: QImage) -> QImage:
    return image.convertToFormat(QImage.Format_ARGB32)


def _rect_tuple(rect) -> list[int]:
    return list(rect.getRect())


def _closed_eye_evidence() -> dict[str, object]:
    app = QApplication.instance() or QApplication([])
    measurements: list[dict[str, object]] = []
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        overlay = ActiveOutfitOverlay(Path(temp_dir) / "store", ROOT)
        for pose, open_name, closed_name, silhouette in CLOSED_EYE_POSES:
            open_image = _rgba(
                overlay.apply(
                    QPixmap(str(ROOT / "assets" / "expressions" / f"{open_name}.png")),
                    silhouette,
                ).toImage()
            )
            closed_image = _rgba(
                overlay.apply(
                    QPixmap(str(ROOT / "assets" / "expressions" / f"{closed_name}.png")),
                    silhouette,
                    suppress_makeup_slots={"eyes"},
                ).toImage()
            )
            bare_closed = _rgba(
                QImage(str(ROOT / "assets" / "expressions" / f"{closed_name}.png"))
            )
            eye_region = _eye_region(pose)
            measurements.append(
                {
                    "pose": pose,
                    "frame_asset": f"assets/expressions/{closed_name}.png",
                    "eye_roi_xywh": _rect_tuple(eye_region.boundingRect()),
                    "changed_pixels": _changed_pixels(open_image, closed_image),
                    "bright_residual_pixels": _bright_residual_pixels(
                        closed_image,
                        bare_closed,
                        eye_region,
                    ),
                    "dark_residual_components": _small_dark_residual_components(
                        closed_image,
                        bare_closed,
                        eye_region,
                    ),
                }
            )
            if pose == "front":
                (EVIDENCE / "blink-front-composed.png").parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                closed_image.save(str(EVIDENCE / "blink-front-composed.png"), "PNG")
        app.processEvents()
    return {
        "video_frame": {
            "frame_index": VIDEO_BLINK_FRAME,
            "timestamp_seconds": VIDEO_BLINK_TIME,
            "path": "docs/release-evidence/media-generation-coherence/frame-024-blink.png",
        },
        "contract": {
            "minimum_closed_diff_pixels": MIN_CLOSED_DIFF_PIXELS,
            "maximum_bright_residual_pixels": MAX_BRIGHT_RESIDUAL_PIXELS,
            "maximum_dark_residual_components": MAX_RESIDUAL_DARK_COMPONENTS,
            "bright_residual_meaning": f"RGB mean >= {BRIGHT_RESIDUAL_MIN}",
            "dark_pixel_meaning": f"max RGB < {DARK_PIXEL_MAX}",
        },
        "measurements": measurements,
    }


def _mouth_corner_evidence() -> dict[str, object]:
    app = QApplication.instance() or QApplication([])
    per_pose: dict[str, dict[str, object]] = {}
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        window = CompanionWindow(startup_speech=False)
        failures: list[str] = []
        try:
            window.show()
            app.processEvents()
            for timer in window.findChildren(QTimer):
                timer.stop()
            for pose, suffix, closed_name in MOUTH_POSES:
                _configure_speech(window, pose, suffix, closed_name)
                closed = _image(window._mouth_aperture_pixmap(closed_name, 0.0))
                eye_regions = window.dedicated_blink_regions[pose]
                mouth_total = 0
                eye_total = 0
                cases = 0
                for label, (expression_root, aperture, source_roots) in OPEN_FRAMES.items():
                    expression = f"{expression_root}{suffix}"
                    source = _image(_source_expression(window, source_roots, suffix))
                    rendered = _image(window._mouth_aperture_pixmap(expression, aperture))
                    mask = _image(window.viseme_mouth_masks[suffix])
                    mouth_residuals = _source_backed_residuals(
                        closed,
                        source,
                        rendered,
                        mask,
                        MOUTH_CORNER_PROBES[pose],
                    )
                    eye_residuals = _new_dark_eye_pixels(
                        closed,
                        rendered,
                        eye_regions,
                    )
                    mouth_total += len(mouth_residuals)
                    eye_total += len(eye_residuals)
                    cases += 1
                    if mouth_residuals or eye_residuals:
                        failures.append(f"{pose}/{label}")
                per_pose[pose] = {
                    "probe_rects_xywh": {
                        side: _rect_tuple(rect)
                        for side, rect in zip(
                            ("left", "right"),
                            MOUTH_CORNER_PROBES[pose],
                        )
                    },
                    "cases": cases,
                    "mouth_residual_pixels": mouth_total,
                    "eye_residual_pixels": eye_total,
                }
        finally:
            window.close()
            app.processEvents()
    return {
        "video_frame": {
            "frame_index": VIDEO_SAMPLE_FRAME,
            "timestamp_seconds": VIDEO_SAMPLE_TIME,
            "path": "docs/release-evidence/media-generation-coherence/frame-070-scene2.png",
            "mouth_roi_xyxy": list(VIDEO_MOUTH_ROI),
        },
        "contract": {
            "dark_eye_max_rgb": DARK_EYE_MAX_RGB,
            "cases": sum(int(item["cases"]) for item in per_pose.values()),
        },
        "per_pose": per_pose,
        "total_mouth_residual_pixels": sum(
            int(item["mouth_residual_pixels"]) for item in per_pose.values()
        ),
        "total_eye_residual_pixels": sum(
            int(item["eye_residual_pixels"]) for item in per_pose.values()
        ),
        "failures": failures,
    }


def _video_xyxy_from_portrait(roi: tuple[int, int, int, int]) -> list[int]:
    x0, y0, x1, y1 = roi
    crop_x, crop_y = VIDEO_CROP_ORIGIN
    render_x, render_y = VIDEO_RENDER_SIZE
    panel_x, panel_y = VIDEO_PANEL_ORIGIN
    return [
        round(panel_x + (x0 - crop_x) * render_x / VIDEO_CROP_SIZE[0]),
        round(panel_y + (y0 - crop_y) * render_y / VIDEO_CROP_SIZE[1]),
        round(panel_x + (x1 - crop_x) * render_x / VIDEO_CROP_SIZE[0]),
        round(panel_y + (y1 - crop_y) * render_y / VIDEO_CROP_SIZE[1]),
    ]


VIDEO_CROP_ORIGIN = (402, 100)


def _hair_evidence() -> dict[str, object]:
    portrait_path = ROOT / "docs" / "media" / "portraits" / "gentle_smile_front.png"
    portrait = cv2.imread(str(portrait_path), cv2.IMREAD_UNCHANGED)
    if portrait is None or portrait.shape[2] != RGBA_CHANNELS:
        raise RuntimeError("Composed portrait could not be read as RGBA.")
    regions: dict[str, dict[str, object]] = {}
    for name, (x0, y0, x1, y1) in FOREHEAD_SIDE_ROIS.items():
        crop = portrait[y0:y1, x0:x1]
        rgb = crop[:, :, :3][:, :, ::-1]
        opaque = crop[:, :, 3] >= OPAQUE_PIXEL_MIN_ALPHA
        solid = opaque & (rgb.max(axis=2) <= MAX_SOLID_HAIR_RGB)
        darkest = np.unravel_index(np.argmin(np.where(opaque, rgb.max(axis=2), 255)), solid.shape)
        darkest_y, darkest_x = darkest
        regions[name] = {
            "portrait_roi_xyxy": [x0, y0, x1, y1],
            "video_roi_xyxy": _video_xyxy_from_portrait((x0, y0, x1, y1)),
            "opaque_pixels": int(opaque.sum()),
            "solid_black_pixels": int(solid.sum()),
            "solid_black_percent_of_opaque": round(
                100.0 * solid.sum() / max(1, opaque.sum()),
                4,
            ),
            "darkest_probe": {
                "xy": [x0 + int(darkest_x), y0 + int(darkest_y)],
                "rgb": rgb[darkest_y, darkest_x].tolist(),
            },
        }
    quality = audit_official_pack(
        DEFAULT_PACK,
        portrait_path,
        DEFAULT_BASE_HAIR,
    )
    return {
        "video_frame": {
            "frame_index": VIDEO_SAMPLE_FRAME,
            "timestamp_seconds": VIDEO_SAMPLE_TIME,
            "path": "docs/release-evidence/media-generation-coherence/frame-070-scene2.png",
        },
        "portrait_frame": "docs/media/portraits/gentle_smile_front.png",
        "solid_black_threshold_max_rgb": MAX_SOLID_HAIR_RGB,
        "forehead_side_regions": regions,
        "official_quality": {
            "composite_specks": quality["composite_specks"],
            "fine_chain": quality["fine_chain"],
            "hair_back_slots": quality["hair_back_slots"],
        },
        "chain_roi_xyxy": list(FINE_CHAIN_ROI),
        "chain_video_roi_xyxy": _video_xyxy_from_portrait(FINE_CHAIN_ROI),
    }


def audit() -> dict[str, object]:
    return {
        "video_frame_samples": {
            "mouth_and_ornament": VIDEO_SAMPLE_FRAME,
            "closed_eye": VIDEO_BLINK_FRAME,
        },
        "mouth_corner_artifact": _mouth_corner_evidence(),
        "closed_eye_makeup": _closed_eye_evidence(),
        "hair_and_headwear": _hair_evidence(),
    }


def main() -> int:
    result = audit()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    output = EVIDENCE / "appearance-evidence.json"
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["mouth_corner_artifact"]["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
