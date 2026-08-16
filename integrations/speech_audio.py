from __future__ import annotations

lazy import io
lazy import threading
lazy import time
lazy import wave
lazy from collections.abc import Callable
lazy from dataclasses import dataclass, field
lazy from pathlib import Path

lazy import sounddevice as sd

lazy from domain.audio_acceleration import (
    PYTHON_PCM_ACCELERATION,
    PcmAccelerationPort,
)
lazy from domain.lip_sync import (
    VISEME_CUES_PER_SECOND,
)
lazy from domain.pcm_audio import PcmAudioError
lazy from domain.service_status_localization import ServiceStatus, service_status


def apply_wav_volume(
    audio: bytes,
    volume_percent: int = 100,
    muted: bool = False,
    *,
    pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
) -> bytes:
    """Apply application-local gain without changing the Windows mixer."""
    gain = 0.0 if muted else max(0, min(160, int(volume_percent))) / 100.0
    if gain == 1.0:
        return audio
    try:
        with wave.open(io.BytesIO(audio), "rb") as source:
            params = source.getparams()
            if params.sampwidth != 2:
                return audio
            frame_chunks = []
            while chunk := source.readframes(4096):
                frame_chunks.append(chunk)
        adjusted = pcm_acceleration.scale_pcm16(b"".join(frame_chunks), gain)
        output = io.BytesIO()
        with wave.open(output, "wb") as target:
            # Streaming WAV responses may use 0xFFFFFFFF as a temporary data
            # length. Never copy that placeholder through setparams(), because
            # Python's wave writer then overflows while closing the file.
            # Writing the format fields separately lets wave derive the real
            # frame count from the bytes that were actually received.
            target.setnchannels(params.nchannels)
            target.setsampwidth(params.sampwidth)
            target.setframerate(params.framerate)
            target.setcomptype(params.comptype, params.compname)
            target.writeframes(adjusted)
        return output.getvalue()
    except OSError, EOFError, wave.Error, PcmAudioError:
        return audio


def _mono_wave_chunk(
    chunk: bytes,
    channels: int,
    pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
) -> bytes:
    if channels == 2:
        return pcm_acceleration.stereo_to_mono_pcm16(chunk)
    return chunk


def _emit_wave_timeline(
    source: wave.Wave_read,
    emit_cue: Callable[[float, str], None],
    playback_start: threading.Event | None = None,
    timeline_ready: threading.Event | None = None,
    *,
    pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
) -> None:
    rate = source.getframerate()
    channels = source.getnchannels()
    if source.getsampwidth() != 2:
        return
    frames_per_chunk = max(1, rate // VISEME_CUES_PER_SECOND)
    chunk = source.readframes(frames_per_chunk)
    if not chunk:
        return
    chunk = _mono_wave_chunk(chunk, channels, pcm_acceleration)
    prepared_cue = pcm_acceleration.infer_vowel_pcm16(chunk, rate)
    if timeline_ready is not None:
        timeline_ready.set()
    if playback_start is not None:
        playback_start.wait(timeout=2.0)
    started_at = time.perf_counter()
    chunk_index = 0
    while chunk:
        deadline = started_at + chunk_index * frames_per_chunk / rate
        remaining = deadline - time.perf_counter()
        if remaining > 0:
            time.sleep(remaining)
        emit_cue(*prepared_cue)
        chunk = source.readframes(frames_per_chunk)
        if chunk:
            prepared_cue = pcm_acceleration.infer_vowel_pcm16(
                _mono_wave_chunk(chunk, channels, pcm_acceleration),
                rate,
            )
        chunk_index += 1


def emit_wave_viseme_cues(
    audio: bytes,
    emit_cue: Callable[[float, str], None],
    playback_start: threading.Event | None = None,
    timeline_ready: threading.Event | None = None,
    *,
    pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
) -> None:
    """Emit the shared audio-driven mouth timeline for any WAV provider."""

    try:
        with wave.open(io.BytesIO(audio), "rb") as source:
            _emit_wave_timeline(
                source,
                emit_cue,
                playback_start,
                timeline_ready,
                pcm_acceleration=pcm_acceleration,
            )
    except OSError, EOFError, wave.Error:
        return
    finally:
        if timeline_ready is not None:
            timeline_ready.set()


class _SpeechPlaybackUnavailable(OSError):
    """The current platform has no verified audio playback adapter."""


@dataclass(frozen=True, slots=True)
class WavePlaybackBoundary:
    winsound_adapter: object | None
    adjust_volume: Callable[..., bytes]
    emit_timeline: Callable[..., None]


def play_wave_with_visemes_impl(  # noqa: PLR0913 -- stable public playback contract
    audio: bytes,
    volume_percent: int,
    muted: bool,
    emit_cue: Callable[[float, str], None],
    audio_path: Path | None = None,
    *,
    boundary: WavePlaybackBoundary,
    pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
) -> None:
    """Play provider WAV audio through the single lip-sync implementation."""

    if boundary.winsound_adapter is None:
        raise _SpeechPlaybackUnavailable(
            service_status(
                "zh-TW",
                ServiceStatus.SPEECH_PLAYBACK_UNAVAILABLE,
            )
        )

    playback_audio = boundary.adjust_volume(
        audio,
        volume_percent,
        muted,
        pcm_acceleration=pcm_acceleration,
    )
    playback_start = threading.Event()
    playback_finished = threading.Event()
    timeline_ready = threading.Event()

    def emit_active_cue(level: float, vowel: str) -> None:
        if not playback_finished.is_set():
            emit_cue(level, vowel)

    cue_thread = threading.Thread(
        target=boundary.emit_timeline,
        args=(audio, emit_active_cue, playback_start, timeline_ready),
        kwargs={"pcm_acceleration": pcm_acceleration},
        daemon=True,
    )
    cue_thread.start()
    timeline_ready.wait(timeout=2.0)
    # Release the first pre-analyzed 20 ms cue immediately before the blocking
    # playback call. The worker stays one cue ahead after playback begins, so
    # long replies do not pay an up-front full-file analysis delay.
    playback_start.set()
    try:
        if audio_path is not None and volume_percent == 100 and not muted:
            boundary.winsound_adapter.PlaySound(
                str(audio_path),
                boundary.winsound_adapter.SND_FILENAME,
            )
        else:
            boundary.winsound_adapter.PlaySound(
                playback_audio,
                boundary.winsound_adapter.SND_MEMORY,
            )
    finally:
        # A delayed analyzer must never reopen the mouth after the blocking
        # playback call has returned. Only the final closed cue may cross the
        # end-of-audio boundary.
        playback_finished.set()
        cue_thread.join(timeout=0.35)
        emit_cue(0.0, "CLOSED")


def play_pcm16_stream_with_visemes_impl(  # noqa: PLR0913 -- stable streaming contract
    read_chunk: Callable[[bytearray], int],
    *,
    volume_percent: int,
    muted: bool,
    emit_cue: Callable[[float, str], None],
    on_first_audio: Callable[[], None] | None = None,
    pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
    sounddevice: object = sd,
) -> None:
    """Play a pull-based PCM16 stream through the shared 50 Hz mouth clock."""

    sample_rate = 24_000
    frames_per_cue = max(1, sample_rate // VISEME_CUES_PER_SECOND)
    bytes_per_cue = frames_per_cue * 2
    read_buffer = bytearray(max(bytes_per_cue * 4, 4_096))
    pending = bytearray()
    gain = 0.0 if muted else max(0, min(160, volume_percent)) / 100.0
    first_audio_pending = True

    try:
        with sounddevice.RawOutputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocksize=frames_per_cue,
        ) as output:
            while True:
                bytes_read = int(read_chunk(read_buffer))
                if bytes_read <= 0:
                    break
                if first_audio_pending:
                    first_audio_pending = False
                    if on_first_audio is not None:
                        on_first_audio()
                pending.extend(read_buffer[:bytes_read])
                while len(pending) >= bytes_per_cue:
                    chunk = bytes(pending[:bytes_per_cue])
                    del pending[:bytes_per_cue]
                    emit_cue(*pcm_acceleration.infer_vowel_pcm16(chunk, sample_rate))
                    output.write(pcm_acceleration.scale_pcm16(chunk, gain))
            if pending:
                if len(pending) % 2:
                    pending.pop()
                if pending:
                    chunk = bytes(pending)
                    emit_cue(*pcm_acceleration.infer_vowel_pcm16(chunk, sample_rate))
                    output.write(pcm_acceleration.scale_pcm16(chunk, gain))
    finally:
        emit_cue(0.0, "CLOSED")


class _SpeechCancelled(Exception):
    """End one obsolete local-speech generation without user-facing errors."""


def abort_raw_output_stream(
    stream: sd.RawOutputStream | None,
    sounddevice: object = sd,
) -> None:
    if stream is None:
        return
    try:
        stream.abort()
    except OSError, RuntimeError, sounddevice.PortAudioError:
        # The worker may have closed the stream during the cancellation race.
        # Its generation gate remains the authoritative publication barrier.
        return


@dataclass(frozen=True, slots=True)
class _CancellableWavePlayback:
    register_stream: Callable[[sd.RawOutputStream], bool]
    release_stream: Callable[[sd.RawOutputStream], None]
    ensure_current: Callable[[], None]
    emit_viseme: Callable[[float, str], None]
    unsupported_error: Callable[[], Exception]
    pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION
    sounddevice: object = field(default_factory=lambda: sd)


def _play_cancellable_wave_bytes(
    audio: bytes,
    volume_percent: int,
    muted: bool,
    playback: _CancellableWavePlayback,
) -> None:
    """Play one WAV through the shared cancellable 50 Hz audio path."""

    playback_audio = apply_wav_volume(
        audio,
        volume_percent,
        muted,
        pcm_acceleration=playback.pcm_acceleration,
    )
    playback.ensure_current()
    with (
        wave.open(io.BytesIO(audio), "rb") as cue_source,
        wave.open(io.BytesIO(playback_audio), "rb") as source,
    ):
        channels = source.getnchannels()
        sample_rate = source.getframerate()
        if (
            source.getsampwidth() != 2
            or source.getcomptype() != "NONE"
            or cue_source.getnchannels() != channels
            or cue_source.getsampwidth() != 2
            or cue_source.getframerate() != sample_rate
            or cue_source.getcomptype() != "NONE"
        ):
            raise playback.unsupported_error()
        frames_per_cue = max(
            1,
            sample_rate // VISEME_CUES_PER_SECOND,
        )
        if source.getnframes() == 0:
            playback.ensure_current()
            playback.emit_viseme(0.0, "CLOSED")
            return
        stream = playback.sounddevice.RawOutputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            blocksize=frames_per_cue,
        )
        if not playback.register_stream(stream):
            stream.close()
            raise _SpeechCancelled
        try:
            playback.ensure_current()
            stream.start()
            while chunk := source.readframes(frames_per_cue):
                playback.ensure_current()
                cue_chunk = cue_source.readframes(frames_per_cue)
                level, vowel = playback.pcm_acceleration.infer_vowel_pcm16(
                    _mono_wave_chunk(
                        cue_chunk,
                        channels,
                        playback.pcm_acceleration,
                    ),
                    sample_rate,
                )
                playback.emit_viseme(level, vowel)
                stream.write(chunk)
            playback.ensure_current()
            stream.stop()
            playback.emit_viseme(0.0, "CLOSED")
        finally:
            playback.release_stream(stream)
            stream.close()
