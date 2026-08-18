from __future__ import annotations

lazy from dataclasses import dataclass, field

lazy from domain.audio_buffer import BoundedAudioQueue
lazy from domain.immutable_config import deep_freeze
lazy from domain.language_support import canonical_ui_language
lazy from integrations.realtime_speech_output import REALTIME_OUTPUT_OPENAI


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
        "audio_failed": "音訊裝置無法啟動：{error}。請到「設定」頁重新選擇輸入／輸出裝置後再試。",
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
        "audio_failed": "音频设备无法启动：{error}。请到「设置」页重新选择输入／输出设备后再试。",
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
        "audio_failed": "The audio device could not start: {error}. Please reselect the input/output device on the Settings page and try again.",
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
        "audio_failed": "音声デバイスを開始できませんでした：{error}。「設定」ページで入出力デバイスを選び直してから再試行してください。",
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
