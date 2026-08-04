from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Callable, Protocol


class SignalPort(Protocol):
    def connect(self, slot: Callable[..., Any]) -> Any: ...


class SecretStorePort(Protocol):
    def load(self) -> str: ...

    def save(self, value: str) -> None: ...

    def clear(self) -> None: ...


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


class SpeechProviderRegistryPort(Protocol):
    def provider(self, provider_id: object) -> Any: ...

    def provider_ids(self) -> tuple[str, ...]: ...

    def output_provider_id(
        self,
        selected_provider_id: object,
        *,
        realtime_running: bool,
        cloud_available: bool = True,
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
    running: bool

    def set_volume(self, volume_percent: int, muted: bool = False) -> None: ...

    def start(self, *args: Any, **kwargs: Any) -> None: ...

    def stop(self) -> None: ...


class SpeechListenerPort(Protocol):
    recognized: SignalPort
    failed: SignalPort
    listening_changed: SignalPort
    recording_changed: SignalPort
    status_changed: SignalPort
    diagnostic_changed: SignalPort
    is_recording: bool

    def toggle_listening(self) -> None: ...
