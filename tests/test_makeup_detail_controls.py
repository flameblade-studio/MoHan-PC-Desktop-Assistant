"""Independent cosmetic controls retain legacy state and affect only their slot."""
from __future__ import annotations

lazy import json
lazy import os
lazy import sys
lazy from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
lazy import pytest
lazy from domain.outfit_pack_makeup import (
    read_makeup_intensity, read_makeup_slot_intensities,
    write_makeup_intensity, write_makeup_slot_intensity,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from test_active_outfit_overlay_makeup import (
    _app, _authority, _configure, _frame, _layer, _lips_block,
    BASE_GRAY, LIP_RED, LIPS_PIXEL, EYES_PIXEL, MIDPOINT_TOLERANCE,
)
lazy from test_global_settings_actions import close_dashboard
lazy from test_outfit_pack_makeup import official_builtin_pack
lazy from test_wardrobe_ui import build_language_dashboard


def test_legacy_global_and_detail_values_preserve_each_other(tmp_path: Path) -> None:
    global_intensity = 0.6
    write_makeup_intensity(tmp_path, .5)
    assert json.loads((tmp_path / "makeup.json").read_text(encoding="utf-8")) == {"intensity": .5}
    assert set(read_makeup_slot_intensities(tmp_path).values()) == {1.0}
    write_makeup_slot_intensity(tmp_path, "lips", .25)
    write_makeup_slot_intensity(tmp_path, "eyes", .75)
    write_makeup_intensity(tmp_path, global_intensity)
    assert read_makeup_intensity(tmp_path) == global_intensity
    assert read_makeup_slot_intensities(tmp_path) == {"eyes": .75, "cheeks": 1., "lips": .25}
    write_makeup_slot_intensity(tmp_path, "lips", 1.)
    write_makeup_slot_intensity(tmp_path, "eyes", 1.)
    assert json.loads((tmp_path / "makeup.json").read_text(encoding="utf-8")) == {"intensity": global_intensity}


def test_invalid_detail_state_retains_last_value_and_notifies(tmp_path: Path) -> None:
    last_valid_intensity = 0.3
    write_makeup_slot_intensity(tmp_path, "lips", last_valid_intensity)
    messages = []
    for value in (True, None, "NaN", "broken"):
        (tmp_path / "makeup.json").write_text(json.dumps({"intensity": 1, "slot_intensities": {"lips": value}}), encoding="utf-8")
        assert read_makeup_slot_intensities(tmp_path, messages.append)["lips"] == last_valid_intensity
    assert len(messages) == 1
    before = (tmp_path / "makeup.json").read_bytes()
    with pytest.raises(ValueError, match="Unknown makeup slot"):
        write_makeup_slot_intensity(tmp_path, "body", .5)
    assert (tmp_path / "makeup.json").read_bytes() == before


def test_overlay_applies_per_slot_multiplier_and_invalidates_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _app()
    _authority(tmp_path)
    eyes = _layer(((EYES_PIXEL[0], EYES_PIXEL[1], 3, 3, LIP_RED),))
    store = _configure(monkeypatch, tmp_path, {"lips": _lips_block(), "eyes": eyes})
    overlay = ActiveOutfitOverlay(store, tmp_path)
    assert overlay.apply(_frame(), "front-crossed").toImage().pixelColor(*LIPS_PIXEL) == LIP_RED
    write_makeup_slot_intensity(store, "lips", 0.)
    image = overlay.apply(_frame(), "front-crossed").toImage()
    assert image.pixelColor(*LIPS_PIXEL) == BASE_GRAY
    assert image.pixelColor(*EYES_PIXEL) == BASE_GRAY  # The fixture's iris remains protected.
    eye_pigment = (EYES_PIXEL[0] + 1, EYES_PIXEL[1])
    assert image.pixelColor(*eye_pigment) == LIP_RED
    write_makeup_intensity(store, .5)
    write_makeup_slot_intensity(store, "eyes", .5)
    pixel = overlay.apply(_frame(), "front-crossed").toImage().pixelColor(*eye_pigment)
    expected = [BASE_GRAY.getRgb()[i] * .75 + LIP_RED.getRgb()[i] * .25 for i in range(3)]
    assert all(abs(pixel.getRgb()[i] - expected[i]) <= MIDPOINT_TOLERANCE for i in range(3))


def test_detail_sliders_persist_after_dashboard_reopen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    global_percent = 60
    _app()
    official_builtin_pack(tmp_path, monkeypatch)
    profile = tmp_path / "profile"
    profile.mkdir()
    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        dashboard.wardrobe_makeup_intensity.setValue(global_percent)
        dashboard.wardrobe_makeup_details["lips"].setValue(25)
        dashboard.wardrobe_makeup_details["eyes"].setValue(75)
    finally:
        close_dashboard(dashboard, db)
    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        assert dashboard.wardrobe_makeup_intensity.value() == global_percent
        assert {k: v.value() for k, v in dashboard.wardrobe_makeup_details.items()} == {"eyes": 75, "cheeks": 100, "lips": 25}
        assert dashboard.wardrobe_makeup_details["lips"].accessibleName() == "唇妝濃淡"
    finally:
        close_dashboard(dashboard, db)


def main() -> int:
    result = pytest.main([str(Path(__file__)), "-q", *sys.argv[1:]])
    if result == 0:
        print("MAKEUP_DETAIL_CONTROLS_OK")
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
