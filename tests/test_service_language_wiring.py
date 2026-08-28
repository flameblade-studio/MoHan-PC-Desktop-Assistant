from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

lazy from infrastructure.db import StudioDB
lazy from infrastructure.platform_contracts import PlatformCapabilities, PlatformPaths
lazy from application.service_container import create_default_services

UI_LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
TEST_SECRETS = (
    "openai-service-language-test-key",
    "azure-service-language-test-key",
    "azure-hd-service-language-test-key",
)


class _WindowsPlatformProbe:
    capabilities = PlatformCapabilities(
        platform_id="windows-test",
        display_name="Windows Test",
        system_local_speech=True,
        verified_female_voice_catalog=True,
        offline_speech_recognition=True,
        secure_secret_storage=True,
        desktop_autostart=False,
        native_window_management=False,
        published_installers=(),
    )

    def __init__(self, root: Path) -> None:
        self.paths = PlatformPaths(root, root, root / "cache")

    def set_autostart(
        self,
        enabled: bool,
        *,
        application_id: str,
        command: str,
    ) -> None:
        del enabled, application_id, command

    def open_path(self, path: Path) -> None:
        del path


class _SecretStoreProbe:
    def __init__(self, path: Path, value: str) -> None:
        self.path = path
        self.value = value

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""

    def __repr__(self) -> str:
        return f"_SecretStoreProbe(value={self.value!r})"


class _SecretStoreFactoryProbe:
    def __init__(self) -> None:
        self.created: list[_SecretStoreProbe] = []

    def __call__(
        self,
        path: Path,
        description: str = "MoHan protected secret",
    ) -> _SecretStoreProbe:
        del description
        value = TEST_SECRETS[len(self.created)]
        store = _SecretStoreProbe(path, value)
        self.created.append(store)
        return store

    def __repr__(self) -> str:
        return f"_SecretStoreFactoryProbe(secrets={TEST_SECRETS!r})"


class _BackupManagerProbe:
    def __init__(self, _db, _backup_dir: Path) -> None:
        return None

    def automatic_if_due(self) -> None:
        return None


def _assert_language_wiring(
    root: Path,
    language: str | None,
    expected: str,
    *,
    saved_language: str | None = None,
) -> None:
    if language is not None and saved_language is not None:
        case_name = f"saved-{saved_language}-explicit-{language}"
    elif language is not None:
        case_name = f"explicit-{language}"
    elif saved_language is not None:
        case_name = f"saved-{saved_language}"
    else:
        case_name = "default"
    data_path = root / case_name
    if saved_language is not None:
        db = StudioDB(data_path / "mohan.db")
        db.set_setting("ui_language", saved_language)
        db.close()
    factory = _SecretStoreFactoryProbe()
    kwargs = {} if language is None else {"ui_language": language}
    opened_databases: list[StudioDB] = []

    def open_database(path: Path) -> StudioDB:
        db = StudioDB(path)
        opened_databases.append(db)
        return db

    with (
        patch("application.service_container.StudioDB", side_effect=open_database),
        patch(
            "application.service_container.platform_secret_store_factory",
            return_value=factory,
        ),
        patch("application.service_container.BackupManager", _BackupManagerProbe),
    ):
        services = create_default_services(
            data_path,
            PROJECT / "voice_listener.ps1",
            platform_services=_WindowsPlatformProbe(root),
            **kwargs,
        )

    assert opened_databases == [services.db]
    assert services.local_tts.language == expected
    assert services.cloud_tts.language == expected
    assert services.listener.language == expected
    assert services.realtime_speech_output is not None
    assert services.realtime_speech_output._local_speech.language == expected

    rendered = repr(services)
    assert all(secret not in rendered for secret in TEST_SECRETS)
    for path in data_path.rglob("*"):
        if path.is_file():
            content = path.read_bytes()
            assert all(
                secret.encode("utf-8") not in content
                for secret in TEST_SECRETS
            )
    services.db.close()


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        _assert_language_wiring(root, None, "zh-TW")
        for language in UI_LANGUAGES:
            _assert_language_wiring(root, language, language)
        _assert_language_wiring(root, "en-US", "en")
        _assert_language_wiring(
            root,
            None,
            "ja-JP",
            saved_language="ja-JP",
        )
        _assert_language_wiring(
            root,
            None,
            "en",
            saved_language="en",
        )
        _assert_language_wiring(
            root,
            "en",
            "en",
            saved_language="ja-JP",
        )
    print("SERVICE_LANGUAGE_WIRING_OK")


if __name__ == "__main__":
    run()
