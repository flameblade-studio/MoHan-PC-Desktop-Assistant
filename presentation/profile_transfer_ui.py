from __future__ import annotations

lazy import json
lazy import sqlite3
lazy import zipfile
lazy from collections.abc import Callable, Mapping
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import TypedDict, Unpack, cast

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

lazy from application.presentation_ports import (
    MANIFEST_FILENAME,
    PROFILE_EXTENSION,
    SENSITIVE_FILENAME,
    SENSITIVE_MANIFEST_KEY,
    PortableProfileManagerFactory,
    ProfileImportResultPort,
    ProfileManifestPort,
    ProfileTransferError,
    safe_error_from_exception,
    unavailable_profile_manager_factory,
)
lazy from domain.contracts import ProfileDatabasePort
lazy from domain.safe_error import SafeError, sanitize_error
lazy from domain.time_utils import local_wall_time
lazy from presentation.auxiliary_ui_localization import (
    AuxiliaryOperation,
    AuxiliaryText,
    auxiliary_text,
    localized_operation_error,
)

__all__ = (
    "PortableProfilePanel",
    "PortableProfilePanelOptions",
    "ProfileArchiveInspection",
    "SensitiveProfileCallbacks",
    "is_strong_profile_password",
    "localized_profile_failure",
)

SensitiveCollector = Callable[[], Mapping[str, object]]
SensitiveRestorer = Callable[[Mapping[str, object]], None]


@dataclass(frozen=True, slots=True)
class SensitiveProfileCallbacks:
    """Injected sensitive-data boundary; the UI never owns secret stores."""

    collect: SensitiveCollector
    restore: SensitiveRestorer


class PortableProfilePanelOptions(TypedDict, total=False):
    """Typed keyword options for the portable-profile panel."""

    before_export: Callable[[], bool] | None
    language: str
    sensitive_callbacks: SensitiveProfileCallbacks | None
    manager_factory: PortableProfileManagerFactory | None


_PORTABLE_PROFILE_PANEL_OPTION_KEYS = frozenset(
    PortableProfilePanelOptions.__optional_keys__
)
_PORTABLE_PROFILE_PANEL_POSITIONAL_OPTIONS = (
    "before_export",
    "language",
    "sensitive_callbacks",
    "manager_factory",
)


def _resolve_profile_panel_options(
    positional: tuple[object, ...],
    keyword: PortableProfilePanelOptions,
) -> PortableProfilePanelOptions:
    if len(positional) > len(_PORTABLE_PROFILE_PANEL_POSITIONAL_OPTIONS):
        raise TypeError("PortableProfilePanel received too many positional options.")
    unknown_options = set(keyword) - _PORTABLE_PROFILE_PANEL_OPTION_KEYS
    if unknown_options:
        unexpected = min(unknown_options)
        raise TypeError(
            f"PortableProfilePanel received an unexpected option: {unexpected}"
        )
    resolved: dict[str, object] = dict(keyword)
    for index, option_value in enumerate(positional):
        option_name = _PORTABLE_PROFILE_PANEL_POSITIONAL_OPTIONS[index]
        if option_name in resolved:
            raise TypeError(
                f"PortableProfilePanel received the option twice: {option_name}"
            )
        resolved[option_name] = option_value
    return cast("PortableProfilePanelOptions", resolved)


@dataclass(frozen=True, slots=True)
class ProfileArchiveInspection:
    """Validated UI inspection result with explicit encrypted-content state."""

    manifest: ProfileManifestPort
    contains_sensitive: bool


def is_strong_profile_password(password: str) -> bool:
    """Require a practical local encryption password without retaining it."""

    categories = (
        any(character.islower() for character in password),
        any(character.isupper() for character in password),
        any(character.isdigit() for character in password),
        any(not character.isalnum() for character in password),
    )
    return len(password) >= 12 and sum(categories) >= 3


def localized_profile_failure(
    language: str,
    error: BaseException,
) -> str:
    """Return a four-language profile error without external error detail."""

    safe: SafeError | None = None
    safe = safe_error_from_exception(error)
    if isinstance(error, ProfileTransferError) or hasattr(error, "safe_error"):
        if safe is None:
            return localized_operation_error(
                language,
                str(error),
                operation=AuxiliaryOperation.PROFILE,
            )
    else:
        safe = sanitize_error(error)
    if safe is None:
        raise AssertionError("profile failure is missing safe metadata")
    return localized_operation_error(
        language,
        safe,
        operation=AuxiliaryOperation.PROFILE,
    )


class PortableProfilePanel(QWidget):
    """Self-contained UI for one-file profile handoff between computers."""

    def __init__(
        self,
        db: ProfileDatabasePort,
        parent: QWidget | None = None,
        *positional_options: object,
        **options: Unpack[PortableProfilePanelOptions],
    ) -> None:
        resolved = _resolve_profile_panel_options(positional_options, options)
        super().__init__(parent)
        self.db = db
        self.before_export = resolved.get("before_export")
        self.language = resolved.get("language", "zh-TW")
        self.sensitive_callbacks = resolved.get("sensitive_callbacks")
        factory = resolved.get("manager_factory") or unavailable_profile_manager_factory
        self.manager = factory(
            db,
            db.path.parent / "backups",
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.heading = QLabel(self._t(AuxiliaryText.PROFILE_HEADING))
        self.heading.setStyleSheet("color:#2f6987;font-size:15px;")
        self.note = QLabel(self._t(AuxiliaryText.PROFILE_NOTE))
        self.note.setWordWrap(True)
        self.include_sensitive = QCheckBox(
            self._t(AuxiliaryText.INCLUDE_ENCRYPTED_SENSITIVE_DATA)
        )
        self.include_sensitive.setChecked(False)
        self.sensitive_warning = QLabel(self._t(AuxiliaryText.SENSITIVE_DATA_WARNING))
        self.sensitive_warning.setWordWrap(True)
        self.sensitive_warning.setVisible(False)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText(self._t(AuxiliaryText.STRONG_PASSWORD))
        self.password_confirmation = QLineEdit()
        self.password_confirmation.setEchoMode(QLineEdit.Password)
        self.password_confirmation.setPlaceholderText(
            self._t(AuxiliaryText.CONFIRM_STRONG_PASSWORD)
        )
        self.password_group = QWidget()
        password_form = QFormLayout(self.password_group)
        password_form.setContentsMargins(0, 0, 0, 0)
        password_form.addRow(
            self._t(AuxiliaryText.STRONG_PASSWORD),
            self.password,
        )
        password_form.addRow(
            self._t(AuxiliaryText.CONFIRM_STRONG_PASSWORD),
            self.password_confirmation,
        )
        self.password_group.setVisible(False)
        buttons = QHBoxLayout()
        self.export_button = QPushButton(self._t(AuxiliaryText.EXPORT_BUTTON))
        self.import_button = QPushButton(self._t(AuxiliaryText.IMPORT_BUTTON))
        buttons.addWidget(self.export_button)
        buttons.addWidget(self.import_button)
        buttons.addStretch()
        layout.addWidget(self.heading)
        layout.addWidget(self.note)
        layout.addWidget(self.include_sensitive)
        layout.addWidget(self.sensitive_warning)
        layout.addWidget(self.password_group)
        layout.addLayout(buttons)
        self.include_sensitive.toggled.connect(self._set_sensitive_export_visible)
        self.export_button.clicked.connect(self.export_profile)
        self.import_button.clicked.connect(self.import_profile)

    def _t(self, key: AuxiliaryText, **values: object) -> str:
        return auxiliary_text(self.language, key, **values)

    def _profile_error(self, error: BaseException) -> str:
        return localized_profile_failure(self.language, error)

    def _show_failure(
        self,
        title: AuxiliaryText,
        message: AuxiliaryText,
        error: BaseException,
    ) -> None:
        QMessageBox.warning(
            self,
            self._t(title),
            self._t(message, reason=self._profile_error(error)),
        )

    def _set_sensitive_export_visible(self, visible: bool) -> None:
        self.sensitive_warning.setVisible(visible)
        self.password_group.setVisible(visible)
        if not visible:
            self._clear_password_fields()

    def _clear_password_fields(self) -> None:
        self.password.clear()
        self.password_confirmation.clear()

    def _export_sensitive_input(
        self,
    ) -> tuple[Mapping[str, object] | None, str | None] | None:
        if not self.include_sensitive.isChecked():
            return None, None
        password = self.password.text()
        if password != self.password_confirmation.text():
            QMessageBox.warning(
                self,
                self._t(AuxiliaryText.EXPORT_FAILED_TITLE),
                self._t(AuxiliaryText.PASSWORD_MISMATCH),
            )
            return None
        if not is_strong_profile_password(password):
            QMessageBox.warning(
                self,
                self._t(AuxiliaryText.EXPORT_FAILED_TITLE),
                self._t(AuxiliaryText.STRONG_PASSWORD)
                + "\n\n"
                + self._t(AuxiliaryText.SENSITIVE_DATA_WARNING),
            )
            return None
        if self.sensitive_callbacks is None:
            QMessageBox.warning(
                self,
                self._t(AuxiliaryText.EXPORT_FAILED_TITLE),
                self._t(AuxiliaryText.PROFILE_ERROR_SECURITY),
            )
            return None
        try:
            payload = self.sensitive_callbacks.collect()
        except RuntimeError as exc:
            self._show_failure(
                AuxiliaryText.EXPORT_FAILED_TITLE,
                AuxiliaryText.EXPORT_FAILED,
                exc,
            )
            return None
        return payload, password

    @staticmethod
    def _archive_contains_sensitive(source: Path) -> bool:
        """Read only the already-validated manifest's sensitive marker."""

        with zipfile.ZipFile(source, "r") as archive:
            payload = json.loads(archive.read(MANIFEST_FILENAME).decode("utf-8"))
            sensitive = payload.get(SENSITIVE_MANIFEST_KEY)
            manifest_marks_sensitive = payload.get("secrets_included") is True or (
                isinstance(sensitive, dict)
                and sensitive.get("included") is True
                and sensitive.get("encrypted") is True
                and sensitive.get("archive_member") == SENSITIVE_FILENAME
            )
            return manifest_marks_sensitive and SENSITIVE_FILENAME in archive.namelist()

    def _inspect_archive(self, source: Path) -> ProfileArchiveInspection:
        manifest, _database_path, temporary = self.manager.inspect_profile(source)
        try:
            contains_sensitive = self._archive_contains_sensitive(source)
        finally:
            temporary.cleanup()
        return ProfileArchiveInspection(manifest, contains_sensitive)

    def _request_import_password(self) -> str | None:
        password, accepted = QInputDialog.getText(
            self,
            self._t(AuxiliaryText.IMPORT_DIALOG_TITLE),
            self._t(AuxiliaryText.IMPORT_ENCRYPTED_PASSWORD_PROMPT),
            QLineEdit.Password,
        )
        return password if accepted and password else None

    def _settings_snapshot(self) -> Mapping[str, str] | None:
        snapshotter = getattr(self.db, "settings_snapshot", None)
        if not callable(snapshotter):
            return None
        snapshot = snapshotter()
        return snapshot if isinstance(snapshot, Mapping) else None

    def _restore_settings_snapshot(
        self,
        snapshot: Mapping[str, str] | None,
    ) -> None:
        if snapshot is None:
            return
        restorer = getattr(self.db, "restore_settings_snapshot", None)
        if callable(restorer):
            restorer(snapshot)

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
        sensitive_input = self._export_sensitive_input()
        if sensitive_input is None:
            return
        sensitive_payload, password = sensitive_input
        try:
            saved_path, manifest = self.manager.export_profile(
                Path(target),
                sensitive_payload=sensitive_payload,
                password=password,
            )
        except (OSError, sqlite3.Error, RuntimeError) as exc:
            self._show_failure(
                AuxiliaryText.EXPORT_FAILED_TITLE,
                AuxiliaryText.EXPORT_FAILED,
                exc,
            )
            return
        finally:
            self._clear_password_fields()
        total = sum(manifest.record_counts.values())
        complete_key = (
            AuxiliaryText.EXPORT_COMPLETE_WITH_SENSITIVE
            if sensitive_payload is not None
            else AuxiliaryText.EXPORT_COMPLETE_WITHOUT_SENSITIVE
        )
        QMessageBox.information(
            self,
            self._t(AuxiliaryText.EXPORT_COMPLETE_TITLE),
            self._t(
                complete_key,
                path=saved_path,
                count=total,
            ),
        )

    def import_profile(self) -> None:
        source = self._select_import_source()
        if source is None:
            return
        settings_snapshot = self._settings_snapshot()
        inspection = self._read_import_archive(source, settings_snapshot)
        if inspection is None:
            return
        proceed, import_password = self._import_password(
            inspection,
            settings_snapshot,
        )
        if not proceed or not self._confirm_import(inspection.manifest):
            self._restore_settings_snapshot(settings_snapshot)
            return
        result = self._run_import(
            source,
            import_password,
            inspection,
            settings_snapshot,
        )
        if result is None:
            return
        sensitive_restored = self._restore_imported_secrets(result)
        if sensitive_restored is None:
            return
        self._show_import_complete(result, sensitive_restored)

    def _select_import_source(self) -> Path | None:
        source, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self._t(AuxiliaryText.IMPORT_DIALOG_TITLE),
            str(Path.home() / "Documents"),
            self._t(
                AuxiliaryText.PROFILE_FILTER,
                extension=PROFILE_EXTENSION,
            ),
        )
        return Path(source) if source else None

    def _read_import_archive(
        self,
        source: Path,
        settings_snapshot: Mapping[str, str] | None,
    ) -> ProfileArchiveInspection | None:
        try:
            return self._inspect_archive(source)
        except (
            OSError,
            ValueError,
            sqlite3.Error,
            RuntimeError,
        ) as exc:
            self._restore_settings_snapshot(settings_snapshot)
            self._show_failure(
                AuxiliaryText.IMPORT_READ_FAILED_TITLE,
                AuxiliaryText.IMPORT_READ_FAILED,
                exc,
            )
            return None

    def _import_password(
        self,
        inspection: ProfileArchiveInspection,
        settings_snapshot: Mapping[str, str] | None,
    ) -> tuple[bool, str | None]:
        if not inspection.contains_sensitive:
            return True, None
        if self.sensitive_callbacks is None:
            self._restore_settings_snapshot(settings_snapshot)
            QMessageBox.warning(
                self,
                self._t(AuxiliaryText.IMPORT_READ_FAILED_TITLE),
                self._t(AuxiliaryText.PROFILE_ERROR_SECURITY),
            )
            return False, None
        password = self._request_import_password()
        return password is not None, password

    def _confirm_import(self, manifest: ProfileManifestPort) -> bool:
        total = sum(manifest.record_counts.values())
        source_label = (
            manifest.source_installation_id[:8]
            if manifest.source_installation_id
            else self._t(AuxiliaryText.LEGACY_SOURCE)
        )
        last_imported_at = str(self.db.setting("portable_last_import_created_at", ""))
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
                created_at=manifest.created_at or self._t(AuxiliaryText.UNKNOWN),
                source=source_label,
                assistant=manifest.assistant_name or self._t(AuxiliaryText.UNNAMED),
                count=total,
                older_warning=older_warning,
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def _run_import(
        self,
        source: Path,
        import_password: str | None,
        inspection: ProfileArchiveInspection,
        settings_snapshot: Mapping[str, str] | None,
    ) -> ProfileImportResultPort | None:
        try:
            return self.manager.import_profile(
                source,
                password=import_password,
            )
        except (
            OSError,
            ValueError,
            sqlite3.Error,
            RuntimeError,
        ) as exc:
            self._restore_settings_snapshot(settings_snapshot)
            if inspection.contains_sensitive:
                QMessageBox.warning(
                    self,
                    self._t(AuxiliaryText.IMPORT_FAILED_TITLE),
                    self._t(AuxiliaryText.ENCRYPTED_CONTENT_AUTH_FAILED),
                )
            else:
                self._show_failure(
                    AuxiliaryText.IMPORT_FAILED_TITLE,
                    AuxiliaryText.IMPORT_FAILED,
                    exc,
                )
            return None

    def _restore_imported_secrets(
        self,
        result: ProfileImportResultPort,
    ) -> bool | None:
        if result.sensitive_payload is None:
            return False
        try:
            self._restore_sensitive_result(result)
        except RuntimeError as exc:
            self._show_failure(
                AuxiliaryText.IMPORT_FAILED_TITLE,
                AuxiliaryText.IMPORT_FAILED,
                exc,
            )
            return None
        return True

    def _show_import_complete(
        self,
        result: ProfileImportResultPort,
        sensitive_restored: bool,
    ) -> None:
        completion = (
            self._t(
                AuxiliaryText.IMPORT_COMPLETE,
                path=result.backup_path,
            )
            + "\n\n"
            + self._t(AuxiliaryText.IMPORT_VISION_REMAINS_OFF)
        )
        if sensitive_restored:
            completion += "\n\n" + self._t(AuxiliaryText.SENSITIVE_DATA_RESTORED)
        QMessageBox.information(
            self,
            self._t(AuxiliaryText.IMPORT_COMPLETE_TITLE),
            completion,
        )
        application = QApplication.instance()
        if application is not None:
            QTimer.singleShot(0, application.quit)

    def _restore_sensitive_result(self, result: ProfileImportResultPort) -> None:
        if self.sensitive_callbacks is None:
            raise ProfileTransferError(
                "Sensitive-data restore callback is unavailable."
            )
        try:
            self.sensitive_callbacks.restore(result.sensitive_payload)
        except RuntimeError:
            try:
                self.manager.restore_import(result)
            except RuntimeError:
                raise ProfileTransferError(
                    "Sensitive-data restore and database rollback failed."
                ) from None
            raise ProfileTransferError(
                "Sensitive-data restore failed; database rollback completed."
            ) from None
