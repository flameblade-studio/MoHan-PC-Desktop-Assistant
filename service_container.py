from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject

from backup_manager import BackupManager
from azure_speech import AzureSpeechTTS
from contracts import (
    AzureSpeechEnginePort,
    CloudSpeechEnginePort,
    LocalSpeechEnginePort,
    RealtimeVoicePort,
    SecretStorePort,
    SpeechProviderRegistryPort,
    SpeechListenerPort,
)
from db import StudioDB
from realtime_voice import RealtimeVoiceClient
from secret_store import SecretStore
from speech import OpenAITTS, SpeechListener, WindowsTTS
from speech_providers import create_builtin_speech_registry


@dataclass
class CompanionServices:
    """Explicit dependencies owned by one companion-window runtime."""

    db: StudioDB
    secret_store: SecretStorePort
    local_tts: LocalSpeechEnginePort
    cloud_tts: CloudSpeechEnginePort
    realtime: RealtimeVoicePort
    listener: SpeechListenerPort
    backup_manager: BackupManager | None = None
    speech_providers: SpeechProviderRegistryPort | None = None
    azure_speech: AzureSpeechEnginePort | None = None
    azure_secret_store: SecretStorePort | None = None


def create_default_services(
    data_path: Path,
    listener_script: Path,
    parent: QObject | None = None,
) -> CompanionServices:
    data_path.mkdir(parents=True, exist_ok=True)
    db = StudioDB(data_path / "mohan.db")
    try:
        backup_manager: BackupManager | None = BackupManager(
            db,
            data_path / "backups",
        )
        backup_manager.automatic_if_due()
    except (OSError, RuntimeError, sqlite3.Error):
        backup_manager = None
    secret_store = SecretStore(data_path / "openai-key.dpapi")
    azure_secret_store = SecretStore(
        data_path / "azure-speech-key.dpapi",
        "MoHan Azure Speech key",
    )
    listener = SpeechListener(
        listener_script,
        api_key_provider=secret_store.load,
        recognition_mode_provider=lambda: str(
            db.setting("speech_recognition", "OpenAI 雲端（較準確）")
        ),
        transcription_model_provider=lambda: str(
            db.setting(
                "transcription_model",
                SpeechListener.TRANSCRIPTION_MODEL,
            )
        ),
        transcription_language_provider=lambda: str(
            db.setting("transcription_language", "zh")
        ),
        transcription_prompt_provider=lambda: str(
            db.setting(
                "transcription_prompt",
                SpeechListener.TRANSCRIPTION_PROMPT,
            )
        ),
        windows_fallback_provider=lambda: bool(
            db.setting("windows_transcription_fallback", True)
        ),
        parent=parent,
    )
    local_tts = WindowsTTS(parent)
    cloud_tts = OpenAITTS(parent)
    azure_tts = AzureSpeechTTS(parent)
    return CompanionServices(
        db=db,
        secret_store=secret_store,
        local_tts=local_tts,
        cloud_tts=cloud_tts,
        realtime=RealtimeVoiceClient(parent),
        listener=listener,
        backup_manager=backup_manager,
        speech_providers=create_builtin_speech_registry(
            local_tts,
            cloud_tts,
            azure_tts,
        ),
        azure_speech=azure_tts,
        azure_secret_store=azure_secret_store,
    )
