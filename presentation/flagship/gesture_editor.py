from __future__ import annotations

lazy from dataclasses import replace

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

lazy from domain.gesture_configuration import (
    BUILTIN_GESTURE_LABELS,
    GESTURE_ACTION_LABELS,
    GestureAction,
    GestureBinding,
    GestureDefinition,
    GestureSource,
)

__all__ = ('FlagshipGestureEditorMixin',)


class FlagshipGestureEditorMixin:
    def _gesture_interaction_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("gestureInteractionCard")
        card.setStyleSheet(
            "QFrame#gestureInteractionCard{background:#f2f7fb;"
            "border:1px solid #9fb8cf;border-radius:12px;padding:8px;}"
        )
        layout = QVBoxLayout(card)
        heading = QLabel(self._t("<b>手勢互動</b>"))
        heading.setStyleSheet("color:#355f7d;font-size:16px;")
        layout.addWidget(heading)
        note = QLabel(
            self._t(
                "所有手勢變更只會先暫存，按下全域保存設定後才會生效。"
                "自訂文字指令會交由既有安全命令流程處理。"
            )
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.gesture_enabled = self._preference_checkbox(
            self._t("啟用手勢互動"), self._gesture_draft.value.enabled
        )
        layout.addWidget(self.gesture_enabled)
        layout.addLayout(self._gesture_editor_layout())
        layout.addWidget(self._gesture_recording_status())
        layout.addLayout(self._gesture_action_buttons())
        self._loading_gesture_editor = False
        self._refresh_gesture_list()
        return card
    def _gesture_editor_layout(self) -> QHBoxLayout:
        editor = QHBoxLayout()
        self.gesture_list = QListWidget()
        self.gesture_list.setAccessibleName(self._t("手勢列表"))
        self.gesture_list.currentRowChanged.connect(self._load_gesture_editor)
        editor.addWidget(self.gesture_list, 2)
        form = QFormLayout()
        self.gesture_name = QLineEdit()
        self.gesture_name.setAccessibleName(self._t("手勢名稱"))
        self.gesture_action = QComboBox()
        self.gesture_action.setAccessibleName(self._t("辨識後動作"))
        for action, labels in GESTURE_ACTION_LABELS.items():
            self.gesture_action.addItem(
                self._gesture_label(labels), action.value
            )
        self.gesture_action.currentIndexChanged.connect(
            self._gesture_action_changed
        )
        self.gesture_command = QLineEdit()
        self.gesture_command.setMaxLength(256)
        self.gesture_command.setAccessibleName(self._t("自訂文字指令"))
        self.gesture_command.setPlaceholderText(
            self._t("輸入一行交給墨寒安全命令流程的文字指令")
        )
        self.gesture_definition_enabled = self._preference_checkbox(
            self._t("啟用此手勢"), False
        )
        self.gesture_definition_enabled.toggled.connect(
            self._stage_selected_gesture
        )
        self.gesture_command.editingFinished.connect(
            self._stage_selected_gesture
        )
        form.addRow(self._t("手勢名稱"), self.gesture_name)
        form.addRow(self._t("辨識後動作"), self.gesture_action)
        form.addRow(self._t("自訂文字指令"), self.gesture_command)
        form.addRow(self.gesture_definition_enabled)
        editor.addLayout(form, 3)
        return editor
    def _gesture_recording_status(self) -> QLabel:
        self.gesture_record_status = QLabel()
        self.gesture_record_status.setWordWrap(True)
        self.gesture_record_status.setAccessibleName(self._t("錄製狀態"))
        return self.gesture_record_status
    def _gesture_action_buttons(self) -> QHBoxLayout:
        actions = QHBoxLayout()
        self.gesture_add_button = QPushButton(self._t("新增自訂手勢"))
        self.gesture_rename_button = QPushButton(self._t("重新命名"))
        self.gesture_delete_button = QPushButton(self._t("刪除自訂手勢"))
        self.gesture_reset_button = QPushButton(self._t("重設內建手勢"))
        self.gesture_record_button = QPushButton(self._t("錄製手部特徵"))
        self.gesture_add_button.clicked.connect(self.add_custom_gesture)
        self.gesture_rename_button.clicked.connect(self.rename_custom_gesture)
        self.gesture_delete_button.clicked.connect(self.delete_custom_gesture)
        self.gesture_reset_button.clicked.connect(self.reset_builtin_gesture)
        self.gesture_record_button.clicked.connect(self.record_custom_gesture)
        for button in (
            self.gesture_add_button,
            self.gesture_rename_button,
            self.gesture_delete_button,
            self.gesture_reset_button,
            self.gesture_record_button,
        ):
            button.setAccessibleName(button.text())
            actions.addWidget(button)
        actions.addStretch(1)
        return actions
    def _gesture_label(self, labels) -> str:
        return {
            "zh-TW": labels.traditional_chinese,
            "zh-CN": labels.simplified_chinese,
            "en": labels.english,
            "ja-JP": labels.japanese,
        }[self.language]
    def _gesture_display_name(self, definition: GestureDefinition) -> str:
        if definition.source is GestureSource.BUILTIN:
            return self._gesture_label(BUILTIN_GESTURE_LABELS[definition.gesture_id])
        return definition.display_name
    def _refresh_gesture_list(self, selected_id: str | None = None) -> None:
        selected_id = selected_id or self._selected_gesture_id()
        self.gesture_list.clear()
        selected_row = 0
        for row, definition in enumerate(self._gesture_draft.value.definitions):
            source = self._t(
                "內建" if definition.source is GestureSource.BUILTIN else "自訂"
            )
            state = self._t("已啟用" if definition.enabled else "已停用")
            item = QListWidgetItem(
                f"{self._gesture_display_name(definition)} · {source} · {state}"
            )
            item.setData(Qt.UserRole, definition.gesture_id)
            self.gesture_list.addItem(item)
            if definition.gesture_id == selected_id:
                selected_row = row
        if self.gesture_list.count():
            self.gesture_list.setCurrentRow(selected_row)
    def _selected_gesture_id(self) -> str | None:
        item = self.gesture_list.currentItem() if hasattr(self, "gesture_list") else None
        return str(item.data(Qt.UserRole)) if item is not None else None
    def _selected_gesture(self) -> GestureDefinition | None:
        identifier = self._selected_gesture_id()
        if identifier is None:
            return None
        return self._gesture_draft.value.definition(identifier)
    def _load_gesture_editor(self, _row: int) -> None:
        definition = self._selected_gesture()
        available = definition is not None
        if definition is None:
            self.gesture_name.clear()
            return
        self._loading_gesture_editor = True
        custom = definition.source is GestureSource.CUSTOM
        self.gesture_name.setText(self._gesture_display_name(definition))
        self.gesture_name.setReadOnly(True)
        self._select_combo_data(self.gesture_action, definition.binding.action.value)
        self.gesture_command.setText(definition.binding.custom_command)
        self.gesture_definition_enabled.setChecked(definition.enabled)
        self.gesture_rename_button.setEnabled(custom)
        self.gesture_delete_button.setEnabled(custom)
        self.gesture_reset_button.setEnabled(not custom)
        recorder_available = custom and self._gesture_recorder.available()
        self.gesture_record_button.setEnabled(recorder_available)
        if not custom:
            status = self._t("內建手勢使用已稽核的偵測器，不需錄製。")
        elif recorder_available:
            status = self._t("可錄製手部特徵；不保存照片或影像。")
        else:
            status = self._t("目前沒有可用的手部 landmark 訊號，無法安全錄製。")
        self.gesture_record_status.setText(status)
        self.gesture_action.setEnabled(available)
        self.gesture_definition_enabled.setEnabled(available)
        self._gesture_action_changed()
        self._loading_gesture_editor = False
    def _gesture_action_changed(self, _index: int = -1) -> None:
        custom = self.gesture_action.currentData() == GestureAction.CUSTOM_COMMAND.value
        self.gesture_command.setEnabled(custom)
        if custom and not self.gesture_command.text().strip():
            return
        self._stage_selected_gesture()
    def _stage_selected_gesture(self) -> None:
        if getattr(self, "_loading_gesture_editor", False):
            return
        definition = self._selected_gesture()
        if definition is None:
            return
        action = GestureAction(str(self.gesture_action.currentData()))
        command = self.gesture_command.text().strip() if action is GestureAction.CUSTOM_COMMAND else ""
        updated = replace(
            definition,
            enabled=self.gesture_definition_enabled.isChecked(),
            binding=GestureBinding(action, command),
        )
        self._gesture_draft.update_definition(updated)
    def add_custom_gesture(self) -> None:
        name, accepted = QInputDialog.getText(
            self, self._t("新增自訂手勢"), self._t("手勢名稱")
        )
        if accepted and name.strip():
            self._gesture_draft.value = self._gesture_draft.value.add_custom(name)
            self._refresh_gesture_list(self._gesture_draft.value.definitions[-1].gesture_id)
    def rename_custom_gesture(self) -> None:
        definition = self._selected_gesture()
        if definition is None or definition.source is GestureSource.BUILTIN:
            return
        name, accepted = QInputDialog.getText(
            self,
            self._t("重新命名"),
            self._t("手勢名稱"),
            text=definition.display_name,
        )
        if accepted and name.strip():
            self._gesture_draft.update_definition(replace(definition, display_name=name.strip()))
            self._refresh_gesture_list(definition.gesture_id)
    def delete_custom_gesture(self) -> None:
        definition = self._selected_gesture()
        if definition is None or definition.source is GestureSource.BUILTIN:
            return
        self._gesture_draft.value = self._gesture_draft.value.remove_custom(definition.gesture_id)
        self._refresh_gesture_list()
    def reset_builtin_gesture(self) -> None:
        definition = self._selected_gesture()
        if definition is None or definition.source is GestureSource.CUSTOM:
            return
        self._gesture_draft.value = self._gesture_draft.value.reset_builtin(definition.gesture_id)
        self._refresh_gesture_list(definition.gesture_id)
    def record_custom_gesture(self) -> None:
        definition = self._selected_gesture()
        if definition is None or definition.source is GestureSource.BUILTIN:
            return
        if not self._gesture_recorder.available():
            self.gesture_record_status.setText(
                self._t("目前沒有可用的手部 landmark 訊號，無法安全錄製。")
            )
            return
        sample = self._gesture_recorder.record(definition.gesture_id)
        if sample is None:
            self.gesture_record_status.setText(self._t("錄製已取消，沒有保存任何資料。"))
            return
        self._gesture_draft.update_definition(
            replace(definition, samples=(*definition.samples, sample))
        )
        self.gesture_record_status.setText(
            self._t("已暫存手部特徵；全域保存後才會生效。")
        )
