from __future__ import annotations

"""Presentation-facing contracts and immutable request data.

This module is the inward-facing seam used by Qt presentation code.  It owns
no GUI objects and imports no adapter implementation; infrastructure and
integration implementations are supplied only by the composition root.
"""

lazy import os
lazy import re
lazy import sqlite3
lazy import sys
lazy from collections.abc import Callable, Mapping
lazy from dataclasses import dataclass, field
lazy from difflib import SequenceMatcher
lazy from pathlib import Path
lazy from typing import Any, Protocol

lazy from domain.contracts import (
    AzureSpeechEnginePort,
    ProfileDatabasePort,
    SecretStoreFactoryPort,
    SecretStorePort,
    SignalPort,
    SpeechListenerPort,
)
lazy from domain.language_support import canonical_ui_language
lazy from domain.prompt_cache import PromptCacheTelemetry, PromptCacheTokenEvidence
lazy from domain.safe_error import SafeError
lazy from domain.speech_providers import (
    AZURE_HD_SPEECH_PROVIDER,
    AZURE_SPEECH_PROVIDER,
    OPENAI_REALTIME_PROVIDER,
)

# Transcription-prompt heuristics.
MAX_TERM_LENGTH = 40
MAX_TERMS = 16
MIN_COMPARISON_LENGTH = 16
MIN_SUBSTRING_LENGTH = 20
SIMILARITY_THRESHOLD = 0.82

DEFAULT_TEXT_MODEL = "gpt-5.6-luna"
TEXT_MODELS = (
    "gpt-5.6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
)
DEFAULT_TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
DEFAULT_TRANSCRIPTION_PROMPT = (
    "請將使用者語音準確轉寫為文字，保留專有名詞、數字與其他語言，"
    "不要翻譯或改寫原意。"
)

REALTIME_OUTPUT_OPENAI = OPENAI_REALTIME_PROVIDER
REALTIME_OUTPUT_AZURE = AZURE_SPEECH_PROVIDER
REALTIME_OUTPUT_AZURE_HD = AZURE_HD_SPEECH_PROVIDER

PROFILE_EXTENSION = ".mohan-profile"
MANIFEST_FILENAME = "manifest.json"
SENSITIVE_FILENAME = "sensitive.enc"
SENSITIVE_MANIFEST_KEY = "sensitive"


class PresentationDatabasePort(ProfileDatabasePort, Protocol):
    """Database operations consumed by the desktop presentation."""

    def close(self) -> None: ...

    def settings_snapshot(self) -> object: ...

    def restore_settings_snapshot(self, snapshot: object) -> None: ...

    def __getattr__(self, name: str) -> Callable[..., Any]: ...


@dataclass(frozen=True, slots=True)
class PlatformPaths:
    data: Path
    config: Path
    cache: Path


@dataclass(frozen=True, slots=True)
class PlatformCapabilities:
    platform_id: str
    display_name: str
    system_local_speech: bool
    verified_female_voice_catalog: bool
    offline_speech_recognition: bool
    secure_secret_storage: bool
    desktop_autostart: bool
    native_window_management: bool
    published_installers: tuple[str, ...]


class PlatformServicePort(Protocol):
    paths: PlatformPaths
    capabilities: PlatformCapabilities

    def set_autostart(
        self,
        enabled: bool,
        *,
        application_id: str,
        command: str,
    ) -> None: ...

    def open_path(self, path: Path) -> None: ...


class _PresentationFallbackPlatformService:
    """Compatibility-only platform facts for directly constructed widgets.

    Production composition supplies the complete platform adapter.  This
    small fallback preserves the established ``FirstRunWizard(db)`` API while
    keeping operating-system adapters out of the presentation layer.
    """

    def __init__(self) -> None:
        platform_id = (
            "windows"
            if sys.platform.startswith("win")
            else "macos"
            if sys.platform == "darwin"
            else "linux"
        )
        home = Path.home()
        if platform_id == "windows":
            root = Path(os.environ.get("LOCALAPPDATA") or home) / "YanJianStudio" / "MoHan"
            config = root
            cache = root / "cache"
            display_name = "Windows"
        elif platform_id == "macos":
            root = home / "Library" / "Application Support" / "YanJianStudio" / "MoHan"
            config = root
            cache = home / "Library" / "Caches" / "YanJianStudio" / "MoHan"
            display_name = "macOS"
        else:
            suffix = Path("YanJianStudio") / "MoHan"
            root = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share") / suffix
            config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config") / suffix
            cache = Path(os.environ.get("XDG_CACHE_HOME") or home / ".cache") / suffix
            display_name = "Linux"
        self.paths = PlatformPaths(root, config, cache)
        windows = platform_id == "windows"
        self.capabilities = PlatformCapabilities(
            platform_id=platform_id,
            display_name=display_name,
            system_local_speech=windows,
            verified_female_voice_catalog=windows,
            offline_speech_recognition=windows,
            secure_secret_storage=windows,
            desktop_autostart=windows,
            native_window_management=windows,
            published_installers=("portable-zip", "exe", "msi") if windows else (),
        )

    def set_autostart(
        self,
        enabled: bool,
        *,
        application_id: str,
        command: str,
    ) -> None:
        del enabled, application_id, command
        raise RuntimeError("Platform services must be injected before changing autostart.")

    def open_path(self, path: Path) -> None:
        del path
        raise RuntimeError("Platform services must be injected before opening a path.")


def fallback_platform_services() -> PlatformServicePort:
    """Return immutable platform facts for backwards-compatible UI creation."""

    return _PresentationFallbackPlatformService()


def default_data_dir(platform: PlatformServicePort | None = None) -> Path:
    """Resolve the historical profile location without an outer-layer import."""

    override = str(os.environ.get("MOHAN_DATA_DIR", "")).strip()
    root = Path(override).expanduser() if override else (
        platform or fallback_platform_services()
    ).paths.data
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass(frozen=True, slots=True)
class PlatformProgressUpdate:
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


_DURATION_FORMATS = frozendict(
    {
        "zh-TW": ("{hours} 小時 {minutes} 分鐘", "{minutes} 分鐘"),
        "zh-CN": ("{hours} 小时 {minutes} 分钟", "{minutes} 分钟"),
        "en": ("{hours} h {minutes} min", "{minutes} min"),
        "ja-JP": ("{hours} 時間 {minutes} 分", "{minutes} 分"),
    }
)


def format_duration(seconds: int, language: str = "zh-TW") -> str:
    hours, rest = divmod(max(0, int(seconds)), 3600)
    minutes = rest // 60
    with_hours, minutes_only = _DURATION_FORMATS[
        canonical_ui_language(language)
    ]
    template = with_hours if hours else minutes_only
    return template.format(hours=hours, minutes=minutes)


@dataclass(frozen=True, slots=True)
class AIWorkerRequest:
    user_text: str
    mode: str
    history: tuple[dict[str, str], ...] = ()
    api_key: str = field(default="", repr=False)
    memories: str = ""
    model: str = DEFAULT_TEXT_MODEL
    persona: str = ""
    assistant_name: str = "墨寒"
    user_title: str = "主上"
    response_language: str = "zh-TW"
    prompt_cache_telemetry: Callable[[PromptCacheTelemetry], None] | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    prompt_cache_token_evidence: PromptCacheTokenEvidence | None = field(
        default=None,
        repr=False,
        compare=False,
    )


class AIWorkerSignalsPort(Protocol):
    done: SignalPort
    failed: SignalPort


class AIWorkerPort(Protocol):
    signals: AIWorkerSignalsPort

    def run(self) -> None: ...


AIWorkerFactory = Callable[[AIWorkerRequest], AIWorkerPort]


@dataclass(frozen=True, slots=True)
class RealtimeSessionConfig:
    model: str = "gpt-realtime-2.1-mini"
    voice: str = "coral"
    transcription_model: str = DEFAULT_TRANSCRIPTION_MODEL
    transcription_language: str = "zh"
    transcription_prompt: str = ""
    noise_reduction: str = "near_field"
    turn_detection: str = "server_vad"
    external_transcription: bool = True
    output_mode: str = REALTIME_OUTPUT_OPENAI
    locale: str = "zh-TW"


@dataclass(frozen=True, slots=True)
class RealtimeVoiceRequest:
    api_key: str = field(repr=False)
    instructions: str
    memory_context: str
    session: RealtimeSessionConfig
    recent_context: str = ""
    echo_guard: bool = True


@dataclass(frozen=True, slots=True)
class AzureRealtimeVoice:
    api_key: str = field(repr=False)
    region: str
    voice: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip() and self.region.strip() and self.voice.strip())


@dataclass(frozen=True, slots=True)
class LocalRealtimeVoice:
    available: bool = False
    voice: str = ""
    rate: int = -1


@dataclass(frozen=True, slots=True)
class RealtimeSpeechOutputConfig:
    mode: str = REALTIME_OUTPUT_OPENAI
    locale: str = "zh-TW"
    azure: AzureRealtimeVoice = AzureRealtimeVoice("", "", "")
    azure_hd: AzureRealtimeVoice = AzureRealtimeVoice("", "", "")
    local: LocalRealtimeVoice = LocalRealtimeVoice()


@dataclass(frozen=True, slots=True)
class RealtimeSpeechOutputConfigRequest:
    """Typed provider settings crossing into the Realtime output factory."""

    mode: str
    locale: str
    azure: AzureRealtimeVoice
    azure_hd: AzureRealtimeVoice
    local: LocalRealtimeVoice


class RealtimeSpeechOutputPort(Protocol):
    speaking_changed: SignalPort
    playback_guard_changed: SignalPort
    viseme_cue: SignalPort
    status_changed: SignalPort
    failed: SignalPort

    def configure(self, config: RealtimeSpeechOutputConfig) -> None: ...

    def set_volume(self, volume_percent: int, muted: bool = False) -> None: ...

    def begin_response(self, *args: Any, **kwargs: Any) -> None: ...

    def add_text(self, *args: Any, **kwargs: Any) -> None: ...

    def finish_response(self, *args: Any, **kwargs: Any) -> None: ...

    def cancel(self, *args: Any, **kwargs: Any) -> None: ...


RealtimeSpeechOutputConfigFactory = Callable[[RealtimeSpeechOutputConfigRequest], RealtimeSpeechOutputConfig]


def create_realtime_output_config(request: RealtimeSpeechOutputConfigRequest) -> RealtimeSpeechOutputConfig:
    """Build the provider-neutral Realtime output configuration."""

    return RealtimeSpeechOutputConfig(
        mode=request.mode,
        locale=request.locale,
        azure=request.azure,
        azure_hd=request.azure_hd,
        local=request.local,
    )


def sanitize_realtime_transcription_prompt(prompt: str) -> str:
    """Keep ASR hints short so instructions cannot become a transcript."""

    raw = (prompt or "").strip()
    if not raw:
        return ""
    marker = re.search(
        r"(?:常用詞|常用词|專有名詞|专有名词|Common terms|"
        r"よく使う語句)\s*[：:]",
        raw,
        flags=re.IGNORECASE,
    )
    term_source = raw[marker.end() :] if marker else raw
    term_source = re.split(
        r"(?:請保留|請使用|不要改寫|不要翻譯|请保留|请使用|"
        r"不要改写|不要翻译|Please|Preserve|Keep the speaker|"
        r"do not|日本語で|固有名詞|話者の意図|書き換え)",
        term_source,
        maxsplit=1,
    )[0]
    terms: list[str] = []
    for value in re.split(r"[、,，。；;\n]+", term_source):
        normalized = value.strip(" 「」『』：:")
        if (
            normalized
            and len(normalized) <= MAX_TERM_LENGTH
            and not re.prefixmatch(
                r"^(?:請|使用|保留|不要|轉錄|語言|请|准确|"
                r"Please|Preserve|Keep|do not|日本語|固有名詞)",
                normalized,
                flags=re.IGNORECASE,
            )
            and normalized not in terms
        ):
            terms.append(normalized)
        if len(terms) >= MAX_TERMS:
            break
    return "可能出現的專有名詞：" + "、".join(terms) + "。" if terms else ""


def resembles_transcription_prompt(text: str, *prompts: str) -> bool:
    def comparison_text(value: str) -> str:
        return re.sub(r"[\W_]+", "", (value or "").casefold())

    candidate = comparison_text(text)
    if len(candidate) < MIN_COMPARISON_LENGTH:
        return False
    for prompt in prompts:
        reference = comparison_text(prompt)
        if len(reference) < MIN_COMPARISON_LENGTH:
            continue
        if candidate == reference:
            return True
        shorter, longer = sorted((candidate, reference), key=len)
        if len(shorter) >= MIN_SUBSTRING_LENGTH and shorter in longer:
            return True
        if SequenceMatcher(None, candidate, reference).ratio() >= SIMILARITY_THRESHOLD:
            return True
    return False


@dataclass(frozen=True, slots=True)
class AzureSpeechRegion:
    identifier: str
    traditional_chinese: str
    simplified_chinese: str
    english: str
    japanese: str
    supports_hd: bool = False
    supports_hd_flash: bool = False

    def label(self, language: str) -> str:
        locale = canonical_ui_language(language)
        names = {
            "zh-TW": self.traditional_chinese,
            "zh-CN": self.simplified_chinese,
            "en": self.english,
            "ja-JP": self.japanese,
        }
        return f"{names[locale]} — {self.identifier}"


AZURE_SPEECH_REGIONS = (
    AzureSpeechRegion("eastasia", "東亞", "东亚", "East Asia", "東アジア"),
    AzureSpeechRegion("southeastasia", "東南亞", "东南亚", "Southeast Asia", "東南アジア", True, True),
    AzureSpeechRegion("australiaeast", "澳洲東部", "澳大利亚东部", "Australia East", "オーストラリア東部"),
    AzureSpeechRegion("centralindia", "印度中部", "印度中部", "Central India", "インド中部", True),
    AzureSpeechRegion("japaneast", "日本東部", "日本东部", "Japan East", "東日本"),
    AzureSpeechRegion("japanwest", "日本西部", "日本西部", "Japan West", "西日本"),
    AzureSpeechRegion("koreacentral", "韓國中部", "韩国中部", "Korea Central", "韓国中部"),
    AzureSpeechRegion("southafricanorth", "南非北部", "南非北部", "South Africa North", "南アフリカ北部"),
    AzureSpeechRegion("canadacentral", "加拿大中部", "加拿大中部", "Canada Central", "カナダ中部", True),
    AzureSpeechRegion("canadaeast", "加拿大東部", "加拿大东部", "Canada East", "カナダ東部"),
    AzureSpeechRegion("northeurope", "北歐", "北欧", "North Europe", "北ヨーロッパ"),
    AzureSpeechRegion("westeurope", "西歐", "西欧", "West Europe", "西ヨーロッパ", True, True),
    AzureSpeechRegion("francecentral", "法國中部", "法国中部", "France Central", "フランス中部", True),
    AzureSpeechRegion("germanywestcentral", "德國中西部", "德国中西部", "Germany West Central", "ドイツ中西部"),
    AzureSpeechRegion("italynorth", "義大利北部", "意大利北部", "Italy North", "イタリア北部"),
    AzureSpeechRegion("norwayeast", "挪威東部", "挪威东部", "Norway East", "ノルウェー東部"),
    AzureSpeechRegion("swedencentral", "瑞典中部", "瑞典中部", "Sweden Central", "スウェーデン中部", True),
    AzureSpeechRegion("switzerlandnorth", "瑞士北部", "瑞士北部", "Switzerland North", "スイス北部"),
    AzureSpeechRegion("switzerlandwest", "瑞士西部", "瑞士西部", "Switzerland West", "スイス西部"),
    AzureSpeechRegion("uksouth", "英國南部", "英国南部", "UK South", "英国南部"),
    AzureSpeechRegion("ukwest", "英國西部", "英国西部", "UK West", "英国西部"),
    AzureSpeechRegion("uaenorth", "阿拉伯聯合大公國北部", "阿联酋北部", "UAE North", "アラブ首長国連邦北部"),
    AzureSpeechRegion("brazilsouth", "巴西南部", "巴西南部", "Brazil South", "ブラジル南部"),
    AzureSpeechRegion("qatarcentral", "卡達中部", "卡塔尔中部", "Qatar Central", "カタール中部"),
    AzureSpeechRegion("centralus", "美國中部", "美国中部", "Central US", "米国中部"),
    AzureSpeechRegion("eastus", "美國東部", "美国东部", "East US", "米国東部", True, True),
    AzureSpeechRegion("eastus2", "美國東部 2", "美国东部 2", "East US 2", "米国東部 2", True),
    AzureSpeechRegion("northcentralus", "美國中北部", "美国中北部", "North Central US", "米国中北部"),
    AzureSpeechRegion("southcentralus", "美國中南部", "美国中南部", "South Central US", "米国中南部"),
    AzureSpeechRegion("westcentralus", "美國中西部", "美国中西部", "West Central US", "米国中西部"),
    AzureSpeechRegion("westus", "美國西部", "美国西部", "West US", "米国西部"),
    AzureSpeechRegion("westus2", "美國西部 2", "美国西部 2", "West US 2", "米国西部 2", True),
    AzureSpeechRegion("westus3", "美國西部 3", "美国西部 3", "West US 3", "米国西部 3"),
)


def azure_region_options(
    language: str,
    *,
    hd_only: bool = False,
    hd_flash_only: bool = False,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (region.label(language), region.identifier)
        for region in AZURE_SPEECH_REGIONS
        if (not hd_only or region.supports_hd)
        and (not hd_flash_only or region.supports_hd_flash)
    )


def azure_region_identifiers(
    *,
    hd_only: bool = False,
    hd_flash_only: bool = False,
) -> tuple[str, ...]:
    return tuple(
        region.identifier
        for region in AZURE_SPEECH_REGIONS
        if (not hd_only or region.supports_hd)
        and (not hd_flash_only or region.supports_hd_flash)
    )


def azure_region_supports_hd_flash(identifier: str) -> bool:
    normalized = str(identifier or "").strip().lower()
    return any(
        region.identifier == normalized and region.supports_hd_flash
        for region in AZURE_SPEECH_REGIONS
    )


_AZURE_FEMALE_VOICES = frozendict(
    {
        "zh-TW": ("zh-TW-HsiaoChenNeural", "zh-TW-HsiaoYuNeural"),
        "zh-CN": (
            "zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural", "zh-CN-XiaochenNeural",
            "zh-CN-XiaohanNeural", "zh-CN-XiaomengNeural", "zh-CN-XiaomoNeural",
            "zh-CN-XiaoqiuNeural", "zh-CN-XiaorouNeural", "zh-CN-XiaoruiNeural",
        ),
        "en": (
            "en-US-AvaMultilingualNeural", "en-US-AmandaMultilingualNeural",
            "en-US-CoraMultilingualNeural", "en-US-JennyMultilingualNeural",
        ),
        "ja-JP": (
            "ja-JP-NanamiNeural", "ja-JP-AoiNeural", "ja-JP-MayuNeural",
            "ja-JP-ShioriNeural",
        ),
    }
)
_AZURE_HD_FEMALE_VOICES = frozendict(
    {
        "zh-CN": (
            "zh-CN-Xiaochen:DragonHDLatestNeural",
            "zh-CN-Xiaoyue:DragonHDOmniLatestNeural",
            "zh-CN-Maroonallegro:DragonHDOmniLatestNeural",
            "zh-CN-Xiaoxiao:DragonHDFlashLatestNeural",
            "zh-CN-Xiaoxiao2:DragonHDFlashLatestNeural",
            "zh-CN-Xiaochen:DragonHDFlashLatestNeural",
            "zh-CN-Xiaoyi:DragonHDFlashLatestNeural",
            "zh-CN-Xiaoyu:DragonHDFlashLatestNeural",
            "zh-CN-Xiaohan:DragonHDFlashLatestNeural",
            "zh-CN-Xiaoshuang:DragonHDFlashLatestNeural",
            "zh-CN-Xiaoyou:DragonHDFlashLatestNeural",
        ),
        "en": (
            "en-US-Ava:DragonHDLatestNeural", "en-US-Aria:DragonHDLatestNeural",
            "en-US-Emma:DragonHDLatestNeural", "en-US-Emma2:DragonHDLatestNeural",
            "en-US-Jenny:DragonHDLatestNeural", "en-US-Nova:DragonHDLatestNeural",
            "en-US-Phoebe:DragonHDLatestNeural", "en-US-Serena:DragonHDLatestNeural",
        ),
        "ja-JP": ("ja-JP-Nanami:DragonHDLatestNeural",),
    }
)


def azure_female_voices(language: str) -> tuple[str, ...]:
    locale = canonical_ui_language(language)
    if locale == "zh-CN":
        return (*_AZURE_FEMALE_VOICES["zh-CN"], *_AZURE_FEMALE_VOICES["zh-TW"])
    if locale == "zh-TW":
        return (*_AZURE_FEMALE_VOICES["zh-TW"], *_AZURE_FEMALE_VOICES["zh-CN"])
    return _AZURE_FEMALE_VOICES[locale]


def azure_hd_female_voices(
    language: str,
    *,
    include_flash: bool = True,
) -> tuple[str, ...]:
    locale = canonical_ui_language(language)
    voices = _AZURE_HD_FEMALE_VOICES[locale if locale in {"en", "ja-JP"} else "zh-CN"]
    return voices if include_flash else tuple(
        voice for voice in voices if ":DragonHDFlash" not in voice
    )


def normalize_azure_region(region: str) -> str:
    normalized = str(region or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9]+", normalized):
        raise ValueError("invalid_region")
    return normalized


def female_windows_voices_for_language(
    voices: list[tuple[str, str]],
    target_language: str,
) -> list[tuple[str, str]]:
    family = str(target_language or "").strip().lower().split("-", 1)[0]
    return [
        (name, culture)
        for name, culture in voices
        if culture.lower().split("-", 1)[0] == family
        and not any(
            marker in name.casefold()
            for marker in ("david", "mark", "zhiwei", "yunxi", "yunyang")
        )
    ]


def preferred_windows_voice(
    voices: list[tuple[str, str]],
    saved: str = "",
    target_language: str = "zh-TW",
) -> str:
    filtered = [
        (name, culture)
        for name, culture in voices
        if not any(
            marker in name.casefold()
            for marker in ("david", "mark", "zhiwei", "yunxi", "yunyang")
        )
    ]
    installed = dict(filtered)
    if saved in installed:
        return saved
    target = str(target_language or "").strip().lower()
    family = target.split("-", 1)[0]
    if target in {"zh", "zh-tw"}:
        for keyword in ("Yating", "Hanhan"):
            for name, culture in filtered:
                if keyword.casefold() in name.casefold() and culture.lower() == "zh-tw":
                    return name
    for name, culture in filtered:
        if culture.lower() == target:
            return name
    for name, culture in filtered:
        if culture.lower().split("-", 1)[0] == family:
            return name
    return filtered[0][0] if filtered else ""


class VoiceCatalogPort(Protocol):
    def azure_region_options(
        self,
        language: str,
        *,
        hd_only: bool = False,
        hd_flash_only: bool = False,
    ) -> tuple[tuple[str, str], ...]: ...

    def azure_region_supports_hd_flash(self, identifier: str) -> bool: ...

    def normalize_azure_region(self, region: str) -> str: ...

    def azure_female_voices(self, language: str) -> tuple[str, ...]: ...

    def azure_hd_female_voices(
        self,
        language: str,
        *,
        include_flash: bool = True,
    ) -> tuple[str, ...]: ...

    def windows_voices(self) -> list[tuple[str, str]]: ...

    def female_windows_voices_for_language(
        self,
        voices: list[tuple[str, str]],
        target_language: str,
    ) -> list[tuple[str, str]]: ...

    def preferred_windows_voice(
        self,
        voices: list[tuple[str, str]],
        saved: str = "",
        target_language: str = "zh-TW",
    ) -> str: ...


class FaceRendererPort(Protocol):
    def render(self, base: Any, motion: Any, layers: Any, *, aperture: float | None = None) -> Any: ...

    def render_overlay(
        self,
        base: Any,
        source: Any,
        *,
        mask: Any | None = None,
        opacity: float = 1.0,
    ) -> Any: ...


class ProfileManifestPort(Protocol):
    created_at: str
    snapshot_id: str
    source_installation_id: str
    assistant_name: str
    organization_name: str
    record_counts: Mapping[str, int]


class ProfileImportResultPort(Protocol):
    manifest: ProfileManifestPort
    backup_path: Path
    imported_counts: Mapping[str, int]
    sensitive_payload: Mapping[str, object] | None


class PortableProfileManagerPort(Protocol):
    def inspect_profile(self, source: Path) -> tuple[Any, Path, Any]: ...

    def export_profile(self, target: Path, **kwargs: Any) -> tuple[Path, Any]: ...

    def import_profile(self, source: Path, **kwargs: Any) -> Any: ...

    def restore_import(self, result: Any) -> None: ...


PortableProfileManagerFactory = Callable[[PresentationDatabasePort, Path], PortableProfileManagerPort]


class ProfileTransferError(RuntimeError):
    """Safe failure shared by every portable-profile boundary."""

    def __init__(self, message: str, *, safe_error: SafeError | None = None) -> None:
        self.safe_error = safe_error
        super().__init__(str(safe_error) if safe_error is not None else message)


class _UnavailableProfileManager:
    """Patchable fail-closed fallback for directly constructed UI tests."""

    @staticmethod
    def _unavailable(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise ProfileTransferError("Profile manager was not injected.")

    inspect_profile = _unavailable
    export_profile = _unavailable
    import_profile = _unavailable
    restore_import = _unavailable


def unavailable_profile_manager_factory(database: PresentationDatabasePort, backup_dir: Path) -> PortableProfileManagerPort:
    del database, backup_dir
    return _UnavailableProfileManager()


class InstallerAssetPort(Protocol):
    kind: str
    name: str
    url: str
    sha256: str
    size: int


class ReleaseInfoPort(Protocol):
    version: str
    tag: str
    release_url: str
    notes: str
    published_at: str
    prerelease: bool

    def preferred_installer(self) -> InstallerAssetPort: ...


class UpdateManagerPort(Protocol):
    def check(self, channel: str) -> ReleaseInfoPort | None: ...

    def download(
        self,
        asset: InstallerAssetPort,
        progress: Callable[[int], None] | None = None,
    ) -> Path: ...


UpdateManagerFactory = Callable[[str, str, Path], UpdateManagerPort]


class _UnavailableUpdateManager:
    @staticmethod
    def check(channel: str) -> None:
        del channel
        raise RuntimeError("Update manager was not injected.")

    @staticmethod
    def download(*args: Any, **kwargs: Any) -> Path:
        del args, kwargs
        raise RuntimeError("Update manager was not injected.")


def unavailable_update_manager_factory(repository: str, current_version: str, download_dir: Path) -> UpdateManagerPort:
    del repository, current_version, download_dir
    return _UnavailableUpdateManager()


class SafeBoundaryError(Protocol):
    safe_error: SafeError | None


PortableSecretBinder = Callable[[object, Path], object]
AutostartConfigurator = Callable[[bool, PlatformServicePort], None]
FaceAssetValidator = Callable[[Path], tuple[Path, ...]]
FaceRendererFactory = Callable[[], FaceRendererPort]
VisibleWindowsProvider = Callable[[], list[dict[str, Any]]]


class OutfitOverlayPort(Protocol):
    """Apply the currently selected, validated appearance to one authored view."""

    def apply(self, frame: Any, view_id: str) -> Any: ...

    def layer_count(self, view_id: str) -> int: ...


class _NoOutfitOverlay:
    @staticmethod
    def apply(frame: Any, view_id: str) -> Any:
        del view_id
        return frame

    @staticmethod
    def layer_count(view_id: str) -> int:
        del view_id
        return 0


OutfitOverlayFactory = Callable[..., OutfitOverlayPort]


def no_outfit_overlay_factory(**_options: object) -> OutfitOverlayPort:
    return _NoOutfitOverlay()


class FullBodyRendererPort(Protocol):
    """Compose one authored 24-view-ring full-body frame from a face-motion frame."""

    def render_view(self, view_id: str, motion: Any, **options: Any) -> Any: ...
    def render_static_preview(self, view_id: str) -> Any: ...

# ``None`` means no full-body compositor was injected (offline dashboards).
FullBodyRendererFactory = Callable[..., FullBodyRendererPort | None]


def no_full_body_renderer_factory(**_options: object) -> None:
    return None


@dataclass(frozen=True, slots=True)
class PresentationPorts:
    """Outer adapters required by presentation, supplied at composition."""

    ai_worker_factory: AIWorkerFactory
    voice_catalog: VoiceCatalogPort
    profile_manager_factory: PortableProfileManagerFactory
    update_manager_factory: UpdateManagerFactory
    portable_secret_binder: PortableSecretBinder
    autostart_configurator: AutostartConfigurator
    validate_face_assets: FaceAssetValidator
    face_renderer_factory: FaceRendererFactory
    visible_windows: VisibleWindowsProvider
    realtime_output_config_factory: RealtimeSpeechOutputConfigFactory = (
        create_realtime_output_config
    )
    outfit_overlay_factory: OutfitOverlayFactory = no_outfit_overlay_factory
    full_body_renderer_factory: FullBodyRendererFactory = no_full_body_renderer_factory


_PORTABLE_SECRET_IDS = frozenset(
    {
        "openai",
        "azure_speech",
        "azure_dragon_hd",
        "home_assistant",
        "oauth_google",
        "oauth_microsoft",
        "oauth_github",
        "face_identities",
        "gesture_templates",
    }
)


@dataclass(frozen=True, slots=True)
class PortableSecretBinding:
    stores: Mapping[str, SecretStorePort] = field(repr=False)

    def collect(self) -> dict[str, object]:
        secrets: dict[str, str] = {}
        for secret_id in sorted(self.stores):
            value = self.stores[secret_id].load()
            if not isinstance(value, str):
                raise TypeError("A protected secret has an invalid type.")
            if value:
                secrets[secret_id] = value
        return {
            "format": "mohan-portable-secrets",
            "version": 1,
            "secrets": secrets,
        }

    def apply(self, payload: Mapping[str, object]) -> None:
        if (
            not isinstance(payload, Mapping)
            or payload.get("format") != "mohan-portable-secrets"
            or payload.get("version") != 1
            or not isinstance(payload.get("secrets"), Mapping)
        ):
            raise RuntimeError("The protected-secret payload is invalid.")
        secrets = payload["secrets"]
        assert isinstance(secrets, Mapping)
        if not set(secrets) <= set(self.stores):
            raise RuntimeError("A protected-secret store is unavailable.")
        previous = {secret_id: self.stores[secret_id].load() for secret_id in secrets}
        attempted: list[str] = []
        try:
            for secret_id, value in secrets.items():
                if not isinstance(secret_id, str) or not isinstance(value, str) or not value:
                    raise RuntimeError("A protected-secret value is invalid.")
                attempted.append(secret_id)
                self.stores[secret_id].save(value)
        except (OSError, RuntimeError, TypeError, ValueError):
            rollback_complete = True
            for secret_id in reversed(attempted):
                try:
                    previous_value = previous[secret_id]
                    if previous_value:
                        self.stores[secret_id].save(previous_value)
                    else:
                        self.stores[secret_id].clear()
                except (OSError, RuntimeError, TypeError, ValueError):
                    rollback_complete = False
            message = (
                "Protected-secret import failed; previous values were restored."
                if rollback_complete
                else "Protected-secret import failed and rollback was incomplete."
            )
            raise RuntimeError(message) from None


def bind_dashboard_portable_secrets(
    dependencies: DashboardServices,
    data_path: Path,
) -> PortableSecretBinding:
    """Create isolated protected stores without exposing adapter types to UI."""

    factory = dependencies.secret_store_factory
    if (
        dependencies.azure_secret_store is None
        or dependencies.azure_hd_secret_store is None
        or factory is None
    ):
        raise RuntimeError("Dashboard secret boundaries are incomplete.")
    root = Path(data_path)
    generated = {
        secret_id: factory(root / filename, description)
        for secret_id, filename, description in (
            ("home_assistant", "home-assistant-token.dpapi", "MoHan Home Assistant token"),
            ("oauth_google", "oauth-google.dpapi", "MoHan google OAuth token"),
            ("oauth_microsoft", "oauth-microsoft.dpapi", "MoHan microsoft OAuth token"),
            ("oauth_github", "oauth-github.dpapi", "MoHan github OAuth token"),
            ("face_identities", "face-identities.dpapi", "MoHan local face identity templates"),
            ("gesture_templates", "gesture-templates.dpapi", "MoHan local gesture skeleton templates"),
        )
    }
    stores = {
        "openai": dependencies.secret_store,
        "azure_speech": dependencies.azure_secret_store,
        "azure_dragon_hd": dependencies.azure_hd_secret_store,
        **generated,
    }
    if set(stores) != _PORTABLE_SECRET_IDS or len({id(store) for store in stores.values()}) != len(stores):
        raise RuntimeError("Dashboard secret boundaries are invalid.")
    return PortableSecretBinding(stores)


@dataclass(frozen=True, slots=True)
class DashboardServices:
    """Application-owned dashboard composition data."""

    listener: SpeechListenerPort
    secret_store: SecretStorePort
    azure_secret_store: SecretStorePort | None = None
    azure_hd_secret_store: SecretStorePort | None = None
    azure_speech: AzureSpeechEnginePort | None = None
    azure_hd_speech: AzureSpeechEnginePort | None = None
    secret_store_factory: SecretStoreFactoryPort | None = None
    platform_services: PlatformServicePort | None = None
    cloud_vision_service_factory: object | None = None
    dense_face_provider_factory: Callable[[], object] | None = None
    presentation_ports: PresentationPorts | None = None


def safe_error_from_exception(error: BaseException) -> SafeError | None:
    value = getattr(error, "safe_error", None)
    return value if isinstance(value, SafeError) else None


def is_boundary_failure(error: BaseException) -> bool:
    return isinstance(
        error,
        (OSError, RuntimeError, sqlite3.Error, TypeError, ValueError),
    )


__all__ = (
    "DEFAULT_TEXT_MODEL",
    "DEFAULT_TRANSCRIPTION_MODEL",
    "DEFAULT_TRANSCRIPTION_PROMPT",
    "MANIFEST_FILENAME",
    "PROFILE_EXTENSION",
    "REALTIME_OUTPUT_AZURE",
    "REALTIME_OUTPUT_AZURE_HD",
    "REALTIME_OUTPUT_OPENAI",
    "SENSITIVE_FILENAME",
    "SENSITIVE_MANIFEST_KEY",
    "TEXT_MODELS",
    "AIWorkerFactory",
    "AIWorkerPort",
    "AIWorkerRequest",
    "AutostartConfigurator",
    "AzureRealtimeVoice",
    "DashboardServices",
    "FaceRendererPort",
    "FullBodyRendererPort",
    "LocalRealtimeVoice",
    "PlatformCapabilities",
    "PlatformPaths",
    "PlatformProgressUpdate",
    "PlatformServicePort",
    "PresentationDatabasePort",
    "PresentationPorts",
    "ProfileImportResultPort",
    "ProfileManifestPort",
    "ProfileTransferError",
    "RealtimeSessionConfig",
    "RealtimeSpeechOutputConfig",
    "RealtimeSpeechOutputConfigFactory",
    "RealtimeSpeechOutputConfigRequest",
    "RealtimeSpeechOutputPort",
    "RealtimeVoiceRequest",
    "ReleaseInfoPort",
    "UpdateManagerFactory",
    "UpdateManagerPort",
    "VoiceCatalogPort",
    "bind_dashboard_portable_secrets",
    "create_realtime_output_config",
    "default_data_dir",
    "fallback_platform_services",
    "format_duration",
    "resembles_transcription_prompt",
    "safe_error_from_exception",
    "sanitize_realtime_transcription_prompt",
    "unavailable_profile_manager_factory",
    "unavailable_update_manager_factory",
)
