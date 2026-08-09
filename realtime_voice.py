from __future__ import annotations

lazy import base64
lazy import hashlib
lazy import io
lazy import json
lazy import queue
lazy import re
lazy import sys
lazy import threading
lazy import time
lazy import uuid
lazy import wave
lazy from collections import deque
lazy from contextlib import suppress
lazy from dataclasses import dataclass, replace
lazy from difflib import SequenceMatcher
lazy from typing import Any

lazy import sounddevice as sd
lazy import websocket
lazy from PySide6.QtCore import QObject, Signal

lazy from audio_buffer import BoundedAudioQueue, PcmPacketizer
lazy from lip_sync import (
    VISEME_CUES_PER_SECOND,
    infer_vowel_pcm16,
)
lazy from pcm_audio import rate_convert_pcm16, scale_pcm16
lazy from speech import transcribe_wav_bytes


@dataclass(frozen=True, slots=True)
class RealtimeSessionConfig:
    model: str = "gpt-realtime-2.1-mini"
    voice: str = "coral"
    transcription_model: str = "gpt-4o-mini-transcribe"
    transcription_language: str = "zh"
    transcription_prompt: str = ""
    noise_reduction: str = "near_field"
    turn_detection: str = "server_vad"
    external_transcription: bool = True


@dataclass(frozen=True, slots=True)
class RealtimeVoiceRequest:
    api_key: str
    instructions: str
    memory_context: str
    session: RealtimeSessionConfig
    recent_context: str = ""
    echo_guard: bool = True


AUDIO_DELTA_EVENTS = frozenset(
    {
        "response.output_audio.delta",
        "response.audio.delta",
    }
)
AUDIO_DONE_EVENTS = frozenset(
    {
        "response.output_audio.done",
        "response.audio.done",
        "response.done",
        "response.cancelled",
        "response.failed",
    }
)
AUDIO_CANCELLED_EVENTS = frozenset(
    {"response.cancelled", "response.failed"}
)
ASSISTANT_TRANSCRIPT_DELTA_EVENTS = frozenset(
    {
        "response.output_audio_transcript.delta",
        "response.audio_transcript.delta",
    }
)
ASSISTANT_TRANSCRIPT_DONE_EVENTS = frozenset(
    {
        "response.output_audio_transcript.done",
        "response.audio_transcript.done",
    }
)
USER_TRANSCRIPT_COMPLETED_EVENT = (
    "conversation.item.input_audio_transcription.completed"
)
USER_TRANSCRIPT_FAILED_EVENT = (
    "conversation.item.input_audio_transcription.failed"
)


class RealtimeVoiceClient(QObject):
    DEVICE_BLOCK_MILLISECONDS = 20
    INPUT_QUEUE_CHUNKS = 32
    PLAYBACK_QUEUE_CHUNKS = 75
    PLAYBACK_CHUNK_BYTES = 24000 * 2 * DEVICE_BLOCK_MILLISECONDS // 1000

    status_changed = Signal(str)
    user_transcript = Signal(str)
    assistant_transcript = Signal(str)
    speaking_changed = Signal(bool)
    viseme_cue = Signal(float, str)
    failed = Signal(str)
    _hybrid_result = Signal(str, str, str, int)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.ws = None
        self.running = False
        self._input_stream = None
        self._output_stream = None
        self._audio_queue: BoundedAudioQueue[bytes | None] = (
            BoundedAudioQueue(self.PLAYBACK_QUEUE_CHUNKS)
        )
        self._input_queue: BoundedAudioQueue[bytes | None] = (
            BoundedAudioQueue(self.INPUT_QUEUE_CHUNKS)
        )
        self._playback_packetizer = PcmPacketizer(
            self.PLAYBACK_CHUNK_BYTES
        )
        self._playback_overflowed = False
        self._audio_lock = threading.Lock()
        self._failure_lock = threading.Lock()
        self._failure_emitted = False
        self._active_model = ""
        self.echo_guard = True
        self._assistant_audio_active = threading.Event()
        self._playback_busy = threading.Event()
        self._assistant_state_lock = threading.Lock()
        self._assistant_audio_generation = 0
        self._last_assistant_audio_at = 0.0
        self._server_audio_done = False
        self._input_resume_at = 0.0
        self._assistant_text = ""
        self._final_transcript_item_ids: set[str] = set()
        self._final_transcript_item_order: deque[str] = deque()
        self._transcription_prompt_source = ""
        self._transcription_prompt_sent = ""
        self.hybrid_transcription = True
        self._hybrid_api_key = ""
        self._hybrid_model = "gpt-4o-mini-transcribe"
        self._hybrid_language = "zh"
        self._hybrid_prompt = ""
        self._session_generation = 0
        self._input_timeline_lock = threading.Lock()
        self._input_audio_offset_ms = 0.0
        self._input_audio_timeline: deque[
            tuple[float, float, bytes]
        ] = deque()
        self._speech_start_ms: dict[str, float] = {}
        self._hybrid_transcription_active = threading.Event()
        self._response_pending = threading.Event()
        self.volume_percent = 125
        self.muted = False
        self._hybrid_result.connect(
            self._finish_hybrid_transcription
        )

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_percent = max(0, min(160, int(volume_percent)))
        self.muted = bool(muted)

    @staticmethod
    def dependencies_available() -> bool:
        try:
            _ = sd.RawInputStream
            _ = sd.RawOutputStream
            _ = websocket.WebSocketApp
        except (AttributeError, ImportError):
            return False
        return True

    @staticmethod
    def _normalized_request(
        request: RealtimeVoiceRequest,
    ) -> RealtimeVoiceRequest:
        session = request.session
        normalized_session = replace(
            session,
            transcription_model=(
                session.transcription_model.strip()
                or "gpt-4o-mini-transcribe"
            ),
            transcription_language=session.transcription_language.strip(),
            transcription_prompt=(
                RealtimeVoiceClient
                ._sanitize_realtime_transcription_prompt(
                    session.transcription_prompt
                )
            ),
            external_transcription=bool(
                session.external_transcription
            ),
        )
        return replace(
            request,
            api_key=request.api_key.strip(),
            session=normalized_session,
            echo_guard=bool(request.echo_guard),
        )

    def _reset_session_state(
        self,
        request: RealtimeVoiceRequest,
    ) -> None:
        session = request.session
        with self._failure_lock:
            self._failure_emitted = False
        self._playback_overflowed = False
        self._playback_packetizer.reset()
        self._active_model = session.model
        self.echo_guard = request.echo_guard
        self.hybrid_transcription = session.external_transcription
        self._hybrid_api_key = request.api_key
        self._hybrid_model = session.transcription_model
        self._hybrid_language = session.transcription_language
        self._hybrid_prompt = session.transcription_prompt
        self._session_generation += 1
        self._assistant_audio_active.clear()
        self._hybrid_transcription_active.clear()
        self._response_pending.clear()
        with self._assistant_state_lock:
            self._assistant_audio_generation += 1
            self._last_assistant_audio_at = 0.0
        self._server_audio_done = False
        self._input_resume_at = 0.0
        self._final_transcript_item_ids.clear()
        self._final_transcript_item_order.clear()
        with self._input_timeline_lock:
            self._input_audio_offset_ms = 0.0
            self._input_audio_timeline.clear()
            self._speech_start_ms.clear()

    def start(self, request: RealtimeVoiceRequest) -> None:
        if self.running:
            return
        if not request.api_key.strip():
            self.failed.emit("請先儲存 OpenAI API 金鑰")
            return
        if not self.dependencies_available():
            self.failed.emit("Realtime 語音元件尚未安裝")
            return
        self._transcription_prompt_source = (
            request.session.transcription_prompt.strip()
        )
        normalized_request = self._normalized_request(request)
        self._transcription_prompt_sent = (
            normalized_request.session.transcription_prompt
        )
        self._reset_session_state(normalized_request)
        self.running = True
        self.status_changed.emit("正在連線…")
        threading.Thread(
            target=self._connect,
            args=(normalized_request,),
            daemon=True,
        ).start()

    def stop(self) -> None:
        self.running = False
        self._session_generation += 1
        self._hybrid_transcription_active.clear()
        self._response_pending.clear()
        self._finish_assistant_audio(force=True)
        ws = self.ws
        self.ws = None
        if ws:
            # A closing WebSocket may reject a second close during shutdown.
            with suppress(Exception):
                ws.close()
        self._close_audio()
        self.status_changed.emit("未連線")

    def _connect(self, request: RealtimeVoiceRequest) -> None:
        safety_id = hashlib.sha256(
            f"mohan-{uuid.getnode()}".encode()
        ).hexdigest()
        url = (
            "wss://api.openai.com/v1/realtime?model="
            + request.session.model
        )

        def on_open(ws):
            self.ws = ws
            full_instructions = self._compose_instructions(
                request.instructions,
                request.memory_context,
                request.recent_context,
            )
            ws.send(
                json.dumps(
                    self._session_update_event(
                        request.session,
                        full_instructions,
                    ),
                    ensure_ascii=False,
                )
            )
            try:
                self._open_audio()
                self.status_changed.emit("已連線，妾在聽")
            except Exception as exc:  # noqa: BLE001 -- audio startup reports all failures
                self._emit_failure(self._audio_error_message(exc))
                self.stop()

        def on_message(_ws, message):
            try:
                event = json.loads(message)
            except (TypeError, json.JSONDecodeError):
                return
            self._handle_server_event(event)

        def on_error(_ws, error):
            if self.running:
                self._emit_failure(str(error))

        def on_close(_ws, _code, _message):
            self.running = False
            self._close_audio()
            self._finish_assistant_audio(force=True)
            self.status_changed.emit("未連線")

        self.ws = websocket.WebSocketApp(
            url,
            header=[
                f"Authorization: Bearer {request.api_key}",
                f"OpenAI-Safety-Identifier: {safety_id}",
            ],
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        self.ws.run_forever(ping_interval=20, ping_timeout=10)

    @staticmethod
    def _sanitize_realtime_transcription_prompt(prompt: str) -> str:
        """Keep ASR hints short so instructions cannot become a transcript."""
        raw = (prompt or "").strip()
        if not raw:
            return ""
        term_source = raw
        marker = re.search(
            r"(?:常用詞|常用词|專有名詞|专有名词|Common terms|"
            r"よく使う語句)\s*[：:]",
            raw,
            flags=re.IGNORECASE,
        )
        if marker:
            term_source = raw[marker.end():]
        term_source = re.split(
            r"(?:請保留|請使用|不要改寫|不要翻譯|请保留|请使用|"
            r"不要改写|不要翻译|Please|Preserve|Keep the speaker|"
            r"do not|日本語で|固有名詞|話者の意図|書き換え)",
            term_source,
            maxsplit=1,
        )[0]
        terms = []
        for value in re.split(r"[、,，。；;\n]+", term_source):
            value = value.strip(" 「」『』：:")
            if (
                value
                and len(value) <= 40
                and not re.match(
                    r"^(?:請|使用|保留|不要|轉錄|語言|请|准确|"
                    r"Please|Preserve|Keep|do not|日本語|固有名詞)",
                    value,
                    flags=re.IGNORECASE,
                )
                and value not in terms
            ):
                terms.append(value)
            if len(terms) >= 16:
                break
        if not terms:
            return ""
        return "可能出現的專有名詞：" + "、".join(terms) + "。"

    @staticmethod
    def _comparison_text(text: str) -> str:
        return re.sub(r"[\W_]+", "", (text or "").casefold())

    @classmethod
    def resembles_transcription_prompt(
        cls,
        text: str,
        *prompts: str,
    ) -> bool:
        candidate = cls._comparison_text(text)
        if len(candidate) < 16:
            return False
        for prompt in prompts:
            reference = cls._comparison_text(prompt)
            if len(reference) < 16:
                continue
            if candidate == reference:
                return True
            shorter, longer = sorted(
                (candidate, reference),
                key=len,
            )
            if len(shorter) >= 20 and shorter in longer:
                return True
            if SequenceMatcher(
                None,
                candidate,
                reference,
            ).ratio() >= 0.82:
                return True
        return False

    @staticmethod
    def _compose_instructions(
        instructions: str,
        memory_context: str,
        recent_context: str,
    ) -> str:
        return (
            instructions
            + "\n以下是主上允許妾長期保留的本機記憶，自然運用，不逐條複誦：\n"
            + (memory_context or "（尚無長期記憶）")
            + "\n以下是最近的對話，只用來承接語境，不要逐字複誦：\n"
            + (recent_context or "（目前沒有可承接的最近對話）")
            + "\n\n## 即時對話承接規則\n"
            "必須先理解並承接最近一輪話題，不可突然切換成客服、行政或工作需求訪談。"
            "當主上說「好呀你說」、「你說吧」、「嗯，你說」或「繼續說」時，"
            "直接延續妾上一句尚未說完的內容。若確實沒有前文可承接，"
            "便自然開啟一個符合兩人關係的陪伴話題。除非主上明確要求規劃工作，"
            "不得回答「請告訴妾需求、安排或優先順序」之類的制式套話。"
            "\n電腦操作必須遵守程式的本機權限設定；未獲授權時先請主上確認。"
        )

    @staticmethod
    def _session_update_event(
        config: RealtimeSessionConfig,
        instructions: str,
    ) -> dict[str, Any]:
        transcription = {
            "model": (
                config.transcription_model
                or "gpt-4o-mini-transcribe"
            ),
        }
        if config.transcription_language:
            transcription["language"] = config.transcription_language
        if config.transcription_prompt:
            transcription["prompt"] = config.transcription_prompt

        if config.turn_detection == "semantic_vad":
            turn_config = {
                "type": "semantic_vad",
                "eagerness": "medium",
                # A response is requested only after a usable final
                # transcription is received. This prevents noise-only VAD
                # turns from making the assistant talk to herself.
                "create_response": False,
                "interrupt_response": True,
            }
        else:
            turn_config = {
                "type": "server_vad",
                "threshold": 0.45,
                "prefix_padding_ms": 500,
                "silence_duration_ms": 850,
                "create_response": False,
                "interrupt_response": True,
            }

        input_audio = {
            "format": {"type": "audio/pcm", "rate": 24000},
            "turn_detection": turn_config,
            "transcription": (
                None
                if config.external_transcription
                else transcription
            ),
        }
        if config.noise_reduction in {"near_field", "far_field"}:
            input_audio["noise_reduction"] = {
                "type": config.noise_reduction,
            }

        event = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "model": config.model,
                "output_modalities": ["audio"],
                "instructions": instructions,
                "reasoning": {"effort": "low"},
                "audio": {
                    "input": input_audio,
                    "output": {
                        "format": {
                            "type": "audio/pcm",
                            "rate": 24000,
                        },
                        "voice": config.voice,
                    },
                },
            },
        }
        if not config.external_transcription:
            event["session"]["include"] = [
                "item.input_audio_transcription.logprobs"
            ]
        return event

    def _handle_audio_delta(self, event: dict[str, Any]) -> None:
        delta = event.get("delta", "")
        if not delta or self._playback_overflowed:
            return
        self._begin_assistant_audio()
        chunks = self._playback_packetizer.feed(
            base64.b64decode(delta)
        )
        for chunk in chunks:
            if not self._queue_playback_chunk(chunk):
                break

    def _handle_audio_done(self, kind: str) -> None:
        if kind in AUDIO_CANCELLED_EVENTS:
            self._playback_packetizer.reset()
        else:
            remainder = self._playback_packetizer.flush()
            if remainder and not self._playback_overflowed:
                self._queue_playback_chunk(remainder)
        self._playback_overflowed = False
        self._response_pending.clear()
        self._mark_assistant_audio_done()

    def _handle_assistant_transcript_delta(
        self,
        event: dict[str, Any],
    ) -> None:
        self._assistant_text += str(event.get("delta", ""))

    def _handle_assistant_transcript_done(
        self,
        event: dict[str, Any],
    ) -> None:
        text = str(
            event.get("transcript") or self._assistant_text
        ).strip()
        self._assistant_text = ""
        if text:
            self.assistant_transcript.emit(text)

    def _handle_user_transcript_completed(
        self,
        event: dict[str, Any],
    ) -> None:
        if self.hybrid_transcription:
            return
        text = str(event.get("transcript", "")).strip()
        item_id = str(event.get("item_id") or "")
        already_seen = (
            bool(item_id)
            and item_id in self._final_transcript_item_ids
        )
        # Only the documented completed event is committed to the chat.
        # Delta and legacy done events stay provisional and never reach chat.
        if self._emit_completed_user_transcript(text, item_id):
            self._request_response()
            return
        if not already_seen:
            self._discard_conversation_item(item_id)
            if not text:
                self.status_changed.emit(
                    "未取得有效轉錄，本輪不會自動回覆"
                )

    def _handle_user_transcript_failed(
        self,
        event: dict[str, Any],
    ) -> None:
        if self.hybrid_transcription:
            return
        error = event.get("error") or {}
        detail = str(
            error.get("message")
            or error.get("code")
            or "無法辨識這段語音"
        )
        self.status_changed.emit(
            f"轉錄失敗，本輪不會自動回覆：{detail}"
        )
        self._discard_conversation_item(
            str(event.get("item_id") or "")
        )

    def _handle_speech_started(
        self,
        event: dict[str, Any],
    ) -> None:
        # Only apply the playback tail to a real interruption. Doing so for
        # normal speech would erase the first 0.9 seconds of the next turn.
        if (
            self._assistant_audio_active.is_set()
            or self._playback_busy.is_set()
            or self._response_pending.is_set()
        ):
            self._finish_assistant_audio(force=True)
        if not self.hybrid_transcription:
            return
        item_id = str(event.get("item_id") or "")
        start_ms = float(
            event.get(
                "audio_start_ms",
                self._current_input_offset_ms() - 500.0,
            )
        )
        if item_id:
            with self._input_timeline_lock:
                self._speech_start_ms[item_id] = max(0.0, start_ms)

    def _handle_speech_stopped(
        self,
        event: dict[str, Any],
    ) -> None:
        if self.hybrid_transcription:
            self._start_hybrid_transcription(event)

    def _handle_realtime_error(
        self,
        event: dict[str, Any],
    ) -> None:
        self._finish_assistant_audio(force=True)
        error = event.get("error") or {}
        self._emit_failure(
            str(error.get("message", "Realtime API 發生錯誤"))
        )

    def _handle_server_event(self, event: dict[str, Any]) -> None:
        kind = str(event.get("type", ""))
        if kind in AUDIO_DELTA_EVENTS:
            self._handle_audio_delta(event)
        elif kind in AUDIO_DONE_EVENTS:
            self._handle_audio_done(kind)
        elif kind in ASSISTANT_TRANSCRIPT_DELTA_EVENTS:
            self._handle_assistant_transcript_delta(event)
        elif kind in ASSISTANT_TRANSCRIPT_DONE_EVENTS:
            self._handle_assistant_transcript_done(event)
        elif kind == USER_TRANSCRIPT_COMPLETED_EVENT:
            self._handle_user_transcript_completed(event)
        elif kind == USER_TRANSCRIPT_FAILED_EVENT:
            self._handle_user_transcript_failed(event)
        elif kind == "input_audio_buffer.speech_started":
            self._handle_speech_started(event)
        elif kind == "input_audio_buffer.speech_stopped":
            self._handle_speech_stopped(event)
        elif kind == "error":
            self._handle_realtime_error(event)

    def _open_audio(self) -> None:
        audio_queue: BoundedAudioQueue[bytes | None] = BoundedAudioQueue(
            self.PLAYBACK_QUEUE_CHUNKS
        )
        input_queue: BoundedAudioQueue[bytes | None] = BoundedAudioQueue(
            self.INPUT_QUEUE_CHUNKS
        )
        input_device = self._preferred_device(sd, "input")
        output_device = self._preferred_device(sd, "output")
        input_rate = int(
            sd.query_devices(input_device, "input")["default_samplerate"]
        )
        output_rate = int(
            sd.query_devices(output_device, "output")["default_samplerate"]
        )
        output_stream = None
        input_stream = None

        def input_callback(indata, _frames, _time, status):
            if status:
                self.status_changed.emit(f"麥克風狀態：{status}")
            if self.running and not self._microphone_blocked():
                input_queue.offer(bytes(indata), keep_latest=True)

        try:
            output_stream = sd.RawOutputStream(
                device=output_device,
                samplerate=output_rate,
                channels=1,
                dtype="int16",
                blocksize=max(
                    1,
                    output_rate * self.DEVICE_BLOCK_MILLISECONDS // 1000,
                ),
                latency="low",
            )
            input_stream = sd.RawInputStream(
                device=input_device,
                samplerate=input_rate,
                channels=1,
                dtype="int16",
                blocksize=max(
                    1,
                    input_rate * self.DEVICE_BLOCK_MILLISECONDS // 1000,
                ),
                latency="low",
                callback=input_callback,
            )
            with self._audio_lock:
                if not self.running:
                    raise RuntimeError("Realtime 連線已停止")
                self._audio_queue = audio_queue
                self._input_queue = input_queue
                self._output_stream = output_stream
                self._input_stream = input_stream
                output_stream.start()
                input_stream.start()
            threading.Thread(
                target=self._playback_loop,
                args=(audio_queue, output_stream, output_rate),
                daemon=True,
            ).start()
            threading.Thread(
                target=self._input_sender_loop,
                args=(input_queue, input_rate),
                daemon=True,
            ).start()
        except Exception:
            with self._audio_lock:
                if input_stream and self._input_stream is input_stream:
                    self._input_stream = None
                if output_stream and self._output_stream is output_stream:
                    self._output_stream = None
            for stream in (input_stream, output_stream):
                if stream:
                    # Preserve the original audio error; cleanup is best effort.
                    with suppress(Exception):
                        stream.abort()
                        stream.close()
            raise

    def _input_sender_loop(
        self,
        input_queue: queue.Queue[bytes | None],
        input_rate: int,
    ) -> None:
        rate_state = None
        reported_drops = 0
        while self.running:
            audio = input_queue.get()
            if audio is None:
                break
            if self._microphone_blocked():
                continue
            if input_rate != 24000:
                audio, rate_state = rate_convert_pcm16(
                    audio, 1, input_rate, 24000, rate_state
                )
            ws = self.ws
            if not ws or not ws.sock or not ws.sock.connected:
                continue
            # Close the race where assistant playback can begin after this
            # packet left the callback queue but before it reaches WebSocket.
            if self._microphone_blocked():
                continue
            packet = base64.b64encode(audio).decode("ascii")
            try:
                ws.send(
                    json.dumps(
                        {"type": "input_audio_buffer.append", "audio": packet}
                    )
                )
                self._remember_sent_audio(audio)
                if isinstance(input_queue, BoundedAudioQueue):
                    dropped = input_queue.snapshot().dropped_oldest
                    if dropped > reported_drops:
                        reported_drops = dropped
                        self.status_changed.emit(
                            "麥克風處理一度落後，已捨棄最舊音訊以恢復即時性"
                        )
            except Exception:  # noqa: BLE001 -- connection loss ends sender loop
                break

    def _queue_playback_chunk(self, chunk: bytes) -> bool:
        if self._audio_queue.offer(chunk, keep_latest=False):
            return True
        self._playback_overflowed = True
        self._playback_packetizer.reset()
        while True:
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        ws = self.ws
        if ws and ws.sock and ws.sock.connected:
            # The peer may close between the connected check and this send.
            with suppress(Exception):
                ws.send(json.dumps({"type": "response.cancel"}))
        self._finish_assistant_audio(force=True)
        self._emit_failure(
            "Realtime 播放緩衝已達 1.5 秒安全上限，已停止本輪語音，"
            "避免延遲持續累積或跳字。"
        )
        return False

    def _playback_loop(
        self,
        audio_queue: queue.Queue[bytes | None],
        output_stream,
        output_rate: int,
    ) -> None:
        rate_state = None
        source_bytes_per_frame = 2
        animation_chunk_bytes = (
            24000 // VISEME_CUES_PER_SECOND
        ) * source_bytes_per_frame
        while self.running:
            audio = audio_queue.get()
            if audio is None:
                break
            self._playback_busy.set()
            try:
                for offset in range(0, len(audio), animation_chunk_bytes):
                    source_chunk = audio[offset : offset + animation_chunk_bytes]
                    if not source_chunk:
                        continue
                    vowel_level, vowel = infer_vowel_pcm16(
                        source_chunk,
                        24000,
                    )
                    self.viseme_cue.emit(vowel_level, vowel)
                    playback_chunk = source_chunk
                    if output_rate != 24000:
                        playback_chunk, rate_state = rate_convert_pcm16(
                            source_chunk,
                            1,
                            24000,
                            output_rate,
                            rate_state,
                        )
                    gain = (
                        0.0
                        if self.muted
                        else self.volume_percent / 100.0
                    )
                    if gain != 1.0:
                        playback_chunk = scale_pcm16(playback_chunk, gain)
                    output_stream.write(playback_chunk)
            except Exception as exc:  # noqa: BLE001 -- playback reports all failures
                self._finish_assistant_audio(force=True)
                self._emit_failure(f"播放語音失敗：{exc}")
                break
            finally:
                self._playback_busy.clear()
            if self._server_audio_done and audio_queue.empty():
                self._finish_assistant_audio()

    def _close_audio(self) -> None:
        with self._audio_lock:
            input_stream = self._input_stream
            output_stream = self._output_stream
            audio_queue = self._audio_queue
            input_queue = self._input_queue
            self._input_stream = None
            self._output_stream = None
            self._audio_queue = BoundedAudioQueue(
                self.PLAYBACK_QUEUE_CHUNKS
            )
            self._input_queue = BoundedAudioQueue(
                self.INPUT_QUEUE_CHUNKS
            )
            self._playback_packetizer.reset()
        for pending_queue in (audio_queue, input_queue):
            if isinstance(pending_queue, BoundedAudioQueue):
                pending_queue.force_stop(None)
            else:
                try:
                    pending_queue.put_nowait(None)
                except queue.Full:
                    try:
                        pending_queue.get_nowait()
                        pending_queue.put_nowait(None)
                    except queue.Empty:
                        pass
        for stream in (input_stream, output_stream):
            if stream:
                # Streams can already be invalidated by their device callback.
                with suppress(Exception):
                    stream.abort()
                    stream.close()

    @staticmethod
    def _preferred_device(sd, kind: str):
        default_device = sd.default.device
        fallback = default_device[0 if kind == "input" else 1]
        if not sys.platform.startswith("win"):
            return fallback
        key = f"default_{kind}_device"
        # Device enumeration is advisory; the platform default is a valid fallback.
        with suppress(Exception):
            for hostapi in sd.query_hostapis():
                if "WASAPI" in hostapi["name"]:
                    candidate = int(hostapi[key])
                    if candidate >= 0:
                        return candidate
        return fallback

    def _remember_sent_audio(self, audio: bytes) -> None:
        duration_ms = len(audio) / 2 / 24000 * 1000.0
        if duration_ms <= 0:
            return
        with self._input_timeline_lock:
            start_ms = self._input_audio_offset_ms
            end_ms = start_ms + duration_ms
            self._input_audio_timeline.append(
                (start_ms, end_ms, bytes(audio))
            )
            self._input_audio_offset_ms = end_ms
            cutoff = end_ms - 45_000.0
            while (
                self._input_audio_timeline
                and self._input_audio_timeline[0][1] < cutoff
            ):
                self._input_audio_timeline.popleft()

    def _current_input_offset_ms(self) -> float:
        with self._input_timeline_lock:
            return self._input_audio_offset_ms

    def _pcm_for_audio_range(
        self,
        start_ms: float,
        end_ms: float,
    ) -> bytes:
        start_ms = max(0.0, end_ms - 15_000.0, start_ms)
        if end_ms <= start_ms:
            return b""
        chunks: list[bytes] = []
        with self._input_timeline_lock:
            timeline = list(self._input_audio_timeline)
        for packet_start, packet_end, packet in timeline:
            overlap_start = max(start_ms, packet_start)
            overlap_end = min(end_ms, packet_end)
            if overlap_end <= overlap_start:
                continue
            first_frame = max(
                0,
                round((overlap_start - packet_start) * 24),
            )
            last_frame = min(
                len(packet) // 2,
                round((overlap_end - packet_start) * 24),
            )
            if last_frame > first_frame:
                chunks.append(
                    packet[first_frame * 2 : last_frame * 2]
                )
        return b"".join(chunks)

    @staticmethod
    def _pcm16_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
        output = io.BytesIO()
        with wave.open(output, "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(rate)
            target.writeframes(pcm)
        return output.getvalue()

    def _start_hybrid_transcription(self, event: dict) -> None:
        item_id = str(event.get("item_id") or "")
        if not item_id or not self.running:
            return
        end_ms = float(
            event.get(
                "audio_end_ms",
                self._current_input_offset_ms(),
            )
        )
        with self._input_timeline_lock:
            start_ms = self._speech_start_ms.pop(
                item_id,
                max(0.0, end_ms - 10_000.0),
            )
        pcm = self._pcm_for_audio_range(start_ms, end_ms)
        if len(pcm) < 24000:
            self.status_changed.emit(
                "語音片段太短，本輪不會自動回覆"
            )
            self._discard_conversation_item(item_id)
            return
        self._hybrid_transcription_active.set()
        self.status_changed.emit("高精度整句轉錄中…")
        wav_audio = self._pcm16_to_wav(pcm)
        generation = self._session_generation
        threading.Thread(
            target=self._run_hybrid_transcription,
            args=(item_id, wav_audio, generation),
            daemon=True,
        ).start()

    def _run_hybrid_transcription(
        self,
        item_id: str,
        wav_audio: bytes,
        generation: int,
    ) -> None:
        try:
            text = transcribe_wav_bytes(
                wav_audio,
                self._hybrid_api_key,
                self._hybrid_model,
                self._hybrid_language,
                self._hybrid_prompt,
            )
            error = ""
        except Exception as exc:  # noqa: BLE001 -- transcription returns diagnostics
            text = ""
            error = str(exc)
        self._hybrid_result.emit(
            item_id,
            text,
            error,
            generation,
        )

    def _finish_hybrid_transcription(
        self,
        item_id: str,
        text: str,
        error: str,
        generation: int,
    ) -> None:
        if generation != self._session_generation or not self.running:
            return
        if error:
            self._hybrid_transcription_active.clear()
            self._discard_conversation_item(item_id)
            self.status_changed.emit(
                f"高精度轉錄失敗，本輪不會自動回覆：{error}"
            )
            return
        accepted = self._emit_completed_user_transcript(
            text.strip(),
            item_id,
        )
        if accepted:
            requested = self._request_response()
            self._hybrid_transcription_active.clear()
            if not requested:
                self.status_changed.emit(
                    "文字已辨識，但無法觸發 Realtime 回覆"
                )
        else:
            self._hybrid_transcription_active.clear()
            self._discard_conversation_item(item_id)

    def _microphone_blocked(self) -> bool:
        return (
            self._hybrid_transcription_active.is_set()
            or self._response_pending.is_set()
            or (
                self.echo_guard
                and (
                    self._assistant_audio_active.is_set()
                    or time.monotonic() < self._input_resume_at
                )
            )
        )

    def _emit_completed_user_transcript(
        self,
        text: str,
        item_id: str = "",
    ) -> bool:
        if not text:
            return False
        if self.resembles_transcription_prompt(
            text,
            self._transcription_prompt_source,
            self._transcription_prompt_sent,
        ):
            self.status_changed.emit(
                "已略過疑似轉錄提示詞回灌"
            )
            return False
        if item_id:
            if item_id in self._final_transcript_item_ids:
                return False
            if len(self._final_transcript_item_order) >= 256:
                oldest = self._final_transcript_item_order.popleft()
                self._final_transcript_item_ids.discard(oldest)
            self._final_transcript_item_order.append(item_id)
            self._final_transcript_item_ids.add(item_id)
        self.user_transcript.emit(text)
        return True

    def _request_response(self) -> bool:
        """Allow one assistant response after a confirmed user transcript."""
        if not self.running:
            return False
        ws = self.ws
        if not ws or not ws.sock or not ws.sock.connected:
            return False
        self._response_pending.set()
        try:
            ws.send(json.dumps({"type": "response.create"}))
        except Exception:  # noqa: BLE001 -- failed request clears pending state
            self._response_pending.clear()
            return False
        self.status_changed.emit("已辨識，墨寒正在回覆")
        return True

    def _discard_conversation_item(self, item_id: str) -> bool:
        """Remove noise-only turns so they cannot pollute later context."""
        if not item_id or not self.running:
            return False
        ws = self.ws
        if not ws or not ws.sock or not ws.sock.connected:
            return False
        try:
            ws.send(
                json.dumps(
                    {
                        "type": "conversation.item.delete",
                        "item_id": item_id,
                    }
                )
            )
        except Exception:  # noqa: BLE001 -- deletion is best-effort and observable
            return False
        return True

    def _clear_server_input_buffer(self) -> None:
        """Discard audio already uploaded immediately around playback."""
        if not self.echo_guard or not self.running:
            return
        ws = self.ws
        if not ws or not ws.sock or not ws.sock.connected:
            return
        # A normal connection-close race will be reported by the lifecycle handler.
        with suppress(Exception):
            ws.send(
                json.dumps({"type": "input_audio_buffer.clear"})
            )

    def _begin_assistant_audio(self) -> None:
        started = False
        with self._assistant_state_lock:
            self._last_assistant_audio_at = time.monotonic()
            if not self._assistant_audio_active.is_set():
                self._assistant_audio_active.set()
                self._server_audio_done = False
                self._assistant_audio_generation += 1
                generation = self._assistant_audio_generation
                started = True
            else:
                generation = self._assistant_audio_generation
        self._response_pending.clear()
        if started:
            self.speaking_changed.emit(True)
            threading.Thread(
                target=self._assistant_audio_watchdog,
                args=(generation,),
                daemon=True,
            ).start()
        if self.echo_guard:
            while True:
                try:
                    self._input_queue.get_nowait()
                except queue.Empty:
                    break
            self._clear_server_input_buffer()

    def _mark_assistant_audio_done(self) -> None:
        self._server_audio_done = True
        if self._audio_queue.empty() and not self._playback_busy.is_set():
            self._finish_assistant_audio()

    def _assistant_audio_watchdog(self, generation: int) -> None:
        while self.running:
            time.sleep(0.25)
            with self._assistant_state_lock:
                if (
                    generation != self._assistant_audio_generation
                    or not self._assistant_audio_active.is_set()
                ):
                    return
                idle_for = (
                    time.monotonic() - self._last_assistant_audio_at
                )
            if (
                idle_for >= 4.0
                and self._audio_queue.empty()
                and not self._playback_busy.is_set()
            ):
                self._finish_assistant_audio(
                    expected_generation=generation,
                )
                return

    def _finish_assistant_audio(
        self,
        *,
        force: bool = False,
        expected_generation: int | None = None,
    ) -> None:
        with self._assistant_state_lock:
            if (
                expected_generation is not None
                and expected_generation != self._assistant_audio_generation
            ):
                return
            was_active = self._assistant_audio_active.is_set()
            self._assistant_audio_active.clear()
            self._server_audio_done = False
            self._last_assistant_audio_at = 0.0
            self._assistant_audio_generation += 1
        if self.echo_guard:
            # 喇叭與房間殘響通常比最後一個音訊封包多持續數百毫秒。
            self._input_resume_at = time.monotonic() + 0.9
            self._clear_server_input_buffer()
        if was_active or force:
            self.viseme_cue.emit(0.0, "CLOSED")
            self.speaking_changed.emit(False)

    def _emit_failure(self, detail: str) -> None:
        with self._failure_lock:
            if self._failure_emitted:
                return
            self._failure_emitted = True
        self.failed.emit(self._friendly_error(detail, self._active_model))

    @staticmethod
    def _friendly_error(detail: str, model: str) -> str:
        raw = str(detail)
        lowered = raw.lower()
        if (
            "model_not_found" in lowered
            or "does not exist or you do not have access" in lowered
        ):
            return (
                f"OpenAI 回報目前儲存的 API 金鑰無法使用「{model}」。"
                "這兩款 Realtime 2.1 模型本身是有效的；請確認 API 後台"
                "勾選模型的 Project，正是建立這支金鑰的同一個 Project。"
                "建議在該 Project 重新建立一支權限為 All 的 API Key，"
                "到墨寒的「設定」頁重新儲存，再啟動 Realtime。"
            )
        if "insufficient_quota" in lowered or "exceeded your current quota" in lowered:
            return (
                "OpenAI API 額度不足或專案預算已達上限。請檢查該 Project "
                "的 Billing、Budget 與 Realtime 模型用量限制。"
            )
        if "401" in lowered or "invalid_api_key" in lowered:
            return (
                "目前儲存的 OpenAI API 金鑰無效或已撤銷。"
                "請到「設定」頁重新貼上同一 Project 新建立的 API Key。"
            )
        if "fin=1 opcode=8" in lowered:
            return f"Realtime 連線被伺服器拒絕。詳細資訊：{raw}"
        return raw

    @staticmethod
    def _audio_error_message(error: Exception) -> str:
        detail = str(error)
        lowered = detail.lower()
        if (
            "rawinputstream" in lowered
            or "directsound error" in lowered
            or "mme error" in lowered
            or "invalid device" in lowered
        ):
            return (
                "Windows 無法開啟麥克風。請到「設定 → 隱私權與安全性 → "
                "麥克風」，開啟麥克風存取權及「讓桌面應用程式存取麥克風」，"
                "並確認沒有其他程式獨占麥克風。詳細資訊："
                + detail
            )
        return f"音訊裝置無法啟動：{detail}"
