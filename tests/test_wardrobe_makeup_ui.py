"""Wardrobe makeup category: shared import button, menu, slider persistence, removal fallback."""

from __future__ import annotations

lazy import json
lazy import os
lazy import shutil
lazy import sys
lazy from pathlib import Path
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy import pytest
lazy from PySide6.QtWidgets import QApplication, QFileDialog

lazy from domain.outfit_pack import (
    BUILTIN_MAKEUP_ITEM_ID,
    BUILTIN_MAKEUP_PACK_ID,
    FOUNDATION_SLOT,
    MAKEUP_SLOTS_V2,
)
lazy from test_global_settings_actions import close_dashboard
lazy from test_outfit_pack_makeup import makeup_pack, official_builtin_pack
lazy from test_wardrobe_ui import build_language_dashboard
lazy from presentation.dashboard_wardrobe_makeup import FRONT_SILHOUETTE
lazy from presentation.ui_localization import ui_text

FESTIVAL_OPTION = "festival-makeup/festival/classic"
HALF_PERCENT = 50
HALF = 0.5
FOUNDATION_INITIAL_INTENSITY = 0.4
FOUNDATION_INITIAL_PERCENT = round(FOUNDATION_INITIAL_INTENSITY * 100)


def _menu_ids(dashboard) -> list[str]:
    selector = dashboard.wardrobe_makeup_selector
    return [str(selector.itemData(index)) for index in range(selector.count())]


def test_legacy_makeup_keeps_the_foundation_control_hidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = QApplication.instance() or QApplication([])
    official_builtin_pack(tmp_path, monkeypatch)
    profile = tmp_path / "profile"
    profile.mkdir()
    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        with patch.object(
            dashboard.wardrobe_service,
            "active_makeup_slots",
            return_value=frozenset({"eyes", "cheeks", "lips"}),
            create=True,
        ) as capability:
            dashboard._refresh_foundation_control()
            application.processEvents()
            capability.assert_called_with(
                FRONT_SILHOUETTE,
                notify=dashboard._wardrobe_makeup_read_warning,
            )
        assert dashboard.wardrobe_makeup_foundation_row.isHidden()
        assert dashboard.wardrobe_makeup_foundation_label.isHidden()
        assert set(dashboard.wardrobe_makeup_details) == {"eyes", "cheeks", "lips"}
    finally:
        close_dashboard(dashboard, db)


def test_v2_foundation_control_is_independent_and_tracks_canonical_view_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = QApplication.instance() or QApplication([])
    official_builtin_pack(tmp_path, monkeypatch)
    profile = tmp_path / "profile"
    profile.mkdir()
    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        calls: list[tuple[str, float]] = []
        with (
            patch.object(
                dashboard.wardrobe_service,
                "active_makeup_slots",
                side_effect=lambda view, notify=None: (
                    frozenset({"eyes", "cheeks", "lips", FOUNDATION_SLOT})
                    if view == FRONT_SILHOUETTE
                    else frozenset({"eyes", "cheeks", "lips"})
                ),
                create=True,
            ) as capability,
            patch.object(
                dashboard.wardrobe_service,
                "set_makeup_slot_intensity",
                side_effect=lambda slot, value: calls.append((slot, value)) or value,
            ),
            patch.object(dashboard, "_refresh_wardrobe_preview"),
        ):
            dashboard._refresh_foundation_control(
                {FOUNDATION_SLOT: FOUNDATION_INITIAL_INTENSITY}
            )
            application.processEvents()
            assert capability.call_args.args == (FRONT_SILHOUETTE,)
            assert capability.call_args.kwargs == {
                "notify": dashboard._wardrobe_makeup_read_warning,
            }
            assert not dashboard.wardrobe_makeup_foundation_row.isHidden()
            assert not dashboard.wardrobe_makeup_foundation_label.isHidden()
            assert dashboard.wardrobe_makeup_foundation.value() == FOUNDATION_INITIAL_PERCENT
            assert dashboard.wardrobe_makeup_foundation.accessibleName() == "粉底濃淡"

            global_value = dashboard.wardrobe_makeup_intensity.value()
            lips_value = dashboard.wardrobe_makeup_details["lips"].value()
            dashboard.wardrobe_makeup_foundation.setValue(35)
            application.processEvents()
            assert calls[-1] == (FOUNDATION_SLOT, 0.35)
            assert dashboard.wardrobe_makeup_intensity.value() == global_value
            assert dashboard.wardrobe_makeup_details["lips"].value() == lips_value

            dashboard._wardrobe_makeup_view_changed("yaw+090-pitch+00")
            application.processEvents()
            assert capability.call_args.args == ("yaw+090-pitch+00",)
            assert capability.call_args.kwargs == {
                "notify": dashboard._wardrobe_makeup_read_warning,
            }
            assert dashboard.wardrobe_makeup_foundation_row.isHidden()
            assert dashboard.wardrobe_makeup_foundation_label.isHidden()
    finally:
        close_dashboard(dashboard, db)


def test_foundation_intensity_round_trips_through_the_real_v2_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A v2 foundation value survives UI reload, view changes, and restart."""

    application = QApplication.instance() or QApplication([])
    formal_archive = (
        ROOT
        / "assets"
        / "official-packs"
        / f"{BUILTIN_MAKEUP_PACK_ID}.mohan-outfit"
    )
    official_root = tmp_path / "official"
    official_root.mkdir()
    shutil.copy2(formal_archive, official_root / formal_archive.name)
    monkeypatch.setattr("domain.outfit_pack.OFFICIAL_PACK_ROOT", official_root)

    profile = tmp_path / "profile"
    profile.mkdir()
    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        assert dashboard._active_makeup_slots() == MAKEUP_SLOTS_V2
        assert not dashboard.wardrobe_makeup_foundation_row.isHidden()
        dashboard.wardrobe_makeup_foundation.setValue(FOUNDATION_INITIAL_PERCENT)
        application.processEvents()
        assert json.loads((profile / "outfits" / "makeup.json").read_text(encoding="utf-8")) == {
            "intensity": 1.0,
            "slot_intensities": {FOUNDATION_SLOT: FOUNDATION_INITIAL_INTENSITY},
        }

        dashboard._reload_wardrobe_makeup_options()
        application.processEvents()
        assert dashboard.wardrobe_makeup_foundation.value() == FOUNDATION_INITIAL_PERCENT

        dashboard._wardrobe_makeup_view_changed("yaw+090-pitch+00")
        dashboard._wardrobe_makeup_view_changed(FRONT_SILHOUETTE)
        application.processEvents()
        assert dashboard.wardrobe_makeup_foundation.value() == FOUNDATION_INITIAL_PERCENT
    finally:
        close_dashboard(dashboard, db)

    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        assert dashboard.wardrobe_makeup_foundation.value() == FOUNDATION_INITIAL_PERCENT
    finally:
        close_dashboard(dashboard, db)


def test_foundation_label_has_four_language_translations() -> None:
    expected = {
        "zh-TW": "粉底濃淡",
        "zh-CN": "粉底浓淡",
        "en": "Foundation intensity",
        "ja-JP": "ファンデーションの濃さ",
    }
    assert {
        language: ui_text(language, "wardrobe_makeup_foundation_intensity", "粉底濃淡")
        for language in expected
    } == expected


def test_makeup_pack_imports_through_the_shared_button_persists_and_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = QApplication.instance() or QApplication([])
    official_builtin_pack(tmp_path, monkeypatch)
    source = makeup_pack(tmp_path / "festival-makeup.mohan-outfit")
    profile = tmp_path / "profile"
    profile.mkdir()
    store = profile / "outfits"

    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        selector = dashboard.wardrobe_makeup_selector
        assert selector.currentData() == "builtin/classic"
        assert _menu_ids(dashboard) == [
            "none", "builtin/light", "builtin/classic",
        ]
        with patch.object(QFileDialog, "getOpenFileName", return_value=(str(source), "")):
            dashboard._import_outfit_package()
        application.processEvents()
        assert (store / "packages" / "festival-makeup.mohan-outfit").is_file(), dashboard.wardrobe_status.text()
        assert FESTIVAL_OPTION in _menu_ids(dashboard)
        selector.setCurrentIndex(_menu_ids(dashboard).index(FESTIVAL_OPTION))
        application.processEvents()
        active = json.loads((store / "active.json").read_text(encoding="utf-8"))
        assert active["makeup"] == {"pack_id": "festival-makeup", "item_id": "festival", "variant_id": "classic"}
        assert dashboard.wardrobe_status.text() == "已套用所選妝容。"
        dashboard.wardrobe_makeup_intensity.setValue(HALF_PERCENT)
        application.processEvents()
        assert json.loads((store / "makeup.json").read_text(encoding="utf-8")) == {"intensity": HALF}
        assert dashboard.wardrobe_makeup_intensity_value.text() == f"{HALF_PERCENT}%"
    finally:
        close_dashboard(dashboard, db)

    # Restart: both the selection and the intensity come back from the store.
    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        assert dashboard.wardrobe_makeup_selector.currentData() == FESTIVAL_OPTION
        assert dashboard.wardrobe_makeup_intensity.value() == HALF_PERCENT
        selector = dashboard.wardrobe_makeup_selector
        selector.setCurrentIndex(_menu_ids(dashboard).index("none"))
        application.processEvents()
        assert dashboard.wardrobe_status.text() == "已卸妝，回到素顏。"
        selector.setCurrentIndex(_menu_ids(dashboard).index(FESTIVAL_OPTION))
        application.processEvents()
    finally:
        close_dashboard(dashboard, db)

    # The pack vanishes from disk: the wardrobe falls back to built-in classic and says so once.
    (store / "packages" / "festival-makeup.mohan-outfit").unlink()
    db, dashboard = build_language_dashboard(profile, "zh-TW")
    try:
        assert dashboard.wardrobe_makeup_selector.currentData() == "builtin/classic"
        assert dashboard.wardrobe_status.text() == "所選妝容的套件已不存在，已改回內建標準妝。"
        active = json.loads((store / "active.json").read_text(encoding="utf-8"))
        assert active["makeup"] == {"pack_id": "builtin", "item_id": "builtin", "variant_id": "classic"}
        assert FESTIVAL_OPTION not in _menu_ids(dashboard)
        assert BUILTIN_MAKEUP_PACK_ID not in _menu_ids(dashboard)
        assert dashboard.wardrobe_service.makeup_options()[1].selection.item_id == BUILTIN_MAKEUP_ITEM_ID
    finally:
        close_dashboard(dashboard, db)
