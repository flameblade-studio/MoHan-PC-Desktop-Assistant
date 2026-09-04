from __future__ import annotations

__all__ = ("notify_vad_degradation",)


def notify_vad_degradation(core: object, voice: object) -> None:
    degraded = bool(getattr(voice, "degraded", False))
    if not degraded:
        setattr(core, "_vad_degradation_notified", False)
        return
    if getattr(core, "_vad_degradation_notified", False):
        return
    setattr(core, "_vad_degradation_notified", True)
    dashboard = getattr(core, "dashboard", None)
    set_voice_phase = getattr(dashboard, "set_voice_phase", None)
    if not callable(set_voice_phase):
        return
    translate = getattr(dashboard, "_t", None)
    message = (
        translate(
            "voice_vad_degraded",
            "語音偵測已降級，改用 RMS。",
        )
        if callable(translate)
        else "語音偵測已降級，改用 RMS。"
    )
    set_voice_phase(message)
