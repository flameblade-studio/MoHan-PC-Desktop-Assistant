from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from contracts import (
    AzureSpeechEnginePort,
    CloudSpeechEnginePort,
    LocalSpeechEnginePort,
)


WINDOWS_LOCAL_PROVIDER = "windows-local"
OPENAI_SPEECH_PROVIDER = "openai-speech"
OPENAI_REALTIME_PROVIDER = "openai-realtime"
AZURE_SPEECH_PROVIDER = "azure-speech"


_LEGACY_PROVIDER_IDS = {
    WINDOWS_LOCAL_PROVIDER: WINDOWS_LOCAL_PROVIDER,
    "Windows 本機語音": WINDOWS_LOCAL_PROVIDER,
    "Windows 本机语音": WINDOWS_LOCAL_PROVIDER,
    "Windows local voice": WINDOWS_LOCAL_PROVIDER,
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
}


def normalize_speech_provider_id(value: object) -> str:
    """Return a stable provider ID for old and localized saved values."""

    text = str(value or "").strip()
    return _LEGACY_PROVIDER_IDS.get(text, WINDOWS_LOCAL_PROVIDER)


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
    api_key: str = ""
    instructions: str = ""
    options: Mapping[str, str] = field(default_factory=dict)


class SpeechProviderPort(Protocol):
    capabilities: SpeechProviderCapabilities

    def speak(self, request: SpeechRequest) -> None: ...


class WindowsSpeechProvider:
    capabilities = SpeechProviderCapabilities(
        provider_id=WINDOWS_LOCAL_PROVIDER,
        offline=True,
        requires_api_key=False,
        verified_female_catalog=True,
        supports_streaming=False,
        supported_languages=("installed",),
    )

    def __init__(self, engine: LocalSpeechEnginePort):
        self.engine = engine

    def speak(self, request: SpeechRequest) -> None:
        self.engine.speak(request.text, request.voice, request.rate)


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
        supported_languages=("zh-TW", "zh-CN", "en-US"),
    )

    def __init__(self, engine: AzureSpeechEnginePort):
        self.engine = engine

    def speak(self, request: SpeechRequest) -> None:
        self.engine.speak(
            request.text,
            request.api_key,
            str(request.options.get("region", "")),
            request.voice,
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
        unavailable, queued text falls back directly to Windows local speech.
        Unknown or unavailable providers also fall back to Windows.
        """

        selected = normalize_speech_provider_id(selected_provider_id)
        if selected == OPENAI_REALTIME_PROVIDER:
            return (
                OPENAI_SPEECH_PROVIDER
                if realtime_running and cloud_available
                else WINDOWS_LOCAL_PROVIDER
            )
        if selected == OPENAI_SPEECH_PROVIDER and not cloud_available:
            return WINDOWS_LOCAL_PROVIDER
        configured = set(
            configured_provider_ids
            if configured_provider_ids is not None
            else self._providers
        )
        configured.add(WINDOWS_LOCAL_PROVIDER)
        if selected in self._providers and selected in configured:
            return selected
        return WINDOWS_LOCAL_PROVIDER

    def fallback_provider_id(self, failed_provider_id: object) -> str | None:
        failed = normalize_speech_provider_id(failed_provider_id)
        if (
            failed != WINDOWS_LOCAL_PROVIDER
            and WINDOWS_LOCAL_PROVIDER in self._providers
        ):
            return WINDOWS_LOCAL_PROVIDER
        return None


def create_builtin_speech_registry(
    local_engine: LocalSpeechEnginePort,
    cloud_engine: CloudSpeechEnginePort,
    azure_engine: AzureSpeechEnginePort | None = None,
) -> SpeechProviderRegistry:
    providers: list[SpeechProviderPort] = [
        WindowsSpeechProvider(local_engine),
        OpenAISpeechProvider(cloud_engine),
    ]
    if azure_engine is not None:
        providers.append(AzureSpeechProvider(azure_engine))
    return SpeechProviderRegistry(tuple(providers))
