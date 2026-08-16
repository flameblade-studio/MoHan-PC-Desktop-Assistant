from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import QApplication, QScrollArea

lazy from flagship_ui import FlagshipControlCenter
lazy from infrastructure.db import StudioDB, StudioDBSettingsPort
lazy from infrastructure.openai_vision_preferences_store import (
    OpenAIVisionPreferencesStore,
)
lazy from openai_vision_preferences import OpenAIVisionPreferences


def build_center(root: Path, language: str, *, key_available: bool = True):
    db = StudioDB(root / f"{language}.db")
    store = OpenAIVisionPreferencesStore(StudioDBSettingsPort(db))
    center = FlagshipControlCenter(
        db,
        root,
        language=language,
        openai_vision_store=store,
        openai_vision_key_available=lambda: key_available,
    )
    return db, store, center


def close_center(db: StudioDB, center: FlagshipControlCenter) -> None:
    center.close_services()
    center.deleteLater()
    QApplication.processEvents()
    db.close()


def assert_staged_global_save(root: Path) -> None:
    db, store, center = build_center(root, "zh-TW")
    try:
        authorizations: list[object] = []
        center.openai_vision_authorization_changed.connect(
            authorizations.append
        )
        assert store.load() == OpenAIVisionPreferences()
        center.openai_vision_enabled.setChecked(True)
        center.openai_cloud_vision_enabled.setChecked(True)
        center.openai_vision_object_semantics.setChecked(True)
        assert store.load() == OpenAIVisionPreferences()
        assert authorizations == []
        center.save_draft_settings()
        saved = store.load()
        assert saved.enabled is True
        assert saved.cloud_vision_enabled is True
        assert saved.object_semantics_enabled is True
        assert saved.raw_image_storage_enabled is False
        assert len(authorizations) == 1
        assert authorizations[0].enabled is True
        assert authorizations[0].key_available is True
    finally:
        close_center(db, center)

    restart_db, restart_store, restart_center = build_center(root, "zh-TW")
    try:
        assert restart_store.load().cloud_vision_enabled is True
        assert "持續授權中" in restart_center.openai_vision_status.text()
    finally:
        close_center(restart_db, restart_center)


def assert_immediate_stop_persists_and_emits(root: Path) -> None:
    db, store, center = build_center(root, "zh-TW")
    try:
        store.save(
            OpenAIVisionPreferences(
                enabled=True,
                cloud_vision_enabled=True,
            )
        )
        center.openai_vision_enabled.setChecked(True)
        center.openai_cloud_vision_enabled.setChecked(True)
        stopped: list[bool] = []
        center.openai_vision_stop_requested.connect(lambda: stopped.append(True))
        center.stop_openai_vision_immediately()
        assert stopped == [True]
        assert store.load().enabled is False
        assert store.load().cloud_vision_enabled is False
        assert center.openai_vision_stop_button.isEnabled() is False
    finally:
        close_center(db, center)


def assert_four_languages_accessibility_and_layout(root: Path) -> None:
    expected = {
        "zh-TW": "允許雲端視覺持續運作",
        "zh-CN": "允许云端视觉持续运行",
        "en": "Allow continuous cloud vision",
        "ja-JP": "クラウド視覚の継続動作を許可",
    }
    for language, cloud_label in expected.items():
        db, _store, center = build_center(root / language, language)
        try:
            center.resize(800, 600)
            center.show()
            QApplication.processEvents()
            assert center.openai_cloud_vision_enabled.text() == cloud_label
            controls = (
                center.openai_vision_enabled,
                center.openai_cloud_vision_enabled,
                center.openai_vision_model,
                center.openai_vision_detail,
                center.openai_vision_trigger,
                center.openai_vision_daily_limit,
                center.openai_vision_per_minute_limit,
                center.openai_vision_object_semantics,
                center.openai_vision_web_suggestions,
                center.openai_vision_status,
                center.openai_vision_stop_button,
            )
            assert all(control.accessibleName().strip() for control in controls)
            page = center.tabs.widget(5)
            assert isinstance(page, QScrollArea)
            assert page.horizontalScrollBarPolicy() is Qt.ScrollBarAlwaysOff
            assert page.viewport().width() <= center.width()
        finally:
            close_center(db, center)


def run() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        assert_staged_global_save(root / "staged")
        assert_immediate_stop_persists_and_emits(root / "stop")
        assert_four_languages_accessibility_and_layout(root / "languages")
    print("FLAGSHIP_OPENAI_VISION_UI_OK")


if __name__ == "__main__":
    run()
