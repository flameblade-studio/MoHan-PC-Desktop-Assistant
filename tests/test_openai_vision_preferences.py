from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.openai_vision_authorization import OpenAIVisionAuthorization
lazy from domain.openai_vision_preferences import (
    OPENAI_VISION_MODELS,
    OpenAIVisionPreferences,
    UnsupportedOpenAIVisionPreferencesVersion,
    VisionDetail,
    VisionTriggerPolicy,
    export_openai_vision_preferences,
    import_openai_vision_preferences,
    preferences_from_mapping,
)


def assert_defaults_and_continuous_opt_in_are_fail_closed() -> None:
    preferences = OpenAIVisionPreferences()
    assert preferences.enabled is False
    assert preferences.cloud_vision_enabled is False
    assert preferences.model_id == "gpt-5.6-luna"
    assert preferences.detail is VisionDetail.LOW
    assert preferences.raw_image_storage_enabled is False
    assert preferences.permits_cloud_frame() is False
    enabled = OpenAIVisionPreferences(
        enabled=True,
        cloud_vision_enabled=True,
    )
    assert enabled.permits_cloud_frame() is True
    assert OpenAIVisionPreferences(enabled=True).permits_cloud_frame() is False
    assert (
        OpenAIVisionPreferences(cloud_vision_enabled=True).permits_cloud_frame()
        is False
    )


def assert_catalog_and_round_trip_are_canonical() -> None:
    assert tuple(model.model_id for model in OPENAI_VISION_MODELS) == (
        "gpt-5.6-sol",
        "gpt-5.6-terra",
        "gpt-5.6-luna",
    )
    expected = OpenAIVisionPreferences(
        enabled=True,
        cloud_vision_enabled=True,
        model_id=OPENAI_VISION_MODELS[2].model_id,
        detail=VisionDetail.ORIGINAL,
        trigger_policy=VisionTriggerPolicy.EVENT_WITH_NOTICE,
        daily_limit=80,
        per_minute_limit=4,
        object_semantics_enabled=True,
        web_search_suggestions_enabled=True,
    )
    payload = export_openai_vision_preferences(expected)
    assert import_openai_vision_preferences(payload) == expected
    assert "api_key" not in repr(payload).lower()
    authorization = OpenAIVisionAuthorization.from_preferences(
        expected, key_available=True
    )
    assert authorization.enabled is True
    assert authorization.key_available is True
    assert "image" not in repr(authorization).lower()
    assert "key=" not in repr(authorization).lower()


def assert_corruption_and_unknown_fields_are_safe() -> None:
    defaults = OpenAIVisionPreferences()
    corruptions = (
        {"enabled": "yes"},
        {"model_id": "unknown"},
        {"daily_limit": 1, "per_minute_limit": 2},
        {"raw_image_storage_enabled": True},
    )
    for raw in corruptions:
        loaded = preferences_from_mapping(raw)
        assert loaded.raw_image_storage_enabled is False
        assert loaded.permits_cloud_frame() is False
        if raw == {"raw_image_storage_enabled": True}:
            assert loaded == defaults
    unknown = preferences_from_mapping({"future": {"ignored": True}})
    assert unknown == defaults
    try:
        import_openai_vision_preferences(
            {
                "format": "mohan-openai-vision-preferences",
                "version": 2,
                "preferences": {},
            }
        )
    except UnsupportedOpenAIVisionPreferencesVersion:
        pass
    else:
        raise AssertionError("unsupported version unexpectedly succeeded")


def run() -> None:
    assert_defaults_and_continuous_opt_in_are_fail_closed()
    assert_catalog_and_round_trip_are_canonical()
    assert_corruption_and_unknown_fields_are_safe()
    print("OPENAI_VISION_PREFERENCES_OK")


if __name__ == "__main__":
    run()
