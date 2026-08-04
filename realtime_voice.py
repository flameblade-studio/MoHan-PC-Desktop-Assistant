from __future__ import annotations

import base64
from collections import deque
from difflib import SequenceMatcher
import hashlib
import io
import json
import queue
import re
import sys
import threading
import time
import uuid
import wave

from PySide6.QtCore import QObject, Signal

from lip_sync import (
    VISEME_CUES_PER_SECOND,
    infer_vowel_pcm16,
)
from pcm_audio import rate_convert_pcm16, scale_pcm16
from speech import transcribe_wav_bytes


class RealtimeVoiceClient(QObject):
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
        self._audio_queue: queue.Queue[bytes | None] = queue.Queue()
        self._input_queue: queue.Queue[bytes | None] = queue.Queue(maxsize=64)
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
            import sounddevice  # noqa: F401
            import websocket  # noqa: F401
        except ImportError:
            return False
        return True

    def start(
        self,
        api_key: str,
        voice: str,
        instructions: str,
        memory_context: str,
        model: str = "gpt-realtime-2.1-mini",
        echo_guard: bool = True,
        transcription_model: str = "gpt-4o-mini-transcribe",
        transcription_language: str = "zh",
        transcription_prompt: str = "",
        noise_reduction: str = "near_field",
        turn_detection: str = "server_vad",
        recent_context: str = "",
        hybrid_transcription: bool = True,
    ) -> None:
        if self.running:
            return
        if not api_key.strip():
            self.failed.emit("請先儲存 OpenAI API 金鑰")
            return
        if not self.dependencies_available():
            self.failed.emit("Realtime 語音元件尚未安裝")
            return
        with self._failure_lock:
            self._failure_emitted = False
        self._active_model = model
        self.echo_guard = echo_guard
        self.hybrid_transcription = bool(hybrid_transcription)
        self._hybrid_api_key = api_key.strip()
        self._hybrid_model = (
            transcription_model.strip()
            or "gpt-4o-mini-transcribe"
        )
        self._hybrid_language = transcription_language.strip()
        self._hybrid_prompt = transcription_prompt.strip()
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
        self._transcription_prompt_source = transcription_prompt.strip()
        self._transcription_prompt_sent = (
            self._sanitize_realtime_transcription_prompt(
                transcription_prompt
            )
        )
        with self._input_timeline_lock:
            self._input_audio_offset_ms = 0.0
            self._input_audio_timeline.clear()
            self._speech_start_ms.clear()
        self.running = True
        self.status_changed.emit("正在連線…")
        threading.Thread(
            target=self._connect,
            args=(
                api_key,
                voice,
                instructions,
                memory_context,
                recent_context,
                model,
                transcription_model,
                transcription_language,
                self._transcription_prompt_sent,
                noise_reduction,
                turn_detection,
                self.hybrid_transcription,
            ),
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
            try:
                ws.close()
            except Exception:
                pass
        self._close_audio()
        self.status_changed.emit("未連線")

    def _connect(
        self,
        api_key: str,
        voice: str,
        instructions: str,
        memory_context: str,
        recent_context: str,
        model: str,
        transcription_model: str,
        transcription_language: str,
        transcription_prompt: str,
        noise_reduction: str,
        turn_detection: str,
        hybrid_transcription: bool,
    ) -> None:
        import websocket

        safety_id = hashlib.sha256(
            f"mohan-{uuid.getnode()}".encode("utf-8")
        ).hexdigest()
        url = f"wss://api.openai.com/v1/realtime?model={model}"

        def on_open(ws):
            self.ws = ws
            full_instructions = self._compose_instructions(
                instructions,
                memory_context,
                recent_context,
            )
            ws.send(
                json.dumps(
                    self._session_update_event(
                        model=model,
                        voice=voice,
                        instructions=full_instructions,
                        transcription_model=transcription_model,
                        transcription_language=transcription_language,
                        transcription_prompt=transcription_prompt,
                        noise_reduction=noise_reduction,
                        turn_detection=turn_detection,
                        external_transcription=hybrid_transcription,
                    ),
                    ensure_ascii=False,
                )
            )
            try:
                self._open_audio()
                self.status_changed.emit("已連線，妾在聽")
            except Exception as exc:
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
                f"Authorization: Bearer {api_key}",
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
        marker = re.search(r"(?:常用詞|專有名詞)\s*[：:]", raw)
        if marker:
            term_source = raw[marker.end():]
        term_source = re.split(
            r"(?:請保留|請使用|不要改寫|轉錄規則)",
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
                    r"^(?:請|使用|保留|不要|轉錄|語言)",
                    value,
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
        *,
        model: str,
        voice: str,
        instructions: str,
        transcription_model: str,
        transcription_language: str,
        transcription_prompt: str,
        noise_reduction: str,
        turn_detection: str,
        external_transcription: bool = True,
    ) -> dict:
        transcription = {
            "model": transcription_model or "gpt-4o-mini-transcribe",
        }
        if transcription_language:
            transcription["language"] = transcription_language
        if transcription_prompt:
            transcription["prompt"] = transcription_prompt

        if turn_detection == "semantic_vad":
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
                None if external_transcription else transcription
            ),
        }
        if noise_reduction in {"near_field", "far_field"}:
            input_audio["noise_reduction"] = {
                "type": noise_reduction,
            }

        event = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "model": model,
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
                        "voice": voice,
                    },
                },
            },
        }
        if not external_transcription:
            event["session"]["include"] = [
                "item.input_audio_transcription.logprobs"
            ]
        return event

    def _handle_server_event(self, event: dict) -> None:
        kind = event.get("type", "")
        if kind in {
            "response.output_audio.delta",
            "response.audio.delta",
        }:
            delta = event.get("delta", "")
            if delta:
                self._begin_assistant_audio()
                self._audio_queue.put(base64.b64decode(delta))
        elif kind in {
            "response.output_audio.done",
            "response.audio.done",
            "response.done",
            "response.cancelled",
            "response.failed",
        }:
            self._response_pending.clear()
            self._mark_assistant_audio_done()
        elif kind in {
            "response.output_audio_transcript.delta",
            "response.audio_transcript.delta",
        }:
            self._assistant_text += event.get("delta", "")
        elif kind in {
            "response.output_audio_transcript.done",
            "response.audio_transcript.done",
        }:
            text = (event.get("transcript") or self._assistant_text).strip()
            self._assistant_text = ""
            if text:
                self.assistant_transcript.emit(text)
        elif kind == (
            "conversation.item.input_audio_transcription.completed"
        ):
            if self.hybrid_transcription:
                return
            text = event.get("transcript", "").strip()
            item_id = str(event.get("item_id") or "")
            already_seen = bool(
                item_id
                and item_id in self._final_transcript_item_ids
            )
            # Only the documented completed event is committed to the chat.
            # Delta and legacy done events are deliberately ignored so a
            # provisional recognition can never appear as a user message.
            accepted = self._emit_completed_user_transcript(
                text,
                item_id,
            )
            if accepted:
                self._request_response()
            elif not already_seen:
                self._discard_conversation_item(item_id)
                if not text:
                    self.status_changed.emit(
                        "未取得有效轉錄，本輪不會自動回覆"
                    )
        elif kind == (
            "conversation.item.input_audio_transcription.failed"
        ):
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
        elif kind == "input_audio_buffer.speech_started":
            # Only apply the playback tail when this is a real interruption.
            # Applying it to ordinary user speech would erase the server
            # buffer and drop the next 0.9 seconds of the user's sentence.
            if (
                self._assistant_audio_active.is_set()
                or self._playback_busy.is_set()
                or self._response_pending.is_set()
            ):
                self._finish_assistant_audio(force=True)
            if self.hybrid_transcription:
                item_id = str(event.get("item_id") or "")
                start_ms = float(
                    event.get(
                        "audio_start_ms",
                        self._current_input_offset_ms() - 500.0,
                    )
                )
                if item_id:
                    with self._input_timeline_lock:
                        self._speech_start_ms[item_id] = max(
                            0.0,
                            start_ms,
                        )
        elif kind == "input_audio_buffer.speech_stopped":
            if self.hybrid_transcription:
                self._start_hybrid_transcription(event)
        elif kind == "error":
            self._finish_assistant_audio(force=True)
            error = event.get("error", {})
            self._emit_failure(
                error.get("message", "Realtime API 發生錯誤")
            )

    def _open_audio(self) -> None:
        import sounddevice as sd

        audio_queue: queue.Queue[bytes | None] = queue.Queue()
        input_queue: queue.Queue[bytes | None] = queue.Queue(maxsize=64)
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
                try:
                    input_queue.put_nowait(bytes(indata))
                except queue.Full:
                    pass

        try:
            output_stream = sd.RawOutputStream(
                device=output_device,
                samplerate=output_rate,
                channels=1,
                dtype="int16",
                blocksize=max(1, output_rate // 10),
            )
            input_stream = sd.RawInputStream(
                device=input_device,
                samplerate=input_rate,
                channels=1,
                dtype="int16",
                blocksize=max(1, input_rate // 10),
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
                    try:
                        stream.abort()
                        stream.close()
                    except Exception:
                        pass
            raise

    def _input_sender_loop(
        self,
        input_queue: queue.Queue[bytes | None],
        input_rate: int,
    ) -> None:
        rate_state = None
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
            except Exception:
                break

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
            except Exception as exc:
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
            self._audio_queue = queue.Queue()
            self._input_queue = queue.Queue(maxsize=64)
        for pending_queue in (audio_queue, input_queue):
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
                try:
                    stream.abort()
                    stream.close()
                except Exception:
                    pass

    @staticmethod
    def _preferred_device(sd, kind: str):
        default_device = sd.default.device
        fallback = default_device[0 if kind == "input" else 1]
        if not sys.platform.startswith("win"):
            return fallback
        key = f"default_{kind}_device"
        try:
            for hostapi in sd.query_hostapis():
                if "WASAPI" in hostapi["name"]:
                    candidate = int(hostapi[key])
                    if candidate >= 0:
                        return candidate
        except Exception:
            pass
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
        except Exception as exc:
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
        except Exception:
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
        except Exception:
            return False
        return True

    def _clear_server_input_buffer(self) -> None:
        """Discard audio already uploaded immediately around playback."""
        if not self.echo_guard or not self.running:
            return
        ws = self.ws
        if not ws or not ws.sock or not ws.sock.connected:
            return
        try:
            ws.send(
                json.dumps({"type": "input_audio_buffer.clear"})
            )
        except Exception:
            # A closing connection can race the guard cleanup.  The normal
            # WebSocket lifecycle will report a material connection failure.
            pass

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
