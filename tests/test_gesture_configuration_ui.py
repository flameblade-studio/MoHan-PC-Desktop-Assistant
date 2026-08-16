from __future__ import annotations

lazy import os
lazy import sqlite3
lazy import sys
lazy import zipfile
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMessageBox,
    QScrollArea,
)

lazy from flagship_ui import FlagshipControlCenter
lazy from gesture_configuration import (
    GESTURE_ACTION_LABELS,
    LANDMARKS_PER_HAND,
    GestureAction,
    GestureLandmark,
    GestureSample,
    GestureSource,
    export_gesture_configuration,
)
lazy from infrastructure.companion_proactivity_preferences_store import (
    CompanionProactivityPreferencesStoreError,
)
lazy from infrastructure.db import StudioDB, StudioDBSettingsPort
lazy from infrastructure.gesture_configuration_store import (
    GESTURE_CONFIGURATION_KEY,
    GestureConfigurationStore,
    GestureConfigurationStoreError,
)
lazy from infrastructure.gesture_template_store import ProtectedGestureTemplateStore
lazy from infrastructure.openai_vision_preferences_store import (
    OpenAIVisionPreferencesStoreError,
)
lazy from infrastructure.profile_transfer import (
    PORTABLE_SETTING_KEYS,
    PortableProfileManager,
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture(scope="module", autouse=True)
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


class Recorder:
    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.requests: list[str] = []

    def available(self) -> bool:
        return self._available

    def record(self, gesture_id: str) -> GestureSample | None:
        self.requests.append(gesture_id)
        return GestureSample(
            tuple(GestureLandmark(index / 100, 0.25) for index in range(LANDMARKS_PER_HAND))
        )


class MemorySecretStore:
    def __init__(self) -> None:
        self.value = ""

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


def build_center(root: Path, language: str = "zh-TW", recorder=None):
    root.mkdir(parents=True, exist_ok=True)
    db = StudioDB(root / f"{language}.db")
    store = GestureConfigurationStore(
        StudioDBSettingsPort(db),
        ProtectedGestureTemplateStore(MemorySecretStore()),
    )
    center = FlagshipControlCenter(
        db,
        root,
        language=language,
        gesture_store=store,
        gesture_recorder=recorder,
    )
    center.show()
    QApplication.processEvents()
    return db, store, center


def close_center(db: StudioDB, center: FlagshipControlCenter) -> None:
    center.close_services()
    center.deleteLater()
    QApplication.processEvents()
    db.close()


def select_gesture(center: FlagshipControlCenter, gesture_id: str) -> None:
    for row in range(center.gesture_list.count()):
        item = center.gesture_list.item(row)
        if item.data(0x0100) == gesture_id:
            center.gesture_list.setCurrentRow(row)
            return
    raise AssertionError(f"gesture not found: {gesture_id}")


def test_staged_edit_global_save_and_cancel(root: Path) -> None:
    db, store, center = build_center(root / "save")
    try:
        original = store.load()
        assert original.enabled is False
        center.gesture_enabled.setChecked(True)
        select_gesture(center, "wave")
        center.gesture_action.setCurrentIndex(
            center.gesture_action.findData(GestureAction.MUTE_AUDIO.value)
        )
        center.gesture_definition_enabled.setChecked(False)
        select_gesture(center, "silence")
        center.gesture_action.setCurrentIndex(
            center.gesture_action.findData(GestureAction.UNMUTE_AUDIO.value)
        )
        select_gesture(center, "wave")
        assert store.load() == original
        center.save_draft_settings()
        saved = store.load()
        assert saved.enabled is True
        assert saved.definition("wave").enabled is False
        assert saved.definition("wave").binding.action is GestureAction.MUTE_AUDIO
        assert saved.definition("silence").binding.action is GestureAction.UNMUTE_AUDIO
        center._gesture_draft.value = center._gesture_draft.value.reset_builtin("wave")
        assert center._gesture_draft.value.definition("wave").enabled is True
    finally:
        close_center(db, center)

    cancel_db, cancel_store, cancel_center = build_center(root / "cancel")
    try:
        before = cancel_store.load()
        cancel_center.gesture_enabled.setChecked(True)
        select_gesture(cancel_center, "thumbs-up")
        cancel_center.gesture_definition_enabled.setChecked(False)
        assert cancel_store.load() == before
    finally:
        close_center(cancel_db, cancel_center)


def test_custom_lifecycle_and_real_recorder_port(root: Path) -> None:
    recorder = Recorder()
    db, store, center = build_center(root, recorder=recorder)
    try:
        with patch.object(QInputDialog, "getText", return_value=("節慶問候", True)):
            center.add_custom_gesture()
        custom = next(
            item
            for item in center._gesture_draft.value.definitions
            if item.source is GestureSource.CUSTOM
        )
        select_gesture(center, custom.gesture_id)
        center.gesture_command.setText("請顯示今天的工作摘要")
        center.gesture_action.setCurrentIndex(
            center.gesture_action.findData(GestureAction.CUSTOM_COMMAND.value)
        )
        center.record_custom_gesture()
        assert recorder.requests == [custom.gesture_id]
        staged = center._gesture_draft.value.definition(custom.gesture_id)
        assert len(staged.samples) == 1
        assert store.load().definitions != center._gesture_draft.value.definitions
        center.save_draft_settings()
        saved = store.load().definition(custom.gesture_id)
        assert saved.binding.action is GestureAction.CUSTOM_COMMAND
        assert saved.binding.custom_command == "請顯示今天的工作摘要"
        assert len(saved.samples) == 1
        ordinary = export_gesture_configuration(store.load())
        ordinary_custom = next(
            item
            for item in ordinary["definitions"]
            if item["gesture_id"] == custom.gesture_id
        )
        assert "samples" not in ordinary_custom

        with patch.object(QInputDialog, "getText", return_value=("節慶招呼", True)):
            center.rename_custom_gesture()
        assert center._gesture_draft.value.definition(custom.gesture_id).display_name == "節慶招呼"
        center.delete_custom_gesture()
        assert all(
            item.gesture_id != custom.gesture_id
            for item in center._gesture_draft.value.definitions
        )
    finally:
        close_center(db, center)


def test_unavailable_recorder_is_explicit_and_never_fakes_samples(root: Path) -> None:
    db, _store, center = build_center(root)
    try:
        with patch.object(QInputDialog, "getText", return_value=("自訂", True)):
            center.add_custom_gesture()
        definition = center._selected_gesture()
        assert definition is not None
        assert center.gesture_record_button.isEnabled() is False
        assert "無法安全錄製" in center.gesture_record_status.text()
        center.record_custom_gesture()
        assert center._selected_gesture().samples == ()
    finally:
        close_center(db, center)


def test_cancel_closes_old_drafts_and_restores_ui(root: Path) -> None:
    db, store, center = build_center(root)
    try:
        old_drafts = (
            center._gesture_draft,
            center._proactivity_draft,
            center._openai_vision_draft,
        )
        center.gesture_enabled.setChecked(True)
        select_gesture(center, "wave")
        center.gesture_definition_enabled.setChecked(False)
        center.companion_enabled.setChecked(False)
        center.openai_vision_enabled.setChecked(True)
        center.cancel_draft_settings()
        assert center.gesture_enabled.isChecked() is store.load().enabled
        assert center.gesture_definition_enabled.isChecked() is True
        assert center.companion_enabled.isChecked() is center.proactivity_store.load().enabled
        assert center.openai_vision_enabled.isChecked() is center.openai_vision_store.load().enabled
        for draft in old_drafts:
            try:
                draft.cancel()
            except (
                GestureConfigurationStoreError,
                CompanionProactivityPreferencesStoreError,
                OpenAIVisionPreferencesStoreError,
            ) as error:
                assert "already closed" in str(error)
            else:
                raise AssertionError("cancelled draft remained open")
    finally:
        close_center(db, center)


class FailingProactivityStore:
    def __init__(self, delegate) -> None:
        self.delegate = delegate

    def load(self):
        return self.delegate.load()

    def begin_edit(self):
        return self.delegate.begin_edit()

    def save(self, _value) -> None:
        raise RuntimeError("forced late settings failure")


def test_late_failure_rolls_back_every_setting_and_rebuilds_ui(root: Path) -> None:
    db, store, center = build_center(root)
    try:
        before = db.settings_snapshot()
        center.gesture_enabled.setChecked(True)
        center.companion_enabled.setChecked(False)
        center.proactivity_store = FailingProactivityStore(center.proactivity_store)
        assert center.save_draft_settings() is False
        assert db.settings_snapshot() == before
        assert store.load().enabled is False
        assert center.gesture_enabled.isChecked() is False
    finally:
        close_center(db, center)


def test_post_commit_refresh_failure_also_rolls_back(root: Path) -> None:
    db, store, center = build_center(root)
    try:
        before = db.settings_snapshot()
        center.gesture_enabled.setChecked(True)

        def fail_refresh(_vision) -> None:
            raise RuntimeError("forced post-commit refresh failure")

        center._after_successful_settings_save = fail_refresh
        assert center.save_draft_settings() is False
        assert db.settings_snapshot() == before
        assert store.load().enabled is False
        assert center.gesture_enabled.isChecked() is False
    finally:
        close_center(db, center)


def test_blank_custom_command_is_four_language_visible_and_never_persists(root: Path) -> None:
    expected = {
        "zh-TW": "必須輸入一行指令",
        "zh-CN": "必须输入一行指令",
        "en": "Enter one command",
        "ja-JP": "一行の指示を入力",
    }
    for language, message_part in expected.items():
        db, store, center = build_center(root / language, language)
        try:
            before = db.settings_snapshot()
            with patch.object(QInputDialog, "getText", return_value=("空白指令", True)):
                center.add_custom_gesture()
            center.gesture_action.blockSignals(True)
            try:
                center.gesture_action.setCurrentIndex(
                    center.gesture_action.findData(GestureAction.CUSTOM_COMMAND.value)
                )
            finally:
                center.gesture_action.blockSignals(False)
            center._gesture_action_changed()
            shown: list[str] = []
            with patch.object(
                QMessageBox,
                "warning",
                side_effect=lambda _parent, _title, message, output=shown: output.append(message),
            ):
                center.gesture_command.blockSignals(True)
                try:
                    assert center.save_draft_settings() is False
                finally:
                    center.gesture_command.blockSignals(False)
            assert shown and message_part in shown[0]
            assert center.gesture_command.hasFocus()
            assert db.settings_snapshot() == before
            assert all(
                definition.display_name != "空白指令"
                for definition in store.load().definitions
            )
        finally:
            center.gesture_command.blockSignals(True)
            close_center(db, center)


def test_four_languages_actions_layout_and_portable_contract(root: Path) -> None:
    expected = {
        "zh-TW": "啟用手勢互動",
        "zh-CN": "启用手势互动",
        "en": "Enable gesture interaction",
        "ja-JP": "ジェスチャー操作を有効化",
    }
    for language, enabled_text in expected.items():
        db, _store, center = build_center(root / language, language)
        try:
            center.resize(800, 600)
            center.show()
            QApplication.processEvents()
            assert center.gesture_enabled.text() == enabled_text
            assert center.gesture_action.count() == len(GESTURE_ACTION_LABELS)
            assert center.gesture_list.count() >= 8
            assert isinstance(center.tabs.widget(5), QScrollArea)
            controls = (
                center.gesture_enabled,
                center.gesture_list,
                center.gesture_name,
                center.gesture_action,
                center.gesture_command,
                center.gesture_record_status,
                center.gesture_record_button,
            )
            assert all(control.accessibleName().strip() for control in controls)
        finally:
            close_center(db, center)

    assert GESTURE_CONFIGURATION_KEY in PORTABLE_SETTING_KEYS
    assert all(
        forbidden not in GESTURE_CONFIGURATION_KEY
        for forbidden in ("photo", "image", "key", "secret")
    )


def test_portable_profile_round_trip_has_gestures_but_no_images_or_keys(root: Path) -> None:
    source_db = StudioDB(root / "source" / "mohan.db")
    target_db = StudioDB(root / "target" / "mohan.db")
    try:
        source_store = GestureConfigurationStore(StudioDBSettingsPort(source_db))
        configuration = source_store.load().add_custom("攜帶手勢")
        source_store.save(configuration)
        source_manager = PortableProfileManager(source_db, root / "source" / "backups")
        bundle, _manifest = source_manager.export_profile(root / "gestures")
        with zipfile.ZipFile(bundle, "r") as archive:
            exported_db = root / "exported.db"
            exported_db.write_bytes(archive.read("profile.db"))
        connection = sqlite3.connect(exported_db)
        try:
            raw = connection.execute(
                "SELECT value FROM settings WHERE key=?",
                (GESTURE_CONFIGURATION_KEY,),
            ).fetchone()[0]
        finally:
            connection.close()
        assert "攜帶手勢" in raw
        assert all(
            token not in raw.casefold()
            for token in ("photo", "base64", "api_key", "samples")
        )

        target_manager = PortableProfileManager(target_db, root / "target" / "backups")
        target_manager.import_profile(bundle)
        imported = GestureConfigurationStore(StudioDBSettingsPort(target_db)).load()
        assert export_gesture_configuration(imported) == export_gesture_configuration(configuration)
    finally:
        source_db.close()
        target_db.close()


def run() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        test_staged_edit_global_save_and_cancel(root)
        test_custom_lifecycle_and_real_recorder_port(root / "custom")
        test_unavailable_recorder_is_explicit_and_never_fakes_samples(root / "unavailable")
        test_cancel_closes_old_drafts_and_restores_ui(root / "cancel-drafts")
        test_late_failure_rolls_back_every_setting_and_rebuilds_ui(root / "rollback")
        test_post_commit_refresh_failure_also_rolls_back(root / "refresh-rollback")
        test_blank_custom_command_is_four_language_visible_and_never_persists(root / "blank")
        test_four_languages_actions_layout_and_portable_contract(root / "languages")
        test_portable_profile_round_trip_has_gestures_but_no_images_or_keys(root / "portable")
    print("GESTURE_CONFIGURATION_UI_OK")


if __name__ == "__main__":
    run()
