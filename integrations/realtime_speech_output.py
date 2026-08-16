from __future__ import annotations

lazy import re
lazy from collections import deque
lazy from dataclasses import dataclass, field

lazy from PySide6.QtCore import QObject, Signal

lazy from domain.contracts import AzureSpeechEnginePort, LocalSpeechEnginePort
lazy from domain.immutable_config import deep_freeze
lazy from domain.language_support import canonical_ui_language

REALTIME_OUTPUT_OPENAI = "openai-realtime"
REALTIME_OUTPUT_AZURE = "azure-speech"
REALTIME_OUTPUT_AZURE_HD = "azure-dragon-hd"
_REALTIME_OUTPUT_LOCAL = "system-local"
_MAX_RESPONSE_TEXT_CHARACTERS = 32_768
_MAX_PLAYBACK_SEGMENTS = 1_024
REALTIME_OUTPUT_MODES = frozenset({
    REALTIME_OUTPUT_OPENAI,
    REALTIME_OUTPUT_AZURE,
    REALTIME_OUTPUT_AZURE_HD,
})
_MESSAGES = deep_freeze({
    "zh-TW": {
        "preparing": "Realtime 已理解，Azure 正在準備發聲",
        "speaking": "Azure 串流發聲中",
        "missing": "所選 Realtime Azure 聲線尚未完成金鑰、區域與聲音設定。",
        "hd_fallback": "Dragon HD 無法發聲，本輪改用一般 Azure Speech",
        "local_fallback": "Azure 無法發聲，本輪改用 Windows 本機女性聲線",
        "local_speaking": "Windows 本機女性聲線發聲中",
        "failed": "Realtime 語音輸出失敗：{error}",
        "queue_full": "Realtime 回應過長，已安全停止本輪語音。",
        "ready": "已連線，妾在聽",
    },
    "zh-CN": {
        "preparing": "Realtime 已理解，Azure 正在准备发声",
        "speaking": "Azure 串流发声中",
        "missing": "所选 Realtime Azure 声线尚未完成密钥、区域与声音设置。",
        "hd_fallback": "Dragon HD 无法发声，本轮改用一般 Azure Speech",
        "local_fallback": "Azure 无法发声，本轮改用 Windows 本机女性声线",
        "local_speaking": "Windows 本机女性声线发声中",
        "failed": "Realtime 语音输出失败：{error}",
        "queue_full": "Realtime 回应过长，已安全停止本轮语音。",
        "ready": "已连接，妾在听",
    },
    "en-US": {
        "preparing": "Realtime understood; Azure is preparing speech",
        "speaking": "Azure streaming speech",
        "missing": "The selected Realtime Azure voice needs a key, region, and voice.",
        "hd_fallback": "Dragon HD failed; using standard Azure Speech for this response",
        "local_fallback": "Azure failed; using a local Windows female voice for this response",
        "local_speaking": "Local Windows female voice is speaking",
        "failed": "Realtime speech output failed: {error}",
        "queue_full": "The Realtime response was too long, so this speech response was stopped safely.",
        "ready": "Connected and listening",
    },
    "ja-JP": {
        "preparing": "Realtime が理解し、Azure が音声を準備しています",
        "speaking": "Azure ストリーミング音声を再生中",
        "missing": "選択した Realtime Azure 音声にはキー、リージョン、音声設定が必要です。",
        "hd_fallback": "Dragon HD が失敗したため、この返答は通常の Azure Speech を使用します",
        "local_fallback": "Azure が失敗したため、この返答は Windows 本機女性音声を使用します",
        "local_speaking": "Windows 本機女性音声を再生中",
        "failed": "Realtime 音声出力に失敗しました：{error}",
        "queue_full": "Realtime の応答が長すぎるため、この音声応答を安全に停止しました。",
        "ready": "接続済み、聞いています",
    },
})


def _message(locale: str, key: str, **values: object) -> str:
    normalized = canonical_ui_language(locale)
    catalog_key = "en-US" if normalized == "en" else normalized
    catalog = _MESSAGES[catalog_key]
    return catalog[key].format(**values)


@dataclass(frozen=True, slots=True)
class AzureRealtimeVoice:
    api_key: str = field(repr=False)
    region: str
    voice: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip() and self.region.strip() and self.voice.strip())


@dataclass(frozen=True, slots=True)
class LocalRealtimeVoice:
    available: bool = False
    voice: str = ""
    rate: int = -1


@dataclass(frozen=True, slots=True)
class RealtimeSpeechOutputConfig:
    mode: str = REALTIME_OUTPUT_OPENAI
    locale: str = "zh-TW"
    azure: AzureRealtimeVoice = AzureRealtimeVoice("", "", "")
    azure_hd: AzureRealtimeVoice = AzureRealtimeVoice("", "", "")
    local: LocalRealtimeVoice = LocalRealtimeVoice()


@dataclass(frozen=True, slots=True)
class RealtimeSpeechTiming:
    operation_id: int
    audio_offset_seconds: float
    duration_seconds: float
    kind: str
    estimated: bool
    cue_id: int | None = None


class RealtimeTextSegmenter:
    """Turn streamed model text into short, speakable, ordered clauses."""

    STRONG_ENDINGS = frozenset("。！？!?\n")
    SOFT_ENDINGS = frozenset("，,；;：:")
    SOFT_MINIMUM = 14
    MAXIMUM = 36
    CONTROL_MARKER = "[[MOHAN_"
    CONTROL_TAG = re.compile(
        r"\[\[\s*MOHAN_[^\]]*(?:\]\]|$)",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._pending = ""

    def reset(self) -> None:
        self._pending = ""

    def feed(self, delta: str) -> tuple[str, ...]:
        self._pending += str(delta or "")
        ready: list[str] = []
        while segment := self._next_segment():
            ready.append(segment)
        return tuple(ready)

    def finish(self) -> tuple[str, ...]:
        final = self.CONTROL_TAG.sub("", self._pending).strip()
        self._pending = ""
        return (final,) if final else ()

    def _next_segment(self) -> str:
        if not self._pending:
            return ""
        marker_at = self._pending.upper().find(self.CONTROL_MARKER)
        if marker_at == 0 or self._pending.startswith("[["):
            return ""
        speakable = self._pending[:marker_at] if marker_at > 0 else self._pending
        for index, character in enumerate(speakable):
            length = index + 1
            if character in self.STRONG_ENDINGS:
                return self._take(length)
            if character in self.SOFT_ENDINGS and length >= self.SOFT_MINIMUM:
                return self._take(length)
        if len(speakable) < self.MAXIMUM:
            return ""
        split_at = max(
            speakable.rfind(" ", 0, self.MAXIMUM),
            speakable.rfind("、", 0, self.MAXIMUM),
        )
        length = split_at + 1 if split_at >= self.SOFT_MINIMUM else self.MAXIMUM
        return self._take(length)

    def _take(self, length: int) -> str:
        segment = self._pending[:length].strip()
        self._pending = self._pending[length:].lstrip()
        return segment


class RealtimeSpeechOutput(QObject):
    """Own the optional Azure playback route without touching native audio."""

    speaking_changed = Signal(bool)
    playback_guard_changed = Signal(bool)
    viseme_cue = Signal(float, str)
    speech_timing = Signal(object)
    status_changed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        azure_speech: AzureSpeechEnginePort,
        azure_hd_speech: AzureSpeechEnginePort,
        local_speech: LocalSpeechEnginePort,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._azure_speech = azure_speech
        self._azure_hd_speech = azure_hd_speech
        self._local_speech = local_speech
        self._config = RealtimeSpeechOutputConfig()
        self._segmenter = RealtimeTextSegmenter()
        self._queue: deque[str] = deque(maxlen=_MAX_PLAYBACK_SEGMENTS)
        self._active_text = ""
        self._active_engine: object | None = None
        self._active_operation_id: int | None = None
        self._active_audio_started = False
        self._speech_timing_seen: set[tuple[object, ...]] = set()
        self._response_complete = False
        self._response_open = False
        self._response_rejected = False
        self._response_text_characters = 0
        self._response_generation = 0
        self._route_mode = REALTIME_OUTPUT_OPENAI
        self._speaking = False
        self._playback_guard = False
        for engine in (azure_speech, azure_hd_speech, local_speech):
            if self._connect_operation_signals(engine):
                continue
            self._connect_legacy_signals(engine)

    @property
    def active(self) -> bool:
        return self._config.mode != REALTIME_OUTPUT_OPENAI

    def configure(self, config: RealtimeSpeechOutputConfig) -> None:
        if config.mode not in REALTIME_OUTPUT_MODES:
            raise ValueError(f"Unsupported Realtime output mode: {config.mode}")
        previous = self._config
        self.cancel(self._response_generation)
        self._config = RealtimeSpeechOutputConfig(
            mode=config.mode,
            locale=canonical_ui_language(config.locale),
            azure=config.azure,
            azure_hd=config.azure_hd,
            local=config.local,
        )
        self._invalidate_changed_azure_catalogs(previous, self._config)

    def _invalidate_changed_azure_catalogs(
        self,
        previous: RealtimeSpeechOutputConfig,
        current: RealtimeSpeechOutputConfig,
    ) -> None:
        for engine, old_voice, new_voice in (
            (self._azure_speech, previous.azure, current.azure),
            (self._azure_hd_speech, previous.azure_hd, current.azure_hd),
        ):
            if old_voice == new_voice:
                continue
            invalidate = getattr(engine, "invalidate_voice_catalog", None)
            if invalidate is not None:
                invalidate()

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self._azure_speech.set_volume(volume_percent, muted)
        self._azure_hd_speech.set_volume(volume_percent, muted)
        self._local_speech.set_volume(volume_percent, muted)

    def _connect_operation_signals(self, engine: object) -> bool:
        operation_started = getattr(engine, "operation_started", None)
        operation_finished = getattr(engine, "operation_finished", None)
        operation_failed = getattr(engine, "operation_failed", None)
        operation_viseme = getattr(engine, "operation_viseme_cue", None)
        operation_latency = getattr(
            engine,
            "operation_synthesis_latency_measured",
            None,
        )
        operation_signals = (
            operation_started,
            operation_finished,
            operation_failed,
            operation_viseme,
            operation_latency,
        )
        if any(signal is None for signal in operation_signals):
            return False
        operation_started.connect(
            lambda operation_id, source=engine: self._operation_started(
                source,
                operation_id,
            )
        )
        operation_finished.connect(
            lambda operation_id, source=engine: self._engine_finished(
                source,
                operation_id,
            )
        )
        operation_failed.connect(
            lambda operation_id, message, source=engine: self._engine_failed(
                source,
                message,
                operation_id,
            )
        )
        operation_viseme.connect(
            lambda operation_id, level, vowel, source=engine: self._viseme_cue(
                source,
                level,
                vowel,
                operation_id,
            )
        )
        operation_latency.connect(
            lambda operation_id, _latency, source=engine: self._audio_started(
                source,
                operation_id,
            )
        )
        self._connect_speech_timing(engine)
        return True

    def _connect_speech_timing(self, engine: object) -> None:
        timing_signal = getattr(engine, "operation_speech_timing", None)
        if timing_signal is None:
            timing_signal = getattr(engine, "operation_timing_event", None)
        connect = getattr(timing_signal, "connect", None)
        if callable(connect):
            connect(
                lambda event, source=engine: self._speech_timing_event(
                    source,
                    event,
                )
            )

    def _connect_legacy_signals(self, engine: object) -> None:
        engine.finished.connect(lambda source=engine: self._engine_finished(source))
        engine.failed.connect(
            lambda message, source=engine: self._engine_failed(
                source,
                message,
            )
        )
        engine.viseme_cue.connect(
            lambda level, vowel, source=engine: self._viseme_cue(
                source,
                level,
                vowel,
            )
        )
        latency_signal = getattr(engine, "synthesis_latency_measured", None)
        if latency_signal is not None:
            latency_signal.connect(
                lambda _latency, source=engine: self._audio_started(source)
            )

    def begin_response(self, generation: int) -> None:
        if not self.active:
            return
        generation = int(generation)
        if generation <= self._response_generation:
            return
        self.cancel(generation)
        self._response_complete = False
        self._response_open = True
        self._response_rejected = False
        self._response_text_characters = 0
        self._route_mode = self._config.mode
        self.status_changed.emit(self._text("preparing"))

    def add_text(self, generation: int, delta: str) -> None:
        if not self.active:
            return
        if (
            int(generation) != self._response_generation
            or self._response_rejected
            or not self._response_open
        ):
            return
        text = str(delta or "")
        if self._response_text_characters + len(text) > _MAX_RESPONSE_TEXT_CHARACTERS:
            self._fail_queue_limit()
            return
        self._response_text_characters += len(text)
        try:
            self._queue_segments(self._segmenter.feed(text))
        except OverflowError:
            self._fail_queue_limit()
            return
        self._speak_next()

    def finish_response(self, generation: int) -> None:
        if not self.active:
            return
        if (
            int(generation) != self._response_generation
            or self._response_rejected
            or not self._response_open
        ):
            return
        try:
            self._queue_segments(self._segmenter.finish())
        except OverflowError:
            self._fail_queue_limit()
            return
        self._response_complete = True
        self._response_open = False
        self._speak_next()
        self._finish_if_idle()

    def cancel(self, generation: int) -> None:
        generation = int(generation)
        if generation < self._response_generation:
            return
        self._response_generation = generation
        self._segmenter.reset()
        self._queue.clear()
        self._active_text = ""
        self._response_complete = False
        self._response_open = False
        self._response_rejected = True
        self._response_text_characters = 0
        self._route_mode = self._config.mode
        active_engine = self._active_engine
        self._active_engine = None
        self._active_operation_id = None
        self._active_audio_started = False
        self._speech_timing_seen.clear()
        if active_engine is not None:
            stop = getattr(active_engine, "stop", None)
            if stop is not None:
                stop()
        self._set_speaking(False)
        self._set_playback_guard(False)

    def _selected_route(self) -> tuple[object, object]:
        if self._route_mode == REALTIME_OUTPUT_AZURE_HD:
            return self._azure_hd_speech, self._config.azure_hd
        if self._route_mode == _REALTIME_OUTPUT_LOCAL:
            return self._local_speech, self._config.local
        return self._azure_speech, self._config.azure

    def _speak_next(self) -> None:
        if self._active_engine is not None or not self._queue:
            return
        engine, voice = self._selected_route()
        if isinstance(voice, AzureRealtimeVoice) and not voice.configured:
            self._fallback_or_fail(self._text("missing"))
            return
        if isinstance(voice, LocalRealtimeVoice) and not voice.available:
            self._fallback_or_fail(self._text("missing"))
            return
        self._active_text = self._queue.popleft()
        self._active_engine = engine
        self._active_operation_id = None
        self._active_audio_started = False
        self._speech_timing_seen.clear()
        self._set_playback_guard(True)
        if isinstance(voice, AzureRealtimeVoice):
            engine.speak(
                self._active_text,
                voice.api_key,
                voice.region,
                voice.voice,
                self._config.locale,
            )
        else:
            engine.speak(self._active_text, voice.voice, voice.rate)

    def _audio_started(
        self,
        source: object,
        operation_id: int | None = None,
    ) -> None:
        if not self._is_active_operation(source, operation_id):
            return
        self._active_audio_started = True
        self._set_speaking(True)
        status_key = "local_speaking" if source is self._local_speech else "speaking"
        self.status_changed.emit(self._text(status_key))

    def _operation_started(
        self,
        source: object,
        operation_id: int,
    ) -> None:
        if source is self._active_engine and self._active_operation_id is None:
            self._active_operation_id = operation_id

    def _viseme_cue(
        self,
        source: object,
        level: float,
        vowel: str,
        operation_id: int | None = None,
    ) -> None:
        if not self._is_active_operation(source, operation_id):
            return
        if not self._speaking:
            self._audio_started(source, operation_id)
        self.viseme_cue.emit(level, vowel)

    def _speech_timing_event(self, source: object, event: object) -> None:
        operation_id = getattr(event, "operation_id", None)
        if not isinstance(operation_id, int) or isinstance(operation_id, bool):
            return
        if not self._is_active_operation(source, operation_id):
            return
        offset = getattr(event, "audio_offset_seconds", None)
        duration = getattr(event, "duration_seconds", None)
        kind = getattr(event, "kind", None)
        estimated = getattr(event, "estimated", None)
        cue_id = getattr(event, "cue_id", None)
        if (
            not isinstance(offset, float | int)
            or isinstance(offset, bool)
            or not isinstance(duration, float | int)
            or isinstance(duration, bool)
            or offset < 0
            or duration < 0
            or kind is None
            or not isinstance(estimated, bool)
        ):
            return
        sanitized = RealtimeSpeechTiming(
            operation_id,
            float(offset),
            float(duration),
            str(kind),
            estimated,
            cue_id if isinstance(cue_id, int) and not isinstance(cue_id, bool) else None,
        )
        identity = (
            sanitized.operation_id,
            sanitized.audio_offset_seconds,
            sanitized.duration_seconds,
            sanitized.kind,
            sanitized.cue_id,
        )
        if identity in self._speech_timing_seen:
            return
        self._speech_timing_seen.add(identity)
        self.speech_timing.emit(sanitized)

    def _engine_finished(
        self,
        source: object,
        operation_id: int | None = None,
    ) -> None:
        if not self._is_active_operation(source, operation_id):
            return
        self._active_engine = None
        self._active_operation_id = None
        self._active_audio_started = False
        self._speech_timing_seen.clear()
        self._active_text = ""
        self._speak_next()
        self._finish_if_idle()

    def _engine_failed(
        self,
        source: object,
        message: str,
        operation_id: int | None = None,
    ) -> None:
        if not self._is_active_operation(source, operation_id):
            return
        failed_text = self._active_text
        audio_started = self._active_audio_started
        self._active_engine = None
        self._active_operation_id = None
        self._active_audio_started = False
        self._speech_timing_seen.clear()
        self._active_text = ""
        if failed_text and not audio_started:
            self._queue.appendleft(failed_text)
        elif audio_started:
            self._queue.clear()
            self._segmenter.reset()
            self._response_open = False
            self._response_rejected = True
            stop = getattr(source, "stop", None)
            if stop is not None:
                stop()
            self._set_speaking(False)
            self._set_playback_guard(False)
            self.failed.emit(self._text("failed", error=message))
            return
        self._fallback_or_fail(message)

    def _fallback_or_fail(self, message: str) -> None:
        if (
            self._route_mode == REALTIME_OUTPUT_AZURE_HD
            and self._config.azure.configured
        ):
            self._route_mode = REALTIME_OUTPUT_AZURE
            self.status_changed.emit(self._text("hd_fallback"))
            self._speak_next()
            return
        if self._route_mode != _REALTIME_OUTPUT_LOCAL and self._config.local.available:
            self._route_mode = _REALTIME_OUTPUT_LOCAL
            self.status_changed.emit(self._text("local_fallback"))
            self._speak_next()
            return
        self._queue.clear()
        self._segmenter.reset()
        self._response_open = False
        self._response_rejected = True
        self._set_speaking(False)
        self._set_playback_guard(False)
        self.failed.emit(self._text("failed", error=message))

    def _queue_segments(self, segments: tuple[str, ...]) -> None:
        if len(self._queue) + len(segments) > _MAX_PLAYBACK_SEGMENTS:
            raise OverflowError("Realtime playback queue limit exceeded")
        self._queue.extend(segments)

    def _fail_queue_limit(self) -> None:
        self.cancel(self._response_generation)
        self.failed.emit(self._text("queue_full"))

    def _is_active_operation(
        self,
        source: object,
        operation_id: int | None,
    ) -> bool:
        if source is not self._active_engine:
            return False
        if operation_id is None:
            return self._active_operation_id is None
        return operation_id == self._active_operation_id

    def _finish_if_idle(self) -> None:
        if self._response_complete and self._active_engine is None and not self._queue:
            self._set_speaking(False)
            self._set_playback_guard(False)
            self.status_changed.emit(self._text("ready"))

    def _set_speaking(self, speaking: bool) -> None:
        if self._speaking == speaking:
            return
        self._speaking = speaking
        self.speaking_changed.emit(speaking)

    def _set_playback_guard(self, active: bool) -> None:
        if self._playback_guard == active:
            return
        self._playback_guard = active
        self.playback_guard_changed.emit(active)

    def _text(self, key: str, **values: object) -> str:
        return _message(self._config.locale, key, **values)
