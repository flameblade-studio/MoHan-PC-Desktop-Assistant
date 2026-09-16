"""UI round trip for independent headwear through the real preview renderer."""

from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS))

lazy import pytest
lazy from PySide6.QtCore import QRect
lazy from PySide6.QtWidgets import QApplication

lazy from presentation import dashboard_wardrobe_categories as appearance_ui
lazy from domain.outfit_pack import OutfitPackError, resolve_active_selection
lazy from test_global_settings_actions import close_dashboard
lazy from test_wardrobe_preview_composite import (
    _build,
    _dependencies,
    _open_wardrobe,
    _wait_composited,
)

WARDROBE_TAB = "雲裳閣"
HEADWEAR = "headwear"
NONE_OPTION = "none"
HEADWEAR_REGION = QRect(400, 70, 260, 240)
FULL_BODY_SIZE = (1024, 1536)
MIN_CATEGORY_TABS = 5


def _resolution_signature(resolution) -> tuple[object, ...]:
    return (
        resolution.status,
        resolution.requested_pack_id,
        resolution.requested_item_id,
        resolution.requested_variant_id,
        resolution.effective_pack_id,
        resolution.effective_item_id,
        resolution.effective_variant_id,
    )


def _effective_id(resolution) -> str:
    return "/".join(
        (
            resolution.effective_pack_id,
            resolution.effective_item_id,
            resolution.effective_variant_id,
        )
    )


def _headwear_option_ids(selector) -> tuple[str, ...]:
    return tuple(
        str(selector.itemData(index))
        for index in range(selector.count())
        if selector.itemData(index) is not None
    )


def _round_trip_headwear(
    application: QApplication,
    dashboard,
    store: Path,
) -> str:
    before_preview = dashboard._wardrobe_pose_source.toImage().copy()
    assert before_preview.size().toTuple() == FULL_BODY_SIZE
    before_garment = _resolution_signature(
        resolve_active_selection(store, "garment")
    )
    before_makeup = _resolution_signature(
        resolve_active_selection(store, "makeup")
    )
    selector = dashboard.wardrobe_appearance_selectors[HEADWEAR]
    button = dashboard.wardrobe_appearance_buttons[HEADWEAR]
    option_ids = _headwear_option_ids(selector)
    assert NONE_OPTION in option_ids
    official_ids = tuple(
        option_id for option_id in option_ids if option_id != NONE_OPTION
    )
    assert official_ids
    official_id = official_ids[0]
    assert selector.findData(official_id) >= 0
    assert button.isEnabled()

    selector.setCurrentIndex(selector.findData(NONE_OPTION))
    application.processEvents()
    button.click()
    application.processEvents()
    _wait_composited(dashboard)
    after_none_preview = dashboard._wardrobe_pose_source.toImage().copy()
    assert before_preview.copy(HEADWEAR_REGION) != after_none_preview.copy(
        HEADWEAR_REGION
    )
    assert _effective_id(resolve_active_selection(store, HEADWEAR)) == (
        "builtin/none/none"
    )
    assert _resolution_signature(
        resolve_active_selection(store, "garment")
    ) == before_garment
    assert _resolution_signature(
        resolve_active_selection(store, "makeup")
    ) == before_makeup

    selector.setCurrentIndex(selector.findData(official_id))
    application.processEvents()
    button.click()
    application.processEvents()
    _wait_composited(dashboard)
    restored_preview = dashboard._wardrobe_pose_source.toImage().copy()
    assert after_none_preview.copy(HEADWEAR_REGION) != restored_preview.copy(
        HEADWEAR_REGION
    )
    assert before_preview.copy(HEADWEAR_REGION) == restored_preview.copy(
        HEADWEAR_REGION
    )
    assert _effective_id(resolve_active_selection(store, HEADWEAR)) == official_id
    assert _resolution_signature(
        resolve_active_selection(store, "garment")
    ) == before_garment
    assert _resolution_signature(
        resolve_active_selection(store, "makeup")
    ) == before_makeup
    assert selector.currentData() == official_id
    return official_id


def _assert_tabs_are_reachable(
    application: QApplication,
    dashboard,
) -> None:
    category_tabs = dashboard.wardrobe_category_tabs
    assert category_tabs.count() >= MIN_CATEGORY_TABS
    for index in range(category_tabs.count()):
        category_tabs.setCurrentIndex(index)
        application.processEvents()
        assert category_tabs.currentIndex() == index
        assert category_tabs.currentWidget() is not None

    main_tabs = dashboard.tabs
    main_tab_names = tuple(
        main_tabs.tabText(index) for index in range(main_tabs.count())
    )
    assert WARDROBE_TAB in main_tab_names
    for index in range(main_tabs.count()):
        main_tabs.setCurrentIndex(index)
        application.processEvents()
        assert main_tabs.currentIndex() == index
        assert main_tabs.currentWidget() is not None
    main_tabs.setCurrentIndex(main_tab_names.index(WARDROBE_TAB))
    application.processEvents()
    category_tabs.setCurrentIndex(2)
    application.processEvents()


def _assert_apply_error_is_global(
    application: QApplication,
    dashboard,
    store: Path,
    official_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_apply(
        _service,
        _category: str,
        _option_id: str,
    ) -> None:
        raise OutfitPackError("forced test failure")

    monkeypatch.setattr(
        appearance_ui.WardrobeAppearanceService,
        "apply",
        reject_apply,
    )
    selector = dashboard.wardrobe_appearance_selectors[HEADWEAR]
    button = dashboard.wardrobe_appearance_buttons[HEADWEAR]
    selector.setCurrentIndex(selector.findData(official_id))
    application.processEvents()
    button.click()
    application.processEvents()
    assert dashboard.wardrobe_status.isVisibleTo(dashboard)
    assert dashboard.wardrobe_status.text() == dashboard._t(
        "wardrobe_appearance_apply_failed",
        '套用髮型或頭飾需要處理；目前外觀持續使用。',
    )
    assert _effective_id(resolve_active_selection(store, HEADWEAR)) == official_id


def test_headwear_none_and_official_round_trip_through_real_preview(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The headwear card drives the real compositor and preserves other slots."""
    application = QApplication.instance() or QApplication([])
    profile = tmp_path / "isolated-profile"
    profile.mkdir()
    db, dashboard = _build(profile, _dependencies(profile))
    try:
        _open_wardrobe(dashboard)
        _wait_composited(dashboard)
        official_id = _round_trip_headwear(
            application,
            dashboard,
            profile / "outfits",
        )
        _assert_tabs_are_reachable(application, dashboard)
        _assert_apply_error_is_global(
            application,
            dashboard,
            profile / "outfits",
            official_id,
            monkeypatch,
        )
    finally:
        close_dashboard(dashboard, db)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

