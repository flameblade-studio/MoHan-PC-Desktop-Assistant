"""Fail-closed loading and role selection for reviewed pose motion assets."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from infrastructure.reviewed_pose_motion import (
    APPROVED_SOURCE_SHA256,
    DIMENSION,
    SCHEMA,
    load_reviewed_pose_motion,
)


BODY_COLOR = QColor(20, 30, 40, 255)
BODY_POINT = (7, 7)
PROBE = (25, 25)
SLOT_COLORS = {
    ("rest", "eyes"): QColor(10, 20, 30, 255),
    ("rest", "cheeks"): QColor(40, 50, 60, 255),
    ("rest", "lips"): QColor(70, 80, 90, 255),
    ("closed", "eyes"): QColor(100, 110, 120, 255),
    ("closed", "cheeks"): QColor(130, 140, 150, 255),
    ("closed", "lips"): QColor(160, 170, 180, 255),
    ("speech", "eyes"): QColor(190, 200, 210, 255),
    ("speech", "cheeks"): QColor(220, 230, 240, 255),
    ("speech", "lips"): QColor(245, 120, 80, 255),
}


@pytest.fixture(scope="module", autouse=True)
def _qt_application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _png(color: QColor, point: tuple[int, int]) -> bytes:
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    image.setPixelColor(*point, color)
    output = QByteArray()
    buffer = QBuffer(output)
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(output)


def _record(root: Path, relative: str, payload: bytes) -> dict[str, str]:
    path = root / Path(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "path": relative,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _write_fixture(root: Path, *, include_mouth_cavity: bool = True) -> tuple[dict, str]:
    root.mkdir(parents=True, exist_ok=True)
    body = _png(BODY_COLOR, BODY_POINT)
    body_record = _record(root, "body.rgba.png", body)
    cosmetics: dict[str, dict[str, dict[str, str]]] = {}
    for state in ("rest", "closed", "speech"):
        cosmetics[state] = {}
        for slot in ("eyes", "cheeks", "lips"):
            relative = f"cosmetics/{state}/{slot}.rgba.png"
            payload = _png(SLOT_COLORS[(state, slot)], PROBE)
            cosmetics[state][slot] = _record(root, relative, payload)

    manifest: dict = {
        "schema": SCHEMA,
        "source_sha256": APPROVED_SOURCE_SHA256,
        "native_body_sha256": body_record["sha256"],
        "native_body": body_record,
        "closed": _record(root, "motion/closed.rgba.png", _png(QColor("red"), PROBE)),
        "speech": _record(root, "motion/speech.rgba.png", _png(QColor("blue"), PROBE)),
        "cosmetics": cosmetics,
    }
    if include_mouth_cavity:
        manifest["mouth_cavity"] = _record(
            root,
            "motion/mouth-cavity.rgba.png",
            _png(QColor("black"), PROBE),
        )
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest, body_record["sha256"]


def _rewrite(root: Path, manifest: dict) -> None:
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_missing_or_existing_invalid_root_fails_closed(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="missing"):
        load_reviewed_pose_motion(tmp_path / "missing", expected_native_body_sha256="0" * 64)
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(ValueError, match="manifest"):
        load_reviewed_pose_motion(existing, expected_native_body_sha256="0" * 64)


def test_loader_pins_source_and_native_body_and_caches_optional_cavity(tmp_path: Path) -> None:
    root = tmp_path / "reviewed-pose-motion"
    manifest, body_sha = _write_fixture(root)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)
    assert assets is not None
    assert assets.source_sha256 == APPROVED_SOURCE_SHA256
    assert assets.native_body_sha256 == body_sha
    assert assets.native_body is not None
    assert assets.native_body.path == manifest["native_body"]["path"]
    assert assets.mouth_cavity is not None


def test_patch_and_cosmetic_roles_include_speech_closed_selection(tmp_path: Path) -> None:
    root = tmp_path / "reviewed-pose-motion"
    _, body_sha = _write_fixture(root)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)
    assert assets is not None

    assert assets.patch("closed").toImage().pixelColor(*PROBE) == QColor("red")
    assert assets.patch("speech").toImage().pixelColor(*PROBE) == QColor("blue")
    assert (
        assets.cosmetic("speech-closed", "eyes").toImage().pixelColor(*PROBE)
        == SLOT_COLORS[("closed", "eyes")]
    )
    assert (
        assets.cosmetic("speech-closed", "cheeks").toImage().pixelColor(*PROBE)
        == SLOT_COLORS[("rest", "cheeks")]
    )
    for slot in ("lips",):
        assert (
            assets.cosmetic("speech-closed", slot).toImage().pixelColor(*PROBE)
            == SLOT_COLORS[("speech", slot)]
        )
    assert (
        assets.cosmetic("rest", "eyes").toImage().pixelColor(*PROBE)
        == SLOT_COLORS[("rest", "eyes")]
    )
    with pytest.raises(ValueError):
        assets.patch("rest")
    with pytest.raises(ValueError):
        assets.cosmetic("unknown", "eyes")


def test_decoded_assets_do_not_read_drifted_files_per_frame(tmp_path: Path) -> None:
    root = tmp_path / "reviewed-pose-motion"
    manifest, body_sha = _write_fixture(root)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)
    assert assets is not None
    closed_path = root / Path(*manifest["closed"]["path"].split("/"))
    closed_path.write_bytes(_png(QColor("green"), PROBE))
    assert assets.patch("closed").toImage().pixelColor(*PROBE) == QColor("red")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)


@pytest.mark.parametrize("path", ["../outside.png", "C:/outside.png", "\\outside.png"])
def test_asset_paths_cannot_escape_manifest_root(tmp_path: Path, path: str) -> None:
    root = tmp_path / "reviewed-pose-motion"
    manifest, body_sha = _write_fixture(root)
    manifest["closed"]["path"] = path
    _rewrite(root, manifest)
    with pytest.raises(ValueError, match="path"):
        load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)


def test_asset_sha_drift_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "reviewed-pose-motion"
    manifest, body_sha = _write_fixture(root)
    manifest["speech"]["sha256"] = "0" * 64
    _rewrite(root, manifest)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)


def test_asset_dimensions_must_be_1254_rgba(tmp_path: Path) -> None:
    root = tmp_path / "reviewed-pose-motion"
    manifest, body_sha = _write_fixture(root)
    relative = manifest["cosmetics"]["rest"]["eyes"]["path"]
    path = root / Path(*relative.split("/"))
    tiny = QImage(1, 1, QImage.Format.Format_RGBA8888)
    tiny.fill(QColor("white"))
    output = QByteArray()
    buffer = QBuffer(output)
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert tiny.save(buffer, "PNG")
    payload = bytes(output)
    path.write_bytes(payload)
    manifest["cosmetics"]["rest"]["eyes"]["sha256"] = hashlib.sha256(payload).hexdigest()
    _rewrite(root, manifest)
    with pytest.raises(ValueError, match="1254x1254"):
        load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)


def test_native_body_expected_digest_is_required_and_no_fallback_is_used(tmp_path: Path) -> None:
    root = tmp_path / "reviewed-pose-motion"
    _, body_sha = _write_fixture(root, include_mouth_cavity=False)
    with pytest.raises(ValueError, match="native body SHA-256 mismatch"):
        load_reviewed_pose_motion(root, expected_native_body_sha256="1" * 64)
    assets = load_reviewed_pose_motion(root, expected_native_body_sha256=body_sha)
    assert assets is not None
    assert assets.mouth_cavity is None
