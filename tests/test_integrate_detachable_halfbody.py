from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication

from infrastructure.detachable_halfbody_assets import (
    DIMENSION,
    PART_ORDER,
    POSES,
    load_detachable_halfbody_assets,
)
from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme
from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer
from tools.art_pipeline.integrate_detachable_halfbody import integrate_detachable_halfbody


def _candidate(root: Path) -> str:
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    records = []
    for pose in sorted(POSES):
        directory = root / pose
        directory.mkdir(parents=True)
        for part in PART_ORDER:
            relative = f"{pose}/{part}.rgba.png"
            target = root / relative
            image.setPixelColor(0, 0, QColor("red") if part == "torso" else QColor(0, 0, 0, 0))
            assert image.save(str(target))
            records.append({
                "pose": pose,
                "role": part,
                "output": relative,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            })
    receipt = {
        "stage": "detachable_candidates_repaired",
        "source_art_owner_approved": True,
        "technical_seam_verified": True,
        "formal_integration": False,
        "layers": records,
    }
    payload = (json.dumps(receipt) + "\n").encode()
    (root / "receipt.json").write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def test_install_and_compose_all_seven_poses(tmp_path: Path) -> None:
    _ = QApplication.instance() or QApplication([])
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    receipt_sha = _candidate(candidate)
    target = tmp_path / "formal"
    backup = tmp_path / "backup"
    receipt = integrate_detachable_halfbody(
        candidate, target, backup,
        expected_receipt_sha256=receipt_sha,
        owner_authorization_text="Owner authorized current integration",
    )
    assert receipt.is_file()
    assets = load_detachable_halfbody_assets(target)
    assert assets is not None
    for pose in POSES:
        assert assets.compose(pose).size().width() == DIMENSION
        assert assets.compose(pose, hidden=frozenset({"hair"})).size().height() == DIMENSION
    (target / "cheek-rest" / "torso.rgba.png").write_bytes(b"changed after validation")
    assert assets.compose("cheek-rest").toImage().pixelColor(0, 0) == QColor("red")
    with pytest.raises(ValueError, match="digest mismatch"):
        load_detachable_halfbody_assets(target)
    assert json.loads(receipt.read_text())["release"] is False


def test_runtime_selects_all_seven_detachable_poses(tmp_path: Path) -> None:
    _ = QApplication.instance() or QApplication([])
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    receipt_sha = _candidate(candidate)
    target = tmp_path / "formal"
    integrate_detachable_halfbody(
        candidate, target, tmp_path / "backup",
        expected_receipt_sha256=receipt_sha,
        owner_authorization_text="Owner authorized current integration",
    )
    renderer = LayeredParametricFaceRenderer(detachable_dir=target)
    base = QPixmap(DIMENSION, DIMENSION)
    base.fill(Qt.GlobalColor.transparent)
    mouth = QImage(DIMENSION, DIMENSION, QImage.Format.Format_ARGB32)
    mouth.fill(Qt.GlobalColor.transparent)
    mouth.setPixelColor(5, 5, QColor("green"))
    mouth_mask = QImage(DIMENSION, DIMENSION, QImage.Format.Format_ARGB32)
    mouth_mask.fill(Qt.GlobalColor.transparent)
    mouth_mask.setPixelColor(5, 5, QColor("white"))
    speech_layers = SimpleNamespace(
        mouth_source=QPixmap.fromImage(mouth),
        mouth_mask=QPixmap.fromImage(mouth_mask),
    )
    blink = QImage(DIMENSION, DIMENSION, QImage.Format.Format_ARGB32)
    blink.fill(Qt.GlobalColor.transparent)
    blink.setPixelColor(10, 10, QColor("blue"))
    cases = (
        ("front-crossed", FacePose.FRONT, "idle_front"),
        ("left-neutral", FacePose.LEAN, "idle_lean"),
        ("cheek-rest", FacePose.CHEEK, "idle"),
        ("front-mock-scold", FacePose.FRONT, "mock_scold"),
        ("front-mock-hit", FacePose.FRONT, "mock_hit_front"),
        ("front-eureka", FacePose.FRONT, "eureka_front"),
        ("front-exasperated", FacePose.FRONT, "exasperated_front"),
    )
    for _, pose, expression in cases:
        motion = FaceMotionFrame(pose, expression, Viseme.CLOSED, MouthShape(), ExpressionShape())
        frame = renderer.render(base, motion, None)
        assert frame.toImage().pixelColor(0, 0) == QColor("red")
        speaking = FaceMotionFrame(
            pose, expression, Viseme.A, MouthShape(aperture=1.0), ExpressionShape(blink=1.0)
        )
        spoken = renderer.render(base, speaking, speech_layers)
        assert spoken.toImage().pixelColor(5, 5).green() > 0
        blinked = renderer.render_overlay(spoken, QPixmap.fromImage(blink))
        assert blinked.toImage().pixelColor(10, 10) == QColor("blue")


def test_integrator_rejects_candidate_drift_without_touching_formal_assets(tmp_path: Path) -> None:
    _ = QApplication.instance() or QApplication([])
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    receipt_sha = _candidate(candidate)
    (candidate / "cheek-rest" / "head.rgba.png").write_bytes(b"drift")
    target = tmp_path / "formal"
    target.mkdir()
    (target / "existing.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="drifted"):
        integrate_detachable_halfbody(
            candidate, target, tmp_path / "backup",
            expected_receipt_sha256=receipt_sha,
            owner_authorization_text="Owner authorized current integration",
        )
    assert (target / "existing.txt").read_text(encoding="utf-8") == "keep"


def test_invalid_installed_manifest_fails_closed(tmp_path: Path) -> None:
    tmp_path.joinpath("manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest"):
        load_detachable_halfbody_assets(tmp_path)
