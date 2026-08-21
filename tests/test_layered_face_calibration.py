from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure.layered_face_assets import load_layered_face_assets
lazy from infrastructure.layered_face_calibration import (
    MAX_ANCHOR_DRIFT_PIXELS,
    calibrate_layered_face_assets,
)

LAYERED_DIR = ROOT / "assets" / "expressions" / "layered"


def _app() -> object:
    return QApplication.instance() or QApplication([])


def test_calibration_accepts_authored_layers() -> None:
    _app()
    manifest = load_layered_face_assets(LAYERED_DIR)
    # Must not raise: every authored layer's center lands inside its base.
    calibrate_layered_face_assets(manifest)


def test_max_anchor_drift_is_one_pixel() -> None:
    assert MAX_ANCHOR_DRIFT_PIXELS == 1


def run() -> None:
    test_calibration_accepts_authored_layers()
    test_max_anchor_drift_is_one_pixel()
    print("LAYERED_FACE_CALIBRATION_OK")


if __name__ == "__main__":
    run()
