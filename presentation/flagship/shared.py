from __future__ import annotations

lazy from dataclasses import dataclass
lazy from typing import Protocol

lazy from application.vision_runtime import VisionReadiness
lazy from domain.companion_proactivity_preferences import (
    CompanionProactivityPreferences,
)
lazy from domain.gesture_configuration import (
    GestureAction,
    GestureConfiguration,
    GestureSample,
)
lazy from domain.openai_vision_preferences import OpenAIVisionPreferences

__all__ = (
    "ASSIST_INTENT_MARKERS",
    "CALENDAR_MARKERS",
    "CALENDAR_WRITE_MARKERS",
    "CHINESE_DAY_COUNTS",
    "CHINESE_MAIL_COUNTS",
    "CORE_PERMISSION_LABELS",
    "DRIVE_MARKERS",
    "DRIVE_WRITE_MARKERS",
    "GESTURE_PERMISSION_CAPABILITIES",
    "GMAIL_MARKERS",
    "GMAIL_SEND_MARKERS",
    "GMAIL_SEND_NEGATIONS",
    "READ_INTENT_MARKERS",
    "FlagshipDraftValues",
    "GestureRecorderPort",
    "UnavailableGestureRecorder",
)

_VISION_HEALTH_TEXTS = frozendict({
    VisionReadiness.READY: frozendict({
        "zh-TW": "靈視環境已就緒",
        "zh-CN": "灵视环境已就绪",
        "en": "Vision is ready",
        "ja-JP": "視覚認識の準備ができました",
    }),
    VisionReadiness.DISABLED: frozendict({
        "zh-TW": "本機視覺感知已停用。",
        "zh-CN": "本地视觉感知已停用。",
        "en": "Local visual perception is disabled.",
        "ja-JP": "ローカル視覚認識は無効です。",
    }),
    VisionReadiness.CAMERA_UNAVAILABLE: frozendict({
        "zh-TW": "攝影機尚未就緒，本機視覺感知保持停用。",
        "zh-CN": "摄像头尚未就绪，本地视觉感知保持停用。",
        "en": "The camera is not ready, so local visual perception remains disabled.",
        "ja-JP": "カメラの準備ができていないため、ローカル視覚認識は無効のままです。",
    }),
    VisionReadiness.ENGINE_UNAVAILABLE: frozendict({
        "zh-TW": "本機視覺引擎無法使用，視覺感知保持停用。",
        "zh-CN": "本地视觉引擎不可用，视觉感知保持停用。",
        "en": "The local vision engine is unavailable, so visual perception remains disabled.",
        "ja-JP": "ローカル視覚エンジンを利用できないため、視覚認識は無効のままです。",
    }),
    VisionReadiness.MODEL_MISSING: frozendict({
        "zh-TW": "本機視覺模型缺失，視覺感知保持停用。",
        "zh-CN": "本地视觉模型缺失，视觉感知保持停用。",
        "en": "Local vision models are missing, so visual perception remains disabled.",
        "ja-JP": "ローカル視覚モデルがないため、視覚認識は無効のままです。",
    }),
    VisionReadiness.MODEL_UNTRUSTED: frozendict({
        "zh-TW": "本機視覺模型未通過完整性驗證，視覺感知保持停用。",
        "zh-CN": "本地视觉模型未通过完整性验证，视觉感知保持停用。",
        "en": "Local vision models failed integrity verification, so visual perception remains disabled.",
        "ja-JP": "ローカル視覚モデルが整合性検証に合格しなかったため、視覚認識は無効のままです。",
    }),
    VisionReadiness.RUNTIME_ERROR: frozendict({
        "zh-TW": "本機視覺分析失敗，已安全停用；其他功能不受影響。",
        "zh-CN": "本地视觉分析失败，已安全停用；其他功能不受影响。",
        "en": "Local vision analysis failed and was safely disabled; other features are unaffected.",
        "ja-JP": "ローカル視覚解析に失敗したため安全に無効化しました。その他の機能には影響しません。",
    }),
})

CORE_PERMISSION_LABELS = frozendict({
    "read_status": "讀取狀態與摘要",
    "search_local": "搜尋白名單資料夾",
    "open_web": "開啟網站",
    "open_folder": "開啟資料夾",
    "launch_app": "啟動白名單程式",
    "window_list": "列出可見視窗",
    "window_activate": "切換至指定視窗",
    "create_file": "建立檔案",
    "rename_file": "重新命名檔案",
    "move_file": "移動檔案",
    "calendar_create": "建立行事曆事件",
    "calendar_update": "修改行事曆事件",
    "calendar_read": "讀取行事曆",
    "email_read": "讀取電子郵件",
    "email_send": "寄送電子郵件",
    "cloud_file_read": "讀取雲端檔案",
    "cloud_file_write": "建立或修改雲端檔案",
    "publish_external": "對外發布內容",
    "home_read": "讀取智慧家庭狀態",
    "home_control": "控制一般智慧設備",
    "home_lock": "控制門鎖",
    "home_alarm": "控制警報",
    "home_heat": "控制加熱與高溫設備",
    "camera_view": "使用攝影機",
    "microphone_access": "使用麥克風",
    "realtime_session": "啟動 Realtime 雲端對話",
    "remote_screen": "遠端查看本程式畫面",
    "remote_file_read": "遠端下載白名單檔案",
    "remote_file_write": "遠端寫入檔案",
    "delete_file": "刪除檔案",
    "shutdown_pc": "關機或重新啟動",
})
GESTURE_PERMISSION_CAPABILITIES = frozendict({
    GestureAction.TOGGLE_LISTENING: "microphone_access",
    GestureAction.START_REALTIME: "realtime_session",
})
READ_INTENT_MARKERS = (
    "讀取",
    "查看",
    "搜尋",
    "查詢",
    "查找",
    "尋找",
    "找出",
    "列出",
    "整理",
    "顯示",
    "檢查",
    "測試",
    "瀏覽",
    "取得",
)


class GestureRecorderPort(Protocol):
    """Optional hand-landmark recorder; implementations never return images."""

    def available(self) -> bool: ...

    def record(self, gesture_id: str) -> GestureSample | None: ...


class UnavailableGestureRecorder:
    """Safe default until a real hand-landmark runtime signal is connected."""

    def available(self) -> bool:
        return False

    def record(self, gesture_id: str) -> GestureSample | None:
        del gesture_id
        return None


@dataclass(frozen=True, slots=True)
class FlagshipDraftValues:
    """Validated settings-only values ready for one guarded persistence pass."""

    gesture: GestureConfiguration
    proactivity: CompanionProactivityPreferences
    vision: OpenAIVisionPreferences
    phrasebook: dict[str, object]
    proactive_mode: str
    welcome_minimum_seconds: int
    conversation_silence_seconds: int
    security: tuple[tuple[str, str], ...]
ASSIST_INTENT_MARKERS = ("幫我", "請", "替我", "執行")
GMAIL_MARKERS = ("gmail", "郵件", "電子郵件", "信件", "信箱")
GMAIL_SEND_MARKERS = ("寄信", "寄出", "發信", "傳送郵件")
GMAIL_SEND_NEGATIONS = ("不要寄", "不用寄", "不寄出", "不要傳送")
CALENDAR_MARKERS = (
    "google calendar",
    "googlecalendar",
    "calendar",
    "日曆",
    "行事曆",
    "行程",
)
CALENDAR_WRITE_MARKERS = ("建立", "新增", "加入", "取消", "刪除")
DRIVE_MARKERS = (
    "google drive",
    "googledrive",
    "雲端硬碟",
    "雲端檔案",
)
DRIVE_WRITE_MARKERS = ("上傳", "寫入", "修改", "刪除", "移動")
CHINESE_DAY_COUNTS = frozendict({
    "一天": 1,
    "一日": 1,
    "三天": 3,
    "三日": 3,
    "七天": 7,
    "七日": 7,
    "一周": 7,
    "兩週": 14,
    "兩周": 14,
    "一個月": 30,
})
CHINESE_MAIL_COUNTS = frozendict({
    "一封": 1,
    "兩封": 2,
    "三封": 3,
    "五封": 5,
    "十封": 10,
})
