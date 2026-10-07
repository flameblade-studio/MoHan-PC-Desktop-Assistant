from __future__ import annotations

lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from dataclasses import field as dataclass_field
lazy from typing import Protocol

lazy from domain.character_pack.character_data import load_mohan_character_data
lazy from domain.language_support import localized_voice_instructions
lazy from domain.speech_providers import (
    AZURE_HD_SPEECH_PROVIDER,
    AZURE_SPEECH_PROVIDER,
    OPENAI_REALTIME_PROVIDER,
    OPENAI_SPEECH_PROVIDER,
    SYSTEM_LOCAL_PROVIDER,
)


class ComboDataPort(Protocol):
    """Minimal combo-box boundary needed by voice-setting serialization."""

    def currentText(self) -> str: ...

    def currentIndex(self) -> int: ...

    def itemText(self, index: int, /) -> str: ...

    def itemData(self, index: int, /, role: int = 256) -> object: ...


class VoiceSettingsPort(Protocol):
    """Minimal settings boundary needed by the voice-default migration."""

    def setting(self, key: str, default: object = None) -> object: ...

    def set_setting(self, key: str, value: object) -> None: ...


@dataclass(frozen=True, slots=True)
class QueuedSpeech:
    text: str
    requested_state: str
    intensity: float = 0.5
    source: str = "conversation"
    delivery_token: str = ""
    completed: Callable[[bool], None] | None = dataclass_field(
        default=None,
        repr=False,
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class SpeechCredentials:
    openai_api_key: str = dataclass_field(repr=False)
    azure_api_key: str = dataclass_field(repr=False)
    azure_region: str
    azure_hd_api_key: str = dataclass_field(repr=False)
    azure_hd_region: str


@dataclass(frozen=True, slots=True)
class SecretInputPolicy:
    saved_key: str
    saved_fallback: str
    title_key: str
    title_fallback: str
    error_key: str
    error_fallback: str


OPENAI_SECRET_POLICY = SecretInputPolicy(
    saved_key="api_key_saved",
    saved_fallback="已安全保存（留空不變）",
    title_key="api_key",
    title_fallback="OpenAI API 金鑰",
    error_key="api_key_save_failed",
    error_fallback="請檢查設定後安全保存 OpenAI API 金鑰：{error}",
)
AZURE_SECRET_POLICY = SecretInputPolicy(
    saved_key="azure_key_saved",
    saved_fallback="已由作業系統安全保存（留空不變）",
    title_key="azure_key",
    title_fallback="Azure Speech 金鑰",
    error_key="azure_key_save_failed",
    error_fallback="請檢查設定後安全保存 Azure Speech 金鑰：{error}",
)
AZURE_HD_SECRET_POLICY = SecretInputPolicy(
    saved_key="azure_hd_key_saved",
    saved_fallback="Dragon HD S0 金鑰已由 Windows 加密保存（留空不變）",
    title_key="azure_hd_key",
    title_fallback="Dragon HD S0 金鑰",
    error_key="azure_hd_key_save_failed",
    error_fallback="請檢查設定後安全保存 Dragon HD S0 金鑰：{error}",
)


_VOICE_PROFILE = load_mohan_character_data().voice
MOHAN_VOICE_DEFAULTS = _VOICE_PROFILE
VOICE_GENERATION_PROMPT = _VOICE_PROFILE.instructions["zh-TW"]
DEFAULT_TTS_VOICE = _VOICE_PROFILE.default_tts_voice
DEFAULT_CLOUD_VOICE = _VOICE_PROFILE.default_cloud_voice
DEFAULT_REALTIME_VOICE = _VOICE_PROFILE.default_realtime_voice
ONECORE_VOICE_PREFIX = _VOICE_PROFILE.system_local.onecore_prefix

# Single source of truth for the voice-volume default.  The dashboard slider,
# the startup volume application, and the gesture-mute path must all agree, or
# a user who never touched the slider gets different loudness per code path.
DEFAULT_VOICE_RATE = _VOICE_PROFILE.default_rate
DEFAULT_VOICE_VOLUME_PERCENT = _VOICE_PROFILE.default_volume_percent

VOICE_ENGINE_SYSTEM = SYSTEM_LOCAL_PROVIDER
# Compatibility export for extensions written before the provider ID became
# platform-neutral.
VOICE_ENGINE_WINDOWS = VOICE_ENGINE_SYSTEM
VOICE_ENGINE_OPENAI = OPENAI_SPEECH_PROVIDER
VOICE_ENGINE_REALTIME = OPENAI_REALTIME_PROVIDER
VOICE_ENGINE_AZURE = AZURE_SPEECH_PROVIDER
VOICE_ENGINE_AZURE_HD = AZURE_HD_SPEECH_PROVIDER

OPENAI_VOICE_ORDER = _VOICE_PROFILE.openai.voice_order
REALTIME_UNSUPPORTED_TTS_VOICES = _VOICE_PROFILE.openai.realtime_unsupported
REALTIME_VOICES = tuple(
    voice
    for voice in OPENAI_VOICE_ORDER
    if voice not in REALTIME_UNSUPPORTED_TTS_VOICES
)
TTS_VOICES = OPENAI_VOICE_ORDER


def combo_data_or_custom_text(
    combo: ComboDataPort,
    fallback: str = "",
) -> str:
    """Persist stable item data while preserving editable custom values."""

    text = combo.currentText().strip()
    index = combo.currentIndex()
    if index >= 0 and text == combo.itemText(index).strip():
        return str(combo.itemData(index) or text or fallback)
    return text or fallback


def migrate_voice_defaults(db: VoiceSettingsPort) -> None:
    if bool(db.setting("voice_prompt_v1204_migrated", False)):
        return
    language = str(db.setting("ui_language", "zh-TW"))
    db.set_setting(
        "voice_instructions",
        localized_voice_instructions(language, VOICE_GENERATION_PROMPT),
    )
    db.set_setting("tts_voice", _VOICE_PROFILE.default_tts_voice)
    db.set_setting("cloud_voice", _VOICE_PROFILE.default_cloud_voice)
    db.set_setting("realtime_voice", _VOICE_PROFILE.default_realtime_voice)
    db.set_setting("voice_prompt_v1204_migrated", True)
