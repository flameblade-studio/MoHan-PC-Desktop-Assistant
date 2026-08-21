from __future__ import annotations

lazy import base64
lazy import json
lazy from collections.abc import Callable
lazy from contextlib import suppress
lazy from typing import Any

lazy from integrations.realtime_contracts import (
    ASSISTANT_TEXT_DELTA_EVENTS,
    ASSISTANT_TEXT_DONE_EVENTS,
    ASSISTANT_TRANSCRIPT_DELTA_EVENTS,
    ASSISTANT_TRANSCRIPT_DONE_EVENTS,
    AUDIO_CANCELLED_EVENTS,
    AUDIO_DELTA_EVENTS,
    AUDIO_DONE_EVENTS,
    MAX_ASSISTANT_RESPONSE_CHARACTERS,
    USER_TRANSCRIPT_COMPLETED_EVENT,
    USER_TRANSCRIPT_FAILED_EVENT,
    _realtime_message,
)

__all__ = ("RealtimeEventMethods",)

MAX_TERMINAL_RESPONSES = 256

class RealtimeEventMethods:
    def _handle_audio_delta(self, event: dict[str, Any]) -> None:
        if not self.native_audio_output:
            return
        response_id = self._event_response_id(event)
        with self._response_state_lock:
            if response_id:
                if (
                    response_id in self._terminal_response_ids
                    or self._native_response_id
                    and self._native_response_id != response_id
                ):
                    return
                self._native_response_id = response_id
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


    def _handle_audio_done(
        self,
        kind: str,
        event: dict[str, Any] | None = None,
    ) -> None:
        if not self.native_audio_output:
            if kind in AUDIO_CANCELLED_EVENTS:
                self._cancel_external_output(
                    self._event_response_id(event or {}),
                    force_signal=True,
                )
            return
        response_id = self._event_response_id(event or {})
        with self._response_state_lock:
            if response_id:
                if response_id in self._terminal_response_ids:
                    return
                if self._native_response_id and self._native_response_id != response_id:
                    return
                self._native_response_id = response_id
            terminal_id = response_id or self._native_response_id
            self._remember_terminal_response_locked(terminal_id)
            self._native_response_id = ""
        if kind in AUDIO_CANCELLED_EVENTS:
            self._playback_packetizer.reset()
            self._discard_native_playback()
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
        delta = str(event.get("delta", ""))
        if (
            len(self._assistant_text) + len(delta)
            > MAX_ASSISTANT_RESPONSE_CHARACTERS
        ):
            self._cancel_server_response()
            self._assistant_text = ""
            self._emit_failure(
                _realtime_message(self._locale, "response_too_long"),
                trusted=True,
            )
            return
        self._assistant_text += delta


    def _handle_assistant_transcript_done(
        self,
        event: dict[str, Any],
    ) -> None:
        text = str(
            event.get("transcript") or self._assistant_text
        ).strip()
        self._assistant_text = ""
        if len(text) > MAX_ASSISTANT_RESPONSE_CHARACTERS:
            self._cancel_server_response()
            self._emit_failure(
                _realtime_message(self._locale, "response_too_long"),
                trusted=True,
            )
            return
        if text:
            self.assistant_transcript.emit(text)


    def _handle_assistant_text_delta(self, event: dict[str, Any]) -> None:
        if self.native_audio_output:
            return
        delta = str(event.get("delta", ""))
        if not delta:
            return
        response_id = self._event_response_id(event)
        output_generation = 0
        response_started = False
        oversized = False
        with self._response_state_lock:
            if not self._response_event_matches_locked(response_id):
                return
            output_generation, response_started = (
                self._begin_output_generation_locked()
            )
            oversized = (
                len(self._assistant_output_text) + len(delta)
                > MAX_ASSISTANT_RESPONSE_CHARACTERS
            )
            if not oversized:
                self._text_response_open = True
                self._assistant_output_text += delta
        if oversized:
            self._reject_oversized_response(response_id)
            return
        if response_started:
            self.output_text_started.emit(output_generation)
        self.output_text_delta.emit(output_generation, delta)


    def _handle_assistant_text_done(self, event: dict[str, Any]) -> None:
        if self.native_audio_output:
            return
        response_id = self._event_response_id(event)
        output_generation = 0
        response_started = False
        text_to_emit = ""
        oversized = False
        with self._response_state_lock:
            if not self._response_event_matches_locked(response_id):
                return
            output_generation, response_started = (
                self._begin_output_generation_locked()
            )
            text = str(event.get("text") or "")
            oversized = len(text) > MAX_ASSISTANT_RESPONSE_CHARACTERS
            if text and not oversized:
                if not self._assistant_output_text:
                    text_to_emit = text
                self._assistant_output_text = text
            self._text_response_open = True
        if oversized:
            self._reject_oversized_response(response_id)
            return
        if response_started:
            self.output_text_started.emit(output_generation)
        if text_to_emit:
            self.output_text_delta.emit(output_generation, text_to_emit)


    def _handle_response_done(self, event: dict[str, Any]) -> None:
        response = event.get("response")
        status = str(
            response.get("status", "")
            if isinstance(response, dict)
            else ""
        ).strip()
        if self.native_audio_output:
            kind = "response.done" if status in {"", "completed"} else "response.failed"
            self._handle_audio_done(kind, event)
            return
        response_id = self._event_response_id(event)
        if status != "completed":
            self._cancel_external_output(
                response_id,
            )
            return
        with self._response_state_lock:
            if not self._response_event_matches_locked(response_id):
                return
            text = self._assistant_output_text.strip()
            output_generation = self._active_output_generation
            self._remember_terminal_response_locked(response_id)
            self._active_response_id = ""
            self._assistant_output_text = ""
            self._text_response_open = False
            self._active_output_generation = 0
            self._anonymous_response_blocked = True
        self._response_pending.clear()
        if text:
            self.assistant_transcript.emit(text)
        if output_generation:
            self.output_text_done.emit(output_generation)


    def _reject_oversized_response(self, response_id: str) -> None:
        self._cancel_server_response()
        self._cancel_external_output(response_id, force_signal=True)
        self._emit_failure(
            _realtime_message(self._locale, "response_too_long"),
            trusted=True,
        )


    def _cancel_server_response(self) -> None:
        ws = self.ws
        if not ws or not ws.sock or not ws.sock.connected:
            return
        with suppress(Exception):
            ws.send(json.dumps({"type": "response.cancel"}))


    def _cancel_external_output(
        self,
        response_id: str = "",
        *,
        force_signal: bool = False,
    ) -> int:
        with self._response_state_lock:
            if response_id:
                if response_id in self._terminal_response_ids:
                    return self._output_generation
                if (
                    self._active_response_id
                    and self._active_response_id != response_id
                ):
                    self._remember_terminal_response_locked(response_id)
                    return self._output_generation
                if (
                    not self._active_response_id
                    and self._anonymous_response_blocked
                ):
                    self._remember_terminal_response_locked(response_id)
                    return self._output_generation
            terminal_id = response_id or self._active_response_id
            self._remember_terminal_response_locked(terminal_id)
            had_output = bool(
                self._active_response_id
                or self._text_response_open
                or self._assistant_output_text
                or self._response_pending.is_set()
                or self._external_playback_active.is_set()
            )
            self._active_response_id = ""
            self._assistant_output_text = ""
            self._text_response_open = False
            self._anonymous_response_blocked = True
            should_advance = force_signal or had_output
            should_emit = (
                should_advance and not self._output_interruption_emitted
            )
            if should_advance:
                self._output_generation += 1
                self._active_output_generation = 0
            if should_emit:
                self._output_interruption_emitted = True
            barrier = self._output_generation
        self._response_pending.clear()
        if should_emit:
            self.output_interrupted.emit(barrier)
        return barrier


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
                    _realtime_message(self._locale, "empty_transcript")
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
            or _realtime_message(self._locale, "realtime_api_error")
        )
        self.status_changed.emit(
            _realtime_message(
                self._locale,
                "transcription_failed",
                error=detail,
            )
        )
        self._discard_conversation_item(
            str(event.get("item_id") or "")
        )


    def _handle_speech_started(
        self,
        event: dict[str, Any],
    ) -> None:
        if not self.native_audio_output:
            self._cancel_external_output(force_signal=True)
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
        if not self.native_audio_output:
            self._cancel_external_output(force_signal=True)
        error = event.get("error") or {}
        detail = str(
            error.get("message")
            or _realtime_message(self._locale, "realtime_api_error")
        )
        self._emit_failure(detail)


    def _handle_server_event(self, event: dict[str, Any]) -> None:
        kind = str(event.get("type", ""))
        handler = self._server_event_handler(kind)
        if handler is not None:
            handler(event)


    def _server_event_handler(
        self,
        kind: str,
    ) -> Callable[[dict[str, Any]], None] | None:
        event_groups = (
            (AUDIO_DELTA_EVENTS, self._handle_audio_delta),
            (ASSISTANT_TRANSCRIPT_DELTA_EVENTS, self._handle_assistant_transcript_delta),
            (ASSISTANT_TRANSCRIPT_DONE_EVENTS, self._handle_assistant_transcript_done),
            (ASSISTANT_TEXT_DELTA_EVENTS, self._handle_assistant_text_delta),
            (ASSISTANT_TEXT_DONE_EVENTS, self._handle_assistant_text_done),
        )
        for kinds, handler in event_groups:
            if kind in kinds:
                return handler
        exact_handlers = {
            "response.created": self._handle_response_created,
            "response.done": self._handle_response_done,
            USER_TRANSCRIPT_COMPLETED_EVENT: self._handle_user_transcript_completed,
            USER_TRANSCRIPT_FAILED_EVENT: self._handle_user_transcript_failed,
            "input_audio_buffer.speech_started": self._handle_speech_started,
            "input_audio_buffer.speech_stopped": self._handle_speech_stopped,
            "error": self._handle_realtime_error,
        }
        exact_handler = exact_handlers.get(kind)
        if exact_handler is not None:
            return exact_handler
        if kind in AUDIO_DONE_EVENTS:
            return lambda event: self._handle_audio_done(kind, event)
        return None


    @staticmethod
    def _event_response_id(event: dict[str, Any]) -> str:
        response = event.get("response")
        nested_id = response.get("id") if isinstance(response, dict) else ""
        return str(event.get("response_id") or nested_id or "").strip()


    def _response_event_matches_locked(self, response_id: str) -> bool:
        if not response_id:
            return not self._anonymous_response_blocked
        if response_id in self._terminal_response_ids:
            return False
        if self._active_response_id:
            return self._active_response_id == response_id
        if self._anonymous_response_blocked:
            return False
        self._active_response_id = response_id
        return True


    def _remember_terminal_response_locked(self, response_id: str) -> None:
        if not response_id or response_id in self._terminal_response_ids:
            return
        if len(self._terminal_response_order) >= MAX_TERMINAL_RESPONSES:
            oldest = self._terminal_response_order.popleft()
            self._terminal_response_ids.discard(oldest)
        self._terminal_response_order.append(response_id)
        self._terminal_response_ids.add(response_id)


    def _prepare_external_response(self) -> None:
        with self._response_state_lock:
            self._assistant_output_text = ""
            self._text_response_open = False
            self._active_response_id = ""
            self._anonymous_response_blocked = False
            self._output_interruption_emitted = False


    def _begin_output_generation_locked(self) -> tuple[int, bool]:
        if self._active_output_generation:
            return self._active_output_generation, False
        self._output_generation += 1
        self._active_output_generation = self._output_generation
        return self._active_output_generation, True


    def _handle_response_created(self, event: dict[str, Any]) -> None:
        if self.native_audio_output:
            response_id = self._event_response_id(event)
            with self._response_state_lock:
                if response_id not in self._terminal_response_ids:
                    self._native_response_id = response_id
            return
        response_id = self._event_response_id(event)
        output_generation = 0
        response_started = False
        with self._response_state_lock:
            if not response_id:
                if self._anonymous_response_blocked:
                    return
            elif (
                response_id in self._terminal_response_ids
                or (
                    self._active_response_id
                    and self._active_response_id != response_id
                )
            ):
                return
            else:
                self._active_response_id = response_id
                self._anonymous_response_blocked = False
            output_generation, response_started = (
                self._begin_output_generation_locked()
            )
            self._output_interruption_emitted = False
        if response_started:
            self.output_text_started.emit(output_generation)
