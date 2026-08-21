from __future__ import annotations

lazy from contextlib import suppress
lazy from dataclasses import replace
lazy from pathlib import Path
lazy from typing import Any
lazy from urllib.parse import urlparse

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QWidget,
)

lazy from application.companion_phrasebook import (
    PHRASEBOOK_SETTING,
    CompanionPhrasebook,
)
lazy from domain.companion_proactivity_preferences import (
    CompanionProactivityPreferences,
)
lazy from domain.flagship_action_models import RISK_NAMES, ActionRequest

HIGH_RISK_THRESHOLD = 3
MEDIUM_RISK_THRESHOLD = 4
lazy from domain.gesture_configuration import (
    GestureAction,
    GestureBinding,
    GestureConfiguration,
)
lazy from domain.openai_vision_authorization import OpenAIVisionAuthorization
lazy from domain.openai_vision_preferences import (
    OpenAIVisionPreferences,
    VisionDetail,
    VisionTriggerPolicy,
)
lazy from infrastructure.companion_proactivity_preferences_store import (
    CompanionProactivityPreferencesStoreError,
)
lazy from infrastructure.gesture_configuration_store import (
    GestureConfigurationStoreError,
)
lazy from infrastructure.openai_vision_preferences_store import (
    OpenAIVisionPreferencesStoreError,
)
lazy from presentation.flagship.shared import (
    CORE_PERMISSION_LABELS,
    FlagshipDraftValues,
)

__all__ = ('FlagshipSettingsSecurityMixin',)


class FlagshipSettingsSecurityMixin:
    def _security_target_section(self, form: QFormLayout) -> None:
        target_heading = QLabel(self._t("<b>允許操作的資料夾與程式</b>"))
        target_heading.setStyleSheet("color:#2f6987;font-size:15px;")
        self.target_list = QListWidget()
        self.target_list.setMinimumHeight(130)
        target_buttons = QWidget()
        target_line = QHBoxLayout(target_buttons)
        target_line.setContentsMargins(0, 0, 0, 0)
        add_folder = QPushButton(self._t("加入資料夾"))
        add_app = QPushButton(self._t("加入程式"))
        add_web = QPushButton(self._t("加入網站"))
        remove_target = QPushButton(self._t("移除選取項目"))
        target_line.addWidget(add_folder)
        target_line.addWidget(add_app)
        target_line.addWidget(add_web)
        target_line.addWidget(remove_target)
        form.addRow(target_heading)
        form.addRow(self.target_list)
        form.addRow("", target_buttons)
        add_folder.clicked.connect(self.add_allowed_folder)
        add_app.clicked.connect(self.add_allowed_app)
        add_web.clicked.connect(self.add_allowed_web)
        remove_target.clicked.connect(self.remove_allowed_target)
        self.refresh_allowed_targets()
    def _security_permission_section(
        self,
        form: QFormLayout,
        stored: dict[str, Any],
    ) -> None:
        permission_heading = QLabel(self._t("<b>能力權限</b>"))
        permission_heading.setStyleSheet("color:#2f6987;font-size:15px;")
        form.addRow(permission_heading)
        for capability, label in CORE_PERMISSION_LABELS.items():
            combo = QComboBox()
            for canonical in ("禁止", "每次詢問", "允許"):
                combo.addItem(self._t(canonical), canonical)
            risk = self.policy.evaluate(ActionRequest(capability, label)).risk
            default = (
                "允許" if risk.value == 1 else "每次詢問" if risk.value < MEDIUM_RISK_THRESHOLD else "禁止"
            )
            stored_mode = str(stored.get(capability, default))
            stored_index = combo.findData(stored_mode)
            combo.setCurrentIndex(max(stored_index, 0))
            if risk.value >= HIGH_RISK_THRESHOLD:
                combo.setToolTip(self._t("即使選擇允許，高風險政策仍會要求確認。"))
            self._permission_controls[capability] = combo
            form.addRow(
                self._t(
                    "{label}（{risk}）",
                    label=self._t(label),
                    risk=self._t(RISK_NAMES[risk]),
                ),
                combo,
            )
    def _security_footer(self, form: QFormLayout) -> None:
        note = QLabel(
            self._t(
                "付款、購買、密碼匯出、停用安全防護、任意 PowerShell／管理員命令"
                "永遠禁止自動執行，無法由此頁解除。"
            )
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#8a5a13;")
        form.addRow(note)
    def validate_draft_settings(self, *, show_error: bool = True) -> FlagshipDraftValues | None:
        """Build every typed value without touching persistence or external services."""

        try:
            gesture = self._staged_gesture_configuration()
            return FlagshipDraftValues(
                gesture=gesture,
                proactivity=self._staged_proactivity_preferences(),
                vision=self._staged_openai_vision_preferences(),
                phrasebook=self._phrasebook_draft.as_setting(),
                proactive_mode=str(self.proactive_mode.currentData()),
                welcome_minimum_seconds=self.minimum_away_minutes.value() * 60,
                conversation_silence_seconds=(
                    self.conversation_silence_minutes.value() * 60
                ),
                security=tuple(
                    (key, str(combo.currentData()))
                    for key, combo in self._permission_controls.items()
                ),
            )
        except (GestureConfigurationStoreError, TypeError, ValueError):
            if show_error:
                self.gesture_command.setFocus(Qt.OtherFocusReason)
                QMessageBox.warning(
                    self,
                    self._t("手勢設定尚未完成"),
                    self._t("選擇自訂文字指令時，必須輸入一行指令後才能保存。"),
                )
            return None
    def _staged_gesture_configuration(self) -> GestureConfiguration:
        definition = self._selected_gesture()
        value = self._gesture_draft.value
        if definition is not None:
            action = GestureAction(str(self.gesture_action.currentData()))
            command = (
                self.gesture_command.text().strip()
                if action is GestureAction.CUSTOM_COMMAND
                else ""
            )
            updated = replace(
                definition,
                enabled=self.gesture_definition_enabled.isChecked(),
                binding=GestureBinding(action, command),
            )
            value = value.replace_definition(updated)
        return replace(value, enabled=self.gesture_enabled.isChecked())
    def _staged_proactivity_preferences(self) -> CompanionProactivityPreferences:
        return CompanionProactivityPreferences(
            enabled=self.companion_enabled.isChecked(),
            meal_enabled=self.companion_meal_enabled.isChecked(),
            hydration_enabled=self.companion_hydration_enabled.isChecked(),
            rest_enabled=self.companion_rest_enabled.isChecked(),
            prolonged_sitting_enabled=self.companion_sitting_enabled.isChecked(),
            special_occasions_enabled=self.companion_occasions_enabled.isChecked(),
            birthday_enabled=self.companion_birthday_enabled.isChecked(),
            brief_absence_seconds=self.companion_brief_minutes.value() * 60,
            long_wait_seconds=self.companion_long_wait_minutes.value() * 60,
            focus_protection_enabled=self.companion_focus_protection.isChecked(),
            meeting_protection_enabled=self.companion_meeting_protection.isChecked(),
            fullscreen_protection_enabled=self.companion_fullscreen_protection.isChecked(),
            daily_limit=self.companion_daily_limit.value(),
        )
    def save_draft_settings(self, values: FlagshipDraftValues | None = None) -> bool:
        """Persist all ordinary settings or restore their exact previous snapshot."""

        self.last_settings_transaction_error = ""
        validated = values or self.validate_draft_settings()
        if validated is None:
            self.last_settings_transaction_error = "validation-failed"
            return False
        before = self.db.settings_snapshot()
        try:
            gesture_before = self.gesture_store.snapshot()
        except GestureConfigurationStoreError:
            self.last_settings_transaction_error = "snapshot-unavailable"
            return False
        try:
            self.openai_vision_store.save(validated.vision)
            self.gesture_store.save(validated.gesture)
            self.proactivity_store.save(validated.proactivity)
            for key, value in (
                ("proactive_interaction_mode", validated.proactive_mode),
                ("multisensory_welcome_minimum_seconds", validated.welcome_minimum_seconds),
                ("multisensory_conversation_silence_seconds", validated.conversation_silence_seconds),
                (PHRASEBOOK_SETTING, validated.phrasebook),
                ("proactive_interaction_enabled", validated.proactivity.enabled),
                ("multisensory_welcome_brief_max_seconds", validated.proactivity.brief_absence_seconds),
                ("multisensory_welcome_long_seconds", validated.proactivity.long_wait_seconds),
                ("flagship_permissions", dict(validated.security)),
            ):
                self.db.set_setting(key, value)
            self._rebuild_draft_settings()
            self._after_successful_settings_save(validated.vision)
        except Exception:
            rollback_incomplete = False
            try:
                self.db.restore_settings_snapshot(before)
            except Exception:
                rollback_incomplete = True
            try:
                self.gesture_store.restore(gesture_before)
            except GestureConfigurationStoreError:
                rollback_incomplete = True
            try:
                self._rebuild_draft_settings()
            except Exception:
                rollback_incomplete = True
            self.last_settings_transaction_error = (
                "rollback-incomplete"
                if rollback_incomplete
                else "save-failed-rolled-back"
            )
            return False
        return True
    def _after_successful_settings_save(self, vision: OpenAIVisionPreferences) -> None:
        self._configure_executor()
        self._refresh_openai_vision_status(vision)
        if self.cloud_vision_service is not None:
            self.cloud_vision_service.refresh_authorization()
        self.openai_vision_authorization_changed.emit(
            OpenAIVisionAuthorization.from_preferences(
                vision,
                key_available=self._openai_vision_has_key(),
            )
        )
        if self.camera_enabled.isChecked():
            self._configure_gesture_runtime()
    def cancel_draft_settings(self) -> None:
        """Close every old draft, rebuild from persistence, and refresh its UI."""

        self._rebuild_draft_settings()
    def _close_drafts(self) -> None:
        for draft in (
            self._gesture_draft,
            self._proactivity_draft,
            self._openai_vision_draft,
        ):
            with suppress(
                GestureConfigurationStoreError,
                CompanionProactivityPreferencesStoreError,
                OpenAIVisionPreferencesStoreError,
            ):
                draft.cancel()
    def reload_draft_settings(self) -> None:
        """Reload controls after an owning settings transaction restores the DB."""

        self._rebuild_draft_settings()
    def _rebuild_draft_settings(self) -> None:
        self._close_drafts()
        self._gesture_draft = self.gesture_store.begin_edit()
        self._proactivity_draft = self.proactivity_store.begin_edit()
        self._openai_vision_draft = self.openai_vision_store.begin_edit()
        self._phrasebook_draft = CompanionPhrasebook.from_setting(
            self.db.setting(PHRASEBOOK_SETTING, {})
        )
        self._refresh_gesture_controls()
        self._refresh_proactivity_controls()
        self._refresh_openai_vision_controls()
    def _refresh_gesture_controls(self) -> None:
        self.gesture_enabled.setChecked(self._gesture_draft.value.enabled)
        self._refresh_gesture_list()
    def _refresh_proactivity_controls(self) -> None:
        preferences = self._proactivity_draft.value
        controls = (
            (self.companion_enabled, preferences.enabled),
            (self.companion_meal_enabled, preferences.meal_enabled),
            (self.companion_hydration_enabled, preferences.hydration_enabled),
            (self.companion_rest_enabled, preferences.rest_enabled),
            (self.companion_sitting_enabled, preferences.prolonged_sitting_enabled),
            (self.companion_occasions_enabled, preferences.special_occasions_enabled),
            (self.companion_birthday_enabled, preferences.birthday_enabled),
            (self.companion_focus_protection, preferences.focus_protection_enabled),
            (self.companion_meeting_protection, preferences.meeting_protection_enabled),
            (self.companion_fullscreen_protection, preferences.fullscreen_protection_enabled),
        )
        for control, checked in controls:
            control.setChecked(checked)
        self.companion_brief_minutes.setValue(preferences.brief_absence_seconds // 60)
        self.companion_long_wait_minutes.setValue(preferences.long_wait_seconds // 60)
        self.companion_daily_limit.setValue(preferences.daily_limit)
    def _refresh_openai_vision_controls(self) -> None:
        preferences = self._openai_vision_draft.value
        self.openai_vision_enabled.setChecked(preferences.enabled)
        self.openai_cloud_vision_enabled.setChecked(preferences.cloud_vision_enabled)
        self.openai_vision_object_semantics.setChecked(preferences.object_semantics_enabled)
        self.openai_vision_web_suggestions.setChecked(preferences.web_search_suggestions_enabled)
        self._select_combo_data(self.openai_vision_model, preferences.model_id)
        self._select_combo_data(self.openai_vision_detail, preferences.detail.value)
        self._select_combo_data(self.openai_vision_trigger, preferences.trigger_policy.value)
        self.openai_vision_daily_limit.setValue(preferences.daily_limit)
        self.openai_vision_per_minute_limit.setValue(preferences.per_minute_limit)
        self._refresh_openai_vision_status(preferences)
    def _staged_openai_vision_preferences(self) -> OpenAIVisionPreferences:
        return OpenAIVisionPreferences(
            enabled=self.openai_vision_enabled.isChecked(),
            cloud_vision_enabled=self.openai_cloud_vision_enabled.isChecked(),
            model_id=str(self.openai_vision_model.currentData()),
            detail=VisionDetail(self.openai_vision_detail.currentData()),
            trigger_policy=VisionTriggerPolicy(
                self.openai_vision_trigger.currentData()
            ),
            daily_limit=self.openai_vision_daily_limit.value(),
            per_minute_limit=self.openai_vision_per_minute_limit.value(),
            object_semantics_enabled=(
                self.openai_vision_object_semantics.isChecked()
            ),
            web_search_suggestions_enabled=(
                self.openai_vision_web_suggestions.isChecked()
            ),
            raw_image_storage_enabled=False,
        )
    def _security_tab(self) -> QWidget:
        scroll, form = self._scroll_form()
        stored = self.db.setting("flagship_permissions", {})
        self._security_target_section(form)
        self._security_permission_section(form, stored)
        self._security_footer(form)
        return scroll
    def refresh_allowed_targets(self) -> None:
        self.target_list.clear()
        for row in self.db.allowed_targets():
            kind = {
                "folder": self._t("資料夾"),
                "app": self._t("程式"),
                "web": self._t("網站"),
            }.get(str(row["target_type"]), str(row["target_type"]))
            access_mode = {
                "read": self._t("只讀"),
                "write": self._t("可寫"),
                "control": self._t("控制"),
            }.get(str(row["access_mode"]), str(row["access_mode"]))
            item = QListWidgetItem(
                f"{kind}｜{row['display_name']}｜{row['target_value']}｜{access_mode}"
            )
            item.setData(Qt.UserRole, int(row["id"]))
            self.target_list.addItem(item)
    def add_allowed_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            self._t("選擇允許墨寒操作的資料夾"),
        )
        if not path:
            return
        mode, ok = self._simple_text_dialog(
            self._t("資料夾權限"),
            self._t("輸入 read（只讀）或 write（可建立、移動與重新命名）"),
        )
        if not ok:
            return
        access_mode = "write" if mode.casefold() == "write" else "read"
        self.db.add_allowed_target(
            "folder",
            Path(path).name or path,
            path,
            access_mode,
        )
        self.refresh_allowed_targets()
        self._configure_executor()
    def add_allowed_app(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self,
            self._t("選擇允許墨寒啟動的程式"),
            "",
            (
                self._t("Windows 程式 (*.exe);;所有檔案 (*)")
                if self.platform_services.capabilities.platform_id == "windows"
                else self._t("應用程式／可執行檔 (*);;所有檔案 (*)")
            ),
        )
        if not path:
            return
        name, ok = self._simple_text_dialog(
            self._t("程式別名"),
            self._t("日後對墨寒說的程式名稱"),
        )
        if not ok or not name:
            return
        self.db.add_allowed_target(
            "app",
            name,
            path,
            "control",
        )
        self.refresh_allowed_targets()
        self._configure_executor()
    def add_allowed_web(self) -> None:
        url, ok = self._simple_text_dialog(
            self._t("加入允許網站"),
            self._t("輸入完整 HTTPS 網址（可限制到指定路徑）"),
        )
        if not ok or not url:
            return
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            QMessageBox.information(
                self,
                self._t("網站白名單"),
                self._t("公開網站只接受完整 HTTPS 網址。"),
            )
            return
        self.db.add_allowed_target(
            "web",
            parsed.hostname or url,
            url.rstrip("/"),
            "control",
        )
        self.refresh_allowed_targets()
        self._configure_executor()
    def remove_allowed_target(self) -> None:
        item = self.target_list.currentItem()
        if item is None:
            return
        if (
            QMessageBox.question(
                self,
                self._t("移除允許項目"),
                self._t("確定撤銷墨寒對此項目的存取權？"),
            )
            != QMessageBox.Yes
        ):
            return
        self.db.remove_allowed_target(int(item.data(Qt.UserRole)))
        self.refresh_allowed_targets()
        self._configure_executor()
    def save_security(self) -> None:
        values = {
            key: str(combo.currentData())
            for key, combo in self._permission_controls.items()
        }
        self.db.set_setting("flagship_permissions", values)
        self._configure_executor()
        self.speak_requested.emit(
            self._t("安全權限已保存。妾會守住這條界線。"),
            "happy",
        )
