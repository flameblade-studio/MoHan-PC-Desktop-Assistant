from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, field
lazy from typing import Protocol

lazy from domain.contracts import (
    AzureSpeechEnginePort,
    CloudSpeechEnginePort,
    LocalSpeechEnginePort,
)

SYSTEM_LOCAL_PROVIDER = "system-local"
# Compatibility name retained for third-party imports. Its value is the new
# platform-neutral persisted ID; the literal old value is migrated below.
WINDOWS_LOCAL_PROVIDER = SYSTEM_LOCAL_PROVIDER
LEGACY_WINDOWS_LOCAL_PROVIDER = "windows-local"
OPENAI_SPEECH_PROVIDER = "openai-speech"
OPENAI_REALTIME_PROVIDER = "openai-realtime"
AZURE_SPEECH_PROVIDER = "azure-speech"
AZURE_HD_SPEECH_PROVIDER = "azure-speech-hd"


_LEGACY_PROVIDER_IDS = {
    SYSTEM_LOCAL_PROVIDER: SYSTEM_LOCAL_PROVIDER,
    LEGACY_WINDOWS_LOCAL_PROVIDER: SYSTEM_LOCAL_PROVIDER,
    "Windows 本機語音": SYSTEM_LOCAL_PROVIDER,
    "Windows 本机语音": SYSTEM_LOCAL_PROVIDER,
    "Windows local voice": SYSTEM_LOCAL_PROVIDER,
    "Windows 本機音声": SYSTEM_LOCAL_PROVIDER,
    "系統本機語音": SYSTEM_LOCAL_PROVIDER,
    "系统本地语音": SYSTEM_LOCAL_PROVIDER,
    "System local voice": SYSTEM_LOCAL_PROVIDER,
    "システム本機音声": SYSTEM_LOCAL_PROVIDER,
    OPENAI_SPEECH_PROVIDER: OPENAI_SPEECH_PROVIDER,
    "OpenAI 自然語音": OPENAI_SPEECH_PROVIDER,
    "OpenAI 自然语音": OPENAI_SPEECH_PROVIDER,
    "OpenAI natural voice": OPENAI_SPEECH_PROVIDER,
    OPENAI_REALTIME_PROVIDER: OPENAI_REALTIME_PROVIDER,
    "Realtime 即時語音": OPENAI_REALTIME_PROVIDER,
    "Realtime 即时语音": OPENAI_REALTIME_PROVIDER,
    "Realtime voice": OPENAI_REALTIME_PROVIDER,
    AZURE_SPEECH_PROVIDER: AZURE_SPEECH_PROVIDER,
    "Azure Speech（預覽）": AZURE_SPEECH_PROVIDER,
    "Azure Speech（预览）": AZURE_SPEECH_PROVIDER,
    "Azure Speech (Preview)": AZURE_SPEECH_PROVIDER,
    AZURE_HD_SPEECH_PROVIDER: AZURE_HD_SPEECH_PROVIDER,
    "Azure Dragon HD（私下測試）": AZURE_HD_SPEECH_PROVIDER,
    "Azure Dragon HD（私下测试）": AZURE_HD_SPEECH_PROVIDER,
    "Azure Dragon HD (Private Preview)": AZURE_HD_SPEECH_PROVIDER,
    "Azure Dragon HD（非公開テスト）": AZURE_HD_SPEECH_PROVIDER,
    "Azure Dragon HD（預覽，需 S0）": AZURE_HD_SPEECH_PROVIDER,
    "Azure Dragon HD（预览，需 S0）": AZURE_HD_SPEECH_PROVIDER,
    "Azure Dragon HD (Preview, requires S0)": AZURE_HD_SPEECH_PROVIDER,
    "Azure Dragon HD（プレビュー、S0 必須）": AZURE_HD_SPEECH_PROVIDER,
}


def normalize_speech_provider_id(value: object) -> str:
    """Return a stable provider ID for old and localized saved values."""

    text = str(value or "").strip()
    return _LEGACY_PROVIDER_IDS.get(text, SYSTEM_LOCAL_PROVIDER)


@dataclass(frozen=True)
class SpeechProviderCapabilities:
    provider_id: str
    offline: bool
    requires_api_key: bool
    verified_female_catalog: bool
    supports_streaming: bool
    supported_languages: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpeechRequest:
    text: str
    voice: str = ""
    rate: int = -1
    api_key: str = field(default="", repr=False)
    instructions: str = ""
    options: Mapping[str, str] = field(default_factory=dict)


class SpeechProviderPort(Protocol):
    capabilities: SpeechProviderCapabilities

    def speak(self, request: SpeechRequest) -> None: ...


class SpeechProviderSettingsPort(Protocol):
    def setting(self, key: str, default: object = None) -> object: ...

    def set_setting(self, key: str, value: object) -> None: ...


def migrate_speech_provider_setting(
    settings: SpeechProviderSettingsPort,
    key: str = "voice_engine",
) -> str:
    """Persist one canonical provider ID while preserving the old choice."""

    current = settings.setting(key, SYSTEM_LOCAL_PROVIDER)
    migrated = normalize_speech_provider_id(current)
    if current != migrated:
        settings.set_setting(key, migrated)
    return migrated


class SystemSpeechProvider:
    default_capabilities = SpeechProviderCapabilities(
        provider_id=SYSTEM_LOCAL_PROVIDER,
        offline=True,
        requires_api_key=False,
        verified_female_catalog=True,
        supports_streaming=False,
        supported_languages=("installed",),
    )

    def __init__(
        self,
        engine: LocalSpeechEnginePort,
        capabilities: SpeechProviderCapabilities | None = None,
    ):
        self.engine = engine
        self.capabilities = capabilities or self.default_capabilities

    def speak(self, request: SpeechRequest) -> None:
        self.engine.speak(request.text, request.voice, request.rate)


class WindowsSpeechProvider(SystemSpeechProvider):
    """Backward-compatible class name for integrations written before RC2."""

    capabilities = SystemSpeechProvider.default_capabilities


class OpenAISpeechProvider:
    capabilities = SpeechProviderCapabilities(
        provider_id=OPENAI_SPEECH_PROVIDER,
        offline=False,
        requires_api_key=True,
        verified_female_catalog=False,
        supports_streaming=True,
        supported_languages=("multilingual",),
    )

    def __init__(self, engine: CloudSpeechEnginePort):
        self.engine = engine

    def speak(self, request: SpeechRequest) -> None:
        self.engine.speak(
            request.text,
            request.api_key,
            request.voice,
            request.instructions,
        )


class AzureSpeechProvider:
    capabilities = SpeechProviderCapabilities(
        provider_id=AZURE_SPEECH_PROVIDER,
        offline=False,
        requires_api_key=True,
        verified_female_catalog=True,
        supports_streaming=False,
        supported_languages=("zh-TW", "zh-CN", "en-US", "ja-JP"),
    )

    def __init__(self, engine: AzureSpeechEnginePort):
        self.engine = engine

    def speak(self, request: SpeechRequest) -> None:
        self.engine.speak(
            request.text,
            request.api_key,
            str(request.options.get("region", "")),
            request.voice,
            str(request.options.get("locale", "zh-TW")),
        )


class AzureHDSpeechProvider(AzureSpeechProvider):
    capabilities = SpeechProviderCapabilities(
        provider_id=AZURE_HD_SPEECH_PROVIDER,
        offline=False,
        requires_api_key=True,
        verified_female_catalog=True,
        supports_streaming=False,
        supported_languages=("multilingual",),
    )


class SpeechProviderRegistry:
    """Explicit registry for replaceable speech engines.

    Providers cannot change expression, lip-sync, permissions, or UI state.
    They only receive a synthesis request and emit audio through the existing
    engine signals.
    """

    def __init__(self, providers: tuple[SpeechProviderPort, ...] = ()):
        self._providers: dict[str, SpeechProviderPort] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: SpeechProviderPort) -> None:
        provider_id = provider.capabilities.provider_id
        if provider_id in self._providers:
            raise ValueError(f"Duplicate speech provider: {provider_id}")
        self._providers[provider_id] = provider

    def provider(self, provider_id: object) -> SpeechProviderPort:
        normalized = normalize_speech_provider_id(provider_id)
        try:
            return self._providers[normalized]
        except KeyError as exc:
            raise LookupError(
                f"Speech provider is not registered: {normalized}"
            ) from exc

    def provider_ids(self) -> tuple[str, ...]:
        return tuple(self._providers)

    def output_provider_id(
        self,
        selected_provider_id: object,
        *,
        realtime_running: bool,
        cloud_available: bool = True,
        configured_provider_ids: tuple[str, ...] | None = None,
    ) -> str:
        """Choose a provider for queued text without changing user settings.

        Realtime owns its live audio while connected. If it is selected but
        unavailable, queued text falls back to the registered system-local
        adapter. Unknown or unavailable providers use the same single fallback.
        """

        selected = normalize_speech_provider_id(selected_provider_id)
        if selected == OPENAI_REALTIME_PROVIDER:
            return (
                OPENAI_SPEECH_PROVIDER
                if realtime_running and cloud_available
                else SYSTEM_LOCAL_PROVIDER
            )
        if selected == OPENAI_SPEECH_PROVIDER and not cloud_available:
            return SYSTEM_LOCAL_PROVIDER
        configured = set(
            configured_provider_ids
            if configured_provider_ids is not None
            else self._providers
        )
        configured.add(SYSTEM_LOCAL_PROVIDER)
        if selected in self._providers and selected in configured:
            return selected
        if (
            selected == AZURE_HD_SPEECH_PROVIDER
            and AZURE_SPEECH_PROVIDER in self._providers
            and AZURE_SPEECH_PROVIDER in configured
        ):
            return AZURE_SPEECH_PROVIDER
        return SYSTEM_LOCAL_PROVIDER

    def fallback_provider_id(self, failed_provider_id: object) -> str | None:
        failed = normalize_speech_provider_id(failed_provider_id)
        if (
            failed == AZURE_HD_SPEECH_PROVIDER
            and AZURE_SPEECH_PROVIDER in self._providers
        ):
            return AZURE_SPEECH_PROVIDER
        local = self._providers.get(SYSTEM_LOCAL_PROVIDER)
        if (
            failed != SYSTEM_LOCAL_PROVIDER
            and local is not None
            and local.capabilities.offline
        ):
            return SYSTEM_LOCAL_PROVIDER
        return None


def create_builtin_speech_registry(
    local_engine: LocalSpeechEnginePort,
    cloud_engine: CloudSpeechEnginePort,
    azure_engine: AzureSpeechEnginePort | None = None,
    azure_hd_engine: AzureSpeechEnginePort | None = None,
    *,
    system_capabilities: SpeechProviderCapabilities | None = None,
) -> SpeechProviderRegistry:
    providers: list[SpeechProviderPort] = [
        SystemSpeechProvider(local_engine, system_capabilities),
        OpenAISpeechProvider(cloud_engine),
    ]
    if azure_engine is not None:
        providers.append(AzureSpeechProvider(azure_engine))
    if azure_hd_engine is not None:
        providers.append(AzureHDSpeechProvider(azure_hd_engine))
    return SpeechProviderRegistry(tuple(providers))
