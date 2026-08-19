from __future__ import annotations

lazy import sqlite3
lazy import threading
lazy from collections.abc import Callable
lazy from dataclasses import dataclass, field
lazy from pathlib import Path
lazy from typing import Protocol

lazy from PySide6.QtCore import QObject

lazy from integrations.speech import (
    OpenAITTS,
    SpeechListener,
    SpeechListenerProviders,
    UnavailableSystemTTS,
    WindowsTTS,
    female_windows_voices_for_language,
    preferred_windows_voice,
    windows_voices,
)
lazy from application import presentation_ports as presentation_contracts
lazy from application.cloud_vision_runtime import CloudVisionRuntime
lazy from application.cloud_vision_ui_bridge import (
    CloudVisionRuntimeService,
    CloudVisionServiceFactoryPort,
    StoredVisionAuthorizationSource,
)
lazy from application.native_acceleration import NativeAcceleration
lazy from application.presentation_ports import (
    AIWorkerPort,
    PresentationPorts,
    VoiceCatalogPort,
    bind_dashboard_portable_secrets,
)
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
lazy from domain.language_support import (
    DEFAULT_UI_LANGUAGE,
    canonical_ui_language,
    localized_transcription_prompt,
)
lazy from domain.openai_vision_preferences import VisionDetail
lazy from domain.speech_providers import (
    SYSTEM_LOCAL_PROVIDER,
    SpeechProviderCapabilities,
    create_builtin_speech_registry,
    migrate_speech_provider_setting,
)
lazy from domain.vision_provider_contracts import (
    VisionFrameRequest,
    VisionProviderResult,
    VisionResultStatus,
)
lazy from infrastructure.app_resources import set_autostart
lazy from infrastructure.backup_manager import BackupManager
lazy from infrastructure.db import StudioDB
lazy from infrastructure.face_assets import validate_face_assets
lazy from infrastructure.face_renderer import ParametricFaceRenderer
lazy from infrastructure.multimodal_model_provider import (
    MultimodalModelPaths,
    OpenCVMultiModalModelProvider,
)
lazy from infrastructure.platform_contracts import PlatformServicePort
lazy from infrastructure.platform_services import current_platform_services
lazy from infrastructure.profile_transfer import PortableProfileManager
lazy from infrastructure.secret_store import platform_secret_store_factory
lazy from infrastructure.updater import UpdateManager
lazy from infrastructure.windows_tools import visible_windows
lazy from integrations import ai_client as ai_integration
lazy from integrations.ai_client import (
    AIWorker,
)
lazy from integrations.azure_regions import (
    azure_region_options,
    azure_region_supports_hd_flash,
)
lazy from integrations.azure_speech import (
    AzureSpeechTTS,
    azure_female_voices,
    azure_hd_female_voices,
    normalize_azure_region,
)
lazy from integrations.realtime_speech_output import RealtimeSpeechOutput
lazy from integrations.realtime_voice import RealtimeVoiceClient


@dataclass
class CompanionServices:
    """Explicit dependencies owned by one companion-window runtime."""

    db: StudioDB
    secret_store: SecretStorePort = field(repr=False)
    local_tts: LocalSpeechEnginePort
    cloud_tts: CloudSpeechEnginePort
    realtime: RealtimeVoicePort
    listener: SpeechListenerPort
    presentation_ports: PresentationPorts
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
    cloud_vision_service_factory: CloudVisionServiceFactoryPort | None = field(
        default=None,
        repr=False,
    )
    dense_face_provider_factory: Callable[[], object] | None = field(
        default=None,
        repr=False,
    )


class _ProductionVoiceCatalog(VoiceCatalogPort):
    """Expose the production voice adapters through one presentation port."""

    @staticmethod
    def azure_region_options(
        language: str,
        *,
        hd_only: bool = False,
        hd_flash_only: bool = False,
    ) -> tuple[tuple[str, str], ...]:
        return azure_region_options(
            language,
            hd_only=hd_only,
            hd_flash_only=hd_flash_only,
        )

    @staticmethod
    def azure_region_supports_hd_flash(identifier: str) -> bool:
        return azure_region_supports_hd_flash(identifier)

    @staticmethod
    def normalize_azure_region(region: str) -> str:
        return normalize_azure_region(region)

    @staticmethod
    def azure_female_voices(language: str) -> tuple[str, ...]:
        return azure_female_voices(language)

    @staticmethod
    def azure_hd_female_voices(
        language: str,
        *,
        include_flash: bool = True,
    ) -> tuple[str, ...]:
        return azure_hd_female_voices(
            language,
            include_flash=include_flash,
        )

    @staticmethod
    def windows_voices() -> list[tuple[str, str]]:
        return windows_voices()

    @staticmethod
    def female_windows_voices_for_language(
        voices: list[tuple[str, str]],
        target_language: str,
    ) -> list[tuple[str, str]]:
        return female_windows_voices_for_language(voices, target_language)

    @staticmethod
    def preferred_windows_voice(
        voices: list[tuple[str, str]],
        saved: str = "",
        target_language: str = "zh-TW",
    ) -> str:
        return preferred_windows_voice(voices, saved, target_language)


def _create_ai_worker(
    request: presentation_contracts.AIWorkerRequest,
) -> AIWorkerPort:
    """Translate the inward request contract to the OpenAI adapter request."""

    return AIWorker(
        ai_integration.AIWorkerRequest(
            user_text=request.user_text,
            mode=request.mode,
            history=request.history,
            api_key=request.api_key,
            memories=request.memories,
            model=request.model,
            persona=request.persona,
            assistant_name=request.assistant_name,
            user_title=request.user_title,
            response_language=request.response_language,
            prompt_cache_telemetry=request.prompt_cache_telemetry,
            prompt_cache_token_evidence=request.prompt_cache_token_evidence,
        )
    )


def create_presentation_ports() -> PresentationPorts:
    """Build every presentation adapter once at the composition boundary."""

    return PresentationPorts(
        ai_worker_factory=_create_ai_worker,
        voice_catalog=_ProductionVoiceCatalog(),
        profile_manager_factory=PortableProfileManager,
        update_manager_factory=UpdateManager,
        portable_secret_binder=bind_dashboard_portable_secrets,
        autostart_configurator=set_autostart,
        validate_face_assets=validate_face_assets,
        face_renderer_factory=ParametricFaceRenderer,
        visible_windows=visible_windows,
    )


class _VisionProviderPort(Protocol):
    def analyze(self, request: VisionFrameRequest) -> VisionProviderResult: ...

    def cancel(self, operation_id: int) -> None: ...


VisionProviderFactory = Callable[
    [str, Callable[[], str]],
    _VisionProviderPort,
]


class _SecretBackedVisionProvider:
    """Load the OS-protected key only after runtime authorization succeeds."""

    def __init__(
        self,
        secret_store: SecretStorePort,
        authorization_source: StoredVisionAuthorizationSource,
        provider_factory: VisionProviderFactory,
    ) -> None:
        self._secret_store = secret_store
        self._authorization_source = authorization_source
        self._provider_factory = provider_factory
        self._lock = threading.Lock()
        self._active: dict[int, _VisionProviderPort] = {}

    def analyze(self, request: VisionFrameRequest) -> VisionProviderResult:
        authorization = self._authorization_source.load()
        provider = self._provider_factory(
            self._safe_key(),
            lambda: authorization.preferences.model_id,
        )
        with self._lock:
            self._active[request.operation_id] = provider
        try:
            return provider.analyze(request)
        finally:
            with self._lock:
                self._active.pop(request.operation_id, None)

    def cancel(self, operation_id: int) -> None:
        with self._lock:
            provider = self._active.get(operation_id)
        if provider is not None:
            provider.cancel(operation_id)

    def _safe_key(self) -> str:
        try:
            return self._secret_store.load()
        except OSError, RuntimeError, TypeError, ValueError:
            return ""


class _UnavailableVisionProvider:
    def analyze(self, request: VisionFrameRequest) -> VisionProviderResult:
        return VisionProviderResult(
            request.operation_id,
            VisionResultStatus("transport_unavailable"),
            request.model or "",
            VisionDetail(request.detail.value),
        )

    def cancel(self, _operation_id: int) -> None:
        return None


def _default_vision_provider_factory(
    api_key: str,
    model_selector: Callable[[], str],
) -> _VisionProviderPort:
    """Resolve the stdlib HTTP factory lazily; never fall back to the SDK."""

    try:
        from integrations import openai_vision_provider

        factory = openai_vision_provider.create_openai_vision_provider
    except AttributeError, ImportError, ModuleNotFoundError:
        return _UnavailableVisionProvider()
    if not callable(factory):
        return _UnavailableVisionProvider()
    try:
        return factory(api_key, model_selector=model_selector)
    except OSError, RuntimeError, TypeError, ValueError:
        return _UnavailableVisionProvider()


def create_cloud_vision_service_factory(
    provider_factory: VisionProviderFactory = _default_vision_provider_factory,
) -> CloudVisionServiceFactoryPort:
    """Build the optional cloud path without creating a client or request."""

    def create(
        secret_store: SecretStorePort,
        authorization_source: StoredVisionAuthorizationSource,
    ) -> CloudVisionRuntimeService:
        provider = _SecretBackedVisionProvider(
            secret_store,
            authorization_source,
            provider_factory,
        )
        return CloudVisionRuntimeService(
            CloudVisionRuntime(provider, authorization_source)
        )

    return create


def _local_speech_engine(
    platform_services: PlatformServicePort,
    parent: QObject | None,
    *,
    language: str,
    pcm_acceleration: NativeAcceleration,
) -> LocalSpeechEnginePort:
    if platform_services.capabilities.system_local_speech:
        return WindowsTTS(
            parent,
            language=language,
            pcm_acceleration=pcm_acceleration,
        )
    return UnavailableSystemTTS(
        f"{platform_services.capabilities.display_name} 本機語音尚未完成實機驗證。",
        parent,
    )


def _realtime_speech_output(
    platform_services: PlatformServicePort,
    parent: QObject | None,
    *,
    language: str,
    pcm_acceleration: NativeAcceleration,
) -> RealtimeSpeechOutput:
    return RealtimeSpeechOutput(
        AzureSpeechTTS(parent, pcm_acceleration=pcm_acceleration),
        AzureSpeechTTS(parent, pcm_acceleration=pcm_acceleration),
        _local_speech_engine(
            platform_services,
            parent,
            language=language,
            pcm_acceleration=pcm_acceleration,
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
    pcm_acceleration = NativeAcceleration()
    # Migrate at the composition boundary so headless and UI startup paths
    # share the same canonical provider setting.
    migrate_speech_provider_setting(db)
    try:
        backup_manager: BackupManager | None = BackupManager(
            db,
            data_path / "backups",
        )
        backup_manager.automatic_if_due()
    except OSError, RuntimeError, sqlite3.Error:
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
                        assistant_name=str(db.setting("assistant_name", "")),
                        user_title=str(db.setting("user_title", "")),
                        organization_name=str(db.setting("organization_name", "")),
                        wake_word=str(db.setting("wake_word", "")),
                    ),
                )
            ),
            windows_fallback=lambda: bool(
                runtime_platform.capabilities.offline_speech_recognition
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
        pcm_acceleration=pcm_acceleration,
    )
    cloud_tts = OpenAITTS(
        parent,
        language=service_language,
        pcm_acceleration=pcm_acceleration,
    )
    azure_tts = AzureSpeechTTS(
        parent,
        pcm_acceleration=pcm_acceleration,
    )
    azure_hd_tts = AzureSpeechTTS(
        parent,
        pcm_acceleration=pcm_acceleration,
    )
    system_capabilities = SpeechProviderCapabilities(
        provider_id=SYSTEM_LOCAL_PROVIDER,
        offline=runtime_platform.capabilities.system_local_speech,
        requires_api_key=False,
        verified_female_catalog=(
            runtime_platform.capabilities.verified_female_voice_catalog
        ),
        supports_streaming=False,
        supported_languages=(
            ("installed",) if runtime_platform.capabilities.system_local_speech else ()
        ),
    )
    return CompanionServices(
        db=db,
        secret_store=secret_store,
        local_tts=local_tts,
        cloud_tts=cloud_tts,
        realtime=RealtimeVoiceClient(
            parent,
            pcm_acceleration=pcm_acceleration,
        ),
        listener=listener,
        presentation_ports=create_presentation_ports(),
        realtime_speech_output=_realtime_speech_output(
            runtime_platform,
            parent,
            language=service_language,
            pcm_acceleration=pcm_acceleration,
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
        cloud_vision_service_factory=create_cloud_vision_service_factory(),
        dense_face_provider_factory=lambda: OpenCVMultiModalModelProvider(
            MultimodalModelPaths.from_directory(
                Path(__file__).resolve().parents[1] / "assets" / "vision-models"
            )
        ),
    )
