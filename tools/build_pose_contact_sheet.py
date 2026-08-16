from __future__ import annotations

lazy import argparse
lazy import json
lazy import os
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import QRect, Qt

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen

lazy from pose_atlas_audit import (
    AtlasLayerEvidence,
    AtlasViewEvidence,
    PoseAtlasAuditReport,
    audit_pose_atlas,
)

_GUI_APPLICATION: QGuiApplication | None = None


def _gui_application() -> QGuiApplication:
    global _GUI_APPLICATION
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    _GUI_APPLICATION = QGuiApplication([])
    return _GUI_APPLICATION


class ManifestHandAudit:
    def __init__(self, results: dict[str, bool]) -> None:
        self._results = results

    def passed(self, view_id: str) -> bool:
        return self._results.get(view_id, False)


def load_manifest(path: Path) -> tuple[tuple[AtlasViewEvidence, ...], ManifestHandAudit]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    views = []
    for entry in payload["views"]:
        rgba = (base / entry["rgba_path"]).read_bytes()
        views.append(
            AtlasViewEvidence(
                entry["view_id"],
                int(entry["yaw_degrees"]),
                int(entry["width"]),
                int(entry["height"]),
                int(entry["anchor"][0]),
                int(entry["anchor"][1]),
                tuple(int(value) for value in entry["alpha_bounds"]),
                str(entry["identity_lock_evidence"]),
                rgba,
                tuple(
                    AtlasLayerEvidence(
                        layer["role"],
                        int(layer["depth"]),
                        layer["owner"],
                        layer["manifest_evidence"],
                    )
                    for layer in entry["layers"]
                ),
            )
        )
    return tuple(views), ManifestHandAudit(
        {str(key): bool(value) for key, value in payload["hand_audit"].items()}
    )


def build_contact_sheet(report: PoseAtlasAuditReport, output: Path) -> None:
    _gui_application()
    if not report.views:
        raise ValueError("A contact sheet requires audited views.")
    columns, tile_width, tile_height, label_height = 6, 180, 180, 42
    sheet = QImage(
        columns * tile_width,
        ((len(report.views) + columns - 1) // columns)
        * (tile_height + label_height),
        QImage.Format_RGBA8888,
    )
    sheet.fill(QColor("#101722"))
    metric_by_yaw = {metric.first_yaw: metric for metric in report.adjacent_metrics}
    painter = QPainter(sheet)
    painter.setPen(QPen(QColor("#dbe8f4")))
    for index, view in enumerate(report.views):
        column, row = index % columns, index // columns
        x, y = column * tile_width, row * (tile_height + label_height)
        image = QImage(view.rgba, view.width, view.height, view.width * 4, QImage.Format_RGBA8888).copy()
        scaled = image.scaled(tile_width, tile_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawImage(QRect(x, y, tile_width, tile_height), scaled)
        metric = metric_by_yaw.get(view.yaw_degrees)
        label = f"{view.yaw_degrees:+04d}°  {view.view_id}"
        if metric is not None:
            label += f"\nΔoutline {metric.outline_displacement}  Δcolor {metric.mean_color_delta:.2f}"
        painter.drawText(QRect(x + 4, y + tile_height, tile_width - 8, label_height), Qt.AlignCenter, label)
    painter.end()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not sheet.save(str(output)):
        raise OSError(f"Could not save contact sheet: {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an offline audited 360-degree pose contact sheet.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    views, hands = load_manifest(arguments.manifest.resolve())
    report = audit_pose_atlas(views, hands)
    if not report.passed:
        for problem in report.problems:
            print(problem, file=sys.stderr)
        return 2
    build_contact_sheet(report, arguments.output.resolve())
    print(arguments.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
