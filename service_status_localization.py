from __future__ import annotations

lazy from collections.abc import Mapping
lazy from enum import StrEnum
lazy from string import Formatter

lazy from language_support import canonical_ui_language
lazy from safe_error import SafeError, sanitize_error


class ServiceStatus(StrEnum):
    """User-facing status and error messages emitted by backend services."""

    AI_PLANNING = "ai_planning"
    AI_PLANNER_KEY_MISSING = "ai_planner_key_missing"
    AI_PLAN_RESPONSE_MISSING = "ai_plan_response_missing"
    AI_PLAN_FORMAT_INVALID = "ai_plan_format_invalid"
    AI_PLAN_STEP_INVALID = "ai_plan_step_invalid"
    AI_PLAN_ARGUMENTS_INVALID = "ai_plan_arguments_invalid"
    AI_RESPONSE_EMPTY = "ai_response_empty"
    CAMERA_COMPONENT_UNAVAILABLE = "camera_component_unavailable"
    CAMERA_NOT_FOUND = "camera_not_found"
    CAMERA_STARTING = "camera_starting"
    CAMERA_ERROR = "camera_error"
    CAMERA_ACTIVE = "camera_active"
    CAMERA_CLOSED = "camera_closed"
    SPEECH_EMPTY_MANUAL_CAPTURE = "speech_empty_manual_capture"
    SPEECH_NOT_DETECTED = "speech_not_detected"
    SPEECH_OPENAI_KEY_INVALID = "speech_openai_key_invalid"
    SPEECH_OPENAI_NOT_AUTHORIZED = "speech_openai_not_authorized"
    SPEECH_OPENAI_MODEL_NOT_FOUND = "speech_openai_model_not_found"
    SPEECH_OPENAI_QUOTA_EXHAUSTED = "speech_openai_quota_exhausted"
    SPEECH_OPENAI_RATE_LIMITED = "speech_openai_rate_limited"
    SPEECH_OPENAI_SERVICE_ERROR = "speech_openai_service_error"
    SPEECH_OPENAI_HTTP_ERROR = "speech_openai_http_error"
    SPEECH_OPENAI_CONNECTION_ERROR = "speech_openai_connection_error"
    SPEECH_OPENAI_TIMEOUT = "speech_openai_timeout"
    SPEECH_OPENAI_EMPTY_RESULT = "speech_openai_empty_result"
    SPEECH_PLAYBACK_UNAVAILABLE = "speech_playback_unavailable"
    SPEECH_WINDOWS_FEMALE_VOICE_MISSING = (
        "speech_windows_female_voice_missing"
    )
    SPEECH_WINDOWS_LEGACY_FAILED = "speech_windows_legacy_failed"
    SPEECH_ONECORE_VOICE_MISSING = "speech_onecore_voice_missing"
    SPEECH_ONECORE_FAILED = "speech_onecore_failed"
    SPEECH_WINDOWS_SYNTHESIS_TIMEOUT = (
        "speech_windows_synthesis_timeout"
    )
    SPEECH_WINDOWS_WAV_UNSUPPORTED = "speech_windows_wav_unsupported"
    SPEECH_OPENAI_KEY_MISSING = "speech_openai_key_missing"
    SPEECH_CAPTURE_STOPPING = "speech_capture_stopping"
    SPEECH_OPENAI_KEY_MISSING_SENTENCE = (
        "speech_openai_key_missing_sentence"
    )
    SPEECH_WINDOWS_FALLBACK_DISABLED = (
        "speech_windows_fallback_disabled"
    )
    SPEECH_RECORDING = "speech_recording"
    SPEECH_RECOGNITION_START_FAILED = (
        "speech_recognition_start_failed"
    )
    SPEECH_WINDOWS_LISTENING = "speech_windows_listening"
    SPEECH_WINDOWS_FALLBACK = "speech_windows_fallback"
    SPEECH_RECORDING_COMPONENT_MISSING = (
        "speech_recording_component_missing"
    )
    SPEECH_WINDOWS_MICROPHONE_ERROR = "speech_windows_microphone_error"
    SPEECH_RECOGNIZING = "speech_recognizing"
    SPEECH_TRANSCRIPTION_SUCCEEDED = "speech_transcription_succeeded"
    SPEECH_WINDOWS_RECOGNIZER_MISSING = (
        "speech_windows_recognizer_missing"
    )
    SPEECH_WINDOWS_MICROPHONE_DENIED = (
        "speech_windows_microphone_denied"
    )
    SPEECH_WINDOWS_RECOGNITION_ERROR = (
        "speech_windows_recognition_error"
    )
    SPEECH_WINDOWS_RECOGNITION_START_ERROR = (
        "speech_windows_recognition_start_error"
    )
    SPEECH_NOT_UNDERSTOOD = "speech_not_understood"


SUPPORTED_SERVICE_LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")


def _text(
    traditional_chinese: str,
    simplified_chinese: str,
    english: str,
    japanese: str,
) -> Mapping[str, str]:
    return frozendict({
        "zh-TW": traditional_chinese,
        "zh-CN": simplified_chinese,
        "en": english,
        "ja-JP": japanese,
    })


_TEXT: Mapping[ServiceStatus, Mapping[str, str]] = frozendict({
    ServiceStatus.AI_PLANNING: _text(
        "規劃中…",
        "规划中…",
        "Planning…",
        "計画を作成中…",
    ),
    ServiceStatus.AI_PLANNER_KEY_MISSING: _text(
        "尚未設定 OpenAI API 金鑰，無法理解自由語句工具任務",
        "尚未设置 OpenAI API 密钥，无法理解自由语句工具任务",
        "The OpenAI API key is not configured, so free-form tool requests cannot be understood",
        "OpenAI API キーが未設定のため、自由文によるツール操作を理解できません",
    ),
    ServiceStatus.AI_PLAN_RESPONSE_MISSING: _text(
        "API 未傳回唯一的安全任務計畫",
        "API 未返回唯一的安全任务计划",
        "The API did not return exactly one safe task plan",
        "API から安全なタスク計画が一つだけ返されませんでした",
    ),
    ServiceStatus.AI_PLAN_FORMAT_INVALID: _text(
        "任務計畫格式錯誤",
        "任务计划格式错误",
        "The task plan format is invalid",
        "タスク計画の形式が正しくありません",
    ),
    ServiceStatus.AI_PLAN_STEP_INVALID: _text(
        "任務步驟格式錯誤",
        "任务步骤格式错误",
        "A task step has an invalid format",
        "タスク手順の形式が正しくありません",
    ),
    ServiceStatus.AI_PLAN_ARGUMENTS_INVALID: _text(
        "工具參數必須是 JSON 物件",
        "工具参数必须是 JSON 对象",
        "Tool arguments must be a JSON object",
        "ツール引数は JSON オブジェクトでなければなりません",
    ),
    ServiceStatus.AI_RESPONSE_EMPTY: _text(
        "API 沒有傳回文字",
        "API 没有返回文字",
        "The API returned no text",
        "API からテキストが返されませんでした",
    ),
    ServiceStatus.CAMERA_COMPONENT_UNAVAILABLE: _text(
        "此封裝未包含 QtMultimedia 攝影機元件",
        "此软件包未包含 QtMultimedia 摄像头组件",
        "This package does not include the QtMultimedia camera component",
        "このパッケージには QtMultimedia カメラコンポーネントが含まれていません",
    ),
    ServiceStatus.CAMERA_NOT_FOUND: _text(
        "找不到可用攝影機",
        "找不到可用摄像头",
        "No available camera was found",
        "利用可能なカメラが見つかりません",
    ),
    ServiceStatus.CAMERA_STARTING: _text(
        "正在啟動攝影機…",
        "正在启动摄像头…",
        "Starting camera…",
        "カメラを起動中…",
    ),
    ServiceStatus.CAMERA_ERROR: _text(
        "攝影機錯誤：{detail}",
        "摄像头错误：{detail}",
        "Camera error: {detail}",
        "カメラエラー：{detail}",
    ),
    ServiceStatus.CAMERA_ACTIVE: _text(
        "攝影機使用中：{device}（僅本機在場偵測）",
        "摄像头使用中：{device}（仅用于本地在场检测）",
        "Camera active: {device} (local presence detection only)",
        "カメラ使用中：{device}（本機内の在席検知のみ）",
    ),
    ServiceStatus.CAMERA_CLOSED: _text(
        "攝影機已關閉",
        "摄像头已关闭",
        "Camera closed",
        "カメラを停止しました",
    ),
    ServiceStatus.SPEECH_EMPTY_MANUAL_CAPTURE: _text(
        "尚未偵測到說話聲，沒有送出空白錄音。",
        "尚未检测到说话声，没有提交空白录音。",
        "No speech was detected, so an empty recording was not submitted.",
        "発話を検出していないため、空の録音は送信しませんでした。",
    ),
    ServiceStatus.SPEECH_NOT_DETECTED: _text(
        "沒有偵測到說話聲，請靠近麥克風後再試一次。",
        "没有检测到说话声，请靠近麦克风后再试一次。",
        "No speech was detected. Move closer to the microphone and try again.",
        "発話を検出できませんでした。マイクに近づいて、もう一度お試しください。",
    ),
    ServiceStatus.SPEECH_OPENAI_KEY_INVALID: _text(
        "OpenAI API 金鑰無效或已被撤銷（HTTP 401）。",
        "OpenAI API 密钥无效或已被撤销（HTTP 401）。",
        "The OpenAI API key is invalid or has been revoked (HTTP 401).",
        "OpenAI API キーが無効であるか、取り消されています（HTTP 401）。",
    ),
    ServiceStatus.SPEECH_OPENAI_NOT_AUTHORIZED: _text(
        "OpenAI Project 未授權使用語音轉錄（HTTP 403）。",
        "OpenAI Project 未获授权使用语音转录（HTTP 403）。",
        "The OpenAI Project is not authorized to use speech transcription (HTTP 403).",
        "OpenAI Project には音声文字起こしを使用する権限がありません（HTTP 403）。",
    ),
    ServiceStatus.SPEECH_OPENAI_MODEL_NOT_FOUND: _text(
        "OpenAI 找不到轉錄模型，或此 Project 無權使用（HTTP 404）。",
        "OpenAI 找不到转录模型，或此 Project 无权使用（HTTP 404）。",
        "OpenAI could not find the transcription model, or this Project cannot use it (HTTP 404).",
        "OpenAI で文字起こしモデルが見つからないか、この Project に利用権限がありません（HTTP 404）。",
    ),
    ServiceStatus.SPEECH_OPENAI_QUOTA_EXHAUSTED: _text(
        "OpenAI API 額度不足或尚未啟用計費（HTTP 429）。",
        "OpenAI API 额度不足或尚未启用计费（HTTP 429）。",
        "The OpenAI API quota is insufficient or billing is not enabled (HTTP 429).",
        "OpenAI API の利用枠が不足しているか、課金が有効になっていません（HTTP 429）。",
    ),
    ServiceStatus.SPEECH_OPENAI_RATE_LIMITED: _text(
        "OpenAI 語音轉錄請求過於頻繁，已達速率限制（HTTP 429）。",
        "OpenAI 语音转录请求过于频繁，已达到速率限制（HTTP 429）。",
        "OpenAI speech transcription requests reached the rate limit (HTTP 429).",
        "OpenAI 音声文字起こしのリクエストがレート制限に達しました（HTTP 429）。",
    ),
    ServiceStatus.SPEECH_OPENAI_SERVICE_ERROR: _text(
        "OpenAI 語音轉錄服務暫時異常（HTTP {status}）。",
        "OpenAI 语音转录服务暂时异常（HTTP {status}）。",
        "The OpenAI speech transcription service is temporarily unavailable (HTTP {status}).",
        "OpenAI 音声文字起こしサービスで一時的な障害が発生しています（HTTP {status}）。",
    ),
    ServiceStatus.SPEECH_OPENAI_HTTP_ERROR: _text(
        "OpenAI 轉錄失敗（HTTP {status}）：{detail}",
        "OpenAI 转录失败（HTTP {status}）：{detail}",
        "OpenAI transcription failed (HTTP {status}): {detail}",
        "OpenAI の文字起こしに失敗しました（HTTP {status}）：{detail}",
    ),
    ServiceStatus.SPEECH_OPENAI_CONNECTION_ERROR: _text(
        "無法連線到 OpenAI：{detail}",
        "无法连接到 OpenAI：{detail}",
        "Could not connect to OpenAI: {detail}",
        "OpenAI に接続できません：{detail}",
    ),
    ServiceStatus.SPEECH_OPENAI_TIMEOUT: _text(
        "OpenAI 轉錄連線逾時。",
        "OpenAI 转录连接超时。",
        "The OpenAI transcription connection timed out.",
        "OpenAI 文字起こしへの接続がタイムアウトしました。",
    ),
    ServiceStatus.SPEECH_OPENAI_EMPTY_RESULT: _text(
        "OpenAI 已成功連線，但沒有從這段錄音辨識出文字。",
        "OpenAI 已成功连接，但没有从这段录音中识别出文字。",
        "OpenAI connected successfully but recognized no text in this recording.",
        "OpenAI への接続には成功しましたが、この録音からテキストを認識できませんでした。",
    ),
    ServiceStatus.SPEECH_PLAYBACK_UNAVAILABLE: _text(
        "此平台的音訊播放介面尚未完成實機驗證；未播放這段語音。",
        "此平台的音频播放接口尚未完成真机验证；未播放这段语音。",
        "Audio playback on this platform has not completed real-device validation; this speech was not played.",
        "このプラットフォームの音声再生機能は実機検証が完了していないため、この音声は再生しませんでした。",
    ),
    ServiceStatus.SPEECH_WINDOWS_FEMALE_VOICE_MISSING: _text(
        "Windows 沒有偵測到已明確標示為女性的本機語音。",
        "Windows 未检测到明确标记为女性的本地语音。",
        "Windows did not detect a local voice explicitly marked as female.",
        "Windows で女性と明示された本機音声を検出できませんでした。",
    ),
    ServiceStatus.SPEECH_WINDOWS_LEGACY_FAILED: _text(
        "Windows 傳統語音播放失敗。",
        "Windows 传统语音播放失败。",
        "Windows legacy speech playback failed.",
        "Windows の従来音声の再生に失敗しました。",
    ),
    ServiceStatus.SPEECH_ONECORE_VOICE_MISSING: _text(
        "找不到 OneCore 聲音：{voice}",
        "找不到 OneCore 声音：{voice}",
        "OneCore voice not found: {voice}",
        "OneCore 音声が見つかりません：{voice}",
    ),
    ServiceStatus.SPEECH_ONECORE_FAILED: _text(
        "OneCore 語音合成失敗。",
        "OneCore 语音合成失败。",
        "OneCore speech synthesis failed.",
        "OneCore 音声合成に失敗しました。",
    ),
    ServiceStatus.SPEECH_WINDOWS_SYNTHESIS_TIMEOUT: _text(
        "Windows 本機語音合成逾時。",
        "Windows 本地语音合成超时。",
        "Windows local speech synthesis timed out.",
        "Windows 本機音声の合成がタイムアウトしました。",
    ),
    ServiceStatus.SPEECH_WINDOWS_WAV_UNSUPPORTED: _text(
        "Windows 本機語音回傳了不支援的 WAV 格式。",
        "Windows 本地语音返回了不支持的 WAV 格式。",
        "Windows local speech returned an unsupported WAV format.",
        "Windows 本機音声から未対応の WAV 形式が返されました。",
    ),
    ServiceStatus.SPEECH_OPENAI_KEY_MISSING: _text(
        "尚未設定 OpenAI API 金鑰",
        "尚未设置 OpenAI API 密钥",
        "The OpenAI API key has not been configured",
        "OpenAI API キーが設定されていません",
    ),
    ServiceStatus.SPEECH_CAPTURE_STOPPING: _text(
        "正在結束收音並送出…",
        "正在结束收音并提交…",
        "Finishing audio capture and submitting…",
        "収音を終了して送信中…",
    ),
    ServiceStatus.SPEECH_OPENAI_KEY_MISSING_SENTENCE: _text(
        "未設定 OpenAI API 金鑰。",
        "未设置 OpenAI API 密钥。",
        "The OpenAI API key has not been configured.",
        "OpenAI API キーが設定されていません。",
    ),
    ServiceStatus.SPEECH_WINDOWS_FALLBACK_DISABLED: _text(
        "Windows 備援目前已關閉。",
        "Windows 备用识别目前已关闭。",
        "Windows fallback recognition is currently disabled.",
        "Windows 代替認識は現在無効です。",
    ),
    ServiceStatus.SPEECH_RECORDING: _text(
        "收音中…再次點擊麥克風可立即送出",
        "收音中…再次点击麦克风可立即提交",
        "Listening… Click the microphone again to submit now",
        "収音中…マイクをもう一度押すと、すぐに送信します",
    ),
    ServiceStatus.SPEECH_RECOGNITION_START_FAILED: _text(
        "無法啟動語音辨識",
        "无法启动语音识别",
        "Could not start speech recognition",
        "音声認識を開始できません",
    ),
    ServiceStatus.SPEECH_WINDOWS_LISTENING: _text(
        "收音與辨識中…",
        "收音与识别中…",
        "Listening and recognizing…",
        "収音して認識中…",
    ),
    ServiceStatus.SPEECH_WINDOWS_FALLBACK: _text(
        "{detail} 正在使用 Windows 備援辨識…",
        "{detail} 正在使用 Windows 备用识别…",
        "{detail} Using Windows fallback recognition…",
        "{detail} Windows 代替認識を使用中…",
    ),
    ServiceStatus.SPEECH_RECORDING_COMPONENT_MISSING: _text(
        "缺少麥克風錄音元件 sounddevice。",
        "缺少麦克风录音组件 sounddevice。",
        "The sounddevice microphone recording component is missing.",
        "マイク録音コンポーネント sounddevice がありません。",
    ),
    ServiceStatus.SPEECH_WINDOWS_MICROPHONE_ERROR: _text(
        "無法使用 Windows 預設麥克風：{detail}",
        "无法使用 Windows 默认麦克风：{detail}",
        "Could not use the Windows default microphone: {detail}",
        "Windows の既定のマイクを使用できません：{detail}",
    ),
    ServiceStatus.SPEECH_RECOGNIZING: _text(
        "辨識中…",
        "识别中…",
        "Recognizing…",
        "認識中…",
    ),
    ServiceStatus.SPEECH_TRANSCRIPTION_SUCCEEDED: _text(
        "OpenAI 轉錄成功：{model}",
        "OpenAI 转录成功：{model}",
        "OpenAI transcription succeeded: {model}",
        "OpenAI の文字起こしに成功しました：{model}",
    ),
    ServiceStatus.SPEECH_WINDOWS_RECOGNIZER_MISSING: _text(
        "Windows 尚未安裝中文語音辨識套件，請先在語言設定加入中文語音功能。",
        "Windows 尚未安装中文语音识别包，请先在语言设置中添加中文语音功能。",
        "Windows does not have the Chinese speech recognition package installed. Add Chinese speech in Language settings first.",
        "Windows に中国語音声認識パッケージがありません。先に言語設定で中国語の音声機能を追加してください。",
    ),
    ServiceStatus.SPEECH_WINDOWS_MICROPHONE_DENIED: _text(
        "Windows 拒絕墨寒使用麥克風。請到「設定 → 隱私權與安全性 → 麥克風」，開啟麥克風存取權、讓應用程式存取麥克風，以及讓桌面應用程式存取麥克風。",
        "Windows 拒绝墨寒使用麦克风。请前往“设置 → 隐私和安全性 → 麦克风”，开启麦克风访问权限、允许应用访问麦克风，以及允许桌面应用访问麦克风。",
        "Windows denied MoHan access to the microphone. In Settings → Privacy & security → Microphone, enable Microphone access, Let apps access your microphone, and Let desktop apps access your microphone.",
        "Windows が墨寒のマイク使用を拒否しました。「設定 → プライバシーとセキュリティ → マイク」で、マイクへのアクセス、アプリのマイクアクセス、デスクトップアプリのマイクアクセスを有効にしてください。",
    ),
    ServiceStatus.SPEECH_WINDOWS_RECOGNITION_ERROR: _text(
        "Windows 語音辨識無法使用：{detail}",
        "Windows 语音识别无法使用：{detail}",
        "Windows speech recognition is unavailable: {detail}",
        "Windows 音声認識を使用できません：{detail}",
    ),
    ServiceStatus.SPEECH_WINDOWS_RECOGNITION_START_ERROR: _text(
        "Windows 語音辨識啟動失敗：{detail}",
        "Windows 语音识别启动失败：{detail}",
        "Windows speech recognition failed to start: {detail}",
        "Windows 音声認識の起動に失敗しました：{detail}",
    ),
    ServiceStatus.SPEECH_NOT_UNDERSTOOD: _text(
        "寒方才未聽清，請再說一次。",
        "寒刚才没有听清，请再说一次。",
        "I did not hear that clearly. Please try again.",
        "よく聞き取れませんでした。もう一度お話しください。",
    ),
})


def _format_fields(template: str) -> frozenset[str]:
    return frozenset(
        field_name
        for _literal, field_name, _format_spec, _conversion
        in Formatter().parse(template)
        if field_name is not None
    )


def _validate_catalog() -> None:
    expected_languages = tuple(SUPPORTED_SERVICE_LANGUAGES)
    for key, translations in _TEXT.items():
        if tuple(translations) != expected_languages:
            raise RuntimeError(
                f"{key} must define service text in canonical language order"
            )
        expected_fields = _format_fields(translations["zh-TW"])
        for language, template in translations.items():
            if _format_fields(template) != expected_fields:
                raise RuntimeError(
                    f"{key} has inconsistent format fields for {language}"
                )


_validate_catalog()

_UNTRUSTED_DYNAMIC_FIELDS: Mapping[ServiceStatus, frozenset[str]] = frozendict({
    ServiceStatus.CAMERA_ERROR: frozenset({"detail"}),
    ServiceStatus.SPEECH_OPENAI_HTTP_ERROR: frozenset({"detail"}),
    ServiceStatus.SPEECH_OPENAI_CONNECTION_ERROR: frozenset({"detail"}),
    ServiceStatus.SPEECH_WINDOWS_MICROPHONE_ERROR: frozenset({"detail"}),
    ServiceStatus.SPEECH_WINDOWS_RECOGNITION_ERROR: frozenset({"detail"}),
    ServiceStatus.SPEECH_WINDOWS_RECOGNITION_START_ERROR: frozenset({"detail"}),
})


def _sanitized_values(
    key: ServiceStatus,
    values: Mapping[str, object],
) -> dict[str, object]:
    unsafe_fields = _UNTRUSTED_DYNAMIC_FIELDS.get(key, frozenset())
    return {
        name: (
            value
            if isinstance(value, SafeError)
            else sanitize_error(
                value if isinstance(value, BaseException | str) else str(value),
                http_status=(
                    int(values["status"])
                    if key is ServiceStatus.SPEECH_OPENAI_HTTP_ERROR
                    and isinstance(values.get("status"), int)
                    else None
                ),
            )
        )
        if name in unsafe_fields
        else value
        for name, value in values.items()
    }


def service_status(
    language: str,
    key: ServiceStatus,
    /,
    **values: object,
) -> str:
    """Return localized service text without exposing provider diagnostics."""

    locale = canonical_ui_language(language)
    return _TEXT[key][locale].format(**_sanitized_values(key, values))


def append_service_status(
    language: str,
    detail: str,
    key: ServiceStatus,
    *,
    separate: bool = False,
) -> str:
    """Append fixed UI guidance without translating its dynamic detail."""

    separator = (
        " "
        if separate or canonical_ui_language(language) == "en"
        else ""
    )
    return f"{detail}{separator}{service_status(language, key)}"
