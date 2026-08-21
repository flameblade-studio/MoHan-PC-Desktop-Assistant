from __future__ import annotations

lazy import base64
lazy import io
lazy import json
lazy import queue
lazy import sys
lazy import threading
lazy import time
lazy import wave
lazy from collections import deque
lazy from contextlib import suppress
lazy from typing import Any

lazy import sounddevice as sd
lazy from PySide6.QtCore import QObject, Signal

from integrations.realtime_contracts import (
    _REALTIME_MESSAGES,
    MAX_ASSISTANT_RESPONSE_CHARACTERS,
    RealtimeSessionConfig,
    RealtimeVoiceRequest,
    _AudioSession,
    _realtime_message,
)
lazy from domain.audio_acceleration import (
    PYTHON_PCM_ACCELERATION,
    PcmAccelerationPort,
)
lazy from domain.audio_buffer import BoundedAudioQueue, PcmPacketizer
lazy from domain.constants import FLOAT_COMPARISON_EPSILON
lazy from domain.lip_sync import VISEME_CUES_PER_SECOND
lazy from domain.safe_error import sanitize_error
lazy from integrations.realtime_events import RealtimeEventMethods
lazy from integrations.realtime_session import RealtimeSessionMethods
lazy from integrations.speech import transcribe_wav_bytes

REALTIME_SAMPLE_RATE = 24000
MAX_TRANSCRIPT_ITEMS = 256
IDLE_FINISH_SECONDS = 4.0

__all__ = (
    "MAX_ASSISTANT_RESPONSE_CHARACTERS",
    "_REALTIME_MESSAGES",
    "RealtimeSessionConfig",
    "RealtimeVoiceClient",
    "RealtimeVoiceRequest",
    "_realtime_message",
)


class RealtimeVoiceClient(RealtimeSessionMethods, RealtimeEventMethods, QObject):
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
    output_text_started = Signal(int)
    output_text_delta = Signal(int, str)
    output_text_done = Signal(int)
    output_interrupted = Signal(int)
    _hybrid_result = Signal(str, str, str, int)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        pcm_acceleration: PcmAccelerationPort = PYTHON_PCM_ACCELERATION,
    ):
        super().__init__(parent)
        self._pcm = pcm_acceleration
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
        self._locale = "zh-TW"
        self.echo_guard = True
        self._assistant_audio_active = threading.Event()
        self._playback_busy = threading.Event()
        self._assistant_state_lock = threading.Lock()
        self._assistant_audio_generation = 0
        self._last_assistant_audio_at = 0.0
        self._server_audio_done = False
        self._input_resume_at = 0.0
        self._assistant_text = ""
        self._response_state_lock = threading.Lock()
        self._initialize_response_lifecycle()
        self._external_playback_active = threading.Event()
        self._final_transcript_item_ids: set[str] = set()
        self._final_transcript_item_order: deque[str] = deque()
        self._transcription_prompt_source = ""
        self._transcription_prompt_sent = ""
        self.hybrid_transcription = True
        self.native_audio_output = True
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

    def _open_audio(self, *, playback_enabled: bool = True) -> None:
        audio_queue: BoundedAudioQueue[bytes | None] = BoundedAudioQueue(
            self.PLAYBACK_QUEUE_CHUNKS
        )
        input_queue: BoundedAudioQueue[bytes | None] = BoundedAudioQueue(
            self.INPUT_QUEUE_CHUNKS
        )
        input_device, input_rate = self._audio_device("input")
        output_device, output_rate = (
            self._audio_device("output")
            if playback_enabled
            else (None, 24_000)
        )
        output_stream = None
        input_stream = None

        def input_callback(indata, _frames, _time, status):
            if status:
                self.status_changed.emit(
                    _realtime_message(
                        self._locale,
                        "microphone_status",
                        status=status,
                    )
                )
            if self.running and not self._microphone_blocked():
                input_queue.offer(bytes(indata), keep_latest=True)

        try:
            output_stream = self._output_audio_stream(
                output_device,
                output_rate,
                playback_enabled,
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
            self._activate_audio_streams(
                _AudioSession(
                    playback_queue=audio_queue,
                    input_queue=input_queue,
                    output_stream=output_stream,
                    input_stream=input_stream,
                    output_rate=output_rate,
                    input_rate=input_rate,
                )
            )
        except Exception:
            self._discard_unstarted_audio_streams(input_stream, output_stream)
            raise

    def _audio_device(self, kind: str) -> tuple[object, int]:
        device = self._preferred_device(sd, kind)
        rate = int(sd.query_devices(device, kind)["default_samplerate"])
        return device, rate

    def _output_audio_stream(
        self,
        device: object,
        rate: int,
        enabled: bool,
    ) -> object | None:
        if not enabled:
            return None
        return sd.RawOutputStream(
            device=device,
            samplerate=rate,
            channels=1,
            dtype="int16",
            blocksize=max(
                1,
                rate * self.DEVICE_BLOCK_MILLISECONDS // 1000,
            ),
            latency="low",
        )

    def _activate_audio_streams(
        self,
        audio: _AudioSession,
    ) -> None:
        with self._audio_lock:
            if not self.running:
                raise RuntimeError("Realtime 連線已停止")
            self._audio_queue = audio.playback_queue
            self._input_queue = audio.input_queue
            self._output_stream = audio.output_stream
            self._input_stream = audio.input_stream
            if audio.output_stream is not None:
                audio.output_stream.start()
            audio.input_stream.start()
        if audio.output_stream is not None:
            threading.Thread(
                target=self._playback_loop,
                args=(
                    audio.playback_queue,
                    audio.output_stream,
                    audio.output_rate,
                ),
                daemon=True,
            ).start()
        threading.Thread(
            target=self._input_sender_loop,
            args=(audio.input_queue, audio.input_rate),
            daemon=True,
        ).start()

    def _discard_unstarted_audio_streams(
        self,
        input_stream: object | None,
        output_stream: object | None,
    ) -> None:
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
            if input_rate != REALTIME_SAMPLE_RATE:
                audio, rate_state = self._pcm.rate_convert_pcm16(
                    audio, 1, input_rate, REALTIME_SAMPLE_RATE, rate_state
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
                            _realtime_message(self._locale, "sender_lag")
                        )
            except Exception:
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
            _realtime_message(self._locale, "playback_buffer_full"),
            trusted=True,
        )
        return False

    def _discard_native_playback(self) -> None:
        while True:
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        self._finish_assistant_audio()
        output_stream = self._output_stream
        if output_stream is not None:
            with suppress(Exception):
                output_stream.abort()
                output_stream.start()

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
            with self._assistant_state_lock:
                playback_generation = self._assistant_audio_generation
            self._playback_busy.set()
            try:
                for offset in range(0, len(audio), animation_chunk_bytes):
                    with self._assistant_state_lock:
                        playback_cancelled = (
                            playback_generation
                            != self._assistant_audio_generation
                        )
                    if playback_cancelled:
                        rate_state = None
                        break
                    source_chunk = audio[offset : offset + animation_chunk_bytes]
                    if not source_chunk:
                        continue
                    vowel_level, vowel = self._pcm.infer_vowel_pcm16(
                        source_chunk,
                        REALTIME_SAMPLE_RATE,
                    )
                    self.viseme_cue.emit(vowel_level, vowel)
                    playback_chunk = source_chunk
                    if output_rate != REALTIME_SAMPLE_RATE:
                        playback_chunk, rate_state = self._pcm.rate_convert_pcm16(
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
                    if abs(gain - 1.0) >= FLOAT_COMPARISON_EPSILON:
                        playback_chunk = self._pcm.scale_pcm16(
                            playback_chunk,
                            gain,
                        )
                    output_stream.write(playback_chunk)
            except Exception as exc:
                self._report_playback_error(exc, playback_generation)
                break
            finally:
                self._playback_busy.clear()
            if self._server_audio_done and audio_queue.empty():
                self._finish_assistant_audio()

    def _report_playback_error(
        self,
        error: Exception,
        playback_generation: int,
    ) -> None:
        with self._assistant_state_lock:
            playback_cancelled = (
                playback_generation != self._assistant_audio_generation
            )
        if playback_cancelled:
            return
        self._finish_assistant_audio(force=True)
        self._emit_failure(
            self._audio_error_message(error, self._locale),
            trusted=True,
        )

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
        if len(pcm) < REALTIME_SAMPLE_RATE:
            self.status_changed.emit(
                _realtime_message(self._locale, "clip_too_short")
            )
            self._discard_conversation_item(item_id)
            return
        self._hybrid_transcription_active.set()
        self.status_changed.emit(
            _realtime_message(self._locale, "transcribing")
        )
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
            error = str(sanitize_error(exc))
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
                _realtime_message(
                    self._locale,
                    "hybrid_failed",
                    error=error,
                )
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
                    _realtime_message(
                        self._locale,
                        "response_not_started",
                    )
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
                    or self._external_playback_active.is_set()
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
                _realtime_message(self._locale, "prompt_echo_skipped")
            )
            return False
        if item_id:
            if item_id in self._final_transcript_item_ids:
                return False
            if len(self._final_transcript_item_order) >= MAX_TRANSCRIPT_ITEMS:
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
        if not self.native_audio_output:
            self._prepare_external_response()
        try:
            response: dict[str, Any] = {"type": "response.create"}
            if not self.native_audio_output:
                response["response"] = {"output_modalities": ["text"]}
            ws.send(json.dumps(response))
        except Exception:
            self._response_pending.clear()
            return False
        self.status_changed.emit(
            _realtime_message(self._locale, "replying")
        )
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
                idle_for >= IDLE_FINISH_SECONDS
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
            # 播放結束後短暫延後收音，避免把墨寒自己的尾音當成使用者輸入。
            self._input_resume_at = time.monotonic() + 0.9
            self._clear_server_input_buffer()
        if was_active or force:
            self.viseme_cue.emit(0.0, "CLOSED")
            self.speaking_changed.emit(False)

    def _emit_failure(self, detail: str, *, trusted: bool = False) -> None:
        with self._failure_lock:
            if self._failure_emitted:
                return
            self._failure_emitted = True
        message = (
            detail
            if trusted
            else self._friendly_error(
                detail,
                self._active_model,
                self._locale,
            )
        )
        self.failed.emit(message)

    @staticmethod
    def _friendly_error(
        detail: str,
        model: str,
        locale: str = "zh-TW",
    ) -> str:
        raw = str(detail)
        lowered = raw.lower()
        if (
            "model_not_found" in lowered
            or "does not exist or you do not have access" in lowered
        ):
            return _realtime_message(
                locale,
                "model_access",
                model=model,
            )
        if "insufficient_quota" in lowered or "exceeded your current quota" in lowered:
            return _realtime_message(locale, "quota")
        if "401" in lowered or "invalid_api_key" in lowered:
            return _realtime_message(locale, "invalid_key")
        if "fin=1 opcode=8" in lowered:
            return _realtime_message(
                locale,
                "server_rejected",
                error=sanitize_error(raw),
            )
        return str(sanitize_error(raw))

    @staticmethod
    def _audio_error_message(
        error: Exception,
        locale: str = "zh-TW",
    ) -> str:
        detail = str(error)
        lowered = detail.lower()
        safe_detail = sanitize_error(error)
        if (
            "rawinputstream" in lowered
            or "directsound error" in lowered
            or "mme error" in lowered
            or "invalid device" in lowered
        ):
            return _realtime_message(
                locale,
                "microphone_failed",
                error=safe_detail,
            )
        return _realtime_message(
            locale,
            "audio_failed",
            error=safe_detail,
        )
