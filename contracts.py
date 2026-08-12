from __future__ import annotations

lazy import sqlite3
lazy from collections.abc import Callable
lazy from pathlib import Path
lazy from typing import Any, Protocol


class SignalPort(Protocol):
    def connect(self, slot: Callable[..., Any]) -> Any: ...


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
    finished: SignalPort
    failed: SignalPort
    viseme_cue: SignalPort

    def set_volume(self, volume_percent: int, muted: bool = False) -> None: ...

    def speak(
        self,
        text: str,
        voice_name: str = "",
        rate: int = -1,
    ) -> None: ...

    def stop(self) -> None: ...


class CloudSpeechEnginePort(Protocol):
    finished: SignalPort
    failed: SignalPort
    viseme_cue: SignalPort

    def set_volume(self, volume_percent: int, muted: bool = False) -> None: ...

    def speak(
        self,
        text: str,
        api_key: str,
        voice: str = "coral",
        instructions: str = "",
    ) -> None: ...


class AzureSpeechEnginePort(Protocol):
    finished: SignalPort
    failed: SignalPort
    viseme_cue: SignalPort
    voice_catalog_ready: SignalPort

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
    status_changed: SignalPort
    user_transcript: SignalPort
    assistant_transcript: SignalPort
    speaking_changed: SignalPort
    viseme_cue: SignalPort
    failed: SignalPort
    output_text_started: SignalPort
    output_text_delta: SignalPort
    output_text_done: SignalPort
    output_interrupted: SignalPort
    running: bool

    def set_volume(self, volume_percent: int, muted: bool = False) -> None: ...

    def set_external_playback_active(self, active: bool) -> None: ...

    def start(self, *args: Any, **kwargs: Any) -> None: ...

    def stop(self) -> int: ...


class SpeechListenerPort(Protocol):
    recognized: SignalPort
    failed: SignalPort
    listening_changed: SignalPort
    recording_changed: SignalPort
    status_changed: SignalPort
    diagnostic_changed: SignalPort
    is_recording: bool

    def toggle_listening(self) -> None: ...
