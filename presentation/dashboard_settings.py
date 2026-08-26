from __future__ import annotations

lazy import os
lazy import sqlite3
lazy from collections.abc import Iterable
lazy from datetime import time as clock_time
lazy from pathlib import Path

lazy from PySide6.QtCore import Qt, QTime
lazy from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

lazy from application.presentation_ports import (
    DEFAULT_TEXT_MODEL,
    TEXT_MODELS,
    PlatformCapabilities,
)
lazy from domain.app_profile import default_persona_for_language, profile_setting
lazy from domain.companion_animation_contract import (
    CHARACTER_SCALE_DEFAULT,
    CHARACTER_SCALE_MAX,
    CHARACTER_SCALE_MIN,
)
lazy from presentation.companion_platform import reminder_line
lazy from presentation.dashboard_composition import (
    DashboardDependencies,
    create_portable_secret_callbacks,
)
lazy from presentation.dashboard_settings_persistence import (
    DashboardSettingsPersistenceMixin,
)
lazy from presentation.first_run_wizard import FirstRunWizard
lazy from presentation.flagship.control_center import (
    ControlCenterDependencies,
    FlagshipControlCenter,
)
lazy from presentation.profile_transfer_ui import PortableProfilePanel
lazy from presentation.settings_ui_localization import (
    PHYSICS_TEXT_KEYS,
    PROACTIVE_MODE_KEYS,
    TOPMOST_MODE_KEYS,
    SettingsText,
)
lazy from presentation.theme_pack_ui import ThemePackPanel
lazy from presentation.ui_localization import (
    SIMPLIFIED_WORK_TYPE_LABELS,
    WORK_TYPE_LABELS,
    display_label,
)
lazy from presentation.ui_localization_ja import JAPANESE_WORK_TYPE_LABELS
lazy from presentation.updater_ui import UpdatePanel

__all__ = ("DashboardSettingsMixin",)


def _configure_form(form: QFormLayout) -> None:
    """Keep four-language labels aligned with their interactive fields."""

    form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    form.setFormAlignment(Qt.AlignTop)
    form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.WrapLongRows)


class DashboardSettingsMixin:
    """General settings, permissions, profile, and save transactions."""

    save_permissions = DashboardSettingsPersistenceMixin.save_permissions
    _permission_allowed = DashboardSettingsPersistenceMixin._permission_allowed
    _current_profile_localization = (
        DashboardSettingsPersistenceMixin._current_profile_localization
    )
    _validated_profile_settings = (
        DashboardSettingsPersistenceMixin._validated_profile_settings
    )
    _persist_profile_settings = (
        DashboardSettingsPersistenceMixin._persist_profile_settings
    )
    _migrate_localized_profile_defaults = (
        DashboardSettingsPersistenceMixin._migrate_localized_profile_defaults
    )
    _migrate_transcription_prompt = (
        DashboardSettingsPersistenceMixin._migrate_transcription_prompt
    )
    _migrate_transcription_language = (
        DashboardSettingsPersistenceMixin._migrate_transcription_language
    )
    _migrate_voice_instructions = (
        DashboardSettingsPersistenceMixin._migrate_voice_instructions
    )
    _migrate_persona_prompt = DashboardSettingsPersistenceMixin._migrate_persona_prompt
    _migrate_reminder_messages = (
        DashboardSettingsPersistenceMixin._migrate_reminder_messages
    )
    _apply_saved_profile = DashboardSettingsPersistenceMixin._apply_saved_profile
    _save_reminder_settings = DashboardSettingsPersistenceMixin._save_reminder_settings
    _save_general_settings = DashboardSettingsPersistenceMixin._save_general_settings
    _save_api_key_if_provided = (
        DashboardSettingsPersistenceMixin._save_api_key_if_provided
    )
    _save_autostart_setting = DashboardSettingsPersistenceMixin._save_autostart_setting
    _persist_external_settings = (
        DashboardSettingsPersistenceMixin._persist_external_settings
    )
    _finish_settings_save = DashboardSettingsPersistenceMixin._finish_settings_save
    save_settings = DashboardSettingsPersistenceMixin.save_settings
    clear_api_key = DashboardSettingsPersistenceMixin.clear_api_key

    @staticmethod
    def _form_scroll_page() -> tuple[QScrollArea, QFormLayout]:
        page = QScrollArea()
        page.setObjectName("formScrollPage")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page.viewport().setStyleSheet("background:transparent;")
        content = QWidget()
        content.setObjectName("formScrollContent")
        content.setStyleSheet("QWidget#formScrollContent{background:transparent;}")
        form = QFormLayout(content)
        _configure_form(form)
        page.setWidget(content)
        return page, form

    @staticmethod
    def _editable_combo(
        items: Iterable[str],
        current_text: str,
    ) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(list(items))
        combo.setCurrentText(current_text)
        # An editable combo's popup view does not always inherit the light
        # QComboBox QAbstractItemView palette, so pin it explicitly to keep the
        # dropdown readable on the light control-centre theme.
        combo.view().setStyleSheet(
            "QAbstractItemView { background: #ffffff; color: #20364a;"
            " selection-background-color: #cfe0ee; selection-color: #17344f; }"
        )
        return combo

    @staticmethod
    def _select_combo_data(combo: QComboBox, value: str) -> None:
        combo.setCurrentIndex(max(0, combo.findData(value)))

    def _permissions_tab(self) -> QWidget:
        tab = QScrollArea()
        tab.setObjectName("formScrollPage")
        tab.setWidgetResizable(True)
        tab.setFrameShape(QFrame.NoFrame)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tab.viewport().setStyleSheet("background:transparent;")
        content = QWidget()
        content.setObjectName("formScrollContent")
        content.setStyleSheet("QWidget#formScrollContent{background:transparent;}")
        form = QFormLayout(content)
        _configure_form(form)
        tab.setWidget(content)
        intro = QLabel(
            self._t(
                "permissions_intro",
                "每項能力分開授權。選擇「每次詢問」時，墨寒執行前會顯示確認視窗；"
                "刪除檔案預設禁止。",
            )
        )
        intro.setWordWrap(True)
        form.addRow(intro)
        stored = self.db.setting("tool_permissions", {})
        defaults = {
            "open_web": "每次詢問",
            "open_folder": "每次詢問",
            "launch_app": "每次詢問",
            "write_files": "每次詢問",
            "delete_files": "禁止",
        }
        labels = {
            "open_web": self._t("permission_open_web", "開啟指定網站"),
            "open_folder": self._t("permission_open_folder", "開啟工作室資料夾"),
            "launch_app": self._t("permission_launch_app", "啟動其他程式"),
            "write_files": self._t("permission_write_files", "建立或修改檔案"),
            "delete_files": self._t("permission_delete_files", "刪除檔案"),
        }
        self.permission_controls = {}
        for key, default in defaults.items():
            combo = QComboBox()
            combo.addItem(self._t("permission_deny", "禁止"), "禁止")
            combo.addItem(
                self._t("permission_ask", "每次詢問"),
                "每次詢問",
            )
            combo.addItem(self._t("permission_allow", "允許"), "允許")
            permission_index = combo.findData(str(stored.get(key, default)))
            combo.setCurrentIndex(max(0, permission_index))
            self.permission_controls[key] = combo
            form.addRow(labels[key], combo)
        warning = QLabel(
            self._t(
                "permissions_warning",
                "安全原則：墨寒不會因聊天內容自動取得更高權限；"
                "API 模型只能提出工具請求，真正執行仍由本機權限層決定。",
            )
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#8a5a13;")
        form.addRow(warning)
        self.flagship_center = FlagshipControlCenter(
            self.db,
            self.db.path.parent,
            self,
            dependencies=ControlCenterDependencies(
                platform_services=self.platform_services,
                secret_store_factory=self.secret_store_factory,
                cloud_vision_service_factory=self.cloud_vision_service_factory,
                dense_face_provider_factory=self.dense_face_provider_factory,
                gesture_controller=self.gesture_controller,
            ),
            language=self.ui_language,
        )
        self.flagship_center.setMinimumHeight(720)
        self.flagship_center.speak_requested.connect(self.speak_requested.emit)
        self.flagship_center.visual_observation_changed.connect(
            self.visual_observation_changed.emit
        )
        self.flagship_center.visual_scene_changed.connect(
            self.visual_scene_changed.emit
        )
        self.flagship_center.multimodal_result_changed.connect(
            self.multimodal_result_changed.emit
        )
        self.flagship_center.remote_command_received.connect(
            self._receive_remote_command
        )
        flagship_heading = QLabel(self._t("flagship_heading", "<b>旗艦控制中心</b>"))
        flagship_heading.setStyleSheet("color:#2f6987;font-size:16px;margin-top:12px;")
        form.addRow(flagship_heading)
        form.addRow(self.flagship_center)
        return tab

    def _step_control(
        self,
        editor: QAbstractSpinBox,
        object_prefix: str,
    ) -> tuple[QWidget, QPushButton, QPushButton]:
        """Use explicit buttons so Windows/QSS cannot steal the up hit area."""
        editor.setButtonSymbols(QAbstractSpinBox.NoButtons)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        up = QPushButton("▲")
        down = QPushButton("▼")
        up.setObjectName(f"{object_prefix}Up")
        down.setObjectName(f"{object_prefix}Down")
        up.setToolTip(self._t("increase", "增加"))
        down.setToolTip(self._t("decrease", "減少"))
        for button in (up, down):
            button.setFixedWidth(46)
            button.setAutoRepeat(True)
            button.setAutoRepeatDelay(420)
            button.setAutoRepeatInterval(110)
        up.clicked.connect(editor.stepUp)
        down.clicked.connect(editor.stepDown)
        layout.addWidget(editor, 1)
        layout.addWidget(up)
        layout.addWidget(down)
        return container, up, down

    def _add_profile_settings(
        self,
        form: QFormLayout,
        parent: QWidget,
    ) -> None:
        heading = QLabel(self._t("profile_heading", "<b>身份與使用者設定</b>"))
        heading.setStyleSheet("color:#2f6987;font-size:15px;")
        self.profile_assistant_name = QLineEdit(
            profile_setting(self.db, "assistant_name")
        )
        self.profile_user_title = QLineEdit(profile_setting(self.db, "user_title"))
        self.profile_organization_name = QLineEdit(
            profile_setting(self.db, "organization_name")
        )
        self.profile_window_title = QLineEdit(profile_setting(self.db, "window_title"))
        self.profile_window_title.setPlaceholderText(
            self._t(
                "window_title_placeholder",
                "留空時自動顯示「助理名稱．組織名稱」",
            )
        )
        self.profile_work_type = self._profile_work_type_combo()
        self.profile_ui_language = self._profile_language_combo()
        self.profile_wake_word = QLineEdit(profile_setting(self.db, "wake_word"))
        form.addRow(heading)
        profile_rows = (
            ("assistant_name", "助理名稱", self.profile_assistant_name),
            ("user_title", "助理對你的稱呼", self.profile_user_title),
            (
                "organization_name",
                "公司／團隊名稱",
                self.profile_organization_name,
            ),
            ("window_title", "完整視窗標題", self.profile_window_title),
            ("work_type", "工作類型", self.profile_work_type),
            ("ui_language", "介面語言", self.profile_ui_language),
            ("wake_word", "語音喚醒詞", self.profile_wake_word),
        )
        for key, fallback, editor in profile_rows:
            form.addRow(self._t(key, fallback), editor)
        self.portable_profile_panel = PortableProfilePanel(
            self.db,
            parent,
            before_export=lambda: self.save_settings(silent=True),
            language=self.ui_language,
            sensitive_callbacks=create_portable_secret_callbacks(
                DashboardDependencies(
                    listener=self.listener,
                    secret_store=self.secret_store,
                    azure_secret_store=self.azure_secret_store,
                    azure_hd_secret_store=self.azure_hd_secret_store,
                    secret_store_factory=self.secret_store_factory,
                    platform_services=self.platform_services,
                    cloud_vision_service_factory=(self.cloud_vision_service_factory),
                    presentation_ports=self.presentation_ports,
                ),
                self.db.path.parent,
            ),
            manager_factory=self.profile_manager_factory,
        )
        form.addRow(self.portable_profile_panel)

    def _profile_work_type_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        for value in FirstRunWizard.WORK_TYPES:
            combo.addItem(
                display_label(
                    self.ui_language,
                    value,
                    WORK_TYPE_LABELS,
                    SIMPLIFIED_WORK_TYPE_LABELS,
                    JAPANESE_WORK_TYPE_LABELS,
                ),
                value,
            )
        saved_work_type = profile_setting(self.db, "work_type")
        saved_index = combo.findData(saved_work_type)
        if saved_index >= 0:
            combo.setCurrentIndex(saved_index)
        else:
            combo.setCurrentText(saved_work_type)
        return combo

    def _profile_language_combo(self) -> QComboBox:
        combo = QComboBox()
        for label, language in (
            ("繁體中文（台灣）", "zh-TW"),
            ("简体中文（中国大陆）", "zh-CN"),
            ("English", "en"),
            ("日本語", "ja-JP"),
        ):
            combo.addItem(label, language)
        self._select_combo_data(
            combo,
            profile_setting(self.db, "ui_language"),
        )
        return combo

    def _add_reminder_settings(self, form: QFormLayout) -> None:
        self.reminder_controls: dict[
            str,
            tuple[QCheckBox, QTimeEdit],
        ] = {}
        self.reminder_step_buttons: dict[
            str,
            tuple[QPushButton, QPushButton],
        ] = {}
        self.reminder_message_controls: dict[str, QLineEdit] = {}
        labels = frozendict({
            "work": self._t("reminder_work", "工作開始"),
            "lunch": self._t("reminder_lunch", "午餐"),
            "dinner": self._t("reminder_dinner", "晚餐"),
            "offwork": self._t("reminder_offwork", "下班"),
        })
        for row in self.db.reminders():
            kind = str(row["kind"])
            self._add_reminder_row(form, row, labels[kind])

    def _add_reminder_row(
        self,
        form: QFormLayout,
        row: sqlite3.Row,
        label: str,
    ) -> None:
        kind = str(row["kind"])
        enabled = QCheckBox(self._t("enabled", "啟用"))
        enabled.setChecked(bool(row["enabled"]))
        reminder_time = QTimeEdit()
        reminder_time.setDisplayFormat("HH:mm")
        parsed_time = clock_time.fromisoformat(str(row["time_of_day"]))
        reminder_time.setTime(QTime(parsed_time.hour, parsed_time.minute))
        time_control, up_button, down_button = self._step_control(
            reminder_time,
            f"{kind}Time",
        )
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(enabled)
        row_layout.addWidget(time_control)
        row_layout.addStretch()
        form.addRow(label, row_widget)
        message = QLineEdit(
            str(
                self.db.setting(
                    f"reminder_message_{kind}",
                    reminder_line(self.ui_language, kind),
                )
            )
        )
        message.setPlaceholderText(
            self._t(
                "reminder_message_placeholder",
                "此提醒觸發時要說的內容",
            )
        )
        form.addRow(
            self._t(
                "reminder_message_label",
                "{label}訊息",
                label=label,
            ),
            message,
        )
        self.reminder_controls[kind] = (enabled, reminder_time)
        self.reminder_step_buttons[kind] = (up_button, down_button)
        self.reminder_message_controls[kind] = message

    def _add_work_rhythm_settings(self, form: QFormLayout) -> None:
        self.break_minutes = QSpinBox()
        self.break_minutes.setRange(30, 240)
        self.break_minutes.setSuffix(self._t("minutes_suffix", " 分鐘"))
        self.break_minutes.setValue(int(self.db.setting("break_minutes", 90)))
        self.overwork_message = QLineEdit(
            str(
                self.db.setting(
                    "reminder_message_overwork",
                    reminder_line(self.ui_language, "overwork"),
                )
            )
        )
        (
            self.break_minutes_control,
            self.break_minutes_up,
            self.break_minutes_down,
        ) = self._step_control(self.break_minutes, "breakMinutes")
        self.tts_enabled = QCheckBox(self._t("read_replies", "讓寒讀出回覆"))
        self.tts_enabled.setChecked(bool(self.db.setting("tts_enabled", True)))
        form.addRow(
            self._t("continuous_work_reminder", "連續工作提醒"),
            self.break_minutes_control,
        )
        form.addRow(
            self._t("overwork_message", "久坐／過勞提醒訊息"),
            self.overwork_message,
        )
        form.addRow(self._t("voice_section", "語音"), self.tts_enabled)

    def _add_desktop_settings(
        self,
        form: QFormLayout,
        capabilities: PlatformCapabilities,
    ) -> None:
        self.autostart = self._autostart_checkbox(capabilities)
        self.topmost_mode = QComboBox()
        topmost_values = (
            "智慧置頂（推薦）",
            "永遠置頂",
            "不置頂",
        )
        for key, value in zip(
            TOPMOST_MODE_KEYS,
            topmost_values,
            strict=True,
        ):
            self.topmost_mode.addItem(self._settings_text(key), value)
        self._select_combo_data(
            self.topmost_mode,
            str(self.db.setting("topmost_mode", topmost_values[0])),
        )
        self.topmost_mode.currentIndexChanged.connect(self._topmost_mode_changed)
        character_scale = self._character_scale_control()
        self.proactive_mode = QComboBox()
        proactive_values = (
            "安靜（只提醒必要事項）",
            "平衡（推薦）",
            "積極（主動建議）",
        )
        for key, value in zip(
            PROACTIVE_MODE_KEYS,
            proactive_values,
            strict=True,
        ):
            self.proactive_mode.addItem(self._settings_text(key), value)
        self._select_combo_data(
            self.proactive_mode,
            {
                "quiet": proactive_values[0],
                "balanced": proactive_values[1],
                "active": proactive_values[2],
            }.get(
                str(
                    self.db.setting(
                        "proactive_interaction_mode",
                        self.db.setting("proactive_mode", proactive_values[1]),
                    )
                ),
                str(self.db.setting("proactive_mode", proactive_values[1])),
            ),
        )
        form.addRow(
            self._settings_text(SettingsText.AUTOSTART_LABEL),
            self.autostart,
        )
        form.addRow(
            self._settings_text(SettingsText.TOPMOST_LABEL),
            self.topmost_mode,
        )
        form.addRow(
            self._settings_text(
                SettingsText.CHARACTER_SCALE_LABEL,
                assistant=self.assistant_name,
            ),
            character_scale,
        )
        form.addRow(
            self._settings_text(SettingsText.PROACTIVE_LABEL),
            self.proactive_mode,
        )

    def _autostart_checkbox(
        self,
        capabilities: PlatformCapabilities,
    ) -> QCheckBox:
        checkbox = QCheckBox(
            self._settings_text(SettingsText.AUTOSTART_WINDOWS)
            if capabilities.desktop_autostart
            else self._settings_text(
                SettingsText.AUTOSTART_UNAVAILABLE,
                platform=capabilities.display_name,
            )
        )
        checkbox.setChecked(
            bool(capabilities.desktop_autostart and self.db.setting("autostart", False))
        )
        checkbox.setEnabled(capabilities.desktop_autostart)
        return checkbox

    def _character_scale_control(self) -> QWidget:
        saved_scale = int(
            self.db.setting(
                "character_scale_percent",
                CHARACTER_SCALE_DEFAULT,
            )
        )
        scale = max(
            CHARACTER_SCALE_MIN,
            min(CHARACTER_SCALE_MAX, saved_scale),
        )
        self.character_scale_slider = QSlider(Qt.Horizontal)
        self.character_scale_slider.setRange(
            CHARACTER_SCALE_MIN,
            CHARACTER_SCALE_MAX,
        )
        self.character_scale_slider.setSingleStep(5)
        self.character_scale_slider.setPageStep(10)
        self.character_scale_slider.setTickInterval(5)
        self.character_scale_slider.setTickPosition(QSlider.TicksBelow)
        self.character_scale_slider.setValue(scale)
        self.character_scale_label = QLabel(f"{scale}%")
        self.character_scale_label.setMinimumWidth(48)
        self.character_scale_label.setAlignment(Qt.AlignCenter)
        reset_button = QPushButton(
            self._settings_text(SettingsText.CHARACTER_SCALE_RESET)
        )
        reset_button.setToolTip(
            self._settings_text(
                SettingsText.CHARACTER_SCALE_RESET_TOOLTIP,
                assistant=self.assistant_name,
            )
        )
        reset_button.clicked.connect(
            lambda: self.character_scale_slider.setValue(CHARACTER_SCALE_DEFAULT)
        )
        control = QWidget()
        layout = QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.character_scale_slider, 1)
        layout.addWidget(self.character_scale_label)
        layout.addWidget(reset_button)
        self.character_scale_slider.valueChanged.connect(self._character_scale_changed)
        return control

    def _topmost_mode_changed(self, _index: int) -> None:
        mode = str(self.topmost_mode.currentData() or "智慧置頂（推薦）")
        self.db.set_setting("topmost_mode", mode)
        self.topmost_mode_changed.emit(mode)

    def _character_scale_changed(self, value: int) -> None:
        value = max(
            CHARACTER_SCALE_MIN,
            min(CHARACTER_SCALE_MAX, int(value)),
        )
        self.character_scale_label.setText(f"{value}%")
        self.db.set_setting("character_scale_percent", value)
        self.character_scale_preview.emit(value)

    def _add_background_settings(self, form: QFormLayout) -> None:
        self.background_assistant_enabled = QCheckBox(
            self._settings_text(SettingsText.BACKGROUND_ASSISTANT_ENABLED)
        )
        self.background_assistant_enabled.setChecked(
            bool(self.db.setting("background_assistant_enabled", False))
        )
        self.background_watch_apps = QLineEdit(
            str(
                self.db.setting(
                    "background_watch_apps",
                    "Visual Studio Code,GitHub Desktop",
                )
            )
        )
        self.background_watch_apps.setPlaceholderText(
            self._settings_text(SettingsText.BACKGROUND_WATCH_APPS_PLACEHOLDER)
        )
        self.background_diagnostic_report = QLineEdit(
            str(self.db.setting("background_diagnostic_report", ""))
        )
        self.background_diagnostic_report.setPlaceholderText(
            self._settings_text(SettingsText.BACKGROUND_DIAGNOSTIC_PLACEHOLDER)
        )
        note = QLabel(self._settings_text(SettingsText.BACKGROUND_SAFETY_NOTE))
        note.setWordWrap(True)
        note.setStyleSheet("color:#356f8d;")
        form.addRow(
            self._settings_text(SettingsText.BACKGROUND_ASSISTANT_LABEL),
            self.background_assistant_enabled,
        )
        form.addRow(
            self._settings_text(SettingsText.BACKGROUND_WATCH_APPS_LABEL),
            self.background_watch_apps,
        )
        form.addRow(
            self._settings_text(SettingsText.BACKGROUND_DIAGNOSTIC_LABEL),
            self.background_diagnostic_report,
        )
        form.addRow("", note)

    def _add_physics_settings(self, form: QFormLayout) -> None:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.physics_controls: dict[str, QCheckBox] = {}
        for key, (name_key, description_key) in PHYSICS_TEXT_KEYS.items():
            control = QCheckBox(self._settings_text(name_key))
            control.setToolTip(self._settings_text(description_key))
            control.setChecked(bool(self.db.setting(key, True)))
            layout.addWidget(control)
            self.physics_controls[key] = control
        note = QLabel(self._settings_text(SettingsText.PHYSICS_NOTE))
        note.setWordWrap(True)
        note.setStyleSheet("color:#356f8d;")
        layout.addWidget(note)
        form.addRow(self._settings_text(SettingsText.PHYSICS_LABEL), box)

    def _add_work_folder_settings(self, form: QFormLayout) -> None:
        self.work_folder = QLineEdit(str(self.db.setting("work_folder", "")))
        self.work_folder.setPlaceholderText(
            self._settings_text(SettingsText.WORK_FOLDER_PLACEHOLDER)
        )
        open_button = QPushButton(self._settings_text(SettingsText.WORK_FOLDER_OPEN))
        open_button.clicked.connect(self.open_work_folder)
        form.addRow(
            self._settings_text(SettingsText.WORK_FOLDER_LABEL),
            self.work_folder,
        )
        form.addRow("", open_button)

    def _add_ai_settings(
        self,
        form: QFormLayout,
        capabilities: PlatformCapabilities,
    ) -> None:
        key_saved = bool(
            capabilities.secure_secret_storage and self.secret_store.load()
        )
        self.api_key_input = self._api_key_input(
            capabilities,
            key_saved,
        )
        self.api_key_input.editingFinished.connect(self._save_api_key_if_provided)
        self.ai_model = self._editable_combo(
            TEXT_MODELS,
            str(self.db.setting("ai_model", DEFAULT_TEXT_MODEL)),
        )
        self.persona_prompt = self._persona_prompt_input()
        clear_button = QPushButton(self._t("remove_api_key", "移除已保存的 API 金鑰"))
        clear_button.clicked.connect(self.clear_api_key)
        clear_button.setEnabled(capabilities.secure_secret_storage)
        self.api_status = QLabel(self._api_status_text(capabilities, key_saved))
        form.addRow(
            self._t("api_key", "OpenAI API 金鑰"),
            self.api_key_input,
        )
        form.addRow(
            self._t("text_model", "文字模型"),
            self.ai_model,
        )
        form.addRow(
            self._settings_text(SettingsText.PERSONA_LABEL),
            self.persona_prompt,
        )
        form.addRow(self._settings_language_note())
        form.addRow("", clear_button)
        form.addRow(
            self._settings_text(SettingsText.AI_CORE_LABEL),
            self.api_status,
        )

    def _api_key_input(
        self,
        capabilities: PlatformCapabilities,
        key_saved: bool,
    ) -> QLineEdit:
        key_input = QLineEdit()
        key_input.setEchoMode(QLineEdit.Password)
        key_input.setAccessibleName(self._t("api_key", "OpenAI API 金鑰"))
        key_input.setToolTip(
            self._t(
                "secret_auto_save_hint",
                "輸入後按 Enter 或移開游標，即會自動安全保存。",
            )
        )
        if capabilities.secure_secret_storage:
            placeholder = (
                self._t(
                    "api_key_saved",
                    "已安全保存（留空不變）",
                )
                if key_saved
                else self._t(
                    "api_key_missing",
                    "貼上 sk- 開頭的 OpenAI Project API Key",
                )
            )
        else:
            placeholder = self._t(
                "platform_secret_storage_unavailable",
                f"{capabilities.display_name} 安全金鑰保存尚未完成實機驗證",
                platform=capabilities.display_name,
            )
            key_input.setEnabled(False)
        key_input.setPlaceholderText(placeholder)
        return key_input

    def _api_status_text(
        self,
        capabilities: PlatformCapabilities,
        key_saved: bool,
    ) -> str:
        if os.getenv("OPENAI_API_KEY"):
            return self._t(
                "api_status_environment",
                "OpenAI API：使用環境變數提供的金鑰",
            )
        if key_saved:
            return self._t(
                "api_status_saved",
                "OpenAI API：金鑰已由 Windows 加密保存",
            )
        if not capabilities.secure_secret_storage:
            return self._t(
                "api_status_secret_unavailable",
                f"OpenAI API：{capabilities.display_name} 安全金鑰保存尚未完成實機驗證",
                platform=capabilities.display_name,
            )
        return self._t(
            "api_status_offline",
            "OpenAI API：未設定，使用離線人設",
        )

    def _persona_prompt_input(self) -> QTextEdit:
        prompt = QTextEdit()
        prompt.setPlainText(
            str(
                self.db.setting(
                    "persona_prompt",
                    default_persona_for_language(self.ui_language),
                )
            )
        )
        prompt.setMinimumHeight(160)
        prompt.setPlaceholderText(self._settings_text(SettingsText.PERSONA_PLACEHOLDER))
        return prompt

    def _settings_language_note(self) -> QLabel:
        note = QLabel(
            self._t(
                "restart_language_note",
                "變更介面語言後，重新啟動墨寒即可完整套用。",
            )
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#356f8d;")
        return note

    def _add_update_settings(
        self,
        form: QFormLayout,
        parent: QWidget,
    ) -> None:
        self.update_panel = UpdatePanel(
            self.db,
            self.platform_services.paths.data,
            parent,
            language=self.ui_language,
            manager_factory=self.update_manager_factory,
        )
        form.addRow(self.update_panel)

    def _settings_tab(self) -> QWidget:
        tab, form = self._form_scroll_page()
        capabilities = self.platform_services.capabilities
        self._add_profile_settings(form, tab)
        form.addRow(QLabel(self._t("system_heading", "<b>工作與系統設定</b>")))
        self._add_reminder_settings(form)
        self._add_work_rhythm_settings(form)
        self._add_desktop_settings(form, capabilities)
        self._add_background_settings(form)
        self._add_physics_settings(form)
        self._add_work_folder_settings(form)
        self._add_ai_settings(form, capabilities)
        self._add_update_settings(form, tab)
        self.theme_pack_panel = ThemePackPanel(
            self.theme_pack_service,
            self.theme_session,
            install=self.theme_pack_service.install,
            remove=self.theme_pack_service.remove,
            language=self.ui_language,
            parent=tab,
        )
        form.addRow(
            QLabel(self._t("theme_preview", "<b>控制台佈景主題</b>")),
        )
        form.addRow(self.theme_pack_panel)
        return tab

    def open_work_folder(self) -> None:
        value = self.work_folder.text().strip()
        if value and Path(value).is_dir():
            if self._permission_allowed(
                "open_folder",
                self._settings_text(SettingsText.WORK_FOLDER_OPEN),
            ):
                self.platform_services.open_path(Path(value))
        else:
            QMessageBox.information(
                self,
                self._settings_text(SettingsText.WORK_FOLDER_INVALID_TITLE),
                self._settings_text(SettingsText.WORK_FOLDER_INVALID_MESSAGE),
            )
