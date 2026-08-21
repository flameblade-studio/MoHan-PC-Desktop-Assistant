from __future__ import annotations

lazy import json
lazy import math
lazy import os
lazy import subprocess
lazy import tempfile
lazy import threading
lazy import wave
lazy from array import array
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from urllib.error import HTTPError, URLError
lazy from urllib.request import Request, urlopen

lazy import sounddevice as sd
lazy from PySide6.QtCore import QObject, QProcess, Signal

from integrations.speech_audio import (
    WavePlaybackBoundary,
    _CancellableWavePlayback,
    _play_cancellable_wave_bytes,
    _SpeechCancelled,
    _SpeechPlaybackUnavailable,
    abort_raw_output_stream,
    apply_wav_volume,
    emit_wave_viseme_cues,
    play_pcm16_stream_with_visemes_impl,
    play_wave_with_visemes_impl,
)
from integrations.speech_recognition import (
    RecordingLimits,
    SpeechEndpointDetector,
    SpeechTranscriptionLocale,
    TranscriptionHttpBoundary,
    TranscriptionRequest,
    transcribe_wav_bytes_impl,
    transcription_http_error_message,
)
from integrations.speech_unavailable import UnavailableSystemTTS
from integrations.speech_voice_catalog import (
    WindowsVoiceInfo,
    _is_allowed_companion_voice,
    female_windows_voices_for_language,
    is_known_male_windows_voice,
    preferred_windows_voice,
    windows_voice_catalog,
    windows_voices,
)
lazy from domain.audio_acceleration import (
    PYTHON_PCM_ACCELERATION,
    PcmAccelerationPort,
)
lazy from domain.safe_error import sanitize_error
lazy from domain.service_status_localization import (
    ServiceStatus,
    append_service_status,
    service_status,
)
lazy from integrations.speech_windows_synthesis import WindowsSpeechSynthesisMethods

__all__ = (
    "DEFAULT_TRANSCRIPTION_MODEL",
    "DEFAULT_TRANSCRIPTION_PROMPT",
    "OpenAITTS",
    "RecordingLimits",
    "SpeechEndpointDetector",
    "SpeechListener",
    "SpeechListenerProviders",
    "SpeechTranscriptionLocale",
    "UnavailableSystemTTS",
    "WindowsTTS",
    "WindowsVoiceInfo",
    "_is_allowed_companion_voice",
    "apply_wav_volume",
    "emit_wave_viseme_cues",
    "female_windows_voices_for_language",
    "is_known_male_windows_voice",
    "play_pcm16_stream_with_visemes",
    "play_wave_with_visemes",
    "preferred_windows_voice",
    "transcribe_wav_bytes",
    "transcription_http_error_message",
    "windows_voice_catalog",
    "windows_voices",
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


def transcribe_wav_bytes(
    audio: bytes,
    api_key: str,
    model: str,
    language: str | SpeechTranscriptionLocale = "",
    prompt: str = "",
) -> str:
    """Transcribe one WAV while preserving the public patchable HTTP boundary."""

    return transcribe_wav_bytes_impl(
        audio,
        api_key,
        TranscriptionRequest(model, language, prompt),
        TranscriptionHttpBoundary(
            open_request=urlopen,
            default_model=DEFAULT_TRANSCRIPTION_MODEL,
        ),
    )


def play_wave_with_visemes(
    audio: bytes,
    volume_percent: int,
    muted: bool,
    emit_cue: Callable[[float, str], None],
    audio_path: Path | None = None,
    *,
    pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
) -> None:
    """Play WAV audio through the patchable Windows integration boundary."""

    play_wave_with_visemes_impl(
        audio,
        volume_percent,
        muted,
        emit_cue,
        audio_path,
        boundary=WavePlaybackBoundary(
            winsound_adapter=winsound,
            adjust_volume=apply_wav_volume,
            emit_timeline=emit_wave_viseme_cues,
        ),
        pcm_acceleration=pcm_acceleration,
    )


def play_pcm16_stream_with_visemes(
    read_chunk: Callable[[bytearray], int],
    *,
    volume_percent: int,
    muted: bool,
    emit_cue: Callable[[float, str], None],
    on_first_audio: Callable[[], None] | None = None,
    pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
) -> None:
    """Play streaming PCM through the current patchable audio adapter."""

    play_pcm16_stream_with_visemes_impl(
        read_chunk,
        volume_percent=volume_percent,
        muted=muted,
        emit_cue=emit_cue,
        on_first_audio=on_first_audio,
        pcm_acceleration=pcm_acceleration,
        sounddevice=sd,
    )


def _abort_raw_output_stream(stream: sd.RawOutputStream | None) -> None:
    abort_raw_output_stream(stream, sd)


@dataclass(frozen=True, slots=True)
class SpeechListenerProviders:
    api_key: Callable[[], str] = _empty_api_key
    recognition_mode: Callable[[], str] = _default_recognition_mode
    transcription_model: Callable[[], str] = _default_transcription_model
    transcription_language: Callable[[], str] = _default_transcription_language
    transcription_prompt: Callable[[], str] = _default_transcription_prompt
    windows_fallback: Callable[[], bool] = _windows_fallback_enabled


class WindowsTTS(QObject):
    failed = Signal(str)
    finished = Signal()
    viseme_cue = Signal(float, str)
    _failed_ready = Signal(int, str)
    _finished_ready = Signal(int)
    _viseme_ready = Signal(int, float, str)

    _run_sapi = WindowsSpeechSynthesisMethods._run_sapi
    _run_onecore = WindowsSpeechSynthesisMethods._run_onecore
    _synthesize_with_powershell = (
        WindowsSpeechSynthesisMethods._synthesize_with_powershell
    )

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        language: str = "zh-TW",
        pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
    ):
        super().__init__(parent)
        self.language = language
        self._pcm = pcm_acceleration
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
        _abort_raw_output_stream(stream)

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

    def _play_wave_bytes(
        self,
        audio: bytes,
        generation: int,
    ) -> None:
        _play_cancellable_wave_bytes(
            audio,
            self.volume_percent,
            self.muted,
            _CancellableWavePlayback(
                register_stream=lambda stream: self._register_stream(
                    generation,
                    stream,
                ),
                release_stream=self._release_stream,
                ensure_current=lambda: self._ensure_current(generation),
                emit_viseme=lambda level, vowel: self._emit_viseme(
                    generation,
                    level,
                    vowel,
                ),
                unsupported_error=lambda: RuntimeError(
                    service_status(
                        self.language,
                        ServiceStatus.SPEECH_WINDOWS_WAV_UNSUPPORTED,
                    )
                ),
                pcm_acceleration=self._pcm,
                sounddevice=sd,
            ),
        )

    def _emit_wave_cues(
        self,
        audio: bytes,
        playback_start: threading.Event | None = None,
    ) -> None:
        emit_wave_viseme_cues(
            audio,
            self.viseme_cue.emit,
            playback_start,
            pcm_acceleration=self._pcm,
        )


class OpenAITTS(QObject):
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
        pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
    ):
        super().__init__(parent)
        self.language = language
        self._pcm = pcm_acceleration
        self.volume_percent = 125
        self.muted = False
        self._state_lock = threading.RLock()
        self._generation = 0
        self._active_stream: sd.RawOutputStream | None = None
        self._failed_ready.connect(self._deliver_failed)
        self._finished_ready.connect(self._deliver_finished)
        self._viseme_ready.connect(self._deliver_viseme)

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
        generation = self._begin_generation()
        if not text.strip() or not api_key.strip():
            self._emit_failed(
                generation,
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_OPENAI_KEY_MISSING,
                ),
            )
            return
        threading.Thread(
            target=self._run,
            args=(text, api_key, voice, instructions, generation),
            daemon=True,
        ).start()

    def stop(self) -> None:
        """Invalidate the current request and abort playback without waiting."""

        self._begin_generation()

    def _begin_generation(self) -> int:
        with self._state_lock:
            self._generation += 1
            generation = self._generation
            stream = self._active_stream
            self._active_stream = None
        _abort_raw_output_stream(stream)
        return generation

    def _is_current(self, generation: int) -> bool:
        with self._state_lock:
            return generation == self._generation

    def _ensure_current(self, generation: int) -> None:
        if not self._is_current(generation):
            raise _SpeechCancelled

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

    def _play_wave_bytes(self, audio: bytes, generation: int) -> None:
        if os.name != "nt":
            raise _SpeechPlaybackUnavailable(
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_PLAYBACK_UNAVAILABLE,
                )
            )
        _play_cancellable_wave_bytes(
            audio,
            self.volume_percent,
            self.muted,
            _CancellableWavePlayback(
                register_stream=lambda stream: self._register_stream(
                    generation,
                    stream,
                ),
                release_stream=self._release_stream,
                ensure_current=lambda: self._ensure_current(generation),
                emit_viseme=lambda level, vowel: self._emit_viseme(
                    generation,
                    level,
                    vowel,
                ),
                unsupported_error=lambda: _SpeechPlaybackUnavailable(
                    service_status(
                        self.language,
                        ServiceStatus.SPEECH_PLAYBACK_UNAVAILABLE,
                    )
                ),
                pcm_acceleration=self._pcm,
                sounddevice=sd,
            ),
        )

    def _run(
        self,
        text: str,
        api_key: str,
        voice: str,
        instructions: str,
        generation: int | None = None,
    ) -> None:
        if generation is None:
            generation = self._begin_generation()
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
            self._ensure_current(generation)
            with urlopen(request, timeout=60) as response:
                audio = response.read()
            self._ensure_current(generation)
            self._play_wave_bytes(audio, generation)
            self._emit_finished(generation)
        except _SpeechCancelled:
            return
        except _SpeechPlaybackUnavailable:
            self._emit_failed(
                generation,
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_PLAYBACK_UNAVAILABLE,
                ),
            )
        except (
            URLError,
            HTTPError,
            OSError,
            RuntimeError,
            TimeoutError,
            wave.Error,
            sd.PortAudioError,
        ) as exc:
            self._emit_failed(generation, str(sanitize_error(exc)))

    def _emit_wave_cues(
        self,
        audio: bytes,
        playback_start: threading.Event | None = None,
    ) -> None:
        emit_wave_viseme_cues(
            audio,
            self.viseme_cue.emit,
            playback_start,
            pcm_acceleration=self._pcm,
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
        self.transcription_model_provider = resolved.transcription_model
        self.transcription_language_provider = resolved.transcription_language
        self.transcription_prompt_provider = resolved.transcription_prompt
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
                self.transcription_model_provider().strip() or self.TRANSCRIPTION_MODEL
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
            initial_silence_blocks=int(self.INITIAL_SILENCE_SECONDS / block_seconds),
            end_silence_blocks=math.ceil(self.END_SILENCE_SECONDS / block_seconds),
            minimum_speech_blocks=math.ceil(self.MIN_SPEECH_SECONDS / block_seconds),
            active_threshold_ratio=(self.ACTIVE_SPEECH_THRESHOLD_RATIO),
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
        except Exception as exc:
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
            stderr = (
                bytes(self.process.readAllStandardError())
                .decode("utf-8", errors="replace")
                .strip()
            )
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
