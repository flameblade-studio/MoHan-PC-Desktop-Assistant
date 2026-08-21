from __future__ import annotations

lazy from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

lazy from domain.safe_error_localization import safe_error_message
lazy from infrastructure.backup_manager import BackupManager

__all__ = ("FlagshipOverviewMixin",)


class FlagshipOverviewMixin:
    def _overview_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel(self._t("<b>墨寒旗艦任務中心</b>"))
        title.setStyleSheet("font-size:18px;color:#2f6987;")
        note = QLabel(
            self._t(
                "所有電腦、雲端、遠端與智慧家庭操作都必須經過："
                "計畫 → 權限判斷 → 確認 → 執行 → 結果驗證 → 稽核。"
            )
        )
        note.setWordWrap(True)
        self.health_summary = QLabel()
        self.health_summary.setWordWrap(True)
        refresh = QPushButton(self._t("重新檢查系統狀態"))
        refresh.clicked.connect(self.refresh_health)
        backup = QPushButton(self._t("立即建立可驗證備份"))
        backup.clicked.connect(self.create_backup)
        task_label = QLabel(self._t("<b>自然語言工具任務</b>"))
        self.task_instruction = QLineEdit()
        self.task_instruction.setPlaceholderText(
            self._t("例如：幫我開啟工作資料夾，然後開啟指定工作網站")
        )
        self.plan_button = QPushButton(self._t("先產生安全計畫"))
        self.plan_button.clicked.connect(
            lambda: self.plan_instruction(
                self.task_instruction.text(),
                source="local",
            )
        )
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(self.health_summary)
        layout.addWidget(refresh)
        layout.addWidget(backup)
        layout.addSpacing(12)
        layout.addWidget(task_label)
        layout.addWidget(self.task_instruction)
        layout.addWidget(self.plan_button)
        layout.addStretch()
        self.refresh_health()
        return page

    def create_backup(self) -> None:
        try:
            target = BackupManager(
                self.db,
                self.data_path / "backups",
            ).create("manual")
        except Exception as exc:
            QMessageBox.warning(
                self,
                self._t("資料備份"),
                self._t(
                    "備份失敗：{error}",
                    error=safe_error_message(self.language, exc),
                ),
            )
            return
        QMessageBox.information(
            self,
            self._t("資料備份"),
            self._t(
                "備份與完整性雜湊已建立：\n{target}",
                target=target,
            ),
        )

    def refresh_health(self) -> None:
        workflow_count = len(self.db.workflows(enabled_only=True))
        paired_count = sum(bool(row["enabled"]) for row in self.db.paired_devices())
        ha = self.db.connector("home_assistant")
        ha_text = self._t("已啟用" if ha and bool(ha["enabled"]) else "未啟用")
        remote_text = self._t(
            "運作中" if self.remote_server and self.remote_server.running else "未啟用"
        )
        self.health_summary.setText(
            self._t(
                "Home Assistant：{home}\n遠端服務：{remote}\n"
                "已啟用工作流程：{workflows}\n有效配對裝置：{devices}\n"
                "安全狀態：高風險操作不允許免確認；任意命令列與付款永久禁止。",
                home=ha_text,
                remote=remote_text,
                workflows=workflow_count,
                devices=paired_count,
            )
        )
