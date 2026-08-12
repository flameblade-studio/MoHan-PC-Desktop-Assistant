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
lazy from collections.abc import Callable
lazy from contextlib import suppress
lazy from dataclasses import dataclass, field, replace
lazy from difflib import SequenceMatcher
lazy from typing import Any

lazy import sounddevice as sd
lazy import websocket
lazy from PySide6.QtCore import QObject, Signal

lazy from audio_buffer import BoundedAudioQueue, PcmPacketizer
lazy from immutable_config import deep_freeze
lazy from language_support import canonical_ui_language
lazy from lip_sync import (
    VISEME_CUES_PER_SECOND,
    infer_vowel_pcm16,
)
lazy from pcm_audio import rate_convert_pcm16, scale_pcm16
lazy from realtime_speech_output import (
    REALTIME_OUTPUT_MODES,
    REALTIME_OUTPUT_OPENAI,
)
lazy from safe_error import sanitize_error
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
    output_mode: str = REALTIME_OUTPUT_OPENAI
    locale: str = "zh-TW"


@dataclass(frozen=True, slots=True)
class RealtimeVoiceRequest:
    api_key: str = field(repr=False)
    instructions: str
    memory_context: str
    session: RealtimeSessionConfig
    recent_context: str = ""
    echo_guard: bool = True


@dataclass(frozen=True, slots=True)
class _AudioSession:
    playback_queue: BoundedAudioQueue[bytes | None]
    input_queue: BoundedAudioQueue[bytes | None]
    output_stream: object | None
    input_stream: object
    output_rate: int
    input_rate: int


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
ASSISTANT_TEXT_DELTA_EVENTS = frozenset(
    {"response.output_text.delta", "response.text.delta"}
)
ASSISTANT_TEXT_DONE_EVENTS = frozenset(
    {"response.output_text.done", "response.text.done"}
)
MAX_ASSISTANT_RESPONSE_CHARACTERS = 32_768
USER_TRANSCRIPT_COMPLETED_EVENT = (
    "conversation.item.input_audio_transcription.completed"
)
USER_TRANSCRIPT_FAILED_EVENT = (
    "conversation.item.input_audio_transcription.failed"
)

_REALTIME_MESSAGES = deep_freeze({
    "zh-TW": {
        "missing_key": "請先儲存 OpenAI API 金鑰",
        "missing_components": "Realtime 語音元件尚未安裝",
        "connecting": "正在連線…",
        "disconnected": "未連線",
        "listening": "已連線，妾在聽",
        "empty_transcript": "未取得有效轉錄，本輪不會自動回覆",
        "transcription_failed": "轉錄失敗，本輪不會自動回覆：{error}",
        "realtime_api_error": "Realtime API 發生錯誤",
        "generic_error": "Realtime 發生錯誤：{error}",
        "microphone_status": "麥克風狀態：{status}",
        "sender_lag": "麥克風處理一度落後，已捨棄最舊音訊以恢復即時性",
        "response_too_long": (
            "Realtime 回應超過 32,768 字元安全上限，已停止本輪回應。"
        ),
        "playback_buffer_full": (
            "Realtime 播放緩衝已達 1.5 秒安全上限，已停止本輪語音，"
            "避免延遲持續累積或跳字。"
        ),
        "playback_failed": "播放語音失敗：{error}",
        "clip_too_short": "語音片段太短，本輪不會自動回覆",
        "transcribing": "高精度整句轉錄中…",
        "hybrid_failed": "高精度轉錄失敗，本輪不會自動回覆：{error}",
        "response_not_started": "文字已辨識，但無法觸發 Realtime 回覆",
        "prompt_echo_skipped": "已略過疑似轉錄提示詞回灌",
        "replying": "已辨識，墨寒正在回覆",
        "model_access": (
            "OpenAI 回報目前儲存的 API 金鑰無法使用「{model}」。"
            "請確認 API 後台勾選模型的 Project，正是建立這支金鑰的同一個 "
            "Project；再於該 Project 建立具適當權限的 API Key，並到墨寒的"
            "「設定」頁重新儲存。"
        ),
        "quota": (
            "OpenAI API 額度不足或專案預算已達上限。請檢查該 Project 的 "
            "Billing、Budget 與 Realtime 模型用量限制。"
        ),
        "invalid_key": (
            "目前儲存的 OpenAI API 金鑰無效或已撤銷。"
            "請到「設定」頁重新貼上同一 Project 新建立的 API Key。"
        ),
        "server_rejected": "Realtime 連線被伺服器拒絕。詳細資訊：{error}",
        "microphone_failed": (
            "Windows 無法開啟麥克風。請到「設定 → 隱私權與安全性 → 麥克風」，"
            "開啟麥克風存取權及「讓桌面應用程式存取麥克風」，並確認沒有其他"
            "程式獨占麥克風。詳細資訊：{error}"
        ),
        "audio_failed": "音訊裝置無法啟動：{error}",
    },
    "zh-CN": {
        "missing_key": "请先保存 OpenAI API 密钥",
        "missing_components": "Realtime 语音组件尚未安装",
        "connecting": "正在连接…",
        "disconnected": "未连接",
        "listening": "已连接，妾在听",
        "empty_transcript": "未取得有效转录，本轮不会自动回复",
        "transcription_failed": "转录失败，本轮不会自动回复：{error}",
        "realtime_api_error": "Realtime API 发生错误",
        "generic_error": "Realtime 发生错误：{error}",
        "microphone_status": "麦克风状态：{status}",
        "sender_lag": "麦克风处理一度落后，已舍弃最旧音频以恢复实时性",
        "response_too_long": (
            "Realtime 回复超过 32,768 字符安全上限，已停止本轮回复。"
        ),
        "playback_buffer_full": (
            "Realtime 播放缓冲已达 1.5 秒安全上限，已停止本轮语音，"
            "避免延迟持续累积或跳字。"
        ),
        "playback_failed": "播放语音失败：{error}",
        "clip_too_short": "语音片段太短，本轮不会自动回复",
        "transcribing": "高精度整句转录中…",
        "hybrid_failed": "高精度转录失败，本轮不会自动回复：{error}",
        "response_not_started": "文字已识别，但无法触发 Realtime 回复",
        "prompt_echo_skipped": "已略过疑似转录提示词回灌",
        "replying": "已识别，墨寒正在回复",
        "model_access": (
            "OpenAI 报告当前保存的 API 密钥无法使用“{model}”。"
            "请确认 API 后台所选模型的 Project 与建立这支密钥的 Project 相同；"
            "再于该 Project 建立具备适当权限的 API Key，并到墨寒的“设置”页"
            "重新保存。"
        ),
        "quota": (
            "OpenAI API 额度不足或项目预算已达上限。请检查该 Project 的 "
            "Billing、Budget 与 Realtime 模型用量限制。"
        ),
        "invalid_key": (
            "当前保存的 OpenAI API 密钥无效或已撤销。"
            "请到“设置”页重新粘贴同一 Project 新建立的 API Key。"
        ),
        "server_rejected": "Realtime 连接被服务器拒绝。详细信息：{error}",
        "microphone_failed": (
            "Windows 无法打开麦克风。请到“设置 → 隐私和安全性 → 麦克风”，"
            "开启麦克风访问权限及“允许桌面应用访问麦克风”，并确认没有其他"
            "程序独占麦克风。详细信息：{error}"
        ),
        "audio_failed": "音频设备无法启动：{error}",
    },
    "en": {
        "missing_key": "Save an OpenAI API key first",
        "missing_components": "Realtime voice components are not installed",
        "connecting": "Connecting…",
        "disconnected": "Disconnected",
        "listening": "Connected and listening",
        "empty_transcript": "No usable transcript was received; this turn will not reply",
        "transcription_failed": "Transcription failed; this turn will not reply: {error}",
        "realtime_api_error": "A Realtime API error occurred",
        "generic_error": "Realtime error: {error}",
        "microphone_status": "Microphone status: {status}",
        "sender_lag": "Microphone processing fell behind; the oldest audio was dropped to restore real-time operation",
        "response_too_long": (
            "The Realtime response exceeded the 32,768-character safety limit; "
            "this response was stopped."
        ),
        "playback_buffer_full": (
            "The Realtime playback buffer reached its 1.5-second safety limit; "
            "this response was stopped to prevent growing delay or skipped words."
        ),
        "playback_failed": "Speech playback failed: {error}",
        "clip_too_short": "The speech clip was too short; this turn will not reply",
        "transcribing": "Transcribing the complete utterance…",
        "hybrid_failed": "High-accuracy transcription failed; this turn will not reply: {error}",
        "response_not_started": "Text was recognized, but the Realtime response could not be started",
        "prompt_echo_skipped": "A probable transcription-prompt echo was skipped",
        "replying": "Recognized; MoHan is replying",
        "model_access": (
            "The saved OpenAI API key cannot access “{model}”. Confirm that the "
            "model and API key belong to the same Project, then save a suitably "
            "authorized key again in MoHan Settings."
        ),
        "quota": (
            "The OpenAI API quota is insufficient or the project budget limit "
            "was reached. Check Billing, Budget, and Realtime model usage limits."
        ),
        "invalid_key": (
            "The saved OpenAI API key is invalid or revoked. Save a new key from "
            "the same Project in Settings."
        ),
        "server_rejected": "The Realtime server rejected the connection. Details: {error}",
        "microphone_failed": (
            "Windows could not open the microphone. In Settings → Privacy & "
            "security → Microphone, enable microphone access and desktop-app "
            "access, and confirm that no other program has exclusive control. "
            "Details: {error}"
        ),
        "audio_failed": "The audio device could not start: {error}",
    },
    "ja-JP": {
        "missing_key": "先に OpenAI API キーを保存してください",
        "missing_components": "Realtime 音声コンポーネントがインストールされていません",
        "connecting": "接続中…",
        "disconnected": "未接続",
        "listening": "接続済み、聞いています",
        "empty_transcript": "有効な文字起こしを取得できなかったため、このターンには応答しません",
        "transcription_failed": "文字起こしに失敗したため、このターンには応答しません：{error}",
        "realtime_api_error": "Realtime API でエラーが発生しました",
        "generic_error": "Realtime エラー：{error}",
        "microphone_status": "マイクの状態：{status}",
        "sender_lag": "マイク処理が遅れたため、リアルタイム性を戻すために最も古い音声を破棄しました",
        "response_too_long": (
            "Realtime の応答が 32,768 文字の安全上限を超えたため、"
            "この応答を停止しました。"
        ),
        "playback_buffer_full": (
            "Realtime の再生バッファーが 1.5 秒の安全上限に達したため、"
            "遅延の増加や語の欠落を防ぐためにこの応答を停止しました。"
        ),
        "playback_failed": "音声の再生に失敗しました：{error}",
        "clip_too_short": "音声区間が短すぎるため、このターンには応答しません",
        "transcribing": "発話全体を高精度で文字起こししています…",
        "hybrid_failed": "高精度文字起こしに失敗したため、このターンには応答しません：{error}",
        "response_not_started": "文字は認識されましたが、Realtime の応答を開始できませんでした",
        "prompt_echo_skipped": "文字起こしプロンプトの反響と思われる内容を除外しました",
        "replying": "認識しました。墨寒が応答しています",
        "model_access": (
            "保存された OpenAI API キーでは「{model}」を利用できません。"
            "モデルと API キーが同じ Project に属することを確認し、適切な権限を"
            "持つキーを墨寒の設定で保存し直してください。"
        ),
        "quota": (
            "OpenAI API の利用枠が不足しているか、プロジェクトの予算上限に"
            "達しました。Billing、Budget、Realtime モデルの利用上限を確認してください。"
        ),
        "invalid_key": (
            "保存された OpenAI API キーは無効か、取り消されています。"
            "同じ Project で新しいキーを作成し、設定で保存し直してください。"
        ),
        "server_rejected": "Realtime サーバーが接続を拒否しました。詳細：{error}",
        "microphone_failed": (
            "Windows でマイクを開けませんでした。「設定 → プライバシーと"
            "セキュリティ → マイク」でマイクとデスクトップアプリのアクセスを"
            "有効にし、他のプログラムがマイクを占有していないことを確認して"
            "ください。詳細：{error}"
        ),
        "audio_failed": "音声デバイスを開始できませんでした：{error}",
    },
})


def _realtime_message(
    locale: str,
    key: str,
    **values: object,
) -> str:
    catalog = _REALTIME_MESSAGES[canonical_ui_language(locale)]
    message = catalog[key]
    return message.format(**values) if values else message


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
    output_text_started = Signal(int)
    output_text_delta = Signal(int, str)
    output_text_done = Signal(int)
    output_interrupted = Signal(int)
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
                RealtimeVoiceClient
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
        except Exception as exc:  # noqa: BLE001 -- audio startup reports all failures
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
                and len(value) <= 40
                and not re.prefixmatch(
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
        if len(self._terminal_response_order) >= 256:
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
                            _realtime_message(self._locale, "sender_lag")
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
        if len(pcm) < 24000:
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
        except Exception as exc:  # noqa: BLE001 -- transcription returns diagnostics
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
        if not self.native_audio_output:
            self._prepare_external_response()
        try:
            response: dict[str, Any] = {"type": "response.create"}
            if not self.native_audio_output:
                response["response"] = {"output_modalities": ["text"]}
            ws.send(json.dumps(response))
        except Exception:  # noqa: BLE001 -- failed request clears pending state
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
