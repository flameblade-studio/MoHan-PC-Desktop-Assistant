from __future__ import annotations

lazy import os
lazy import re
lazy import sys
lazy from pathlib import Path
lazy from string import Formatter
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6.QtWidgets import QApplication

lazy from presentation.auxiliary_ui_localization import (
    TRANSLATIONS,
    AuxiliaryText,
    auxiliary_text,
)
lazy from infrastructure.db import StudioDB
lazy from infrastructure.profile_transfer import ProfileTransferError
lazy from infrastructure.updater import ReleaseInfo
lazy from presentation.profile_transfer_ui import PortableProfilePanel
lazy from presentation.updater_ui import UpdatePanel

LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
MOJIBAKE = re.compile(r"(?:\ufffd|[ÃÂ]{2,}|(?:銝|隞|撠|雿|蝟|摰)[\ue000-\uf8ff])")
SENSITIVE_PROFILE_KEYS = (
    AuxiliaryText.INCLUDE_ENCRYPTED_SENSITIVE_DATA,
    AuxiliaryText.STRONG_PASSWORD,
    AuxiliaryText.CONFIRM_STRONG_PASSWORD,
    AuxiliaryText.SENSITIVE_DATA_WARNING,
    AuxiliaryText.PASSWORD_MISMATCH,
    AuxiliaryText.EXPORT_COMPLETE_WITH_SENSITIVE,
    AuxiliaryText.EXPORT_COMPLETE_WITHOUT_SENSITIVE,
    AuxiliaryText.IMPORT_ENCRYPTED_PASSWORD_PROMPT,
    AuxiliaryText.ENCRYPTED_CONTENT_AUTH_FAILED,
    AuxiliaryText.IMPORT_VISION_REMAINS_OFF,
    AuxiliaryText.SENSITIVE_DATA_RESTORED,
)


def format_fields(template: str) -> frozenset[str]:
    return frozenset(
        field_name
        for _literal, field_name, _format_spec, _conversion in Formatter().parse(
            template
        )
        if field_name is not None
    )


def assert_complete_translation_contract() -> None:
    expected = set(AuxiliaryText)
    assert tuple(TRANSLATIONS) == LANGUAGES
    for language in LANGUAGES:
        assert set(TRANSLATIONS[language]) == expected
        assert all(TRANSLATIONS[language].values())
        assert not MOJIBAKE.search(
            "\n".join(TRANSLATIONS[language][key] for key in SENSITIVE_PROFILE_KEYS)
        ), language
    for key in AuxiliaryText:
        fields = format_fields(TRANSLATIONS["zh-TW"][key])
        assert all(
            format_fields(TRANSLATIONS[language][key]) == fields
            for language in LANGUAGES
        ), key
        values = {field: f"<{field}>" for field in fields}
        for language in LANGUAGES:
            TRANSLATIONS[language][key].format(**values)
    english_contract = "\n".join(TRANSLATIONS["en"].values())
    assert not CJK.search(english_contract), english_contract
    for filename in (
        "presentation/updater_ui.py",
        "presentation/profile_transfer_ui.py",
    ):
        source = (ROOT / filename).read_text(encoding="utf-8")
        assert not CJK.search(source), filename


def assert_sensitive_profile_text_contract() -> None:
    for language in LANGUAGES:
        values = TRANSLATIONS[language]
        assert all(values[key].strip() for key in SENSITIVE_PROFILE_KEYS)

    # Public builds must describe sensitive export as optional and excluded by
    # default. UI state remains the responsibility of profile_transfer_ui.py.
    assert "選用" in auxiliary_text(
        "zh-TW", AuxiliaryText.INCLUDE_ENCRYPTED_SENSITIVE_DATA
    )
    assert "可选" in auxiliary_text(
        "zh-CN", AuxiliaryText.INCLUDE_ENCRYPTED_SENSITIVE_DATA
    )
    assert "optional" in auxiliary_text(
        "en", AuxiliaryText.INCLUDE_ENCRYPTED_SENSITIVE_DATA
    ).lower()
    assert "任意" in auxiliary_text(
        "ja-JP", AuxiliaryText.INCLUDE_ENCRYPTED_SENSITIVE_DATA
    )
    for language in LANGUAGES:
        note = auxiliary_text(language, AuxiliaryText.PROFILE_NOTE)
        warning = auxiliary_text(language, AuxiliaryText.SENSITIVE_DATA_WARNING)
        assert note
        assert warning
    assert "permissions" in auxiliary_text(
        "en", AuxiliaryText.SENSITIVE_DATA_WARNING
    )
    assert "local paths" in auxiliary_text(
        "en", AuxiliaryText.SENSITIVE_DATA_WARNING
    )
    assert "camera" in auxiliary_text(
        "en", AuxiliaryText.IMPORT_VISION_REMAINS_OFF
    ).lower()
    assert "face recognition" in auxiliary_text(
        "en", AuxiliaryText.IMPORT_VISION_REMAINS_OFF
    ).lower()


def visible_update_text(panel: UpdatePanel) -> tuple[str, ...]:
    return (
        panel.title.text(),
        panel.current.text(),
        panel.channel_label.text(),
        *(panel.channel.itemText(index) for index in range(panel.channel.count())),
        panel.automatic.text(),
        panel.check_button.text(),
        panel.download_button.text(),
        panel.status.text(),
        panel.notes.placeholderText(),
    )


def visible_profile_text(panel: PortableProfilePanel) -> tuple[str, ...]:
    return (
        panel.heading.text(),
        panel.note.text(),
        panel.export_button.text(),
        panel.import_button.text(),
    )


def assert_primary_controls(
    update_panel: UpdatePanel,
    profile_panel: PortableProfilePanel,
    language: str,
) -> None:
    assert update_panel.title.text() == auxiliary_text(
        language,
        AuxiliaryText.UPDATE_TITLE,
    )
    assert update_panel.channel.itemData(0) == "stable"
    assert update_panel.channel.itemData(1) == "preview"
    assert update_panel.check_button.text() == auxiliary_text(
        language,
        AuxiliaryText.CHECK_NOW,
    )
    assert update_panel.download_button.text() == auxiliary_text(
        language,
        AuxiliaryText.DOWNLOAD_INSTALL,
    )
    assert profile_panel.heading.text() == auxiliary_text(
        language,
        AuxiliaryText.PROFILE_HEADING,
    )
    assert profile_panel.export_button.text() == auxiliary_text(
        language,
        AuxiliaryText.EXPORT_BUTTON,
    )
    assert profile_panel.import_button.text() == auxiliary_text(
        language,
        AuxiliaryText.IMPORT_BUTTON,
    )


def assert_english_has_no_han_characters(
    update_panel: UpdatePanel,
    profile_panel: PortableProfilePanel,
) -> None:
    # Product names, versions, SHA256, GitHub, API, OAuth, and RC are Latin
    # identifiers and need no exception. English auxiliary UI must contain no
    # Han characters at all.
    english_text = visible_update_text(update_panel) + visible_profile_text(
        profile_panel
    )
    assert not CJK.search("\n".join(english_text)), english_text


def assert_update_runtime_messages(panel: UpdatePanel, language: str) -> None:
    panel.release = ReleaseInfo(
        version="4.0.0",
        tag="v4.0.0",
        release_url="https://github.com/example/release",
        notes="",
        published_at="2026-08-12T00:00:00Z",
        prerelease=False,
        installers=(),
    )
    with patch(
        "PySide6.QtWidgets.QMessageBox.information"
    ) as information:
        panel._check_completed(panel.release)
    assert panel.status.text() == auxiliary_text(
        language,
        AuxiliaryText.NEW_VERSION,
        version="4.0.0",
    )
    assert panel.notes.toPlainText() == auxiliary_text(
        language,
        AuxiliaryText.NO_RELEASE_NOTES,
    )
    assert information.call_args.args[1:] == (
        auxiliary_text(language, AuxiliaryText.NEW_VERSION_TITLE),
        auxiliary_text(
            language,
            AuxiliaryText.NEW_VERSION_AVAILABLE,
            version="4.0.0",
        ),
    )

    with patch(
        "PySide6.QtWidgets.QMessageBox.warning"
    ) as warning:
        panel._operation_failed("無法連線至 GitHub 更新服務。")
    source_failure = "無法連線至 GitHub 更新服務。"
    failure_text = (
        source_failure
        if language == "zh-TW"
        else auxiliary_text(
            language,
            AuxiliaryText.UPDATE_ERROR_CONNECTION,
        )
    )
    assert panel.status.text() == failure_text
    assert warning.call_args.args[1:] == (
        auxiliary_text(language, AuxiliaryText.UPDATE_DIALOG_TITLE),
        failure_text,
    )
    if language == "en":
        assert not CJK.search(failure_text)


def assert_profile_runtime_messages(
    panel: PortableProfilePanel,
    language: str,
) -> None:
    with (
        patch(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            return_value=("C:/portable.mohan-profile", ""),
        ),
        patch.object(
            panel.manager,
            "export_profile",
            side_effect=ProfileTransferError("攜帶檔雜湊驗證失敗"),
        ),
        patch("PySide6.QtWidgets.QMessageBox.warning") as warning,
    ):
        panel.export_profile()
    source_failure = "攜帶檔雜湊驗證失敗"
    expected_reason = (
        source_failure
        if language == "zh-TW"
        else auxiliary_text(
            language,
            AuxiliaryText.PROFILE_ERROR_SECURITY,
        )
    )
    assert warning.call_args.args[1:] == (
        auxiliary_text(language, AuxiliaryText.EXPORT_FAILED_TITLE),
        auxiliary_text(
            language,
            AuxiliaryText.EXPORT_FAILED,
            reason=expected_reason,
        ),
    )
    if language == "en":
        assert not CJK.search(
            "\n".join(str(value) for value in warning.call_args.args[1:])
        )


def assert_language(
    app: QApplication,
    db: StudioDB,
    root: Path,
    language: str,
) -> None:
    update_panel = UpdatePanel(db, root, language=language)
    profile_panel = PortableProfilePanel(db, language=language)
    try:
        assert_primary_controls(update_panel, profile_panel, language)
        if language == "en":
            assert_english_has_no_han_characters(update_panel, profile_panel)
        assert_update_runtime_messages(update_panel, language)
        assert_profile_runtime_messages(profile_panel, language)
    finally:
        update_panel.close()
        profile_panel.close()
        app.processEvents()


def assert_default_language_is_backward_compatible(
    db: StudioDB,
    root: Path,
) -> None:
    update_panel = UpdatePanel(db, root)
    profile_panel = PortableProfilePanel(db)
    try:
        assert update_panel.title.text() == "<b>軟體更新</b>"
        assert profile_panel.export_button.text() == "匯出墨寒攜帶檔"
    finally:
        update_panel.close()
        profile_panel.close()


def run() -> None:
    assert_complete_translation_contract()
    assert_sensitive_profile_text_contract()
    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        db = StudioDB(root / "mohan.db")
        try:
            for language in LANGUAGES:
                assert_language(app, db, root, language)
            assert_default_language_is_backward_compatible(db, root)
        finally:
            db.close()
    print("AUXILIARY_UI_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
