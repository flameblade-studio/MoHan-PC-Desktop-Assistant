from __future__ import annotations

lazy import ast
lazy import importlib
lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

lazy from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

lazy from application.service_container import create_default_services
lazy from domain.speech_providers import (
    LEGACY_WINDOWS_LOCAL_PROVIDER,
    SYSTEM_LOCAL_PROVIDER,
    WindowsSpeechProvider,
    normalize_speech_provider_id,
)
lazy from infrastructure.app_resources import set_autostart
lazy from infrastructure.db import StudioDB
lazy from infrastructure.platform_contracts import (
    PlatformCapabilities,
    PlatformPaths,
    PlatformServicePort,
    UnsupportedPlatformFeature,
)
lazy from infrastructure.platform_services import (
    create_platform_services,
    normalized_platform_id,
    resolved_data_dir,
)
lazy from infrastructure.secret_store import platform_secret_store_factory
lazy from integrations.speech import preferred_windows_voice
lazy from presentation.dashboard_composition import DashboardDependencies
lazy from presentation.dashboard_window import Dashboard
lazy from presentation.flagship_ui import (
    ControlCenterDependencies,
    FlagshipControlCenter,
)


def eager_direct_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            if not getattr(node, "is_lazy", 0):
                names.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and not getattr(node, "is_lazy", 0)
        ):
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


def _assert_windows_platform_contract() -> None:
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


def _create_linux_platform() -> PlatformServicePort:
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
    return linux


def _assert_relative_xdg_fallbacks() -> None:
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


def _create_macos_platform() -> PlatformServicePort:
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
    return macos


def _assert_platform_detection() -> None:
    with patch("sys.platform", "darwin"):
        assert normalized_platform_id() == "macos"
    try:
        normalized_platform_id("posix")
    except RuntimeError:
        pass
    else:
        raise AssertionError("generic posix must not be misidentified as Linux")


def _assert_autostart_fails_closed(
    linux: PlatformServicePort,
    macos: PlatformServicePort,
) -> None:
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


def _assert_data_directory_override(linux: PlatformServicePort) -> None:
    assert resolved_data_dir(
        linux,
        environ={"MOHAN_DATA_DIR": "/var/tmp/custom-mohan"},
    ) == Path("/var/tmp/custom-mohan")


def _assert_speech_provider_migration() -> None:
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


def _assert_windows_voice_contract() -> None:
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


def _assert_autostart_delegation() -> None:
    probe = AutostartProbe()
    set_autostart(True, probe)
    assert probe.calls and probe.calls[0][0:2] == (True, "MoHanStudio")
    assert probe.calls[0][2].startswith(f'"{sys.executable}"')
    assert str(PROJECT / "app.py") in probe.calls[0][2]


def _assert_platform_modules_are_lazy() -> None:
    assert "winreg" not in eager_direct_imports(PROJECT / "app.py")
    assert "winreg" not in eager_direct_imports(
        PROJECT / "infrastructure" / "platform_windows.py"
    )
    assert "winsound" not in eager_direct_imports(
        PROJECT / "integrations" / "speech.py"
    )


def _assert_core_modules_import() -> None:
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


def _assert_non_windows_composition_fails_closed(
    linux: PlatformServicePort,
) -> None:
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


def _create_dashboard(root: Path, linux: PlatformServicePort):
    services = create_default_services(
        root,
        PROJECT / "voice_listener.ps1",
        platform_services=linux,
    )
    dashboard = Dashboard(
        services.db,
        DashboardDependencies(
            listener=services.listener,
            secret_store=services.secret_store,
            azure_secret_store=services.azure_secret_store,
            secret_store_factory=services.secret_store_factory,
            platform_services=linux,
            presentation_ports=services.presentation_ports,
        ),
    )
    return services, dashboard


def _assert_linux_dashboard_fails_closed(
    root: Path,
    linux: PlatformServicePort,
) -> None:
    services, dashboard = _create_dashboard(root, linux)
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
    for path in (linux.paths.data, linux.paths.config, linux.paths.cache):
        assert path.resolve() in protected

    center._cloud_connected("google", {"access_token": "test-value"})
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
    assert not dashboard.timer.isActive()
    services.db.close()


def _assert_macos_control_center_paths(
    qt: QApplication,
    root: Path,
    macos: PlatformServicePort,
) -> None:
    mac_db = StudioDB(root / "macos.db")
    mac_factory = platform_secret_store_factory(macos)
    mac_center = FlagshipControlCenter(
        mac_db,
        root,
        dependencies=ControlCenterDependencies(
            platform_services=macos,
            secret_store_factory=mac_factory,
        ),
    )
    mac_protected = set(mac_center.policy.protected_paths)
    for path in (macos.paths.data, macos.paths.config, macos.paths.cache):
        assert path.resolve() in mac_protected
    mac_center.close_services()
    mac_center.close()
    mac_db.close()
    qt.processEvents()


def _assert_platform_ui_boundaries(
    qt: QApplication,
    linux: PlatformServicePort,
    macos: PlatformServicePort,
) -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        _assert_linux_dashboard_fails_closed(root, linux)
        _assert_macos_control_center_paths(qt, root, macos)


def _assert_qt_widget_smoke(qt: QApplication) -> None:
    widget = QWidget()
    assert widget.metaObject().className() == "QWidget"
    widget.close()
    qt.processEvents()


def run() -> None:
    # Windows keeps the exact public-build profile location.
    _assert_windows_platform_contract()
    linux = _create_linux_platform()
    _assert_relative_xdg_fallbacks()
    macos = _create_macos_platform()
    _assert_platform_detection()
    _assert_autostart_fails_closed(linux, macos)
    _assert_data_directory_override(linux)
    # Existing values migrate to one platform-neutral speech provider ID.
    _assert_speech_provider_migration()
    # Taiwan Windows defaults remain Yating first, then Hanhan.
    _assert_windows_voice_contract()
    _assert_autostart_delegation()
    # Platform-only modules must never load eagerly from core modules.
    _assert_platform_modules_are_lazy()
    _assert_core_modules_import()
    # Non-Windows composition must fail closed for secrets and system speech.
    _assert_non_windows_composition_fails_closed(linux)
    qt = QApplication.instance() or QApplication([])
    _assert_platform_ui_boundaries(qt, linux, macos)
    _assert_qt_widget_smoke(qt)
    print("CROSS_PLATFORM_CORE_OK")


if __name__ == "__main__":
    run()
