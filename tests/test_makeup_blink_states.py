"""Sealed eye-state makeup preserves gates, selection and independent intensity."""
from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
lazy import pytest
lazy from PySide6.QtGui import QColor
lazy from domain.outfit_pack import OutfitPackError, apply_appearance_selection, install_outfit_pack, inspect_outfit_pack, list_installed_selections
lazy from domain.outfit_pack_makeup import load_makeup_safe_regions, verify_makeup_layers, write_makeup_slot_intensity
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from test_outfit_pack import _pack
lazy from test_outfit_pack_makeup import makeup_manifest, layer_png, canvas_for, _entry
lazy from test_active_outfit_overlay_makeup import _app, _authority, _frame, BASE_GRAY, EYES_PIXEL

VIEW = "front-crossed"
POINT = (610, 250)
COLORS = {"half": QColor("red"), "closed": QColor("blue")}


def _state_pack():
    manifest, assets = makeup_manifest()
    variant = manifest["makeup"][0]["variants"][0]
    variant["eye_states"] = {}
    for state, color in COLORS.items():
        poses = {}
        for view in variant["poses"]:
            size = canvas_for(view)
            blocks = ((600, 250, 11, 1),) if view == VIEW else ()
            data = layer_png(size, blocks, color)
            path = f"assets/{state}-{view}-eyes.png"
            assets[path] = data
            poses[view] = [_entry(path, data, "eyes", size)]
        variant["eye_states"][state] = poses
    return manifest, assets


def test_installed_states_and_slider_cache(tmp_path, monkeypatch):
    _app()
    _authority(tmp_path)
    monkeypatch.setattr("domain.outfit_pack.OFFICIAL_PACK_ROOT", tmp_path / "official")
    manifest, assets = _state_pack()
    archive = _pack(tmp_path / "states.mohan-outfit", manifest, assets)
    regions = load_makeup_safe_regions(tmp_path / "assets/makeup-safe-regions.json")
    verify_makeup_layers(archive, regions)
    store = tmp_path / "store"
    # Import uses the same authored calibration as the runtime root.
    monkeypatch.setattr("domain.outfit_pack_makeup.SAFE_REGION_PATH", tmp_path / "assets/makeup-safe-regions.json")
    install_outfit_pack(archive, store)
    selection = next(item for item in list_installed_selections(store, "makeup") if item.pack_id == "festival-makeup")
    apply_appearance_selection(store, selection)
    overlay = ActiveOutfitOverlay(store, tmp_path)
    assert overlay._active_layers(VIEW, (1254, 1254), suppress_makeup_slots=frozenset({"eyes"}), eye_state="half")
    for state in ("half", "closed", "half"):
        image = overlay.apply(_frame(), VIEW, suppress_makeup_slots={"eyes"}, eye_state=state).toImage()
        assert image.pixelColor(*POINT) == COLORS[state]
        assert image.pixelColor(*EYES_PIXEL) == BASE_GRAY
    write_makeup_slot_intensity(store, "eyes", 0)
    assert overlay.apply(_frame(), VIEW, suppress_makeup_slots={"eyes"}, eye_state="closed").toImage() == _frame().toImage()
    write_makeup_slot_intensity(store, "eyes", 1)
    assert overlay.apply(_frame(), VIEW, suppress_makeup_slots={"eyes"}, eye_state="closed").toImage().pixelColor(*POINT) == COLORS["closed"]
    assert overlay.apply(_frame(), VIEW).toImage() == _frame().toImage()


@pytest.mark.parametrize("defect", ("missing_state", "missing_view", "wrong_slot", "bad_hash"))
def test_malformed_state_rejected(tmp_path, defect):
    manifest, assets = _state_pack()
    states = manifest["makeup"][0]["variants"][0]["eye_states"]
    if defect == "missing_state":
        del states["half"]
    elif defect == "missing_view":
        del states["half"][VIEW]
    elif defect == "wrong_slot":
        states["half"][VIEW][0]["slot"] = "lips"
    else:
        states["half"][VIEW][0]["sha256"] = "0" * 64
    with pytest.raises(OutfitPackError):
        inspect_outfit_pack(_pack(tmp_path / "invalid.mohan-outfit", manifest, assets))


def main():
    result = pytest.main([__file__, "-q"])
    if result:
        raise SystemExit(result)
    print("MAKEUP_BLINK_STATES_OK")


if __name__ == "__main__":
    main()
