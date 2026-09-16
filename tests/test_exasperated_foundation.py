"""Regression gates for the source-bound exasperated foundation slot."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from infrastructure import exasperated_candidate_appearance as appearance_module
lazy from infrastructure.exasperated_candidate_appearance import (
    FOUNDATION_SCHEMA,
    SCHEMA,
    SLOTS,
    SLOTS_V2,
    STATES,
    ExasperatedCandidateAppearance,
)
lazy from infrastructure.exasperated_candidate_assets import APPROVED_SOURCE_SHA256, DIMENSION

AVAILABLE_STATUS = "available"
BASE_COLOR = QColor("#293241")
FOUNDATION_COLOR = QColor("#e9c46a")
EYES_COLOR = QColor("#264653")
CHEEKS_COLOR = QColor("#e76f51")
LIPS_COLOR = QColor("#e63946")
FOUNDATION_RECT = QRect(100, 100, 40, 40)
EYES_RECT = QRect(115, 115, 15, 15)
CHEEKS_RECT = QRect(200, 200, 15, 15)
LIPS_RECT = QRect(300, 300, 15, 15)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _write_png(root: Path, relative: str, rectangle: QRect, color: QColor) -> dict[str, str]:
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        painter.fillRect(rectangle, color)
    finally:
        painter.end()
    path = root / Path(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path), "PNG")
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _manifest(root: Path, *, schema: str) -> dict[str, object]:
    slots = SLOTS_V2 if schema == FOUNDATION_SCHEMA else SLOTS
    layers: dict[str, dict[str, str]] = {
        "garment": _write_png(root, "garment.rgba.png", QRect(), QColor("#ffffff")),
        "replace_mask": _write_png(root, "replace_mask.rgba.png", QRect(), QColor("#ffffff")),
    }
    colors = {
        "foundation": FOUNDATION_COLOR,
        "eyes": EYES_COLOR,
        "cheeks": CHEEKS_COLOR,
        "lips": LIPS_COLOR,
    }
    rectangles = {
        "foundation": FOUNDATION_RECT,
        "eyes": EYES_RECT,
        "cheeks": CHEEKS_RECT,
        "lips": LIPS_RECT,
    }
    for state in STATES:
        for slot in slots:
            relative = f"{state}/{slot}.rgba.png"
            layers[f"{state}/{slot}"] = _write_png(
                root,
                relative,
                rectangles[slot],
                colors[slot],
            )
    manifest: dict[str, object] = {
        "schema": schema,
        "source_sha256": APPROVED_SOURCE_SHA256,
        "cosmetic_status": AVAILABLE_STATUS,
        "layers": layers,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return manifest


def _frame(*, fill: QColor = BASE_COLOR) -> QPixmap:
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGBA8888)
    image.fill(fill)
    return QPixmap.fromImage(image)


def _rgba_bytes(pixmap: QPixmap) -> bytes:
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    return bytes(image.constBits())


def _load(root: Path, *, schema: str = FOUNDATION_SCHEMA) -> ExasperatedCandidateAppearance:
    _app()
    _manifest(root, schema=schema)
    return ExasperatedCandidateAppearance.load(root)


@pytest.mark.parametrize("mutation", ("missing_foundation", "foundation_digest", "source_sha256"))
def test_v2_requires_foundation_and_approved_source_digest(tmp_path: Path, mutation: str) -> None:
    _app()
    manifest = _manifest(tmp_path, schema=FOUNDATION_SCHEMA)
    layers = manifest["layers"]
    assert isinstance(layers, dict)
    if mutation == "missing_foundation":
        del layers["rest/foundation"]
        expected = "clothing and all mouth-specific cosmetics"
    elif mutation == "foundation_digest":
        record = layers["rest/foundation"]
        assert isinstance(record, dict)
        record["sha256"] = "0" * 64
        expected = "digest mismatch"
    else:
        manifest["source_sha256"] = "f" * 64
        expected = "approved exasperated source"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match=expected):
        ExasperatedCandidateAppearance.load(tmp_path)


def test_v1_keeps_the_three_slot_contract(tmp_path: Path) -> None:
    appearance = _load(tmp_path, schema=SCHEMA)

    assert appearance.schema == SCHEMA
    assert appearance.cosmetic_slots == SLOTS
    appearance.set_makeup_intensities(dict.fromkeys(SLOTS, 1.0))
    with pytest.raises(ValueError, match="configured slots"):
        appearance.set_makeup_intensities(dict.fromkeys(SLOTS_V2, 1.0))


def test_v2_paints_foundation_before_features_and_supports_bare_removal(tmp_path: Path) -> None:
    appearance = _load(tmp_path)
    appearance.garment_enabled = False
    appearance.set_makeup_intensities(dict.fromkeys(SLOTS_V2, 1.0))

    result = appearance.apply(_frame(), "front-exasperated").toImage()

    assert appearance.cosmetic_slots == SLOTS_V2
    assert result.pixelColor(105, 105) == FOUNDATION_COLOR
    assert result.pixelColor(120, 120) == EYES_COLOR
    assert result.pixelColor(205, 205) == CHEEKS_COLOR
    assert result.pixelColor(305, 305) == LIPS_COLOR

    appearance.set_makeup_intensities(dict.fromkeys(SLOTS_V2, 0.0))
    assert _rgba_bytes(appearance.apply(_frame(), "front-exasperated")) == _rgba_bytes(_frame())


def test_v2_light_variant_scales_all_slots_once_and_removal_clears_foundation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    appearance = _load(tmp_path)
    appearance.store = tmp_path
    selection = SimpleNamespace(
        effective_pack_id=appearance_module.BUILTIN_MAKEUP_PACK_ID,
        effective_variant_id="light",
    )
    captured: dict[str, frozenset[str]] = {}
    monkeypatch.setattr(
        appearance_module,
        "resolve_active_selection",
        lambda _store, category: (
            selection
            if category == "makeup"
            else SimpleNamespace(effective_pack_id="builtin")
        ),
    )
    monkeypatch.setattr(appearance_module, "read_makeup_intensity", lambda _store: 1.0)

    def read_slots(_store: Path, *, slots: frozenset[str]) -> dict[str, float]:
        captured["slots"] = slots
        return dict.fromkeys(slots, 1.0)

    monkeypatch.setattr(appearance_module, "read_makeup_slot_intensities", read_slots)
    appearance.apply(_frame(), "front-exasperated")

    assert captured["slots"] == frozenset(SLOTS_V2)
    assert appearance.makeup_intensities == pytest.approx(dict.fromkeys(SLOTS_V2, 0.55))

    selection.effective_pack_id = "builtin"
    removed = appearance.apply(_frame(), "front-exasperated")
    assert _rgba_bytes(removed) == _rgba_bytes(_frame())
    assert appearance.makeup_intensities == dict.fromkeys(SLOTS_V2, 0.0)
