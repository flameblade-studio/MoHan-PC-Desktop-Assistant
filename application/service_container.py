from __future__ import annotations

lazy import sqlite3
lazy import threading
lazy import os
lazy import logging
lazy from collections.abc import Callable
lazy from dataclasses import dataclass, field
lazy from pathlib import Path
lazy from typing import Protocol

lazy from PySide6.QtCore import QObject
lazy from PySide6.QtGui import QRegion

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
lazy from application.character_runtime_bootstrap import (
    ACTIVE_CHARACTER_ENV,
    DEFAULT_CHARACTER_ID,
    SUPPORTED_CHARACTER_IDS as _SUPPORTED_CHARACTER_IDS,
    activate_product_character_runtime,
)
lazy from application.cloud_vision_runtime import CloudVisionRuntime
lazy from application.character_profile_defaults import (
    seed_character_profile_settings,
)
lazy from application.cloud_vision_ui_bridge import (
    CloudVisionRuntimeService,
    CloudVisionServiceFactoryPort,
    StoredVisionAuthorizationSource,
)
lazy from application.native_acceleration import NativeAcceleration
lazy from application.presentation_ports import (
    AIWorkerPort,
    PresentationPorts,
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
    default_character_display_name,
)
lazy from domain.character_source import (
    CharacterSource,
    active_character_source,
)
lazy from domain.character_renderer_compatibility import validated_renderer_rig
lazy from domain.language_support import (
    DEFAULT_UI_LANGUAGE,
    canonical_ui_language,
    localized_transcription_prompt,
)
lazy from domain.constants import (
    CHARACTER_ASSET_PATHS,
    POSE_ATLAS_LAYERED_RELATIVE_ROOT,
    POSE_ATLAS_RELATIVE_ROOT,
)
lazy from domain.outfit_pack import set_official_pack_id_reservations
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
lazy from infrastructure.app_resources import resource_path, set_autostart
lazy from infrastructure.backup_manager import BackupManager
lazy from infrastructure.bundled_character_source import (
    LegacyMohanCharacterSource,
)
lazy from infrastructure.installed_character_packs import (
    CharacterPackInstallError,
    load_development_character_pack_archive,
    load_installed_character_pack,
    list_installed_character_packs,
)
lazy from infrastructure.db import StudioDB
lazy from infrastructure.face_assets import validate_face_assets
lazy from infrastructure.core_hand_regions import load_core_hand_regions
lazy from infrastructure.layered_face_renderer import (
    ExasperatedSourceBindings,
    LayeredParametricFaceRenderer,
    load_layered_face_assets,
)
lazy from infrastructure.layered_full_body_renderer import (
    LayeredFullBodyRenderer,
    load_layered_full_body_assets,
)
lazy from infrastructure.outfit_source_bound_expressions import (
    OutfitSourceBoundExpressionProvider,
)
lazy from infrastructure.full_body_display_placement import load_full_body_display_placement
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.exasperated_candidate_appearance import ExasperatedCandidateAppearance
lazy from infrastructure.exasperated_candidate_assets import (
    FORMAL_ASSET_RELATIVE_DIR,
    validate_formal_exasperated_install,
)
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


_CHARACTER_SELECTION_LOGGER = logging.getLogger("mohan.character_selection")
SUPPORTED_CHARACTER_IDS = _SUPPORTED_CHARACTER_IDS


def create_character_source(character_id: str) -> CharacterSource:
    """Build one bundled or installed source and keep MoHan on rejection."""

    root = resource_path(".")
    try:
        source = activate_product_character_runtime(
            root,
            character_id=character_id,
            development_archive_loader=load_development_character_pack_archive,
            installed_loader=load_installed_character_pack,
        )
    except RuntimeError as error:
        if error.__cause__ is not None:
            bundled_source = LegacyMohanCharacterSource(root)
            _reserve_official_pack_id_reservations(
                bundled_source,
                bundled_source=bundled_source,
            )
        raise
    bundled_source = (
        source
        if source.character_id == DEFAULT_CHARACTER_ID
        else LegacyMohanCharacterSource(root)
    )
    _reserve_official_pack_id_reservations(
        source,
        bundled_source=bundled_source,
    )
    return source


def create_default_character_source() -> CharacterSource:
    """Select the launch-configured character while keeping MoHan as default."""

    return create_character_source(
        os.environ.get(ACTIVE_CHARACTER_ENV, DEFAULT_CHARACTER_ID)
    )


def _reserve_official_pack_id_reservations(
    source: CharacterSource,
    *,
    bundled_source: CharacterSource,
    data_root: Path | None = None,
) -> None:
    """Refresh IDs from bundled, installed, and currently active sources."""

    try:
        installed_sources = list_installed_character_packs(data_root=data_root)
    except CharacterPackInstallError:
        installed_sources = ()
        reservations_complete = False
        _CHARACTER_SELECTION_LOGGER.exception("Official appearance ID scan failed")
    else:
        reservations_complete = True
    sources = (bundled_source, *installed_sources, source)
    pack_ids: set[str] = set()
    for candidate in sources:
        defaults = candidate.appearance.appearance_defaults
        pack_ids.update((defaults.outfit_pack_id, defaults.makeup_pack_id))
    set_official_pack_id_reservations(pack_ids, complete=reservations_complete)


@dataclass
class CompanionServices:
    """Explicit dependencies owned by one companion-window runtime."""

    db: StudioDB
    secret_store: SecretStorePort = field(
        repr=False,
    )
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


class _ProductionVoiceCatalog:
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

    return _create_presentation_ports(active_character_source())


def _create_presentation_ports(character_source: CharacterSource) -> PresentationPorts:
    """Build presentation adapters from the already selected character source."""

    asset_root = character_source.assets.asset_root
    official_pack_roots = getattr(
        character_source.assets,
        "official_pack_roots",
        (asset_root / "assets" / "official-packs",),
    )
    shared_hand_region_provider: Callable[[str], QRegion] | None = None
    hand_region_loaded = False

    def shared_hand_regions() -> Callable[[str], QRegion] | None:
        nonlocal hand_region_loaded, shared_hand_region_provider
        if not hand_region_loaded:
            shared_hand_region_provider = load_core_hand_regions(asset_root)
            hand_region_loaded = True
        return shared_hand_region_provider

    def outfit_overlay_factory(on_stale_body_profile=None):
        return ActiveOutfitOverlay(
            presentation_contracts.default_data_dir() / "outfits",
            asset_root,
            on_stale_body_profile=on_stale_body_profile,
            visible_hand_region=shared_hand_regions(),
            official_pack_root=official_pack_roots,
        )

    def face_renderer_factory() -> LayeredParametricFaceRenderer:
        source_bound = hasattr(character_source, "appearance")
        if source_bound:
            validated_renderer_rig(character_source)
        configured = os.environ.get("MOHAN_EXASPERATED_CANDIDATE_DIR")
        candidate_dir = None
        face_manifest = None
        authority_dir = None
        detachable_dir = None
        if source_bound:
            face_layer_root = character_source.assets.resolve_path(
                str(CHARACTER_ASSET_PATHS["halfbody_layers"])
            )
            authority_dir = character_source.assets.resolve_path(
                str(CHARACTER_ASSET_PATHS["halfbody_root"])
            )
            detachable_dir = character_source.assets.resolve_optional_path(
                str(CHARACTER_ASSET_PATHS["halfbody_detachable"])
            )
            face_manifest = load_layered_face_assets(face_layer_root)
            if getattr(character_source, "character_id", None) == DEFAULT_CHARACTER_ID:
                if configured is None:
                    candidate_dir = resource_path(FORMAL_ASSET_RELATIVE_DIR).resolve()
                    validate_formal_exasperated_install(candidate_dir)
                else:
                    candidate_dir = Path(configured)
                    if not candidate_dir.is_absolute():
                        raise ValueError(
                            "Exasperated candidate directory must be absolute."
                        )
                    candidate_dir = candidate_dir.resolve()
        elif configured is None:
            candidate_dir = resource_path(FORMAL_ASSET_RELATIVE_DIR).resolve()
            validate_formal_exasperated_install(candidate_dir)
        else:
            candidate_dir = Path(configured)
            if not candidate_dir.is_absolute():
                raise ValueError("Exasperated candidate directory must be absolute.")
            candidate_dir = candidate_dir.resolve()
        appearance_dir = (
            candidate_dir / "appearance" if candidate_dir is not None else None
        )
        candidate_appearance = None
        if (
            candidate_dir is not None
            and appearance_dir is not None
            and appearance_dir.exists()
        ):
            candidate_appearance = ExasperatedCandidateAppearance.load(
                appearance_dir, official_pack_root=official_pack_roots,
            )
            candidate_appearance.store = presentation_contracts.default_data_dir() / "outfits"
        elif candidate_dir is not None and configured is None:
            raise FileNotFoundError(f"Default exasperated appearance is missing: {appearance_dir}")
        return LayeredParametricFaceRenderer(
            manifest=face_manifest,
            outfit_overlay=outfit_overlay_factory(),
            authority_dir=authority_dir,
            detachable_dir=detachable_dir,
            use_detachable=detachable_dir is not None,
            exasperated_candidate_dir=candidate_dir,
            exasperated_source_bindings=ExasperatedSourceBindings(
                appearance_overlay=candidate_appearance,
                expression_provider=OutfitSourceBoundExpressionProvider(
                    presentation_contracts.default_data_dir() / "outfits",
                    official_pack_root=official_pack_roots,
                ),
            ),
        )

    def full_body_renderer_factory(outfit_overlay=None):
        if not hasattr(character_source, "appearance"):
            # Keep the legacy structural test seam for older callers that pass
            # a display-placement-only stub rather than a CharacterSource.
            return LayeredFullBodyRenderer(
                outfit_overlay=outfit_overlay,
                display_placement=load_full_body_display_placement(
                    character_source.assets.resolve_path(POSE_ATLAS_RELATIVE_ROOT)
                ),
            )
        validated_renderer_rig(character_source)
        layered_root = character_source.assets.resolve_path(
            POSE_ATLAS_LAYERED_RELATIVE_ROOT
        )
        authority_root = character_source.assets.resolve_path(POSE_ATLAS_RELATIVE_ROOT)
        manifest = load_layered_full_body_assets(layered_root)
        return LayeredFullBodyRenderer(
            manifest=manifest,
            outfit_overlay=outfit_overlay,
            authority_root=authority_root,
            display_placement=load_full_body_display_placement(authority_root),
        )

    return PresentationPorts(
        ai_worker_factory=_create_ai_worker,
        voice_catalog=_ProductionVoiceCatalog(),
        profile_manager_factory=PortableProfileManager,
        update_manager_factory=UpdateManager,
        portable_secret_binder=bind_dashboard_portable_secrets,
        autostart_configurator=set_autostart,
        validate_face_assets=validate_face_assets,
        face_renderer_factory=face_renderer_factory,
        visible_windows=visible_windows,
        official_pack_roots=official_pack_roots,
        outfit_overlay_factory=outfit_overlay_factory,
        full_body_renderer_factory=full_body_renderer_factory,
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
    """Resolve the stdlib HTTP factory lazily; the SDK remains outside this path."""

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
    """Build the optional cloud path while preserving the client and request boundary."""

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


def _initialize_backup_manager(
    db: StudioDB,
    data_path: Path,
) -> BackupManager | None:
    manager: BackupManager | None = None
    try:
        manager = BackupManager(db, data_path / "backups")
        manager.automatic_if_due()
    except (OSError, RuntimeError, sqlite3.Error) as error:
        if manager is not None and not getattr(
            manager,
            "automatic_backup_failed",
            False,
        ):
            record_failure = getattr(manager, "record_automatic_failure", None)
            if callable(record_failure):
                record_failure(error)
    return manager


def create_default_services(
    data_path: Path,
    listener_script: Path,
    parent: QObject | None = None,
    platform_services: PlatformServicePort | None = None,
    *,
    ui_language: str | None = None,
) -> CompanionServices:
    runtime_platform = platform_services or current_platform_services()
    character_source = active_character_source()
    data_path.mkdir(parents=True, exist_ok=True)
    _reserve_official_pack_id_reservations(
        character_source,
        bundled_source=LegacyMohanCharacterSource(resource_path(".")),
        data_root=data_path,
    )
    db = StudioDB(data_path / "mohan.db")
    language_value = (
        ui_language
        if ui_language is not None
        else db.setting("ui_language", DEFAULT_UI_LANGUAGE)
    )
    service_language = canonical_ui_language(str(language_value))
    seed_character_profile_settings(db, character_source, service_language, protect_source_voice=not db.existing_install or character_source.character_id != DEFAULT_CHARACTER_ID)
    pcm_acceleration = NativeAcceleration()
    # Migrate at the composition boundary so headless and UI startup paths
    # share the same canonical provider setting.
    migrate_speech_provider_setting(db)
    backup_manager = _initialize_backup_manager(db, data_path)
    secret_factory = platform_secret_store_factory(runtime_platform)
    secret_store = secret_factory(
        data_path / "openai-key.dpapi",
        f"{default_character_display_name('en')} OpenAI API key",
    )
    azure_secret_store = secret_factory(
        data_path / "azure-speech-key.dpapi",
        f"{default_character_display_name('en')} Azure Speech key",
    )
    azure_hd_secret_store = secret_factory(
        data_path / "azure-dragon-hd-key.dpapi",
        f"{default_character_display_name('en')} Azure Dragon HD Speech key",
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
        presentation_ports=_create_presentation_ports(character_source),
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
