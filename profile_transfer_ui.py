from __future__ import annotations

lazy import sqlite3
lazy from collections.abc import Callable
lazy from pathlib import Path

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

lazy from contracts import ProfileDatabasePort
lazy from profile_transfer import (
    PROFILE_EXTENSION,
    PortableProfileManager,
    ProfileTransferError,
)
lazy from time_utils import local_wall_time


class PortableProfilePanel(QWidget):
    """Self-contained UI for one-file profile handoff between computers."""

    def __init__(
        self,
        db: ProfileDatabasePort,
        parent: QWidget | None = None,
        before_export: Callable[[], bool] | None = None,
    ):
        super().__init__(parent)
        self.db = db
        self.before_export = before_export
        self.manager = PortableProfileManager(
            db,
            db.path.parent / "backups",
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("<b>攜帶、換機與進度接續</b>")
        heading.setStyleSheet("color:#2f6987;font-size:15px;")
        note = QLabel(
            "匯出後只需攜帶一個檔案，即可在另一台電腦接續對話、"
            "記憶、待辦、靈感與工作進度。API 金鑰、OAuth、"
            "電腦權限、資料夾路徑與裝置設定不會被帶走。"
        )
        note.setWordWrap(True)
        buttons = QHBoxLayout()
        self.export_button = QPushButton("匯出墨寒攜帶檔")
        self.import_button = QPushButton("匯入並接續進度")
        buttons.addWidget(self.export_button)
        buttons.addWidget(self.import_button)
        buttons.addStretch()
        layout.addWidget(heading)
        layout.addWidget(note)
        layout.addLayout(buttons)
        self.export_button.clicked.connect(self.export_profile)
        self.import_button.clicked.connect(self.import_profile)

    def export_profile(self) -> None:
        if self.before_export is not None and not self.before_export():
            return
        assistant_name = str(
            self.db.setting("assistant_name", "墨寒")
        ).strip() or "墨寒"
        default_name = (
            f"{assistant_name}-攜帶進度-"
            f"{local_wall_time():%Y%m%d-%H%M%S}{PROFILE_EXTENSION}"
        )
        target, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "匯出墨寒攜帶檔",
            str(Path.home() / "Documents" / default_name),
            f"墨寒攜帶檔 (*{PROFILE_EXTENSION})",
        )
        if not target:
            return
        try:
            saved_path, manifest = self.manager.export_profile(Path(target))
        except (OSError, sqlite3.Error, ProfileTransferError) as exc:
            QMessageBox.warning(
                self,
                "匯出墨寒攜帶檔",
                f"匯出失敗：{exc}",
            )
            return
        total = sum(manifest.record_counts.values())
        QMessageBox.information(
            self,
            "匯出完成",
            "墨寒攜帶檔已建立。\n\n"
            f"位置：{saved_path}\n"
            f"收錄資料與設定共 {total} 筆。\n\n"
            "此檔案不含 API 金鑰、OAuth 權杖或本機電腦權限。",
        )

    def import_profile(self) -> None:
        source, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "匯入墨寒攜帶檔",
            str(Path.home() / "Documents"),
            f"墨寒攜帶檔 (*{PROFILE_EXTENSION})",
        )
        if not source:
            return
        try:
            manifest, _database_path, temporary = self.manager.inspect_profile(
                Path(source)
            )
            temporary.cleanup()
        except (
            OSError,
            ValueError,
            sqlite3.Error,
            ProfileTransferError,
        ) as exc:
            QMessageBox.warning(
                self,
                "匯入墨寒攜帶檔",
                f"無法讀取攜帶檔：{exc}",
            )
            return
        total = sum(manifest.record_counts.values())
        source_label = (
            manifest.source_installation_id[:8]
            if manifest.source_installation_id
            else "舊版攜帶檔"
        )
        last_imported_at = str(
            self.db.setting("portable_last_import_created_at", "")
        )
        older_warning = ""
        if (
            last_imported_at
            and manifest.created_at
            and manifest.created_at < last_imported_at
        ):
            older_warning = (
                "\n\n⚠ 此檔建立時間早於上次匯入的進度。"
                "若繼續，較新的共同進度可能被取代。"
            )
        answer = QMessageBox.question(
            self,
            "確認接續進度",
            "即將以攜帶檔內的共同進度取代這台電腦目前的"
            "對話、記憶、待辦與工作資料。\n\n"
            f"建立時間：{manifest.created_at or '未知'}\n"
            f"來源裝置識別：{source_label}\n"
            f"助理名稱：{manifest.assistant_name or '未命名'}\n"
            f"資料與設定：約 {total} 筆\n\n"
            "匯入前會自動備份目前資料；這台電腦的 API 金鑰、"
            "OAuth、權限、路徑與裝置設定將維持不變。"
            f"{older_warning}\n\n"
            "確定匯入嗎？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            result = self.manager.import_profile(Path(source))
        except (
            OSError,
            ValueError,
            sqlite3.Error,
            ProfileTransferError,
        ) as exc:
            QMessageBox.warning(
                self,
                "匯入墨寒攜帶檔",
                f"匯入失敗，原資料未變更：{exc}",
            )
            return
        QMessageBox.information(
            self,
            "進度接續完成",
            "墨寒的共同進度已匯入完成。\n\n"
            f"原資料備份：{result.backup_path}\n\n"
            "程式現在會安全關閉；請重新開啟墨寒，"
            "即可從匯入後的進度繼續使用。",
        )
        application = QApplication.instance()
        if application is not None:
            QTimer.singleShot(0, application.quit)
