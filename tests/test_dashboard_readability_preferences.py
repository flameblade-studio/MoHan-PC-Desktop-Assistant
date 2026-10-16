from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtWidgets import QApplication, QFrame, QPushButton, QSplitter

lazy from presentation.desktop_companion_status import (
    DESKTOP_STATUS_COLLAPSED_SETTING,
)
lazy from presentation.lingxiao_shell import update_draft_bar
lazy from presentation.lingxiao_tokens import TYPE_SCALE
lazy from test_global_settings_actions import build_dashboard, close_dashboard

EXPECTED_TYPE_SCALE = {
    "label": 13,
    "body": 15,
    "body_strong": 16,
    "card_title": 18,
    "page_title": 25,
    "section_title": 32,
    "brand": 23,
    "numeral": 17,
}
FEATURE_PAGE_COUNT = 7


def _status_widgets(dashboard):
    stages = dashboard.findChildren(QFrame, "desktopCompanionStage")
    cards = dashboard.findChildren(QFrame, "desktopCompanionStatusCard")
    toggles = dashboard.findChildren(QPushButton, "desktopCompanionStatusToggle")
    splitters = dashboard.findChildren(QSplitter, "featurePageSplitter")
    assert len(stages) == FEATURE_PAGE_COUNT
    assert len(cards) == FEATURE_PAGE_COUNT
    assert len(toggles) == FEATURE_PAGE_COUNT
    assert len(splitters) == FEATURE_PAGE_COUNT
    return stages, cards, toggles, splitters


def test_owner_selected_type_scale_tokens() -> None:
    assert dict(TYPE_SCALE) == EXPECTED_TYPE_SCALE


def test_status_cards_default_to_expanded_for_legacy_profiles() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        db, dashboard = build_dashboard(Path(temporary))
        try:
            stages, cards, toggles, splitters = _status_widgets(dashboard)
            assert db.setting(DESKTOP_STATUS_COLLAPSED_SETTING, False) is False
            assert all(stage.property("mohanStatusCollapsed") is False for stage in stages)
            assert all(not card.isHidden() for card in cards)
            assert all(toggle.isChecked() for toggle in toggles)
            assert all(
                splitter.sizes()[0] > splitter.sizes()[1] / 3
                for splitter in splitters
            )
        finally:
            close_dashboard(dashboard, db)


def test_status_collapse_is_immediate_persisted_and_not_a_settings_draft() -> None:
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        db, dashboard = build_dashboard(root)
        try:
            original = dashboard._settings_draft_snapshot
            _stages, _cards, toggles, _splitters = _status_widgets(dashboard)
            toggles[0].click()
            application.processEvents()

            stages, cards, toggles, splitters = _status_widgets(dashboard)
            assert db.setting(DESKTOP_STATUS_COLLAPSED_SETTING) is True
            assert dashboard._settings_draft_snapshot == original
            assert update_draft_bar(dashboard) == 0
            assert all(stage.property("mohanStatusCollapsed") is True for stage in stages)
            assert all(card.isHidden() for card in cards)
            assert all(not toggle.isChecked() for toggle in toggles)
            assert all(
                splitter.sizes()[0] < splitter.sizes()[1]
                for splitter in splitters
            )

            dashboard.cancel_settings_changes()
            assert db.setting(DESKTOP_STATUS_COLLAPSED_SETTING) is True
        finally:
            close_dashboard(dashboard, db)

        reopened_db, reopened = build_dashboard(root)
        try:
            stages, cards, toggles, _splitters = _status_widgets(reopened)
            assert reopened_db.setting(DESKTOP_STATUS_COLLAPSED_SETTING) is True
            assert all(stage.property("mohanStatusCollapsed") is True for stage in stages)
            assert all(card.isHidden() for card in cards)
            assert all(not toggle.isChecked() for toggle in toggles)
        finally:
            close_dashboard(reopened, reopened_db)
