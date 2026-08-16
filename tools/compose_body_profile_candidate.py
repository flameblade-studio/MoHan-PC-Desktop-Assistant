from __future__ import annotations

lazy import argparse
lazy import json
lazy from pathlib import Path

lazy from PySide6.QtCore import QPointF, Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath

FRONT_TORSO_POLYGON = (
    (0.410, 0.600),
    (0.590, 0.600),
    (0.640, 0.775),
    (0.590, 0.805),
    (0.410, 0.805),
    (0.360, 0.775),
)
FEATHER_FRACTION = 0.08
FEATHER_STEPS = 20


def _load_rgba(path: Path) -> QImage:
    image = QImage(str(path)).convertToFormat(QImage.Format_RGBA8888)
    if image.isNull():
        raise ValueError(f"Unable to read image: {path}")
    return image


def _torso_mask(width: int, height: int) -> QImage:
    mask = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
    mask.fill(Qt.transparent)
    painter = QPainter(mask)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setCompositionMode(QPainter.CompositionMode_Source)
    center_x = sum(point[0] for point in FRONT_TORSO_POLYGON) / len(
        FRONT_TORSO_POLYGON
    )
    center_y = sum(point[1] for point in FRONT_TORSO_POLYGON) / len(
        FRONT_TORSO_POLYGON
    )
    for step in range(FEATHER_STEPS + 1):
        inset = FEATHER_FRACTION * step / FEATHER_STEPS
        scale = 1.0 - inset
        points = tuple(
            (
                center_x + (x - center_x) * scale,
                center_y + (y - center_y) * scale,
            )
            for x, y in FRONT_TORSO_POLYGON
        )
        path = QPainterPath()
        first_x, first_y = points[0]
        path.moveTo(first_x * width, first_y * height)
        for x, y in points[1:]:
            path.lineTo(QPointF(x * width, y * height))
        path.closeSubpath()
        alpha = max(1, round(255 * step / FEATHER_STEPS))
        painter.setBrush(QColor(255, 255, 255, alpha))
        painter.drawPath(path)
    painter.end()
    return mask


def _clipped_layer(image: QImage, mask: QImage) -> QImage:
    """Return one source image clipped to the explicitly approved region."""

    layer = QImage(image)
    painter = QPainter(layer)
    painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, mask)
    painter.end()
    return layer


def compose_candidate(
    base_path: Path,
    donor_path: Path,
    output_path: Path,
    protected_overlays: tuple[Path, ...] = (),
) -> dict[str, object]:
    """Replace only the approved torso while preserving core identity pixels."""

    base = _load_rgba(base_path)
    donor = _load_rgba(donor_path)
    if donor.size() != base.size():
        raise ValueError("Base and donor images must use the same canvas.")
    mask = _torso_mask(base.width(), base.height())
    result = QImage(base)
    painter = QPainter(result)
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    painter.drawImage(0, 0, _clipped_layer(donor, mask))
    for overlay_path in protected_overlays:
        overlay = _load_rgba(overlay_path)
        if overlay.size() != base.size():
            raise ValueError("Protected overlays must use the base canvas.")
        painter.drawImage(0, 0, _clipped_layer(overlay, mask))
    painter.end()

    outside_changed = 0
    inside_changed = 0
    base_bits = base.constBits()
    result_bits = result.constBits()
    mask_bits = mask.constBits()
    for index in range(base.width() * base.height()):
        offset = index * 4
        changed = base_bits[offset : offset + 4] != result_bits[offset : offset + 4]
        if not changed:
            continue
        if mask_bits[offset + 3] == 0:
            outside_changed += 1
        else:
            inside_changed += 1
    if outside_changed:
        raise AssertionError("Protected pixels changed outside the torso mask.")
    if inside_changed == 0:
        raise AssertionError("The candidate did not alter the approved torso.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not result.save(str(output_path), "PNG"):
        raise OSError(f"Unable to save image: {output_path}")
    return {
        "base": str(base_path),
        "donor": str(donor_path),
        "output": str(output_path),
        "canvas": [base.width(), base.height()],
        "changed_inside_mask": inside_changed,
        "changed_outside_mask": outside_changed,
        "protected_overlays": [str(path) for path in protected_overlays],
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compose a protected MoHan body-profile art candidate."
    )
    parser.add_argument("base", type=Path)
    parser.add_argument("donor", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--protect", type=Path, action="append", default=[])
    parser.add_argument("--audit", type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = _arguments()
    audit = compose_candidate(
        arguments.base,
        arguments.donor,
        arguments.output,
        tuple(arguments.protect),
    )
    if arguments.audit is not None:
        arguments.audit.parent.mkdir(parents=True, exist_ok=True)
        arguments.audit.write_text(
            json.dumps(audit, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(json.dumps(audit, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
