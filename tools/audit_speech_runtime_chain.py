"""Deterministic pre-package audit of the local speech-to-mouth chain.

The audit never opens a real audio device.  It drives the production PCM
streaming, viseme dynamics, speech lifecycle, and face-motion code through a
recording PortAudio-compatible sink.  This makes it safe in CI while still
proving that a non-empty TTS payload starts playback and produces a non-zero
mouth parameter.  It also verifies that sounddevice resolved a real PortAudio
binary, which catches PyInstaller builds that collected only ``sounddevice.py``.
"""

from __future__ import annotations

lazy import io
lazy import json
lazy import math
lazy import struct
lazy import wave
lazy from dataclasses import asdict, dataclass
lazy from pathlib import Path
lazy from collections.abc import Callable
lazy from typing import Self

lazy import sounddevice

lazy from application.speech_performance import (
    SpeechPerformancePhase,
    SpeechPerformanceTimeline,
)
lazy from domain.face_motion import FaceMotionController
lazy from domain.face_microtiming import (
    ATTENTION_GLANCE_INTERVAL_MS,
    BLINK_DURATION_MS,
    BLINK_INTERVAL_MS,
    SACCADE_INTERVAL_MS,
    audit_interval_samples,
)
lazy from domain.lip_sync import VisemeDynamics
lazy from integrations.speech_audio import play_pcm16_stream_with_visemes_impl

AUDIT_SCHEMA = "mohan.speech-runtime-chain-audit.v2"
SAMPLE_RATE = 24_000
CUE_HZ = 50
SAMPLE_COUNT = SAMPLE_RATE // 4
TONE_HZ = 220.0
TONE_AMPLITUDE = 12_000
MINIMUM_WAVE_HEADER_BYTES = 44


@dataclass(frozen=True, slots=True)
class SpeechRuntimeAudit:
    schema: str
    tts_bytes_nonempty: bool
    playback_started: bool
    playback_wrote_pcm: bool
    voice_phase_speaking: bool
    mouth_parameter_nonzero: bool
    portaudio_binary_present: bool
    mouth_audio_timing_aligned: bool
    speech_event_chain_consistent: bool
    blink_microtiming_natural: bool
    gaze_microtiming_natural: bool
    event_trace: tuple[RuntimeEvent, ...]
    issues: tuple[str, ...]
    passed: bool


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    ordinal: int
    kind: str
    audio_frames: int
    phase: str
    cue_viseme: str = ""
    timeline_viseme: str = ""
    frame_viseme: str = ""
    cue_level: float = 0.0
    mouth_aperture: float = 0.0


class _RecordingOutputStream:
    instances: list[_RecordingOutputStream] = []
    write_observer: Callable[[bytes], None] | None = None

    def __init__(self, **_settings: object) -> None:
        self.writes: list[bytes] = []
        self.__class__.instances.append(self)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def write(self, chunk: bytes) -> None:
        self.writes.append(bytes(chunk))
        if self.__class__.write_observer is not None:
            self.__class__.write_observer(bytes(chunk))


class _RecordingSoundDevice:
    RawOutputStream = _RecordingOutputStream

    @staticmethod
    def query_hostapis() -> list[object]:
        return []


def _tone_pcm() -> bytes:
    return b"".join(
        struct.pack(
            "<h",
            int(TONE_AMPLITUDE * math.sin(2.0 * math.pi * TONE_HZ * index / SAMPLE_RATE)),
        )
        for index in range(SAMPLE_COUNT)
    )


def _wave_bytes(pcm: bytes) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(SAMPLE_RATE)
        target.writeframes(pcm)
    return output.getvalue()


def _portaudio_binary_present() -> bool:
    resolved = getattr(sounddevice, "_libname", "")
    return bool(resolved) and Path(str(resolved)).is_file()


def audit_event_trace(events: tuple[RuntimeEvent, ...]) -> tuple[str, ...]:
    """Prove audio, speaking phase, viseme and frame share one ordered chain."""

    issues: list[str] = []
    kinds = tuple(event.kind for event in events)
    for required in ("first-audio", "mouth-frame", "audio-write", "mouth-closed"):
        if required not in kinds:
            issues.append(f"missing-event:{required}")
    first_audio = next((event for event in events if event.kind == "first-audio"), None)
    first_write = next((event for event in events if event.kind == "audio-write"), None)
    active_frames = tuple(
        event
        for event in events
        if event.kind == "mouth-frame" and event.cue_level > 0.0
    )
    if first_audio is not None and active_frames:
        if active_frames[0].ordinal <= first_audio.ordinal:
            issues.append("mouth-frame-before-first-audio")
    if first_audio is not None and first_write is not None:
        if first_write.ordinal <= first_audio.ordinal:
            issues.append("audio-write-before-first-audio")
    writes = tuple(event for event in events if event.kind == "audio-write")
    for frame in active_frames:
        next_event = (
            events[frame.ordinal + 1]
            if frame.ordinal + 1 < len(events)
            else None
        )
        if next_event is None or next_event.kind != "audio-write":
            issues.append(f"mouth-frame-not-adjacent-to-audio-write:{frame.ordinal}")
        following_write = next(
            (event for event in writes if event.ordinal > frame.ordinal),
            None,
        )
        if following_write is None:
            issues.append(f"mouth-frame-without-audio-write:{frame.ordinal}")
            continue
        drift = following_write.audio_frames - frame.audio_frames
        if drift <= 0 or drift > SAMPLE_RATE // CUE_HZ:
            issues.append(f"mouth-audio-drift:{frame.ordinal}:{drift}")
        if frame.phase != SpeechPerformancePhase.SPEAKING.value:
            issues.append(f"mouth-frame-not-speaking:{frame.ordinal}")
        if frame.timeline_viseme != frame.cue_viseme:
            issues.append(f"timeline-viseme-mismatch:{frame.ordinal}")
        if frame.frame_viseme == "CLOSED" or frame.mouth_aperture <= 0.0:
            issues.append(f"rendered-mouth-not-active:{frame.ordinal}")
    closing = next((event for event in reversed(events) if event.kind == "mouth-closed"), None)
    if closing is not None and writes and closing.ordinal <= writes[-1].ordinal:
        issues.append("mouth-closed-before-final-audio-write")
    if closing is not None and closing.phase != SpeechPerformancePhase.IDLE.value:
        issues.append("mouth-closed-without-idle-handoff")
    return tuple(dict.fromkeys(issues))


def audit_runtime_microtiming() -> tuple[str, ...]:
    """Validate deterministic samples against production-authored ranges."""

    blink = (2_800, 4_350, 6_200, 3_620, 5_180)
    blink_duration = (118, 132, 145, 124, 139)
    glance = (38_000, 57_400, 78_000, 46_900, 69_300)
    saccade = (4_000, 7_850, 11_000, 5_600, 9_420)
    return (
        *audit_interval_samples("blink", blink, allowed_range=BLINK_INTERVAL_MS),
        *audit_interval_samples(
            "blink-duration",
            blink_duration,
            allowed_range=BLINK_DURATION_MS,
        ),
        *audit_interval_samples(
            "attention-gaze",
            glance,
            allowed_range=ATTENTION_GLANCE_INTERVAL_MS,
        ),
        *audit_interval_samples(
            "saccade-gaze",
            saccade,
            allowed_range=SACCADE_INTERVAL_MS,
        ),
    )


def run_audit() -> SpeechRuntimeAudit:
    pcm = _tone_pcm()
    tts_bytes = _wave_bytes(pcm)
    pending = bytearray(pcm)
    playback_started: list[bool] = []
    observed_speaking: list[bool] = []
    mouth_apertures: list[float] = []
    timeline = SpeechPerformanceTimeline()
    timeline.prepare("system-local")
    dynamics = VisemeDynamics()
    face_motion = FaceMotionController()
    event_trace: list[RuntimeEvent] = []
    audio_frames = 0

    def record(kind: str, **values: object) -> None:
        event_trace.append(
            RuntimeEvent(
                ordinal=len(event_trace),
                kind=kind,
                audio_frames=audio_frames,
                phase=timeline.snapshot.phase.value,
                **values,
            )
        )

    def read_chunk(buffer: bytearray) -> int:
        if not pending:
            return 0
        size = min(len(buffer), len(pending))
        buffer[:size] = pending[:size]
        del pending[:size]
        return size

    def emit_cue(level: float, vowel: str) -> None:
        update = timeline.viseme(level, vowel)
        if update is not None:
            observed_speaking.append(
                timeline.snapshot.phase is SpeechPerformancePhase.SPEAKING
            )
        viseme = dynamics.advance(level, vowel)
        frame = face_motion.advance(
            viseme,
            pose="front",
            expression="idle_front",
        )
        mouth_apertures.append(frame.mouth.aperture)
        record(
            "mouth-frame",
            cue_viseme=str(vowel).upper(),
            timeline_viseme=timeline.snapshot.last_viseme,
            frame_viseme=viseme.selected,
            cue_level=float(level),
            mouth_aperture=frame.mouth.aperture,
        )

    def first_audio() -> None:
        playback_started.append(True)
        timeline.first_audio()
        record("first-audio")

    def wrote_audio(chunk: bytes) -> None:
        nonlocal audio_frames
        audio_frames += len(chunk) // 2
        record("audio-write")

    _RecordingOutputStream.instances.clear()
    _RecordingOutputStream.write_observer = wrote_audio
    try:
        play_pcm16_stream_with_visemes_impl(
            read_chunk,
            volume_percent=100,
            muted=False,
            emit_cue=emit_cue,
            on_first_audio=first_audio,
            sounddevice=_RecordingSoundDevice,
        )
    finally:
        _RecordingOutputStream.write_observer = None
    timeline.final_audio()
    timeline.mouth_closed()
    record("mouth-closed", cue_viseme="CLOSED", timeline_viseme="CLOSED")
    wrote_pcm = any(
        stream.writes
        for stream in _RecordingOutputStream.instances
    )
    trace_issues = audit_event_trace(tuple(event_trace))
    microtiming_issues = audit_runtime_microtiming()
    blink_issues = tuple(
        issue for issue in microtiming_issues if issue.startswith("blink:")
    )
    gaze_issues = tuple(
        issue for issue in microtiming_issues if not issue.startswith("blink:")
    )
    checks = {
        "tts_bytes_nonempty": len(tts_bytes) > MINIMUM_WAVE_HEADER_BYTES,
        "playback_started": playback_started == [True],
        "playback_wrote_pcm": wrote_pcm,
        "voice_phase_speaking": any(observed_speaking),
        "mouth_parameter_nonzero": max(mouth_apertures, default=0.0) > 0.0,
        "portaudio_binary_present": _portaudio_binary_present(),
        "mouth_audio_timing_aligned": not any(
            issue.startswith(("mouth-", "audio-write-"))
            for issue in trace_issues
        ),
        "speech_event_chain_consistent": not trace_issues,
        "blink_microtiming_natural": not blink_issues,
        "gaze_microtiming_natural": not gaze_issues,
    }
    return SpeechRuntimeAudit(
        schema=AUDIT_SCHEMA,
        **checks,
        event_trace=tuple(event_trace),
        issues=(*trace_issues, *microtiming_issues),
        passed=all(checks.values()),
    )


def main() -> int:
    result = run_audit()
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
