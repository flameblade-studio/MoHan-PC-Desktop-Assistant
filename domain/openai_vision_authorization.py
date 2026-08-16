from __future__ import annotations

lazy from dataclasses import dataclass

lazy from domain.openai_vision_preferences import (
    OpenAIVisionPreferences,
    VisionDetail,
    VisionTriggerPolicy,
)


@dataclass(frozen=True, slots=True)
class OpenAIVisionAuthorization:
    """Saved continuous authorization; it contains no image or secret."""

    enabled: bool
    model_id: str
    detail: VisionDetail
    trigger_policy: VisionTriggerPolicy
    daily_limit: int
    per_minute_limit: int
    object_semantics_enabled: bool
    web_search_suggestions_enabled: bool
    key_available: bool

    @classmethod
    def from_preferences(
        cls,
        preferences: OpenAIVisionPreferences,
        *,
        key_available: bool,
    ) -> OpenAIVisionAuthorization:
        return cls(
            enabled=(preferences.enabled and preferences.cloud_vision_enabled),
            model_id=preferences.model_id,
            detail=preferences.detail,
            trigger_policy=preferences.trigger_policy,
            daily_limit=preferences.daily_limit,
            per_minute_limit=preferences.per_minute_limit,
            object_semantics_enabled=preferences.object_semantics_enabled,
            web_search_suggestions_enabled=(
                preferences.web_search_suggestions_enabled
            ),
            key_available=key_available is True,
        )
