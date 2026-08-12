from __future__ import annotations

lazy import hmac
lazy import secrets
lazy import threading
lazy import time
lazy from collections.abc import Callable
lazy from dataclasses import dataclass, field
lazy from typing import Any

lazy from azure.cognitiveservices import speech as speechsdk

lazy from azure_regions import azure_region_supports_hd_flash

_CREDENTIAL_FINGERPRINT_SECRET = secrets.token_bytes(32)


@dataclass(frozen=True, slots=True)
class AzureVoiceCatalog:
    """One verified, region-specific Azure female voice catalogue."""

    region: str
    language: str
    hd_only: bool
    voices: tuple[str, ...]
    source: str


@dataclass(frozen=True, slots=True)
class _CachedCatalog:
    expires_at: float
    catalog: AzureVoiceCatalog


@dataclass(frozen=True, slots=True)
class _CatalogCacheKey:
    region: str
    language: str
    hd_only: bool
    credential_fingerprint: bytes = field(repr=False)


def _credential_fingerprint(api_key: str) -> bytes:
    """Return a process-local, irreversible credential identity."""

    return hmac.digest(
        _CREDENTIAL_FINGERPRINT_SECRET,
        api_key.encode("utf-8"),
        "sha256",
    )


def _language_locales(language: str) -> tuple[str, ...]:
    normalized = str(language or "").strip().lower()
    if normalized == "zh-cn":
        return ("zh-CN", "zh-TW")
    if normalized in {"en", "en-us"}:
        return ("en-US",)
    if normalized in {"ja", "ja-jp"}:
        return ("ja-JP",)
    return ("zh-TW", "zh-CN")


def _voice_value(voice: object, *names: str) -> str:
    for name in names:
        value = getattr(voice, name, "")
        if value:
            return str(value)
    return ""


def _is_female(voice: object) -> bool:
    raw_gender = getattr(voice, "gender", "")
    gender = str(getattr(raw_gender, "name", raw_gender))
    return gender.rsplit(".", 1)[-1].strip().lower() == "female"


def _voice_short_name(voice: object) -> str:
    return _voice_value(voice, "short_name", "shortName")


def _voice_locale(voice: object) -> str:
    return _voice_value(voice, "locale")


def _is_hd_voice(short_name: str) -> bool:
    return ":DragonHD" in short_name


def _filter_voices(
    voices: tuple[object, ...],
    language: str,
    *,
    hd_only: bool,
    include_flash: bool,
) -> tuple[str, ...]:
    locales = _language_locales(language)
    grouped: dict[str, list[str]] = {locale: [] for locale in locales}
    for voice in voices:
        if not _is_female(voice):
            continue
        locale = _voice_locale(voice)
        short_name = _voice_short_name(voice)
        if locale not in grouped or not short_name:
            continue
        is_hd = _is_hd_voice(short_name)
        if is_hd != hd_only:
            continue
        incompatible_standard_voice = (
            ":" in short_name or not short_name.endswith("Neural")
        )
        if not hd_only and incompatible_standard_voice:
            continue
        if not include_flash and ":DragonHDFlash" in short_name:
            continue
        grouped[locale].append(short_name)
    return tuple(
        dict.fromkeys(
            voice
            for locale in locales
            for voice in sorted(grouped[locale], key=str.casefold)
        )
    )


class AzureVoiceCatalogService:
    """Query Azure for female voices and retain only a short-lived cache.

    Subscription keys are passed directly to the SDK configuration and are
    never stored in this service, cache keys, exceptions, or diagnostics.
    A process-local, non-reversible fingerprint isolates cached catalogues
    belonging to different Azure credentials without exposing either key.
    """

    def __init__(
        self,
        *,
        cache_seconds: float = 3_600.0,
        clock: Callable[[], float] = time.monotonic,
        sdk_loader: Callable[[], Any] | None = None,
    ) -> None:
        self._cache_seconds = max(0.0, float(cache_seconds))
        self._clock = clock
        self._sdk_loader = sdk_loader or self._load_sdk
        self._cache: dict[_CatalogCacheKey, _CachedCatalog] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _load_sdk() -> Any:
        return speechsdk

    def query(
        self,
        api_key: str,
        region: str,
        language: str,
        *,
        hd_only: bool,
    ) -> AzureVoiceCatalog:
        cache_key = _CatalogCacheKey(
            region=region,
            language=language,
            hd_only=hd_only,
            credential_fingerprint=_credential_fingerprint(api_key),
        )
        now = self._clock()
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None and cached.expires_at > now:
                return cached.catalog

        sdk = self._sdk_loader()
        speech_config = sdk.SpeechConfig(subscription=api_key, region=region)
        synthesizer = sdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=None,
        )
        result = synthesizer.get_voices_async().get()
        voices = _filter_voices(
            tuple(getattr(result, "voices", ())),
            language,
            hd_only=hd_only,
            include_flash=(
                not hd_only or azure_region_supports_hd_flash(region)
            ),
        )
        if not voices:
            raise RuntimeError("Azure returned no matching female voices")
        catalog = AzureVoiceCatalog(
            region=region,
            language=language,
            hd_only=hd_only,
            voices=voices,
            source="azure",
        )
        with self._lock:
            self._cache[cache_key] = _CachedCatalog(
                expires_at=now + self._cache_seconds,
                catalog=catalog,
            )
        return catalog

    def invalidate(self, region: str | None = None) -> None:
        with self._lock:
            if region is None:
                self._cache.clear()
                return
            self._cache = {
                key: value
                for key, value in self._cache.items()
                if key.region != region
            }
