"""Narrow service-bundle contract consumed by the reusable companion UI."""

from __future__ import annotations

lazy from collections.abc import Callable
lazy from typing import Any, Protocol

lazy from domain.contracts import (
    AzureSpeechEnginePort,
    CloudSpeechEnginePort,
    LocalSpeechEnginePort,
    RealtimeVoicePort,
    SecretStoreFactoryPort,
    SecretStorePort,
    SpeechListenerPort,
    SpeechProviderRegistryPort,
)


class CompanionServicesPort(Protocol):
    """Structural view of services already composed by the product shell."""

    db: Any
    secret_store: SecretStorePort
    local_tts: LocalSpeechEnginePort
    cloud_tts: CloudSpeechEnginePort
    realtime: RealtimeVoicePort
    listener: SpeechListenerPort
    presentation_ports: Any
    realtime_speech_output: Any | None
    backup_manager: Any | None
    speech_providers: SpeechProviderRegistryPort | None
    azure_speech: AzureSpeechEnginePort | None
    azure_hd_speech: AzureSpeechEnginePort | None
    azure_secret_store: SecretStorePort | None
    azure_hd_secret_store: SecretStorePort | None
    secret_store_factory: SecretStoreFactoryPort | None
    platform_services: Any | None
    cloud_vision_service_factory: Any | None
    dense_face_provider_factory: Callable[[], object] | None
