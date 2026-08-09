from __future__ import annotations

lazy import subprocess
lazy from pathlib import Path

lazy from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal
lazy from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

lazy from updater import ReleaseInfo, UpdateError, UpdateManager
lazy from version_info import APP_VERSION, PROJECT_REPOSITORY


class _WorkerSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(int)


class _Worker(QRunnable):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            result = self.callback(self.signals.progress.emit)
        except (UpdateError, ValueError, OSError) as exc:
            self.signals.failed.emit(str(exc))
        else:
            self.signals.completed.emit(result)


class UpdatePanel(QWidget):
    def __init__(self, db, data_dir: Path, parent=None):
        super().__init__(parent)
        self.db = db
        self.manager = UpdateManager(
            PROJECT_REPOSITORY,
            APP_VERSION,
            data_dir / "updates",
        )
        self.thread_pool = QThreadPool.globalInstance()
        self.release: ReleaseInfo | None = None
        self.silent_check = False

        layout = QVBoxLayout(self)
        title = QLabel("<b>軟體更新</b>")
        self.current = QLabel(f"目前版本：{APP_VERSION}")
        row = QHBoxLayout()
        self.channel = QComboBox()
        self.channel.addItem("穩定版（建議）", "stable")
        self.channel.addItem("預覽版／RC", "preview")
        saved_channel = str(db.setting("update_channel", "stable"))
        self.channel.setCurrentIndex(
            max(0, self.channel.findData(saved_channel))
        )
        self.automatic = QCheckBox("啟動後自動檢查更新")
        self.automatic.setChecked(
            bool(db.setting("automatic_update_check", True))
        )
        self.check_button = QPushButton("立即檢查更新")
        self.download_button = QPushButton("下載並安裝")
        self.download_button.setEnabled(False)
        row.addWidget(QLabel("更新頻道"))
        row.addWidget(self.channel)
        row.addWidget(self.automatic)
        row.addStretch()
        row.addWidget(self.check_button)
        row.addWidget(self.download_button)
        self.status = QLabel("尚未檢查")
        self.status.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.notes = QTextBrowser()
        self.notes.setPlaceholderText("有新版本時會在此顯示 Release Notes。")
        self.notes.setMaximumHeight(150)
        layout.addWidget(title)
        layout.addWidget(self.current)
        layout.addLayout(row)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        layout.addWidget(self.notes)

        self.channel.currentIndexChanged.connect(self._save_preferences)
        self.automatic.toggled.connect(self._save_preferences)
        self.check_button.clicked.connect(self.check_updates)
        self.download_button.clicked.connect(self.download_update)
        self._automatic_check_started = False

    def start_automatic_check(self) -> None:
        if self._automatic_check_started or not self.automatic.isChecked():
            return
        self._automatic_check_started = True
        QTimer.singleShot(5_000, lambda: self.check_updates(silent=True))

    def _save_preferences(self) -> None:
        self.db.set_setting("update_channel", self.channel.currentData())
        self.db.set_setting(
            "automatic_update_check", self.automatic.isChecked()
        )

    def _set_busy(self, busy: bool) -> None:
        self.check_button.setEnabled(not busy)
        self.download_button.setEnabled(not busy and self.release is not None)

    def check_updates(self, _checked=False, silent: bool = False) -> None:
        self._save_preferences()
        self.silent_check = silent
        self.release = None
        self._set_busy(True)
        self.status.setText("正在安全地檢查 GitHub Release……")
        worker = _Worker(
            lambda _progress: self.manager.check(
                str(self.channel.currentData())
            )
        )
        worker.signals.completed.connect(self._check_completed)
        worker.signals.failed.connect(self._operation_failed)
        self.thread_pool.start(worker)

    def _check_completed(self, result) -> None:
        self.release = result if isinstance(result, ReleaseInfo) else None
        self._set_busy(False)
        if self.release is None:
            self.status.setText("目前已是此更新頻道的最新版本。")
            self.notes.clear()
            return
        self.status.setText(
            f"發現新版本 {self.release.version}；安裝前會驗證 SHA256。"
        )
        self.notes.setMarkdown(self.release.notes or "此版本未提供說明。")
        self.download_button.setEnabled(True)
        if not self.silent_check:
            QMessageBox.information(
                self,
                "發現墨寒新版本",
                f"新版本 {self.release.version} 已可下載。",
            )

    def download_update(self) -> None:
        if self.release is None:
            return
        asset = self.release.preferred_installer()
        answer = QMessageBox.question(
            self,
            "下載官方更新",
            "將從官方 GitHub Release 下載安裝程式，完成 SHA256 驗證後再啟動。\n\n"
            f"版本：{self.release.version}\n檔案：{asset.name}\n\n是否繼續？",
        )
        if answer != QMessageBox.Yes:
            return
        self._set_busy(True)
        self.progress.setVisible(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status.setText("正在下載並核對安裝程式……")

        def download(progress):
            return self.manager.download(
                asset,
                lambda received, total: progress(
                    min(100, int(received * 100 / total))
                ),
            )

        worker = _Worker(download)
        worker.signals.progress.connect(self.progress.setValue)
        worker.signals.completed.connect(self._download_completed)
        worker.signals.failed.connect(self._operation_failed)
        self.thread_pool.start(worker)

    def _download_completed(self, result) -> None:
        self._set_busy(False)
        self.progress.setValue(100)
        path = Path(result)
        answer = QMessageBox.question(
            self,
            "驗證完成",
            "SHA256 驗證通過。現在將關閉墨寒並開啟安裝程式。\n"
            "您的對話、記憶、待辦與設定仍保留在本機資料目錄。\n\n"
            "是否立即升級？",
        )
        if answer != QMessageBox.Yes:
            self.status.setText(f"已安全下載：{path}")
            return
        try:
            if path.suffix.lower() == ".msi":
                subprocess.Popen(["msiexec.exe", "/i", str(path)])
            else:
                subprocess.Popen([str(path)])
        except OSError as exc:
            self._operation_failed(f"無法啟動安裝程式：{exc}")
            return
        QTimer.singleShot(250, QApplication.quit)

    def _operation_failed(self, message: str) -> None:
        self._set_busy(False)
        self.progress.setVisible(False)
        self.status.setText(message)
        if not self.silent_check:
            QMessageBox.warning(self, "墨寒更新", message)
