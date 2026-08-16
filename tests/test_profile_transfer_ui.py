from __future__ import annotations

lazy import json
lazy import os
lazy import sys
lazy import zipfile
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import Mock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox

lazy from auxiliary_ui_localization import AuxiliaryText, auxiliary_text
lazy from infrastructure.db import StudioDB
lazy from infrastructure.profile_transfer import (
    ProfileImportResult,
    ProfileManifest,
    ProfileTransferError,
)
lazy from profile_transfer_ui import (
    PortableProfilePanel,
    ProfileArchiveInspection,
    SensitiveProfileCallbacks,
    is_strong_profile_password,
)

LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")


def manifest() -> ProfileManifest:
    return ProfileManifest(
        created_at="2026-08-13T12:00:00+08:00",
        snapshot_id="a" * 32,
        source_installation_id="b" * 32,
        assistant_name="MoHan",
        organization_name="Flameblade Studio",
        record_counts=frozendict({"settings": 1}),
    )


def result(*, sensitive: bool = False) -> ProfileImportResult:
    return ProfileImportResult(
        manifest=manifest(),
        backup_path=Path("C:/backup.db"),
        imported_counts=frozendict({"settings": 1}),
        sensitive_payload=(
            frozendict({"format": "test", "secrets": {}})
            if sensitive
            else None
        ),
    )


def panel(
    db: StudioDB,
    *,
    language: str = "zh-TW",
    callbacks: SensitiveProfileCallbacks | None = None,
) -> PortableProfilePanel:
    return PortableProfilePanel(
        db,
        language=language,
        sensitive_callbacks=callbacks,
    )


def assert_panel_options_preserve_legacy_calls(db: StudioDB) -> None:
    callback = lambda: True
    callbacks = SensitiveProfileCallbacks(dict, lambda _payload: None)
    factory = Mock()
    factory.return_value = Mock()
    view = PortableProfilePanel(
        db,
        None,
        callback,
        "ja-JP",
        callbacks,
        factory,
    )
    try:
        assert view.before_export is callback
        assert view.language == "ja-JP"
        assert view.sensitive_callbacks is callbacks
        factory.assert_called_once_with(db, db.path.parent / "backups")
    finally:
        view.close()

    for create in (
        lambda: PortableProfilePanel(db, unexpected=True),
        lambda: PortableProfilePanel(db, None, callback, before_export=callback),
    ):
        try:
            create()
        except TypeError:
            pass
        else:
            raise AssertionError("invalid panel options were accepted")


def assert_default_opt_in_controls(db: StudioDB) -> None:
    for language in LANGUAGES:
        view = panel(db, language=language)
        try:
            assert not view.include_sensitive.isChecked()
            assert view.password_group.isHidden()
            assert view.password.echoMode() == QLineEdit.Password
            assert view.password_confirmation.echoMode() == QLineEdit.Password
            assert view.include_sensitive.text() == auxiliary_text(
                language,
                AuxiliaryText.INCLUDE_ENCRYPTED_SENSITIVE_DATA,
            )
            assert view.password.placeholderText() == auxiliary_text(
                language,
                AuxiliaryText.STRONG_PASSWORD,
            )
            assert view.password_confirmation.placeholderText() == auxiliary_text(
                language,
                AuxiliaryText.CONFIRM_STRONG_PASSWORD,
            )
            assert view.note.text() == auxiliary_text(
                language,
                AuxiliaryText.PROFILE_NOTE,
            )
            view.include_sensitive.setChecked(True)
            assert not view.password_group.isHidden()
            view.password.setText("temporary-password")
            view.include_sensitive.setChecked(False)
            assert view.password_group.isHidden()
            assert not view.password.text()
        finally:
            view.close()


def assert_password_rules() -> None:
    assert is_strong_profile_password("MoHan#2026Secure")
    assert not is_strong_profile_password("short")
    assert not is_strong_profile_password("onlylowercasepassword")


def assert_export_is_explicit_and_injected(db: StudioDB) -> None:
    collector = Mock(return_value={"format": "test", "secrets": {}})
    restorer = Mock()
    view = panel(
        db,
        callbacks=SensitiveProfileCallbacks(collector, restorer),
    )
    view.include_sensitive.setChecked(True)
    view.password.setText("MoHan#2026Secure")
    view.password_confirmation.setText("different")
    with (
        patch(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            return_value=("C:/portable.mohan-profile", ""),
        ),
        patch("PySide6.QtWidgets.QMessageBox.warning") as warning,
        patch.object(view.manager, "export_profile") as export_profile,
    ):
        view.export_profile()
    export_profile.assert_not_called()
    collector.assert_not_called()
    assert warning.call_args.args[2] == auxiliary_text(
        "zh-TW", AuxiliaryText.PASSWORD_MISMATCH
    )

    view.password.setText("MoHan#2026Secure")
    view.password_confirmation.setText("MoHan#2026Secure")
    export_profile = Mock(return_value=(Path("C:/portable.mohan-profile"), manifest()))
    with (
        patch(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            return_value=("C:/portable.mohan-profile", ""),
        ),
        patch.object(view.manager, "export_profile", export_profile),
        patch("PySide6.QtWidgets.QMessageBox.information") as information,
    ):
        view.export_profile()
    export_profile.assert_called_once_with(
        Path("C:/portable.mohan-profile"),
        sensitive_payload={"format": "test", "secrets": {}},
        password="MoHan#2026Secure",
    )
    collector.assert_called_once_with()
    assert "加密" in information.call_args.args[2]
    assert not view.password.text()
    assert not view.password_confirmation.text()
    view.close()


def assert_default_export_needs_no_password_or_callback(db: StudioDB) -> None:
    view = panel(db)
    exporter = Mock(
        return_value=(Path("C:/portable.mohan-profile"), manifest())
    )
    with (
        patch(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            return_value=("C:/portable.mohan-profile", ""),
        ),
        patch.object(view.manager, "export_profile", exporter),
        patch("PySide6.QtWidgets.QMessageBox.information") as information,
    ):
        view.export_profile()
    exporter.assert_called_once_with(
        Path("C:/portable.mohan-profile"),
        sensitive_payload=None,
        password=None,
    )
    assert "未包含" in information.call_args.args[2]
    view.close()


def assert_manifest_controls_password_prompt(db: StudioDB) -> None:
    callbacks = SensitiveProfileCallbacks(Mock(return_value={}), Mock())
    view = panel(db, callbacks=callbacks)
    import_result = result()
    with (
        patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("C:/portable.mohan-profile", ""),
        ),
        patch.object(
            view,
            "_inspect_archive",
            return_value=ProfileArchiveInspection(manifest(), False),
        ),
        patch.object(view, "_request_import_password") as password_prompt,
        patch(
            "PySide6.QtWidgets.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ),
        patch.object(
            view.manager,
            "import_profile",
            return_value=import_result,
        ) as importer,
        patch("PySide6.QtWidgets.QMessageBox.information"),
        patch(
            "presentation.profile_transfer_ui.QApplication.instance",
            return_value=None,
        ),
    ):
        view.import_profile()
    password_prompt.assert_not_called()
    importer.assert_called_once_with(
        Path("C:/portable.mohan-profile"),
        password=None,
    )
    view.close()


def assert_cancel_and_wrong_password_preserve_settings(db: StudioDB) -> None:
    callbacks = SensitiveProfileCallbacks(Mock(return_value={}), Mock())
    view = panel(db, callbacks=callbacks)
    db.set_setting("proof", "unchanged")
    original = db.settings_snapshot()
    with (
        patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("C:/portable.mohan-profile", ""),
        ),
        patch.object(
            view,
            "_inspect_archive",
            return_value=ProfileArchiveInspection(manifest(), True),
        ),
        patch.object(view, "_request_import_password", return_value=None),
        patch.object(view.manager, "import_profile") as importer,
    ):
        view.import_profile()
    importer.assert_not_called()
    assert db.settings_snapshot() == original

    def fail_import(*_args: object, **_kwargs: object) -> ProfileImportResult:
        db.set_setting("proof", "must roll back")
        raise ProfileTransferError("password or authentication failed")

    with (
        patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("C:/portable.mohan-profile", ""),
        ),
        patch.object(
            view,
            "_inspect_archive",
            return_value=ProfileArchiveInspection(manifest(), True),
        ),
        patch.object(
            view,
            "_request_import_password",
            return_value="Wrong#Password2026",
        ),
        patch(
            "PySide6.QtWidgets.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ),
        patch.object(view.manager, "import_profile", side_effect=fail_import),
        patch("PySide6.QtWidgets.QMessageBox.warning") as warning,
    ):
        view.import_profile()
    assert db.settings_snapshot() == original
    assert warning.call_args.args[2] == auxiliary_text(
        "zh-TW", AuxiliaryText.ENCRYPTED_CONTENT_AUTH_FAILED
    )
    view.close()


def assert_validation_failure_preserves_settings(db: StudioDB) -> None:
    view = panel(db)
    db.set_setting("validation-proof", "unchanged")
    original = db.settings_snapshot()

    def fail_inspection(_source: Path) -> ProfileArchiveInspection:
        db.set_setting("validation-proof", "must roll back")
        raise ProfileTransferError("archive validation failed")

    with (
        patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("C:/portable.mohan-profile", ""),
        ),
        patch.object(view, "_inspect_archive", side_effect=fail_inspection),
        patch("PySide6.QtWidgets.QMessageBox.warning"),
        patch.object(view.manager, "import_profile") as importer,
    ):
        view.import_profile()
    importer.assert_not_called()
    assert db.settings_snapshot() == original
    view.close()


def assert_sensitive_restore_and_vision_notice(db: StudioDB) -> None:
    restorer = Mock()
    view = panel(
        db,
        language="en",
        callbacks=SensitiveProfileCallbacks(Mock(return_value={}), restorer),
    )
    with (
        patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("C:/portable.mohan-profile", ""),
        ),
        patch.object(
            view,
            "_inspect_archive",
            return_value=ProfileArchiveInspection(manifest(), True),
        ),
        patch.object(
            view,
            "_request_import_password",
            return_value="MoHan#2026Secure",
        ),
        patch(
            "PySide6.QtWidgets.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ),
        patch.object(view.manager, "import_profile", return_value=result(sensitive=True)),
        patch("PySide6.QtWidgets.QMessageBox.information") as information,
        patch(
            "presentation.profile_transfer_ui.QApplication.instance",
            return_value=None,
        ),
    ):
        view.import_profile()
    restorer.assert_called_once()
    completion = information.call_args.args[2]
    assert "camera and face recognition remain off" in completion
    assert "restored securely" in completion
    view.close()


def assert_manifest_and_archive_must_agree() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        valid = root / "valid.mohan-profile"
        with zipfile.ZipFile(valid, "w") as archive:
            archive.writestr("manifest.json", json.dumps({"secrets_included": True}))
            archive.writestr("sensitive.enc", b"encrypted")
        assert PortableProfilePanel._archive_contains_sensitive(valid)

        missing = root / "missing.mohan-profile"
        with zipfile.ZipFile(missing, "w") as archive:
            archive.writestr("manifest.json", json.dumps({"secrets_included": True}))
        assert not PortableProfilePanel._archive_contains_sensitive(missing)


def run() -> None:
    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db = StudioDB(Path(temp) / "mohan.db")
        try:
            assert_panel_options_preserve_legacy_calls(db)
            assert_default_opt_in_controls(db)
            assert_password_rules()
            assert_export_is_explicit_and_injected(db)
            assert_default_export_needs_no_password_or_callback(db)
            assert_manifest_controls_password_prompt(db)
            assert_cancel_and_wrong_password_preserve_settings(db)
            assert_validation_failure_preserves_settings(db)
            assert_sensitive_restore_and_vision_notice(db)
            assert_manifest_and_archive_must_agree()
        finally:
            db.close()
    app.processEvents()
    print("PROFILE_TRANSFER_UI_OK")


if __name__ == "__main__":
    run()
