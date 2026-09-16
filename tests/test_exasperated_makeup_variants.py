"""Regression gates for the v3 exasperated light and classic cosmetics."""

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

lazy import infrastructure.exasperated_candidate_appearance as appearance_module
lazy from infrastructure.exasperated_candidate_appearance import (
    FOUNDATION_SCHEMA,
    LOOK_VARIANTS,
    SCHEMA,
    SLOTS,
    SLOTS_V2,
    STATES,
    VARIANT_SCHEMA,
    ExasperatedCandidateAppearance,
)
lazy from infrastructure.exasperated_candidate_assets import APPROVED_SOURCE_SHA256, DIMENSION

AVAILABLE_STATUS = "available"
BASE_COLOR = QColor("#293241")
RECTS = {
    "foundation": QRect(100, 100, 15, 15),
    "eyes": QRect(200, 100, 15, 15),
    "cheeks": QRect(300, 100, 15, 15),
    "lips": QRect(400, 100, 15, 15),
}
POINTS = {slot: (rect.x() + 3, rect.y() + 3) for slot, rect in RECTS.items()}
VARIANT_COLORS = {
    "classic": {
        "foundation": QColor("#e9c46a"),
        "eyes": QColor("#264653"),
        "cheeks": QColor("#e76f51"),
        "lips": QColor("#e63946"),
    },
    "light": {
        "foundation": QColor("#90be6d"),
        "eyes": QColor("#577590"),
        "cheeks": QColor("#f9c74f"),
        "lips": QColor("#f9844a"),
    },
    "glamorous": {
        "foundation": QColor("#e0a458"),
        "eyes": QColor("#6a040f"),
        "cheeks": QColor("#d00000"),
        "lips": QColor("#9d0208"),
    },
}
STATE_COLORS = {
    "rest": QColor("#8338ec"),
    "mid": QColor("#fb5607"),
    "open": QColor("#ffbe0b"),
    "round": QColor("#06d6a0"),
}
MOUTH_EXPRESSIONS = {
    None: "rest",
    "exasperated_front_speech_mid": "mid",
    "exasperated_front_speech_open": "open",
    "exasperated_front_speech_round": "round",
}


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _write_png(root: Path, relative: str, rectangle: QRect, color: QColor) -> dict[str, str]:
    image = QImage(DIMENSION, DIMENSION, QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        if not rectangle.isNull():
            painter.fillRect(rectangle, color)
    finally:
        painter.end()
    path = root / Path(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path), "PNG")
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _manifest(root: Path, *, variants: tuple[str, ...] = LOOK_VARIANTS) -> dict[str, object]:
    layers: dict[str, dict[str, str]] = {
        "garment": _write_png(root, "garment.rgba.png", QRect(), QColor("#ffffff")),
        "replace_mask": _write_png(root, "replace_mask.rgba.png", QRect(), QColor("#ffffff")),
    }
    for variant in variants:
        for state in STATES:
            for slot in SLOTS_V2:
                key = f"{variant}/{state}/{slot}"
                relative = f"{key}.rgba.png"
                color = VARIANT_COLORS[variant][slot]
                if slot == "lips":
                    color = STATE_COLORS[state]
                layers[key] = _write_png(root, relative, RECTS[slot], color)
    manifest: dict[str, object] = {
        "schema": VARIANT_SCHEMA,
        "source_sha256": APPROVED_SOURCE_SHA256,
        "cosmetic_status": AVAILABLE_STATUS,
        "variants": list(variants),
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


def _appearance(root: Path) -> ExasperatedCandidateAppearance:
    _app()
    _manifest(root)
    appearance = ExasperatedCandidateAppearance.load(root)
    appearance.store = root
    return appearance


def _selection(*, makeup_pack: str, variant: str) -> SimpleNamespace:
    return SimpleNamespace(
        effective_pack_id=makeup_pack,
        effective_variant_id=variant,
    )


def _stub_selection(
    monkeypatch: pytest.MonkeyPatch,
    selection: SimpleNamespace,
    *,
    intensity: float = 1.0,
) -> None:
    monkeypatch.setattr(
        appearance_module,
        "resolve_active_selection",
        lambda _store, category: (
            selection
            if category == "makeup"
            else SimpleNamespace(effective_pack_id="builtin")
        ),
    )
    monkeypatch.setattr(appearance_module, "read_makeup_intensity", lambda _store: intensity)
    monkeypatch.setattr(
        appearance_module,
        "read_makeup_slot_intensities",
        lambda _store, *, slots: dict.fromkeys(slots, 1.0),
    )


def _legacy_manifest(root: Path, schema: str) -> dict[str, object]:
    slots = SLOTS_V2 if schema == FOUNDATION_SCHEMA else SLOTS
    layers: dict[str, dict[str, str]] = {
        "garment": _write_png(root, "garment.rgba.png", QRect(), QColor("#ffffff")),
        "replace_mask": _write_png(root, "replace_mask.rgba.png", QRect(), QColor("#ffffff")),
    }
    for state in STATES:
        for slot in slots:
            key = f"{state}/{slot}"
            layers[key] = _write_png(root, f"{key}.rgba.png", RECTS[slot], VARIANT_COLORS["classic"][slot])
    manifest: dict[str, object] = {
        "schema": schema,
        "source_sha256": APPROVED_SOURCE_SHA256,
        "cosmetic_status": AVAILABLE_STATUS,
        "layers": layers,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return manifest


def test_v3_requires_both_declared_variants_and_every_slot(tmp_path: Path) -> None:
    _app()
    manifest = _manifest(tmp_path)

    manifest["variants"] = [LOOK_VARIANTS[0]]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="classic and light variants"):
        ExasperatedCandidateAppearance.load(tmp_path)

    manifest = _manifest(tmp_path)
    manifest["variants"] = [*LOOK_VARIANTS, "unknown"]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="classic and light variants"):
        ExasperatedCandidateAppearance.load(tmp_path)

    manifest = _manifest(tmp_path)
    layers = manifest["layers"]
    assert isinstance(layers, dict)
    del layers["light/rest/eyes"]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="clothing and all mouth-specific cosmetics"):
        ExasperatedCandidateAppearance.load(tmp_path)


@pytest.mark.parametrize("schema", (SCHEMA, FOUNDATION_SCHEMA))
def test_legacy_schemas_reject_glamorous_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    schema: str,
) -> None:
    _app()
    _legacy_manifest(tmp_path, schema)
    appearance = ExasperatedCandidateAppearance.load(tmp_path)
    appearance.store = tmp_path
    _stub_selection(
        monkeypatch,
        _selection(
            makeup_pack=appearance_module.BUILTIN_MAKEUP_PACK_ID,
            variant="glamorous",
        ),
    )

    with pytest.raises(ValueError, match="variant is unavailable"):
        appearance.apply(_frame(), "front-exasperated")


def test_v3_two_variant_manifest_remains_compatible(tmp_path: Path) -> None:
    _app()
    _manifest(tmp_path, variants=("classic", "light"))

    appearance = ExasperatedCandidateAppearance.load(tmp_path)

    assert appearance.look_variants == ("classic", "light")
    assert appearance.cosmetics_available


@pytest.mark.parametrize("variant", LOOK_VARIANTS)
@pytest.mark.parametrize("expression,state", MOUTH_EXPRESSIONS.items())
def test_v3_uses_selected_variant_layers_for_all_mouth_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    variant: str,
    expression: str | None,
    state: str,
) -> None:
    appearance = _appearance(tmp_path)
    appearance.garment_enabled = False
    selection = _selection(
        makeup_pack=appearance_module.BUILTIN_MAKEUP_PACK_ID,
        variant=variant,
    )
    _stub_selection(monkeypatch, selection)

    result = appearance.apply(
        _frame(),
        "front-exasperated",
        mouth_expression=expression,
    ).toImage()

    assert appearance.cosmetic_slots == SLOTS_V2
    assert appearance.makeup_intensities == dict.fromkeys(SLOTS_V2, 1.0)
    for slot in SLOTS:
        expected = STATE_COLORS[state] if slot == "lips" else VARIANT_COLORS[variant][slot]
        assert result.pixelColor(*POINTS[slot]) == expected
    assert result.pixelColor(*POINTS["foundation"]) == VARIANT_COLORS[variant]["foundation"]


def test_v3_switches_between_light_and_classic_without_legacy_point_five_five(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    appearance = _appearance(tmp_path)
    appearance.garment_enabled = False
    selection = _selection(
        makeup_pack=appearance_module.BUILTIN_MAKEUP_PACK_ID,
        variant="light",
    )
    _stub_selection(monkeypatch, selection)
    light = appearance.apply(_frame(), "front-exasperated").toImage()

    selection.effective_variant_id = "classic"
    classic = appearance.apply(_frame(), "front-exasperated").toImage()

    assert light.pixelColor(*POINTS["eyes"]) == VARIANT_COLORS["light"]["eyes"]
    assert classic.pixelColor(*POINTS["eyes"]) == VARIANT_COLORS["classic"]["eyes"]
    assert light.pixelColor(*POINTS["foundation"]) == VARIANT_COLORS["light"]["foundation"]
    assert classic.pixelColor(*POINTS["foundation"]) == VARIANT_COLORS["classic"]["foundation"]
    assert appearance.makeup_intensities == dict.fromkeys(SLOTS_V2, 1.0)
    assert _rgba_bytes(QPixmap.fromImage(light)) != _rgba_bytes(QPixmap.fromImage(classic))


def test_v3_bare_selection_paints_no_cosmetics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    appearance = _appearance(tmp_path)
    appearance.garment_enabled = False
    selection = _selection(makeup_pack="builtin", variant="none")
    _stub_selection(monkeypatch, selection)
    frame = _frame()

    result = appearance.apply(frame, "front-exasperated", mouth_expression="exasperated_front_speech_open")

    assert _rgba_bytes(result) == _rgba_bytes(frame)
    assert appearance.makeup_intensities == dict.fromkeys(SLOTS_V2, 0.0)
    assert appearance._selected_variant is None


def test_v3_unknown_selected_variant_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    appearance = _appearance(tmp_path)
    selection = _selection(
        makeup_pack=appearance_module.BUILTIN_MAKEUP_PACK_ID,
        variant="unknown",
    )
    _stub_selection(monkeypatch, selection)

    with pytest.raises(ValueError, match="variant is unavailable"):
        appearance.apply(_frame(), "front-exasperated")


def test_v1_and_v2_schema_constants_remain_distinct() -> None:
    assert SCHEMA != FOUNDATION_SCHEMA
    assert FOUNDATION_SCHEMA != VARIANT_SCHEMA
    assert set(SLOTS) < set(SLOTS_V2)
