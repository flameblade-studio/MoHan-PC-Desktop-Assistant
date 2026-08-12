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

lazy from auxiliary_ui_localization import (
    AuxiliaryOperation,
    AuxiliaryText,
    auxiliary_text,
    localized_operation_error,
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
        language: str = "zh-TW",
    ):
        super().__init__(parent)
        self.db = db
        self.before_export = before_export
        self.language = language
        self.manager = PortableProfileManager(
            db,
            db.path.parent / "backups",
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.heading = QLabel(self._t(AuxiliaryText.PROFILE_HEADING))
        self.heading.setStyleSheet("color:#2f6987;font-size:15px;")
        self.note = QLabel(self._t(AuxiliaryText.PROFILE_NOTE))
        self.note.setWordWrap(True)
        buttons = QHBoxLayout()
        self.export_button = QPushButton(self._t(AuxiliaryText.EXPORT_BUTTON))
        self.import_button = QPushButton(self._t(AuxiliaryText.IMPORT_BUTTON))
        buttons.addWidget(self.export_button)
        buttons.addWidget(self.import_button)
        buttons.addStretch()
        layout.addWidget(self.heading)
        layout.addWidget(self.note)
        layout.addLayout(buttons)
        self.export_button.clicked.connect(self.export_profile)
        self.import_button.clicked.connect(self.import_profile)

    def _t(self, key: AuxiliaryText, **values: object) -> str:
        return auxiliary_text(self.language, key, **values)

    def _profile_error(self, message: str) -> str:
        return localized_operation_error(
            self.language,
            message,
            operation=AuxiliaryOperation.PROFILE,
        )

    def export_profile(self) -> None:
        if self.before_export is not None and not self.before_export():
            return
        assistant_name = str(
            self.db.setting(
                "assistant_name",
                self._t(AuxiliaryText.DEFAULT_ASSISTANT_NAME),
            )
        ).strip() or self._t(AuxiliaryText.DEFAULT_ASSISTANT_NAME)
        default_name = self._t(
            AuxiliaryText.EXPORT_FILENAME,
            assistant=assistant_name,
            timestamp=f"{local_wall_time():%Y%m%d-%H%M%S}",
            extension=PROFILE_EXTENSION,
        )
        target, _selected_filter = QFileDialog.getSaveFileName(
            self,
            self._t(AuxiliaryText.EXPORT_DIALOG_TITLE),
            str(Path.home() / "Documents" / default_name),
            self._t(
                AuxiliaryText.PROFILE_FILTER,
                extension=PROFILE_EXTENSION,
            ),
        )
        if not target:
            return
        try:
            saved_path, manifest = self.manager.export_profile(Path(target))
        except (OSError, sqlite3.Error, ProfileTransferError) as exc:
            QMessageBox.warning(
                self,
                self._t(AuxiliaryText.EXPORT_FAILED_TITLE),
                self._t(
                    AuxiliaryText.EXPORT_FAILED,
                    reason=self._profile_error(str(exc)),
                ),
            )
            return
        total = sum(manifest.record_counts.values())
        QMessageBox.information(
            self,
            self._t(AuxiliaryText.EXPORT_COMPLETE_TITLE),
            self._t(
                AuxiliaryText.EXPORT_COMPLETE,
                path=saved_path,
                count=total,
            ),
        )

    def import_profile(self) -> None:
        source, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self._t(AuxiliaryText.IMPORT_DIALOG_TITLE),
            str(Path.home() / "Documents"),
            self._t(
                AuxiliaryText.PROFILE_FILTER,
                extension=PROFILE_EXTENSION,
            ),
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
                self._t(AuxiliaryText.IMPORT_READ_FAILED_TITLE),
                self._t(
                    AuxiliaryText.IMPORT_READ_FAILED,
                    reason=self._profile_error(str(exc)),
                ),
            )
            return
        total = sum(manifest.record_counts.values())
        source_label = (
            manifest.source_installation_id[:8]
            if manifest.source_installation_id
            else self._t(AuxiliaryText.LEGACY_SOURCE)
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
            older_warning = self._t(AuxiliaryText.OLDER_WARNING)
        answer = QMessageBox.question(
            self,
            self._t(AuxiliaryText.IMPORT_CONFIRM_TITLE),
            self._t(
                AuxiliaryText.IMPORT_CONFIRM,
                created_at=manifest.created_at
                or self._t(AuxiliaryText.UNKNOWN),
                source=source_label,
                assistant=manifest.assistant_name
                or self._t(AuxiliaryText.UNNAMED),
                count=total,
                older_warning=older_warning,
            ),
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
                self._t(AuxiliaryText.IMPORT_FAILED_TITLE),
                self._t(
                    AuxiliaryText.IMPORT_FAILED,
                    reason=self._profile_error(str(exc)),
                ),
            )
            return
        QMessageBox.information(
            self,
            self._t(AuxiliaryText.IMPORT_COMPLETE_TITLE),
            self._t(
                AuxiliaryText.IMPORT_COMPLETE,
                path=result.backup_path,
            ),
        )
        application = QApplication.instance()
        if application is not None:
            QTimer.singleShot(0, application.quit)
