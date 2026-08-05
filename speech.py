from __future__ import annotations

import base64
import io
import json
import locale
import math
import os
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QProcess, Signal

from lip_sync import (
    VISEME_CUES_PER_SECOND,
    infer_vowel_pcm16,
)
from pcm_audio import PcmAudioError, scale_pcm16, stereo_to_mono_pcm16


if os.name == "nt":
    import winsound
else:
    # Keep the module importable on macOS/Linux. A later platform audio
    # adapter will provide verified playback there; silently pretending that
    # Windows playback exists would turn a compatibility gate into a false
    # claim.
    winsound = None


CREATE_NO_WINDOW = 0x08000000


def transcription_http_error_message(
    status: int,
    detail: str,
) -> str:
    lowered = detail.lower()
    if status == 401:
        return "OpenAI API 金鑰無效或已被撤銷（HTTP 401）。"
    if status == 403:
        return "OpenAI Project 未授權使用語音轉錄（HTTP 403）。"
    if status == 404:
        return "OpenAI 找不到轉錄模型，或此 Project 無權使用（HTTP 404）。"
    if status == 429 and (
        "insufficient_quota" in lowered
        or "quota" in lowered
        or "billing" in lowered
    ):
        return "OpenAI API 額度不足或尚未啟用計費（HTTP 429）。"
    if status == 429:
        return "OpenAI 語音轉錄請求過於頻繁，已達速率限制（HTTP 429）。"
    if status >= 500:
        return f"OpenAI 語音轉錄服務暫時異常（HTTP {status}）。"
    compact = " ".join(detail.split())[:180]
    return f"OpenAI 轉錄失敗（HTTP {status}）：{compact}"


def transcribe_wav_bytes(
    audio: bytes,
    api_key: str,
    model: str,
    language: str = "",
    prompt: str = "",
) -> str:
    """Transcribe a complete WAV utterance through the accurate endpoint."""
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
    if language:
        add_field("language", language)
    if prompt:
        add_field("prompt", prompt)
    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                'Content-Disposition: form-data; name="file"; '
                'filename="mohan.wav"\r\n'
            ).encode(),
            b"Content-Type: audio/wav\r\n\r\n",
            audio,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    request = urllib.request.Request(
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
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            transcription_http_error_message(exc.code, detail)
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"無法連線到 OpenAI：{exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise RuntimeError("OpenAI 轉錄連線逾時。") from exc
    text = str(result.get("text", "")).strip()
    if not text:
        raise RuntimeError(
            "OpenAI 已成功連線，但沒有從這段錄音辨識出文字。"
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


def emit_wave_viseme_cues(
    audio: bytes,
    emit_cue: Callable[[float, str], None],
    playback_start: threading.Event | None = None,
) -> None:
    """Emit the shared audio-driven mouth timeline for any WAV provider."""

    try:
        with wave.open(io.BytesIO(audio), "rb") as source:
            rate = source.getframerate()
            channels = source.getnchannels()
            width = source.getsampwidth()
            frames_per_chunk = max(1, rate // VISEME_CUES_PER_SECOND)
            if playback_start is not None:
                playback_start.wait(timeout=2.0)
            started_at = time.perf_counter()
            chunk_index = 0
            while chunk := source.readframes(frames_per_chunk):
                if width != 2:
                    continue
                if channels == 2:
                    chunk = stereo_to_mono_pcm16(chunk)
                vowel_level, vowel = infer_vowel_pcm16(chunk, rate)
                deadline = started_at + chunk_index * frames_per_chunk / rate
                remaining = deadline - time.perf_counter()
                if remaining > 0:
                    time.sleep(remaining)
                emit_cue(vowel_level, vowel)
                chunk_index += 1
    except (OSError, EOFError, wave.Error):
        return


def play_wave_with_visemes(
    audio: bytes,
    volume_percent: int,
    muted: bool,
    emit_cue: Callable[[float, str], None],
    audio_path: Path | None = None,
) -> None:
    """Play provider WAV audio through the single lip-sync implementation."""

    if winsound is None:
        raise OSError(
            "此平台的音訊播放介面尚未完成實機驗證；未播放這段語音。"
        )

    playback_start = threading.Event()
    cue_thread = threading.Thread(
        target=emit_wave_viseme_cues,
        args=(audio, emit_cue, playback_start),
        daemon=True,
    )
    cue_thread.start()
    playback_start.set()
    playback_audio = apply_wav_volume(audio, volume_percent, muted)
    if audio_path is not None and volume_percent == 100 and not muted:
        winsound.PlaySound(str(audio_path), winsound.SND_FILENAME)
    else:
        winsound.PlaySound(playback_audio, winsound.SND_MEMORY)
    cue_thread.join(timeout=0.35)
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


def windows_voice_catalog() -> list[WindowsVoiceInfo]:
    """Return installed female OneCore and Desktop SAPI voices."""

    if os.name != "nt":
        return []
    import winreg

    voices: list[WindowsVoiceInfo] = []
    locations = (
        (
            r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens",
            "OneCore::",
        ),
        (r"SOFTWARE\Microsoft\Speech\Voices\Tokens", ""),
    )
    for registry_path, prefix in locations:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as root:
                token_count = winreg.QueryInfoKey(root)[0]
                for index in range(token_count):
                    token = winreg.EnumKey(root, index)
                    with winreg.OpenKey(root, token + r"\Attributes") as attrs:
                        try:
                            name = str(winreg.QueryValueEx(attrs, "Name")[0])
                        except OSError:
                            name = token
                        try:
                            language = str(
                                winreg.QueryValueEx(attrs, "Language")[0]
                            ).split(";", 1)[0]
                            culture = locale.windows_locale.get(
                                int(language, 16), ""
                            ).replace("_", "-")
                        except (OSError, ValueError):
                            culture = ""
                        try:
                            gender = str(
                                winreg.QueryValueEx(attrs, "Gender")[0]
                            )
                        except OSError:
                            gender = ""
                    full_name = prefix + name
                    normalized_gender = _normalized_voice_gender(
                        gender,
                        full_name,
                    )
                    if _is_allowed_companion_voice(
                        full_name,
                        normalized_gender,
                    ):
                        voices.append(
                            WindowsVoiceInfo(
                                full_name,
                                culture,
                                normalized_gender,
                            )
                        )
        except OSError:
            continue
    return voices


def windows_voices() -> list[tuple[str, str]]:
    return [(voice.name, voice.culture) for voice in windows_voice_catalog()]


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


class WindowsTTS(QObject):
    failed = Signal(str)
    finished = Signal()
    viseme_cue = Signal(float, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.volume_percent = 125
        self.muted = False

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_percent = max(0, min(160, int(volume_percent)))
        self.muted = bool(muted)

    def speak(self, text: str, voice_name: str = "", rate: int = -1) -> None:
        if os.name != "nt" or not text.strip():
            self.finished.emit()
            return
        threading.Thread(
            target=self._run,
            args=(text, voice_name, rate),
            daemon=True,
        ).start()

    def _run(self, text: str, voice_name: str, rate: int) -> None:
        try:
            installed = windows_voices()
            selected_voice = preferred_windows_voice(
                installed,
                voice_name,
                "",
            )
            if not selected_voice:
                raise RuntimeError(
                    "Windows 沒有偵測到已明確標示為女性的本機語音。"
                )
            voice_name = selected_voice
            if voice_name.startswith("OneCore::"):
                self._run_onecore(
                    text,
                    voice_name.removeprefix("OneCore::"),
                )
            else:
                self._run_sapi(text, voice_name, rate)
            self.finished.emit()
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            if voice_name.startswith("OneCore::"):
                try:
                    desktop_voices = [
                        voice
                        for voice in windows_voices()
                        if not voice[0].startswith("OneCore::")
                    ]
                    fallback = preferred_windows_voice(desktop_voices)
                    self._run_sapi(text, fallback, rate)
                    self.finished.emit()
                    return
                except (OSError, subprocess.SubprocessError, RuntimeError):
                    pass
            self.failed.emit(str(exc))
            self.finished.emit()

    def _run_sapi(self, text: str, voice_name: str, rate: int) -> None:
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
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-EncodedCommand", command],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=120,
            )
            if result.returncode or not audio_path.exists():
                detail = result.stderr.decode("utf-8", errors="replace")[:240]
                raise RuntimeError(detail or "Windows 傳統語音播放失敗。")
            self._play_wave_bytes(audio_path.read_bytes(), audio_path)
        finally:
            audio_path.unlink(missing_ok=True)

    def _run_onecore(self, text: str, voice_name: str) -> None:
        fd, name = tempfile.mkstemp(prefix="mohan-onecore-", suffix=".wav")
        os.close(fd)
        audio_path = Path(name)
        audio_path.unlink(missing_ok=True)
        text_encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        voice_encoded = base64.b64encode(voice_name.encode("utf-8")).decode("ascii")
        path_encoded = base64.b64encode(
            str(audio_path).encode("utf-8")
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
            "$synth=[Windows.Media.SpeechSynthesis.SpeechSynthesizer]::new();"
            "$voice=[Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices|"
            "Where-Object{$_.DisplayName -eq $voiceName -or $_.Id -like ('*'+$voiceName+'*')}|"
            "Select-Object -First 1;"
            "if(-not $voice){throw ('找不到 OneCore 聲音：'+$voiceName)};"
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
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-EncodedCommand", command],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=120,
            )
            if result.returncode or not audio_path.exists():
                detail = result.stderr.decode("utf-8", errors="replace")[:3000]
                raise RuntimeError(detail or "OneCore 語音合成失敗。")
            self._play_wave_bytes(audio_path.read_bytes(), audio_path)
        finally:
            audio_path.unlink(missing_ok=True)

    def _play_wave_bytes(
        self,
        audio: bytes,
        audio_path: Path | None = None,
    ) -> None:
        play_wave_with_visemes(
            audio,
            self.volume_percent,
            self.muted,
            self.viseme_cue.emit,
            audio_path,
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


class OpenAITTS(QObject):
    failed = Signal(str)
    finished = Signal()
    viseme_cue = Signal(float, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
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
            self.failed.emit("尚未設定 OpenAI API 金鑰")
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
        request = urllib.request.Request(
            "https://api.openai.com/v1/audio/speech",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                audio = response.read()
            play_wave_with_visemes(
                audio,
                self.volume_percent,
                self.muted,
                self.viseme_cue.emit,
            )
            self.finished.emit()
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            OSError,
            RuntimeError,
            TimeoutError,
            wave.Error,
        ) as exc:
            self.failed.emit(str(exc))

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

    TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
    RECORD_BLOCK_SECONDS = 0.1
    END_SILENCE_SECONDS = 0.85
    MIN_SPEECH_SECONDS = 0.8
    INITIAL_SILENCE_SECONDS = 2.0
    MAX_RECORD_SECONDS = 10.0
    ACTIVE_SPEECH_THRESHOLD_RATIO = 0.68
    TRANSCRIPTION_PROMPT = (
        "請依使用者選擇的語言精確轉錄，保留原意，不要改寫。"
        "人名、公司名、產品名與工作術語請優先依提示中的常用詞判斷。"
    )

    def __init__(
        self,
        script_path: Path,
        api_key_provider: Callable[[], str] | None = None,
        recognition_mode_provider: Callable[[], str] | None = None,
        transcription_model_provider: Callable[[], str] | None = None,
        transcription_language_provider: Callable[[], str] | None = None,
        transcription_prompt_provider: Callable[[], str] | None = None,
        windows_fallback_provider: Callable[[], bool] | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.script_path = script_path
        self.api_key_provider = api_key_provider or (lambda: "")
        self.recognition_mode_provider = recognition_mode_provider or (
            lambda: "OpenAI 高準確辨識（推薦）"
        )
        self.transcription_model_provider = (
            transcription_model_provider
            or (lambda: self.TRANSCRIPTION_MODEL)
        )
        self.transcription_language_provider = (
            transcription_language_provider or (lambda: "zh")
        )
        self.transcription_prompt_provider = (
            transcription_prompt_provider
            or (lambda: self.TRANSCRIPTION_PROMPT)
        )
        self.windows_fallback_provider = (
            windows_fallback_provider or (lambda: True)
        )
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
            self.status_changed.emit("正在結束收音並送出…")
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
                reason = "未設定 OpenAI API 金鑰。"
                self.diagnostic_changed.emit(reason)
                if self.windows_fallback_provider():
                    self._start_windows(fallback_reason=reason)
                else:
                    self.failed.emit(reason + "Windows 備援目前已關閉。")
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
                "收音中…再次點擊麥克風可立即送出"
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
        self.process.errorOccurred.connect(lambda _e: self.failed.emit("無法啟動語音辨識"))
        if audio_path is None:
            self.listening_changed.emit(True)
            self.status_changed.emit("收音與辨識中…")
        else:
            self.status_changed.emit(
                f"{fallback_reason} 正在使用 Windows 備援辨識…"
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

    def _record_wav(self) -> Path:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("缺少麥克風錄音元件 sounddevice。") from exc

        sample_rate = 16000
        block_size = int(sample_rate * self.RECORD_BLOCK_SECONDS)
        frames: list[bytes] = []
        speech_started = False
        speech_blocks = 0
        quiet_blocks = 0
        baseline: list[float] = []
        threshold = 120.0

        try:
            with sd.RawInputStream(
                samplerate=sample_rate,
                blocksize=block_size,
                channels=1,
                dtype="int16",
            ) as stream:
                max_blocks = int(
                    self.MAX_RECORD_SECONDS / self.RECORD_BLOCK_SECONDS
                )
                initial_silence_blocks = int(
                    self.INITIAL_SILENCE_SECONDS / self.RECORD_BLOCK_SECONDS
                )
                end_silence_blocks = math.ceil(
                    self.END_SILENCE_SECONDS / self.RECORD_BLOCK_SECONDS
                )
                minimum_speech_blocks = math.ceil(
                    self.MIN_SPEECH_SECONDS / self.RECORD_BLOCK_SECONDS
                )
                for _ in range(max_blocks):
                    data, _overflowed = stream.read(block_size)
                    chunk = bytes(data)
                    frames.append(chunk)
                    level = self._rms(chunk)

                    if self._stop_recording.is_set():
                        if speech_started:
                            break
                        raise RuntimeError(
                            "尚未偵測到說話聲，沒有送出空白錄音。"
                        )

                    if not speech_started and len(baseline) < 3:
                        baseline.append(level)
                        if level > 500:
                            speech_started = True
                        elif len(baseline) == 3:
                            threshold = max(120.0, (sum(baseline) / 3) * 2.2)
                        continue

                    active_threshold = (
                        max(
                            90.0,
                            threshold * self.ACTIVE_SPEECH_THRESHOLD_RATIO,
                        )
                        if speech_started
                        else threshold
                    )
                    if level >= active_threshold:
                        speech_started = True
                        quiet_blocks = 0
                    elif speech_started:
                        quiet_blocks += 1
                        if (
                            speech_blocks >= minimum_speech_blocks
                            and quiet_blocks >= end_silence_blocks
                        ):
                            break
                    elif len(frames) >= initial_silence_blocks:
                        raise RuntimeError("沒有偵測到說話聲，請靠近麥克風後再試一次。")
                    if speech_started:
                        speech_blocks += 1
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"無法使用 Windows 預設麥克風：{exc}") from exc

        if not speech_started:
            raise RuntimeError("沒有偵測到說話聲，請靠近麥克風後再試一次。")

        fd, name = tempfile.mkstemp(prefix="mohan-recording-", suffix=".wav")
        os.close(fd)
        path = Path(name)
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(sample_rate)
            output.writeframes(b"".join(frames))
        return path

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
            language or "",
            prompt or "",
        )

    @staticmethod
    def _http_error_message(status: int, detail: str) -> str:
        return transcription_http_error_message(status, detail)

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
            self.status_changed.emit("辨識中…")
            text = self._transcribe(
                audio_path,
                api_key,
                model=model,
                language=language,
                prompt=prompt,
            )
            self.diagnostic_changed.emit(
                f"OpenAI 轉錄成功：{model}"
            )
            self.recognized.emit(text)
            audio_path.unlink(missing_ok=True)
            self._busy.clear()
            self.listening_changed.emit(False)
        except Exception as exc:
            self._recording_active.clear()
            self.recording_changed.emit(False)
            reason = str(exc)
            self.diagnostic_changed.emit(reason)
            if audio_path and audio_path.exists():
                if fallback_enabled:
                    # 雲端不可用時，將同一段錄音交給 Windows，不要求使用者重說。
                    self._fallback_requested.emit(str(audio_path), reason)
                else:
                    audio_path.unlink(missing_ok=True)
                    self._busy.clear()
                    self.failed.emit(reason + " Windows 備援目前已關閉。")
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
                "Windows 尚未安裝中文語音辨識套件，請先在語言設定加入中文語音功能。"
            )
        elif text.startswith("__ERROR__:"):
            detail = text.removeprefix("__ERROR__:")
            if "0x80070005" in detail or "Access is denied" in detail:
                self.failed.emit(
                    "Windows 拒絕墨寒使用麥克風。請到「設定 → "
                    "隱私權與安全性 → 麥克風」，開啟麥克風存取權、"
                    "讓應用程式存取麥克風，以及讓桌面應用程式存取麥克風。"
                )
            else:
                self.failed.emit("Windows 語音辨識無法使用：" + detail)
        elif text and text != "__EMPTY__":
            self.recognized.emit(text)
        elif stderr:
            self.failed.emit(f"Windows 語音辨識啟動失敗：{stderr[:180]}")
        else:
            self.failed.emit("寒方才未聽清，請再說一次。")
