from __future__ import annotations

lazy from dataclasses import dataclass

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

lazy from domain.text_normalizer import to_taiwan_traditional
lazy from presentation.dashboard_dialogs import (
    ArchivedMemoryDialog,
    IdeaEditorDialog,
    MemoryEditorDialog,
    TodoRow,
)
lazy from presentation.dashboard_shared import (
    MEMORY_CATEGORIES,
    TODO_CATEGORIES,
    memory_category_label,
)

__all__ = ("DashboardTodayMemoryMixin", "MemoryTabActions")

MEMORY_PREVIEW_LENGTH = 90
IDEA_PREVIEW_LENGTH = 58


@dataclass(frozen=True, slots=True)
class MemoryTabActions:
    add: QPushButton
    edit: QPushButton
    delete: QPushButton
    clear: QPushButton
    optimize: QPushButton
    archives: QPushButton


class DashboardTodayMemoryMixin:
    def _today_entry_row(
        self,
    ) -> tuple[QHBoxLayout, QPushButton, QPushButton]:
        entry = QHBoxLayout()
        self.todo_input = QLineEdit()
        self.todo_input.setPlaceholderText(
            self._t(
                "today_input_placeholder",
                "輸入待辦標題，例如：完成漫畫第 3 話分鏡",
            )
        )
        self.todo_category = QComboBox()
        for category, key in TODO_CATEGORIES:
            self.todo_category.addItem(self._t(key, category), category)
        add = QPushButton(self._t("add_todo", "＋ 加入待辦"))
        idea = QPushButton(self._t("save_as_idea", "✦ 收入靈感"))
        self.today_add_button = add
        self.today_save_idea_button = idea
        entry.addWidget(self.todo_input, 1)
        entry.addWidget(self.todo_category)
        entry.addWidget(add)
        entry.addWidget(idea)
        return entry, add, idea


    def _today_todo_pane(self) -> QWidget:
        self.todo_feedback = QLabel("")
        self.todo_feedback.setObjectName("entryFeedback")
        todo_header = QHBoxLayout()
        self.today_tasks_heading = QLabel(
            self._t("today_tasks_heading", "<b>今天要做</b>")
        )
        todo_header.addWidget(self.today_tasks_heading)
        self.todo_count = QLabel()
        self.todo_count.setObjectName("sectionCount")
        todo_header.addWidget(self.todo_count)
        todo_header.addStretch()

        self.todo_list = QVBoxLayout()
        self.todo_list.setAlignment(Qt.AlignTop)
        self.todo_list.setContentsMargins(8, 8, 8, 8)
        self.todo_list.setSpacing(7)
        container = QWidget()
        container.setObjectName("todoContainer")
        container.setLayout(self.todo_list)
        self.todo_scroll = QScrollArea()
        self.todo_scroll.setObjectName("todoScroll")
        self.todo_scroll.viewport().setObjectName("todoViewport")
        self.todo_scroll.setWidgetResizable(True)
        self.todo_scroll.setWidget(container)
        todo_pane = QWidget()
        todo_pane.setObjectName("todayPane")
        pane_layout = QVBoxLayout(todo_pane)
        pane_layout.setContentsMargins(0, 0, 0, 0)
        pane_layout.setSpacing(6)
        pane_layout.addLayout(todo_header)
        pane_layout.addWidget(self.todo_scroll, 1)
        return todo_pane


    def _today_idea_pane(
        self,
    ) -> tuple[QWidget, QPushButton, QPushButton]:
        idea_header = QHBoxLayout()
        self.creative_ideas_heading = QLabel(
            self._t("creative_ideas_heading", "<b>創作靈感</b>")
        )
        idea_header.addWidget(self.creative_ideas_heading)
        self.idea_count = QLabel()
        self.idea_count.setObjectName("sectionCount")
        idea_header.addWidget(self.idea_count)
        idea_header.addStretch()
        edit_idea = QPushButton(
            self._t("edit_selected_idea", "編輯選取靈感")
        )
        edit_idea.setToolTip(
            self._t(
                "edit_selected_idea_tooltip",
                "也可以直接雙擊下方任一靈感",
            )
        )
        idea_header.addWidget(edit_idea)
        delete_ideas = QPushButton(
            self._t("delete_checked_ideas", "刪除勾選靈感")
        )
        delete_ideas.setToolTip(
            self._t(
                "delete_checked_ideas_tooltip",
                "只刪除已勾選的靈感，執行前會再次確認",
            )
        )
        self.today_edit_idea_button = edit_idea
        self.today_delete_ideas_button = delete_ideas
        idea_header.addWidget(delete_ideas)
        self.idea_list = QListWidget()
        self.idea_list.setObjectName("ideaList")
        self.idea_list.setMinimumHeight(0)
        self.idea_list.setSpacing(2)
        idea_pane = QWidget()
        idea_pane.setObjectName("todayPane")
        idea_pane_layout = QVBoxLayout(idea_pane)
        idea_pane_layout.setContentsMargins(0, 0, 0, 0)
        idea_pane_layout.setSpacing(6)
        idea_pane_layout.addLayout(idea_header)
        idea_pane_layout.addWidget(self.idea_list, 1)
        return idea_pane, edit_idea, delete_ideas


    def _today_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        entry, add, idea = self._today_entry_row()
        todo_pane = self._today_todo_pane()
        idea_pane, edit_idea, delete_ideas = (
            self._today_idea_pane()
        )
        self.today_splitter = QSplitter(Qt.Vertical)
        self.today_splitter.setObjectName("todaySplitter")
        self.today_splitter.setChildrenCollapsible(False)
        self.today_splitter.addWidget(todo_pane)
        self.today_splitter.addWidget(idea_pane)
        self.today_splitter.setStretchFactor(0, 1)
        self.today_splitter.setStretchFactor(1, 1)
        self._today_split_initialized = False
        layout.addLayout(entry)
        layout.addWidget(self.todo_feedback)
        layout.addWidget(self.today_splitter, 1)
        add.clicked.connect(self.add_todo)
        idea.clicked.connect(self.add_idea)
        edit_idea.clicked.connect(self.edit_selected_idea)
        delete_ideas.clicked.connect(self.delete_checked_ideas)
        self.idea_list.itemDoubleClicked.connect(self.edit_idea_item)
        self.todo_input.returnPressed.connect(self.add_todo)
        return tab


    def _memory_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        entry_row, add_button = self._memory_entry_row()
        filter_row, edit_button, delete_button = (
            self._memory_filter_row()
        )
        action_row, clear_button, optimize_button, archives_button = (
            self._memory_action_row()
        )
        self.memory_list = self._memory_list_widget()
        self.auto_memory = self._memory_auto_checkbox()
        layout.addWidget(self._memory_intro())
        layout.addLayout(entry_row)
        layout.addLayout(filter_row)
        layout.addWidget(self.memory_list, 1)
        layout.addWidget(self.auto_memory)
        layout.addLayout(action_row)
        self._connect_memory_actions(
            MemoryTabActions(
                add=add_button,
                edit=edit_button,
                delete=delete_button,
                clear=clear_button,
                optimize=optimize_button,
                archives=archives_button,
            )
        )
        return tab


    def _memory_intro(self) -> QLabel:
        intro = QLabel(
            self._t(
                "memory_intro",
                "墨寒只保存主上允許留下的人物、偏好、目標、工作流程與"
                "重要日期。記憶存於本機，可分類瀏覽、逐項編輯或刪除。",
            )
        )
        intro.setWordWrap(True)
        return intro


    def _memory_entry_row(self) -> tuple[QHBoxLayout, QPushButton]:
        entry = QHBoxLayout()
        self.memory_input = QLineEdit()
        self.memory_input.setPlaceholderText(
            self._t(
                "memory_input_placeholder",
                "例如：主上偏好先完成漫畫，再處理行政工作",
            )
        )
        self.memory_category = QComboBox()
        for category in MEMORY_CATEGORIES:
            self.memory_category.addItem(
                memory_category_label(self.ui_language, category), category
            )
        self.memory_category.setCurrentIndex(
            self.memory_category.findData("偏好")
        )
        add_button = QPushButton(self._t("remember", "讓寒記住"))
        entry.addWidget(self.memory_input, 1)
        entry.addWidget(self.memory_category)
        entry.addWidget(add_button)
        return entry, add_button


    def _memory_filter_row(
        self,
    ) -> tuple[QHBoxLayout, QPushButton, QPushButton]:
        filter_row = QHBoxLayout()
        filter_row.addWidget(
            QLabel(self._t("memory_filter_label", "分類瀏覽"))
        )
        self.memory_filter = QComboBox()
        self.memory_filter.addItem(self._t("all_memories", "全部記憶"), "")
        for category in MEMORY_CATEGORIES:
            self.memory_filter.addItem(
                memory_category_label(self.ui_language, category), category
            )
        self.memory_count = QLabel()
        self.memory_count.setObjectName("sectionCount")
        filter_row.addWidget(self.memory_filter)
        filter_row.addWidget(self.memory_count)
        filter_row.addStretch()
        edit_button = QPushButton(
            self._t("edit_selected_memory", "編輯選取記憶")
        )
        edit_button.setToolTip(
            self._t("edit_memory_tooltip", "也可以直接雙擊下方任一記憶")
        )
        delete_button = QPushButton(
            self._t("delete_checked_memories", "刪除勾選記憶")
        )
        delete_button.setToolTip(
            self._t(
                "delete_checked_memories_tooltip",
                "只刪除已勾選的記憶，執行前會再次確認",
            )
        )
        filter_row.addWidget(edit_button)
        filter_row.addWidget(delete_button)
        return filter_row, edit_button, delete_button


    @staticmethod
    def _memory_list_widget() -> QListWidget:
        memory_list = QListWidget()
        memory_list.setObjectName("memoryList")
        memory_list.setSpacing(3)
        return memory_list


    def _memory_action_row(
        self,
    ) -> tuple[QHBoxLayout, QPushButton, QPushButton, QPushButton]:
        actions = QHBoxLayout()
        clear_button = QPushButton(
            self._t("clear_all_memories", "清除全部記憶")
        )
        optimize_button = QPushButton(
            self._t("optimize_memories", "安全整理記憶")
        )
        optimize_button.setToolTip(
            self._t(
                "optimize_memories_tooltip",
                "合併低重要度重複內容，超量舊記憶只會先封存",
            )
        )
        archives_button = QPushButton(
            self._t("view_archived_memories", "查看已封存記憶")
        )
        actions.addWidget(clear_button)
        actions.addWidget(optimize_button)
        actions.addWidget(archives_button)
        actions.addStretch()
        return (
            actions,
            clear_button,
            optimize_button,
            archives_button,
        )


    def _memory_auto_checkbox(self) -> QCheckBox:
        checkbox = QCheckBox(
            self._t(
                "auto_memory",
                "從「請記住／我喜歡／我習慣」等明確說法自動建立記憶",
            )
        )
        checkbox.setChecked(bool(self.db.setting("auto_memory", True)))
        return checkbox


    def _connect_memory_actions(self, actions: MemoryTabActions) -> None:
        actions.add.clicked.connect(self.add_memory)
        self.memory_input.returnPressed.connect(self.add_memory)
        actions.edit.clicked.connect(self.edit_selected_memory)
        actions.delete.clicked.connect(self.delete_checked_memories)
        self.memory_list.itemDoubleClicked.connect(self.edit_memory_item)
        self.memory_filter.currentIndexChanged.connect(self.refresh_memories)
        actions.clear.clicked.connect(self.clear_memories)
        actions.optimize.clicked.connect(self.optimize_memories)
        actions.archives.clicked.connect(self.show_archived_memories)


    def refresh_memories(self, *_args) -> None:
        if not hasattr(self, "memory_list"):
            return
        self.memory_list.clear()
        selected_category = (
            str(self.memory_filter.currentData() or "")
            if hasattr(self, "memory_filter")
            else ""
        )
        rows = self.db.list_memories(
            limit=1000,
            category=selected_category or None,
        )
        all_rows = self.db.list_memories(limit=1000)
        counts = dict.fromkeys(MEMORY_CATEGORIES, 0)
        for row in all_rows:
            category = to_taiwan_traditional(str(row["category"]))
            counts[category] = counts.get(category, 0) + 1
        if hasattr(self, "memory_filter"):
            self.memory_filter.setItemText(
                0,
                f"{self._t('all_memories', '全部記憶')}（{len(all_rows)}）",
            )
            for index in range(1, self.memory_filter.count()):
                category = str(self.memory_filter.itemData(index))
                self.memory_filter.setItemText(
                    index,
                    f"{memory_category_label(self.ui_language, category)}"
                    f"（{counts.get(category, 0)}）",
                )
        self.memory_count.setText(
            self._t("memory_count", "{count} 則", count=len(rows))
        )
        if not rows:
            empty = QListWidgetItem(
                self._t(
                    "memory_empty",
                    "這個分類目前沒有記憶。",
                )
            )
            empty.setFlags(Qt.NoItemFlags)
            self.memory_list.addItem(empty)
            return
        source_labels = {
            "manual": self._t(
                "memory_source_manual_short",
                "手動",
            ),
            "conversation": self._t(
                "memory_source_conversation_short",
                "對話",
            ),
        }
        for row in rows:
            content = " ".join(
                str(row["content"]).split()
            )
            if len(content) > MEMORY_PREVIEW_LENGTH:
                content = content[:MEMORY_PREVIEW_LENGTH].rstrip() + "…"
            title = str(
                row["title"]
                or content
                or self._t("memory_untitled", "未命名記憶")
            )
            source = source_labels.get(
                str(row["source"]), str(row["source"])
            )
            item = QListWidgetItem(
                self._t(
                    "memory_item",
                    "【{category}】{title}　重要度 {importance}／5\n"
                    "{content}\n來源：{source}　更新：{updated}",
                    category=memory_category_label(
                        self.ui_language,
                        to_taiwan_traditional(str(row["category"])),
                    ),
                    title=title,
                    importance=int(row["importance"]),
                    content=content,
                    source=source,
                    updated=str(row["updated_at"])[5:16],
                )
            )
            item.setData(Qt.UserRole, int(row["id"]))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setToolTip(str(row["content"]))
            self.memory_list.addItem(item)


    def refresh_todos(self) -> None:
        while self.todo_list.count():
            item = self.todo_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        rows = self.db.list_todos()
        self.todo_count.setText(
            self._t("todo_count", "{count} 件未完成", count=len(rows))
        )
        if not rows:
            empty = QLabel(
                self._t(
                    "todo_empty",
                    "今日卷冊尚空。\n主上先寫下一件真正重要的事。",
                )
            )
            empty.setObjectName("emptyState")
            empty.setAlignment(Qt.AlignCenter)
            self.todo_list.addWidget(empty)
        for row in rows:
            widget = TodoRow(self.db, row, self.ui_language)
            widget.changed.connect(self.refresh_todos)
            self.todo_list.addWidget(widget)


    def refresh_ideas(self) -> None:
        self.idea_list.clear()
        rows = self.db.list_ideas()
        self.idea_count.setText(
            self._t("idea_count", "{count} 則", count=len(rows))
        )
        if not rows:
            empty = QListWidgetItem(
                self._t(
                    "idea_empty",
                    "尚無靈感紀錄；輸入上方文字後按「收入靈感」。",
                )
            )
            empty.setFlags(Qt.NoItemFlags)
            self.idea_list.addItem(empty)
        for row in rows:
            title = str(row["title"] or row["text"])
            content = str(row["content"] or "")
            preview = " ".join(content.split())
            if len(preview) > IDEA_PREVIEW_LENGTH:
                preview = preview[:IDEA_PREVIEW_LENGTH] + "…"
            line = title
            if preview:
                line += f"\n{preview}"
            line += f"  ·  {row['updated_at'][5:16]}"
            item = QListWidgetItem(line)
            item.setData(Qt.UserRole, int(row["id"]))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setToolTip(
                self._t(
                    "idea_edit_tooltip",
                    "雙擊開啟並編輯標題與內文",
                )
            )
            self.idea_list.addItem(item)


    def add_todo(self) -> None:
        text = self.todo_input.text().strip()
        if not text:
            self.todo_feedback.setText(
                self._t("todo_title_required", "請先輸入待辦標題。")
            )
            self.todo_input.setFocus()
            return
        category = str(
            self.todo_category.currentData()
            or self.todo_category.currentText()
        )
        self.db.add_todo(text, category)
        self.todo_input.clear()
        self.refresh_todos()
        self.todo_feedback.setText(
            self._t("todo_added", "✓ 已加入待辦：{text}", text=text)
        )
        self.todo_input.setFocus()
        self.speak_requested.emit(
            self._t("todo_added_speech", "已收入今日卷冊。"), "happy"
        )


    def add_idea(self) -> None:
        text = self.todo_input.text().strip()
        if not text:
            self.todo_feedback.setText(
                self._t(
                    "idea_capture_required",
                    "請先輸入要收藏的靈感。",
                )
            )
            self.todo_input.setFocus()
            return
        self.db.add_idea(text)
        self.todo_input.clear()
        self.refresh_ideas()
        self.todo_feedback.setText(
            self._t("idea_added", "✓ 已收入靈感：{text}", text=text)
        )
        self.todo_input.setFocus()
        self.speak_requested.emit(
            self._t(
                "idea_added_speech",
                "靈光稍縱即逝，妾已替主上收好。",
            ),
            "happy",
        )


    def edit_selected_idea(self) -> None:
        item = self.idea_list.currentItem()
        if item is None or item.data(Qt.UserRole) is None:
            self.todo_feedback.setText(
                self._t(
                    "idea_select_edit",
                    "請先選取一則要編輯的靈感。",
                )
            )
            return
        self.edit_idea_item(item)


    def edit_idea_item(self, item: QListWidgetItem) -> None:
        idea_id = item.data(Qt.UserRole)
        if idea_id is None:
            return
        row = self.db.idea(int(idea_id))
        if row is None:
            self.todo_feedback.setText(
                self._t(
                    "idea_not_found",
                    "找不到這則靈感，請重新整理後再試。",
                )
            )
            return
        editor = IdeaEditorDialog(
            str(row["title"] or row["text"]),
            str(row["content"] or ""),
            self,
            language=self.ui_language,
        )
        if editor.exec() != QDialog.Accepted:
            return
        title, content = editor.values()
        self.db.update_idea(int(idea_id), title, content)
        self.refresh_ideas()
        self.todo_feedback.setText(
            self._t(
                "idea_updated",
                "✓ 已更新靈感：{title}",
                title=title,
            )
        )


    def checked_idea_ids(self) -> list[int]:
        checked: list[int] = []
        for index in range(self.idea_list.count()):
            item = self.idea_list.item(index)
            idea_id = item.data(Qt.UserRole)
            if idea_id is not None and item.checkState() == Qt.Checked:
                checked.append(int(idea_id))
        return checked


    def delete_checked_ideas(self) -> None:
        idea_ids = self.checked_idea_ids()
        if not idea_ids:
            self.todo_feedback.setText(
                self._t(
                    "idea_select_delete",
                    "請先勾選要刪除的靈感。",
                )
            )
            return
        answer = QMessageBox.question(
            self,
            self._t("idea_delete_title", "刪除創作靈感"),
            self._t(
                "idea_delete_confirm",
                "確定永久刪除勾選的 {count} 則靈感嗎？",
                count=len(idea_ids),
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        deleted = self.db.delete_ideas(idea_ids)
        self.refresh_ideas()
        self.todo_feedback.setText(
            self._t(
                "idea_deleted",
                "✓ 已刪除 {count} 則靈感。",
                count=deleted,
            )
        )


    def add_memory(self) -> None:
        text = self.memory_input.text().strip()
        if not text:
            self.memory_input.setFocus()
            return
        self.db.add_memory(
            text,
            str(self.memory_category.currentData() or "其他"),
            "manual",
            4,
        )
        self.memory_input.clear()
        self.refresh_memories()
        self.speak_requested.emit(
            self._t(
                "memory_added_speech",
                "妾已記下。主上日後若要更改，也可逐項整理。",
            ),
            "happy",
        )


    def edit_selected_memory(self) -> None:
        item = self.memory_list.currentItem()
        if item is None or item.data(Qt.UserRole) is None:
            QMessageBox.information(
                self,
                self._t("memory_select_edit_title", "尚未選取"),
                self._t(
                    "memory_select_edit",
                    "請先選取一則要編輯的記憶。",
                ),
            )
            return
        self.edit_memory_item(item)


    def edit_memory_item(self, item: QListWidgetItem) -> None:
        memory_id = item.data(Qt.UserRole)
        if memory_id is None:
            return
        row = self.db.memory(int(memory_id))
        if row is None:
            QMessageBox.information(
                self,
                self._t("memory_not_found_title", "找不到記憶"),
                self._t(
                    "memory_not_found",
                    "這則記憶已不存在，清單將重新整理。",
                ),
            )
            self.refresh_memories()
            return
        editor = MemoryEditorDialog(
            row,
            self,
            language=self.ui_language,
        )
        if editor.exec() != QDialog.Accepted:
            return
        title, content, category, importance = editor.values()
        if not self.db.update_memory(
            int(memory_id), title, content, category, importance
        ):
            QMessageBox.warning(
                self,
                self._t(
                    "memory_save_failed_title",
                    "無法保存記憶",
                ),
                self._t(
                    "memory_save_failed",
                    "可能已有內容完全相同的記憶。原有資料未被變更。",
                ),
            )
            return
        self.refresh_memories()


    def checked_memory_ids(self) -> list[int]:
        checked: list[int] = []
        for index in range(self.memory_list.count()):
            item = self.memory_list.item(index)
            memory_id = item.data(Qt.UserRole)
            if memory_id is not None and item.checkState() == Qt.Checked:
                checked.append(int(memory_id))
        return checked


    def delete_checked_memories(self) -> None:
        memory_ids = self.checked_memory_ids()
        if not memory_ids:
            QMessageBox.information(
                self,
                self._t(
                    "memory_select_delete_title",
                    "尚未勾選",
                ),
                self._t(
                    "memory_select_delete",
                    "請先勾選要刪除的記憶。",
                ),
            )
            return
        answer = QMessageBox.question(
            self,
            self._t("memory_delete_title", "刪除長期記憶"),
            self._t(
                "memory_delete_confirm",
                "確定永久刪除勾選的 {count} 則記憶嗎？",
                count=len(memory_ids),
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.db.delete_memories(memory_ids)
        self.refresh_memories()


    def delete_memory(self) -> None:
        item = self.memory_list.currentItem()
        if not item or item.data(Qt.UserRole) is None:
            return
        self.db.delete_memory(int(item.data(Qt.UserRole)))
        self.refresh_memories()


    def clear_memories(self) -> None:
        answer = QMessageBox.question(
            self,
            self._t("memory_clear_title", "清除長期記憶"),
            self._t(
                "memory_clear_confirm",
                "確定要刪除墨寒保存的全部長期記憶嗎？此動作無法復原。",
            ),
        )
        if answer == QMessageBox.Yes:
            self.db.clear_memories()
            self.refresh_memories()


    def optimize_memories(self) -> None:
        result = self.db.optimize_memories()
        self.refresh_memories()
        QMessageBox.information(
            self,
            self._t("memory_optimize_title", "記憶整理完成"),
            self._t(
                "memory_optimize_result",
                "合併 {deduplicated} 則近似記憶，"
                "封存 {pruned} 則較舊低重要度記憶。\n"
                "目前使用中 {active} 則；"
                "可還原封存 {archived} 則。",
                **result,
            ),
        )


    def show_archived_memories(self) -> None:
        dialog = ArchivedMemoryDialog(
            self.db,
            self,
            language=self.ui_language,
        )
        dialog.exec()
        if dialog.changed:
            self.refresh_memories()
