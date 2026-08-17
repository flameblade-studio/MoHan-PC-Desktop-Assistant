from __future__ import annotations

lazy import html

lazy from PySide6.QtWidgets import QMessageBox

lazy from domain.app_profile import (
    ProfileLocalizationContext,
    ProfileSettingsValues,
    default_persona_for_language,
    profile_setting,
    profile_window_title,
)
lazy from domain.language_support import (
    english_voice_instructions,
    is_builtin_transcription_prompt,
    japanese_voice_instructions,
    localized_transcription_prompt,
    localized_voice_instructions,
    migrate_builtin_reminder_line,
    simplified_chinese_voice_instructions,
    transcription_language_for_ui,
)
lazy from domain.safe_error_localization import safe_error_message
lazy from domain.speech_configuration import (
    OPENAI_SECRET_POLICY,
    VOICE_GENERATION_PROMPT,
    combo_data_or_custom_text,
)
lazy from presentation.companion_platform import REMINDER_LINES, reminder_line
lazy from presentation.settings_ui_localization import SettingsText

__all__ = ("DashboardSettingsPersistenceMixin",)


class DashboardSettingsPersistenceMixin:
    def save_permissions(self) -> None:
        permissions = {
            key: str(combo.currentData() or "禁止")
            for key, combo in self.permission_controls.items()
        }
        self.db.set_setting("tool_permissions", permissions)
        if not getattr(self, "_saving_all_settings", False):
            self.speak_requested.emit(
                self._t(
                    "permission_saved_speech",
                    "電腦工具權限已保存。妾會照此邊界行事。",
                ),
                "happy",
            )

    def _permission_allowed(self, key: str, action: str) -> bool:
        stored = self.db.setting("tool_permissions", {})
        default = "禁止" if key == "delete_files" else "每次詢問"
        mode = str(stored.get(key, default))
        if hasattr(self, "permission_controls") and key in self.permission_controls:
            mode = str(self.permission_controls[key].currentData() or default)
        if mode == "允許":
            return True
        if mode == "禁止":
            QMessageBox.information(
                self,
                self._t("permission_blocked", "權限已阻擋"),
                self._t(
                    "permission_blocked_message",
                    "墨寒目前無權{action}。",
                    action=action,
                ),
            )
            return False
        answer = QMessageBox.question(
            self,
            self._t(
                "permission_request",
                "墨寒請求電腦權限",
            ),
            self._t(
                "permission_request_message",
                "是否允許墨寒這一次{action}？",
                action=action,
            ),
        )
        return answer == QMessageBox.Yes

    def _current_profile_localization(self) -> ProfileLocalizationContext:
        return ProfileLocalizationContext(
            assistant_name=self.assistant_name,
            user_title=self.user_title,
            organization_name=self.organization_name,
            wake_word=profile_setting(self.db, "wake_word"),
            ui_language=self.ui_language,
        )

    def _validated_profile_settings(
        self,
    ) -> ProfileSettingsValues | None:
        assistant_name = self.profile_assistant_name.text().strip()
        user_title = self.profile_user_title.text().strip()
        if not assistant_name or not user_title:
            QMessageBox.information(
                self,
                self._settings_text(SettingsText.PROFILE_REQUIRED_TITLE),
                self._settings_text(SettingsText.PROFILE_REQUIRED_MESSAGE),
            )
            return None
        return ProfileSettingsValues(
            assistant_name=assistant_name,
            user_title=user_title,
            organization_name=(self.profile_organization_name.text().strip()),
            window_title=self.profile_window_title.text().strip(),
            work_type=combo_data_or_custom_text(
                self.profile_work_type,
                "其他",
            ),
            ui_language=str(self.profile_ui_language.currentData() or "zh-TW"),
            wake_word=(self.profile_wake_word.text().strip() or assistant_name),
        )

    def _persist_profile_settings(
        self,
        values: ProfileSettingsValues,
    ) -> None:
        for key, value in values.setting_items():
            self.db.set_setting(key, value)

    def _migrate_localized_profile_defaults(
        self,
        previous: ProfileLocalizationContext,
        current: ProfileSettingsValues,
    ) -> None:
        self._migrate_transcription_prompt(previous, current.localization)
        if current.ui_language == previous.ui_language:
            return
        self._migrate_transcription_language(current.ui_language)
        self._migrate_voice_instructions(current.ui_language)
        self._migrate_persona_prompt(current.ui_language)
        self._migrate_reminder_messages(current.ui_language)

    def _migrate_transcription_prompt(
        self,
        previous: ProfileLocalizationContext,
        current: ProfileLocalizationContext,
    ) -> None:
        prompt = self.transcription_prompt.toPlainText().strip()
        if not is_builtin_transcription_prompt(
            prompt,
            previous.ui_language,
            assistant_name=previous.assistant_name,
            user_title=previous.user_title,
            organization_name=previous.organization_name,
            wake_word=previous.wake_word,
        ):
            return
        self.transcription_prompt.setPlainText(
            localized_transcription_prompt(
                current.ui_language,
                assistant_name=current.assistant_name,
                user_title=current.user_title,
                organization_name=current.organization_name,
                wake_word=current.wake_word,
            )
        )

    def _migrate_transcription_language(self, ui_language: str) -> None:
        language = self.transcription_language.text().strip()
        if language in {"zh", "en", "ja"}:
            self.transcription_language.setText(
                transcription_language_for_ui(ui_language)
            )

    def _migrate_voice_instructions(self, ui_language: str) -> None:
        instructions = self.voice_instructions.text().strip()
        built_in_instructions = frozenset({
            VOICE_GENERATION_PROMPT,
            english_voice_instructions(),
            simplified_chinese_voice_instructions(),
            japanese_voice_instructions(),
        })
        if instructions in built_in_instructions:
            self.voice_instructions.setText(
                localized_voice_instructions(
                    ui_language,
                    VOICE_GENERATION_PROMPT,
                )
            )

    def _migrate_persona_prompt(self, ui_language: str) -> None:
        persona = self.persona_prompt.toPlainText().strip()
        built_in_personas = frozenset(
            default_persona_for_language(language).strip()
            for language in ("zh-TW", "zh-CN", "en", "ja-JP")
        )
        if persona in built_in_personas:
            self.persona_prompt.setPlainText(default_persona_for_language(ui_language))

    def _migrate_reminder_messages(self, ui_language: str) -> None:
        for kind, message in self.reminder_message_controls.items():
            message.setText(
                migrate_builtin_reminder_line(
                    message.text(),
                    ui_language,
                    kind,
                    REMINDER_LINES[kind],
                )
            )
        self.overwork_message.setText(
            migrate_builtin_reminder_line(
                self.overwork_message.text(),
                ui_language,
                "overwork",
                REMINDER_LINES["overwork"],
            )
        )

    def _apply_saved_profile(self, values: ProfileSettingsValues) -> None:
        self.assistant_name = values.assistant_name
        self.user_title = values.user_title
        self.organization_name = values.organization_name
        title = profile_window_title(self.db)
        self.setWindowTitle(title)
        self.header_title.setText(f"<b>{html.escape(title)}</b>")

    def _save_reminder_settings(self, ui_language: str) -> None:
        for kind, (enabled, reminder_time) in self.reminder_controls.items():
            self.db.update_reminder(
                kind,
                reminder_time.time().toString("HH:mm"),
                enabled.isChecked(),
            )
            message = self.reminder_message_controls[kind].text().strip()
            self.db.set_setting(
                f"reminder_message_{kind}",
                message or reminder_line(ui_language, kind),
            )

    def _save_general_settings(self, ui_language: str) -> None:
        persona = self.persona_prompt.toPlainText().strip()
        overwork_message = self.overwork_message.text().strip()
        settings = (
            ("break_minutes", self.break_minutes.value()),
            (
                "reminder_message_overwork",
                overwork_message or reminder_line(ui_language, "overwork"),
            ),
            ("tts_enabled", self.tts_enabled.isChecked()),
            ("work_folder", self.work_folder.text().strip()),
            ("auto_memory", self.auto_memory.isChecked()),
            ("ai_model", self.ai_model.currentText()),
            (
                "persona_prompt",
                persona or default_persona_for_language(ui_language),
            ),
            (
                "topmost_mode",
                str(self.topmost_mode.currentData() or "智慧置頂（推薦）"),
            ),
            (
                "character_scale_percent",
                self.character_scale_slider.value(),
            ),
            (
                "proactive_mode",
                str(self.proactive_mode.currentData() or "平衡（推薦）"),
            ),
            (
                "background_assistant_enabled",
                self.background_assistant_enabled.isChecked(),
            ),
            (
                "background_watch_apps",
                self.background_watch_apps.text().strip(),
            ),
            (
                "background_diagnostic_report",
                self.background_diagnostic_report.text().strip(),
            ),
        )
        for key, value in settings:
            self.db.set_setting(key, value)
        for key, control in self.physics_controls.items():
            self.db.set_setting(key, control.isChecked())

    def _save_api_key_if_provided(self) -> None:
        saved = self._persist_secret_input(
            self.api_key_input,
            self.secret_store,
            OPENAI_SECRET_POLICY,
            silent=False,
        )
        if saved:
            self.api_status.setText(
                self._t(
                    "api_status_saved",
                    "OpenAI API：金鑰已由作業系統安全保存",
                )
            )

    def _save_autostart_setting(self) -> None:
        if not self.platform_services.capabilities.desktop_autostart:
            self.db.set_setting("autostart", False)
            return
        enabled = self.autostart.isChecked()
        try:
            self.autostart_configurator(enabled, self.platform_services)
        except OSError as exc:
            QMessageBox.warning(
                self,
                self._settings_text(SettingsText.AUTOSTART_ERROR_TITLE),
                self._settings_text(
                    SettingsText.AUTOSTART_ERROR,
                    reason=safe_error_message(self.ui_language, exc),
                ),
            )
            return
        self.db.set_setting("autostart", enabled)

    def _persist_external_settings(self) -> None:
        """Apply non-transactional secrets and device state after DB commit."""

        self._persist_azure_key(silent=False)
        self._persist_azure_hd_key(silent=False)
        self._save_api_key_if_provided()
        self._save_autostart_setting()

    def _finish_settings_save(
        self,
        ui_language: str,
        silent: bool,
    ) -> None:
        self.settings_saved.emit()
        self.ui_language = ui_language
        if not silent:
            self.speak_requested.emit(
                self._t("settings_saved", "設定已保存。"),
                "happy",
            )

    def save_settings(
        self,
        silent: bool = False,
        *,
        persist_external: bool = True,
        finish: bool = True,
    ) -> bool:
        previous = self._current_profile_localization()
        values = self._validated_profile_settings()
        if values is None:
            return False
        self._persist_profile_settings(values)
        self._migrate_localized_profile_defaults(previous, values)
        self._apply_saved_profile(values)
        self._save_reminder_settings(values.ui_language)
        self._save_general_settings(values.ui_language)
        self.save_voice_settings(
            silent=True,
            persist_external=persist_external,
        )
        if persist_external:
            self._save_api_key_if_provided()
            self._save_autostart_setting()
        if finish:
            self._finish_settings_save(values.ui_language, silent)
        return True

    def clear_api_key(self) -> None:
        platform = self.platform_services.capabilities
        answer = QMessageBox.question(
            self,
            self._t("remove_api_key", "移除已保存的 API 金鑰"),
            self._t(
                "remove_api_key_confirm",
                "確定要移除由 {platform} 安全保存的 OpenAI API 金鑰嗎？",
                platform=platform.display_name,
            ),
        )
        if answer == QMessageBox.Yes:
            self.secret_store.clear()
            self.api_key_input.clear()
            self.api_key_input.setPlaceholderText(
                self._t(
                    "api_key_missing",
                    "貼上 sk- 開頭的 OpenAI Project API Key",
                )
            )
            self.api_status.setText(
                self._t(
                    "api_status_offline",
                    "OpenAI API：未設定，使用離線人設",
                )
            )
