from __future__ import annotations

lazy import base64
lazy import io
lazy import json
lazy import locale
lazy import math
lazy import os
lazy import subprocess
lazy import tempfile
lazy import threading
lazy import time
lazy import wave
lazy import winreg
lazy from array import array
lazy from collections.abc import Callable
lazy from dataclasses import dataclass, field
lazy from pathlib import Path
lazy from urllib.error import HTTPError, URLError
lazy from urllib.request import Request, urlopen

lazy import sounddevice as sd
lazy from PySide6.QtCore import QObject, QProcess, Signal

lazy from lip_sync import (
    VISEME_CUES_PER_SECOND,
    infer_vowel_pcm16,
)
lazy from pcm_audio import PcmAudioError, scale_pcm16, stereo_to_mono_pcm16
lazy from safe_error import sanitize_error
lazy from service_status_localization import (
    ServiceStatus,
    append_service_status,
    service_status,
)

if os.name == "nt":
    lazy import winsound
else:
    # Keep the module importable on macOS/Linux. A later platform audio
    # adapter will provide verified playback there; silently pretending that
    # Windows playback exists would turn a compatibility gate into a false
    # claim.
    winsound = None


CREATE_NO_WINDOW = 0x08000000
DEFAULT_TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
DEFAULT_TRANSCRIPTION_PROMPT = (
    "請依使用者選擇的語言精確轉錄，保留原意，不要改寫。"
    "人名、公司名、產品名與工作術語請優先依提示中的常用詞判斷。"
)


def _empty_api_key() -> str:
    return ""


def _default_recognition_mode() -> str:
    return "OpenAI 高準確辨識（推薦）"


def _default_transcription_model() -> str:
    return DEFAULT_TRANSCRIPTION_MODEL


def _default_transcription_language() -> str:
    return "zh"


def _default_transcription_prompt() -> str:
    return DEFAULT_TRANSCRIPTION_PROMPT


def _windows_fallback_enabled() -> bool:
    return True


@dataclass(frozen=True, slots=True)
class SpeechListenerProviders:
    api_key: Callable[[], str] = _empty_api_key
    recognition_mode: Callable[[], str] = _default_recognition_mode
    transcription_model: Callable[[], str] = (
        _default_transcription_model
    )
    transcription_language: Callable[[], str] = (
        _default_transcription_language
    )
    transcription_prompt: Callable[[], str] = (
        _default_transcription_prompt
    )
    windows_fallback: Callable[[], bool] = (
        _windows_fallback_enabled
    )


@dataclass(frozen=True, slots=True)
class RecordingLimits:
    max_blocks: int
    initial_silence_blocks: int
    end_silence_blocks: int
    minimum_speech_blocks: int
    active_threshold_ratio: float


@dataclass(slots=True)
class SpeechEndpointDetector:
    limits: RecordingLimits
    speech_started: bool = False
    speech_blocks: int = 0
    quiet_blocks: int = 0
    threshold: float = 120.0
    baseline: list[float] = field(default_factory=list)
    language: str = "zh-TW"

    def _handle_manual_stop(self, stop_requested: bool) -> bool:
        if not stop_requested:
            return False
        if self.speech_started:
            return True
        raise RuntimeError(
            service_status(
                self.language,
                ServiceStatus.SPEECH_EMPTY_MANUAL_CAPTURE,
            )
        )

    def _calibrate(self, level: float) -> bool:
        baseline = self.baseline
        if self.speech_started or len(baseline) >= 3:
            return False
        baseline.append(level)
        if level > 500:
            self.speech_started = True
        elif len(baseline) == 3:
            self.threshold = max(
                120.0,
                (sum(baseline) / 3) * 2.2,
            )
        return True

    def _active_threshold(self) -> float:
        if not self.speech_started:
            return self.threshold
        return max(
            90.0,
            self.threshold * self.limits.active_threshold_ratio,
        )

    def advance(
        self,
        level: float,
        captured_blocks: int,
        stop_requested: bool,
    ) -> bool:
        if self._handle_manual_stop(stop_requested):
            return True
        if self._calibrate(level):
            return False
        if level >= self._active_threshold():
            self.speech_started = True
            self.quiet_blocks = 0
        elif self.speech_started:
            self.quiet_blocks += 1
            if (
                self.speech_blocks
                >= self.limits.minimum_speech_blocks
                and self.quiet_blocks
                >= self.limits.end_silence_blocks
            ):
                return True
        elif captured_blocks >= self.limits.initial_silence_blocks:
            raise RuntimeError(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_NOT_DETECTED,
                )
            )
        if self.speech_started:
            self.speech_blocks += 1
        return False


@dataclass(frozen=True, slots=True)
class SpeechTranscriptionLocale:
    """Provider transcription language paired with its UI locale."""

    provider_language: str = ""
    ui_language: str = "zh-TW"


def transcription_http_error_message(
    status: int,
    detail: str,
    *,
    language: str = "zh-TW",
) -> str:
    lowered = detail.lower()
    match status:
        case 401:
            key = ServiceStatus.SPEECH_OPENAI_KEY_INVALID
        case 403:
            key = ServiceStatus.SPEECH_OPENAI_NOT_AUTHORIZED
        case 404:
            key = ServiceStatus.SPEECH_OPENAI_MODEL_NOT_FOUND
        case 429 if any(
            marker in lowered
            for marker in ("insufficient_quota", "quota", "billing")
        ):
            key = ServiceStatus.SPEECH_OPENAI_QUOTA_EXHAUSTED
        case 429:
            key = ServiceStatus.SPEECH_OPENAI_RATE_LIMITED
        case _ if status >= 500:
            safe = sanitize_error(detail, http_status=status)
            return (
                service_status(
                    language,
                    ServiceStatus.SPEECH_OPENAI_SERVICE_ERROR,
                    status=status,
                )
                + f" [{safe}]"
            )
        case _:
            return service_status(
                language,
                ServiceStatus.SPEECH_OPENAI_HTTP_ERROR,
                status=status,
                detail=str(sanitize_error(detail, http_status=status)),
            )
    return service_status(language, key)


def transcribe_wav_bytes(
    audio: bytes,
    api_key: str,
    model: str,
    language: str | SpeechTranscriptionLocale = "",
    prompt: str = "",
) -> str:
    """Transcribe a complete WAV utterance through the accurate endpoint."""
    locale = (
        language
        if isinstance(language, SpeechTranscriptionLocale)
        else SpeechTranscriptionLocale(
            provider_language=language,
        )
    )
    boundary = f"----MohanBoundary{os.urandom(12).hex()}"
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; '
                    f'name="{name}"\r\n\r\n'
                ).encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )

    add_field("model", model or SpeechListener.TRANSCRIPTION_MODEL)
    if locale.provider_language:
        add_field("language", locale.provider_language)
    if prompt:
        add_field("prompt", prompt)
    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                b'Content-Disposition: form-data; name="file"; '
                b'filename="mohan.wav"\r\n'
            ),
            b"Content-Type: audio/wav\r\n\r\n",
            audio,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    request = Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=b"".join(parts),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": (
                f"multipart/form-data; boundary={boundary}"
            ),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        failure = transcription_http_error_message(
            exc.code,
            detail,
            language=locale.ui_language,
        )
        result = None
    except URLError as exc:
        failure = service_status(
            locale.ui_language,
            ServiceStatus.SPEECH_OPENAI_CONNECTION_ERROR,
            detail=sanitize_error(exc),
        )
        result = None
    except TimeoutError as exc:
        del exc
        failure = service_status(
            locale.ui_language,
            ServiceStatus.SPEECH_OPENAI_TIMEOUT,
        )
        result = None
    else:
        failure = ""
    if failure:
        raise RuntimeError(failure)
    assert result is not None
    text = str(result.get("text", "")).strip()
    if not text:
        raise RuntimeError(
            service_status(
                locale.ui_language,
                ServiceStatus.SPEECH_OPENAI_EMPTY_RESULT,
            )
        )
    return text


def apply_wav_volume(
    audio: bytes,
    volume_percent: int = 100,
    muted: bool = False,
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
        adjusted = scale_pcm16(b"".join(frame_chunks), gain)
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
    except (OSError, EOFError, wave.Error, PcmAudioError):
        return audio


def _mono_wave_chunk(chunk: bytes, channels: int) -> bytes:
    if channels == 2:
        return stereo_to_mono_pcm16(chunk)
    return chunk


def _emit_wave_timeline(
    source: wave.Wave_read,
    emit_cue: Callable[[float, str], None],
    playback_start: threading.Event | None = None,
    timeline_ready: threading.Event | None = None,
) -> None:
    rate = source.getframerate()
    channels = source.getnchannels()
    if source.getsampwidth() != 2:
        return
    frames_per_chunk = max(1, rate // VISEME_CUES_PER_SECOND)
    chunk = source.readframes(frames_per_chunk)
    if not chunk:
        return
    chunk = _mono_wave_chunk(chunk, channels)
    prepared_cue = infer_vowel_pcm16(chunk, rate)
    if timeline_ready is not None:
        timeline_ready.set()
    if playback_start is not None:
        playback_start.wait(timeout=2.0)
    started_at = time.perf_counter()
    chunk_index = 0
    while chunk:
        deadline = (
            started_at
            + chunk_index * frames_per_chunk / rate
        )
        remaining = deadline - time.perf_counter()
        if remaining > 0:
            time.sleep(remaining)
        emit_cue(*prepared_cue)
        chunk = source.readframes(frames_per_chunk)
        if chunk:
            prepared_cue = infer_vowel_pcm16(
                _mono_wave_chunk(chunk, channels),
                rate,
            )
        chunk_index += 1


def emit_wave_viseme_cues(
    audio: bytes,
    emit_cue: Callable[[float, str], None],
    playback_start: threading.Event | None = None,
    timeline_ready: threading.Event | None = None,
) -> None:
    """Emit the shared audio-driven mouth timeline for any WAV provider."""

    try:
        with wave.open(io.BytesIO(audio), "rb") as source:
            _emit_wave_timeline(
                source,
                emit_cue,
                playback_start,
                timeline_ready,
            )
    except (OSError, EOFError, wave.Error):
        return
    finally:
        if timeline_ready is not None:
            timeline_ready.set()


class _SpeechPlaybackUnavailable(OSError):
    """The current platform has no verified audio playback adapter."""


def play_wave_with_visemes(
    audio: bytes,
    volume_percent: int,
    muted: bool,
    emit_cue: Callable[[float, str], None],
    audio_path: Path | None = None,
) -> None:
    """Play provider WAV audio through the single lip-sync implementation."""

    if winsound is None:
        raise _SpeechPlaybackUnavailable(
            service_status(
                "zh-TW",
                ServiceStatus.SPEECH_PLAYBACK_UNAVAILABLE,
            )
        )

    playback_audio = apply_wav_volume(audio, volume_percent, muted)
    playback_start = threading.Event()
    playback_finished = threading.Event()
    timeline_ready = threading.Event()

    def emit_active_cue(level: float, vowel: str) -> None:
        if not playback_finished.is_set():
            emit_cue(level, vowel)

    cue_thread = threading.Thread(
        target=emit_wave_viseme_cues,
        args=(audio, emit_active_cue, playback_start, timeline_ready),
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
            winsound.PlaySound(str(audio_path), winsound.SND_FILENAME)
        else:
            winsound.PlaySound(playback_audio, winsound.SND_MEMORY)
    finally:
        # A delayed analyzer must never reopen the mouth after the blocking
        # playback call has returned. Only the final closed cue may cross the
        # end-of-audio boundary.
        playback_finished.set()
        cue_thread.join(timeout=0.35)
        emit_cue(0.0, "CLOSED")


def play_pcm16_stream_with_visemes(
    read_chunk: Callable[[bytearray], int],
    *,
    volume_percent: int,
    muted: bool,
    emit_cue: Callable[[float, str], None],
    on_first_audio: Callable[[], None] | None = None,
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
        with sd.RawOutputStream(
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
                    emit_cue(*infer_vowel_pcm16(chunk, sample_rate))
                    output.write(scale_pcm16(chunk, gain))
            if pending:
                if len(pending) % 2:
                    pending.pop()
                if pending:
                    chunk = bytes(pending)
                    emit_cue(*infer_vowel_pcm16(chunk, sample_rate))
                    output.write(scale_pcm16(chunk, gain))
    finally:
        emit_cue(0.0, "CLOSED")


@dataclass(frozen=True)
class WindowsVoiceInfo:
    """One installed Windows speech voice with trustworthy metadata."""

    name: str
    culture: str
    gender: str


_KNOWN_FEMALE_VOICE_MARKERS = ("yating", "hanhan")
_KNOWN_MALE_VOICE_MARKERS = ("zhiwei",)


def is_known_male_windows_voice(name: str) -> bool:
    lowered_name = str(name or "").lower()
    return any(
        marker in lowered_name for marker in _KNOWN_MALE_VOICE_MARKERS
    )


def _normalized_voice_gender(value: str, name: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"female", "feminine", "woman"}:
        return "female"
    if normalized in {"male", "masculine", "man"}:
        return "male"
    lowered_name = name.lower()
    if any(marker in lowered_name for marker in _KNOWN_FEMALE_VOICE_MARKERS):
        return "female"
    if is_known_male_windows_voice(lowered_name):
        return "male"
    return "unknown"


def _is_allowed_companion_voice(name: str, gender: str = "") -> bool:
    """Allow only voices Windows identifies as female.

    Yating and Hanhan remain compatibility fallbacks for older Windows voice
    registrations that omit Gender. Unknown voices are deliberately excluded:
    silently falling back to a possibly male system voice would violate the
    character contract.
    """

    lowered_name = name.lower()
    if is_known_male_windows_voice(lowered_name):
        return False
    return _normalized_voice_gender(gender, name) == "female"


def _registry_string(
    attributes,
    value_name: str,
    fallback: str = "",
) -> str:
    try:
        return str(winreg.QueryValueEx(attributes, value_name)[0])
    except OSError:
        return fallback


def _registry_culture(attributes) -> str:
    language = _registry_string(attributes, "Language")
    try:
        locale_id = int(language.split(";", 1)[0], 16)
    except ValueError:
        return ""
    return locale.windows_locale.get(locale_id, "").replace("_", "-")


def _registry_voice(
    root,
    token: str,
    prefix: str,
) -> WindowsVoiceInfo | None:
    with winreg.OpenKey(root, token + r"\Attributes") as attributes:
        name = _registry_string(attributes, "Name", token)
        culture = _registry_culture(attributes)
        full_name = prefix + name
        gender = _normalized_voice_gender(
            _registry_string(attributes, "Gender"),
            full_name,
        )
    if not _is_allowed_companion_voice(full_name, gender):
        return None
    return WindowsVoiceInfo(full_name, culture, gender)


def _registry_voices(
    registry_path: str,
    prefix: str,
) -> list[WindowsVoiceInfo]:
    voices: list[WindowsVoiceInfo] = []
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            registry_path,
        ) as root:
            for index in range(winreg.QueryInfoKey(root)[0]):
                token = winreg.EnumKey(root, index)
                try:
                    voice = _registry_voice(root, token, prefix)
                except OSError:
                    continue
                if voice is not None:
                    voices.append(voice)
    except OSError:
        return []
    return voices


def windows_voice_catalog() -> list[WindowsVoiceInfo]:
    """Return installed female OneCore and Desktop SAPI voices."""

    if os.name != "nt":
        return []
    locations = (
        (
            r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens",
            "OneCore::",
        ),
        (r"SOFTWARE\Microsoft\Speech\Voices\Tokens", ""),
    )
    return [
        *_registry_voices(registry_path, prefix)
        for registry_path, prefix in locations
    ]


def windows_voices() -> list[tuple[str, str]]:
    return [(voice.name, voice.culture) for voice in windows_voice_catalog()]


def female_windows_voices_for_language(
    voices: list[tuple[str, str]],
    target_language: str,
) -> list[tuple[str, str]]:
    target = str(target_language or "").strip().lower()
    family = target.split("-", 1)[0]
    return [
        (name, culture)
        for name, culture in voices
        if not is_known_male_windows_voice(name)
        and culture.lower().split("-", 1)[0] == family
    ]


def preferred_windows_voice(
    voices: list[tuple[str, str]],
    saved: str = "",
    target_language: str = "zh-TW",
) -> str:
    voices = [
        (name, culture)
        for name, culture in voices
        if not is_known_male_windows_voice(name)
    ]
    installed = {name: culture for name, culture in voices}
    if saved in installed:
        return saved
    target = str(target_language or "").strip().lower()
    family = target.split("-", 1)[0]
    if target in {"zh", "zh-tw"}:
        for keyword in ("Yating", "Hanhan"):
            for name, culture in voices:
                if (
                    keyword.lower() in name.lower()
                    and culture.lower() == "zh-tw"
                ):
                    return name
    for name, culture in voices:
        if target and culture.lower() == target:
            return name
    for name, culture in voices:
        if family and culture.lower().split("-", 1)[0] == family:
            return name
    return voices[0][0] if voices else ""


class _SpeechCancelled(Exception):
    """End one obsolete local-speech generation without user-facing errors."""


class WindowsTTS(QObject):
    failed = Signal(str)
    finished = Signal()
    viseme_cue = Signal(float, str)
    _failed_ready = Signal(int, str)
    _finished_ready = Signal(int)
    _viseme_ready = Signal(int, float, str)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        language: str = "zh-TW",
    ):
        super().__init__(parent)
        self.language = language
        self.volume_percent = 125
        self.muted = False
        self._state_lock = threading.RLock()
        self._generation = 0
        self._active_process: subprocess.Popen[bytes] | None = None
        self._active_stream: sd.RawOutputStream | None = None
        self._failed_ready.connect(self._deliver_failed)
        self._finished_ready.connect(self._deliver_finished)
        self._viseme_ready.connect(self._deliver_viseme)

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_percent = max(0, min(160, int(volume_percent)))
        self.muted = bool(muted)

    def speak(self, text: str, voice_name: str = "", rate: int = -1) -> None:
        generation = self._begin_generation()
        if os.name != "nt" or not text.strip():
            self._emit_finished(generation)
            return
        threading.Thread(
            target=self._run,
            args=(text, voice_name, rate, generation),
            daemon=True,
        ).start()

    def stop(self) -> None:
        self._begin_generation()

    def _begin_generation(self) -> int:
        with self._state_lock:
            self._generation += 1
            generation = self._generation
            process = self._active_process
            stream = self._active_stream
            self._active_process = None
            self._active_stream = None
        self._terminate_process(process)
        self._abort_stream(stream)
        return generation

    def _is_current(self, generation: int) -> bool:
        with self._state_lock:
            return generation == self._generation

    def _ensure_current(self, generation: int) -> None:
        if not self._is_current(generation):
            raise _SpeechCancelled

    def _emit_finished(self, generation: int) -> None:
        if self._is_current(generation):
            self._finished_ready.emit(generation)

    def _deliver_finished(self, generation: int) -> None:
        with self._state_lock:
            if generation == self._generation:
                self.finished.emit()

    def _emit_failed(self, generation: int, message: str) -> None:
        if self._is_current(generation):
            self._failed_ready.emit(generation, message)

    def _deliver_failed(self, generation: int, message: str) -> None:
        with self._state_lock:
            if generation == self._generation:
                self.failed.emit(message)

    def _emit_viseme(
        self,
        generation: int,
        level: float,
        vowel: str,
    ) -> None:
        if self._is_current(generation):
            self._viseme_ready.emit(generation, level, vowel)

    def _deliver_viseme(
        self,
        generation: int,
        level: float,
        vowel: str,
    ) -> None:
        with self._state_lock:
            if generation == self._generation:
                self.viseme_cue.emit(level, vowel)

    def _register_process(
        self,
        generation: int,
        process: subprocess.Popen[bytes],
    ) -> bool:
        with self._state_lock:
            if generation != self._generation:
                return False
            self._active_process = process
            return True

    def _release_process(
        self,
        process: subprocess.Popen[bytes],
    ) -> None:
        with self._state_lock:
            if self._active_process is process:
                self._active_process = None

    def _register_stream(
        self,
        generation: int,
        stream: sd.RawOutputStream,
    ) -> bool:
        with self._state_lock:
            if generation != self._generation:
                return False
            self._active_stream = stream
            return True

    def _release_stream(self, stream: sd.RawOutputStream) -> None:
        with self._state_lock:
            if self._active_stream is stream:
                self._active_stream = None

    @staticmethod
    def _terminate_process(
        process: subprocess.Popen[bytes] | None,
    ) -> None:
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
        except OSError:
            # The worker still has the generation gate, so a process that
            # exited during this race cannot publish obsolete results.
            return

    @staticmethod
    def _abort_stream(stream: sd.RawOutputStream | None) -> None:
        if stream is None:
            return
        try:
            stream.abort()
        except (OSError, RuntimeError, sd.PortAudioError):
            # PortAudio can report that another thread already closed the
            # stream. The generation gate remains the authoritative stop.
            return

    def _run(
        self,
        text: str,
        voice_name: str,
        rate: int,
        generation: int | None = None,
    ) -> None:
        # Keep the established direct-call contract used by diagnostics while
        # treating such a call as a new, independently cancellable utterance.
        if generation is None:
            generation = self._begin_generation()
        try:
            self._ensure_current(generation)
            installed = windows_voices()
            selected_voice = preferred_windows_voice(
                installed,
                voice_name,
                "",
            )
            if not selected_voice:
                self._emit_failed(
                    generation,
                    service_status(
                        self.language,
                        ServiceStatus.SPEECH_WINDOWS_FEMALE_VOICE_MISSING,
                    ),
                )
                self._emit_finished(generation)
                return
            voice_name = selected_voice
            if voice_name.startswith("OneCore::"):
                self._run_onecore(
                    text,
                    voice_name.removeprefix("OneCore::"),
                    generation,
                )
            else:
                self._run_sapi(text, voice_name, rate, generation)
            self._emit_finished(generation)
        except _SpeechCancelled:
            return
        except (
            OSError,
            RuntimeError,
            subprocess.SubprocessError,
            wave.Error,
            sd.PortAudioError,
        ) as exc:
            if not self._is_current(generation):
                return
            if voice_name.startswith("OneCore::"):
                try:
                    desktop_voices = [
                        voice
                        for voice in windows_voices()
                        if not voice[0].startswith("OneCore::")
                    ]
                    fallback = preferred_windows_voice(desktop_voices)
                    self._run_sapi(text, fallback, rate, generation)
                    self._emit_finished(generation)
                    return
                except _SpeechCancelled:
                    return
                except (
                    OSError,
                    RuntimeError,
                    subprocess.SubprocessError,
                    wave.Error,
                    sd.PortAudioError,
                ):
                    pass
            self._emit_failed(generation, str(sanitize_error(exc)))
            self._emit_finished(generation)

    def _run_sapi(
        self,
        text: str,
        voice_name: str,
        rate: int,
        generation: int,
    ) -> None:
        fd, name = tempfile.mkstemp(prefix="mohan-sapi-", suffix=".wav")
        os.close(fd)
        audio_path = Path(name)
        audio_path.unlink(missing_ok=True)
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        voice_encoded = base64.b64encode(voice_name.encode("utf-8")).decode("ascii")
        path_encoded = base64.b64encode(
            str(audio_path).encode("utf-8")
        ).decode("ascii")
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$n=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{voice_encoded}'));"
            "if($n){$s.SelectVoice($n)}else{"
            "$v=$s.GetInstalledVoices()|?{$_.VoiceInfo.Culture.Name -like 'zh-*'}|select -First 1;"
            "if($v){$s.SelectVoice($v.VoiceInfo.Name)}};"
            f"$s.Rate={max(-10, min(10, rate))};"
            f"$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'));"
            f"$p=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{path_encoded}'));"
            "$s.SetOutputToWaveFile($p);$s.Speak($t);$s.Dispose()"
        )
        command = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            self._synthesize_with_powershell(
                command,
                audio_path,
                generation,
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_WINDOWS_LEGACY_FAILED,
                ),
                240,
            )
            self._play_wave_bytes(
                audio_path.read_bytes(),
                generation,
            )
        finally:
            audio_path.unlink(missing_ok=True)

    def _run_onecore(
        self,
        text: str,
        voice_name: str,
        generation: int,
    ) -> None:
        fd, name = tempfile.mkstemp(prefix="mohan-onecore-", suffix=".wav")
        os.close(fd)
        audio_path = Path(name)
        audio_path.unlink(missing_ok=True)
        text_encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        voice_encoded = base64.b64encode(voice_name.encode("utf-8")).decode("ascii")
        path_encoded = base64.b64encode(
            str(audio_path).encode("utf-8")
        ).decode("ascii")
        missing_voice_encoded = base64.b64encode(
            service_status(
                self.language,
                ServiceStatus.SPEECH_ONECORE_VOICE_MISSING,
                voice=voice_name,
            ).encode("utf-8")
        ).decode("ascii")
        script = (
            "Add-Type -AssemblyName System.Runtime.WindowsRuntime;"
            "$null=[Windows.Media.SpeechSynthesis.SpeechSynthesizer,"
            "Windows.Media.SpeechSynthesis,ContentType=WindowsRuntime];"
            "$null=[Windows.Storage.Streams.DataReader,"
            "Windows.Storage.Streams,ContentType=WindowsRuntime];"
            "function Await($Operation,$ResultType){"
            "$method=[System.WindowsRuntimeSystemExtensions].GetMethods()|"
            "Where-Object{$_.Name -eq 'AsTask' -and $_.IsGenericMethod -and "
            "$_.GetGenericArguments().Count -eq 1 -and "
            "$_.GetParameters().Count -eq 1}|Select-Object -First 1;"
            "$task=$method.MakeGenericMethod($ResultType).Invoke($null,@($Operation));"
            "$task.Wait();$task.Result};"
            f"$text=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{text_encoded}'));"
            f"$voiceName=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{voice_encoded}'));"
            f"$path=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{path_encoded}'));"
            f"$missingVoice=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{missing_voice_encoded}'));"
            "$synth=[Windows.Media.SpeechSynthesis.SpeechSynthesizer]::new();"
            "$voice=[Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices|"
            "Where-Object{$_.DisplayName -eq $voiceName -or $_.Id -like ('*'+$voiceName+'*')}|"
            "Select-Object -First 1;"
            "if(-not $voice){throw $missingVoice};"
            "$synth.Voice=$voice;"
            "$stream=Await ($synth.SynthesizeTextToStreamAsync($text)) "
            "([Windows.Media.SpeechSynthesis.SpeechSynthesisStream]);"
            "$reader=[Windows.Storage.Streams.DataReader]::new($stream);"
            "$null=Await ($reader.LoadAsync([uint32]$stream.Size)) ([uint32]);"
            "$bytes=New-Object byte[] ([int]$stream.Size);"
            "$reader.ReadBytes($bytes);"
            "[IO.File]::WriteAllBytes($path,$bytes);"
            "$reader.Dispose();$stream.Dispose();$synth.Dispose();"
        )
        command = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            self._synthesize_with_powershell(
                command,
                audio_path,
                generation,
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_ONECORE_FAILED,
                ),
                3000,
            )
            self._play_wave_bytes(
                audio_path.read_bytes(),
                generation,
            )
        finally:
            audio_path.unlink(missing_ok=True)

    def _synthesize_with_powershell(
        self,
        command: str,
        audio_path: Path,
        generation: int,
        failure_message: str,
        detail_limit: int,
    ) -> None:
        self._ensure_current(generation)
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-EncodedCommand", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
        )
        if not self._register_process(generation, process):
            self._terminate_process(process)
            raise _SpeechCancelled
        try:
            try:
                _stdout, stderr = process.communicate(timeout=120)
            except subprocess.TimeoutExpired as exc:
                self._terminate_process(process)
                process.communicate()
                self._ensure_current(generation)
                raise RuntimeError(
                    service_status(
                        self.language,
                        ServiceStatus.SPEECH_WINDOWS_SYNTHESIS_TIMEOUT,
                    )
                ) from exc
        finally:
            self._release_process(process)
        self._ensure_current(generation)
        if process.returncode or not audio_path.exists():
            detail = stderr.decode("utf-8", errors="replace")[:detail_limit]
            raise RuntimeError(
                str(sanitize_error(detail)) if detail else failure_message
            )

    def _play_wave_bytes(
        self,
        audio: bytes,
        generation: int,
    ) -> None:
        playback_audio = apply_wav_volume(
            audio,
            self.volume_percent,
            self.muted,
        )
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
                raise RuntimeError(
                    service_status(
                        self.language,
                        ServiceStatus.SPEECH_WINDOWS_WAV_UNSUPPORTED,
                    )
                )
            frames_per_cue = max(
                1,
                sample_rate // VISEME_CUES_PER_SECOND,
            )
            stream = sd.RawOutputStream(
                samplerate=sample_rate,
                channels=channels,
                dtype="int16",
                blocksize=frames_per_cue,
            )
            if not self._register_stream(generation, stream):
                stream.close()
                raise _SpeechCancelled
            try:
                self._ensure_current(generation)
                stream.start()
                while chunk := source.readframes(frames_per_cue):
                    self._ensure_current(generation)
                    cue_chunk = cue_source.readframes(frames_per_cue)
                    level, vowel = infer_vowel_pcm16(
                        _mono_wave_chunk(cue_chunk, channels),
                        sample_rate,
                    )
                    self._emit_viseme(generation, level, vowel)
                    stream.write(chunk)
                self._ensure_current(generation)
                stream.stop()
                self._emit_viseme(generation, 0.0, "CLOSED")
            finally:
                self._release_stream(stream)
                stream.close()

    def _emit_wave_cues(
        self,
        audio: bytes,
        playback_start: threading.Event | None = None,
    ) -> None:
        emit_wave_viseme_cues(
            audio,
            self.viseme_cue.emit,
            playback_start,
        )


class UnavailableSystemTTS(QObject):
    """Fail closed when a platform has no verified local speech adapter."""

    failed = Signal(str)
    finished = Signal()
    viseme_cue = Signal(float, str)

    def __init__(
        self,
        reason: str,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.reason = reason
        self.volume_percent = 125
        self.muted = False

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_percent = max(0, min(160, int(volume_percent)))
        self.muted = bool(muted)

    def speak(self, text: str, voice_name: str = "", rate: int = -1) -> None:
        del voice_name, rate
        if text.strip():
            self.failed.emit(self.reason)
        self.finished.emit()

    def stop(self) -> None:
        """Match the local speech contract when no adapter is available."""


class OpenAITTS(QObject):
    failed = Signal(str)
    finished = Signal()
    viseme_cue = Signal(float, str)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        language: str = "zh-TW",
    ):
        super().__init__(parent)
        self.language = language
        self.volume_percent = 125
        self.muted = False

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_percent = max(0, min(160, int(volume_percent)))
        self.muted = bool(muted)

    def speak(
        self,
        text: str,
        api_key: str,
        voice: str = "coral",
        instructions: str = "",
    ) -> None:
        if not text.strip() or not api_key.strip():
            self.failed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_OPENAI_KEY_MISSING,
                )
            )
            return
        threading.Thread(
            target=self._run,
            args=(text, api_key, voice, instructions),
            daemon=True,
        ).start()

    def _run(self, text: str, api_key: str, voice: str, instructions: str) -> None:
        payload = {
            "model": "gpt-4o-mini-tts",
            "voice": voice,
            "input": text,
            "response_format": "wav",
        }
        if instructions.strip():
            payload["instructions"] = instructions.strip()
        request = Request(
            "https://api.openai.com/v1/audio/speech",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                audio = response.read()
            play_wave_with_visemes(
                audio,
                self.volume_percent,
                self.muted,
                self.viseme_cue.emit,
            )
            self.finished.emit()
        except _SpeechPlaybackUnavailable:
            self.failed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_PLAYBACK_UNAVAILABLE,
                )
            )
        except (
            URLError,
            HTTPError,
            OSError,
            RuntimeError,
            TimeoutError,
            wave.Error,
        ) as exc:
            self.failed.emit(str(sanitize_error(exc)))

    def _emit_wave_cues(
        self,
        audio: bytes,
        playback_start: threading.Event | None = None,
    ) -> None:
        emit_wave_viseme_cues(
            audio,
            self.viseme_cue.emit,
            playback_start,
        )


class SpeechListener(QObject):
    recognized = Signal(str)
    failed = Signal(str)
    listening_changed = Signal(bool)
    recording_changed = Signal(bool)
    status_changed = Signal(str)
    diagnostic_changed = Signal(str)
    _fallback_requested = Signal(str, str)

    TRANSCRIPTION_MODEL = DEFAULT_TRANSCRIPTION_MODEL
    RECORD_BLOCK_SECONDS = 0.1
    END_SILENCE_SECONDS = 0.85
    MIN_SPEECH_SECONDS = 0.8
    INITIAL_SILENCE_SECONDS = 2.0
    MAX_RECORD_SECONDS = 10.0
    ACTIVE_SPEECH_THRESHOLD_RATIO = 0.68
    TRANSCRIPTION_PROMPT = DEFAULT_TRANSCRIPTION_PROMPT

    def __init__(
        self,
        script_path: Path,
        providers: SpeechListenerProviders | None = None,
        parent: QObject | None = None,
        *,
        language: str = "zh-TW",
    ):
        super().__init__(parent)
        self.language = language
        resolved = providers or SpeechListenerProviders()
        self.script_path = script_path
        self.api_key_provider = resolved.api_key
        self.recognition_mode_provider = resolved.recognition_mode
        self.transcription_model_provider = (
            resolved.transcription_model
        )
        self.transcription_language_provider = (
            resolved.transcription_language
        )
        self.transcription_prompt_provider = (
            resolved.transcription_prompt
        )
        self.windows_fallback_provider = resolved.windows_fallback
        self.process: QProcess | None = None
        self.output_path: Path | None = None
        self.audio_path: Path | None = None
        self._busy = threading.Event()
        self._recording_active = threading.Event()
        self._stop_recording = threading.Event()
        self._fallback_requested.connect(self._start_windows_fallback)

    @property
    def is_recording(self) -> bool:
        return self._recording_active.is_set()

    @property
    def is_busy(self) -> bool:
        return self._busy.is_set()

    def toggle_listening(self) -> None:
        if self._recording_active.is_set():
            self._stop_recording.set()
            self.status_changed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_CAPTURE_STOPPING,
                )
            )
            return
        if self._busy.is_set():
            return
        self.listen_once()

    def listen_once(self) -> None:
        if self._busy.is_set() or (
            self.process and self.process.state() != QProcess.NotRunning
        ):
            return
        mode = self.recognition_mode_provider()
        api_key = (self.api_key_provider() or os.getenv("OPENAI_API_KEY", "")).strip()
        if mode.startswith("OpenAI"):
            if not api_key:
                reason = service_status(
                    self.language,
                    ServiceStatus.SPEECH_OPENAI_KEY_MISSING_SENTENCE,
                )
                self.diagnostic_changed.emit(reason)
                if self.windows_fallback_provider():
                    self._start_windows(fallback_reason=reason)
                else:
                    self.failed.emit(
                        append_service_status(
                            self.language,
                            reason,
                            ServiceStatus.SPEECH_WINDOWS_FALLBACK_DISABLED,
                        )
                    )
                return
            # Freeze every SQLite-backed provider on the Qt/main thread.
            # Accessing StudioDB from the recording worker raises SQLite's
            # cross-thread ProgrammingError before the API request is sent.
            model = (
                self.transcription_model_provider().strip()
                or self.TRANSCRIPTION_MODEL
            )
            language = self.transcription_language_provider().strip()
            prompt = self.transcription_prompt_provider().strip()
            fallback_enabled = bool(self.windows_fallback_provider())
            self._busy.set()
            self._stop_recording.clear()
            self._recording_active.set()
            self.listening_changed.emit(True)
            self.recording_changed.emit(True)
            self.status_changed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_RECORDING,
                )
            )
            threading.Thread(
                target=self._listen_with_openai,
                args=(
                    api_key,
                    model,
                    language,
                    prompt,
                    fallback_enabled,
                ),
                daemon=True,
            ).start()
            return
        self._start_windows()

    def _start_windows(
        self,
        audio_path: Path | None = None,
        fallback_reason: str = "",
    ) -> None:
        self._busy.set()
        fd, name = tempfile.mkstemp(prefix="mohan-voice-", suffix=".txt")
        os.close(fd)
        self.output_path = Path(name)
        self.output_path.unlink(missing_ok=True)
        self.audio_path = audio_path
        self.process = QProcess(self)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(
            lambda _error: self.failed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_RECOGNITION_START_FAILED,
                )
            )
        )
        if audio_path is None:
            self.listening_changed.emit(True)
            self.status_changed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_WINDOWS_LISTENING,
                )
            )
        else:
            self.status_changed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_WINDOWS_FALLBACK,
                    detail=fallback_reason,
                )
            )
        arguments = [
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(self.script_path),
            "-OutputPath",
            str(self.output_path),
        ]
        if audio_path is not None:
            arguments.extend(["-InputPath", str(audio_path)])
        self.process.start(
            "powershell.exe",
            arguments,
        )

    def _start_windows_fallback(
        self,
        audio_path: str,
        reason: str,
    ) -> None:
        self._start_windows(Path(audio_path), fallback_reason=reason)

    @staticmethod
    def _rms(chunk: bytes) -> float:
        samples = array("h")
        samples.frombytes(chunk)
        if not samples:
            return 0.0
        return (sum(sample * sample for sample in samples) / len(samples)) ** 0.5

    def _require_recording_dependency(self) -> None:
        try:
            _ = sd.RawInputStream
        except (AttributeError, ImportError) as exc:
            raise RuntimeError(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_RECORDING_COMPONENT_MISSING,
                )
            ) from exc

    def _recording_limits(self) -> RecordingLimits:
        block_seconds = self.RECORD_BLOCK_SECONDS
        return RecordingLimits(
            max_blocks=int(self.MAX_RECORD_SECONDS / block_seconds),
            initial_silence_blocks=int(
                self.INITIAL_SILENCE_SECONDS / block_seconds
            ),
            end_silence_blocks=math.ceil(
                self.END_SILENCE_SECONDS / block_seconds
            ),
            minimum_speech_blocks=math.ceil(
                self.MIN_SPEECH_SECONDS / block_seconds
            ),
            active_threshold_ratio=(
                self.ACTIVE_SPEECH_THRESHOLD_RATIO
            ),
        )

    def _capture_recording_frames(
        self,
        sample_rate: int,
        block_size: int,
    ) -> tuple[bytes, ...]:
        limits = self._recording_limits()
        detector = SpeechEndpointDetector(
            limits,
            language=self.language,
        )
        frames: list[bytes] = []
        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=block_size,
            channels=1,
            dtype="int16",
        ) as stream:
            for _ in range(limits.max_blocks):
                data, _overflowed = stream.read(block_size)
                chunk = bytes(data)
                frames.append(chunk)
                if detector.advance(
                    self._rms(chunk),
                    len(frames),
                    self._stop_recording.is_set(),
                ):
                    break
        if not detector.speech_started:
            raise RuntimeError(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_NOT_DETECTED,
                )
            )
        return tuple(frames)

    @staticmethod
    def _write_recording(
        frames: tuple[bytes, ...],
        sample_rate: int,
    ) -> Path:
        fd, name = tempfile.mkstemp(
            prefix="mohan-recording-",
            suffix=".wav",
        )
        os.close(fd)
        path = Path(name)
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(sample_rate)
            output.writeframes(b"".join(frames))
        return path

    def _record_wav(self) -> Path:
        self._require_recording_dependency()
        sample_rate = 16000
        block_size = int(sample_rate * self.RECORD_BLOCK_SECONDS)
        try:
            frames = self._capture_recording_frames(
                sample_rate,
                block_size,
            )
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_WINDOWS_MICROPHONE_ERROR,
                    detail=sanitize_error(exc),
                )
            ) from exc
        return self._write_recording(frames, sample_rate)

    def _transcribe(
        self,
        audio_path: Path,
        api_key: str,
        model: str | None = None,
        language: str | None = None,
        prompt: str | None = None,
    ) -> str:
        resolved_model = (
            model
            or self.transcription_model_provider().strip()
            or self.TRANSCRIPTION_MODEL
        )
        if language is None:
            language = self.transcription_language_provider().strip()
        if prompt is None:
            prompt = self.transcription_prompt_provider().strip()
        return transcribe_wav_bytes(
            audio_path.read_bytes(),
            api_key,
            resolved_model,
            SpeechTranscriptionLocale(
                provider_language=language or "",
                ui_language=self.language,
            ),
            prompt or "",
        )

    @staticmethod
    def _http_error_message(
        status: int,
        detail: str,
        *,
        language: str = "zh-TW",
    ) -> str:
        return transcription_http_error_message(
            status,
            detail,
            language=language,
        )

    def _listen_with_openai(
        self,
        api_key: str,
        model: str,
        language: str,
        prompt: str,
        fallback_enabled: bool,
    ) -> None:
        audio_path: Path | None = None
        try:
            audio_path = self._record_wav()
            self._recording_active.clear()
            self.recording_changed.emit(False)
            self.status_changed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_RECOGNIZING,
                )
            )
            text = self._transcribe(
                audio_path,
                api_key,
                model=model,
                language=language,
                prompt=prompt,
            )
            self.diagnostic_changed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_TRANSCRIPTION_SUCCEEDED,
                    model=model,
                )
            )
            self.recognized.emit(text)
            audio_path.unlink(missing_ok=True)
            self._busy.clear()
            self.listening_changed.emit(False)
        except Exception as exc:  # noqa: BLE001 -- worker restores UI state on failure
            self._recording_active.clear()
            self.recording_changed.emit(False)
            reason = str(sanitize_error(exc))
            self.diagnostic_changed.emit(reason)
            if audio_path and audio_path.exists():
                if fallback_enabled:
                    # 雲端不可用時，將同一段錄音交給 Windows，不要求使用者重說。
                    self._fallback_requested.emit(str(audio_path), reason)
                else:
                    audio_path.unlink(missing_ok=True)
                    self._busy.clear()
                    self.failed.emit(
                        append_service_status(
                            self.language,
                            reason,
                            ServiceStatus.SPEECH_WINDOWS_FALLBACK_DISABLED,
                            separate=True,
                        )
                    )
                    self.listening_changed.emit(False)
            else:
                self._busy.clear()
                self.failed.emit(reason)
                self.listening_changed.emit(False)

    def _finished(self) -> None:
        self._busy.clear()
        self.listening_changed.emit(False)
        text = ""
        stderr = ""
        if self.process:
            stderr = bytes(self.process.readAllStandardError()).decode(
                "utf-8", errors="replace"
            ).strip()
        if self.output_path and self.output_path.exists():
            text = self.output_path.read_text(encoding="utf-8-sig").strip()
            self.output_path.unlink(missing_ok=True)
        if self.audio_path and self.audio_path.exists():
            self.audio_path.unlink(missing_ok=True)
        self.audio_path = None
        self.process = None
        if text == "__ERROR__:NO_RECOGNIZER":
            self.failed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_WINDOWS_RECOGNIZER_MISSING,
                )
            )
        elif text.startswith("__ERROR__:"):
            detail = text.removeprefix("__ERROR__:")
            if "0x80070005" in detail or "Access is denied" in detail:
                self.failed.emit(
                    service_status(
                        self.language,
                        ServiceStatus.SPEECH_WINDOWS_MICROPHONE_DENIED,
                    )
                )
            else:
                self.failed.emit(
                    service_status(
                        self.language,
                        ServiceStatus.SPEECH_WINDOWS_RECOGNITION_ERROR,
                        detail=sanitize_error(detail),
                    )
                )
        elif text and text != "__EMPTY__":
            self.recognized.emit(text)
        elif stderr:
            self.failed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_WINDOWS_RECOGNITION_START_ERROR,
                    detail=sanitize_error(stderr),
                )
            )
        else:
            self.failed.emit(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_NOT_UNDERSTOOD,
                )
            )
