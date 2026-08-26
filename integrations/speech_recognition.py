from __future__ import annotations

lazy import json
lazy import os
lazy from collections.abc import Callable
lazy from dataclasses import dataclass, field
lazy from urllib.error import HTTPError, URLError
lazy from urllib.request import Request, urlopen

MAX_TRANSCRIPTION_RESPONSE_BYTES = 1024 * 1024
MAX_TRANSCRIPTION_ERROR_BYTES = 64 * 1024

lazy from domain.safe_error import sanitize_error
lazy from domain.service_status_localization import ServiceStatus, service_status

BASELINE_SAMPLES = 3
SPEECH_START_THRESHOLD = 500
SERVER_ERROR_BOUNDARY = 500


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
        if self.speech_started or len(baseline) >= BASELINE_SAMPLES:
            return False
        baseline.append(level)
        if level > SPEECH_START_THRESHOLD:
            self.speech_started = True
        elif len(baseline) == BASELINE_SAMPLES:
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
                self.speech_blocks >= self.limits.minimum_speech_blocks
                and self.quiet_blocks >= self.limits.end_silence_blocks
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
            marker in lowered for marker in ("insufficient_quota", "quota", "billing")
        ):
            key = ServiceStatus.SPEECH_OPENAI_QUOTA_EXHAUSTED
        case 429:
            key = ServiceStatus.SPEECH_OPENAI_RATE_LIMITED
        case _ if status >= SERVER_ERROR_BOUNDARY:
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


@dataclass(frozen=True, slots=True)
class TranscriptionRequest:
    model: str
    language: str | SpeechTranscriptionLocale = ""
    prompt: str = ""


@dataclass(frozen=True, slots=True)
class TranscriptionHttpBoundary:
    open_request: Callable[..., object] = urlopen
    default_model: str = "gpt-4o-mini-transcribe"


def transcribe_wav_bytes_impl(
    audio: bytes,
    api_key: str,
    request_options: TranscriptionRequest,
    http: TranscriptionHttpBoundary,
) -> str:
    """Transcribe a complete WAV utterance through the accurate endpoint."""
    locale = (
        request_options.language
        if isinstance(request_options.language, SpeechTranscriptionLocale)
        else SpeechTranscriptionLocale(
            provider_language=request_options.language,
        )
    )
    boundary = f"----MohanBoundary{os.urandom(12).hex()}"
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.extend([
            f"--{boundary}\r\n".encode(),
            (f'Content-Disposition: form-data; name="{name}"\r\n\r\n').encode(),
            value.encode("utf-8"),
            b"\r\n",
        ])

    add_field("model", request_options.model or http.default_model)
    if locale.provider_language:
        add_field("language", locale.provider_language)
    if request_options.prompt:
        add_field("prompt", request_options.prompt)
    parts.extend([
        f"--{boundary}\r\n".encode(),
        (b'Content-Disposition: form-data; name="file"; filename="mohan.wav"\r\n'),
        b"Content-Type: audio/wav\r\n\r\n",
        audio,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    request = Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=b"".join(parts),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": (f"multipart/form-data; boundary={boundary}"),
        },
        method="POST",
    )
    try:
        with http.open_request(request, timeout=60) as response:
            payload = response.read(MAX_TRANSCRIPTION_RESPONSE_BYTES + 1)
        if len(payload) > MAX_TRANSCRIPTION_RESPONSE_BYTES:
            raise ValueError("transcription-response-too-large")
        result = json.loads(payload.decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read(MAX_TRANSCRIPTION_ERROR_BYTES).decode(
            "utf-8", errors="replace"
        )
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
    except (UnicodeError, ValueError, json.JSONDecodeError):
        failure = service_status(
            locale.ui_language,
            ServiceStatus.SPEECH_OPENAI_EMPTY_RESULT,
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
