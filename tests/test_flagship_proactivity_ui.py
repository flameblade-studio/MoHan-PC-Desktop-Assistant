from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import QApplication, QDialog, QPushButton, QScrollArea

lazy from companion_phrasebook import (
    PHRASEBOOK_SETTING,
    CompanionPhrasebook,
    grouped_phrasebook_categories,
)
lazy from companion_proactivity_preferences import CompanionProactivityPreferences
lazy from flagship_ui import ControlCenterDependencies, FlagshipControlCenter
lazy from infrastructure.companion_proactivity_preferences_store import (
    CompanionProactivityPreferencesStore,
)
lazy from infrastructure.db import StudioDB, StudioDBSettingsPort

PHRASEBOOK_CATEGORY_COUNT = 28
LONG_WAIT_MIN_MINUTES = 121


def build_center(root: Path, language: str = "zh-TW"):
    db = StudioDB(root / f"{language}.db")
    store = CompanionProactivityPreferencesStore(StudioDBSettingsPort(db))
    center = FlagshipControlCenter(
        db,
        root,
        language=language,
        dependencies=ControlCenterDependencies(proactivity_store=store),
    )
    return db, store, center


def close_center(db: StudioDB, center: FlagshipControlCenter) -> None:
    center.close_services()
    center.deleteLater()
    QApplication.processEvents()
    db.close()


def assert_staged_global_save_and_cancel(root: Path) -> None:
    db, store, center = build_center(root)
    try:
        original = store.load()
        center.companion_enabled.setChecked(False)
        center.companion_meal_enabled.setChecked(False)
        center.companion_hydration_enabled.setChecked(False)
        center.companion_rest_enabled.setChecked(False)
        center.companion_sitting_enabled.setChecked(False)
        center.companion_occasions_enabled.setChecked(False)
        center.companion_birthday_enabled.setChecked(False)
        center.companion_focus_protection.setChecked(False)
        center.companion_meeting_protection.setChecked(False)
        center.companion_fullscreen_protection.setChecked(False)
        center.companion_brief_minutes.setValue(15)
        center.companion_long_wait_minutes.setValue(120)
        center.companion_daily_limit.setValue(4)
        assert store.load() == original

        staged_phrasebook = CompanionPhrasebook(
            {}, (), {"wellbeing.meal.initial": ("private fixture",)}
        )
        center._phrasebook_draft = staged_phrasebook
        assert db.setting(PHRASEBOOK_SETTING, None) is None
        center.save_draft_settings()
        assert store.load() == CompanionProactivityPreferences(
            enabled=False,
            meal_enabled=False,
            hydration_enabled=False,
            rest_enabled=False,
            prolonged_sitting_enabled=False,
            special_occasions_enabled=False,
            birthday_enabled=False,
            brief_absence_seconds=900,
            long_wait_seconds=7200,
            focus_protection_enabled=False,
            meeting_protection_enabled=False,
            fullscreen_protection_enabled=False,
            daily_limit=4,
        )
        assert CompanionPhrasebook.from_setting(
            db.setting(PHRASEBOOK_SETTING, {})
        ) == staged_phrasebook
    finally:
        close_center(db, center)

    cancel_db, cancel_store, cancel_center = build_center(root / "cancel")
    try:
        cancel_center.companion_enabled.setChecked(False)
        cancel_center._phrasebook_draft = CompanionPhrasebook(
            {}, ("private uncommitted fixture",), {}
        )
        assert cancel_store.load() == CompanionProactivityPreferences()
        assert cancel_db.setting(PHRASEBOOK_SETTING, None) is None
    finally:
        close_center(cancel_db, cancel_center)


def assert_phrasebook_has_24_discoverable_staged_groups(root: Path) -> None:
    categories = tuple(
        item
        for _group, group_categories in grouped_phrasebook_categories()
        for item in group_categories
    )
    assert len(categories) == PHRASEBOOK_CATEGORY_COUNT
    assert len({key for key, _title in categories}) == PHRASEBOOK_CATEGORY_COUNT
    db, _store, center = build_center(root)
    try:
        before = db.settings_snapshot()
        with patch.object(QDialog, "exec", return_value=QDialog.Accepted):
            center.edit_companion_phrasebook()
        assert db.settings_snapshot() == before
        assert center.companion_phrasebook_button.text() == (
            "編輯 28 組多情境詞庫"
        )
        visible_subpage_saves = [
            button.text()
            for button in center.findChildren(QPushButton)
            if button.text() in {"儲存", "保存", "Save"}
        ]
        assert visible_subpage_saves == []
    finally:
        close_center(db, center)


def assert_four_languages_accessibility_and_small_layout(root: Path) -> None:
    expected_tabs = {
        "zh-TW": "陪伴與關心",
        "zh-CN": "陪伴与关怀",
        "en": "Companion Care",
        "ja-JP": "寄り添いと気遣い",
    }
    for language, tab_title in expected_tabs.items():
        db, _store, center = build_center(root / language, language)
        try:
            center.resize(800, 600)
            center.show()
            QApplication.processEvents()
            titles = [
                center.tabs.tabText(index)
                for index in range(center.tabs.count())
            ]
            assert tab_title in titles
            center.tabs.setCurrentIndex(titles.index(tab_title))
            page = center.tabs.currentWidget()
            assert isinstance(page, QScrollArea)
            assert page.horizontalScrollBarPolicy() is Qt.ScrollBarAlwaysOff
            assert page.viewport().width() <= center.width()
            controls = (
                center.companion_enabled,
                center.companion_meal_enabled,
                center.companion_hydration_enabled,
                center.companion_rest_enabled,
                center.companion_sitting_enabled,
                center.companion_occasions_enabled,
                center.companion_birthday_enabled,
                center.companion_focus_protection,
                center.companion_meeting_protection,
                center.companion_fullscreen_protection,
                center.companion_brief_minutes,
                center.companion_long_wait_minutes,
                center.companion_daily_limit,
                center.companion_phrasebook_button,
            )
            assert all(control.accessibleName().strip() for control in controls)
            for prefix, editor in (
                ("companionBriefMinutes", center.companion_brief_minutes),
                ("companionLongWaitMinutes", center.companion_long_wait_minutes),
                ("companionDailyLimit", center.companion_daily_limit),
            ):
                up = center.findChild(QPushButton, f"{prefix}Up")
                down = center.findChild(QPushButton, f"{prefix}Down")
                assert up is not None and down is not None
                assert up.accessibleName().strip()
                assert down.accessibleName().strip()
                before = editor.value()
                up.click()
                QApplication.processEvents()
                assert editor.value() == min(editor.maximum(), before + 1)
                down.click()
                QApplication.processEvents()
                assert editor.value() == before
            center.companion_brief_minutes.setValue(120)
            assert center.companion_long_wait_minutes.minimum() == LONG_WAIT_MIN_MINUTES
            assert center.companion_long_wait_minutes.value() >= LONG_WAIT_MIN_MINUTES
        finally:
            close_center(db, center)


def run() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        assert_staged_global_save_and_cancel(root / "staged")
        assert_phrasebook_has_24_discoverable_staged_groups(root / "phrases")
        assert_four_languages_accessibility_and_small_layout(root / "locales")
    print("FLAGSHIP_PROACTIVITY_UI_OK")


if __name__ == "__main__":
    run()
