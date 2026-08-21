from __future__ import annotations

lazy import queue
lazy import re
lazy import threading
lazy import time
lazy from contextlib import suppress
lazy from dataclasses import dataclass, field
lazy from xml.sax.saxutils import escape, quoteattr

lazy from azure.cognitiveservices import speech as speechsdk
lazy from PySide6.QtCore import QObject, Signal

lazy from domain.audio_acceleration import (
    PYTHON_PCM_ACCELERATION,
    PcmAccelerationPort,
)
lazy from domain.immutable_config import deep_freeze
lazy from domain.language_support import canonical_ui_language
lazy from domain.speech_boundary import SpeechTimingCollector, SpeechTimingEvent
lazy from integrations.azure_regions import azure_region_supports_hd_flash
lazy from integrations.azure_voice_catalog import (
    AzureVoiceCatalog,
    AzureVoiceCatalogService,
)
lazy from integrations.speech import play_pcm16_stream_with_visemes

VOICE_LOCALE_PREFIX_LENGTH = 5
RATE_LIMIT_STATUS = 429
SERVER_ERROR_BOUNDARY = 500

AZURE_FEMALE_VOICES: frozendict[str, tuple[str, ...]] = frozendict({
    "zh-TW": (
        "zh-TW-HsiaoChenNeural",
        "zh-TW-HsiaoYuNeural",
    ),
    "zh-CN": (
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-XiaoyiNeural",
        "zh-CN-XiaochenNeural",
        "zh-CN-XiaohanNeural",
        "zh-CN-XiaomengNeural",
        "zh-CN-XiaomoNeural",
        "zh-CN-XiaoqiuNeural",
        "zh-CN-XiaorouNeural",
        "zh-CN-XiaoruiNeural",
    ),
    "en-US": (
        "en-US-AvaMultilingualNeural",
        "en-US-AmandaMultilingualNeural",
        "en-US-CoraMultilingualNeural",
        "en-US-JennyMultilingualNeural",
    ),
    "ja-JP": (
        "ja-JP-NanamiNeural",
        "ja-JP-AoiNeural",
        "ja-JP-MayuNeural",
        "ja-JP-ShioriNeural",
    ),
})
AZURE_HD_FEMALE_VOICES: frozendict[str, tuple[str, ...]] = frozendict({
    "zh-CN": (
        "zh-CN-Xiaochen:DragonHDLatestNeural",
        "zh-CN-Xiaoyue:DragonHDOmniLatestNeural",
        "zh-CN-Maroonallegro:DragonHDOmniLatestNeural",
        "zh-CN-Xiaoxiao:DragonHDFlashLatestNeural",
        "zh-CN-Xiaoxiao2:DragonHDFlashLatestNeural",
        "zh-CN-Xiaochen:DragonHDFlashLatestNeural",
        "zh-CN-Xiaoyi:DragonHDFlashLatestNeural",
        "zh-CN-Xiaoyu:DragonHDFlashLatestNeural",
        "zh-CN-Xiaohan:DragonHDFlashLatestNeural",
        "zh-CN-Xiaoshuang:DragonHDFlashLatestNeural",
        "zh-CN-Xiaoyou:DragonHDFlashLatestNeural",
    ),
    "en-US": (
        "en-US-Ava:DragonHDLatestNeural",
        "en-US-Aria:DragonHDLatestNeural",
        "en-US-Emma:DragonHDLatestNeural",
        "en-US-Emma2:DragonHDLatestNeural",
        "en-US-Jenny:DragonHDLatestNeural",
        "en-US-Nova:DragonHDLatestNeural",
        "en-US-Phoebe:DragonHDLatestNeural",
        "en-US-Serena:DragonHDLatestNeural",
    ),
    "ja-JP": ("ja-JP-Nanami:DragonHDLatestNeural",),
})


def _build_voice_locale_index() -> frozendict[str, str]:
    index: dict[str, str] = {}
    for catalog in (AZURE_FEMALE_VOICES, AZURE_HD_FEMALE_VOICES):
        for locale, voices in catalog.items():
            index.update(dict.fromkeys(voices, locale))
    return frozendict(index)


_VOICE_LOCALE = _build_voice_locale_index()
_REGION_PATTERN = re.compile(r"^[a-z0-9-]{2,32}$")
_VOICE_PATTERN = re.compile(
    r"^(zh-(?:TW|CN)|en-US|ja-JP)-[A-Za-z0-9]+"
    r"(?::DragonHD(?:Omni|Flash)?LatestNeural|Neural)$"
)
_AUDIO_CHUNK_MAX_BYTES = 65_536
_AUDIO_QUEUE_MAX_CHUNKS = 64
_AUDIO_QUEUE_POLL_SECONDS = 0.05
_AUDIO_STREAM_TIMEOUT_SECONDS = 60.0
_MESSAGES = deep_freeze({
    "zh-TW": {
        "invalid_region": "Azure Speech 區域格式不正確。",
        "unsupported_voice": "Azure Speech 只允許已確認的女性聲線。",
        "missing_settings": "尚未設定 Azure Speech 金鑰與區域。",
        "credentials": "Azure Speech 金鑰、區域或資源權限不正確。",
        "quota": "Azure Speech 免費額度或速率限制已達上限。",
        "service": "Azure Speech 服務暫時異常（HTTP {status}）。",
        "request": "Azure Speech 失敗（HTTP {status}）。",
        "network": "無法連線到 Azure Speech：{error}",
    },
    "zh-CN": {
        "invalid_region": "Azure Speech 区域格式不正确。",
        "unsupported_voice": "Azure Speech 只允许已确认的女性声线。",
        "missing_settings": "尚未设置 Azure Speech 密钥与区域。",
        "credentials": "Azure Speech 密钥、区域或资源权限不正确。",
        "quota": "Azure Speech 免费额度或速率限制已达到上限。",
        "service": "Azure Speech 服务暂时异常（HTTP {status}）。",
        "request": "Azure Speech 失败（HTTP {status}）。",
        "network": "无法连接 Azure Speech：{error}",
    },
    "en-US": {
        "invalid_region": "The Azure Speech region is invalid.",
        "unsupported_voice": ("Azure Speech accepts only verified female voices."),
        "missing_settings": (
            "The Azure Speech key and region have not been configured."
        ),
        "credentials": (
            "The Azure Speech key, region, or resource permission is invalid."
        ),
        "quota": "The Azure Speech quota or rate limit has been reached.",
        "service": ("Azure Speech is temporarily unavailable (HTTP {status})."),
        "request": "Azure Speech failed (HTTP {status}).",
        "network": "Could not connect to Azure Speech: {error}",
    },
    "ja-JP": {
        "invalid_region": "Azure Speech のリージョン形式が正しくありません。",
        "unsupported_voice": "確認済みの女性音声だけを使用できます。",
        "missing_settings": "Azure Speech のキーとリージョンが未設定です。",
        "credentials": "Azure Speech のキー、リージョン、またはリソース権限が正しくありません。",
        "quota": "Azure Speech の無料枠またはレート上限に達しました。",
        "service": "Azure Speech は一時的に利用できません（HTTP {status}）。",
        "request": "Azure Speech に失敗しました（HTTP {status}）。",
        "network": "Azure Speech に接続できません：{error}",
    },
})


class _PushAudioReader:
    """Adapt Azure's push callback to the playback loop's bounded reads."""

    def __init__(self) -> None:
        self._chunks: queue.Queue[bytes] = queue.Queue(maxsize=_AUDIO_QUEUE_MAX_CHUNKS)
        self._pending = bytearray()
        self._pending_lock = threading.Lock()
        self._cancelled = threading.Event()
        self._closed = threading.Event()

    def write(self, audio_buffer: memoryview) -> int:
        chunk = bytes(audio_buffer)
        for offset in range(0, len(chunk), _AUDIO_CHUNK_MAX_BYTES):
            bounded_chunk = chunk[offset : offset + _AUDIO_CHUNK_MAX_BYTES]
            while not self._cancelled.is_set() and not self._closed.is_set():
                try:
                    self._chunks.put(
                        bounded_chunk,
                        timeout=_AUDIO_QUEUE_POLL_SECONDS,
                    )
                    break
                except queue.Full:
                    continue
        return len(chunk)

    def close(self) -> None:
        self._closed.set()

    def cancel(self) -> None:
        self._cancelled.set()
        self._closed.set()
        with self._pending_lock:
            self._pending.clear()
        while True:
            try:
                self._chunks.get_nowait()
            except queue.Empty:
                break

    def read(self, audio_buffer: bytearray) -> int:
        if self._cancelled.is_set():
            return 0
        deadline = time.monotonic() + _AUDIO_STREAM_TIMEOUT_SECONDS
        while True:
            with self._pending_lock:
                if self._pending:
                    bytes_read = min(len(audio_buffer), len(self._pending))
                    audio_buffer[:bytes_read] = self._pending[:bytes_read]
                    del self._pending[:bytes_read]
                    return bytes_read
            if self._cancelled.is_set():
                return 0
            if self._closed.is_set() and self._chunks.empty():
                return 0
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                raise TimeoutError("Azure audio stream timed out")
            try:
                chunk = self._chunks.get(
                    timeout=min(_AUDIO_QUEUE_POLL_SECONDS, remaining)
                )
            except queue.Empty as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Azure audio stream timed out") from exc
                continue
            with self._pending_lock:
                self._pending.extend(chunk)


@dataclass(slots=True)
class _SynthesisOutcome:
    result: object | None = None
    failure: Exception | None = None
    done: threading.Event = field(default_factory=threading.Event)


@dataclass(frozen=True, slots=True)
class _SynthesisRequest:
    text: str
    api_key: str = field(repr=False)
    region: str
    voice: str
    locale: str


def _await_synthesis(
    synthesis: object,
    audio_reader: _PushAudioReader,
    outcome: _SynthesisOutcome,
) -> None:
    try:
        outcome.result = synthesis.get()
    except (OSError, RuntimeError, TimeoutError) as exc:
        outcome.failure = exc
    finally:
        audio_reader.close()
        outcome.done.set()


def _streaming_synthesizer(
    api_key: str,
    region: str,
) -> tuple[_PushAudioReader, object]:
    speech_config = speechsdk.SpeechConfig(
        subscription=api_key,
        region=region,
    )
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Raw24Khz16BitMonoPcm
    )
    audio_reader = _PushAudioReader()

    class StreamCallback(speechsdk.audio.PushAudioOutputStreamCallback):
        def __init__(self) -> None:
            super().__init__()

        def write(self, audio_buffer: memoryview) -> int:
            return audio_reader.write(audio_buffer)

        def close(self) -> None:
            audio_reader.close()

    push_stream = speechsdk.audio.PushAudioOutputStream(StreamCallback())
    audio_config = speechsdk.audio.AudioOutputConfig(stream=push_stream)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )
    return audio_reader, synthesizer


def _completed_synthesis_result(outcome: _SynthesisOutcome) -> object:
    if not outcome.done.wait(timeout=60.0):
        raise TimeoutError("Azure synthesis did not finish")
    if outcome.failure is not None:
        raise outcome.failure
    if outcome.result is None:
        raise RuntimeError("Azure synthesis returned no result")
    return outcome.result


def _message(locale: str, key: str, **values: object) -> str:
    normalized = canonical_ui_language(locale)
    catalog_key = "en-US" if normalized == "en" else normalized
    catalog = _MESSAGES[catalog_key]
    return catalog[key].format(**values)


def _error_locale(locale: str, voice: str) -> str:
    """Use the explicit UI locale, retaining compatibility for old callers."""

    return canonical_ui_language(locale) if locale.strip() else _voice_locale(voice)


def normalize_azure_region(region: str) -> str:
    normalized = str(region or "").strip().lower()
    if not _REGION_PATTERN.fullmatch(normalized):
        raise ValueError("invalid_region")
    return normalized


def azure_female_voices(language: str) -> tuple[str, ...]:
    normalized = str(language or "").strip().lower()
    if normalized == "zh-cn":
        return (
            *AZURE_FEMALE_VOICES["zh-CN"],
            *AZURE_FEMALE_VOICES["zh-TW"],
        )
    if normalized in {"en", "en-us"}:
        return AZURE_FEMALE_VOICES["en-US"]
    if normalized in {"ja", "ja-jp"}:
        return AZURE_FEMALE_VOICES["ja-JP"]
    return (
        *AZURE_FEMALE_VOICES["zh-TW"],
        *AZURE_FEMALE_VOICES["zh-CN"],
    )


def azure_hd_female_voices(
    language: str,
    *,
    include_flash: bool = True,
) -> tuple[str, ...]:
    normalized = str(language or "").strip().lower()
    if normalized in {"en", "en-us"}:
        voices = AZURE_HD_FEMALE_VOICES["en-US"]
    elif normalized in {"ja", "ja-jp"}:
        voices = AZURE_HD_FEMALE_VOICES["ja-JP"]
    else:
        voices = AZURE_HD_FEMALE_VOICES["zh-CN"]
    if include_flash:
        return voices
    return tuple(voice for voice in voices if not azure_hd_voice_uses_flash(voice))


def azure_hd_voice_uses_flash(voice: str) -> bool:
    return ":DragonHDFlash" in str(voice)


def is_azure_hd_voice(voice: str) -> bool:
    return ":DragonHD" in str(voice)


def _render_azure_ssml(text: str, voice: str) -> bytes:
    if not _VOICE_PATTERN.fullmatch(voice):
        raise ValueError("unsupported_voice")
    locale = _VOICE_LOCALE.get(voice, voice[:5])
    parameters = " parameters='temperature=0.8'" if is_azure_hd_voice(voice) else ""
    body = (
        f"<speak version='1.0' xml:lang={quoteattr(locale)}>"
        f"<voice xml:lang={quoteattr(locale)} xml:gender='Female' "
        f"name={quoteattr(voice)}{parameters}>{escape(text)}</voice></speak>"
    )
    return body.encode("utf-8")


def build_azure_ssml(text: str, voice: str) -> bytes:
    """Build SSML only for the bundled, statically verified female voices."""
    if voice not in _VOICE_LOCALE:
        raise ValueError("unsupported_voice")
    return _render_azure_ssml(text, voice)


def _voice_locale(voice: str) -> str:
    return _VOICE_LOCALE.get(voice, voice[:VOICE_LOCALE_PREFIX_LENGTH] if len(voice) >= VOICE_LOCALE_PREFIX_LENGTH else "zh-TW")


def azure_speech_error_message(
    status: int,
    detail: str,
    locale: str = "zh-TW",
) -> str:
    _ = detail  # Never echo a remote response that could contain user data.
    if status in {401, 403}:
        return _message(locale, "credentials")
    if status == RATE_LIMIT_STATUS:
        return _message(locale, "quota")
    if status >= SERVER_ERROR_BOUNDARY:
        return _message(locale, "service", status=status)
    return _message(locale, "request", status=status)


class AzureSpeechTTS(QObject):
    failed = Signal(str)
    finished = Signal()
    synthesis_latency_measured = Signal(float)
    viseme_cue = Signal(float, str)
    operation_started = Signal(int)
    operation_failed = Signal(int, str)
    operation_finished = Signal(int)
    operation_synthesis_latency_measured = Signal(int, float)
    operation_viseme_cue = Signal(int, float, str)
    operation_timing_event = Signal(object)
    voice_catalog_ready = Signal(object)
    voice_catalog_failed = Signal(str, str, bool)
    _voice_catalog_result_pending = Signal(int, object)
    _voice_catalog_fallback_pending = Signal(int, str, str, bool)

    def __init__(
        self,
        parent: QObject | None = None,
        catalog_service: AzureVoiceCatalogService | None = None,
        *,
        pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
    ):
        super().__init__(parent)
        self._pcm = pcm_acceleration
        self.volume_percent = 125
        self.muted = False
        self.last_synthesis_latency_ms: float | None = None
        self._catalog_service = catalog_service or AzureVoiceCatalogService()
        self._catalog_lock = threading.Lock()
        self._catalog_generation = 0
        self._playback_lock = threading.RLock()
        self._playback_generation = 0
        self._active_reader: _PushAudioReader | None = None
        self._active_synthesizer: object | None = None
        self._voice_catalog_result_pending.connect(
            self._publish_voice_catalog_result
        )
        self._voice_catalog_fallback_pending.connect(
            self._publish_fallback_catalog
        )

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_percent = max(0, min(160, int(volume_percent)))
        self.muted = bool(muted)

    def speak(
        self,
        text: str,
        api_key: str,
        region: str,
        voice: str,
        locale: str = "",
    ) -> None:
        operation_id = self._begin_operation()
        self._emit_started(operation_id)
        if not text.strip():
            self._emit_finished(operation_id)
            return
        locale = _error_locale(locale, voice)
        if not api_key.strip() or not region.strip():
            self._emit_failed(
                operation_id,
                _message(locale, "missing_settings"),
            )
            return
        try:
            normalized_region = normalize_azure_region(region)
            if not _VOICE_PATTERN.fullmatch(voice):
                raise ValueError("unsupported_voice")
        except ValueError as exc:
            self._emit_failed(operation_id, _message(locale, str(exc)))
            return
        threading.Thread(
            target=self._run,
            args=(
                _SynthesisRequest(
                    text=text,
                    api_key=api_key,
                    region=normalized_region,
                    voice=voice,
                    locale=locale,
                ),
                operation_id,
            ),
            daemon=True,
        ).start()

    def stop(self) -> None:
        """Cancel only this engine instance's current synthesis and playback."""
        with self._playback_lock:
            self._playback_generation += 1
            reader = self._active_reader
            synthesizer = self._active_synthesizer
            self._active_reader = None
            self._active_synthesizer = None
        self._cancel_playback(reader, synthesizer)

    def close(self) -> None:
        """End playback and reject every catalog result still in flight."""
        self.stop()
        self.invalidate_voice_catalog()

    @staticmethod
    def _cancel_playback(
        reader: _PushAudioReader | None,
        synthesizer: object | None,
    ) -> None:
        if reader is not None:
            reader.cancel()
        stop_speaking = getattr(synthesizer, "stop_speaking_async", None)
        if stop_speaking is not None:
            with suppress(RuntimeError, OSError):
                stop_speaking()

    def invalidate_voice_catalog(self, region: str | None = None) -> None:
        with self._catalog_lock:
            self._catalog_generation += 1
        self._catalog_service.invalidate(region)

    def _begin_catalog_request(self) -> int:
        with self._catalog_lock:
            self._catalog_generation += 1
            return self._catalog_generation

    def _is_current_catalog_request(self, generation: int) -> bool:
        with self._catalog_lock:
            return generation == self._catalog_generation

    def refresh_voice_catalog(
        self,
        api_key: str,
        region: str,
        language: str,
        *,
        hd_only: bool,
    ) -> None:
        generation = self._begin_catalog_request()
        try:
            normalized_region = normalize_azure_region(region)
        except ValueError:
            if self._is_current_catalog_request(generation):
                self.voice_catalog_failed.emit(region, language, hd_only)
            return
        if not api_key.strip():
            self._queue_fallback_catalog(
                normalized_region,
                language,
                hd_only,
                generation,
            )
            return
        threading.Thread(
            target=self._query_voice_catalog,
            args=(
                api_key,
                normalized_region,
                language,
                hd_only,
                generation,
            ),
            daemon=True,
        ).start()

    def _query_voice_catalog(
        self,
        api_key: str,
        region: str,
        language: str,
        hd_only: bool,
        generation: int,
    ) -> None:
        try:
            catalog = self._catalog_service.query(
                api_key,
                region,
                language,
                hd_only=hd_only,
            )
        except ImportError, OSError, RuntimeError, TimeoutError, ValueError:
            self._queue_fallback_catalog(
                region,
                language,
                hd_only,
                generation,
            )
            return
        self._voice_catalog_result_pending.emit(generation, catalog)

    def _queue_fallback_catalog(
        self,
        region: str,
        language: str,
        hd_only: bool,
        generation: int,
    ) -> None:
        self._voice_catalog_fallback_pending.emit(
            generation,
            region,
            language,
            hd_only,
        )

    def _publish_voice_catalog_result(
        self,
        generation: int,
        catalog: AzureVoiceCatalog,
    ) -> None:
        if not self._is_current_catalog_request(generation):
            return
        self.voice_catalog_ready.emit(catalog)

    def _publish_fallback_catalog(
        self,
        generation: int,
        region: str,
        language: str,
        hd_only: bool,
    ) -> None:
        if not self._is_current_catalog_request(generation):
            return
        if hd_only:
            voices = azure_hd_female_voices(
                language,
                include_flash=azure_region_supports_hd_flash(region),
            )
        else:
            voices = azure_female_voices(language)
        self.voice_catalog_ready.emit(
            AzureVoiceCatalog(
                region=region,
                language=language,
                hd_only=hd_only,
                voices=voices,
                source="fallback",
            )
        )

    def _run(
        self,
        request: _SynthesisRequest,
        operation_id: int,
    ) -> None:
        if not self._is_current_playback(operation_id):
            return
        try:
            ssml = self._verified_ssml_for_request(
                request.text,
                request.api_key,
                request.region,
                request.voice,
            )
        except OSError, RuntimeError, TimeoutError, ValueError:
            self._emit_failed(
                operation_id,
                _message(request.locale, "unsupported_voice"),
            )
            return
        if not self._is_current_playback(operation_id):
            return
        try:
            request_started = time.perf_counter()
            audio_reader, synthesizer = _streaming_synthesizer(
                request.api_key,
                request.region,
            )
            if not self._activate_playback(
                operation_id,
                audio_reader,
                synthesizer,
            ):
                audio_reader.close()
                return
            self._connect_native_timing(synthesizer, operation_id)
            synthesis = synthesizer.speak_ssml_async(
                ssml.decode("utf-8")
            )
            outcome = _SynthesisOutcome()
            result_thread = threading.Thread(
                target=_await_synthesis,
                args=(synthesis, audio_reader, outcome),
                daemon=True,
            )
            result_thread.start()

            def record_first_audio() -> None:
                self._record_synthesis_latency(
                    operation_id,
                    request_started,
                )

            def emit_viseme(level: float, vowel: str) -> None:
                self._emit_viseme(operation_id, level, vowel)

            play_pcm16_stream_with_visemes(
                audio_reader.read,
                volume_percent=self.volume_percent,
                muted=self.muted,
                emit_cue=emit_viseme,
                on_first_audio=record_first_audio,
                pcm_acceleration=self._pcm,
            )
            if not self._is_current_playback(operation_id):
                return
            result = _completed_synthesis_result(outcome)
            if result.reason == speechsdk.ResultReason.Canceled:
                self._emit_failed(
                    operation_id,
                    _message(request.locale, "service", status=503),
                )
                return
            self._emit_finished(operation_id)
        except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
            self._emit_failed(
                operation_id,
                _message(
                    request.locale,
                    "network",
                    error=type(exc).__name__,
                ),
            )
        finally:
            self._release_playback(operation_id)

    def _connect_native_timing(
        self,
        synthesizer: object,
        operation_id: int,
    ) -> None:
        """Best-effort native timing; local 50 Hz mouth cues remain authoritative fallback."""

        collector = SpeechTimingCollector(operation_id)

        def emit(event: SpeechTimingEvent | None) -> None:
            if event is None:
                return
            with self._playback_lock:
                if operation_id == self._playback_generation:
                    self.operation_timing_event.emit(event)

        word_signal = getattr(synthesizer, "synthesis_word_boundary", None)
        viseme_signal = getattr(synthesizer, "viseme_received", None)
        connect_word = getattr(word_signal, "connect", None)
        connect_viseme = getattr(viseme_signal, "connect", None)
        if callable(connect_word):
            with suppress(RuntimeError, OSError, TypeError, AttributeError):
                connect_word(lambda event: emit(collector.word_boundary(event)))
        if callable(connect_viseme):
            with suppress(RuntimeError, OSError, TypeError, AttributeError):
                connect_viseme(lambda event: emit(collector.viseme(event)))

    def _verified_ssml_for_request(
        self,
        text: str,
        api_key: str,
        region: str,
        voice: str,
    ) -> bytes:
        if voice in _VOICE_LOCALE:
            return build_azure_ssml(text, voice)
        if not _VOICE_PATTERN.fullmatch(voice):
            raise ValueError("unsupported_voice")
        locale = _voice_locale(voice)
        hd_only = is_azure_hd_voice(voice)
        catalog = self._catalog_service.query(
            api_key,
            region,
            locale,
            hd_only=hd_only,
        )
        expected_catalog = (
            catalog.source == "azure"
            and catalog.region == region
            and catalog.language == locale
            and catalog.hd_only == hd_only
            and voice in catalog.voices
        )
        if not expected_catalog:
            raise ValueError("unsupported_voice")
        return _render_azure_ssml(text, voice)

    def _begin_operation(self) -> int:
        with self._playback_lock:
            self._playback_generation += 1
            operation_id = self._playback_generation
            reader = self._active_reader
            synthesizer = self._active_synthesizer
            self._active_reader = None
            self._active_synthesizer = None
        self._cancel_playback(reader, synthesizer)
        return operation_id

    def _activate_playback(
        self,
        operation_id: int,
        audio_reader: _PushAudioReader,
        synthesizer: object,
    ) -> bool:
        with self._playback_lock:
            if operation_id != self._playback_generation:
                return False
            self._active_reader = audio_reader
            self._active_synthesizer = synthesizer
            return True

    def _is_current_playback(self, operation_id: int) -> bool:
        with self._playback_lock:
            return operation_id == self._playback_generation

    def _record_synthesis_latency(
        self,
        operation_id: int,
        request_started: float,
    ) -> None:
        latency_ms = max(
            0.0,
            (time.perf_counter() - request_started) * 1_000.0,
        )
        with self._playback_lock:
            if operation_id != self._playback_generation:
                return
            self.last_synthesis_latency_ms = latency_ms
            self.operation_synthesis_latency_measured.emit(
                operation_id,
                latency_ms,
            )
            if operation_id == self._playback_generation:
                self.synthesis_latency_measured.emit(latency_ms)

    def _emit_started(self, operation_id: int) -> None:
        with self._playback_lock:
            if operation_id == self._playback_generation:
                self.operation_started.emit(operation_id)

    def _emit_viseme(
        self,
        operation_id: int,
        level: float,
        vowel: str,
    ) -> None:
        with self._playback_lock:
            if operation_id != self._playback_generation:
                return
            self.operation_viseme_cue.emit(operation_id, level, vowel)
            if operation_id == self._playback_generation:
                self.viseme_cue.emit(level, vowel)

    def _emit_finished(self, operation_id: int) -> None:
        with self._playback_lock:
            if operation_id != self._playback_generation:
                return
            self.operation_finished.emit(operation_id)
            if operation_id == self._playback_generation:
                self.finished.emit()

    def _emit_failed(self, operation_id: int, message: str) -> None:
        with self._playback_lock:
            if operation_id != self._playback_generation:
                return
            self.operation_failed.emit(operation_id, message)
            if operation_id == self._playback_generation:
                self.failed.emit(message)

    def _release_playback(self, operation_id: int) -> None:
        with self._playback_lock:
            if operation_id == self._playback_generation:
                self._active_reader = None
                self._active_synthesizer = None
