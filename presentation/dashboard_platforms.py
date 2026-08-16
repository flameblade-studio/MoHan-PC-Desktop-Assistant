from __future__ import annotations

lazy import html
lazy import webbrowser
lazy from dataclasses import dataclass
lazy from datetime import datetime

lazy from PySide6.QtCore import Qt, QTimer
lazy from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

lazy from application.presentation_ports import PlatformProgressUpdate
lazy from domain.time_utils import local_wall_time
lazy from presentation.ui_localization import (
    PLATFORM_STATUS_LABELS,
    SIMPLIFIED_PLATFORM_STATUS_LABELS,
    display_label,
)
lazy from presentation.ui_localization_ja import JAPANESE_PLATFORM_STATUS_LABELS

__all__ = (
    "PLATFORM_STATUSES",
    "DashboardPlatformMixin",
    "PlatformCardControls",
    "platform_status_label",
)

PLATFORM_STATUSES = (
    "尚未開始",
    "準備資料",
    "進行中",
    "待送出",
    "等待回覆",
    "審核中",
    "需修正",
    "已排程",
    "已完成",
    "已上架",
    "暫停",
)


@dataclass(slots=True)
class PlatformCardControls:
    card: QFrame
    status: QComboBox
    item_name: QLineEdit
    missing: QLineEdit
    next_action: QLineEdit
    notes: QLineEdit
    url: QLineEdit
    validation: QLabel
    updated: QLabel
    save_button: QPushButton
    timer: QTimer
    dirty: bool = False

    @property
    def editors(self) -> tuple[QLineEdit, ...]:
        return (
            self.item_name,
            self.missing,
            self.next_action,
            self.notes,
            self.url,
        )


def platform_status_label(language: str, value: str) -> str:
    return display_label(
        language,
        value,
        PLATFORM_STATUS_LABELS,
        SIMPLIFIED_PLATFORM_STATUS_LABELS,
        JAPANESE_PLATFORM_STATUS_LABELS,
    )


class DashboardPlatformMixin:
    def _platform_add_controls(
        self,
    ) -> tuple[QHBoxLayout, QPushButton]:
        add_row = QHBoxLayout()
        self.new_platform_name = QLineEdit()
        self.new_platform_name.setPlaceholderText(
            self._t(
                "platform_name_placeholder",
                "平台、系統或工具名稱，例如：公司 ERP、Notion、客戶後台",
            )
        )
        self.new_platform_url = QLineEdit()
        self.new_platform_url.setPlaceholderText(
            self._t(
                "platform_url_placeholder",
                "網址（可留空，例如：https://example.com）",
            )
        )
        add_platform = QPushButton(
            self._t("add_platform", "新增工作平台")
        )
        add_row.addWidget(self.new_platform_name, 2)
        add_row.addWidget(self.new_platform_url, 2)
        add_row.addWidget(add_platform)
        return add_row, add_platform

    def _platform_filter_controls(
        self,
    ) -> tuple[QHBoxLayout, QPushButton]:
        header = QHBoxLayout()
        self.platform_summary = QLabel()
        self.platform_summary.setObjectName("sectionCount")
        self.platform_filter = QComboBox()
        for key, chinese, value in (
            ("platform_filter_all", "全部平台", "all"),
            ("platform_filter_active", "進行中", "active"),
            ("platform_filter_blocked", "待補資料／阻礙", "blocked"),
            ("platform_filter_finished", "已完成／已上架", "finished"),
            ("platform_filter_not_started", "尚未開始", "not_started"),
        ):
            self.platform_filter.addItem(self._t(key, chinese), value)
        save_all = QPushButton(
            self._t("save_all_platforms", "立即保存全部")
        )
        header.addWidget(self.platform_summary, 1)
        header.addWidget(QLabel(self._t("show", "顯示")))
        header.addWidget(self.platform_filter)
        header.addWidget(save_all)
        return header, save_all

    def _platform_card_scroll(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.platform_card_host = QWidget()
        self.platform_card_layout = QVBoxLayout(
            self.platform_card_host
        )
        self.platform_card_layout.setContentsMargins(0, 4, 6, 4)
        self.platform_card_layout.setSpacing(10)
        self.platform_controls: dict[str, PlatformCardControls] = {}
        self._platform_loading = False
        self.platform_empty = QLabel(
            self._t(
                "platform_empty",
                "尚未建立工作平台。\n"
                "請在上方輸入公司系統、協作工具、客戶後台或任何工作平台。",
            )
        )
        self.platform_empty.setObjectName("emptyState")
        self.platform_empty.setAlignment(Qt.AlignCenter)
        self.platform_empty.setWordWrap(True)
        self.platform_card_layout.addWidget(self.platform_empty)
        self.platform_card_layout.addStretch()
        scroll.setWidget(self.platform_card_host)
        return scroll

    def _platform_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        intro = QLabel(
            self._t(
                "platform_intro",
                "集中管理工作中使用的平台、系統、客戶入口或協作工具。"
                "每位使用者都可以建立自己的工作平台，不預設綁定任何產業。",
            )
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#486d83;")
        layout.addWidget(intro)
        add_row, add_platform = self._platform_add_controls()
        layout.addLayout(add_row)
        header, save_all = self._platform_filter_controls()
        self.platform_feedback = QLabel(
            self._t(
                "platform_auto_save_note",
                "修改後會自動保存；也可以使用每張卡片的保存按鈕。",
            )
        )
        self.platform_feedback.setStyleSheet("color:#4c6b82;")
        self.platform_feedback.setWordWrap(True)
        layout.addLayout(header)
        layout.addWidget(self.platform_feedback)
        layout.addWidget(self._platform_card_scroll(), 1)
        add_platform.clicked.connect(self.add_custom_platform)
        self.new_platform_name.returnPressed.connect(self.add_custom_platform)
        self.platform_filter.currentTextChanged.connect(
            self._filter_platform_cards
        )
        save_all.clicked.connect(lambda: self.save_platforms())
        self._reload_platform_cards()
        self._refresh_platform_summary()
        return tab

    def _create_platform_card(self, platform: str, row=None) -> None:
        controls, grid = self._build_platform_card_controls()
        self._populate_platform_card_grid(grid, platform, controls)
        self._connect_platform_card(platform, controls)
        self.platform_controls[platform] = controls
        self.platform_card_layout.insertWidget(
            max(0, self.platform_card_layout.count() - 1),
            controls.card,
        )
        if row is not None:
            self._load_platform_row(row)

    def _build_platform_card_controls(
        self,
    ) -> tuple[PlatformCardControls, QGridLayout]:
        card = QFrame()
        card.setObjectName("platformCard")
        card.setStyleSheet(
            "QFrame#platformCard{background:#f5f8fb;"
            "border:1px solid #c3d0dc;border-radius:12px;}"
        )
        grid = QGridLayout(card)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        status = QComboBox()
        for value in PLATFORM_STATUSES:
            status.addItem(platform_status_label(self.ui_language, value), value)
        controls = PlatformCardControls(
            card=card,
            status=status,
            item_name=self._platform_editor(
                self._t(
                    "platform_item_placeholder",
                    "目前負責的工作項目、專案或案件",
                )
            ),
            missing=self._platform_editor(
                self._t(
                    "platform_missing_placeholder",
                    "待補資料、等待他人回覆或其他阻礙；沒有可留空",
                )
            ),
            next_action=self._platform_editor(
                self._t("platform_next_placeholder", "下一個具體動作與期限")
            ),
            notes=self._platform_editor(
                self._t(
                    "platform_notes_placeholder",
                    "備註、規則、聯絡窗口或其他補充",
                )
            ),
            url=self._platform_editor(
                self._t("platform_url_card_placeholder", "https://…（可留空）")
            ),
            validation=QLabel(),
            updated=QLabel(self._t("platform_not_saved", "尚未保存")),
            save_button=QPushButton(self._t("save_platform", "保存此平台")),
            timer=QTimer(self),
        )
        controls.validation.setWordWrap(True)
        controls.updated.setStyleSheet("color:#64788a;font-size:11px;")
        controls.timer.setSingleShot(True)
        controls.timer.setInterval(750)
        return controls, grid

    @staticmethod
    def _platform_editor(placeholder: str) -> QLineEdit:
        editor = QLineEdit()
        editor.setPlaceholderText(placeholder)
        return editor

    def _populate_platform_card_grid(
        self,
        grid: QGridLayout,
        platform: str,
        controls: PlatformCardControls,
    ) -> None:
        name = QLabel(f"<b>{html.escape(platform)}</b>")
        name.setStyleSheet("font-size:15px;color:#17344f;")
        grid.addWidget(name, 0, 0)
        grid.addWidget(controls.status, 0, 1)
        grid.addWidget(controls.updated, 0, 2)
        grid.addLayout(
            self._platform_card_actions(platform, controls.save_button),
            0,
            3,
        )
        fields = (
            (self._t("platform_field_item", "工作項目／專案"), controls.item_name),
            (self._t("platform_field_missing", "待補資料／阻礙"), controls.missing),
            (self._t("platform_field_next", "下一步"), controls.next_action),
            (self._t("platform_field_notes", "備註"), controls.notes),
            (self._t("platform_field_url", "網址"), controls.url),
        )
        for row, (label, editor) in enumerate(fields, start=1):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(editor, row, 1, 1, 3)
        grid.addWidget(controls.validation, 6, 0, 1, 4)

    def _platform_card_actions(
        self,
        platform: str,
        save_button: QPushButton,
    ) -> QHBoxLayout:
        open_button = QPushButton(
            self._t("open_platform", "開啟網站／工具")
        )
        delete_button = QPushButton(
            self._t("delete_platform", "刪除平台")
        )
        delete_button.setObjectName("dangerButton")
        open_button.clicked.connect(
            lambda _checked=False, name=platform: self.open_platform(name)
        )
        delete_button.clicked.connect(
            lambda _checked=False, name=platform: (
                self.delete_custom_platform(name)
            )
        )
        actions = QHBoxLayout()
        for button in (open_button, save_button, delete_button):
            actions.addWidget(button)
        return actions

    def _connect_platform_card(
        self,
        platform: str,
        controls: PlatformCardControls,
    ) -> None:
        controls.status.currentTextChanged.connect(
            lambda _value, name=platform: self._platform_changed(name)
        )
        for editor in controls.editors:
            editor.textChanged.connect(
                lambda _value, name=platform: self._platform_changed(name)
            )
        controls.save_button.clicked.connect(
            lambda _checked=False, name=platform: self.save_platform(name)
        )
        controls.timer.timeout.connect(
            lambda name=platform: self.save_platform(name, silent=True)
        )

    def _load_platform_row(self, row) -> None:
        platform = row["platform"]
        controls = self.platform_controls.get(platform)
        if controls is None:
            return
        status = str(row["status"])
        if controls.status.findData(status) < 0:
            controls.status.addItem(
                platform_status_label(self.ui_language, status), status
            )
        controls.status.setCurrentIndex(
            max(0, controls.status.findData(status))
        )
        for field in ("item_name", "missing", "next_action", "notes", "url"):
            editor = getattr(controls, field)
            editor.setText(str(row[field] or ""))
        controls.dirty = False
        controls.save_button.setText(
            self._t("save_platform", "保存此平台")
        )
        controls.updated.setText(
            self._format_platform_updated(row["updated_at"])
        )
        self._validate_platform(platform)

    def _clear_platform_cards(self) -> None:
        for controls in self.platform_controls.values():
            controls.timer.stop()
            controls.card.deleteLater()
        self.platform_controls.clear()

    def _reload_platform_cards(self) -> None:
        self._platform_loading = True
        try:
            self._clear_platform_cards()
            for row in self.db.platform_rows():
                self._create_platform_card(row["platform"], row)
        finally:
            self._platform_loading = False
        self.platform_empty.setVisible(not self.platform_controls)
        self._refresh_platform_summary()
        self._filter_platform_cards()

    @staticmethod
    def _normalize_platform_url(value: str) -> str:
        value = value.strip()
        if value and "://" not in value:
            value = "https://" + value
        return value

    def add_custom_platform(self) -> None:
        platform = self.new_platform_name.text().strip()
        url = self._normalize_platform_url(self.new_platform_url.text())
        if not platform:
            self.platform_feedback.setText(
                self._t(
                    "platform_name_required",
                    "請先輸入平台、系統或工具名稱。",
                )
            )
            self.new_platform_name.setFocus()
            return
        if not self.db.add_platform(platform, url):
            self.platform_feedback.setText(
                self._t(
                    "platform_duplicate",
                    "「{platform}」已存在，請使用不同名稱。",
                    platform=platform,
                )
            )
            return
        row = next(
            row
            for row in self.db.platform_rows()
            if row["platform"].casefold() == platform.casefold()
        )
        self._platform_loading = True
        try:
            self._create_platform_card(row["platform"], row)
        finally:
            self._platform_loading = False
        self.new_platform_name.clear()
        self.new_platform_url.clear()
        self.platform_empty.hide()
        self.platform_feedback.setText(
            self._t(
                "platform_added",
                "已新增工作平台：{platform}",
                platform=platform,
            )
        )
        self._refresh_platform_summary()
        self._filter_platform_cards()

    def delete_custom_platform(self, platform: str) -> None:
        answer = QMessageBox.question(
            self,
            self._t("platform_delete_title", "刪除工作平台"),
            self._t(
                "platform_delete_confirm",
                "確定刪除「{platform}」及其工作進度嗎？此動作無法復原。",
                platform=platform,
            ),
        )
        if answer != QMessageBox.Yes:
            return
        controls = self.platform_controls.get(platform)
        if controls is not None:
            controls.timer.stop()
        if not self.db.delete_platform(platform):
            self.platform_feedback.setText(
                self._t(
                    "platform_not_found",
                    "找不到工作平台：{platform}",
                    platform=platform,
                )
            )
            return
        if controls is not None:
            controls.card.deleteLater()
            del self.platform_controls[platform]
        self.platform_empty.setVisible(not self.platform_controls)
        self.platform_feedback.setText(
            self._t(
                "platform_deleted",
                "已刪除工作平台：{platform}",
                platform=platform,
            )
        )
        self._refresh_platform_summary()
        self._filter_platform_cards()

    def _format_platform_updated(self, value: str) -> str:
        try:
            updated = datetime.fromisoformat(value)
            return self._t(
                "platform_updated",
                "更新：{updated}",
                updated=f"{updated:%m/%d %H:%M}",
            )
        except (TypeError, ValueError):
            return self._t(
                "platform_updated_unknown",
                "更新時間不明",
            )

    def _platform_update(self, platform: str) -> PlatformProgressUpdate:
        controls = self.platform_controls[platform]
        return PlatformProgressUpdate(
            platform=platform,
            status=str(
                controls.status.currentData()
                or controls.status.currentText()
            ),
            item_name=controls.item_name.text(),
            missing=controls.missing.text(),
            next_action=controls.next_action.text(),
            notes=controls.notes.text(),
            url=self._normalize_platform_url(controls.url.text()),
        )

    def _platform_changed(self, platform: str) -> None:
        if self._platform_loading:
            return
        controls = self.platform_controls[platform]
        controls.dirty = True
        controls.save_button.setText(
            self._t("save_changes", "保存變更")
        )
        controls.updated.setText(
            self._t("platform_not_saved", "尚未保存")
        )
        controls.timer.start()
        self.platform_feedback.setText(
            self._t(
                "platform_waiting_auto_save",
                "{platform} 有變更，正在等待自動保存……",
                platform=platform,
            )
        )
        self._validate_platform(platform)
        self._refresh_platform_summary()
        self._filter_platform_cards()

    def _validate_platform(self, platform: str) -> None:
        controls = self.platform_controls[platform]
        status = str(
            controls.status.currentData()
            or controls.status.currentText()
        )
        missing = controls.missing.text().strip()
        next_action = controls.next_action.text().strip()
        item_name = controls.item_name.text().strip()
        notes = controls.notes.text().strip()
        message = ""
        color = "#efc27f"
        if status in {"已完成", "已上架"} and missing:
            message = self._t(
                "platform_validation_finished_blocked",
                "注意：工作已完成，但仍列有待補資料或阻礙。",
            )
        elif status == "需修正" and not (missing or next_action or notes):
            message = self._t(
                "platform_validation_revision_details",
                "請在待補資料／阻礙、下一步或備註中寫明需修正的內容。",
            )
        elif status == "尚未開始" and any(
            (item_name, missing, next_action, notes)
        ):
            message = self._t(
                "platform_validation_not_started_data",
                "已有工作資料，請確認狀態是否應改為「準備資料」。",
            )
        elif status in {
            "待送出",
            "等待回覆",
            "審核中",
            "已排程",
            "已完成",
            "已上架",
        } and not item_name:
            message = self._t(
                "platform_validation_item_name",
                "建議填寫工作項目、專案或案件名稱，日後較容易辨認。",
            )
            color = "#356f8d"
        controls.validation.setText(message)
        controls.validation.setStyleSheet(f"color:{color};")

    def _refresh_platform_summary(self) -> None:
        if not hasattr(self, "platform_controls"):
            return
        statuses = [
            str(controls.status.currentData() or controls.status.currentText())
            for controls in self.platform_controls.values()
        ]
        missing_count = sum(
            bool(controls.missing.text().strip())
            for controls in self.platform_controls.values()
        )
        dirty_count = sum(
            controls.dirty
            for controls in self.platform_controls.values()
        )
        finished = sum(
            status in {"已完成", "已上架"} for status in statuses
        )
        not_started = statuses.count("尚未開始")
        in_progress = len(statuses) - finished - not_started
        dirty_text = (
            self._t(
                "platform_summary_unsaved",
                "｜未保存 {count}",
                count=dirty_count,
            )
            if dirty_count
            else ""
        )
        self.platform_summary.setText(
            self._t(
                "platform_summary",
                "{total} 個平台｜已完成 {finished}｜進行中 {active}｜"
                "尚未開始 {not_started}｜待補／阻礙 {blocked}{unsaved}",
                total=len(statuses),
                finished=finished,
                active=in_progress,
                not_started=not_started,
                blocked=missing_count,
                unsaved=dirty_text,
            )
        )

    def _filter_platform_cards(self, _value: str = "") -> None:
        if not hasattr(self, "platform_filter"):
            return
        selected = str(
            self.platform_filter.currentData()
            or self.platform_filter.currentText()
        )
        for controls in self.platform_controls.values():
            status = str(
                controls.status.currentData()
                or controls.status.currentText()
            )
            has_missing = bool(controls.missing.text().strip())
            visible = (
                selected == "all"
                or selected == "active"
                and status not in {"尚未開始", "已完成", "已上架"}
                or selected == "blocked"
                and has_missing
                or selected == "finished"
                and status in {"已完成", "已上架"}
                or selected == "not_started"
                and status == "尚未開始"
            )
            controls.card.setVisible(visible)

    def save_platform(self, platform: str, silent: bool = False) -> None:
        controls = self.platform_controls[platform]
        controls.timer.stop()
        self.db.update_platforms([self._platform_update(platform)])
        controls.dirty = False
        controls.save_button.setText(
            self._t("save_platform", "保存此平台")
        )
        controls.updated.setText(
            self._format_platform_updated(
                local_wall_time().isoformat(timespec="seconds")
            )
        )
        self._validate_platform(platform)
        self._refresh_platform_summary()
        self.platform_feedback.setText(
            self._t(
                "platform_saved_automatic" if silent else "platform_saved",
                "{platform} 已自動保存。" if silent else "{platform} 已保存。",
                platform=platform,
            )
        )

    def save_platforms(self, silent: bool = False) -> None:
        entries = []
        for platform, controls in self.platform_controls.items():
            controls.timer.stop()
            entries.append(self._platform_update(platform))
        self.db.update_platforms(entries)
        now = local_wall_time().isoformat(timespec="seconds")
        for platform, controls in self.platform_controls.items():
            controls.dirty = False
            controls.save_button.setText(
                self._t("save_platform", "保存此平台")
            )
            controls.updated.setText(
                self._format_platform_updated(now)
            )
            self._validate_platform(platform)
        self._refresh_platform_summary()
        missing_count = sum(
            bool(controls.missing.text().strip())
            for controls in self.platform_controls.values()
        )
        self.platform_feedback.setText(
            self._t(
                "all_platforms_saved",
                "全部工作平台已保存；{count} 個平台仍列有待補資料或阻礙。",
                count=missing_count,
            )
        )
        if not silent:
            self.speak_requested.emit(
                self._t(
                    "all_platforms_saved_speech",
                    "工作平台已保存。仍有 {count} 個平台標有待補資料或阻礙。",
                    count=missing_count,
                ),
                "happy",
            )

    def open_platform(self, platform: str) -> None:
        controls = self.platform_controls.get(platform)
        url = (
            self._normalize_platform_url(controls.url.text())
            if controls is not None
            else ""
        )
        if not url:
            row = next(
                (
                    row
                    for row in self.db.platform_rows()
                    if row["platform"] == platform
                ),
                None,
            )
            url = self._normalize_platform_url(row["url"] if row else "")
        if not url:
            QMessageBox.information(
                self,
                self._t(
                    "platform_url_missing_title",
                    "尚未設定網址",
                ),
                self._t(
                    "platform_url_missing",
                    "請先在「{platform}」卡片填入網站或工具網址。",
                    platform=platform,
                ),
            )
            return
        if not url.lower().startswith(("https://", "http://")):
            QMessageBox.warning(
                self,
                self._t(
                    "platform_url_unsupported_title",
                    "網址格式不支援",
                ),
                self._t(
                    "platform_url_unsupported",
                    "只允許開啟 http:// 或 https:// 網址。",
                ),
            )
            return
        action = self._t(
            "permission_open_platform",
            "開啟 {platform} 網站",
            platform=platform,
        )
        if self._permission_allowed("open_web", action):
            webbrowser.open(url)
