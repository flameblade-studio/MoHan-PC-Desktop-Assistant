from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QPoint
from PySide6.QtGui import QImage, QPixmap, QRegion
from PySide6.QtWidgets import QApplication

from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
from tools.render_marketing_portraits import ROOT

CANVAS_SIZE = (1254, 1254)
DARK_PIXEL_MAX = 140
SMALL_COMPONENT_MAX_AREA = 25
BRIGHT_RESIDUAL_MIN = 180
# The repaired run leaves at most five antialiased edge pixels in the cheek
# eye region; ten leaves a small deterministic margin without allowing a
# visible background crescent.
MAX_BRIGHT_RESIDUAL_PIXELS = 10
MAX_RESIDUAL_DARK_COMPONENTS = 3
# Fixed from the repaired three-pose run: 19,451, 21,578 and 20,796 changed
# pixels.  18,000 keeps a conservative margin while remaining well above the
# 2,546-pixel failure signature that exposed the too-small eye replacement.
MIN_CLOSED_DIFF_PIXELS = 18_000
EYE_LAYERS = (
    "iris_left",
    "iris_right",
    "eyelid_left",
    "eyelid_right",
    "eyeliner_left",
    "eyeliner_right",
)
POSES = (
    ("cheek", "idle", "blink", "cheek-rest"),
    ("lean", "idle_lean", "blink_lean", "left-neutral"),
    ("front", "idle_front", "blink_front", "front-crossed"),
)


def _eye_region(pose: str) -> QRegion:
    root = ROOT / "assets" / "expressions" / "layered"
    region = QRegion()
    for layer in EYE_LAYERS:
        region = region.united(QRegion(QPixmap(str(root / f"{pose}_{layer}.png")).mask()))
    return region


def _region_points(region: QRegion):
    bounds = region.boundingRect()
    for y in range(bounds.top(), bounds.bottom() + 1):
        for x in range(bounds.left(), bounds.right() + 1):
            if region.contains(QPoint(x, y)):
                yield x, y


def _changed_pixels(first: QImage, second: QImage) -> int:
    return sum(
        first.pixel(x, y) != second.pixel(x, y)
        for y in range(CANVAS_SIZE[1])
        for x in range(CANVAS_SIZE[0])
    )


def _bright_residual_pixels(
    closed: QImage,
    bare_closed: QImage,
    eye_region: QRegion,
) -> int:
    return sum(
        closed.pixelColor(x, y) != bare_closed.pixelColor(x, y)
        and sum(
            getattr(closed.pixelColor(x, y), channel)()
            for channel in ("red", "green", "blue")
        )
        / 3
        >= BRIGHT_RESIDUAL_MIN
        for x, y in _region_points(eye_region)
    )


def _small_dark_residual_components(
    closed: QImage,
    bare_closed: QImage,
    eye_region: QRegion,
) -> int:
    points: set[tuple[int, int]] = set()
    for x, y in _region_points(eye_region):
        color = closed.pixelColor(x, y)
        if (
            color != bare_closed.pixelColor(x, y)
            and max(color.red(), color.green(), color.blue()) < DARK_PIXEL_MAX
        ):
            points.add((x, y))
    # The contract counts only isolated dark components of at most 25 pixels;
    # the continuous authored eyelash line is intentionally not a speckle.
    small = 0
    while points:
        before = len(points)
        component = {points.pop()}
        pending = list(component)
        while pending:
            x, y = pending.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    point = (x + dx, y + dy)
                    if point in points:
                        points.remove(point)
                        component.add(point)
                        pending.append(point)
        if len(component) <= SMALL_COMPONENT_MAX_AREA:
            small += 1
        assert len(points) < before
    return small


def run() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        overlay = ActiveOutfitOverlay(Path(temp_dir) / "store", ROOT)
        for pose, open_name, closed_name, silhouette in POSES:
            open_image = overlay.apply(
                QPixmap(str(ROOT / "assets" / "expressions" / f"{open_name}.png")),
                silhouette,
            ).toImage().convertToFormat(QImage.Format_ARGB32)
            closed_image = overlay.apply(
                QPixmap(str(ROOT / "assets" / "expressions" / f"{closed_name}.png")),
                silhouette,
                suppress_makeup_slots={"eyes"},
            ).toImage().convertToFormat(QImage.Format_ARGB32)
            bare_closed = QImage(
                str(ROOT / "assets" / "expressions" / f"{closed_name}.png")
            ).convertToFormat(QImage.Format_ARGB32)
            eye_region = _eye_region(pose)
            assert _changed_pixels(open_image, closed_image) >= MIN_CLOSED_DIFF_PIXELS, (
                f"{closed_name} changed too little from {open_name}"
            )
            assert _bright_residual_pixels(
                closed_image,
                bare_closed,
                eye_region,
            ) <= MAX_BRIGHT_RESIDUAL_PIXELS, (
                f"{closed_name} exposes an open-eye brightness residual"
            )
            assert _small_dark_residual_components(
                closed_image,
                bare_closed,
                eye_region,
            ) <= MAX_RESIDUAL_DARK_COMPONENTS, (
                f"{closed_name} leaves isolated dark eye speckles"
            )
            assert overlay.layer_count(silhouette) > 0
            assert overlay.layer_count(
                silhouette,
                suppress_makeup_slots={"eyes"},
            ) > 0


if __name__ == "__main__":
    raise SystemExit(run())
