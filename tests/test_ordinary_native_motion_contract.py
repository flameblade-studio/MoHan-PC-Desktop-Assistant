"""Regression coverage for the source-bound ordinary native motion contract."""

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
    FOUNDATION_COSMETIC_SLOTS,
    VARIANT_SCHEMA,
    load_reviewed_pose_motion,
)


POINT = (17, 17)
LOOKS = ("light", "classic", "glamorous")
STATES = ("rest", "closed")


@pytest.fixture(scope="module", autouse=True)
def _qt_application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _png(color: QColor, *, grayscale: bool = False) -> bytes:
    image_format = (
        QImage.Format.Format_Grayscale8
        if grayscale
        else QImage.Format.Format_RGBA8888
    )
    image = QImage(DIMENSION, DIMENSION, image_format)
    image.fill(Qt.GlobalColor.transparent if not grayscale else 0)
    image.setPixelColor(*POINT, color)
    output = QByteArray()
    buffer = QBuffer(output)
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(output)


def _record(root: Path, relative: str, payload: bytes) -> dict[str, str]:
    path = root / Path(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"path": relative, "sha256": hashlib.sha256(payload).hexdigest()}


def _write_fixture(root: Path) -> tuple[dict, str, str]:
    """Write a small, deterministic ordinary-native v3 fixture."""

    body = _record(root, "body.rgba.png", _png(QColor("#182838")))
    closed = _record(root, "closed.rgba.png", _png(QColor("#203040")))
    half = {
        "native_endpoint": _record(
            root, "half/native-endpoint.rgba.png", _png(QColor("#304050"))
        ),
        "patch": _record(
            root, "half/patch.rgba.png", _png(QColor("#405060"))
        ),
        "eye_support": _record(
            root, "half/eye-support.rgba.png", _png(QColor("#506070"))
        ),
        "eye_aperture": _record(
            root, "half/eye-aperture.rgba.png", _png(QColor("#607080"))
        ),
        "coverage": _record(
            root,
            "half/coverage.png",
            _png(QColor(255, 255, 255), grayscale=True),
        ),
        "oral_cavity": _record(
            root,
            "half/oral-cavity.png",
            _png(QColor(255, 255, 255), grayscale=True),
        ),
    }
    variant_cosmetics: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
    for look_index, look in enumerate(LOOKS):
        variant_cosmetics[look] = {}
        for state_index, state in enumerate(STATES):
            variant_cosmetics[look][state] = {}
            for slot_index, slot in enumerate(FOUNDATION_COSMETIC_SLOTS):
                color = QColor(
                    20 + look_index * 30 + state_index * 10 + slot_index,
                    30 + look_index * 30 + state_index * 10 + slot_index,
                    40 + look_index * 30 + state_index * 10 + slot_index,
                    255,
                )
                variant_cosmetics[look][state][slot] = _record(
                    root,
                    f"cosmetics/{look}/{state}/{slot}.rgba.png",
                    _png(color),
                )
    half_cosmetics: dict[str, dict[str, str]] = {}
    for look_index, look in enumerate(LOOKS):
        half_cosmetics[look] = {}
        for slot_index, slot in enumerate(FOUNDATION_COSMETIC_SLOTS):
            half_cosmetics[look][slot] = _record(
                root,
                f"half/cosmetics/{look}/{slot}.rgba.png",
                _png(QColor(110 + look_index * 20 + slot_index, 120, 130)),
            )

    source_sha = "a" * 64
    manifest = {
        "schema": VARIANT_SCHEMA,
        "source_kind": "ordinary_native",
        "source_sha256": source_sha,
        "native_body_sha256": body["sha256"],
        "native_body": body,
        "closed": closed,
        "cosmetics": variant_cosmetics,
        "half": {**half, "cosmetics": half_cosmetics},
        "motion_state_policy": {
            "available": ["rest", "half", "closed"],
            "speech": "missing_ordinary_native_mouth_source",
            "no_fabricated_states": True,
        },
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest, body["sha256"], source_sha


def _load(root: Path, body_sha: str, source_sha: str):
    return load_reviewed_pose_motion(
        root,
        expected_native_body_sha256=body_sha,
        expected_source_sha256=source_sha,
    )


def test_ordinary_native_loads_half_inputs_and_explicitly_lacks_speech(
    tmp_path: Path,
) -> None:
    root = tmp_path / "motion"
    _, body_sha, source_sha = _write_fixture(root)
    assets = _load(root, body_sha, source_sha)

    assert set(assets.patches) == {"closed"}
    assert set(assets.half_inputs or {}) == {
        "native_endpoint",
        "patch",
        "eye_support",
        "eye_aperture",
        "coverage",
        "oral_cavity",
    }
    assert set(assets.variants or {}) == set(LOOKS)
    for variant in assets.variants or {}:
        assert set(assets.variants[variant]) == {"rest", "closed", "half"}
        assert set(assets.variants[variant]["half"]) == set(
            FOUNDATION_COSMETIC_SLOTS
        )
    with pytest.raises(ValueError, match="unavailable.*speech|speech.*unavailable"):
        assets.patch("speech")
    with pytest.raises(ValueError, match="unavailable.*speech|speech.*unavailable"):
        assets.cosmetic("speech", "eyes", variant="glamorous")


def test_half_endpoint_is_required_and_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "motion"
    _, body_sha, source_sha = _write_fixture(root)
    (root / "half" / "patch.rgba.png").unlink()

    with pytest.raises(
        ValueError,
        match="half/patch|Missing reviewed pose motion asset",
    ):
        _load(root, body_sha, source_sha)


def test_half_cosmetics_are_required_and_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "motion"
    manifest, body_sha, source_sha = _write_fixture(root)
    manifest["half"]["cosmetics"]["classic"].pop("eyes")
    (root / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="HALF cosmetics"):
        _load(root, body_sha, source_sha)


def test_fixture_source_digest_remains_explicitly_bound(tmp_path: Path) -> None:
    root = tmp_path / "motion"
    _, body_sha, _ = _write_fixture(root)

    with pytest.raises(ValueError, match="approved source"):
        load_reviewed_pose_motion(
            root,
            expected_native_body_sha256=body_sha,
            expected_source_sha256=APPROVED_SOURCE_SHA256,
        )
