"""Behavioral gates for the opt-in exasperated garment and makeup overlay."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from infrastructure.exasperated_candidate_appearance import (
    SCHEMA,
    SLOTS,
    STATES,
    ExasperatedCandidateAppearance,
)
from infrastructure.exasperated_candidate_assets import (
    APPROVED_SOURCE_SHA256,
    DIMENSION,
    SHA256_HEX_LENGTH,
)

ZERO_INTENSITY = 0.0
FULL_INTENSITY = 1.0
VALID_INTENSITIES = {"eyes": 0.25, "cheeks": 0.5, "lips": 0.75}
NAN_INTENSITY = float("nan")
ABOVE_MAX_INTENSITY = 1.01
BELOW_MIN_INTENSITY = -0.01
OPAQUE_ALPHA = 255

BODY_RECT = QRect(480, 480, 80, 80)
SLEEVE_RECT = QRect(900, 480, 40, 40)
RETAINED_BODY_RECT = QRect(700, 480, 40, 40)
BODY_POINT = (500, 500)
SLEEVE_POINT = (910, 490)
RETAINED_BODY_POINT = (710, 490)
EYES_RECT = QRect(260, 260, 20, 20)
CHEEKS_RECT = QRect(360, 360, 20, 20)
LIPS_RECT = QRect(460, 460, 20, 20)
SLOT_RECTS = {"eyes": EYES_RECT, "cheeks": CHEEKS_RECT, "lips": LIPS_RECT}
SLOT_POINTS = {"eyes": (270, 270), "cheeks": (370, 370), "lips": (470, 470)}

BASE_COLOR = QColor("#293241")
BODY_COLOR = QColor("#6c584c")
GARMENT_COLOR = QColor("#227c9d")
SLOT_COLORS = {
    "eyes": QColor("#3a86ff"),
    "cheeks": QColor("#ff006e"),
}
MOUTH_COLORS = {
    "rest": QColor("#8338ec"),
    "mid": QColor("#fb5607"),
    "open": QColor("#ffbe0b"),
    "round": QColor("#06d6a0"),
}

NOT_APPROVED_STATUS = "not_approved"
AVAILABLE_STATUS = "available"

MOUTH_CASES = (
    ("exasperated_front_speech_mid", "mid"),
    ("exasperated_front_speech_i", "mid"),
    ("exasperated_front_speech_open", "open"),
    ("exasperated_front_speech_round", "round"),
    ("exasperated_front_speech_u", "round"),
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _write_png(root: Path, relative: str, rectangles: tuple[tuple[QRect, QColor], ...]) -> dict[str, str]:
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        for rectangle, color in rectangles:
            painter.fillRect(rectangle, color)
    finally:
        painter.end()
    path = root / Path(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path), "PNG")
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _candidate_manifest(root: Path, *, cosmetic_status: str = AVAILABLE_STATUS) -> dict:
    layers = {
        "garment": _write_png(root, "garment.rgba.png", ((BODY_RECT, GARMENT_COLOR), (SLEEVE_RECT, GARMENT_COLOR))),
        "replace_mask": _write_png(root, "replace_mask.rgba.png", ((BODY_RECT, QColor("white")),)),
    }
    if cosmetic_status != NOT_APPROVED_STATUS:
        for state in STATES:
            for slot in SLOTS:
                relative = f"{state}/{slot}.rgba.png"
                color = MOUTH_COLORS[state] if slot == "lips" else SLOT_COLORS[slot]
                layers[f"{state}/{slot}"] = _write_png(
                    root,
                    relative,
                    ((SLOT_RECTS[slot], color),),
                )
    manifest = {
        "schema": SCHEMA,
        "source_sha256": APPROVED_SOURCE_SHA256,
        "cosmetic_status": cosmetic_status,
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


def _appearance(root: Path, *, cosmetic_status: str = AVAILABLE_STATUS) -> ExasperatedCandidateAppearance:
    _app()
    _candidate_manifest(root, cosmetic_status=cosmetic_status)
    return ExasperatedCandidateAppearance.load(root)


def test_not_approved_manifest_loads_without_fake_cosmetic_layers(tmp_path: Path) -> None:
    appearance = _appearance(tmp_path, cosmetic_status=NOT_APPROVED_STATUS)

    assert set(appearance.layers) == {"garment", "replace_mask"}
    assert appearance.cosmetics_available is False
    appearance.garment_enabled = False
    appearance.set_makeup_intensities({slot: FULL_INTENSITY for slot in SLOTS})
    frame = _frame()

    assert _rgba_bytes(appearance.apply(frame, "front-exasperated")) == _rgba_bytes(frame)


def test_garment_off_and_makeup_zero_return_the_original_frame(tmp_path: Path) -> None:
    appearance = _appearance(tmp_path)
    appearance.garment_enabled = False
    appearance.set_makeup_intensities({slot: ZERO_INTENSITY for slot in SLOTS})
    frame = _frame()

    result = appearance.apply(frame, "front-exasperated", mouth_expression="exasperated_front_speech_open")

    assert _rgba_bytes(result) == _rgba_bytes(frame)


def test_destination_out_replaces_old_body_and_keeps_new_sleeve_outside_body_alpha(tmp_path: Path) -> None:
    appearance = _appearance(tmp_path)
    appearance.set_makeup_intensities({slot: ZERO_INTENSITY for slot in SLOTS})
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        painter.fillRect(BODY_RECT, BODY_COLOR)
        painter.fillRect(RETAINED_BODY_RECT, BODY_COLOR)
    finally:
        painter.end()
    frame = QPixmap.fromImage(image)

    result = appearance.apply(frame, "front-exasperated").toImage()

    assert result.pixelColor(*BODY_POINT) == GARMENT_COLOR
    assert result.pixelColor(*BODY_POINT).alpha() == OPAQUE_ALPHA
    assert result.pixelColor(*SLEEVE_POINT) == GARMENT_COLOR
    assert result.pixelColor(*SLEEVE_POINT).alpha() == OPAQUE_ALPHA
    assert result.pixelColor(*RETAINED_BODY_POINT) == BODY_COLOR


@pytest.mark.parametrize(("expression", "state"), MOUTH_CASES)
def test_mouth_state_selects_the_bound_lips_and_maps_i_u(
    tmp_path: Path, expression: str, state: str,
) -> None:
    appearance = _appearance(tmp_path)
    appearance.garment_enabled = False
    appearance.set_makeup_intensities({"eyes": ZERO_INTENSITY, "cheeks": ZERO_INTENSITY, "lips": FULL_INTENSITY})

    result = appearance.apply(_frame(), "front-exasperated", mouth_expression=expression).toImage()

    assert result.pixelColor(*SLOT_POINTS["lips"]) == MOUTH_COLORS[state]
    assert result.pixelColor(*SLOT_POINTS["eyes"]) == BASE_COLOR
    assert result.pixelColor(*SLOT_POINTS["cheeks"]) == BASE_COLOR


@pytest.mark.parametrize("active_slot", SLOTS)
def test_makeup_slots_apply_independent_intensities(tmp_path: Path, active_slot: str) -> None:
    appearance = _appearance(tmp_path)
    appearance.garment_enabled = False
    values = {slot: ZERO_INTENSITY for slot in SLOTS}
    values[active_slot] = FULL_INTENSITY
    appearance.set_makeup_intensities(values)

    result = appearance.apply(_frame(), "front-exasperated").toImage()

    for slot in SLOTS:
        point = SLOT_POINTS[slot]
        expected = (
            MOUTH_COLORS["rest"] if slot == "lips" else SLOT_COLORS[slot]
        ) if slot == active_slot else BASE_COLOR
        assert result.pixelColor(*point) == expected


@pytest.mark.parametrize(
    "invalid_values",
    (
        {"eyes": NAN_INTENSITY, "cheeks": VALID_INTENSITIES["cheeks"], "lips": VALID_INTENSITIES["lips"]},
        {"eyes": ABOVE_MAX_INTENSITY, "cheeks": VALID_INTENSITIES["cheeks"], "lips": VALID_INTENSITIES["lips"]},
        {"eyes": VALID_INTENSITIES["eyes"], "cheeks": VALID_INTENSITIES["cheeks"], "lips": BELOW_MIN_INTENSITY},
    ),
)
def test_invalid_makeup_intensities_are_rejected_atomically(
    tmp_path: Path, invalid_values: dict[str, float],
) -> None:
    appearance = _appearance(tmp_path)
    appearance.set_makeup_intensities(VALID_INTENSITIES)
    before = dict(appearance.makeup_intensities)

    with pytest.raises(ValueError, match="finite values from zero to one"):
        appearance.set_makeup_intensities(invalid_values)

    assert appearance.makeup_intensities == before


@pytest.mark.parametrize("mutation", ("source_sha256", "garment_digest"))
def test_malformed_source_and_asset_digest_fail_closed(tmp_path: Path, mutation: str) -> None:
    _app()
    manifest = _candidate_manifest(tmp_path)
    if mutation == "source_sha256":
        manifest["source_sha256"] = "f" * SHA256_HEX_LENGTH
        expected = "approved exasperated source"
    else:
        manifest["layers"]["garment"]["sha256"] = "0" * SHA256_HEX_LENGTH
        expected = "digest mismatch"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match=expected):
        ExasperatedCandidateAppearance.load(tmp_path)


def test_loader_rejects_non_dict_manifest_and_layers(tmp_path: Path) -> None:
    _app()
    _candidate_manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"

    manifest_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="approved exasperated source"):
        ExasperatedCandidateAppearance.load(tmp_path)

    manifest = _candidate_manifest(tmp_path)
    manifest["layers"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="clothing and all mouth-specific cosmetics"):
        ExasperatedCandidateAppearance.load(tmp_path)


def test_layer_pixmaps_are_decoded_once_and_reused(tmp_path: Path) -> None:
    appearance = _appearance(tmp_path)

    first = appearance._pixmap("garment")
    second = appearance._pixmap("garment")

    assert first is second
    assert set(appearance._pixmaps) == {"garment"}


def test_other_silhouettes_are_left_byte_identical(tmp_path: Path) -> None:
    appearance = _appearance(tmp_path)
    appearance.set_makeup_intensities(VALID_INTENSITIES)
    frame = _frame()

    result = appearance.apply(frame, "front-crossed", mouth_expression="unrecognized")

    assert _rgba_bytes(result) == _rgba_bytes(frame)


def test_light_selection_preserves_slot_ratios_and_can_be_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import infrastructure.exasperated_candidate_appearance as module

    appearance = _appearance(tmp_path)
    appearance.store = tmp_path
    selection = SimpleNamespace(
        effective_pack_id=module.BUILTIN_MAKEUP_PACK_ID, effective_variant_id="light",
    )
    monkeypatch.setattr(module, "resolve_active_selection", lambda _store, category: (
        selection if category == "makeup" else SimpleNamespace(effective_pack_id="builtin")
    ))
    monkeypatch.setattr(module, "read_makeup_intensity", lambda _store: FULL_INTENSITY)
    monkeypatch.setattr(module, "read_makeup_slot_intensities", lambda _store, **_kwargs: VALID_INTENSITIES)
    frame = _frame()
    appearance.apply(frame, "front-exasperated")
    expected_light_opacity = 0.55
    assert appearance.makeup_intensities == pytest.approx({
        slot: value * expected_light_opacity for slot, value in VALID_INTENSITIES.items()
    })
    selection.effective_pack_id = "builtin"
    removed = appearance.apply(frame, "front-exasperated")
    assert _rgba_bytes(removed) == _rgba_bytes(frame)
    assert appearance.makeup_intensities == dict.fromkeys(SLOTS, ZERO_INTENSITY)
