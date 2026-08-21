from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, fields
lazy from enum import StrEnum
lazy from typing import Final

PREFERENCES_FORMAT: Final = "mohan-openai-vision-preferences"
PREFERENCES_VERSION: Final = 1
MAX_DAILY_LIMIT = 1000
MAX_PER_MINUTE_LIMIT = 60


@dataclass(frozen=True, slots=True)
class VisionModel:
    model_id: str
    label: str


# The only source of supported cloud-vision model identifiers and labels.
OPENAI_VISION_MODELS: Final = (
    VisionModel("gpt-5.6-sol", "GPT-5.6 Sol"),
    VisionModel("gpt-5.6-terra", "GPT-5.6 Terra"),
    VisionModel("gpt-5.6-luna", "GPT-5.6 Luna"),
)
OPENAI_VISION_MODEL_IDS: Final = frozenset(
    model.model_id for model in OPENAI_VISION_MODELS
)
DEFAULT_OPENAI_VISION_MODEL: Final = OPENAI_VISION_MODELS[2].model_id


class VisionDetail(StrEnum):
    LOW = "low"
    AUTO = "auto"
    HIGH = "high"
    ORIGINAL = "original"


class VisionTriggerPolicy(StrEnum):
    MANUAL = "manual"
    EVENT_WITH_NOTICE = "event_with_notice"


MASTER_ENABLED_KEY: Final = "openai_vision_enabled"
CLOUD_ENABLED_KEY: Final = "openai_cloud_vision_enabled"
MODEL_KEY: Final = "openai_vision_model"
DETAIL_KEY: Final = "openai_vision_detail"
TRIGGER_POLICY_KEY: Final = "openai_vision_trigger_policy"
DAILY_LIMIT_KEY: Final = "openai_vision_daily_limit"
PER_MINUTE_LIMIT_KEY: Final = "openai_vision_per_minute_limit"
OBJECT_SEMANTICS_KEY: Final = "openai_vision_object_semantics_enabled"
WEB_SUGGESTIONS_KEY: Final = "openai_vision_web_suggestions_enabled"
RAW_IMAGE_STORAGE_KEY: Final = "openai_vision_raw_image_storage_enabled"

SETTING_KEYS: Final = (
    MASTER_ENABLED_KEY,
    CLOUD_ENABLED_KEY,
    MODEL_KEY,
    DETAIL_KEY,
    TRIGGER_POLICY_KEY,
    DAILY_LIMIT_KEY,
    PER_MINUTE_LIMIT_KEY,
    OBJECT_SEMANTICS_KEY,
    WEB_SUGGESTIONS_KEY,
    RAW_IMAGE_STORAGE_KEY,
)


class OpenAIVisionPreferencesError(RuntimeError):
    """A fixed-detail preference boundary error."""


class UnsupportedOpenAIVisionPreferencesVersion(OpenAIVisionPreferencesError):
    """The portable preference version cannot be interpreted safely."""


@dataclass(frozen=True, slots=True)
class OpenAIVisionPreferences:
    enabled: bool = False
    cloud_vision_enabled: bool = False
    model_id: str = DEFAULT_OPENAI_VISION_MODEL
    detail: VisionDetail = VisionDetail.LOW
    trigger_policy: VisionTriggerPolicy = VisionTriggerPolicy.MANUAL
    daily_limit: int = 20
    per_minute_limit: int = 2
    object_semantics_enabled: bool = False
    web_search_suggestions_enabled: bool = False
    raw_image_storage_enabled: bool = False

    def __post_init__(self) -> None:
        flags = (
            self.enabled,
            self.cloud_vision_enabled,
            self.object_semantics_enabled,
            self.web_search_suggestions_enabled,
            self.raw_image_storage_enabled,
        )
        if any(type(value) is not bool for value in flags):
            raise TypeError("OpenAI vision flags must be boolean.")
        if self.model_id not in OPENAI_VISION_MODEL_IDS:
            raise ValueError("OpenAI vision model is unsupported.")
        if not isinstance(self.detail, VisionDetail):
            raise TypeError("OpenAI vision detail is invalid.")
        if not isinstance(self.trigger_policy, VisionTriggerPolicy):
            raise TypeError("OpenAI vision trigger policy is invalid.")
        if type(self.daily_limit) is not int or not 1 <= self.daily_limit <= MAX_DAILY_LIMIT:
            raise ValueError("OpenAI vision daily limit is invalid.")
        if (
            type(self.per_minute_limit) is not int
            or not 1 <= self.per_minute_limit <= MAX_PER_MINUTE_LIMIT
            or self.per_minute_limit > self.daily_limit
        ):
            raise ValueError("OpenAI vision per-minute limit is invalid.")
        if self.raw_image_storage_enabled:
            raise ValueError("Raw image storage is forbidden.")

    def permits_cloud_frame(self) -> bool:
        """Report whether saved settings may authorize cloud frames."""

        return self.enabled and self.cloud_vision_enabled


def settings_payload(preferences: OpenAIVisionPreferences) -> dict[str, object]:
    _require_preferences(preferences)
    return {
        MASTER_ENABLED_KEY: preferences.enabled,
        CLOUD_ENABLED_KEY: preferences.cloud_vision_enabled,
        MODEL_KEY: preferences.model_id,
        DETAIL_KEY: preferences.detail.value,
        TRIGGER_POLICY_KEY: preferences.trigger_policy.value,
        DAILY_LIMIT_KEY: preferences.daily_limit,
        PER_MINUTE_LIMIT_KEY: preferences.per_minute_limit,
        OBJECT_SEMANTICS_KEY: preferences.object_semantics_enabled,
        WEB_SUGGESTIONS_KEY: preferences.web_search_suggestions_enabled,
        RAW_IMAGE_STORAGE_KEY: False,
    }


def preferences_from_mapping(raw: object) -> OpenAIVisionPreferences:
    defaults = OpenAIVisionPreferences()
    if not isinstance(raw, Mapping):
        return defaults
    try:
        return OpenAIVisionPreferences(
            enabled=_bool(raw, "enabled", defaults.enabled),
            cloud_vision_enabled=_bool(
                raw, "cloud_vision_enabled", defaults.cloud_vision_enabled
            ),
            model_id=_model(raw.get("model_id"), defaults.model_id),
            detail=_enum(raw.get("detail"), VisionDetail, defaults.detail),
            trigger_policy=_enum(
                raw.get("trigger_policy"),
                VisionTriggerPolicy,
                defaults.trigger_policy,
            ),
            daily_limit=_int(raw, "daily_limit", defaults.daily_limit),
            per_minute_limit=_int(
                raw, "per_minute_limit", defaults.per_minute_limit
            ),
            object_semantics_enabled=_bool(
                raw,
                "object_semantics_enabled",
                defaults.object_semantics_enabled,
            ),
            web_search_suggestions_enabled=_bool(
                raw,
                "web_search_suggestions_enabled",
                defaults.web_search_suggestions_enabled,
            ),
            raw_image_storage_enabled=False,
        )
    except (TypeError, ValueError):
        return defaults


def export_openai_vision_preferences(
    preferences: OpenAIVisionPreferences,
) -> dict[str, object]:
    _require_preferences(preferences)
    portable = {
        field.name: getattr(preferences, field.name)
        for field in fields(preferences)
    }
    portable["detail"] = preferences.detail.value
    portable["trigger_policy"] = preferences.trigger_policy.value
    portable["raw_image_storage_enabled"] = False
    return {
        "format": PREFERENCES_FORMAT,
        "version": PREFERENCES_VERSION,
        "preferences": portable,
    }


def import_openai_vision_preferences(
    payload: Mapping[str, object],
) -> OpenAIVisionPreferences:
    if not isinstance(payload, Mapping):
        return OpenAIVisionPreferences()
    if payload.get("format") != PREFERENCES_FORMAT:
        return OpenAIVisionPreferences()
    version = payload.get("version")
    if type(version) is not int or version != PREFERENCES_VERSION:
        raise UnsupportedOpenAIVisionPreferencesVersion(
            "OpenAI vision preference version is unsupported."
        )
    return preferences_from_mapping(payload.get("preferences"))


def _require_preferences(preferences: OpenAIVisionPreferences) -> None:
    if not isinstance(preferences, OpenAIVisionPreferences):
        raise OpenAIVisionPreferencesError(
            "OpenAI vision preferences are invalid."
        )


def _bool(raw: Mapping[str, object], key: str, default: bool) -> bool:
    value = raw.get(key, default)
    return value if type(value) is bool else default


def _int(raw: Mapping[str, object], key: str, default: int) -> int:
    value = raw.get(key, default)
    return value if type(value) is int else default


def _model(value: object, default: str) -> str:
    return value if isinstance(value, str) and value in OPENAI_VISION_MODEL_IDS else default


def _enum[EnumT](value: object, enum_type: type[EnumT], default: EnumT) -> EnumT:
    try:
        return enum_type(value)
    except (TypeError, ValueError):
        return default
