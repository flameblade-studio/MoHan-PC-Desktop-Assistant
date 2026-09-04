from __future__ import annotations

lazy from PySide6.QtCore import QPoint, Qt, Signal
lazy from PySide6.QtGui import QMouseEvent, QWheelEvent
lazy from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

lazy from application.presentation_ports import PresentationDatabasePort
lazy from domain.app_profile import profile_setting
lazy from domain.text_normalizer import to_taiwan_traditional
lazy from presentation.dashboard_shared import (
    MEMORY_CATEGORIES,
    TODO_CATEGORIES,
    memory_category_label,
)
lazy from presentation.presentation_resources import STYLE
lazy from presentation.ui_localization import ui_text

__all__ = (
    "ArchivedMemoryDialog",
    "ChatHistoryDialog",
    "ClickableLabel",
    "IdeaEditorDialog",
    "MemoryEditorDialog",
    "TodoRow",
    "ZoomTextBrowser",
)

CHAT_HISTORY_PREVIEW_LENGTH = 110
MAX_CHAT_HISTORY_ITEMS = 500


class ClickableLabel(QLabel):
    clicked = Signal()
    drag_started = Signal(QPoint)
    drag_moved = Signal(QPoint)
    drag_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._press_position: QPoint | None = None
        self._dragged = False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._press_position = event.position().toPoint()
            self._dragged = False
            self.drag_started.emit(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._press_position is not None
            and event.buttons() & Qt.LeftButton
            and (
                event.position().toPoint() - self._press_position
            ).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._dragged = True
        if event.buttons() & Qt.LeftButton:
            self.drag_moved.emit(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        release_position = event.position().toPoint()
        is_click = (
            event.button() == Qt.LeftButton
            and self._press_position is not None
            and not self._dragged
            and (
                release_position - self._press_position
            ).manhattanLength()
            < QApplication.startDragDistance()
        )
        self._press_position = None
        self._dragged = False
        self.drag_finished.emit()
        if is_click:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ZoomTextBrowser(QTextBrowser):
    zoom_step_requested = Signal(int)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.zoom_step_requested.emit(1 if delta > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)


class TodoRow(QFrame):
    changed = Signal()

    def __init__(self, db: PresentationDatabasePort, todo, language: str = "zh-TW"):
        super().__init__()
        self.setObjectName("todoCard")
        # A task card should keep its content height.  Letting QVBoxLayout
        # stretch every QFrame vertically makes cards overlap visually in a
        # tall or wide dashboard capture.
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.db = db
        self.todo_id = int(todo["id"])
        self.language = language
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 10, 9)
        layout.setSpacing(10)
        done = QCheckBox()
        done.setToolTip(
            ui_text(language, "todo_complete_tooltip", "標記為已完成")
        )
        done.setChecked(todo["status"] == "完成")
        text_column = QVBoxLayout()
        text_column.setSpacing(2)
        title = QLabel(str(todo["title"]))
        title.setObjectName("todoTitle")
        title.setWordWrap(True)
        category_value = str(todo["category"])
        category_key = dict(TODO_CATEGORIES).get(category_value)
        category_label = (
            ui_text(language, category_key, category_value)
            if category_key is not None
            else category_value
        )
        category = QLabel(
            f"{category_label} · "
            f"{ui_text(language, 'todo_category_suffix', '今日待辦')}"
        )
        category.setObjectName("todoCategory")
        delete = QPushButton(ui_text(language, "delete", "刪除"))
        delete.setToolTip(
            ui_text(language, "delete_todo_tooltip", "刪除這筆待辦")
        )
        delete.setFixedWidth(64)
        done.toggled.connect(self._toggle)
        delete.clicked.connect(self._delete)
        text_column.addWidget(title)
        text_column.addWidget(category)
        layout.addWidget(done)
        layout.addLayout(text_column, 1)
        layout.addWidget(delete)

    def _toggle(self, checked: bool) -> None:
        self.db.set_todo_done(self.todo_id, checked)
        self.changed.emit()

    def _delete(self) -> None:
        self.db.delete_todo(self.todo_id)
        self.changed.emit()


class IdeaEditorDialog(QDialog):
    def __init__(
        self,
        title: str,
        content: str,
        parent=None,
        *,
        language: str = "zh-TW",
    ):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(
            ui_text(language, "idea_editor_title", "編輯創作靈感")
        )
        self.setMinimumSize(560, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(ui_text(language, "idea_title", "<b>靈感標題</b>"))
        )
        self.title_input = QLineEdit(str(title))
        self.title_input.setPlaceholderText(
            ui_text(
                language,
                "idea_title_placeholder",
                "替這則靈感取一個清楚的標題",
            )
        )
        layout.addWidget(self.title_input)
        layout.addWidget(
            QLabel(ui_text(language, "idea_content", "<b>靈感內文</b>"))
        )
        self.content_input = QTextEdit()
        self.content_input.setPlainText(
            str(content)
        )
        self.content_input.setPlaceholderText(
            ui_text(
                language,
                "idea_content_placeholder",
                "記下情節、畫面、台詞、音樂方向或後續可執行的想法……",
            )
        )
        layout.addWidget(self.content_input, 1)
        buttons = QHBoxLayout()
        cancel = QPushButton(ui_text(language, "cancel", "取消"))
        save = QPushButton(ui_text(language, "save_idea", "保存靈感"))
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)

    def _save(self) -> None:
        if not self.title_input.text().strip():
            QMessageBox.information(
                self,
                ui_text(
                    self.language,
                    "idea_title_required_title",
                    "尚無標題",
                ),
                ui_text(
                    self.language,
                    "idea_title_required",
                    "請先填寫靈感標題。",
                ),
            )
            self.title_input.setFocus()
            return
        self.accept()

    def values(self) -> tuple[str, str]:
        return (
            self.title_input.text().strip(),
            self.content_input.toPlainText().strip(),
        )


class MemoryEditorDialog(QDialog):
    def __init__(
        self,
        memory,
        parent=None,
        *,
        language: str = "zh-TW",
    ):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(
            ui_text(language, "memory_editor_title", "編輯長期記憶")
        )
        self.setMinimumSize(620, 500)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                ui_text(language, "memory_title_label", "<b>記憶標題</b>")
            )
        )
        self.title_input = QLineEdit(
            str(memory["title"] or "")
        )
        self.title_input.setPlaceholderText(
            ui_text(
                language,
                "memory_title_placeholder",
                "用一句短標題辨識這則記憶",
            )
        )
        layout.addWidget(self.title_input)
        layout.addLayout(self._details_row(memory))

        layout.addWidget(
            QLabel(
                ui_text(language, "memory_content_label", "<b>記憶內容</b>")
            )
        )
        self.content_input = QTextEdit()
        self.content_input.setPlainText(
            str(memory["content"] or "")
        )
        self.content_input.setPlaceholderText(
            ui_text(
                language,
                "memory_content_placeholder",
                "完整記錄人物背景、偏好、目標、工作流程或重要日期……",
            )
        )
        layout.addWidget(self.content_input, 1)
        source_labels = {
            "manual": ui_text(
                language, "memory_source_manual", "手動建立"
            ),
            "conversation": ui_text(
                language,
                "memory_source_conversation",
                "由對話明確記住",
            ),
        }
        source = source_labels.get(
            str(memory["source"]), str(memory["source"])
        )
        meta = QLabel(
            ui_text(
                language,
                "memory_metadata",
                "來源：{source}　建立：{created}　更新：{updated}",
                source=source,
                created=str(memory["created_at"])[:16],
                updated=str(memory["updated_at"])[:16],
            )
        )
        meta.setStyleSheet("color:#4c6b82;")
        layout.addWidget(meta)
        buttons = QHBoxLayout()
        cancel = QPushButton(ui_text(language, "cancel", "取消"))
        save = QPushButton(ui_text(language, "save_memory", "保存記憶"))
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)

    def _details_row(self, memory) -> QHBoxLayout:
        details = QHBoxLayout()
        category_box = QVBoxLayout()
        category_box.addWidget(
            QLabel(
                ui_text(
                    self.language,
                    "memory_category_label",
                    "<b>類別</b>",
                )
            )
        )
        self.category_input = QComboBox()
        for category in MEMORY_CATEGORIES:
            self.category_input.addItem(
                memory_category_label(self.language, category), category
            )
        current_category = to_taiwan_traditional(str(memory["category"]))
        current_index = self.category_input.findData(current_category)
        if current_index < 0:
            self.category_input.addItem(
                current_category,
                current_category,
            )
            current_index = self.category_input.count() - 1
        self.category_input.setCurrentIndex(current_index)
        category_box.addWidget(self.category_input)

        importance_box = QVBoxLayout()
        importance_box.addWidget(
            QLabel(
                ui_text(
                    self.language,
                    "memory_importance_label",
                    "<b>重要度</b>",
                )
            )
        )
        self.importance_input = QSpinBox()
        self.importance_input.setRange(1, 5)
        self.importance_input.setValue(int(memory["importance"]))
        self.importance_input.setSuffix("／5")
        importance_box.addWidget(self.importance_input)
        details.addLayout(category_box, 1)
        details.addLayout(importance_box, 1)
        return details

    def _save(self) -> None:
        if not self.title_input.text().strip():
            QMessageBox.information(
                self,
                ui_text(
                    self.language,
                    "memory_title_required_title",
                    "尚無標題",
                ),
                ui_text(
                    self.language,
                    "memory_title_required",
                    "請先填寫記憶標題。",
                ),
            )
            self.title_input.setFocus()
            return
        if not self.content_input.toPlainText().strip():
            QMessageBox.information(
                self,
                ui_text(
                    self.language,
                    "memory_content_required_title",
                    "尚無內容",
                ),
                ui_text(
                    self.language,
                    "memory_content_required",
                    "請先填寫記憶內容。",
                ),
            )
            self.content_input.setFocus()
            return
        self.accept()

    def values(self) -> tuple[str, str, str, int]:
        return (
            self.title_input.text().strip(),
            self.content_input.toPlainText().strip(),
            str(self.category_input.currentData() or "其他"),
            self.importance_input.value(),
        )


class ArchivedMemoryDialog(QDialog):
    def __init__(
        self,
        db: PresentationDatabasePort,
        parent=None,
        *,
        language: str = "zh-TW",
    ):
        super().__init__(parent)
        self.db = db
        self.language = language
        self.changed = False
        self.setWindowTitle(
            ui_text(
                language,
                "archived_memory_title",
                "已封存的長期記憶",
            )
        )
        self.setMinimumSize(720, 520)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        intro = QLabel(
            ui_text(
                language,
                "archived_memory_intro",
                "自動整理只會封存較舊、低重要度的對話記憶，不會直接銷毀。"
                "您可以在這裡隨時勾選還原。",
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.archive_list = QListWidget()
        layout.addWidget(self.archive_list, 1)
        self.archive_status = QLabel()
        layout.addWidget(self.archive_status)
        buttons = QHBoxLayout()
        restore = QPushButton(
            ui_text(
                language,
                "restore_checked_memories",
                "還原勾選記憶",
            )
        )
        close = QPushButton(ui_text(language, "close", "關閉"))
        buttons.addWidget(restore)
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)
        restore.clicked.connect(self.restore_checked)
        close.clicked.connect(self.accept)
        self.refresh_archives()

    def refresh_archives(self) -> None:
        self.archive_list.clear()
        consume = getattr(self.db, "consume_corrupt_data_notifications", None)
        if callable(consume):
            messages = consume()
            if messages:
                QMessageBox.warning(
                    self,
                    ui_text(self.language, "corrupt_data_title", "資料讀取警告"),
                    "\n".join(
                        ui_text(self.language, "corrupt_data_message", message)
                        for message in messages
                    ),
                )
        rows = self.db.list_archived_memories(1000)
        for row in rows:
            if str(row.get("status", "ok")) == "corrupt":
                item = QListWidgetItem(
                    ui_text(
                        self.language,
                        "archived_memory_corrupt",
                        "【無法讀取】這筆封存記憶的原檔已保留。"
                        "\n封存原因：{reason}\u3000時間：{archived}",
                        reason=str(row["reason"]),
                        archived=str(row["archived_at"])[:16],
                    )
                )
                item.setFlags(Qt.NoItemFlags)
                self.archive_list.addItem(item)
                continue
            item = QListWidgetItem(
                ui_text(
                    self.language,
                    "archived_memory_item",
                    "【{category}】{title}\n{content}\n"
                    "封存原因：{reason}　時間：{archived}",
                    category=memory_category_label(
                        self.language,
                        to_taiwan_traditional(str(row["category"])),
                    ),
                    title=str(row["title"]),
                    content=str(row["content"]),
                    reason=str(row["reason"]),
                    archived=str(row["archived_at"])[:16],
                )
            )
            item.setData(Qt.UserRole, int(row["id"]))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.archive_list.addItem(item)
        self.archive_status.setText(
            ui_text(
                self.language,
                "archived_memory_count",
                "目前共有 {count} 則可還原記憶",
                count=len(rows),
            )
        )

    def restore_checked(self) -> None:
        selected = [
            int(self.archive_list.item(index).data(Qt.UserRole))
            for index in range(self.archive_list.count())
            if self.archive_list.item(index).checkState() == Qt.Checked
        ]
        if not selected:
            QMessageBox.information(
                self,
                ui_text(
                    self.language,
                    "archived_memory_select_title",
                    "尚未選取",
                ),
                ui_text(
                    self.language,
                    "archived_memory_select",
                    "請先勾選要還原的記憶。",
                ),
            )
            return
        restored = 0
        corrupt = 0
        for archive_id in selected:
            result = self.db.restore_archived_memory(archive_id)
            if isinstance(result, int) and result > 0:
                restored += 1
            elif str(getattr(result, "status", "")) == "corrupt":
                corrupt += 1
        self.changed = self.changed or restored > 0
        self.refresh_archives()
        status = ui_text(
            self.language,
            "archived_memory_restored",
            "已還原 {count} 則記憶。",
            count=restored,
        )
        if corrupt:
            status += "\n" + ui_text(
                self.language,
                "corrupt_data_message",
                "某項設定／記憶無法讀取，已保留原檔",
            )
        self.archive_status.setText(status)


class ChatHistoryDialog(QDialog):
    def __init__(
        self,
        db: PresentationDatabasePort,
        parent=None,
        *,
        language: str = "zh-TW",
    ):
        super().__init__(parent)
        self.db = db
        self.language = language
        self.changed = False
        self.setWindowTitle(
            ui_text(language, "chat_history_title", "管理／清除對話")
        )
        self.setMinimumSize(720, 520)
        layout = QVBoxLayout(self)
        intro = QLabel(
            ui_text(
                language,
                "chat_history_intro",
                "對話平時保存在本機，不會自動刪除。"
                "請只勾選確定要永久刪除的紀錄。",
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.history_list = QListWidget()
        layout.addWidget(self.history_list, 1)
        self.history_status = QLabel()
        self.history_status.setStyleSheet("color: #356d88;")
        layout.addWidget(self.history_status)
        buttons = QHBoxLayout()
        delete = QPushButton(
            ui_text(language, "delete_checked_chats", "刪除勾選對話")
        )
        close = QPushButton(ui_text(language, "close", "關閉"))
        buttons.addWidget(delete)
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)
        delete.clicked.connect(self.delete_checked)
        close.clicked.connect(self.accept)
        self.refresh_history()

    def refresh_history(self) -> None:
        self.history_list.clear()
        rows = self.db.chat_history(500)
        for row in rows:
            speaker = (
                profile_setting(self.db, "user_title")
                if row["role"] == "user"
                else profile_setting(self.db, "assistant_name")
            )
            content = " ".join(
                str(row["content"]).split()
            )
            if len(content) > CHAT_HISTORY_PREVIEW_LENGTH:
                content = content[:CHAT_HISTORY_PREVIEW_LENGTH] + "…"
            item = QListWidgetItem(
                ui_text(
                    self.language,
                    "chat_history_item",
                    "{created}｜{speaker}\n{content}",
                    created=row["created_at"][5:16],
                    speaker=speaker,
                    content=content,
                )
            )
            item.setData(Qt.UserRole, int(row["id"]))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setToolTip(str(row["content"]))
            self.history_list.addItem(item)
        total = self.db.chat_count()
        suffix = (
            ui_text(
                self.language,
                "chat_history_truncated_suffix",
                "（管理視窗最多顯示最近 500 則）",
            )
            if total > MAX_CHAT_HISTORY_ITEMS
            else ""
        )
        self.history_status.setText(
            ui_text(
                self.language,
                "chat_history_status",
                "本機共保存 {count} 則對話。{suffix}",
                count=total,
                suffix=suffix,
            )
        )

    def checked_chat_ids(self) -> list[int]:
        checked: list[int] = []
        for index in range(self.history_list.count()):
            item = self.history_list.item(index)
            if item.checkState() == Qt.Checked:
                checked.append(int(item.data(Qt.UserRole)))
        return checked

    def delete_checked(self) -> None:
        chat_ids = self.checked_chat_ids()
        if not chat_ids:
            QMessageBox.information(
                self,
                ui_text(
                    self.language,
                    "chat_select_delete_title",
                    "尚未勾選",
                ),
                ui_text(
                    self.language,
                    "chat_select_delete",
                    "請先勾選要刪除的對話。",
                ),
            )
            return
        answer = QMessageBox.question(
            self,
            ui_text(
                self.language,
                "chat_delete_title",
                "永久刪除對話",
            ),
            ui_text(
                self.language,
                "chat_delete_confirm",
                "確定永久刪除勾選的 {count} 則對話嗎？",
                count=len(chat_ids),
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.db.delete_chat_entries(chat_ids)
        self.changed = True
        self.refresh_history()
