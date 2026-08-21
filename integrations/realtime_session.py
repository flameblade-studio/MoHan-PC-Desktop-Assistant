from __future__ import annotations

lazy import hashlib
lazy import json
lazy import re
lazy import threading
lazy import time
lazy import uuid
lazy from collections import deque
lazy from collections.abc import Callable
lazy from contextlib import suppress
lazy from dataclasses import replace
lazy from difflib import SequenceMatcher
lazy from typing import Any

lazy import sounddevice as sd
lazy import websocket

lazy from domain.language_support import canonical_ui_language
lazy from integrations.realtime_speech_output import (
    REALTIME_OUTPUT_MODES,
    REALTIME_OUTPUT_OPENAI,
)

# Transcription-prompt heuristics.
MAX_TERM_LENGTH = 40
MAX_TERMS = 16
MIN_COMPARISON_LENGTH = 16
MIN_SUBSTRING_LENGTH = 20
SIMILARITY_THRESHOLD = 0.82


def _realtime_message(
    locale: str,
    key: str,
    **values: object,
) -> str:
    catalog = _REALTIME_MESSAGES[canonical_ui_language(locale)]
    message = catalog[key]
    return message.format(**values) if values else message



lazy from integrations.realtime_contracts import (
    _REALTIME_MESSAGES,
    RealtimeSessionConfig,
    RealtimeVoiceRequest,
    _realtime_message,
)

__all__ = ("RealtimeSessionMethods",)


class RealtimeSessionMethods:
    def _initialize_response_lifecycle(self) -> None:
        self._assistant_output_text = ""
        self._text_response_open = False
        self._active_response_id = ""
        self._native_response_id = ""
        self._terminal_response_ids: set[str] = set()
        self._terminal_response_order: deque[str] = deque()
        self._anonymous_response_blocked = False
        self._output_interruption_emitted = False
        self._output_generation = 0
        self._active_output_generation = 0


    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_percent = max(0, min(160, int(volume_percent)))
        self.muted = bool(muted)


    def set_external_playback_active(self, active: bool) -> None:
        """Block echo-prone microphone upload during delegated playback."""
        if active:
            self._external_playback_active.set()
            self._clear_server_input_buffer()
            return
        self._external_playback_active.clear()
        if self.echo_guard:
            self._input_resume_at = time.monotonic() + 0.9
            self._clear_server_input_buffer()


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
                RealtimeSessionMethods
                ._sanitize_realtime_transcription_prompt(
                    session.transcription_prompt
                )
            ),
            external_transcription=bool(
                session.external_transcription
            ),
            output_mode=(
                session.output_mode
                if session.output_mode in REALTIME_OUTPUT_MODES
                else REALTIME_OUTPUT_OPENAI
            ),
            locale=canonical_ui_language(session.locale),
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
        self._locale = canonical_ui_language(session.locale)
        self.echo_guard = request.echo_guard
        self.hybrid_transcription = session.external_transcription
        self.native_audio_output = session.output_mode == "openai-realtime"
        self._hybrid_api_key = request.api_key
        self._hybrid_model = session.transcription_model
        self._hybrid_language = session.transcription_language
        self._hybrid_prompt = session.transcription_prompt
        self._session_generation += 1
        self._assistant_audio_active.clear()
        self._external_playback_active.clear()
        self._hybrid_transcription_active.clear()
        self._response_pending.clear()
        self._assistant_text = ""
        with self._response_state_lock:
            self._assistant_output_text = ""
            self._text_response_open = False
            self._active_response_id = ""
            self._native_response_id = ""
            self._terminal_response_ids.clear()
            self._terminal_response_order.clear()
            self._anonymous_response_blocked = False
            self._output_interruption_emitted = False
            self._output_generation += 1
            self._active_output_generation = 0
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
        self._locale = canonical_ui_language(request.session.locale)
        if not request.api_key.strip():
            self.failed.emit(_realtime_message(self._locale, "missing_key"))
            return
        if not self.dependencies_available():
            self.failed.emit(
                _realtime_message(self._locale, "missing_components")
            )
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
        self.status_changed.emit(
            _realtime_message(self._locale, "connecting")
        )
        generation = self._session_generation
        threading.Thread(
            target=self._connect,
            args=(normalized_request, generation),
            daemon=True,
        ).start()


    def stop(self) -> int:
        self.running = False
        self._session_generation += 1
        self._hybrid_transcription_active.clear()
        self._response_pending.clear()
        self._finish_assistant_audio(force=True)
        barrier = self._cancel_external_output(force_signal=True)
        self._external_playback_active.clear()
        ws = self.ws
        self.ws = None
        if ws:
            # A closing WebSocket may reject a second close during shutdown.
            with suppress(Exception):
                ws.close()
        self._close_audio()
        self.status_changed.emit(
            _realtime_message(self._locale, "disconnected")
        )
        return barrier


    def _connect(
        self,
        request: RealtimeVoiceRequest,
        generation: int,
    ) -> None:
        def is_current_session() -> bool:
            return generation == self._session_generation

        if not is_current_session():
            return
        safety_id = hashlib.sha256(
            f"mohan-{uuid.getnode()}".encode()
        ).hexdigest()
        url = (
            "wss://api.openai.com/v1/realtime?model="
            + request.session.model
        )

        callbacks = self._websocket_callbacks(
            request,
            is_current_session,
        )

        websocket_app = websocket.WebSocketApp(
            url,
            header=[
                f"Authorization: Bearer {request.api_key}",
                f"OpenAI-Safety-Identifier: {safety_id}",
            ],
            **callbacks,
        )
        if not is_current_session():
            return
        self.ws = websocket_app
        websocket_app.run_forever(ping_interval=20, ping_timeout=10)


    def _websocket_callbacks(
        self,
        request: RealtimeVoiceRequest,
        is_current_session: Callable[[], bool],
    ) -> dict[str, Callable[..., None]]:
        def on_open(ws) -> None:
            if not is_current_session():
                with suppress(Exception):
                    ws.close()
                return
            self._open_realtime_session(ws, request)

        def on_message(_ws, message: object) -> None:
            if not is_current_session():
                return
            try:
                event = json.loads(message)
            except (TypeError, json.JSONDecodeError):
                return
            self._handle_server_event(event)

        def on_error(_ws, error: object) -> None:
            if is_current_session() and self.running:
                self._emit_failure(str(error))

        def on_close(_ws, _code, _message) -> None:
            if is_current_session():
                self._close_realtime_session()

        return {
            "on_open": on_open,
            "on_message": on_message,
            "on_error": on_error,
            "on_close": on_close,
        }


    def _open_realtime_session(
        self,
        ws: object,
        request: RealtimeVoiceRequest,
    ) -> None:
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
            self._open_audio(playback_enabled=self.native_audio_output)
            self.status_changed.emit(
                _realtime_message(self._locale, "listening")
            )
        except Exception as exc:
            self._emit_failure(
                self._audio_error_message(exc, self._locale),
                trusted=True,
            )
            self.stop()


    def _close_realtime_session(self) -> None:
        self.running = False
        self.ws = None
        if not self.native_audio_output:
            self._cancel_external_output(force_signal=True)
        self._close_audio()
        self._finish_assistant_audio(force=True)
        self.status_changed.emit(
            _realtime_message(self._locale, "disconnected")
        )


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
                and len(value) <= MAX_TERM_LENGTH
                and not re.prefixmatch(
                    r"^(?:請|使用|保留|不要|轉錄|語言|请|准确|"
                    r"Please|Preserve|Keep|do not|日本語|固有名詞)",
                    value,
                    flags=re.IGNORECASE,
                )
                and value not in terms
            ):
                terms.append(value)
            if len(terms) >= MAX_TERMS:
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
        if len(candidate) < MIN_COMPARISON_LENGTH:
            return False
        for prompt in prompts:
            reference = cls._comparison_text(prompt)
            if len(reference) < MIN_COMPARISON_LENGTH:
                continue
            if candidate == reference:
                return True
            shorter, longer = sorted(
                (candidate, reference),
                key=len,
            )
            if len(shorter) >= MIN_SUBSTRING_LENGTH and shorter in longer:
                return True
            if SequenceMatcher(
                None,
                candidate,
                reference,
            ).ratio() >= SIMILARITY_THRESHOLD:
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

        native_audio = config.output_mode == "openai-realtime"
        event = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "model": config.model,
                "output_modalities": ["audio" if native_audio else "text"],
                "instructions": instructions,
                "reasoning": {"effort": "low"},
                "audio": {"input": input_audio},
            },
        }
        if native_audio:
            event["session"]["audio"]["output"] = {
                "format": {
                    "type": "audio/pcm",
                    "rate": 24000,
                },
                "voice": config.voice,
            }
        if not config.external_transcription:
            event["session"]["include"] = [
                "item.input_audio_transcription.logprobs"
            ]
        return event
