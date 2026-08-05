from __future__ import annotations

import ast
import importlib
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app import Dashboard, set_autostart
from db import StudioDB
from flagship_ui import FlagshipControlCenter
from platform_contracts import (
    PlatformCapabilities,
    PlatformPaths,
    UnsupportedPlatformFeature,
)
from platform_services import (
    create_platform_services,
    normalized_platform_id,
    resolved_data_dir,
)
from service_container import create_default_services
from secret_store import platform_secret_store_factory
from speech import preferred_windows_voice
from speech_providers import (
    LEGACY_WINDOWS_LOCAL_PROVIDER,
    SYSTEM_LOCAL_PROVIDER,
    WindowsSpeechProvider,
    normalize_speech_provider_id,
)


def direct_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".", 1)[0])
    return names


class AutostartProbe:
    capabilities = PlatformCapabilities(
        platform_id="test",
        display_name="Test",
        system_local_speech=False,
        verified_female_voice_catalog=False,
        offline_speech_recognition=False,
        secure_secret_storage=False,
        desktop_autostart=True,
        native_window_management=False,
        published_installers=(),
    )
    paths = PlatformPaths(Path("data"), Path("config"), Path("cache"))

    def __init__(self) -> None:
        self.calls: list[tuple[bool, str, str]] = []

    def set_autostart(
        self,
        enabled: bool,
        *,
        application_id: str,
        command: str,
    ) -> None:
        self.calls.append((enabled, application_id, command))

    def open_path(self, path: Path) -> None:
        del path


def run() -> None:
    # Windows must continue using the exact public-build profile location.
    windows = create_platform_services(
        "windows",
        environ={"LOCALAPPDATA": r"C:\Users\USERNAME\AppData\Local"},
        home=Path(r"C:\Users\USERNAME"),
    )
    assert windows.paths.data == (
        Path(r"C:\Users\USERNAME\AppData\Local")
        / "YanJianStudio"
        / "MoHan"
    )
    assert windows.paths.config == windows.paths.data
    assert windows.capabilities.system_local_speech
    assert windows.capabilities.verified_female_voice_catalog
    assert windows.capabilities.secure_secret_storage
    assert windows.capabilities.published_installers == (
        "portable-zip",
        "exe",
        "msi",
    )

    linux = create_platform_services(
        "linux",
        environ={
            "XDG_DATA_HOME": "/var/tmp/mohan-data",
            "XDG_CONFIG_HOME": "/var/tmp/mohan-config",
            "XDG_CACHE_HOME": "/var/tmp/mohan-cache",
        },
        home=Path("/home/tester"),
    )
    assert linux.paths.data == Path("/var/tmp/mohan-data/YanJianStudio/MoHan")
    assert linux.paths.config == Path(
        "/var/tmp/mohan-config/YanJianStudio/MoHan"
    )
    assert linux.paths.cache == Path(
        "/var/tmp/mohan-cache/YanJianStudio/MoHan"
    )
    assert not linux.capabilities.system_local_speech
    assert not linux.capabilities.secure_secret_storage
    assert linux.capabilities.published_installers == ()

    relative_xdg = create_platform_services(
        "linux",
        environ={
            "XDG_DATA_HOME": "relative/data",
            "XDG_CONFIG_HOME": "relative/config",
            "XDG_CACHE_HOME": "relative/cache",
        },
        home=Path("/home/tester"),
    )
    assert relative_xdg.paths.data == Path(
        "/home/tester/.local/share/YanJianStudio/MoHan"
    )
    assert relative_xdg.paths.config == Path(
        "/home/tester/.config/YanJianStudio/MoHan"
    )
    assert relative_xdg.paths.cache == Path(
        "/home/tester/.cache/YanJianStudio/MoHan"
    )

    macos = create_platform_services(
        "darwin",
        environ={},
        home=Path("/Users/tester"),
    )
    assert macos.paths.data == Path(
        "/Users/tester/Library/Application Support/YanJianStudio/MoHan"
    )
    assert macos.paths.cache == Path(
        "/Users/tester/Library/Caches/YanJianStudio/MoHan"
    )
    assert not macos.capabilities.desktop_autostart
    with patch("platform_services.sys.platform", "darwin"), patch(
        "platform_services.os.name",
        "posix",
    ):
        assert normalized_platform_id() == "macos"
    try:
        normalized_platform_id("posix")
    except RuntimeError:
        pass
    else:
        raise AssertionError("generic posix must not be misidentified as Linux")

    linux.set_autostart(False, application_id="MoHan", command="mohan")
    macos.set_autostart(False, application_id="MoHan", command="mohan")
    for platform in (linux, macos):
        try:
            platform.set_autostart(
                True,
                application_id="MoHan",
                command="mohan",
            )
        except UnsupportedPlatformFeature:
            pass
        else:
            raise AssertionError("unsupported autostart enable must fail closed")

    assert resolved_data_dir(
        linux,
        environ={"MOHAN_DATA_DIR": "/var/tmp/custom-mohan"},
    ) == Path("/var/tmp/custom-mohan")

    # Existing values migrate in place to one platform-neutral provider ID.
    assert SYSTEM_LOCAL_PROVIDER == "system-local"
    assert LEGACY_WINDOWS_LOCAL_PROVIDER == "windows-local"
    for old_value in (
        "windows-local",
        "Windows 本機語音",
        "Windows 本机语音",
        "Windows local voice",
        "Windows 本機音声",
    ):
        assert normalize_speech_provider_id(old_value) == SYSTEM_LOCAL_PROVIDER

    # The Taiwan Windows default contract remains Yating first, then Hanhan.
    voices = [
        ("Microsoft Hanhan Desktop", "zh-TW"),
        ("OneCore::Microsoft Yating", "zh-TW"),
        ("Microsoft Zira Desktop", "en-US"),
    ]
    assert preferred_windows_voice(voices, "", "zh-TW") == (
        "OneCore::Microsoft Yating"
    )
    assert WindowsSpeechProvider.capabilities.provider_id == (
        SYSTEM_LOCAL_PROVIDER
    )
    assert WindowsSpeechProvider.capabilities.offline

    probe = AutostartProbe()
    set_autostart(True, probe)
    assert probe.calls and probe.calls[0][0:2] == (True, "MoHanStudio")
    assert probe.calls[0][2].startswith(f'"{sys.executable}"')
    assert str(PROJECT / "app.py") in probe.calls[0][2]

    # Platform-only modules must not be imported unconditionally by core files.
    assert "winreg" not in direct_imports(PROJECT / "app.py")
    assert "winreg" not in direct_imports(PROJECT / "platform_windows.py")
    assert "winsound" not in direct_imports(PROJECT / "speech.py")

    for module_name in (
        "ai_client",
        "db",
        "expression_system",
        "flagship_core",
        "platform_contracts",
        "platform_linux",
        "platform_macos",
        "platform_services",
        "platform_windows",
        "secret_store",
        "service_container",
        "speech",
        "speech_providers",
        "windows_tools",
        "app",
    ):
        importlib.import_module(module_name)

    # A non-Windows composition remains fail-closed: no plaintext key file and
    # no falsely advertised offline system voice.
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        seeded_db = StudioDB(Path(temp) / "mohan.db")
        seeded_db.set_setting("voice_engine", "windows-local")
        seeded_db.close()
        services = create_default_services(
            Path(temp),
            PROJECT / "voice_listener.ps1",
            platform_services=linux,
        )
        assert services.platform_services is linux
        assert services.db.setting("voice_engine") == SYSTEM_LOCAL_PROVIDER
        assert services.secret_store.load() == ""
        try:
            services.secret_store.save("must-not-be-written")
        except OSError:
            pass
        else:
            raise AssertionError("non-Windows secrets must fail closed")
        assert not (Path(temp) / "openai-key.unavailable").exists()
        assert not services.speech_providers.provider(
            SYSTEM_LOCAL_PROVIDER
        ).capabilities.offline
        services.db.close()

    qt = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        services = create_default_services(
            root,
            PROJECT / "voice_listener.ps1",
            platform_services=linux,
        )
        dashboard = Dashboard(
            services.db,
            services.listener,
            services.secret_store,
            azure_secret_store=services.azure_secret_store,
            secret_store_factory=services.secret_store_factory,
            platform_services=linux,
        )
        assert dashboard.voice_engine.findData(SYSTEM_LOCAL_PROVIDER) == -1
        assert all(
            "Windows" not in dashboard.speech_recognition.itemText(index)
            for index in range(dashboard.speech_recognition.count())
        )
        assert not dashboard.windows_transcription_fallback.isEnabled()
        assert "Windows" not in dashboard.windows_transcription_fallback.text()
        assert not dashboard.windows_voice.isEnabled()
        assert "Windows" not in dashboard.windows_voice.currentText()
        assert not dashboard.azure_key_input.isEnabled()
        assert not dashboard.api_key_input.isEnabled()
        assert not dashboard.autostart.isEnabled()
        assert dashboard.save_settings(silent=True)
        assert services.db.setting("autostart") is False

        center = dashboard.flagship_center
        assert center.secret_store_factory is services.secret_store_factory
        assert not center.cloud_connect_button.isEnabled()
        assert not center.ha_token.isEnabled()
        protected = set(center.policy.protected_paths)
        for path in (
            linux.paths.data,
            linux.paths.config,
            linux.paths.cache,
        ):
            assert path.resolve() in protected

        center._cloud_connected(
            "google",
            {"access_token": "test-value"},
        )
        assert "無法安全保存" in center.cloud_status.text()
        assert services.db.connector("google") is None
        center.ha_url.setText("http://homeassistant.local:8123")
        center.ha_token.setText("test-value")
        with patch.object(QMessageBox, "warning") as warning:
            center.save_home_settings()
        assert warning.call_count == 1
        assert services.db.connector("home_assistant") is None
        assert not list(root.glob("*.unavailable"))
        center.close_services()
        dashboard.close()
        services.db.close()

        mac_db = StudioDB(root / "macos.db")
        mac_factory = platform_secret_store_factory(macos)
        mac_center = FlagshipControlCenter(
            mac_db,
            root,
            platform_services=macos,
            secret_store_factory=mac_factory,
        )
        mac_protected = set(mac_center.policy.protected_paths)
        for path in (
            macos.paths.data,
            macos.paths.config,
            macos.paths.cache,
        ):
            assert path.resolve() in mac_protected
        mac_center.close_services()
        mac_center.close()
        mac_db.close()
        qt.processEvents()

    widget = QWidget()
    assert widget.metaObject().className() == "QWidget"
    widget.close()
    qt.processEvents()
    print("CROSS_PLATFORM_CORE_OK")


if __name__ == "__main__":
    run()
