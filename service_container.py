from __future__ import annotations

lazy import sqlite3
lazy from dataclasses import dataclass, field
lazy from pathlib import Path

lazy from PySide6.QtCore import QObject

lazy from azure_speech import AzureSpeechTTS
lazy from backup_manager import BackupManager
lazy from contracts import (
    AzureSpeechEnginePort,
    CloudSpeechEnginePort,
    LocalSpeechEnginePort,
    RealtimeVoicePort,
    SecretStoreFactoryPort,
    SecretStorePort,
    SpeechListenerPort,
    SpeechProviderRegistryPort,
)
lazy from db import StudioDB
lazy from language_support import (
    DEFAULT_UI_LANGUAGE,
    canonical_ui_language,
    localized_transcription_prompt,
)
lazy from platform_contracts import PlatformServicePort
lazy from platform_services import current_platform_services
lazy from realtime_speech_output import RealtimeSpeechOutput
lazy from realtime_voice import RealtimeVoiceClient
lazy from secret_store import platform_secret_store_factory
lazy from speech import (
    OpenAITTS,
    SpeechListener,
    SpeechListenerProviders,
    UnavailableSystemTTS,
    WindowsTTS,
)
lazy from speech_providers import (
    SYSTEM_LOCAL_PROVIDER,
    SpeechProviderCapabilities,
    create_builtin_speech_registry,
    migrate_speech_provider_setting,
)


@dataclass
class CompanionServices:
    """Explicit dependencies owned by one companion-window runtime."""

    db: StudioDB
    secret_store: SecretStorePort = field(repr=False)
    local_tts: LocalSpeechEnginePort
    cloud_tts: CloudSpeechEnginePort
    realtime: RealtimeVoicePort
    listener: SpeechListenerPort
    realtime_speech_output: RealtimeSpeechOutput | None = None
    backup_manager: BackupManager | None = None
    speech_providers: SpeechProviderRegistryPort | None = None
    azure_speech: AzureSpeechEnginePort | None = None
    azure_hd_speech: AzureSpeechEnginePort | None = None
    azure_secret_store: SecretStorePort | None = field(
        default=None,
        repr=False,
    )
    azure_hd_secret_store: SecretStorePort | None = field(
        default=None,
        repr=False,
    )
    secret_store_factory: SecretStoreFactoryPort | None = field(
        default=None,
        repr=False,
    )
    platform_services: PlatformServicePort | None = None


def _local_speech_engine(
    platform_services: PlatformServicePort,
    parent: QObject | None,
    *,
    language: str,
) -> LocalSpeechEnginePort:
    if platform_services.capabilities.system_local_speech:
        return WindowsTTS(parent, language=language)
    return UnavailableSystemTTS(
        f"{platform_services.capabilities.display_name} 本機語音"
        "尚未完成實機驗證。",
        parent,
    )


def _realtime_speech_output(
    platform_services: PlatformServicePort,
    parent: QObject | None,
    *,
    language: str,
) -> RealtimeSpeechOutput:
    return RealtimeSpeechOutput(
        AzureSpeechTTS(parent),
        AzureSpeechTTS(parent),
        _local_speech_engine(
            platform_services,
            parent,
            language=language,
        ),
        parent,
    )


def create_default_services(
    data_path: Path,
    listener_script: Path,
    parent: QObject | None = None,
    platform_services: PlatformServicePort | None = None,
    *,
    ui_language: str | None = None,
) -> CompanionServices:
    runtime_platform = platform_services or current_platform_services()
    data_path.mkdir(parents=True, exist_ok=True)
    db = StudioDB(data_path / "mohan.db")
    language_value = (
        ui_language
        if ui_language is not None
        else db.setting("ui_language", DEFAULT_UI_LANGUAGE)
    )
    service_language = canonical_ui_language(str(language_value))
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
    azure_hd_secret_store = secret_factory(
        data_path / "azure-dragon-hd-key.dpapi",
        "MoHan Azure Dragon HD Speech key",
    )
    listener = SpeechListener(
        listener_script,
        SpeechListenerProviders(
            api_key=secret_store.load,
            recognition_mode=lambda: str(
                db.setting(
                    "speech_recognition",
                    "OpenAI 雲端（較準確）",
                )
            ),
            transcription_model=lambda: str(
                db.setting(
                    "transcription_model",
                    SpeechListener.TRANSCRIPTION_MODEL,
                )
            ),
            transcription_language=lambda: str(
                db.setting("transcription_language", "zh")
            ),
            transcription_prompt=lambda: str(
                db.setting(
                    "transcription_prompt",
                    localized_transcription_prompt(
                        str(db.setting("ui_language", "zh-TW")),
                        assistant_name=str(
                            db.setting("assistant_name", "")
                        ),
                        user_title=str(
                            db.setting("user_title", "")
                        ),
                        organization_name=str(
                            db.setting("organization_name", "")
                        ),
                        wake_word=str(
                            db.setting("wake_word", "")
                        ),
                    ),
                )
            ),
            windows_fallback=lambda: bool(
                runtime_platform.capabilities
                .offline_speech_recognition
                and db.setting(
                    "windows_transcription_fallback",
                    True,
                )
            ),
        ),
        parent=parent,
        language=service_language,
    )
    local_tts = _local_speech_engine(
        runtime_platform,
        parent,
        language=service_language,
    )
    cloud_tts = OpenAITTS(parent, language=service_language)
    azure_tts = AzureSpeechTTS(parent)
    azure_hd_tts = AzureSpeechTTS(parent)
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
        realtime_speech_output=_realtime_speech_output(
            runtime_platform,
            parent,
            language=service_language,
        ),
        backup_manager=backup_manager,
        speech_providers=create_builtin_speech_registry(
            local_tts,
            cloud_tts,
            azure_tts,
            azure_hd_tts,
            system_capabilities=system_capabilities,
        ),
        azure_speech=azure_tts,
        azure_hd_speech=azure_hd_tts,
        azure_secret_store=azure_secret_store,
        azure_hd_secret_store=azure_hd_secret_store,
        secret_store_factory=secret_factory,
        platform_services=runtime_platform,
    )
