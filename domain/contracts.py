from __future__ import annotations

lazy import sqlite3
lazy from pathlib import Path
lazy from typing import Any, Protocol


# PySide exposes class-level ``Signal`` descriptors and instance-level
# ``SignalInstance`` objects.  Its generated stubs do not preserve that binding
# during structural protocol comparison, so Qt signals stay opaque at this
# framework-neutral domain boundary.
SignalPort = object


class SecretStorePort(Protocol):
    def load(self) -> str: ...

    def save(self, value: str) -> None: ...

    def clear(self) -> None: ...


class SecretStoreFactoryPort(Protocol):
    """Create one platform-approved secret boundary for a named purpose."""

    def __call__(
        self,
        path: Path,
        description: str = "MoHan protected secret",
    ) -> SecretStorePort: ...


class ProfileDatabasePort(Protocol):
    path: Path
    conn: sqlite3.Connection

    def setting(self, key: str, default: object = None) -> object: ...

    def set_setting(self, key: str, value: object) -> None: ...


class LocalSpeechEnginePort(Protocol):
    @property
    def finished(self) -> SignalPort: ...

    @property
    def failed(self) -> SignalPort: ...

    @property
    def viseme_cue(self) -> SignalPort: ...

    def set_volume(self, volume_percent: int, muted: bool = False) -> None: ...

    def speak(
        self,
        text: str,
        voice_name: str = "",
        rate: int = -1,
    ) -> None: ...

    def stop(self) -> None: ...


class CloudSpeechEnginePort(Protocol):
    @property
    def finished(self) -> SignalPort: ...

    @property
    def failed(self) -> SignalPort: ...

    @property
    def viseme_cue(self) -> SignalPort: ...

    def set_volume(self, volume_percent: int, muted: bool = False) -> None: ...

    def speak(
        self,
        text: str,
        api_key: str,
        voice: str = "coral",
        instructions: str = "",
    ) -> None: ...

    def stop(self) -> None: ...


class AzureSpeechEnginePort(Protocol):
    @property
    def finished(self) -> SignalPort: ...

    @property
    def failed(self) -> SignalPort: ...

    @property
    def viseme_cue(self) -> SignalPort: ...

    @property
    def voice_catalog_ready(self) -> SignalPort: ...

    def set_volume(self, volume_percent: int, muted: bool = False) -> None: ...

    def speak(
        self,
        text: str,
        api_key: str,
        region: str,
        voice: str,
        locale: str = "",
    ) -> None: ...

    def stop(self) -> None: ...

    def refresh_voice_catalog(
        self,
        api_key: str,
        region: str,
        language: str,
        *,
        hd_only: bool,
    ) -> None: ...

    def invalidate_voice_catalog(self, region: str | None = None) -> None: ...


class SpeechProviderRegistryPort(Protocol):
    def provider(self, provider_id: object) -> Any: ...

    def provider_ids(self) -> tuple[str, ...]: ...

    def output_provider_id(
        self,
        selected_provider_id: object,
        *,
        realtime_running: bool,
        cloud_available: bool = True,
        configured_provider_ids: tuple[str, ...] | None = None,
    ) -> str: ...

    def fallback_provider_id(
        self,
        failed_provider_id: object,
    ) -> str | None: ...


class RealtimeVoicePort(Protocol):
    @property
    def status_changed(self) -> SignalPort: ...

    @property
    def user_transcript(self) -> SignalPort: ...

    @property
    def assistant_transcript(self) -> SignalPort: ...

    @property
    def speaking_changed(self) -> SignalPort: ...

    @property
    def viseme_cue(self) -> SignalPort: ...

    @property
    def failed(self) -> SignalPort: ...

    @property
    def output_text_started(self) -> SignalPort: ...

    @property
    def output_text_delta(self) -> SignalPort: ...

    @property
    def output_text_done(self) -> SignalPort: ...

    @property
    def output_interrupted(self) -> SignalPort: ...
    running: bool

    def set_volume(self, volume_percent: int, muted: bool = False) -> None: ...

    def set_external_playback_active(self, active: bool) -> None: ...

    def start(self, *args: Any, **kwargs: Any) -> None: ...

    def stop(self) -> int: ...


class SpeechListenerPort(Protocol):
    @property
    def recognized(self) -> SignalPort: ...

    @property
    def failed(self) -> SignalPort: ...

    @property
    def listening_changed(self) -> SignalPort: ...

    @property
    def recording_changed(self) -> SignalPort: ...

    @property
    def status_changed(self) -> SignalPort: ...

    @property
    def diagnostic_changed(self) -> SignalPort: ...
    @property
    def is_recording(self) -> bool: ...

    def toggle_listening(self) -> None: ...
