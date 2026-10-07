from __future__ import annotations

lazy import inspect
lazy import logging
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest

lazy from application.native_acceleration import NativeAcceleration
lazy from application.native_rgba_acceleration import NativeRgbaAcceleration
lazy from application.theme_pack_service import _BUILTIN_NAMES
lazy from application.wardrobe_service import BUILTIN_OUTFIT_FALLBACK_NAME
lazy from domain.character_pack.character_data import load_mohan_character_data
lazy from domain.contracts import (
    SecretStoreFactoryPort,
    default_character_display_name,
)
lazy from domain.expression_system import (
    INTERNAL_EMOTION_INSTRUCTION,
    parse_internal_emotion,
)
lazy from domain.gesture_configuration import GESTURE_ACTION_LABELS, GestureAction
lazy from infrastructure.platform_linux import LinuxPlatformServices
lazy from infrastructure.platform_macos import MacOSPlatformServices
lazy from infrastructure.platform_services import normalized_platform_id
lazy from infrastructure.platform_windows import WindowsPlatformServices
lazy from infrastructure.portable_secret_binding import bind_dashboard_portable_secrets
lazy from infrastructure.secret_store import PlatformSecretStoreFactory, SecretStore


EXPECTED_NAMES = frozendict(
    {
        "zh-TW": "墨寒",
        "zh-CN": "墨寒",
        "en": "MoHan",
        "ja-JP": "墨寒",
    }
)


class _MemoryStore:
    def __init__(self) -> None:
        self.value = ""

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


class _RecordingFactory:
    def __init__(self) -> None:
        self.descriptions: dict[str, str] = {}

    def __call__(self, path: Path, description: str = "") -> _MemoryStore:
        self.descriptions[path.name] = description
        return _MemoryStore()


def _raising_loader(_name: str) -> None:
    raise ImportError("synthetic")


def test_four_language_names_come_from_character_persona_data() -> None:
    character_data = load_mohan_character_data()
    for locale, expected in EXPECTED_NAMES.items():
        assert default_character_display_name(locale) == expected
        assert character_data.personas[locale].identity.display_name == expected
    assert default_character_display_name("en-US") == EXPECTED_NAMES["en"]
    assert default_character_display_name("ja") == EXPECTED_NAMES["ja-JP"]


def test_identity_derived_text_stays_byte_for_byte_compatible() -> None:
    assert dict(_BUILTIN_NAMES) == {
        "zh-TW": "墨寒藍銀主題",
        "zh-CN": "墨寒蓝银主题",
        "en": "MoHan Blue-Silver",
        "ja-JP": "墨寒ブルーシルバー",
    }
    assert BUILTIN_OUTFIT_FALLBACK_NAME == "墨寒藍白漢服"

    acknowledgement = GESTURE_ACTION_LABELS[
        GestureAction.POSITIVE_ACKNOWLEDGEMENT
    ]
    assert (
        acknowledgement.traditional_chinese,
        acknowledgement.simplified_chinese,
        acknowledgement.english,
        acknowledgement.japanese,
    ) == (
        "墨寒以正向表情回應",
        "墨寒以正向表情回应",
        "MoHan responds positively",
        "墨寒が肯定的に応える",
    )
    command = GESTURE_ACTION_LABELS[GestureAction.CUSTOM_COMMAND]
    assert (
        command.traditional_chinese,
        command.simplified_chinese,
        command.english,
        command.japanese,
    ) == (
        "自訂墨寒文字指令",
        "自定义墨寒文字指令",
        "Custom MoHan text command",
        "墨寒のカスタム文字指示",
    )
    assert "[[MOHAN_EMOTION:情緒:強度]]" in INTERNAL_EMOTION_INSTRUCTION
    reply = parse_internal_emotion(
        "主上，妾已想明白。[[MOHAN_EMOTION:thinking:0.72]]"
    )
    assert reply.text == "主上，妾已想明白。"
    assert (reply.expression, reply.emotion, reply.intensity, reply.valid_tag) == (
        "thinking_front",
        "thinking",
        0.72,
        True,
    )


def test_platform_paths_and_error_text_stay_compatible() -> None:
    home = Path("C:/snapshot-home")
    environment = {
        "LOCALAPPDATA": "C:/snapshot-local",
        "XDG_DATA_HOME": "C:/snapshot-xdg-data",
        "XDG_CONFIG_HOME": "C:/snapshot-xdg-config",
        "XDG_CACHE_HOME": "C:/snapshot-xdg-cache",
    }
    windows = WindowsPlatformServices(environ=environment, home=home)
    macos = MacOSPlatformServices(environ=environment, home=home)
    linux = LinuxPlatformServices(environ=environment, home=home)
    assert windows.paths.data.as_posix() == (
        "C:/snapshot-local/YanJianStudio/MoHan"
    )
    assert macos.paths.data.as_posix() == (
        "C:/snapshot-home/Library/Application Support/YanJianStudio/MoHan"
    )
    assert linux.paths.data.as_posix() == (
        "C:/snapshot-home/.local/share/YanJianStudio/MoHan"
    )
    with pytest.raises(
        RuntimeError,
        match="^MoHan 尚未定義此作業系統平台：plan9$",
    ):
        normalized_platform_id("plan9")


def test_secret_descriptions_and_fail_closed_text_stay_compatible(
    tmp_path: Path,
) -> None:
    assert inspect.signature(SecretStore).parameters["description"].default == (
        "MoHan OpenAI API key"
    )
    assert (
        inspect.signature(SecretStoreFactoryPort.__call__)
        .parameters["description"]
        .default
        == "MoHan protected secret"
    )

    platform = SimpleNamespace(
        capabilities=SimpleNamespace(
            secure_secret_storage=False,
            display_name="SyntheticOS",
        )
    )
    unavailable = PlatformSecretStoreFactory(platform)(tmp_path / "secret.bin")
    assert unavailable.reason == (
        "SyntheticOS 的原生安全金鑰保存尚未完成實機驗證；"
        "墨寒不會退回明文保存。"
    )

    factory = _RecordingFactory()
    dependencies = SimpleNamespace(
        secret_store=_MemoryStore(),
        azure_secret_store=_MemoryStore(),
        azure_hd_secret_store=_MemoryStore(),
        secret_store_factory=factory,
    )
    bind_dashboard_portable_secrets(dependencies, tmp_path)
    assert factory.descriptions == {
        "home-assistant-token.dpapi": "MoHan Home Assistant token",
        "oauth-google.dpapi": "MoHan google OAuth token",
        "oauth-microsoft.dpapi": "MoHan microsoft OAuth token",
        "oauth-github.dpapi": "MoHan github OAuth token",
        "face-identities.dpapi": "MoHan local face identity templates",
        "gesture-templates.dpapi": "MoHan local gesture skeleton templates",
    }


def test_native_diagnostic_text_stays_compatible(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    native = NativeAcceleration(module_loader=_raising_loader)
    rgba = NativeRgbaAcceleration(module_loader=_raising_loader)
    native.status()
    native._disable_operation("analyze", RuntimeError("synthetic"))
    rgba.status()
    rgba._disable_operation("alpha_over", RuntimeError("synthetic"))
    assert [record.getMessage() for record in caplog.records] == [
        "MoHan native acceleration is unavailable; using Python: ImportError: synthetic",
        "MoHan native operation analyze requires attention; using Python fallback "
        "(attention event 1): RuntimeError",
        "MoHan native RGBA acceleration is unavailable; using Python: ImportError: synthetic",
        "MoHan native RGBA operation alpha_over requires attention; using Python "
        "fallback (attention event 1): RuntimeError",
    ]
