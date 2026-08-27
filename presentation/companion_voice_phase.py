"""Small voice-output state helpers used during speech-runtime startup."""

from __future__ import annotations

lazy from domain.app_profile import profile_setting
lazy from domain.safe_error_localization import safe_error_message
lazy from domain.speech_configuration import VOICE_ENGINE_SYSTEM
lazy from presentation.ui_localization import ui_text


def speech_audio_state(db, *, session_muted: bool = False) -> tuple[bool, bool]:
    """Return TTS preference and whether audible provider work is allowed."""

    tts_enabled = bool(db.setting("tts_enabled", True))
    persisted_muted = bool(db.setting("voice_muted", False))
    return tts_enabled, tts_enabled and not (persisted_muted or session_muted)


def sync_idle_voice_phase(dashboard, db, muted: bool) -> None:
    """Keep the visible idle phase aligned with the persisted mute switch."""

    language = profile_setting(db, "ui_language")
    dashboard.set_voice_phase(
        ui_text(
            language,
            "voice_muted_short" if muted else "voice_ready_short",
            "已靜音" if muted else "準備就緒",
        )
    )


def apply_voice_volume(runtime, volume_percent: int, muted: bool) -> None:
    """Apply one volume state to every mounted provider and idle status."""

    engines = [runtime.tts, runtime.cloud_tts, runtime.realtime]
    engines.extend(
        engine
        for engine in (
            runtime.azure_tts,
            runtime.azure_hd_tts,
            runtime.realtime_speech_output,
        )
        if engine is not None
    )
    for engine in engines:
        engine.set_volume(volume_percent, muted)
    if not getattr(runtime, "speech_playing", False):
        sync_idle_voice_phase(runtime.dashboard, runtime.db, muted)


def release_failed_local_voice(runtime, message: str) -> None:
    """Expose a local-provider failure and release its queued speech line."""

    try:
        runtime.speech_providers.record_failure(VOICE_ENGINE_SYSTEM)
    except (AttributeError, LookupError):
        pass
    platform_name = runtime.platform_services.capabilities.display_name
    language = profile_setting(runtime.db, "ui_language")
    runtime.dashboard.set_api_status(
        f"{platform_name} 本機語音失敗："
        f"{safe_error_message(language, message)}"
    )
    # A failed engine cannot emit the normal finished signal. Reuse the
    # terminal release path so the mouth closes and later lines remain usable.
    runtime._speech_audio_finished()
