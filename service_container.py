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
    SecretStoreFactoryPort,
    SecretStorePort,
    SpeechProviderRegistryPort,
    SpeechListenerPort,
)
from db import StudioDB
from language_support import localized_transcription_prompt
from platform_contracts import PlatformServicePort
from platform_services import current_platform_services
from realtime_voice import RealtimeVoiceClient
from secret_store import platform_secret_store_factory
from speech import (
    OpenAITTS,
    SpeechListener,
    UnavailableSystemTTS,
    WindowsTTS,
)
from speech_providers import (
    SYSTEM_LOCAL_PROVIDER,
    SpeechProviderCapabilities,
    create_builtin_speech_registry,
    migrate_speech_provider_setting,
)


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
    secret_store_factory: SecretStoreFactoryPort | None = None
    platform_services: PlatformServicePort | None = None


def create_default_services(
    data_path: Path,
    listener_script: Path,
    parent: QObject | None = None,
    platform_services: PlatformServicePort | None = None,
) -> CompanionServices:
    runtime_platform = platform_services or current_platform_services()
    data_path.mkdir(parents=True, exist_ok=True)
    db = StudioDB(data_path / "mohan.db")
    # Migrate at the composition boundary so headless and UI startup paths
    # share the same canonical provider setting.
    migrate_speech_provider_setting(db)
    try:
        backup_manager: BackupManager | None = BackupManager(
            db,
            data_path / "backups",
        )
        backup_manager.automatic_if_due()
    except (OSError, RuntimeError, sqlite3.Error):
        backup_manager = None
    secret_factory = platform_secret_store_factory(runtime_platform)
    secret_store = secret_factory(
        data_path / "openai-key.dpapi",
        "MoHan OpenAI API key",
    )
    azure_secret_store = secret_factory(
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
                localized_transcription_prompt(
                    str(db.setting("ui_language", "zh-TW")),
                    assistant_name=str(db.setting("assistant_name", "")),
                    user_title=str(db.setting("user_title", "")),
                    organization_name=str(
                        db.setting("organization_name", "")
                    ),
                    wake_word=str(db.setting("wake_word", "")),
                ),
            )
        ),
        windows_fallback_provider=lambda: bool(
            runtime_platform.capabilities.offline_speech_recognition
            and db.setting("windows_transcription_fallback", True)
        ),
        parent=parent,
    )
    if runtime_platform.capabilities.system_local_speech:
        local_tts: LocalSpeechEnginePort = WindowsTTS(parent)
    else:
        local_tts = UnavailableSystemTTS(
            f"{runtime_platform.capabilities.display_name} 本機語音"
            "尚未完成實機驗證。",
            parent,
        )
    cloud_tts = OpenAITTS(parent)
    azure_tts = AzureSpeechTTS(parent)
    system_capabilities = SpeechProviderCapabilities(
        provider_id=SYSTEM_LOCAL_PROVIDER,
        offline=runtime_platform.capabilities.system_local_speech,
        requires_api_key=False,
        verified_female_catalog=(
            runtime_platform.capabilities.verified_female_voice_catalog
        ),
        supports_streaming=False,
        supported_languages=(
            ("installed",)
            if runtime_platform.capabilities.system_local_speech
            else ()
        ),
    )
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
            system_capabilities=system_capabilities,
        ),
        azure_speech=azure_tts,
        azure_secret_store=azure_secret_store,
        secret_store_factory=secret_factory,
        platform_services=runtime_platform,
    )
