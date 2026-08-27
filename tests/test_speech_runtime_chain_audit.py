from __future__ import annotations

lazy from pathlib import Path

lazy import pytest

lazy from tools import audit_speech_runtime_chain as audit
lazy from integrations.speech import WindowsTTS
lazy from integrations.speech_audio import play_pcm16_stream_with_visemes_impl


class _RejectedDeviceError(RuntimeError):
    pass


class _RejectingSoundDevice:
    PortAudioError = _RejectedDeviceError

    class RawOutputStream:
        def __init__(self, **_settings: object) -> None:
            raise _RejectedDeviceError("synthetic output device rejection")

    @staticmethod
    def query_hostapis() -> list[object]:
        return []


def test_synthetic_packaged_speech_chain_reaches_nonzero_mouth() -> None:
    result = audit.run_audit()

    assert result.tts_bytes_nonempty
    assert result.playback_started
    assert result.playback_wrote_pcm
    assert result.voice_phase_speaking
    assert result.mouth_parameter_nonzero
    assert result.portaudio_binary_present
    assert result.mouth_audio_timing_aligned
    assert result.speech_event_chain_consistent
    assert result.blink_microtiming_natural
    assert result.gaze_microtiming_natural
    assert not result.issues
    assert result.passed


def test_cross_modal_trace_rejects_mouth_before_audio() -> None:
    events = (
        audit.RuntimeEvent(0, "mouth-frame", 0, "speaking", "A", "A", "A", 0.8, 0.5),
        audit.RuntimeEvent(1, "first-audio", 0, "speaking"),
        audit.RuntimeEvent(2, "audio-write", 480, "speaking"),
        audit.RuntimeEvent(3, "mouth-closed", 480, "idle"),
    )

    assert "mouth-frame-before-first-audio" in audit.audit_event_trace(events)


def test_cross_modal_trace_rejects_viseme_frame_or_phase_divergence() -> None:
    events = (
        audit.RuntimeEvent(0, "first-audio", 0, "speaking"),
        audit.RuntimeEvent(1, "mouth-frame", 0, "idle", "A", "I", "CLOSED", 0.8, 0.0),
        audit.RuntimeEvent(2, "audio-write", 480, "speaking"),
        audit.RuntimeEvent(3, "mouth-closed", 480, "idle"),
    )

    issues = audit.audit_event_trace(events)

    assert "mouth-frame-not-speaking:1" in issues
    assert "timeline-viseme-mismatch:1" in issues
    assert "rendered-mouth-not-active:1" in issues


def test_microtiming_rejects_fixed_mechanical_period() -> None:
    from domain.face_microtiming import audit_interval_samples

    issues = audit_interval_samples(
        "blink",
        (3_000, 3_000, 3_000, 3_000),
        allowed_range=(2_800, 6_200),
    )

    assert "blink:mechanical-fixed-period" in issues


def test_missing_portaudio_binary_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(audit.sounddevice, "_libname", str(Path("missing-portaudio.dll")))

    result = audit.run_audit()

    assert not result.portaudio_binary_present
    assert not result.passed


def test_empty_provider_wave_fails_instead_of_silent_success() -> None:
    empty_wave = audit._wave_bytes(b"")
    engine = WindowsTTS()

    with pytest.raises(RuntimeError):
        engine._play_wave_bytes(empty_wave, engine._begin_generation())


def test_missing_or_rejected_output_device_is_not_silent() -> None:
    pending = bytearray(audit._tone_pcm())

    def read_chunk(buffer: bytearray) -> int:
        if not pending:
            return 0
        size = min(len(buffer), len(pending))
        buffer[:size] = pending[:size]
        del pending[:size]
        return size

    with pytest.raises(_RejectedDeviceError, match="output device rejection"):
        play_pcm16_stream_with_visemes_impl(
            read_chunk,
            volume_percent=100,
            muted=False,
            emit_cue=lambda _level, _vowel: None,
            sounddevice=_RejectingSoundDevice,
        )
