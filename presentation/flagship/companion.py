from __future__ import annotations

lazy from dataclasses import replace

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

lazy from application.companion_phrasebook import (
    CompanionPhrasebook,
    grouped_phrasebook_categories,
)
lazy from domain.companion_proactivity_preferences import (
    CompanionProactivityPreferences,
)
lazy from domain.performance_preferences import PerformancePreferences

__all__ = ('FlagshipCompanionMixin',)


class FlagshipCompanionMixin:
    def _companion_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setObjectName("companionProactivityScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self._companion_preference_card())
        layout.addWidget(self._performance_preference_card())
        layout.addWidget(self._gesture_interaction_card())
        layout.addWidget(self._openai_vision_preference_card())
        layout.addWidget(self._companion_phrasebook_card())
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll
    def _companion_preference_card(self) -> QFrame:
        preferences = self._proactivity_draft.value
        preference_card = QFrame()
        preference_card.setObjectName("companionProactivityCard")
        preference_card.setStyleSheet(
            "QFrame#companionProactivityCard{background:#f5fbfe;"
            "border:1px solid #bfd8e4;border-radius:12px;padding:8px;}"
        )
        preference_form = QFormLayout(preference_card)
        heading = QLabel(self._t("<b>主動陪伴與健康提醒</b>"))
        heading.setStyleSheet("color:#2f6987;font-size:16px;")
        preference_form.addRow(heading)
        note = QLabel(
            self._t(
                "所有變更會先暫存；只有控制台下方的全域保存設定才會生效。"
            )
        )
        note.setWordWrap(True)
        preference_form.addRow(note)

        self.companion_enabled = self._preference_checkbox(
            self._t("啟用主動陪伴"), preferences.enabled
        )
        self.companion_meal_enabled = self._preference_checkbox(
            self._t("飲食提醒"), preferences.meal_enabled
        )
        self.companion_hydration_enabled = self._preference_checkbox(
            self._t("喝水提醒"), preferences.hydration_enabled
        )
        self.companion_rest_enabled = self._preference_checkbox(
            self._t("休息提醒"), preferences.rest_enabled
        )
        self.companion_sitting_enabled = self._preference_checkbox(
            self._t("久坐提醒"), preferences.prolonged_sitting_enabled
        )
        self.companion_occasions_enabled = self._preference_checkbox(
            self._t("特殊節日提醒"), preferences.special_occasions_enabled
        )
        self.companion_birthday_enabled = self._preference_checkbox(
            self._t("墨寒生日提醒"), preferences.birthday_enabled
        )
        self.companion_focus_protection = self._preference_checkbox(
            self._t("專注時暫停主動提醒"),
            preferences.focus_protection_enabled,
        )
        self.companion_meeting_protection = self._preference_checkbox(
            self._t("會議時暫停主動提醒"),
            preferences.meeting_protection_enabled,
        )
        self.companion_fullscreen_protection = self._preference_checkbox(
            self._t("全螢幕時暫停主動提醒"),
            preferences.fullscreen_protection_enabled,
        )
        for control in (
            self.companion_enabled,
            self.companion_meal_enabled,
            self.companion_hydration_enabled,
            self.companion_rest_enabled,
            self.companion_sitting_enabled,
            self.companion_occasions_enabled,
            self.companion_birthday_enabled,
            self.companion_focus_protection,
            self.companion_meeting_protection,
            self.companion_fullscreen_protection,
        ):
            preference_form.addRow(control)
        self._add_companion_numeric_controls(preference_form, preferences)
        self._add_proactive_interaction_controls(preference_form)
        return preference_card
    def _add_proactive_interaction_controls(self, form: QFormLayout) -> None:
        """Visible owners of the proactive-mode and welcome-timing settings.

        These three controls used to be constructed for the remote tab but were
        never added to any layout, so every flagship save silently overwrote the
        user's values with the ones read at construction time.  They now live on
        the companion tab, and ``save_draft_settings`` persists each key only
        after the user actually changed its control (see
        ``_proactive_interaction_touched``).
        """

        self._proactive_interaction_touched: set[str] = set()
        self.proactive_mode = QComboBox()
        for label, value in (
            (self._t("安靜（不主動寒暄）"), "quiet"),
            (self._t("適度（推薦）"), "balanced"),
            (self._t("積極（較常主動關心）"), "active"),
        ):
            self.proactive_mode.addItem(label, value)
        self.proactive_mode.setAccessibleName(self._t("主動寒暄模式"))
        self.framing_style = QComboBox()
        for label, value in (
            (self._t("沉穩（對話期間固定半身，建議）"), "steady"),
            (self._t("靈動（依情境切換全身與半身）"), "lively"),
            (self._t("固定半身（僅換裝預覽顯示全身）"), "half-only"),
        ):
            self.framing_style.addItem(label, value)
        self.framing_style.setAccessibleName(self._t("桌面角色構圖風格"))
        self.framing_style.currentIndexChanged.connect(
            lambda _index: self._proactive_interaction_touched.add(
                "framing_style"
            )
        )
        self.minimum_away_minutes = QSpinBox()
        self.minimum_away_minutes.setRange(1, 30)
        self.minimum_away_minutes.setSuffix(self._t(" 分鐘"))
        self.minimum_away_minutes.setAccessibleName(
            self._t("歡迎回來的最短離座時間（分鐘）")
        )
        self.conversation_silence_minutes = QSpinBox()
        self.conversation_silence_minutes.setRange(10, 240)
        self.conversation_silence_minutes.setSuffix(self._t(" 分鐘"))
        self.conversation_silence_minutes.setAccessibleName(
            self._t("對話沉默關心門檻（分鐘）")
        )
        self._refresh_proactive_interaction_controls()
        self.proactive_mode.currentIndexChanged.connect(
            lambda _index: self._proactive_interaction_touched.add(
                "proactive_interaction_mode"
            )
        )
        self.minimum_away_minutes.valueChanged.connect(
            lambda _value: self._proactive_interaction_touched.add(
                "multisensory_welcome_minimum_seconds"
            )
        )
        self.conversation_silence_minutes.valueChanged.connect(
            lambda _value: self._proactive_interaction_touched.add(
                "multisensory_conversation_silence_seconds"
            )
        )
        form.addRow(self._t("桌面角色構圖風格"), self.framing_style)
        form.addRow(self._t("主動寒暄模式"), self.proactive_mode)
        form.addRow(
            self._t("歡迎回來的最短離座時間"),
            self._companion_step_control(
                self.minimum_away_minutes,
                "companionMinimumAwayMinutes",
            ),
        )
        form.addRow(
            self._t("對話沉默關心門檻"),
            self._companion_step_control(
                self.conversation_silence_minutes,
                "companionConversationSilenceMinutes",
            ),
        )
    def _refresh_proactive_interaction_controls(self) -> None:
        """Re-read the persisted values and mark every control untouched."""

        mode_index = self.proactive_mode.findData(
            str(self.db.setting("proactive_interaction_mode", "balanced"))
        )
        self.proactive_mode.setCurrentIndex(max(0, mode_index))
        style_index = self.framing_style.findData(
            str(self.db.setting("framing_style", "steady"))
        )
        self.framing_style.setCurrentIndex(max(0, style_index))
        self.minimum_away_minutes.setValue(
            max(
                1,
                round(
                    float(
                        self.db.setting(
                            "multisensory_welcome_minimum_seconds", 60
                        )
                    )
                    / 60
                ),
            )
        )
        self.conversation_silence_minutes.setValue(
            max(
                10,
                round(
                    float(
                        self.db.setting(
                            "multisensory_conversation_silence_seconds",
                            45 * 60,
                        )
                    )
                    / 60
                ),
            )
        )
        self._proactive_interaction_touched.clear()
    def _performance_preference_card(self) -> QFrame:
        preferences = self._performance_draft.value
        card = QFrame()
        card.setObjectName("companionPerformanceCard")
        card.setStyleSheet(
            "QFrame#companionPerformanceCard{background:#f6f6fd;"
            "border:1px solid #c6c8e4;border-radius:12px;padding:8px;}"
        )
        form = QFormLayout(card)
        heading = QLabel(self._t("<b>演出偏好</b>"))
        heading.setStyleSheet("color:#4a4f87;font-size:16px;")
        form.addRow(heading)
        note = QLabel(
            self._t(
                "背身與 360° 演出預設關閉；勾選後按全域保存設定才會生效。"
            )
        )
        note.setWordWrap(True)
        form.addRow(note)
        self.performance_view_360 = self._preference_checkbox(
            self._t("允許 360° 視角演出"), preferences.view_360_enabled
        )
        self.performance_full_back = self._preference_checkbox(
            self._t("允許全背身演出"), preferences.full_back_view_enabled
        )
        self.performance_emotional_back = self._preference_checkbox(
            self._t("允許情緒背身演出"),
            preferences.emotional_back_view_enabled,
        )
        self.performance_camera_context = self._preference_checkbox(
            self._t("允許攝影機情境驅動演出"),
            preferences.camera_context_enabled,
        )
        for control in (
            self.performance_view_360,
            self.performance_full_back,
            self.performance_emotional_back,
            self.performance_camera_context,
        ):
            form.addRow(control)
        self.performance_intensity = QSpinBox()
        self.performance_intensity.setRange(0, 100)
        self.performance_intensity.setValue(preferences.intensity_percent)
        self.performance_intensity.setAccessibleName(self._t("演出強度"))
        form.addRow(
            self._t("演出強度"),
            self._companion_step_control(
                self.performance_intensity,
                "companionPerformanceIntensity",
            ),
        )
        return card
    def _refresh_performance_controls(self) -> None:
        preferences = self._performance_draft.value
        self.performance_view_360.setChecked(preferences.view_360_enabled)
        self.performance_full_back.setChecked(preferences.full_back_view_enabled)
        self.performance_emotional_back.setChecked(
            preferences.emotional_back_view_enabled
        )
        self.performance_camera_context.setChecked(
            preferences.camera_context_enabled
        )
        self.performance_intensity.setValue(preferences.intensity_percent)
    def _staged_performance_preferences(self) -> PerformancePreferences:
        return replace(
            self._performance_draft.value,
            view_360_enabled=self.performance_view_360.isChecked(),
            full_back_view_enabled=self.performance_full_back.isChecked(),
            emotional_back_view_enabled=(
                self.performance_emotional_back.isChecked()
            ),
            camera_context_enabled=self.performance_camera_context.isChecked(),
            intensity_percent=self.performance_intensity.value(),
        )
    def _add_companion_numeric_controls(
        self,
        form: QFormLayout,
        preferences: CompanionProactivityPreferences,
    ) -> None:
        self.companion_brief_minutes = QSpinBox()
        self.companion_brief_minutes.setRange(1, 720)
        self.companion_brief_minutes.setSuffix(self._t(" 分鐘"))
        self.companion_brief_minutes.setValue(
            preferences.brief_absence_seconds // 60
        )
        self.companion_brief_minutes.setAccessibleName(
            self._t("短暫離座門檻（分鐘）")
        )
        self.companion_long_wait_minutes = QSpinBox()
        self.companion_long_wait_minutes.setRange(5, 43_200)
        self.companion_long_wait_minutes.setSuffix(self._t(" 分鐘"))
        self.companion_long_wait_minutes.setValue(
            preferences.long_wait_seconds // 60
        )
        self.companion_long_wait_minutes.setAccessibleName(
            self._t("久候門檻（分鐘）")
        )
        self.companion_daily_limit = QSpinBox()
        self.companion_daily_limit.setRange(1, 32)
        self.companion_daily_limit.setValue(preferences.daily_limit)
        self.companion_daily_limit.setAccessibleName(
            self._t("每日主動提醒上限")
        )
        self.companion_brief_minutes.valueChanged.connect(
            self._keep_companion_thresholds_separate
        )
        self._keep_companion_thresholds_separate(
            self.companion_brief_minutes.value()
        )
        form.addRow(
            self._t("短暫離座門檻"),
            self._companion_step_control(
                self.companion_brief_minutes,
                "companionBriefMinutes",
            ),
        )
        form.addRow(
            self._t("久候門檻"),
            self._companion_step_control(
                self.companion_long_wait_minutes,
                "companionLongWaitMinutes",
            ),
        )
        form.addRow(
            self._t("每日主動提醒上限"),
            self._companion_step_control(
                self.companion_daily_limit,
                "companionDailyLimit",
            ),
        )

    def _companion_step_control(
        self,
        editor: QSpinBox,
        object_prefix: str,
    ) -> QWidget:
        editor.setButtonSymbols(QAbstractSpinBox.NoButtons)
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(editor, 1)
        down_button = QPushButton("▼")
        down_button.setObjectName(f"{object_prefix}Down")
        down_button.setAccessibleName(
            editor.accessibleName() + self._t("，減少")
        )
        down_button.clicked.connect(editor.stepDown)
        up_button = QPushButton("▲")
        up_button.setObjectName(f"{object_prefix}Up")
        up_button.setAccessibleName(
            editor.accessibleName() + self._t("，增加")
        )
        up_button.clicked.connect(editor.stepUp)
        row.addWidget(down_button)
        row.addWidget(up_button)
        return container
    def _companion_phrasebook_card(self) -> QFrame:
        phrase_card = QFrame()
        phrase_card.setObjectName("companionPhrasebookCard")
        phrase_card.setStyleSheet(
            "QFrame#companionPhrasebookCard{background:#fff8f4;"
            "border:1px solid #e4c8b8;border-radius:12px;padding:8px;}"
        )
        phrase_layout = QVBoxLayout(phrase_card)
        phrase_heading = QLabel(self._t("<b>多情境陪伴詞庫</b>"))
        phrase_heading.setStyleSheet("color:#9a4f3d;font-size:16px;")
        phrase_layout.addWidget(phrase_heading)
        self.companion_phrasebook_summary = QLabel(
            self._t("可編輯 24 組問候、關心、健康提醒與特殊節日詞句。")
        )
        self.companion_phrasebook_summary.setWordWrap(True)
        phrase_layout.addWidget(self.companion_phrasebook_summary)
        self.companion_phrasebook_button = QPushButton(
            self._t("編輯 28 組多情境詞庫")
        )
        self.companion_phrasebook_button.setAccessibleName(
            self._t("編輯 28 組多情境詞庫")
        )
        self.companion_phrasebook_button.clicked.connect(
            self.edit_companion_phrasebook
        )
        phrase_layout.addWidget(self.companion_phrasebook_button)
        return phrase_card
    def _keep_companion_thresholds_separate(self, brief_minutes: int) -> None:
        minimum = max(5, int(brief_minutes) + 1)
        self.companion_long_wait_minutes.setMinimum(minimum)
        if self.companion_long_wait_minutes.value() < minimum:
            self.companion_long_wait_minutes.setValue(minimum)
    def edit_companion_phrasebook(self) -> None:
        phrasebook = self._phrasebook_draft
        dialog = QDialog(self)
        dialog.setWindowTitle(self._t("多情境陪伴詞庫"))
        root = QVBoxLayout(dialog)
        groups = QTabWidget()
        editors: dict[str, QTextEdit] = {}
        for group_title, categories in grouped_phrasebook_categories():
            category_tabs = QTabWidget()
            for key, title in categories:
                editor = QTextEdit()
                values = (
                    phrasebook.check_ins
                    if key == "check_ins"
                    else (
                        phrasebook.scenarios.get(key, ())
                        if key.startswith(("wellbeing.", "occasion."))
                        else phrasebook.welcomes.get(key, ())
                    )
                )
                editor.setPlainText("\n".join(values))
                editor.setPlaceholderText(
                    self._t("每行一句；留白時使用公開版中性預設。")
                )
                editor.setAccessibleName(self._t(title))
                category_tabs.addTab(editor, self._t(title))
                editors[key] = editor
            groups.addTab(category_tabs, self._t(group_title))
        root.addWidget(groups)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(self._t("完成編輯"))
        buttons.button(QDialogButtonBox.Cancel).setText(self._t("取消"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        root.addWidget(buttons)
        if dialog.exec() != QDialog.Accepted:
            return
        values_by_key = {
            key: tuple(
                line.strip()
                for line in editor.toPlainText().splitlines()
                if line.strip()
            )
            for key, editor in editors.items()
        }
        welcomes = {
            key: values
            for key, values in values_by_key.items()
            if key != "check_ins"
            and not key.startswith(("wellbeing.", "occasion."))
        }
        scenarios = {
            key: values
            for key, values in values_by_key.items()
            if key.startswith(("wellbeing.", "occasion."))
        }
        self._phrasebook_draft = CompanionPhrasebook(
            welcomes,
            values_by_key["check_ins"],
            scenarios,
        )
