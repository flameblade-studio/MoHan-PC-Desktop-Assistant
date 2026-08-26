"""Fail-closed runtime acceptance for the canonical 25-layer front view.

This audit complements the file-semantic validator: valid PNGs are not enough
when the live renderer later paints the authority face over blink or gaze.  It
renders the actual yaw+000 runtime path and proves that rest, blink, speech,
gaze and body physics each have the expected visible effect.
"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import os
lazy from collections import Counter
lazy from dataclasses import asdict, dataclass
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy from PySide6.QtCore import QPoint
lazy from PySide6.QtGui import QImage, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication

lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from infrastructure.layered_full_body_assets import load_layered_full_body_assets
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSET_ROOT = ROOT / "assets" / "pose-atlas" / "v4-layered"
DEFAULT_AUTHORITY = ROOT / "assets" / "pose-atlas" / "v4" / "yaw+000-pitch+00.png"
VIEW_ID = "yaw+000-pitch+00"
SCHEMA = "mohan.yaw000-layer-runtime-audit.v1"
EXPECTED_LAYERS = 25
SAMPLE_STEP = 6
MAX_REST_MEAN_ERROR = 2.0
MIN_FEATURE_CHANGED_PIXELS = 12
MIN_SPEECH_CHANGED_PIXELS = 20
MIN_PHYSICS_CHANGED_PIXELS = 50


@dataclass(frozen=True, slots=True)
class RuntimeIssue:
    code: str
    message: str
    measured: float | int
    required: float | int


@dataclass(frozen=True, slots=True)
class RuntimeReport:
    schema: str
    passed: bool
    view_id: str
    layer_count: int
    metrics: dict[str, float | int]
    issues_by_code: dict[str, int]
    issues: tuple[RuntimeIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _frame(
    *,
    viseme: Viseme = Viseme.CLOSED,
    aperture: float = 0.0,
    blink: float = 0.0,
    gaze_x: float = 0.0,
    breath: float = 0.5,
) -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "speaking_front" if viseme is not Viseme.CLOSED else "idle_front",
        viseme,
        MouthShape(aperture=aperture, width=0.75, jaw=aperture),
        ExpressionShape(blink=blink),
        gaze_x=gaze_x,
        breath=breath,
    )


def _changed(first: QImage, second: QImage, region: QRegion) -> int:
    bounds = region.boundingRect()
    if bounds.isEmpty():
        return 0
    count = 0
    for y in range(max(0, bounds.top()), min(first.height(), bounds.bottom() + 1)):
        for x in range(max(0, bounds.left()), min(first.width(), bounds.right() + 1)):
            if region.contains(QPoint(x, y)) and first.pixel(x, y) != second.pixel(x, y):
                count += 1
    return count


def _sampled_mean_error(actual: QImage, expected: QImage) -> float:
    differences: list[int] = []
    for y in range(0, expected.height(), SAMPLE_STEP):
        for x in range(0, expected.width(), SAMPLE_STEP):
            target = expected.pixelColor(x, y)
            if target.alpha() == 0:
                continue
            value = actual.pixelColor(x, y)
            differences.append(
                max(
                    abs(value.red() - target.red()),
                    abs(value.green() - target.green()),
                    abs(value.blue() - target.blue()),
                    abs(value.alpha() - target.alpha()),
                )
            )
    return float("inf") if not differences else sum(differences) / len(differences)


def _region(view, *layers: str) -> QRegion:
    region = QRegion()
    for layer in layers:
        path = view.path(layer)
        if path is not None:
            region = region.united(QRegion(QPixmap(str(path)).mask()))
    return region


def audit(
    asset_root: Path = DEFAULT_ASSET_ROOT,
    authority_path: Path = DEFAULT_AUTHORITY,
) -> RuntimeReport:
    QApplication.instance() or QApplication([])
    manifest = load_layered_full_body_assets(Path(asset_root))
    view = manifest.view(VIEW_ID)
    renderer = LayeredFullBodyRenderer(manifest)
    neutral = renderer.render_view(VIEW_ID, _frame()).toImage()
    blink = renderer.render_view(VIEW_ID, _frame(blink=1.0)).toImage()
    gaze = renderer.render_view(VIEW_ID, _frame(gaze_x=0.85)).toImage()
    speech = renderer.render_view(
        VIEW_ID,
        _frame(viseme=Viseme.A, aperture=0.9),
    ).toImage()
    physics = renderer.render_view(
        VIEW_ID,
        _frame(breath=0.9),
        pose_id="greeting-wave",
        left_hand="open-left",
        right_hand="relaxed-right",
        body_energy=0.8,
        gesture_beat=True,
    ).toImage()
    authority = QPixmap(str(authority_path)).toImage()
    blink_region = _region(
        view,
        "eyelid_left",
        "eyelid_right",
        "eyeliner_left",
        "eyeliner_right",
    )
    gaze_region = _region(view, "iris_left", "iris_right")
    mouth_region = _region(
        view,
        "oral_cavity",
        "lip_lower",
        "lip_upper",
        "corner_left",
        "corner_right",
    )
    full_region = QRegion(0, 0, neutral.width(), neutral.height())
    metrics: dict[str, float | int] = {
        "rest_mean_channel_error": _sampled_mean_error(neutral, authority),
        "blink_changed_pixels": _changed(neutral, blink, blink_region),
        "gaze_changed_pixels": _changed(neutral, gaze, gaze_region),
        "speech_changed_pixels": _changed(neutral, speech, mouth_region),
        "physics_changed_pixels": _changed(neutral, physics, full_region),
    }
    issues: list[RuntimeIssue] = []
    if len(view.layers) != EXPECTED_LAYERS:
        issues.append(
            RuntimeIssue(
                "layer-count",
                "yaw+000 does not contain the complete 25-layer contract.",
                len(view.layers),
                EXPECTED_LAYERS,
            )
        )
    checks = (
        ("rest-authority", "rest_mean_channel_error", MAX_REST_MEAN_ERROR, False),
        ("blink-inert", "blink_changed_pixels", MIN_FEATURE_CHANGED_PIXELS, True),
        ("gaze-inert", "gaze_changed_pixels", MIN_FEATURE_CHANGED_PIXELS, True),
        ("speech-inert", "speech_changed_pixels", MIN_SPEECH_CHANGED_PIXELS, True),
        ("physics-inert", "physics_changed_pixels", MIN_PHYSICS_CHANGED_PIXELS, True),
    )
    for code, metric, threshold, minimum in checks:
        value = metrics[metric]
        failed = value < threshold if minimum else value > threshold
        if failed:
            relation = "at least" if minimum else "at most"
            issues.append(
                RuntimeIssue(
                    code,
                    f"{metric} must be {relation} {threshold}.",
                    value,
                    threshold,
                )
            )
    counts = Counter(issue.code for issue in issues)
    return RuntimeReport(
        SCHEMA,
        not issues,
        VIEW_ID,
        len(view.layers),
        metrics,
        dict(sorted(counts.items())),
        tuple(issues),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--json-output", type=Path)
    arguments = parser.parse_args()
    try:
        report = audit(arguments.asset_root, arguments.authority)
    except Exception as error:
        print(f"YAW000_LAYER_RUNTIME_ERROR: {type(error).__name__}: {error}")
        return 2
    payload = json.dumps(
        report.to_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    if arguments.json_output is not None:
        arguments.json_output.parent.mkdir(parents=True, exist_ok=True)
        arguments.json_output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
