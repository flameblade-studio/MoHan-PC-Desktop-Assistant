from __future__ import annotations

lazy from PySide6.QtWidgets import QLineEdit, QMessageBox

lazy from application.presentation_ports import (
    REALTIME_OUTPUT_OPENAI,
    azure_hd_female_voices,
    azure_region_supports_hd_flash,
)
lazy from domain.contracts import SecretStorePort
lazy from domain.safe_error_localization import safe_error_message
lazy from domain.speech_configuration import (
    AZURE_HD_SECRET_POLICY,
    AZURE_SECRET_POLICY,
    VOICE_ENGINE_SYSTEM,
    SecretInputPolicy,
)
lazy from domain.speech_providers import normalize_speech_provider_id

__all__ = ("DashboardVoiceRuntimeMethods",)


class DashboardVoiceRuntimeMethods:
    def _persist_windows_voice_migration(
        self,
        preferred: str,
        saved_voice: str,
        force_default: bool,
    ) -> None:
        if force_default:
            self.db.set_setting("onecore_yating_v181_migrated", True)
        if preferred and (force_default or not saved_voice):
            self.db.set_setting("windows_voice", preferred)

    def _preview_voice(self) -> None:
        self.save_voice_settings(silent=True)
        self.voice_preview_requested.emit()

    def _voice_engine_changed(self, _index: int) -> None:
        provider_id = normalize_speech_provider_id(self.voice_engine.currentData())
        self.db.set_setting("voice_engine", provider_id)

    def _windows_voice_changed(self, _index: int) -> None:
        self.db.set_setting(
            "windows_voice", str(self.windows_voice.currentData() or "")
        )
        self.realtime_output_settings_changed.emit()

    def _voice_rate_changed(self, rate: int) -> None:
        self.db.set_setting("voice_rate", rate)
        self.realtime_output_settings_changed.emit()

    def _openai_voice_changed(self, voice: str) -> None:
        selected_voice = voice.strip()
        if not selected_voice:
            return
        self.db.set_setting("tts_voice", selected_voice)
        self.db.set_setting("cloud_voice", selected_voice)

    def _azure_voice_changed(self, voice: str) -> None:
        selected_voice = voice.strip()
        if not selected_voice:
            return
        self.db.set_setting("azure_speech_voice", selected_voice)
        self.realtime_output_settings_changed.emit()

    def _azure_region_changed(self, _index: int) -> None:
        region = str(self.azure_region.currentData() or "")
        self.db.set_setting("azure_speech_region", region)
        self.realtime_output_settings_changed.emit()
        self._request_azure_voice_catalog(hd_only=False)

    def _azure_hd_voice_changed(self, voice: str) -> None:
        selected_voice = voice.strip()
        if not selected_voice:
            return
        self.db.set_setting("azure_hd_speech_voice", selected_voice)
        self.realtime_output_settings_changed.emit()

    def _azure_hd_region_changed(self, _index: int) -> None:
        region = str(self.azure_hd_region.currentData() or "")
        self.db.set_setting(
            "azure_hd_speech_region",
            region,
        )
        self._refresh_azure_hd_voice_options(region)
        self._request_azure_voice_catalog(hd_only=True)

    def _request_azure_voice_catalog(self, *, hd_only: bool) -> None:
        engine = self.azure_hd_tts if hd_only else self.azure_tts
        secret_store = (
            self.azure_hd_secret_store if hd_only else self.azure_secret_store
        )
        region_combo = self.azure_hd_region if hd_only else self.azure_region
        if engine is None or secret_store is None:
            return
        refresh_catalog = getattr(engine, "refresh_voice_catalog", None)
        if refresh_catalog is None:
            return
        region = str(region_combo.currentData() or "").strip().lower()
        if not region:
            return
        refresh_catalog(
            secret_store.load(),
            region,
            self.ui_language,
            hd_only=hd_only,
        )

    def _apply_azure_voice_catalog(self, catalog: object) -> None:
        hd_only = bool(getattr(catalog, "hd_only", False))
        region_combo = self.azure_hd_region if hd_only else self.azure_region
        expected_region = str(region_combo.currentData() or "").strip().lower()
        if getattr(catalog, "region", "") != expected_region:
            return
        voices = tuple(getattr(catalog, "voices", ()))
        if not voices:
            return
        combo = self.azure_hd_voice if hd_only else self.azure_voice
        setting_key = "azure_hd_speech_voice" if hd_only else "azure_speech_voice"
        current_voice = combo.currentText().strip()
        selected_voice = current_voice if current_voice in voices else voices[0]
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(voices)
        combo.setCurrentText(selected_voice)
        combo.blockSignals(False)
        self.db.set_setting(setting_key, selected_voice)
        if selected_voice != current_voice:
            self.realtime_output_settings_changed.emit()

    def _refresh_azure_hd_voice_options(self, region: str) -> None:
        voices = azure_hd_female_voices(
            self.ui_language,
            include_flash=azure_region_supports_hd_flash(region),
        )
        current_voice = self.azure_hd_voice.currentText().strip()
        selected_voice = current_voice if current_voice in voices else voices[0]
        self.azure_hd_voice.blockSignals(True)
        self.azure_hd_voice.clear()
        self.azure_hd_voice.addItems(voices)
        self.azure_hd_voice.setCurrentText(selected_voice)
        self.azure_hd_voice.blockSignals(False)
        self.db.set_setting("azure_hd_speech_voice", selected_voice)
        self.realtime_output_settings_changed.emit()

    def _realtime_voice_changed(self, voice: str) -> None:
        selected_voice = voice.strip()
        if not selected_voice:
            return
        self.db.set_setting("realtime_voice", selected_voice)
        self.realtime_voice_changed.emit(selected_voice)

    def _realtime_output_mode_index_changed(self, _index: int) -> None:
        mode = str(self.realtime_output_mode.currentData() or REALTIME_OUTPUT_OPENAI)
        self.db.set_setting("realtime_output_mode", mode)
        self._apply_realtime_output_mode_state(mode)
        self.realtime_output_mode_changed.emit(mode)

    def clear_azure_speech_key(self) -> None:
        if self.azure_secret_store is None:
            return
        platform = self.platform_services.capabilities
        answer = QMessageBox.question(
            self,
            self._t("azure_remove_key", "移除 Azure Speech 金鑰"),
            self._t(
                "azure_remove_key_confirm",
                f"確定移除由 {platform.display_name} 安全保存的 Azure Speech 金鑰嗎？",
            ),
        )
        if answer == QMessageBox.Yes:
            self.azure_secret_store.clear()
            self._invalidate_azure_voice_catalog(hd_only=False)
            self.azure_key_input.clear()
            self.azure_key_input.setPlaceholderText(
                self._t(
                    "azure_key_missing",
                    "貼上 Azure Speech 資源金鑰",
                )
            )
            self.realtime_output_settings_changed.emit()

    def clear_azure_hd_speech_key(self) -> None:
        if self.azure_hd_secret_store is None:
            return
        platform = self.platform_services.capabilities
        answer = QMessageBox.question(
            self,
            self._t("azure_hd_remove_key", "移除 Dragon HD S0 金鑰"),
            self._t(
                "azure_hd_remove_key_confirm",
                "確定移除由 {platform} 安全保存的 Dragon HD S0 金鑰嗎？",
                platform=platform.display_name,
            ),
        )
        if answer == QMessageBox.Yes:
            self.azure_hd_secret_store.clear()
            self._invalidate_azure_voice_catalog(hd_only=True)
            self.azure_hd_key_input.clear()
            self.azure_hd_key_input.setPlaceholderText(
                self._t(
                    "azure_hd_key_missing",
                    "貼上獨立的 Dragon HD S0 資源金鑰",
                )
            )
            self.realtime_output_settings_changed.emit()

    def _update_voice_volume_label(self) -> None:
        self.voice_volume_label.setText(f"{self.voice_volume.value()}%")

    def _voice_volume_changed(self, _value=None) -> None:
        self._update_voice_volume_label()
        volume = self.voice_volume.value()
        muted = self.voice_muted.isChecked()
        self.db.set_setting("voice_volume_percent", volume)
        self.db.set_setting("voice_muted", muted)
        self.volume_changed.emit(volume, muted)

    def save_voice_settings(
        self,
        silent: bool = False,
        *,
        persist_external: bool = True,
    ) -> None:
        self.db.set_setting(
            "speech_recognition",
            str(
                self.speech_recognition.currentData()
                or "OpenAI 高準確辨識（推薦）"
            ),
        )
        self.db.set_setting(
            "transcription_model",
            self.transcription_model.currentText().strip(),
        )
        self.db.set_setting(
            "transcription_language",
            self.transcription_language.text().strip(),
        )
        self.db.set_setting(
            "transcription_prompt",
            self.transcription_prompt.toPlainText().strip(),
        )
        self.db.set_setting(
            "windows_transcription_fallback",
            self.windows_transcription_fallback.isChecked(),
        )
        self.db.set_setting(
            "voice_engine",
            str(self.voice_engine.currentData() or VOICE_ENGINE_SYSTEM),
        )
        selected_windows_voice = str(self.windows_voice.currentData() or "")
        if selected_windows_voice:
            self.db.set_setting("windows_voice", selected_windows_voice)
        self.db.set_setting("tts_voice", self.tts_voice.currentText())
        self.db.set_setting("cloud_voice", self.tts_voice.currentText())
        self.db.set_setting("realtime_voice", self.realtime_voice.currentText())
        self.db.set_setting(
            "realtime_output_mode",
            str(self.realtime_output_mode.currentData() or REALTIME_OUTPUT_OPENAI),
        )
        self.db.set_setting(
            "azure_speech_voice",
            self.azure_voice.currentText(),
        )
        self.db.set_setting(
            "azure_speech_region",
            str(self.azure_region.currentData() or ""),
        )
        self.db.set_setting(
            "azure_hd_speech_voice",
            self.azure_hd_voice.currentText(),
        )
        self.db.set_setting(
            "azure_hd_speech_region",
            str(self.azure_hd_region.currentData() or ""),
        )
        if persist_external:
            self._persist_azure_key(silent=silent)
            self._persist_azure_hd_key(silent=silent)
        self.db.set_setting("realtime_model", self.realtime_model.currentText())
        self.db.set_setting(
            "realtime_transcription_model",
            self.realtime_transcription_model.currentText().strip(),
        )
        self.db.set_setting(
            "realtime_noise_reduction",
            str(self.realtime_noise_reduction.currentData() or "near_field"),
        )
        self.db.set_setting(
            "realtime_turn_detection",
            str(self.realtime_turn_detection.currentData() or "server_vad"),
        )
        self.db.set_setting("realtime_echo_guard", self.realtime_echo_guard.isChecked())
        self.db.set_setting(
            "realtime_hybrid_transcription",
            self.realtime_hybrid_transcription.isChecked(),
        )
        self.db.set_setting("voice_rate", self.voice_rate.value())
        self.db.set_setting(
            "voice_volume_percent",
            self.voice_volume.value(),
        )
        self.db.set_setting("voice_muted", self.voice_muted.isChecked())
        self.db.set_setting(
            "voice_instructions", self.voice_instructions.text().strip()
        )
        if not silent:
            self.speak_requested.emit(
                self._t("voice_settings_saved", "聲音設定已保存。"),
                "happy",
            )

    def _save_azure_key_immediately(self) -> None:
        if self._persist_azure_key(silent=False):
            self.realtime_output_settings_changed.emit()
            self._request_azure_voice_catalog(hd_only=False)

    def _save_azure_hd_key_immediately(self) -> None:
        if self._persist_azure_hd_key(silent=False):
            self.realtime_output_settings_changed.emit()
            self._request_azure_voice_catalog(hd_only=True)

    def _persist_azure_key(self, *, silent: bool) -> bool:
        saved = self._persist_secret_input(
            self.azure_key_input,
            self.azure_secret_store,
            AZURE_SECRET_POLICY,
            silent=silent,
        )
        if saved:
            self._invalidate_azure_voice_catalog(hd_only=False)
        return saved

    def _persist_azure_hd_key(self, *, silent: bool) -> bool:
        saved = self._persist_secret_input(
            self.azure_hd_key_input,
            self.azure_hd_secret_store,
            AZURE_HD_SECRET_POLICY,
            silent=silent,
        )
        if saved:
            self._invalidate_azure_voice_catalog(hd_only=True)
        return saved

    def _invalidate_azure_voice_catalog(self, *, hd_only: bool) -> None:
        engine = self.azure_hd_tts if hd_only else self.azure_tts
        invalidate = getattr(engine, "invalidate_voice_catalog", None)
        if invalidate is not None:
            invalidate()

    def _persist_secret_input(
        self,
        key_input: QLineEdit,
        secret_store: SecretStorePort | None,
        policy: SecretInputPolicy,
        *,
        silent: bool,
    ) -> bool:
        secret = key_input.text().strip()
        if not secret or secret_store is None:
            return False
        try:
            secret_store.save(secret)
        except OSError as exc:
            if not silent:
                QMessageBox.warning(
                    self,
                    self._t(policy.title_key, policy.title_fallback),
                    self._t(
                        policy.error_key,
                        policy.error_fallback,
                        error=safe_error_message(self.ui_language, exc),
                    ),
                )
            return False
        key_input.clear()
        key_input.setPlaceholderText(self._t(policy.saved_key, policy.saved_fallback))
        return True

    def set_realtime_status(self, status: str, active: bool | None = None) -> None:
        self.realtime_status.setText(
            self._t(
                "realtime_status_format",
                "Realtime：{status}",
                status=status,
            )
        )
        if active is not None:
            self.realtime_btn.blockSignals(True)
            self.realtime_btn.setChecked(active)
            self.realtime_btn.setText(
                self._t("stop_realtime", "停止 Realtime 自然對話")
                if active
                else self._t(
                    "start_realtime",
                    "啟動 Realtime 自然對話",
                )
            )
            self.realtime_btn.blockSignals(False)
