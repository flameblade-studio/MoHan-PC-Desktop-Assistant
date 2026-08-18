from __future__ import annotations

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QAbstractSpinBox,
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
        return preference_card
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
