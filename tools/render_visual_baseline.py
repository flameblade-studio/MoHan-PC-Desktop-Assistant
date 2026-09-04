"""Render and check the consumer-facing composed visual baseline.

The half-body scenes deliberately use the same ``render_portrait`` helper and
the same fresh-store ``ActiveOutfitOverlay`` path as
``tools/render_marketing_portraits.py``. When the runtime PoseAtlas has the
canonical full-body yaw views, the two requested yaw scenes use the runtime
``LayeredFullBodyRenderer`` with that same overlay.

The first committed baseline is the current ``main`` state and therefore
intentionally includes known defects. After issue ``#185`` is merged into
this branch, rerun ``QT_QPA_PLATFORM=offscreen py -3.15
tools/render_visual_baseline.py --write`` to update the baseline deliberately.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import os
lazy import sys
lazy from collections.abc import Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QBuffer, QByteArray, QIODevice
lazy from PySide6.QtGui import QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.constants import (
    POSE_ATLAS_LAYERED_ROOT_NAME,
    POSE_ATLAS_ROOT_NAME,
)
lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.layered_full_body_assets import (
    VIEW_IDS,
    load_layered_full_body_assets,
)
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer
lazy from tools.render_marketing_portraits import render_portrait

BASELINE_ROOT = ROOT / "tests" / "visual_baseline"
DIFF_ROOT = ROOT / "work" / "visual-baseline"
FULL_BODY_ROOT = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_ROOT_NAME
FULL_BODY_LAYERED_ROOT = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME
HEAD_CROP = (300, 100, 700, 420)
DIFF_CHANNEL_THRESHOLD = 8
MAX_DIFFERENCE_RATIO = 0.0005
MAX_DIFFERENCE_BLOCK_AREA = 64
YAW_SCENE_VIEWS = (
    ("yaw+030", "yaw+030-pitch+00"),
    ("yaw-030", "yaw-030-pitch+00"),
)


class QtUnavailableError(RuntimeError):
    """Raised when the offscreen Qt renderer cannot be initialized."""


@dataclass(frozen=True, slots=True)
class SceneSpec:
    """One stable consumer scene and the defect it is intended to catch."""

    name: str
    reason: str
    expression: str | None = None
    view_id: str | None = None
    crop: tuple[int, int, int, int] | None = None


BASE_SCENE_SPECS = (
    SceneSpec(
        "idle_front",
        "整體基線，固定使用者最常看到的正面合成畫面。",
        expression="idle_front",
    ),
    SceneSpec(
        "speaking_open",
        "張嘴畫面，抓嘴角殘留、口腔邊界與嘴型不動。",
        expression="speaking_front",
    ),
    SceneSpec(
        "speaking_closed",
        "閉嘴畫面，確認發話結束後恢復正確的閉口來源。",
        expression="idle_front",
    ),
    SceneSpec(
        "blink_closed",
        "閉眼畫面，抓眼皮未蓋滿與 eyes 妝容疊在眼皮上的問題。",
        expression="blink_front",
    ),
    SceneSpec(
        "head_crop",
        "正面頭部原尺寸裁圖，放大檢查髮絲空心、髮飾碎片與流蘇缺段。",
        crop=HEAD_CROP,
    ),
)


def _application() -> QApplication:
    try:
        return QApplication.instance() or QApplication([])
    except ImportError as exc:
        raise QtUnavailableError(
            "PySide6 is unavailable; visual rendering was skipped"
        ) from exc


def _has_runtime_yaw_variants() -> bool:
    available_views = frozenset(VIEW_IDS)
    return all(
        view_id in available_views and (FULL_BODY_ROOT / f"{view_id}.png").is_file()
        for _scene_name, view_id in YAW_SCENE_VIEWS
    )


def scene_specs() -> tuple[SceneSpec, ...]:
    """Return the fixed scenes, adding yaw probes only when runtime has them."""

    if not _has_runtime_yaw_variants():
        return BASE_SCENE_SPECS
    return BASE_SCENE_SPECS + tuple(
        SceneSpec(
            scene_name,
            f"全身執行期 {view_id} 視角，抓轉身時的髮飾、衣裝與身體接縫。",
            view_id=view_id,
        )
        for scene_name, view_id in YAW_SCENE_VIEWS
    )


def _as_image(pixmap: QPixmap, label: str) -> QImage:
    if pixmap.isNull():
        raise RuntimeError(f"Rendered pixmap is null: {label}")
    return pixmap.toImage().convertToFormat(QImage.Format_ARGB32)


def _idle_full_body_motion() -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "idle_front",
        Viseme.CLOSED,
        MouthShape(),
        ExpressionShape(),
        breath=0.5,
    )


def render_scenes(
    scene_names: Sequence[str] | None = None,
) -> dict[str, QImage]:
    """Render requested scenes in memory through runtime composition paths."""

    _application()
    specs = scene_specs()
    by_name = {spec.name: spec for spec in specs}
    requested = tuple(scene_names or by_name)
    if len(set(requested)) != len(requested):
        raise ValueError("scene names must be unique")
    unknown = tuple(name for name in requested if name not in by_name)
    if unknown:
        raise ValueError(f"unknown visual baseline scene(s): {', '.join(unknown)}")

    requested_specs = tuple(by_name[name] for name in requested)
    needs_idle = any(
        spec.expression == "idle_front" or spec.crop is not None
        for spec in requested_specs
    )
    expression_names = {
        spec.expression for spec in requested_specs if spec.expression is not None
    }
    if any(spec.crop is not None for spec in requested_specs):
        expression_names.add("idle_front")

    images: dict[str, QImage] = {}
    with TemporaryDirectory(prefix="mohan-visual-baseline-") as temporary:
        overlay = ActiveOutfitOverlay(Path(temporary) / "store", ROOT)
        expression_images: dict[str, QImage] = {}
        for expression in sorted(expression_names):
            expression_images[expression] = render_portrait(overlay, expression)

        for spec in requested_specs:
            if spec.expression is not None:
                images[spec.name] = expression_images[spec.expression]
            elif spec.crop is not None:
                if not needs_idle:
                    raise RuntimeError("head crop has no idle source")
                images[spec.name] = (
                    expression_images["idle_front"]
                    .copy(*spec.crop)
                    .convertToFormat(QImage.Format_ARGB32)
                )

        yaw_specs = tuple(spec for spec in requested_specs if spec.view_id is not None)
        if yaw_specs:
            manifest = load_layered_full_body_assets(FULL_BODY_LAYERED_ROOT)
            renderer = LayeredFullBodyRenderer(
                manifest,
                outfit_overlay=overlay,
            )
            motion = _idle_full_body_motion()
            for spec in yaw_specs:
                view_id = spec.view_id
                if view_id is None:
                    raise RuntimeError(f"Yaw scene has no view id: {spec.name}")
                frame = renderer.render_view(view_id, motion)
                if frame.isNull():
                    raise RuntimeError(
                        f"Full-body renderer produced no frame: {view_id}"
                    )
                if overlay.layer_count(view_id) == 0:
                    raise RuntimeError(
                        f"No official appearance layers rendered: {view_id}"
                    )
                images[spec.name] = _as_image(frame, spec.name)
    return images


def _encode_png(image: QImage) -> bytes:
    payload = QByteArray()
    buffer = QBuffer(payload)
    try:
        if not buffer.open(QIODevice.WriteOnly):
            raise RuntimeError("Could not open an in-memory Qt PNG buffer")
        if not image.save(buffer, "PNG"):
            raise RuntimeError("Qt could not encode the visual baseline PNG")
        return bytes(payload)
    finally:
        buffer.close()


def _write_png(image: QImage, target: Path) -> tuple[str, int]:
    payload = _encode_png(image)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest(), len(payload)


@dataclass(frozen=True, slots=True)
class BaselineArtifact:
    scene: str
    reason: str
    path: Path
    sha256: str
    size_bytes: int


def write_baseline(
    scene_names: Sequence[str] | None = None,
    *,
    baseline_root: Path = BASELINE_ROOT,
) -> tuple[BaselineArtifact, ...]:
    """Render and write the requested baseline PNGs with Qt's PNG encoder."""

    specs = scene_specs()
    selected_names = tuple(scene_names or (spec.name for spec in specs))
    images = render_scenes(selected_names)
    by_name = {spec.name: spec for spec in specs}
    artifacts: list[BaselineArtifact] = []
    for name in selected_names:
        target = baseline_root / f"{name}.png"
        digest, size_bytes = _write_png(images[name], target)
        artifacts.append(
            BaselineArtifact(
                name,
                by_name[name].reason,
                target,
                digest,
                size_bytes,
            )
        )
    return tuple(artifacts)


def _difference_mask(
    baseline: QImage,
    current: QImage,
) -> tuple[bytearray, int, int]:
    if baseline.size() != current.size():
        raise ValueError(
            "baseline/current dimensions differ: "
            f"{baseline.width()}x{baseline.height()} vs "
            f"{current.width()}x{current.height()}"
        )
    first = baseline.convertToFormat(QImage.Format_RGBA8888)
    second = current.convertToFormat(QImage.Format_RGBA8888)
    first_bytes = bytes(first.constBits())
    second_bytes = bytes(second.constBits())
    width, height = first.width(), first.height()
    first_stride, second_stride = first.bytesPerLine(), second.bytesPerLine()
    mask = bytearray(width * height)
    difference_pixels = 0
    for y in range(height):
        first_row = y * first_stride
        second_row = y * second_stride
        mask_row = y * width
        for x in range(width):
            first_pixel = first_row + x * 4
            second_pixel = second_row + x * 4
            if any(
                abs(
                    first_bytes[first_pixel + channel]
                    - second_bytes[second_pixel + channel]
                )
                > DIFF_CHANNEL_THRESHOLD
                for channel in range(4)
            ):
                mask[mask_row + x] = 1
                difference_pixels += 1
    return mask, difference_pixels, width * height


def _largest_difference_block(
    mask: bytearray,
    width: int,
    height: int,
) -> tuple[int, tuple[int, int, int, int] | None]:
    visited = bytearray(len(mask))
    largest_pixels = 0
    largest_bbox: tuple[int, int, int, int] | None = None
    for start, is_difference in enumerate(mask):
        if not is_difference or visited[start]:
            continue
        stack = [start]
        visited[start] = 1
        pixel_count = 0
        left = top = width
        right = bottom = -1
        while stack:
            index = stack.pop()
            x, y = index % width, index // width
            pixel_count += 1
            left = min(left, x)
            top = min(top, y)
            right = max(right, x)
            bottom = max(bottom, y)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    neighbour_x, neighbour_y = x + dx, y + dy
                    if not (0 <= neighbour_x < width and 0 <= neighbour_y < height):
                        continue
                    neighbour = neighbour_y * width + neighbour_x
                    if mask[neighbour] and not visited[neighbour]:
                        visited[neighbour] = 1
                        stack.append(neighbour)
        bbox = (left, top, right - left + 1, bottom - top + 1)
        if pixel_count > largest_pixels:
            largest_pixels = pixel_count
            largest_bbox = bbox
    return largest_pixels, largest_bbox


def _write_difference_triptych(
    baseline: QImage,
    current: QImage,
    mask: bytearray,
    target: Path,
) -> None:
    width, height = baseline.width(), baseline.height()
    heatmap = QImage(width, height, QImage.Format_ARGB32)
    heatmap.fill(0xFF151515)
    for index, is_difference in enumerate(mask):
        if is_difference:
            heatmap.setPixel(index % width, index // width, 0xFFFF3B30)

    triptych = QImage(width * 3, height, QImage.Format_ARGB32)
    triptych.fill(0xFF101010)
    painter = QPainter(triptych)
    try:
        painter.drawImage(0, 0, baseline)
        painter.drawImage(width, 0, current)
        painter.drawImage(width * 2, 0, heatmap)
    finally:
        painter.end()
    _write_png(triptych, target)


@dataclass(frozen=True, slots=True)
class DifferenceReport:
    scene: str
    reason: str
    baseline_path: Path
    diff_path: Path
    baseline_sha256: str | None
    current_sha256: str
    current_size_bytes: int
    difference_pixels: int
    difference_ratio: float
    max_difference_block_area: int
    max_difference_bbox: tuple[int, int, int, int] | None
    passed: bool
    error: str | None = None


def _error_report(
    spec: SceneSpec,
    baseline_path: Path,
    diff_path: Path,
    current_sha256: str,
    current_size_bytes: int,
    error: str,
) -> DifferenceReport:
    return DifferenceReport(
        spec.name,
        spec.reason,
        baseline_path,
        diff_path,
        None,
        current_sha256,
        current_size_bytes,
        0,
        1.0,
        0,
        None,
        False,
        error,
    )


def _compare_scene(
    spec: SceneSpec,
    current: QImage,
    baseline_root: Path,
    diff_root: Path,
) -> DifferenceReport:
    current_payload = _encode_png(current)
    current_sha256 = hashlib.sha256(current_payload).hexdigest()
    baseline_path = baseline_root / f"{spec.name}.png"
    diff_path = diff_root / f"{spec.name}.diff.png"
    if not baseline_path.is_file():
        return _error_report(
            spec,
            baseline_path,
            diff_path,
            current_sha256,
            len(current_payload),
            "baseline PNG is missing",
        )

    baseline_payload = baseline_path.read_bytes()
    baseline = QImage(str(baseline_path))
    if baseline.isNull():
        return _error_report(
            spec,
            baseline_path,
            diff_path,
            current_sha256,
            len(current_payload),
            "baseline PNG could not be decoded by Qt",
        )

    baseline_sha256 = hashlib.sha256(baseline_payload).hexdigest()
    try:
        mask, difference_pixels, total_pixels = _difference_mask(
            baseline,
            current,
        )
    except ValueError as exc:
        return _error_report(
            spec,
            baseline_path,
            diff_path,
            current_sha256,
            len(current_payload),
            str(exc),
        )

    max_block_area, max_bbox = _largest_difference_block(
        mask,
        current.width(),
        current.height(),
    )
    difference_ratio = difference_pixels / total_pixels
    passed = (
        difference_ratio <= MAX_DIFFERENCE_RATIO
        and max_block_area <= MAX_DIFFERENCE_BLOCK_AREA
    )
    _write_difference_triptych(baseline, current, mask, diff_path)
    return DifferenceReport(
        spec.name,
        spec.reason,
        baseline_path,
        diff_path,
        baseline_sha256,
        current_sha256,
        len(current_payload),
        difference_pixels,
        difference_ratio,
        max_block_area,
        max_bbox,
        passed,
    )


def check_baseline(
    scene_names: Sequence[str] | None = None,
    *,
    baseline_root: Path = BASELINE_ROOT,
    diff_root: Path = DIFF_ROOT,
) -> tuple[DifferenceReport, ...]:
    """Render and compare scenes, writing one baseline/current/heatmap triptych each."""

    specs = scene_specs()
    selected_names = tuple(scene_names or (spec.name for spec in specs))
    images = render_scenes(selected_names)
    by_name = {spec.name: spec for spec in specs}
    diff_root.mkdir(parents=True, exist_ok=True)
    reports: list[DifferenceReport] = []
    for name in selected_names:
        reports.append(
            _compare_scene(
                by_name[name],
                images[name],
                baseline_root,
                diff_root,
            )
        )
    return tuple(reports)


def _shown(path: Path) -> str:
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def _shown_bbox(bbox: tuple[int, int, int, int] | None) -> str:
    return "none" if bbox is None else "(" + ",".join(map(str, bbox)) + ")"


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n", maxsplit=1)[0],
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--write",
        action="store_true",
        help="render and replace the tracked baseline PNGs",
    )
    modes.add_argument(
        "--check",
        action="store_true",
        help="render, compare and write ignored difference triptychs",
    )
    return parser.parse_args(argv)


def _print_check_report(report: DifferenceReport) -> None:
    status = "PASS" if report.passed else "FAIL"
    error = f" error={report.error}" if report.error else ""
    print(
        f"CHECK scene={report.scene} reason={report.reason} "
        f"diff_pixels={report.difference_pixels} "
        f"diff_ratio={report.difference_ratio * 100:.6f}% "
        f"max_block_area={report.max_difference_block_area} "
        f"max_bbox={_shown_bbox(report.max_difference_bbox)} "
        f"current_sha256={report.current_sha256[:12]} "
        f"current_size={report.current_size_bytes} "
        f"diff_path={_shown(report.diff_path)} status={status}{error}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _arguments(argv)
    try:
        if arguments.write:
            artifacts = write_baseline()
            print(
                "BASELINE_POLICY source=main includes_known_defects=true "
                "rerun=--write after #185 merge"
            )
            for artifact in artifacts:
                print(
                    f"WRITE scene={artifact.scene} reason={artifact.reason} "
                    f"sha256={artifact.sha256[:12]} "
                    f"size={artifact.size_bytes} "
                    f"path={_shown(artifact.path)}"
                )
            print(f"VISUAL_BASELINE_WRITE_OK count={len(artifacts)}")
            return 0

        reports = check_baseline()
        for report in reports:
            _print_check_report(report)
        failed = tuple(report for report in reports if not report.passed)
        if failed:
            print(f"VISUAL_BASELINE_CHECK_FAILED count={len(failed)}")
            return 1
        print(f"VISUAL_BASELINE_CHECK_OK count={len(reports)}")
        return 0
    except QtUnavailableError as exc:
        print(f"VISUAL_BASELINE_QT_UNAVAILABLE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
