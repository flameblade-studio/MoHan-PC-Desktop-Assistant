"""Exercise cache writers and privacy boundaries through runtime adapters."""
from __future__ import annotations

lazy import logging
lazy from dataclasses import FrozenInstanceError, fields, make_dataclass
lazy from pathlib import Path

lazy import pytest
lazy from PySide6.QtGui import QColor, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication
lazy from domain.outfit_pack import OutfitPackError
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.appearance_layer_stack import AppearanceLayerStack
lazy from infrastructure.outfit_layer_cache_key import OutfitLayerCacheKey
lazy from infrastructure.outfit_overlay_diagnostics import record_outfit_fallback


@pytest.mark.parametrize("route", ("combined", "suppressed", "makeup-view", "split", "split-state"))
def test_runtime_cache_writers_are_visible_and_invalidated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, route: str,
) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    overlay = ActiveOutfitOverlay(tmp_path, tmp_path, visible_hand_region=None)
    frame = QPixmap(8, 8)
    frame.fill(QColor("white"))
    layer = (frame, 0, 0, QRegion(frame.rect()), 1.0)
    stack = AppearanceLayerStack((), (layer,))
    monkeypatch.setattr(overlay, "_refresh_state", lambda: None)
    monkeypatch.setattr(overlay, "_reviewed_frame", lambda *args, **kwargs: None)
    monkeypatch.setattr(overlay, "_active_layers", lambda *args, **kwargs: stack)
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: False)
    monkeypatch.setattr(overlay, "_selected_silhouette_region", lambda *args: None)
    monkeypatch.setattr(overlay, "_base_clear_regions", lambda *args: (None, None, None))
    options = {}
    if route in {"suppressed", "split-state"}:
        options.update(suppress_makeup_slots={"eyes"}, eye_state="closed")
        overlay.set_active_mouth_state("open")
    if route in {"makeup-view", "split-state"}:
        options["makeup_view_id"] = "cheek-rest-legacy"
    if route.startswith("split"):
        overlay.apply_appearance(frame, "view")
        overlay.apply_makeup(frame, "view", **options)
        expected = 2
    else:
        overlay.apply(frame, "view", **options)
        expected = 1
    assert overlay.layer_count("view", **options) == expected
    overlay._invalidate_view("view")
    assert overlay.layer_count("view", **options) == 0
    assert not overlay._layers_by_view
    assert not overlay._layers_by_view_without_makeup_slots
    assert not overlay._phase_layers_by_view


def test_nondefault_appearance_phase_count_uses_the_written_identity(tmp_path: Path) -> None:
    overlay = ActiveOutfitOverlay(tmp_path, tmp_path, visible_hand_region=None)
    key = OutfitLayerCacheKey.for_phase(
        "view", "appearance", frozenset({"eyes"}), "closed", "open", "legacy",
    )
    overlay.set_active_mouth_state("open")
    overlay._phase_layers_by_view[key] = (object(),)
    assert overlay.layer_count(
        "view", suppress_makeup_slots={"eyes"}, eye_state="closed", makeup_view_id="legacy",
    ) == 1
    with pytest.raises(FrozenInstanceError):
        key.view_id = "other"


def test_key_factories_preserve_a_new_default_field() -> None:
    expected_revision = 2
    schema = [(field.name, field.type, field.default) for field in fields(OutfitLayerCacheKey)]
    schema.insert(1, ("material_revision", int, expected_revision))
    ExtendedKey = make_dataclass("ExtendedKey", schema, frozen=True, slots=True, namespace={
        "combined": classmethod(OutfitLayerCacheKey.combined.__func__),
        "for_phase": classmethod(OutfitLayerCacheKey.for_phase.__func__),
    })
    for key, phase, eye_state in (
        (ExtendedKey.combined("view"), "combined", "rest"),
        (ExtendedKey.for_phase("view", "makeup", eye_state="closed"), "makeup", "closed"),
    ):
        assert key.material_revision == expected_revision
        assert type(key) is ExtendedKey
        assert key.phase == phase
        assert key.eye_state == eye_state
        assert {key: "cached"}[ExtendedKey(**{
            field.name: getattr(key, field.name) for field in fields(OutfitLayerCacheKey)
        })] == "cached"


@pytest.mark.parametrize("path", (
    "C:Users/alice/secret.png", "C:/Users/alice/secret.png",
    "/home/alice/secret.png", "\\\\server\\alice\\secret.png",
))
def test_diagnostics_omit_local_paths_and_unsafe_context(
    path: str, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger="mohan.outfit_overlay")
    error = OutfitPackError("alice private details", reason=path, pack_id=path, asset_path=path)
    seen = set()
    for _ in range(2):
        record_outfit_fallback(error, view_id=path, seen=seen)
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.outfit_reason == "OutfitPackError"
    assert record.outfit_view == "invalid_view_id"
    assert record.outfit_pack_id is None
    assert record.outfit_asset_path is None
    assert "alice" not in str(record.__dict__)


def test_diagnostics_omit_unknown_view_names(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="mohan.outfit_overlay")
    record_outfit_fallback(OutfitPackError("Private details"), view_id="alice", seen=set())
    assert len(caplog.records) == 1
    assert caplog.records[0].outfit_view == "invalid_view_id"
    assert "alice" not in str(caplog.records[0].__dict__)
