"""Narrow service-bundle contract consumed by the reusable companion UI."""

from __future__ import annotations

lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from typing import Any, Protocol

lazy from domain.contracts import (
    AzureSpeechEnginePort,
    CloudSpeechEnginePort,
    LocalSpeechEnginePort,
    ProfileDatabasePort,
    RealtimeVoicePort,
    SecretStoreFactoryPort,
    SecretStorePort,
    SpeechListenerPort,
    SpeechProviderRegistryPort,
)


class PresentationDatabasePort(ProfileDatabasePort, Protocol):
    """Database operations consumed by reusable desktop presentation code."""

    def close(self) -> None: ...

    def settings_snapshot(self) -> object: ...

    def restore_settings_snapshot(self, snapshot: object) -> None: ...

    def __getattr__(self, name: str) -> Callable[..., Any]: ...


@dataclass(frozen=True, slots=True)
class PlatformProgressUpdate:
    """One platform-progress edit crossing the presentation boundary."""

    platform: str
    status: str
    missing: str
    item_name: str = ""
    next_action: str = ""
    notes: str = ""
    url: str = ""

    def database_row(self, updated_at: str) -> tuple[str, ...]:
        return (
            self.platform.strip(),
            self.status.strip() or "尚未開始",
            self.missing.strip(),
            self.item_name.strip(),
            self.next_action.strip(),
            self.notes.strip(),
            self.url.strip(),
            updated_at,
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
