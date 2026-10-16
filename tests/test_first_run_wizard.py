from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtGui import QPixmap
lazy from PySide6.QtWidgets import QApplication

lazy from domain.app_profile import profile_window_title
lazy from infrastructure.db import StudioDB
lazy from infrastructure.profile_transfer import PortableProfileManager
lazy from domain.constants import CHARACTER_ASSET_PATHS
lazy from presentation import first_run_wizard as wizard_module
lazy from presentation.first_run_wizard import FirstRunWizard


LANGUAGE_DEFAULTS = {
    "zh-TW": "墨寒",
    "zh-CN": "墨寒",
    "en": "MoHan",
    "ja-JP": "墨寒",
}


@pytest.fixture(scope="module")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("language, expected_name", LANGUAGE_DEFAULTS.items())
def test_fresh_install_uses_language_specific_identity_defaults(
    application: QApplication,
    tmp_path: Path,
    language: str,
    expected_name: str,
) -> None:
    database_path = tmp_path / f"fresh-{language}.db"
    db = StudioDB(database_path)
    db.set_setting("ui_language", language)
    wizard = FirstRunWizard(db)

    assert wizard.assistant_name.text() == expected_name
    assert wizard.wake_word.text() == expected_name
    assert wizard.window_title.text() == ""

    wizard._save()
    assert db.setting("assistant_name") == expected_name
    assert db.setting("wake_word") == expected_name
    assert db.setting("window_title") == ""
    assert profile_window_title(db) == expected_name
    wizard.close()
    db.close()

    reopened = StudioDB(database_path)
    assert reopened.setting("assistant_name") == expected_name
    assert reopened.setting("wake_word") == expected_name
    assert reopened.setting("window_title") == ""
    assert profile_window_title(reopened) == expected_name
    reopened.close()
    application.processEvents()


@pytest.mark.parametrize("language", LANGUAGE_DEFAULTS)
def test_existing_settings_remain_exactly_unchanged_after_reopen(
    application: QApplication,
    tmp_path: Path,
    language: str,
) -> None:
    database_path = tmp_path / f"existing-{language}.db"
    custom = {
        "assistant_name": f"Assistant-{language}",
        "user_title": f"User-{language}",
        "window_title": f"Window-{language}",
        "wake_word": f"Wake-{language}",
        "ui_language": language,
        "onboarding_complete": True,
    }
    db = StudioDB(database_path)
    for key, value in custom.items():
        db.set_setting(key, value)
    db.close()

    reopened = StudioDB(database_path)
    expected_snapshot = reopened.settings_snapshot()
    wizard = FirstRunWizard(reopened)
    for target_language in LANGUAGE_DEFAULTS:
        wizard.ui_language.setCurrentIndex(
            wizard.ui_language.findData(target_language)
        )
        application.processEvents()
        assert wizard.assistant_name.text() == custom["assistant_name"]
        assert wizard.user_title.text() == custom["user_title"]
        assert wizard.window_title.text() == custom["window_title"]
        assert wizard.wake_word.text() == custom["wake_word"]
    assert reopened.settings_snapshot() == expected_snapshot
    wizard.close()
    reopened.close()


def test_language_switch_replaces_only_unmodified_unsaved_defaults(
    application: QApplication,
    tmp_path: Path,
) -> None:
    db = StudioDB(tmp_path / "language-switch.db")
    wizard = FirstRunWizard(db)
    wizard.assistant_name.setText("Ava")
    wizard.window_title.setText("Ava Workspace")

    wizard.ui_language.setCurrentIndex(wizard.ui_language.findData("en"))
    application.processEvents()
    assert wizard.assistant_name.text() == "Ava"
    assert wizard.window_title.text() == "Ava Workspace"
    assert wizard.wake_word.text() == "MoHan"
    assert wizard.user_title.text() == "Commander"

    wizard.ui_language.setCurrentIndex(wizard.ui_language.findData("ja-JP"))
    application.processEvents()
    assert wizard.assistant_name.text() == "Ava"
    assert wizard.window_title.text() == "Ava Workspace"
    assert wizard.wake_word.text() == "墨寒"
    assert wizard.user_title.text() == "主様"
    wizard.close()
    db.close()


def test_persisted_builtin_spelling_is_not_treated_as_an_unsaved_default(
    application: QApplication,
    tmp_path: Path,
) -> None:
    db = StudioDB(tmp_path / "persisted-builtin-name.db")
    persisted = {
        "assistant_name": "MoHan",
        "user_title": "Commander",
        "window_title": "MoHan",
        "wake_word": "MoHan",
        "ui_language": "en",
        "onboarding_complete": False,
    }
    for key, value in persisted.items():
        db.set_setting(key, value)
    expected_snapshot = db.settings_snapshot()
    wizard = FirstRunWizard(db)

    wizard.ui_language.setCurrentIndex(wizard.ui_language.findData("zh-TW"))
    application.processEvents()
    assert wizard.assistant_name.text() == "MoHan"
    assert wizard.user_title.text() == "Commander"
    assert wizard.window_title.text() == "MoHan"
    assert wizard.wake_word.text() == "MoHan"
    assert db.settings_snapshot() == expected_snapshot
    wizard.close()
    db.close()


def test_manually_entered_builtin_spelling_remains_user_owned(
    application: QApplication,
    tmp_path: Path,
) -> None:
    db = StudioDB(tmp_path / "manual-builtin-name.db")
    wizard = FirstRunWizard(db)
    wizard.assistant_name.setText("MoHan")
    wizard.user_title.setText("Commander")
    wizard.window_title.setText("MoHan")
    wizard.wake_word.setText("MoHan")

    wizard.ui_language.setCurrentIndex(wizard.ui_language.findData("en"))
    wizard.ui_language.setCurrentIndex(wizard.ui_language.findData("zh-TW"))
    application.processEvents()
    assert wizard.assistant_name.text() == "MoHan"
    assert wizard.user_title.text() == "Commander"
    assert wizard.window_title.text() == "MoHan"
    assert wizard.wake_word.text() == "MoHan"
    wizard.close()
    db.close()


def test_imported_profile_is_not_rewritten_by_the_wizard(
    application: QApplication,
    tmp_path: Path,
) -> None:
    source_db = StudioDB(tmp_path / "source.db")
    imported_values = {
        "assistant_name": "Imported Assistant",
        "user_title": "Imported User",
        "window_title": "Imported Window",
        "wake_word": "Imported Wake",
        "ui_language": "en",
        "onboarding_complete": False,
    }
    for key, value in imported_values.items():
        source_db.set_setting(key, value)
    bundle, _manifest = PortableProfileManager(
        source_db,
        tmp_path / "source-backups",
    ).export_profile(tmp_path / "imported")

    target_db = StudioDB(tmp_path / "target.db")
    PortableProfileManager(
        target_db,
        tmp_path / "target-backups",
    ).import_profile(bundle)
    expected_snapshot = target_db.settings_snapshot()
    wizard = FirstRunWizard(target_db)
    wizard.ui_language.setCurrentIndex(wizard.ui_language.findData("zh-TW"))
    application.processEvents()

    assert wizard.assistant_name.text() == imported_values["assistant_name"]
    assert wizard.user_title.text() == imported_values["user_title"]
    assert wizard.window_title.text() == imported_values["window_title"]
    assert wizard.wake_word.text() == imported_values["wake_word"]
    assert target_db.settings_snapshot() == expected_snapshot
    wizard.close()
    source_db.close()
    target_db.close()


def test_body_pack_source_without_composed_portrait_never_uses_mohan_portrait(
    application: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    optional_path_calls: list[str] = []
    source = SimpleNamespace(
        appearance=SimpleNamespace(resolved_body_pack=object()),
        manifest=SimpleNamespace(body_pack=object()),
        assets=SimpleNamespace(
            resolve_optional_path=lambda path: optional_path_calls.append(path),
        ),
    )
    monkeypatch.setattr(wizard_module, "active_character_source", lambda: source)
    resource_requests: list[str] = []
    original_resource_path = wizard_module.resource_path

    def track_resource_path(path: str) -> Path:
        resource_requests.append(path)
        return original_resource_path(path)

    monkeypatch.setattr(wizard_module, "resource_path", track_resource_path)
    db = StudioDB(tmp_path / "body-pack-wizard.db")

    wizard = FirstRunWizard(db)

    assert wizard.hero_image.isHidden()
    assert optional_path_calls == []
    assert resource_requests == [CHARACTER_ASSET_PATHS["onboarding_artwork"]]
    wizard.close()
    db.close()
    application.processEvents()


def test_mohan_null_injected_pixmap_resolves_its_active_source_portrait(
    application: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    portrait = Path(__file__).resolve().parents[1] / CHARACTER_ASSET_PATHS["first_run_portrait"]
    path_calls: list[str] = []
    source = SimpleNamespace(
        appearance=SimpleNamespace(resolved_body_pack=None),
        manifest=SimpleNamespace(body_pack=None),
        assets=SimpleNamespace(
            resolve_optional_path=lambda path: path_calls.append(path) or portrait,
        ),
    )
    monkeypatch.setattr(wizard_module, "active_character_source", lambda: source)
    db = StudioDB(tmp_path / "mohan-null-pixmap-wizard.db")

    wizard = FirstRunWizard(db, appearance_pixmap=QPixmap())

    assert path_calls == [CHARACTER_ASSET_PATHS["first_run_portrait"]]
    assert wizard.hero_image.pixmap() is not None
    assert not wizard.hero_image.pixmap().isNull()
    wizard.close()
    db.close()
    application.processEvents()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
