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

lazy from auxiliary_ui_localization import (
    AuxiliaryOperation,
    AuxiliaryText,
    auxiliary_text,
    localized_operation_error,
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
    def __init__(
        self,
        db,
        data_dir: Path,
        parent=None,
        language: str = "zh-TW",
    ):
        super().__init__(parent)
        self.db = db
        self.language = language
        self.manager = UpdateManager(
            PROJECT_REPOSITORY,
            APP_VERSION,
            data_dir / "updates",
        )
        self.thread_pool = QThreadPool.globalInstance()
        self.release: ReleaseInfo | None = None
        self.silent_check = False

        layout = QVBoxLayout(self)
        self.title = QLabel(self._t(AuxiliaryText.UPDATE_TITLE))
        self.current = QLabel(
            self._t(AuxiliaryText.CURRENT_VERSION, version=APP_VERSION)
        )
        row = QHBoxLayout()
        self.channel = QComboBox()
        self.channel.addItem(self._t(AuxiliaryText.CHANNEL_STABLE), "stable")
        self.channel.addItem(self._t(AuxiliaryText.CHANNEL_PREVIEW), "preview")
        saved_channel = str(db.setting("update_channel", "stable"))
        self.channel.setCurrentIndex(
            max(0, self.channel.findData(saved_channel))
        )
        self.automatic = QCheckBox(self._t(AuxiliaryText.AUTO_CHECK))
        self.automatic.setChecked(
            bool(db.setting("automatic_update_check", True))
        )
        self.check_button = QPushButton(self._t(AuxiliaryText.CHECK_NOW))
        self.download_button = QPushButton(
            self._t(AuxiliaryText.DOWNLOAD_INSTALL)
        )
        self.download_button.setEnabled(False)
        self.channel_label = QLabel(self._t(AuxiliaryText.CHANNEL_LABEL))
        row.addWidget(self.channel_label)
        row.addWidget(self.channel)
        row.addWidget(self.automatic)
        row.addStretch()
        row.addWidget(self.check_button)
        row.addWidget(self.download_button)
        self.status = QLabel(self._t(AuxiliaryText.NOT_CHECKED))
        self.status.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.notes = QTextBrowser()
        self.notes.setPlaceholderText(
            self._t(AuxiliaryText.NOTES_PLACEHOLDER)
        )
        self.notes.setMaximumHeight(150)
        layout.addWidget(self.title)
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

    def _t(self, key: AuxiliaryText, **values: object) -> str:
        return auxiliary_text(self.language, key, **values)

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
        self.status.setText(self._t(AuxiliaryText.CHECKING))
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
            self.status.setText(self._t(AuxiliaryText.UP_TO_DATE))
            self.notes.clear()
            return
        self.status.setText(
            self._t(
                AuxiliaryText.NEW_VERSION,
                version=self.release.version,
            )
        )
        self.notes.setMarkdown(
            self.release.notes or self._t(AuxiliaryText.NO_RELEASE_NOTES)
        )
        self.download_button.setEnabled(True)
        if not self.silent_check:
            QMessageBox.information(
                self,
                self._t(AuxiliaryText.NEW_VERSION_TITLE),
                self._t(
                    AuxiliaryText.NEW_VERSION_AVAILABLE,
                    version=self.release.version,
                ),
            )

    def download_update(self) -> None:
        if self.release is None:
            return
        asset = self.release.preferred_installer()
        answer = QMessageBox.question(
            self,
            self._t(AuxiliaryText.DOWNLOAD_TITLE),
            self._t(
                AuxiliaryText.DOWNLOAD_PROMPT,
                version=self.release.version,
                filename=asset.name,
            ),
        )
        if answer != QMessageBox.Yes:
            return
        self._set_busy(True)
        self.progress.setVisible(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status.setText(self._t(AuxiliaryText.DOWNLOADING))

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
            self._t(AuxiliaryText.VERIFIED_TITLE),
            self._t(AuxiliaryText.VERIFIED_PROMPT),
        )
        if answer != QMessageBox.Yes:
            self.status.setText(
                self._t(AuxiliaryText.SAFE_DOWNLOADED, path=path)
            )
            return
        try:
            if path.suffix.lower() == ".msi":
                subprocess.Popen(["msiexec.exe", "/i", str(path)])
            else:
                subprocess.Popen([str(path)])
        except OSError:
            self._operation_failed(
                "",
                key=AuxiliaryText.INSTALLER_LAUNCH_FAILED,
            )
            return
        QTimer.singleShot(250, QApplication.quit)

    def _operation_failed(
        self,
        message: str,
        *,
        key: AuxiliaryText | None = None,
    ) -> None:
        self._set_busy(False)
        self.progress.setVisible(False)
        localized_message = (
            self._t(key)
            if key is not None
            else localized_operation_error(
                self.language,
                message,
                operation=AuxiliaryOperation.UPDATE,
            )
        )
        self.status.setText(localized_message)
        if not self.silent_check:
            QMessageBox.warning(
                self,
                self._t(AuxiliaryText.UPDATE_DIALOG_TITLE),
                localized_message,
            )
