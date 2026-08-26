from __future__ import annotations

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTextEdit,
    QWidget,
)

lazy from application.presentation_ports import (
    DEFAULT_TRANSCRIPTION_MODEL,
    REALTIME_OUTPUT_AZURE,
    REALTIME_OUTPUT_AZURE_HD,
    REALTIME_OUTPUT_OPENAI,
    PlatformCapabilities,
    azure_female_voices,
    azure_hd_female_voices,
    azure_region_identifiers,
    azure_region_options,
    azure_region_supports_hd_flash,
)
lazy from domain.app_profile import profile_setting
lazy from domain.language_support import localized_transcription_prompt
lazy from domain.speech_configuration import (
    REALTIME_VOICES,
    TTS_VOICES,
    VOICE_ENGINE_AZURE,
    VOICE_ENGINE_AZURE_HD,
    VOICE_ENGINE_OPENAI,
    VOICE_ENGINE_REALTIME,
    VOICE_ENGINE_SYSTEM,
    VOICE_GENERATION_PROMPT,
    migrate_voice_defaults,
)
lazy from domain.speech_providers import migrate_speech_provider_setting
lazy from presentation.dashboard_voice_catalog import DashboardVoiceCatalogMethods
lazy from presentation.dashboard_voice_runtime import DashboardVoiceRuntimeMethods

__all__ = ("DashboardVoiceMixin",)


class DashboardVoiceMixin:
    """Voice, transcription, Azure, and Realtime dashboard settings."""

    _available_windows_voices = DashboardVoiceCatalogMethods._available_windows_voices
    _preferred_windows_voice = DashboardVoiceCatalogMethods._preferred_windows_voice
    _windows_voice_label = staticmethod(
        DashboardVoiceCatalogMethods._windows_voice_label
    )
    _persist_windows_voice_migration = (
        DashboardVoiceRuntimeMethods._persist_windows_voice_migration
    )
    _preview_voice = DashboardVoiceRuntimeMethods._preview_voice
    _voice_engine_changed = DashboardVoiceRuntimeMethods._voice_engine_changed
    _windows_voice_changed = DashboardVoiceRuntimeMethods._windows_voice_changed
    _voice_rate_changed = DashboardVoiceRuntimeMethods._voice_rate_changed
    _openai_voice_changed = DashboardVoiceRuntimeMethods._openai_voice_changed
    _azure_voice_changed = DashboardVoiceRuntimeMethods._azure_voice_changed
    _azure_region_changed = DashboardVoiceRuntimeMethods._azure_region_changed
    _azure_hd_voice_changed = DashboardVoiceRuntimeMethods._azure_hd_voice_changed
    _azure_hd_region_changed = DashboardVoiceRuntimeMethods._azure_hd_region_changed
    _request_azure_voice_catalog = (
        DashboardVoiceRuntimeMethods._request_azure_voice_catalog
    )
    _apply_azure_voice_catalog = DashboardVoiceRuntimeMethods._apply_azure_voice_catalog
    _refresh_azure_hd_voice_options = (
        DashboardVoiceRuntimeMethods._refresh_azure_hd_voice_options
    )
    _realtime_voice_changed = DashboardVoiceRuntimeMethods._realtime_voice_changed
    _realtime_output_mode_index_changed = (
        DashboardVoiceRuntimeMethods._realtime_output_mode_index_changed
    )
    clear_azure_speech_key = DashboardVoiceRuntimeMethods.clear_azure_speech_key
    clear_azure_hd_speech_key = DashboardVoiceRuntimeMethods.clear_azure_hd_speech_key
    _update_voice_volume_label = DashboardVoiceRuntimeMethods._update_voice_volume_label
    _voice_volume_changed = DashboardVoiceRuntimeMethods._voice_volume_changed
    save_voice_settings = DashboardVoiceRuntimeMethods.save_voice_settings
    _save_azure_key_immediately = (
        DashboardVoiceRuntimeMethods._save_azure_key_immediately
    )
    _save_azure_hd_key_immediately = (
        DashboardVoiceRuntimeMethods._save_azure_hd_key_immediately
    )
    _persist_azure_key = DashboardVoiceRuntimeMethods._persist_azure_key
    _persist_azure_hd_key = DashboardVoiceRuntimeMethods._persist_azure_hd_key
    _invalidate_azure_voice_catalog = (
        DashboardVoiceRuntimeMethods._invalidate_azure_voice_catalog
    )
    _persist_secret_input = DashboardVoiceRuntimeMethods._persist_secret_input
    set_realtime_status = DashboardVoiceRuntimeMethods.set_realtime_status

    def _initialize_transcription_controls(
        self,
        capabilities: PlatformCapabilities,
    ) -> None:
        self.speech_recognition = self._speech_recognition_combo(capabilities)
        self.transcription_model = self._editable_combo(
            ("gpt-4o-mini-transcribe", "gpt-4o-transcribe"),
            str(
                self.db.setting(
                    "transcription_model",
                    DEFAULT_TRANSCRIPTION_MODEL,
                )
            ),
        )
        self.transcription_language = self._transcription_language_input()
        self.transcription_prompt = self._transcription_prompt_input()
        self.windows_transcription_fallback = self._transcription_fallback_checkbox(
            capabilities
        )
        self.transcription_diagnostic = self._transcription_diagnostic_label()

    def _speech_recognition_combo(
        self,
        capabilities: PlatformCapabilities,
    ) -> QComboBox:
        combo = QComboBox()
        combo.addItem(
            self._t(
                "openai_recognition",
                "OpenAI 高準確辨識（推薦）",
            ),
            "OpenAI 高準確辨識（推薦）",
        )
        if capabilities.offline_speech_recognition:
            combo.addItem(
                self._t("windows_recognition", "Windows 離線辨識"),
                "Windows 離線辨識",
            )
        self._select_combo_data(
            combo,
            str(
                self.db.setting(
                    "speech_recognition",
                    "OpenAI 高準確辨識（推薦）",
                )
            ),
        )
        return combo

    def _transcription_language_input(self) -> QLineEdit:
        language = QLineEdit(str(self.db.setting("transcription_language", "zh")))
        language.setPlaceholderText(
            self._t(
                "transcription_language_placeholder",
                "ISO 語言代碼；留空可讓模型自動判斷",
            )
        )
        return language

    def _transcription_prompt_input(self) -> QTextEdit:
        prompt = QTextEdit()
        default_prompt = localized_transcription_prompt(
            self.ui_language,
            assistant_name=self.assistant_name,
            user_title=self.user_title,
            organization_name=self.organization_name,
            wake_word=profile_setting(self.db, "wake_word"),
        )
        prompt.setPlainText(
            str(self.db.setting("transcription_prompt", default_prompt))
        )
        prompt.setMaximumHeight(100)
        return prompt

    def _transcription_fallback_checkbox(
        self,
        capabilities: PlatformCapabilities,
    ) -> QCheckBox:
        fallback = QCheckBox(
            self._t(
                "openai_fallback",
                "OpenAI 失敗時使用 Windows 離線辨識",
            )
        )
        available = capabilities.offline_speech_recognition
        fallback.setChecked(
            bool(
                available
                and self.db.setting(
                    "windows_transcription_fallback",
                    True,
                )
            )
        )
        if available:
            return fallback
        fallback.setText(
            self._t(
                "platform_offline_fallback_unavailable",
                f"{capabilities.display_name} 離線辨識尚未完成實機驗證",
                platform=capabilities.display_name,
            )
        )
        fallback.setEnabled(False)
        return fallback

    def _transcription_diagnostic_label(self) -> QLabel:
        diagnostic = QLabel(
            str(
                self.db.setting(
                    "last_transcription_diagnostic",
                    self._t(
                        "no_transcription_error",
                        "尚無轉錄錯誤紀錄",
                    ),
                )
            )
        )
        diagnostic.setWordWrap(True)
        diagnostic.setStyleSheet("color:#2f6987; padding:6px;")
        return diagnostic

    def _initialize_voice_provider_controls(
        self,
        capabilities: PlatformCapabilities,
    ) -> None:
        self.voice_engine = self._voice_engine_combo(capabilities)
        self.windows_voice = self._windows_voice_combo(capabilities)
        migrate_voice_defaults(self.db)
        self.tts_voice = self._editable_combo(
            TTS_VOICES,
            str(
                self.db.setting(
                    "tts_voice",
                    self.db.setting("cloud_voice", "coral"),
                )
            ),
        )
        self.realtime_voice = self._editable_combo(
            REALTIME_VOICES,
            str(self.db.setting("realtime_voice", "coral")),
        )
        self._initialize_azure_voice_controls(capabilities)
        self.cloud_voice = self.tts_voice

    def _voice_engine_combo(
        self,
        capabilities: PlatformCapabilities,
    ) -> QComboBox:
        combo = QComboBox()
        if capabilities.system_local_speech:
            combo.addItem(
                self._t("windows_engine", "Windows 本機語音"),
                VOICE_ENGINE_SYSTEM,
            )
        cloud_engines = (
            (
                VOICE_ENGINE_OPENAI,
                self._t("openai_engine", "OpenAI 自然語音"),
            ),
            (
                VOICE_ENGINE_REALTIME,
                self._t("realtime_engine", "Realtime 即時語音"),
            ),
            (
                VOICE_ENGINE_AZURE,
                self._t("azure_engine", "Azure Speech（預覽）"),
            ),
            (
                VOICE_ENGINE_AZURE_HD,
                self._t(
                    "azure_hd_engine",
                    "Azure Dragon HD（預覽，需 S0）",
                ),
            ),
        )
        for key, label in cloud_engines:
            combo.addItem(label, key)
        self._select_combo_data(
            combo,
            migrate_speech_provider_setting(self.db),
        )
        return combo

    def _windows_voice_combo(
        self,
        capabilities: PlatformCapabilities,
    ) -> QComboBox:
        combo = QComboBox()
        available = self._available_windows_voices(capabilities)
        if not available:
            combo.addItem(
                self._unavailable_windows_voice_label(capabilities),
                "",
            )
            combo.model().item(0).setEnabled(False)
        if not capabilities.system_local_speech:
            combo.setEnabled(False)
        saved_voice = str(self.db.setting("windows_voice", ""))
        preferred, force_default = self._preferred_windows_voice(
            available,
            saved_voice,
        )
        for name, culture in sorted(
            available,
            key=lambda voice: (
                voice[0] != preferred,
                voice[1].lower(),
                voice[0].lower(),
            ),
        ):
            combo.addItem(
                self._windows_voice_label(name, culture),
                name,
            )
        self._persist_windows_voice_migration(
            preferred,
            saved_voice,
            force_default,
        )
        preferred_index = combo.findData(preferred)
        if preferred_index >= 0:
            combo.setCurrentIndex(preferred_index)
        return combo

    def _unavailable_windows_voice_label(
        self,
        capabilities: PlatformCapabilities,
    ) -> str:
        if capabilities.system_local_speech:
            return self._t(
                "no_female_voice",
                "未偵測到已確認的女性 Windows 聲音",
            )
        return self._t(
            "platform_local_voice_unavailable",
            f"{capabilities.display_name} 本機語音尚未完成實機驗證",
            platform=capabilities.display_name,
        )

    def _initialize_azure_voice_controls(
        self,
        capabilities: PlatformCapabilities,
    ) -> None:
        azure_voices = azure_female_voices(self.ui_language)
        saved_voice = str(self.db.setting("azure_speech_voice", azure_voices[0]))
        selected_voice = saved_voice if saved_voice in azure_voices else azure_voices[0]
        self.azure_voice = self._editable_combo(
            azure_voices,
            selected_voice,
        )
        self.azure_voice.setEditable(False)
        self.azure_region = self._azure_region_combo(
            setting_key="azure_speech_region",
        )
        self._initialize_azure_key_controls(capabilities)

        saved_hd_region = (
            str(self.db.setting("azure_hd_speech_region", "")).strip().lower()
        )
        azure_hd_voices = azure_hd_female_voices(
            self.ui_language,
            include_flash=azure_region_supports_hd_flash(saved_hd_region),
        )
        saved_hd_voice = str(
            self.db.setting("azure_hd_speech_voice", azure_hd_voices[0])
        )
        selected_hd_voice = (
            saved_hd_voice if saved_hd_voice in azure_hd_voices else azure_hd_voices[0]
        )
        if selected_hd_voice != saved_hd_voice:
            self.db.set_setting(
                "azure_hd_speech_voice",
                selected_hd_voice,
            )
        self.azure_hd_voice = self._editable_combo(
            azure_hd_voices,
            selected_hd_voice,
        )
        self.azure_hd_voice.setEditable(False)
        self.azure_hd_region = self._azure_region_combo(
            setting_key="azure_hd_speech_region",
            hd_only=True,
        )
        self._initialize_azure_hd_key_controls(capabilities)

    def _azure_region_combo(
        self,
        *,
        setting_key: str,
        hd_only: bool = False,
        hd_flash_only: bool = False,
    ) -> QComboBox:
        combo = QComboBox()
        combo.addItem(
            self._t(
                "azure_region_choose",
                "請選擇 Azure 資源建立時所在的區域",
            ),
            "",
        )
        for label, identifier in azure_region_options(
            self.ui_language,
            hd_only=hd_only,
            hd_flash_only=hd_flash_only,
        ):
            combo.addItem(label, identifier)

        saved_region = str(self.db.setting(setting_key, "")).strip().lower()
        known_regions = azure_region_identifiers()
        if (
            saved_region
            and saved_region not in known_regions
            and combo.findData(saved_region) < 0
        ):
            combo.addItem(
                self._t(
                    "azure_region_saved",
                    "既有設定 · {region}",
                    region=saved_region,
                ),
                saved_region,
            )
        self._select_combo_data(combo, saved_region)
        return combo

    def _initialize_azure_hd_key_controls(
        self,
        capabilities: PlatformCapabilities,
    ) -> None:
        self.azure_hd_key_input = QLineEdit()
        self.azure_hd_key_input.setEchoMode(QLineEdit.Password)
        self.azure_hd_key_input.setAccessibleName(
            self._t("azure_hd_key", "Dragon HD S0 金鑰")
        )
        self.azure_hd_key_input.setToolTip(
            self._t(
                "secret_auto_save_hint",
                "輸入後按 Enter 或移開游標，即會自動安全保存。",
            )
        )
        secure_storage = capabilities.secure_secret_storage
        key_saved = bool(
            secure_storage
            and self.azure_hd_secret_store
            and self.azure_hd_secret_store.load()
        )
        if secure_storage:
            placeholder = self._t(
                "azure_hd_key_saved" if key_saved else "azure_hd_key_missing",
                (
                    "Dragon HD S0 金鑰已由 Windows 加密保存（留空不變）"
                    if key_saved
                    else "貼上獨立的 Dragon HD S0 資源金鑰"
                ),
            )
        else:
            placeholder = self._t(
                "platform_secret_storage_unavailable",
                f"{capabilities.display_name} 安全金鑰保存尚未完成實機驗證",
                platform=capabilities.display_name,
            )
            self.azure_hd_key_input.setEnabled(False)
        self.azure_hd_key_input.setPlaceholderText(placeholder)
        self.azure_hd_key_input.editingFinished.connect(
            self._save_azure_hd_key_immediately
        )
        self.azure_hd_clear_key = QPushButton(
            self._t("azure_hd_remove_key", "移除 Dragon HD S0 金鑰")
        )
        self.azure_hd_clear_key.clicked.connect(self.clear_azure_hd_speech_key)
        self.azure_hd_clear_key.setEnabled(secure_storage)

    def _initialize_azure_key_controls(
        self,
        capabilities: PlatformCapabilities,
    ) -> None:
        self.azure_key_input = QLineEdit()
        self.azure_key_input.setEchoMode(QLineEdit.Password)
        self.azure_key_input.setAccessibleName(
            self._t("azure_key", "Azure Speech 金鑰")
        )
        self.azure_key_input.setToolTip(
            self._t(
                "secret_auto_save_hint",
                "輸入後按 Enter 或移開游標，即會自動安全保存。",
            )
        )
        secure_storage = capabilities.secure_secret_storage
        key_saved = bool(
            secure_storage
            and self.azure_secret_store
            and self.azure_secret_store.load()
        )
        if secure_storage:
            placeholder = (
                self._t(
                    "azure_key_saved",
                    "已由 Windows 加密保存（留空不變）",
                )
                if key_saved
                else self._t(
                    "azure_key_missing",
                    "貼上 Azure Speech 資源金鑰",
                )
            )
        else:
            placeholder = self._t(
                "platform_secret_storage_unavailable",
                f"{capabilities.display_name} 安全金鑰保存尚未完成實機驗證",
                platform=capabilities.display_name,
            )
            self.azure_key_input.setEnabled(False)
        self.azure_key_input.setPlaceholderText(placeholder)
        self.azure_key_input.editingFinished.connect(self._save_azure_key_immediately)
        self.azure_clear_key = QPushButton(
            self._t("azure_remove_key", "移除 Azure Speech 金鑰")
        )
        self.azure_clear_key.clicked.connect(self.clear_azure_speech_key)
        self.azure_clear_key.setEnabled(secure_storage)

    def _initialize_realtime_controls(self) -> None:
        self.realtime_output_mode = self._realtime_output_mode_combo()
        self.realtime_output_mode_note = self._voice_note("")
        self._apply_realtime_output_mode_state(
            str(self.realtime_output_mode.currentData() or REALTIME_OUTPUT_OPENAI)
        )
        self.realtime_model = self._editable_combo(
            ("gpt-realtime-2.1-mini", "gpt-realtime-2.1"),
            str(
                self.db.setting(
                    "realtime_model",
                    "gpt-realtime-2.1-mini",
                )
            ),
        )
        self.realtime_transcription_model = self._editable_combo(
            ("gpt-4o-mini-transcribe", "gpt-4o-transcribe"),
            str(
                self.db.setting(
                    "realtime_transcription_model",
                    "gpt-4o-mini-transcribe",
                )
            ),
        )
        self.realtime_noise_reduction = self._realtime_noise_reduction_combo()
        self.realtime_turn_detection = self._realtime_turn_detection_combo()
        self.realtime_echo_guard = self._realtime_echo_guard_checkbox()
        self.realtime_hybrid_transcription = (
            self._realtime_hybrid_transcription_checkbox()
        )

    def _realtime_output_mode_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem(
            self._t(
                "realtime_output_openai",
                "OpenAI Realtime 原生語音（最低延遲，既有預設）",
            ),
            REALTIME_OUTPUT_OPENAI,
        )
        combo.addItem(
            self._t(
                "realtime_output_azure",
                "Azure Speech 女性聲線（柔和串流）",
            ),
            REALTIME_OUTPUT_AZURE,
        )
        combo.addItem(
            self._t(
                "realtime_output_azure_hd",
                "Azure Dragon HD 女性聲線（需 S0）",
            ),
            REALTIME_OUTPUT_AZURE_HD,
        )
        self._select_combo_data(
            combo,
            str(
                self.db.setting(
                    "realtime_output_mode",
                    REALTIME_OUTPUT_OPENAI,
                )
            ),
        )
        return combo

    def _apply_realtime_output_mode_state(self, mode: str) -> None:
        # The selected output route decides which provider speaks; it must not
        # prevent the user from preselecting the native Realtime voice that
        # will be used after switching back to OpenAI output.
        self.realtime_voice.setEnabled(True)
        if mode == REALTIME_OUTPUT_AZURE:
            note = self._t(
                "realtime_output_note_azure",
                "沿用上方「Azure Speech 女性聲線」、區域與金鑰。"
                "OpenAI Realtime 負責即時理解，Azure 以串流方式發聲。",
            )
        elif mode == REALTIME_OUTPUT_AZURE_HD:
            note = self._t(
                "realtime_output_note_azure_hd",
                "沿用上方「Dragon HD 女性聲線」、S0 區域與獨立金鑰。"
                "OpenAI Realtime 負責即時理解，Dragon HD 以串流方式發聲。",
            )
        else:
            note = self._t(
                "realtime_output_note_openai",
                "使用下方「OpenAI Realtime 原生聲線」；延遲最低，"
                "完整保留 OpenAI Realtime 的原生即時語音輸出。",
            )
        self.realtime_output_mode_note.setText(note)
        self.realtime_output_mode.setToolTip(note)
        self.realtime_voice.setToolTip(note)

    def _realtime_noise_reduction_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem(
            self._t("near_field", "近距離麥克風（推薦）"),
            "near_field",
        )
        combo.addItem(
            self._t("far_field", "遠距離／筆電麥克風"),
            "far_field",
        )
        combo.addItem(
            self._t("noise_off", "關閉降噪"),
            "off",
        )
        self._select_combo_data(
            combo,
            str(
                self.db.setting(
                    "realtime_noise_reduction",
                    "near_field",
                )
            ),
        )
        return combo

    def _realtime_turn_detection_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem(
            self._t(
                "stable_vad",
                "穩定完整（推薦，停頓約 0.85 秒）",
            ),
            "server_vad",
        )
        combo.addItem(
            self._t(
                "semantic_vad",
                "自然語意（可能提早切段）",
            ),
            "semantic_vad",
        )
        self._select_combo_data(
            combo,
            str(
                self.db.setting(
                    "realtime_turn_detection",
                    "server_vad",
                )
            ),
        )
        return combo

    def _realtime_echo_guard_checkbox(self) -> QCheckBox:
        checkbox = QCheckBox(
            self._t(
                "echo_guard_option",
                "防止墨寒把自己的聲音誤認成主上（推薦）",
            )
        )
        checkbox.setChecked(bool(self.db.setting("realtime_echo_guard", True)))
        checkbox.setToolTip(
            self._t(
                "echo_guard_tooltip",
                "墨寒說話時暫停上傳麥克風，播放結束後再恢復；"
                "啟用時無法在她說話途中插話。",
            )
        )
        return checkbox

    def _realtime_hybrid_transcription_checkbox(self) -> QCheckBox:
        checkbox = QCheckBox(
            self._t(
                "hybrid_transcript",
                "畫面採用高精度整句轉錄（推薦）",
            )
        )
        checkbox.setChecked(
            bool(
                self.db.setting(
                    "realtime_hybrid_transcription",
                    True,
                )
            )
        )
        checkbox.setToolTip(
            self._t(
                "hybrid_transcript_tooltip",
                "Realtime 保留原生音訊理解；每句說完後，畫面文字改用"
                "完整錄音的 OpenAI 高精度轉錄。成功後才允許墨寒回答。",
            )
        )
        return checkbox

    def _initialize_voice_rate_control(self) -> QWidget:
        self.voice_rate = QSpinBox()
        self.voice_rate.setRange(-5, 5)
        self.voice_rate.setValue(int(self.db.setting("voice_rate", -1)))
        self.voice_rate.setSuffix(self._t("level_suffix", " 級"))
        self.voice_rate.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.voice_rate.lineEdit().setReadOnly(True)
        self.voice_rate.setAlignment(Qt.AlignCenter)
        control = QWidget()
        layout = QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.voice_rate_down = QPushButton("－")
        self.voice_rate_down.setToolTip(self._t("rate_down", "降低本機朗讀速度"))
        self.voice_rate_down.setFixedWidth(48)
        self.voice_rate_up = QPushButton("＋")
        self.voice_rate_up.setToolTip(self._t("rate_up", "提高本機朗讀速度"))
        self.voice_rate_up.setFixedWidth(48)
        self.voice_rate_down.clicked.connect(self.voice_rate.stepDown)
        self.voice_rate_up.clicked.connect(self.voice_rate.stepUp)
        self.voice_rate.valueChanged.connect(self._voice_rate_changed)
        layout.addWidget(self.voice_rate_down)
        layout.addWidget(self.voice_rate, 1)
        layout.addWidget(self.voice_rate_up)
        return control

    def _initialize_voice_volume_control(self) -> QWidget:
        self.voice_volume = QSlider(Qt.Horizontal)
        self.voice_volume.setRange(0, 160)
        self.voice_volume.setSingleStep(5)
        self.voice_volume.setPageStep(10)
        self.voice_volume.setValue(int(self.db.setting("voice_volume_percent", 125)))
        self.voice_volume_label = QLabel()
        self.voice_volume_label.setMinimumWidth(52)
        self.voice_volume_label.setAlignment(Qt.AlignCenter)
        self.voice_muted = QCheckBox(self._t("mute", "靜音"))
        self.voice_muted.setChecked(bool(self.db.setting("voice_muted", False)))
        control = QWidget()
        layout = QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.voice_volume, 1)
        layout.addWidget(self.voice_volume_label)
        layout.addWidget(self.voice_muted)
        self.voice_volume.valueChanged.connect(self._voice_volume_changed)
        self.voice_muted.toggled.connect(self._voice_volume_changed)
        self._update_voice_volume_label()
        return control

    def _initialize_voice_action_controls(self) -> None:
        self.voice_instructions = QLineEdit(
            str(
                self.db.setting(
                    "voice_instructions",
                    VOICE_GENERATION_PROMPT,
                )
            )
        )
        self.voice_preview_button = QPushButton(
            self._t("preview_voice", "試聽：主上，妾在。")
        )
        self.voice_preview_button.clicked.connect(self._preview_voice)
        self.realtime_status = QLabel(
            self._t("realtime_disconnected", "Realtime：未連線")
        )
        self.realtime_btn = QPushButton(
            self._t("start_realtime", "啟動 Realtime 自然對話")
        )
        self.realtime_btn.setCheckable(True)
        self.realtime_btn.toggled.connect(self.realtime_toggle_requested.emit)

    @staticmethod
    def _voice_note(text: str) -> QLabel:
        note = QLabel(text)
        note.setWordWrap(True)
        return note

    def _recognition_note(
        self,
        capabilities: PlatformCapabilities,
    ) -> QLabel:
        if capabilities.offline_speech_recognition:
            text = self._t(
                "recognition_note",
                "單次麥克風預設使用 gpt-4o-mini-transcribe 與墨寒專用繁中詞庫；"
                "停止說話約 0.85 秒即送出，最長 10 秒；收音時再次點擊"
                "麥克風可立即送出。Windows 備援可自行關閉。",
            )
        else:
            text = self._t(
                "recognition_note_no_offline",
                "單次麥克風使用 OpenAI 高準確辨識；此平台的離線辨識尚未"
                "完成實機驗證，因此不會顯示或假裝提供離線備援。",
            )
        return self._voice_note(text)

    def _windows_voice_note(
        self,
        capabilities: PlatformCapabilities,
    ) -> QLabel:
        if capabilities.system_local_speech:
            text = self._t(
                "female_voice_note",
                "離線聲音僅列出 Windows 已明確標示為女性的聲音；"
                "台灣繁中仍優先使用 Yating（zh-TW）。",
            )
        else:
            text = self._t(
                "platform_local_voice_note",
                f"{capabilities.display_name} 本機語音尚未完成實機驗證；"
                "未支援前不會顯示其他平台的聲音或宣稱有離線朗讀。",
                platform=capabilities.display_name,
            )
        return self._voice_note(text)

    def _azure_voice_note(
        self,
        capabilities: PlatformCapabilities,
    ) -> QLabel:
        if capabilities.system_local_speech:
            text = self._t(
                "azure_speech_note",
                "預覽功能；需自備 Azure Speech 資源金鑰與相符區域。"
                "只列官方標示為女性的繁中、簡中或英文聲線；失敗時"
                "立即回到 Windows 本機女聲。F0 免費額度及計費以"
                " Microsoft 當期規則為準。",
            )
        else:
            text = self._t(
                "azure_speech_note_no_local_fallback",
                "預覽功能；需自備 Azure Speech 資源金鑰與相符區域。"
                "此平台尚無已驗證的本機語音，服務失敗時會安全停止播放，"
                "不會假裝已切換到離線聲音。",
            )
        return self._voice_note(text)

    def _azure_hd_voice_note(self) -> QLabel:
        return self._voice_note(
            self._t(
                "azure_hd_speech_note",
                "可選預覽功能；請使用獨立的 S0 語音資源、金鑰與相符區域。"
                "Dragon HD 不提供 viseme，因此墨寒會使用既有音訊分析維持"
                "嘴型同步。發話前等待時間取決於網路與區域距離。若 HD 失敗，"
                "依序退回一般 Azure，再退回 Windows "
                "本機語音；每一層只嘗試一次，避免重複計費。",
            )
        )

    def _model_access_note(self) -> QLabel:
        return self._voice_note(
            self._t(
                "model_access_note",
                "若後台已勾選模型但仍顯示無權限，請確認勾選模型與建立 API Key "
                "的是同一個 Project；在該 Project 重新建立金鑰後，到「設定」"
                "頁重新儲存。",
            )
        )

    def _echo_guard_note(self) -> QLabel:
        return self._voice_note(
            self._t(
                "echo_guard_note",
                "防回音開啟時，墨寒說話期間會停止上傳麥克風，並清除本機"
                "與伺服器端殘留音訊；結束約一秒後才恢復。對話頁只顯示"
                "高精度整句轉錄的最終結果，不顯示辨識中的暫定文字。",
            )
        )

    def _realtime_note(self) -> QLabel:
        return self._voice_note(
            self._t(
                "realtime_note",
                "Realtime 會持續使用麥克風。預設以穩定切段保留句首 500 毫秒，"
                "停止約 0.85 秒後才判定說完。高精度整句轉錄開啟時，"
                "Realtime 原生模型負責理解聲音，螢幕文字則使用與單次"
                "麥克風相同的 gpt-4o-mini-transcribe 與繁中詞庫；"
                "不會同時收取 Realtime 內建字幕的第二筆轉錄費。"
                "啟動時才會傳送聲音；關閉後立即停止。"
                "mini 較省費用並已設為預設；完整版適合品質優先時使用。",
            )
        )

    def _add_transcription_rows(
        self,
        form: QFormLayout,
        capabilities: PlatformCapabilities,
    ) -> None:
        form.addRow(
            self._t("speech_recognition", "單次麥克風辨識"),
            self.speech_recognition,
        )
        form.addRow(
            self._t("transcription_model", "轉錄模型"),
            self.transcription_model,
        )
        form.addRow(
            self._t("transcription_language", "轉錄語言"),
            self.transcription_language,
        )
        form.addRow(
            self._t("transcription_prompt", "轉錄提示／常用詞"),
            self.transcription_prompt,
        )
        fallback_label = (
            self._t(
                "windows_transcription_fallback",
                "Windows 備援",
            )
            if capabilities.offline_speech_recognition
            else self._t("offline_fallback", "離線備援")
        )
        form.addRow(fallback_label, self.windows_transcription_fallback)
        form.addRow(
            self._t("last_transcription", "最近一次轉錄"),
            self.transcription_diagnostic,
        )
        form.addRow("", self._recognition_note(capabilities))

    def _add_voice_provider_rows(
        self,
        form: QFormLayout,
        capabilities: PlatformCapabilities,
    ) -> None:
        form.addRow(
            self._t("voice_engine", "朗讀方式"),
            self.voice_engine,
        )
        voice_label = (
            self._t("windows_voice", "Windows 聲音")
            if capabilities.system_local_speech
            else self._t(
                "platform_local_voice",
                f"{capabilities.display_name} 本機聲音",
                platform=capabilities.display_name,
            )
        )
        form.addRow(voice_label, self.windows_voice)
        form.addRow("", self._windows_voice_note(capabilities))
        form.addRow(
            self._t("tts_voice", "OpenAI 文字朗讀聲音"),
            self.tts_voice,
        )
        form.addRow(
            self._t("azure_voice", "Azure Speech 女性聲線"),
            self.azure_voice,
        )
        form.addRow(
            self._t("azure_region", "Azure Speech 區域"),
            self.azure_region,
        )
        form.addRow(
            self._t("azure_key", "Azure Speech 金鑰"),
            self.azure_key_input,
        )
        form.addRow("", self.azure_clear_key)
        form.addRow("", self._azure_voice_note(capabilities))
        form.addRow(
            self._t("azure_hd_voice", "Dragon HD 女性聲線"),
            self.azure_hd_voice,
        )
        form.addRow(
            self._t("azure_hd_region", "Dragon HD S0 區域"),
            self.azure_hd_region,
        )
        form.addRow(
            self._t("azure_hd_key", "Dragon HD S0 金鑰"),
            self.azure_hd_key_input,
        )
        form.addRow("", self.azure_hd_clear_key)
        form.addRow("", self._azure_hd_voice_note())

    def _add_realtime_rows(self, form: QFormLayout) -> None:
        form.addRow(
            self._t(
                "realtime_output_source",
                "Realtime 回覆聲音來源",
            ),
            self.realtime_output_mode,
        )
        form.addRow("", self.realtime_output_mode_note)
        form.addRow(
            self._t("realtime_voice", "OpenAI Realtime 原生聲線"),
            self.realtime_voice,
        )
        form.addRow(
            self._t("realtime_model", "Realtime 模型"),
            self.realtime_model,
        )
        form.addRow(
            self._t(
                "realtime_transcription_model",
                "Realtime 轉錄模型",
            ),
            self.realtime_transcription_model,
        )
        form.addRow(
            self._t("realtime_noise", "Realtime 麥克風降噪"),
            self.realtime_noise_reduction,
        )
        form.addRow(
            self._t("realtime_turn", "Realtime 發言切段"),
            self.realtime_turn_detection,
        )
        form.addRow(
            self._t(
                "realtime_screen_transcript",
                "Realtime 畫面轉錄",
            ),
            self.realtime_hybrid_transcription,
        )
        form.addRow("", self._model_access_note())
        form.addRow(
            self._t("echo_guard", "防回音"),
            self.realtime_echo_guard,
        )
        form.addRow("", self._echo_guard_note())

    def _add_voice_output_rows(
        self,
        form: QFormLayout,
        rate_control: QWidget,
        volume_control: QWidget,
    ) -> None:
        form.addRow(
            self._t("local_rate", "本機語速"),
            rate_control,
        )
        form.addRow(
            self._t("mohan_volume", "墨寒專屬音量"),
            volume_control,
        )
        form.addRow(
            self._t("voice_style", "聲音風格"),
            self.voice_instructions,
        )
        form.addRow("", self.voice_preview_button)
        form.addRow(
            self._t("realtime", "即時語音"),
            self.realtime_status,
        )
        form.addRow("", self.realtime_btn)
        form.addRow("", self._realtime_note())

    def _voice_tab(self) -> QWidget:
        tab, form = self._form_scroll_page()
        capabilities = self.platform_services.capabilities
        self._initialize_transcription_controls(capabilities)
        self._initialize_voice_provider_controls(capabilities)
        self._initialize_realtime_controls()
        rate_control = self._initialize_voice_rate_control()
        volume_control = self._initialize_voice_volume_control()
        self._initialize_voice_action_controls()
        self._add_transcription_rows(form, capabilities)
        self._add_voice_provider_rows(form, capabilities)
        self._add_realtime_rows(form)
        self._add_voice_output_rows(
            form,
            rate_control,
            volume_control,
        )
        self.voice_engine.currentIndexChanged.connect(self._voice_engine_changed)
        self.windows_voice.currentIndexChanged.connect(self._windows_voice_changed)
        self.tts_voice.currentTextChanged.connect(self._openai_voice_changed)
        self.azure_voice.currentTextChanged.connect(self._azure_voice_changed)
        self.azure_region.currentIndexChanged.connect(self._azure_region_changed)
        self.azure_hd_voice.currentTextChanged.connect(self._azure_hd_voice_changed)
        self.azure_hd_region.currentIndexChanged.connect(self._azure_hd_region_changed)
        self.realtime_voice.currentTextChanged.connect(self._realtime_voice_changed)
        self.realtime_output_mode.currentIndexChanged.connect(
            self._realtime_output_mode_index_changed
        )
        return tab
