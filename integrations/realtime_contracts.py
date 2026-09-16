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
        "missing_components": "請安裝 Realtime 語音元件",
        "connecting": "正在連線…",
        "disconnected": "目前等待連線，請重新啟動 Realtime",
        "listening": "已連線，妾在聽",
        "empty_transcript": "轉錄結果為空，本輪等待新的語音",
        "transcription_failed": "轉錄結果需要重試，本輪等待新的語音：{error}",
        "realtime_api_error": "Realtime API 回報錯誤，請檢查設定後再試",
        "generic_error": "Realtime 回報錯誤：{error}",
        "microphone_status": "麥克風狀態：{status}",
        "sender_lag": "麥克風處理已恢復即時性，已捨棄較早音訊",
        "response_too_long": (
            "Realtime 回應達到 32,768 字元安全上限，本輪回應已停止。"
        ),
        "playback_buffer_full": (
            "Realtime 播放緩衝達到 1.5 秒安全上限，本輪語音已停止，"
            "以維持延遲與文字同步。"
        ),
        "playback_failed": "播放語音需要重試：{error}",
        "clip_too_short": "語音片段長度需要增加，本輪等待新的語音",
        "transcribing": "高精度整句轉錄中…",
        "hybrid_failed": "高精度轉錄需要重試，本輪等待新的語音：{error}",
        "response_not_started": "文字已辨識；Realtime 回覆尚待啟動，請檢查連線後再試",
        "prompt_echo_skipped": "已過濾疑似轉錄提示詞回灌內容，等待實際語音輸入",
        "replying": "已辨識，墨寒正在回覆",
        "model_access": (
            "OpenAI 回報目前儲存的 API 金鑰需要在同一 Project 啟用「{model}」使用權限。"
            "請確認 API 後台勾選模型的 Project，正是建立這支金鑰的同一個 "
            "Project；再於該 Project 建立具適當權限的 API Key，並到墨寒的"
            "「設定」頁重新儲存。"
        ),
        "quota": (
            "OpenAI API 額度需要補充，或專案預算已達上限。請檢查該 Project 的 "
            "Billing、Budget 與 Realtime 模型用量限制。"
        ),
        "invalid_key": (
            "目前儲存的 OpenAI API 金鑰需要更新。"
            "請到「設定」頁貼上同一 Project 新建立的 API Key。"
        ),
        "server_rejected": "Realtime 伺服器回報連線狀態需要重新建立。詳細資訊：{error}",
        "microphone_failed": (
            "Windows 麥克風存取需要處理。請到「設定 → 隱私權與安全性 → 麥克風」，"
            "開啟麥克風存取權及「讓桌面應用程式存取麥克風」，並釋放其他程式"
            "持有的獨佔麥克風控制權，讓本程式取得使用權。詳細資訊：{error}"
        ),
        "audio_failed": "音訊裝置尚待啟動：{error}。請到「設定」頁重新選擇輸入／輸出裝置後再試。",
    },
    "zh-CN": {
        "missing_key": "请先保存 OpenAI API 密钥",
        "missing_components": "请安装 Realtime 语音组件",
        "connecting": "正在连接…",
        "disconnected": "当前等待连接，请重新启动 Realtime",
        "listening": "已连接，妾在听",
        "empty_transcript": "转录结果为空，本轮等待新的语音",
        "transcription_failed": "转录结果需要重试，本轮等待新的语音：{error}",
        "realtime_api_error": "Realtime API 报告错误，请检查设置后再试",
        "generic_error": "Realtime 报告错误：{error}",
        "microphone_status": "麦克风状态：{status}",
        "sender_lag": "麦克风处理已恢复实时性，已舍弃较早音频",
        "response_too_long": (
            "Realtime 回复达到 32,768 字符安全上限，本轮回复已停止。"
        ),
        "playback_buffer_full": (
            "Realtime 播放缓冲达到 1.5 秒安全上限，本轮语音已停止，"
            "以维持延迟与文字同步。"
        ),
        "playback_failed": "播放语音需要重试：{error}",
        "clip_too_short": "语音片段长度需要增加，本轮等待新的语音",
        "transcribing": "高精度整句转录中…",
        "hybrid_failed": "高精度转录需要重试，本轮等待新的语音：{error}",
        "response_not_started": "文字已识别；Realtime 回复尚待启动，请检查连接后再试",
        "prompt_echo_skipped": "已过滤疑似转录提示词回灌内容，等待实际语音输入",
        "replying": "已识别，墨寒正在回复",
        "model_access": (
            "OpenAI 报告当前保存的 API 密钥需要在同一 Project 启用“{model}”使用权限。"
            "请确认 API 后台所选模型的 Project 与建立这支密钥的 Project 相同；"
            "再于该 Project 建立具备适当权限的 API Key，并到墨寒的“设置”页"
            "重新保存。"
        ),
        "quota": (
            "OpenAI API 额度需要补充，或项目预算已达上限。请检查该 Project 的 "
            "Billing、Budget 与 Realtime 模型用量限制。"
        ),
        "invalid_key": (
            "当前保存的 OpenAI API 密钥需要更新。"
            "请到“设置”页粘贴同一 Project 新建立的 API Key。"
        ),
        "server_rejected": "Realtime 服务器报告连接状态需要重新建立。详细信息：{error}",
        "microphone_failed": (
            "Windows 麦克风访问需要处理。请到“设置 → 隐私和安全性 → 麦克风”，"
            "开启麦克风访问权限及“允许桌面应用访问麦克风”，并释放其他程序"
            "持有的独占麦克风控制权，让本程序取得使用权。详细信息：{error}"
        ),
        "audio_failed": "音频设备尚待启动：{error}。请到「设置」页重新选择输入／输出设备后再试。",
    },
    "en": {
        "missing_key": "Save an OpenAI API key first",
        "missing_components": "Install the Realtime voice components",
        "connecting": "Connecting…",
        "disconnected": "Waiting for a connection; restart Realtime",
        "listening": "Connected and listening",
        "empty_transcript": "The transcript is empty; this turn is waiting for new audio",
        "transcription_failed": "The transcript needs a retry; this turn is waiting for new audio: {error}",
        "realtime_api_error": "The Realtime API reported an error; check Settings and try again",
        "generic_error": "Realtime reported an error: {error}",
        "microphone_status": "Microphone status: {status}",
        "sender_lag": "Microphone processing is real-time again; earlier audio was dropped",
        "response_too_long": (
            "The Realtime response reached the 32,768-character safety limit; "
            "this response is stopped."
        ),
        "playback_buffer_full": (
            "The Realtime playback buffer reached its 1.5-second safety limit; "
            "this response is stopped to keep delay and text synchronized."
        ),
        "playback_failed": "Speech playback needs a retry: {error}",
        "clip_too_short": "The speech clip needs more audio; this turn is waiting for new audio",
        "transcribing": "Transcribing the complete utterance…",
        "hybrid_failed": "High-accuracy transcription needs a retry; this turn is waiting for new audio: {error}",
        "response_not_started": "Text was recognized; the Realtime response is waiting to start. Check the connection and try again",
        "prompt_echo_skipped": "Filtered probable transcription-prompt echo content; waiting for actual voice input",
        "replying": "Recognized; MoHan is replying",
        "model_access": (
            "Enable “{model}” access for the saved OpenAI API key in the same Project. Confirm that the "
            "model and API key belong to the same Project, then save a suitably "
            "authorized key again in MoHan Settings."
        ),
        "quota": (
            "The OpenAI API quota needs replenishment or the project budget limit "
            "was reached. Check Billing, Budget, and Realtime model usage limits."
        ),
        "invalid_key": (
            "The saved OpenAI API key needs an update. Save a new key from the same "
            "Project in Settings."
        ),
        "server_rejected": "The Realtime server reported a connection state that needs to be re-established. Details: {error}",
        "microphone_failed": (
            "Microphone access requires attention. In Settings → Privacy & security "
            "→ Microphone, enable microphone access and desktop-app access, and "
            "release exclusive microphone control held by other apps so this app can use it. "
            "Details: {error}"
        ),
        "audio_failed": "The audio device is waiting to start: {error}. Please reselect the input/output device on the Settings page and try again.",
    },
    "ja-JP": {
        "missing_key": "先に OpenAI API キーを保存してください",
        "missing_components": "Realtime 音声コンポーネントをインストールしてください",
        "connecting": "接続中…",
        "disconnected": "接続待機中です。Realtime を再起動してください",
        "listening": "接続済み、聞いています",
        "empty_transcript": "文字起こし結果が空のため、このターンは新しい音声を待機します",
        "transcription_failed": "文字起こし結果の再試行が必要です。このターンは新しい音声を待機します：{error}",
        "realtime_api_error": "Realtime API がエラーを報告しました。設定を確認して再試行してください",
        "generic_error": "Realtime がエラーを報告しました：{error}",
        "microphone_status": "マイクの状態：{status}",
        "sender_lag": "マイク処理がリアルタイムに戻りました。古い音声を整理しました",
        "response_too_long": (
            "Realtime の応答が 32,768 文字の安全上限に達したため、"
            "この応答を停止します。"
        ),
        "playback_buffer_full": (
            "Realtime の再生バッファーが 1.5 秒の安全上限に達したため、"
            "遅延と文字の同期を保つためにこの応答を停止します。"
        ),
        "playback_failed": "音声の再生に再試行が必要です：{error}",
        "clip_too_short": "音声区間に追加の音声が必要なため、このターンは新しい音声を待機します",
        "transcribing": "発話全体を高精度で文字起こししています…",
        "hybrid_failed": "高精度文字起こしの再試行が必要です。このターンは新しい音声を待機します：{error}",
        "response_not_started": "文字を認識しました。Realtime の応答は開始待ちです。接続を確認して再試行してください",
        "prompt_echo_skipped": "文字起こしプロンプトの反響と思われる内容を除外し、実際の音声入力を待機しています",
        "replying": "認識しました。墨寒が応答しています",
        "model_access": (
            "保存された OpenAI API キーで「{model}」を利用する権限を同じ Project に設定してください。"
            "モデルと API キーが同じ Project に属することを確認し、適切な権限を"
            "持つキーを墨寒の設定で保存してください。"
        ),
        "quota": (
            "OpenAI API の利用枠の補充が必要か、プロジェクトの予算上限に"
            "達しました。Billing、Budget、Realtime モデルの利用上限を確認してください。"
        ),
        "invalid_key": (
            "保存された OpenAI API キーの更新が必要です。"
            "同じ Project で新しいキーを作成し、設定で保存してください。"
        ),
        "server_rejected": "Realtime サーバーが接続状態の再確立を報告しました。詳細：{error}",
        "microphone_failed": (
            "Windows のマイクアクセスには対応が必要です。「設定 → プライバシーと"
            "セキュリティ → マイク」でマイクとデスクトップアプリのアクセスを"
            "有効にし、他のアプリが保持するマイクの排他的制御を解放して、この"
            "アプリがマイクを利用できる状態にしてください。詳細：{error}"
        ),
        "audio_failed": "音声デバイスは開始待ちです：{error}。「設定」ページで入出力デバイスを選び直してから再試行してください。",
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
