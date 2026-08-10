from __future__ import annotations

lazy import ctypes
lazy import html
lazy import math
lazy import os
lazy import random
lazy import sqlite3
lazy import sys
lazy import time
lazy import webbrowser
lazy from collections import deque
lazy from collections.abc import Iterable
lazy from contextlib import suppress
lazy from ctypes import wintypes
lazy from dataclasses import dataclass
lazy from datetime import datetime
lazy from datetime import time as clock_time
lazy from pathlib import Path

lazy from runtime_bootstrap import ensure_default_jit, jit_is_enabled

ensure_default_jit(__name__, __file__)

lazy from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QThreadPool,
    QTime,
    QTimer,
    QVariantAnimation,
    Signal,
)
lazy from PySide6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QFont,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPixmap,
    QShortcut,
    QWheelEvent,
)
lazy from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QSystemTrayIcon,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

lazy from ai_client import (
    DEFAULT_TEXT_MODEL,
    ENGLISH_PERSONA,
    JAPANESE_PERSONA,
    PERSONA,
    SIMPLIFIED_CHINESE_PERSONA,
    TEXT_MODELS,
    AIWorker,
    AIWorkerRequest,
)
lazy from azure_speech import azure_female_voices
lazy from background_agents import (
    DiagnosticReportWorker,
    ManagerWorkerScheduler,
    VisibleAppWorker,
)
lazy from command_parser import is_start_work_command, is_stop_work_command
lazy from contracts import (
    SecretStoreFactoryPort,
    SecretStorePort,
    SpeechListenerPort,
)
lazy from db import PlatformProgressUpdate, StudioDB, format_duration
lazy from expression_system import (
    ExpressionArbiter,
    FaceAnchorProfile,
    parse_internal_emotion,
    plan_wait_expressions,
)
lazy from feature_registry import DashboardFeatureRegistry
lazy from flagship_ui import FlagshipControlCenter
lazy from language_support import (
    english_voice_instructions,
    is_builtin_transcription_prompt,
    is_english,
    is_japanese,
    is_simplified_chinese,
    japanese_voice_instructions,
    localized_reminder_line,
    localized_transcription_prompt,
    localized_voice_instructions,
    migrate_builtin_reminder_line,
    response_language_instruction,
    simplified_chinese_voice_instructions,
    transcription_language_for_ui,
)
lazy from lip_sync import (
    VISEME_CHANGE_TRANSITION_SECONDS,
    VISEME_CLOSE_TRANSITION_SECONDS,
    VISEME_OPEN_TRANSITION_SECONDS,
    VisemeDynamics,
    VisemeFrame,
)
lazy from platform_contracts import PlatformCapabilities, PlatformServicePort
lazy from platform_services import current_platform_services, resolved_data_dir
lazy from profile_transfer_ui import PortableProfilePanel
lazy from realtime_voice import (
    RealtimeSessionConfig,
    RealtimeVoiceClient,
    RealtimeVoiceRequest,
)
lazy from service_container import CompanionServices, create_default_services
lazy from speech import (
    SpeechListener,
    is_known_male_windows_voice,
    preferred_windows_voice,
    windows_voices,
)
lazy from speech_providers import (
    AZURE_SPEECH_PROVIDER,
    OPENAI_REALTIME_PROVIDER,
    OPENAI_SPEECH_PROVIDER,
    SYSTEM_LOCAL_PROVIDER,
    SpeechRequest,
    create_builtin_speech_registry,
    migrate_speech_provider_setting,
    normalize_speech_provider_id,
)
lazy from text_normalizer import to_taiwan_traditional
lazy from time_utils import local_wall_time
lazy from ui_localization import (
    MODE_LABELS,
    SIMPLIFIED_MODE_LABELS,
    SIMPLIFIED_WORK_TYPE_LABELS,
    WORK_TYPE_LABELS,
    display_label,
    ui_text,
)
lazy from ui_localization_ja import (
    JAPANESE_MODE_LABELS,
    JAPANESE_WORK_TYPE_LABELS,
)
lazy from updater_ui import UpdatePanel
lazy from version_info import APP_VERSION
lazy from windows_tools import visible_windows

DEFAULT_PROFILE = frozendict({
    "assistant_name": "墨寒",
    "user_title": "主上",
    "organization_name": "",
    "window_title": "",
    "work_type": "一般辦公／行政",
    "ui_language": "zh-TW",
    "wake_word": "墨寒",
})

NEUTRAL_VISEME_ASSET_STEMS = frozendict({
    "A": "mouth_wide",
    "I": "mouth_i",
    "U": "mouth_round",
    "E": "mouth_mid",
    "O": "mouth_o",
})


@dataclass(frozen=True, slots=True)
class QueuedSpeech:
    text: str
    requested_state: str
    intensity: float = 0.5
    source: str = "conversation"


@dataclass(frozen=True, slots=True)
class SpeechCredentials:
    openai_api_key: str
    azure_api_key: str
    azure_region: str


@dataclass(frozen=True, slots=True)
class DashboardDependencies:
    listener: SpeechListenerPort
    secret_store: SecretStorePort
    azure_secret_store: SecretStorePort | None = None
    secret_store_factory: SecretStoreFactoryPort | None = None
    platform_services: PlatformServicePort | None = None


@dataclass(slots=True)
class PlatformCardControls:
    card: QFrame
    status: QComboBox
    item_name: QLineEdit
    missing: QLineEdit
    next_action: QLineEdit
    notes: QLineEdit
    url: QLineEdit
    validation: QLabel
    updated: QLabel
    save_button: QPushButton
    timer: QTimer
    dirty: bool = False

    @property
    def editors(self) -> tuple[QLineEdit, ...]:
        return (
            self.item_name,
            self.missing,
            self.next_action,
            self.notes,
            self.url,
        )


@dataclass(frozen=True, slots=True)
class MemoryTabActions:
    add: QPushButton
    edit: QPushButton
    delete: QPushButton
    clear: QPushButton
    optimize: QPushButton
    archives: QPushButton


@dataclass(frozen=True, slots=True)
class ProfileLocalizationContext:
    assistant_name: str
    user_title: str
    organization_name: str
    wake_word: str
    ui_language: str


@dataclass(frozen=True, slots=True)
class ProfileSettingsValues:
    assistant_name: str
    user_title: str
    organization_name: str
    window_title: str
    work_type: str
    ui_language: str
    wake_word: str

    @property
    def localization(self) -> ProfileLocalizationContext:
        return ProfileLocalizationContext(
            assistant_name=self.assistant_name,
            user_title=self.user_title,
            organization_name=self.organization_name,
            wake_word=self.wake_word,
            ui_language=self.ui_language,
        )

    def setting_items(self) -> tuple[tuple[str, object], ...]:
        return (
            ("assistant_name", self.assistant_name),
            ("user_title", self.user_title),
            ("organization_name", self.organization_name),
            ("window_title", self.window_title),
            ("work_type", self.work_type),
            ("ui_language", self.ui_language),
            ("wake_word", self.wake_word),
            ("onboarding_complete", True),
        )


MEMORY_CATEGORIES = (
    "人物",
    "偏好",
    "目標",
    "工作流程",
    "重要日期",
    "其他",
)

EMERGENCY_COMMANDS = frozenset(
    {
        "墨寒停手",
        "寒停手",
        "停手",
        "停止所有操作",
        "取消所有任務",
    }
)
TEASING_COMMAND_MARKERS = (
    "妳在看我",
    "你在看我",
    "偷看我",
    "一直看我",
    "喜歡我嗎",
    "喜歡我吧",
    "是不是喜歡",
    "愛慕我",
    "在意我吧",
)
TODAY_WORK_DURATION_MARKERS = ("多久", "幾小時", "工作時間")
IDEA_CAPTURE_MARKERS = ("靈感", "點子", "構想")
EXPLICIT_TOOL_COMMAND_MARKERS = (
    "請執行",
    "幫我開啟",
    "替我開啟",
    "幫我控制",
    "幫我建立檔案",
    "幫我移動",
    "幫我啟動",
)
SPEAKING_BLINK_PREFIXES = (
    ("mouth_mid", "blink_mid"),
    ("mouth_wide", "blink_wide"),
    ("mouth_round", "blink_round"),
    ("mouth_i", "blink_i"),
    ("mouth_o", "blink_o"),
    ("speaking", "blink_open"),
)
PHYSICS_POSE_SUFFIXES = (
    ("", "cheek"),
    ("_lean", "lean"),
    ("_front", "front"),
)
PHYSICS_SPEECH_FRAME_PREFIXES = (
    "idle",
    "speaking",
    "blink",
    "mouth_mid",
    "mouth_wide",
    "mouth_round",
    "mouth_i",
    "mouth_o",
    "blink_mid",
    "blink_open",
    "blink_wide",
    "blink_round",
    "blink_i",
    "blink_o",
)


def classify_memory_text(text: str) -> str:
    normalized = to_taiwan_traditional(text)
    category_terms = (
        (
            "重要日期",
            ("生日", "紀念日", "日期", "截止日", "每年", "月號"),
        ),
        (
            "目標",
            ("目標", "希望完成", "想要達成", "計畫達成", "今年要"),
        ),
        (
            "人物",
            (
                "朋友",
                "家人",
                "同事",
                "客戶",
                "主管",
                "老師",
                "學生",
                "名字叫",
                "名叫",
                "是我的",
            ),
        ),
        (
            "工作流程",
            (
                "工作流程",
                "工作習慣",
                "我習慣",
                "每次都先",
                "完成後再",
                "上架",
                "交稿",
            ),
        ),
        (
            "偏好",
            (
                "偏好",
                "喜歡",
                "不喜歡",
                "比較想",
                "習慣用",
                "常用",
            ),
        ),
    )
    for category, terms in category_terms:
        if any(term in normalized for term in terms):
            return category
    return "其他"

# Every expression enters the same rendering pipeline.  The pose mapping is
# explicit because filename suffixes alone are not reliable for legacy assets.
# It is also the single source of truth used by blinking, lip sync, gaze and
# the five flagship physics effects.
EXPRESSION_POSES = frozendict({
    "glance": "cheek",
    "caught": "cheek",
    "happy": "cheek",
    "worried": "cheek",
    "reminder": "cheek",
    "thinking_front": "front",
    "gentle_smile_front": "front",
    "worried_front": "front",
    "shy_front": "front",
    "mock_scold": "front",
    "surprised_front": "front",
    "relieved_front": "front",
    "tired_front": "front",
    "proud_front": "front",
    "shy_cute_front": "front",
    "mock_hit_front": "front",
    "attentive_front": "front",
    "determined_front": "front",
    "restrained_amused_front": "front",
    "exasperated_front": "front",
    "eureka_front": "front",
    "protective_front": "front",
})

NEW_EXPRESSION_ASSETS = (
    "shy_cute_front",
    "mock_hit_front",
    "attentive_front",
    "determined_front",
    "restrained_amused_front",
    "exasperated_front",
    "eureka_front",
    "protective_front",
)
EYES_CLOSED_EXPRESSIONS = frozenset({"exasperated_front"})
GESTURE_SPEECH_EXPRESSIONS = frozenset(
    {
        "mock_scold",
        "mock_hit_front",
        "exasperated_front",
        "eureka_front",
    }
)
EXPRESSION_SPEECH_EXPRESSIONS = frozenset(EXPRESSION_POSES)
EXPRESSION_SPEECH_FRAMES = frozendict({
    expression: frozendict({
        frame: f"{expression}_speech_{frame}"
        for frame in ("mid", "open", "round")
    })
    for expression in EXPRESSION_SPEECH_EXPRESSIONS
})
EXPRESSION_DERIVED_VISEME_FRAMES = frozendict({
    expression: frozendict({
        "I": f"{expression}_speech_i",
        "U": f"{expression}_speech_u",
    })
    for expression in EXPRESSION_SPEECH_EXPRESSIONS
})
EXPRESSION_VISEME_FRAMES = frozendict({
    expression: frozendict({
        "A": EXPRESSION_SPEECH_FRAMES[expression]["open"],
        "I": EXPRESSION_DERIVED_VISEME_FRAMES[expression]["I"],
        "U": EXPRESSION_DERIVED_VISEME_FRAMES[expression]["U"],
        "E": EXPRESSION_SPEECH_FRAMES[expression]["mid"],
        "O": EXPRESSION_SPEECH_FRAMES[expression]["round"],
    })
    for expression in EXPRESSION_SPEECH_EXPRESSIONS
})
GESTURE_SPEECH_FRAMES = frozendict({
    expression: EXPRESSION_SPEECH_FRAMES[expression]
    for expression in GESTURE_SPEECH_EXPRESSIONS
})
EXPRESSION_SPEECH_ASSETS = tuple(
    asset
    for frames in EXPRESSION_SPEECH_FRAMES.values()
    for asset in frames.values()
)
EXPRESSION_BLINK_FRAMES = frozendict({
    "thinking_front": "thinking_front_speech_blink",
    "glance": "glance_speech_blink",
    "happy": "happy_speech_blink",
    "worried": "worried_speech_blink",
    "reminder": "reminder_speech_blink",
})
EXPRESSION_BLINK_ASSETS = tuple(EXPRESSION_BLINK_FRAMES.values())
EXPRESSION_IMAGE_ASSETS = (
    "idle",
    "idle_lean",
    "idle_front",
    "blink",
    "blink_lean",
    "blink_front",
    "glance",
    "caught",
    "speaking",
    "speaking_lean",
    "speaking_front",
    "happy",
    "worried",
    "reminder",
    "thinking_front",
    "gentle_smile_front",
    "worried_front",
    "shy_front",
    "mock_scold",
    "surprised_front",
    "relieved_front",
    "tired_front",
    "proud_front",
    *NEW_EXPRESSION_ASSETS,
    *EXPRESSION_SPEECH_ASSETS,
    *EXPRESSION_BLINK_ASSETS,
    "viseme_mid_front",
    "viseme_wide_front",
    "viseme_round",
    "viseme_round_lean",
    "viseme_round_front",
    "viseme_i",
    "viseme_i_lean",
    "viseme_i_front",
    "viseme_o",
    "viseme_o_lean",
    "viseme_o_front",
)
GESTURE_SPEECH_ASSETS = tuple(
    asset
    for frames in GESTURE_SPEECH_FRAMES.values()
    for asset in frames.values()
)
EXPRESSION_SPEECH_MOUTH_RECTS = frozendict({
    expression: (
        QRect(170, 194, 60, 42)
        if pose == "cheek"
        else QRect(158, 194, 62, 42)
        if pose == "lean"
        else QRect(202, 195, 62, 43)
    )
    for expression, pose in EXPRESSION_POSES.items()
} | {
    "mock_scold": QRect(202, 196, 53, 44),
    "mock_hit_front": QRect(201, 190, 56, 50),
    "exasperated_front": QRect(199, 201, 58, 47),
    "eureka_front": QRect(197, 190, 58, 48),
})
CHEEK_SPEECH_CLOSED_EXPRESSION = "idle_speech_neutral"
# Keep the photographed cheek-rest mouth corners outside the animated region.
# At the runtime 465 px canvas, the visible central lips occupy roughly
# x=184..207; widening this mask reaches both smile corners and recreates the
# Joker-like corner flutter reported in rapid A/I/U/E/O transitions.
CHEEK_SPEECH_CENTRAL_MOUTH_RECT = QRect(184, 198, 24, 34)
GESTURE_SPEECH_MOUTH_RECTS = frozendict({
    expression: EXPRESSION_SPEECH_MOUTH_RECTS[expression]
    for expression in GESTURE_SPEECH_EXPRESSIONS
})
# Verified per-asset facial registration. Runtime rendering uses these fixed
# values so startup stays fast; the pixel matcher remains available to QA tests
# for detecting a replaced or accidentally shifted asset.
EXPRESSION_FACE_OFFSETS = frozendict({
    "glance": (0, 0),
    "caught": (0, 1),
    "happy": (0, 0),
    "worried": (0, 0),
    "reminder": (0, 0),
    "thinking_front": (3, 0),
    "gentle_smile_front": (0, 0),
    "worried_front": (0, 0),
    "shy_front": (1, 0),
    "mock_scold": (5, 3),
    "surprised_front": (0, 0),
    "relieved_front": (0, 0),
    "tired_front": (0, 0),
    "proud_front": (0, -1),
    "shy_cute_front": (0, 0),
    "mock_hit_front": (1, -1),
    "attentive_front": (1, 3),
    "determined_front": (0, 0),
    "restrained_amused_front": (0, 0),
    "exasperated_front": (-1, 6),
    "eureka_front": (-1, -1),
    "protective_front": (0, -4),
})
EXPRESSION_EYE_OFFSETS = frozendict({
    **EXPRESSION_FACE_OFFSETS,
    "caught": (0, 3),
    "reminder": (0, 1),
    "thinking_front": (4, -3),
    "surprised_front": (0, -1),
    "attentive_front": (1, 2),
    "determined_front": (0, 1),
    "restrained_amused_front": (0, 1),
    "protective_front": (0, -3),
})
EXPRESSION_MOUTH_OFFSETS = frozendict({
    **EXPRESSION_FACE_OFFSETS,
    "caught": (0, 0),
    "mock_scold": (4, 4),
    "proud_front": (0, 0),
    "mock_hit_front": (1, -2),
    "eureka_front": (0, 0),
    "protective_front": (0, -3),
})
APP_NAME = "墨寒桌面助理"
APP_ICON_PATH = "assets/mohan-halfbody.ico"
WINDOWS_APP_USER_MODEL_ID = (
    "FlamebladeStudio.MoHanDesktopAssistant"
)
CHARACTER_CANVAS_WIDTH = 470
CHARACTER_IMAGE_SIZE = 465
CHARACTER_BASE_Y = 215
CHARACTER_SCALE_MIN = 75
CHARACTER_SCALE_MAX = 180
CHARACTER_SCALE_DEFAULT = 100
MOUTH_CLOSE_DEADLINE_MS = max(
    110,
    math.ceil(VISEME_CLOSE_TRANSITION_SECONDS * 1000) + 32,
)
PLATFORM_STATUSES = (
    "尚未開始",
    "準備資料",
    "進行中",
    "待送出",
    "等待回覆",
    "審核中",
    "需修正",
    "已排程",
    "已完成",
    "已上架",
    "暫停",
)
REMINDER_LINES = frozendict({
    "work": "主上，今日之局已開。若要開始，妾替你計時。",
    "lunch": "到吃飯時間了。工作可以稍候，主上的身體不能。",
    "dinner": "主上，先去用晚膳。空著腹談什麼長策。",
    "offwork": "你已經不需要向任何老闆證明自己肯加班了。",
    "overwork": "主上已連續工作太久。離席、飲水、伸展，十分鐘後再戰。",
})


def reminder_line(language: str, kind: str) -> str:
    return localized_reminder_line(
        language,
        kind,
        REMINDER_LINES[kind],
    )


def default_persona_for_language(language: str) -> str:
    if is_english(language):
        return ENGLISH_PERSONA
    if is_simplified_chinese(language):
        return SIMPLIFIED_CHINESE_PERSONA
    if is_japanese(language):
        return JAPANESE_PERSONA
    return PERSONA


def normalize_for_language(text: str, language: str) -> str:
    if (
        is_english(language)
        or is_simplified_chinese(language)
        or is_japanese(language)
    ):
        return str(text)
    return to_taiwan_traditional(str(text))


def combo_data_or_custom_text(combo: QComboBox, fallback: str = "") -> str:
    """Persist stable item data while preserving editable custom values."""
    text = combo.currentText().strip()
    index = combo.currentIndex()
    if index >= 0 and text == combo.itemText(index).strip():
        return str(combo.itemData(index) or text or fallback)
    return text or fallback

VOICE_GENERATION_PROMPT = (
    "請使用台灣繁體中文，以自然的台灣中文口音說話。"
    "聲線如二十多歲的女性動漫配音，清澈、沉靜、帶有古典氣質；"
    "咬字清楚但不要字正腔圓得像播報員。"
    "語氣專業、機敏、略帶傲嬌，對主上含有不明說的溫柔與愛慕。"
    "避免中國普通話腔、兒童聲、過度甜膩、誇張撒嬌或舞台式朗誦。"
)

VOICE_ENGINE_SYSTEM = SYSTEM_LOCAL_PROVIDER
# Compatibility export for extensions and tests written before the provider
# ID became platform-neutral.
VOICE_ENGINE_WINDOWS = VOICE_ENGINE_SYSTEM
VOICE_ENGINE_OPENAI = OPENAI_SPEECH_PROVIDER
VOICE_ENGINE_REALTIME = OPENAI_REALTIME_PROVIDER
VOICE_ENGINE_AZURE = AZURE_SPEECH_PROVIDER

REALTIME_VOICES = (
    "coral",
    "marin",
    "shimmer",
    "cedar",
    "sage",
    "verse",
    "alloy",
    "ash",
    "ballad",
    "echo",
)

TTS_VOICES = (
    "coral",
    "marin",
    "cedar",
    "shimmer",
    "nova",
    "sage",
    "alloy",
    "ash",
    "ballad",
    "echo",
    "fable",
    "onyx",
    "verse",
)


def migrate_voice_defaults(db: StudioDB) -> None:
    if bool(db.setting("voice_prompt_v1204_migrated", False)):
        return
    language = str(db.setting("ui_language", "zh-TW"))
    db.set_setting(
        "voice_instructions",
        localized_voice_instructions(language, VOICE_GENERATION_PROMPT),
    )
    db.set_setting("tts_voice", "coral")
    db.set_setting("cloud_voice", "coral")
    db.set_setting("realtime_voice", "coral")
    db.set_setting("voice_prompt_v1204_migrated", True)


STYLE = """
QWidget { color: #24364a; font-size: 13px; }
QDialog, QMainWindow { background: #eef3f8; }
QTabWidget::pane { border: 1px solid #b9c9d8; border-radius: 12px; background: #ffffff; }
QTabBar::tab { background: #e4ebf3; color: #48647a; padding: 10px 18px; margin: 2px; border-radius: 9px; }
QTabBar::tab:selected { background: #cfe0ee; color: #17344f; font-weight: 600; }
QTabBar::tab:hover { background: #d9e6f0; color: #17344f; }
QLineEdit, QTextBrowser, QTextEdit, QListWidget, QComboBox, QTimeEdit, QSpinBox {
    background: #ffffff; color: #20364a; border: 1px solid #b8c8d6; border-radius: 9px; padding: 7px;
    selection-background-color: #9fc4dc; selection-color: #102a3d;
}
QScrollArea#todoScroll {
    background: #ffffff;
    border: 1px solid #c3d0dc;
    border-radius: 10px;
}
QScrollArea#formScrollPage {
    background: #ffffff;
    border: none;
}
QScrollArea#formScrollPage QWidget#qt_scrollarea_viewport {
    background: #ffffff;
}
QWidget#formScrollContent {
    background: #ffffff;
}
QScrollArea#formScrollPage QScrollBar:vertical {
    background: #edf2f6;
    width: 14px;
    margin: 0;
}
QScrollArea#formScrollPage QScrollBar::handle:vertical {
    background: #9eb5c7;
    min-height: 28px;
    border-radius: 6px;
    margin: 2px;
}
QScrollArea#formScrollPage QScrollBar::handle:vertical:hover {
    background: #789bb2;
}
QScrollArea#formScrollPage QScrollBar::add-line:vertical,
QScrollArea#formScrollPage QScrollBar::sub-line:vertical {
    height: 0;
    background: transparent;
}
QScrollArea#formScrollPage QScrollBar::add-page:vertical,
QScrollArea#formScrollPage QScrollBar::sub-page:vertical {
    background: transparent;
}
QWidget#todoViewport, QWidget#todoContainer { background: #ffffff; }
QFrame#todoCard {
    background: #f5f8fb;
    border: 1px solid #c3d0dc;
    border-radius: 10px;
}
QLabel#todoTitle { color: #1e3549; font-size: 14px; font-weight: 600; }
QLabel#todoCategory { color: #356d88; font-size: 11px; }
QLabel#sectionCount { color: #356d88; }
QLabel#emptyState {
    color: #64788a;
    padding: 24px;
}
QLabel#entryFeedback { color: #3f7752; padding-left: 4px; }
QListWidget#ideaList {
    background: #ffffff;
    color: #24364a;
    border: 1px solid #c3d0dc;
    border-radius: 10px;
    padding: 6px;
}
QListWidget#ideaList::item {
    background: #f3f7fa;
    border: 1px solid #c8d4df;
    border-radius: 7px;
    margin: 3px;
    padding: 9px;
}
QListWidget#ideaList::item:selected { background: #cfe0ee; color: #17344f; }
QSplitter#todaySplitter::handle {
    background: #b3c4d1;
    height: 6px;
    margin: 2px 0;
    border-radius: 3px;
}
QSplitter#todaySplitter::handle:hover { background: #789bb2; }
QPushButton {
    background: #dce9f3; color: #17344f; border: 1px solid #8eabc0; border-radius: 10px; padding: 8px 13px;
    font-weight: 600;
}
QPushButton:hover { background: #c9dfed; border-color: #6f96ae; }
QPushButton:pressed { background: #aecbdc; }
QPushButton:disabled { background: #e8edf1; color: #8997a3; border-color: #ccd5dc; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    background: #ffffff;
    border: 2px solid #58758a;
    border-radius: 5px;
}
QCheckBox::indicator:hover { border-color: #245f80; background: #f1f7fb; }
QCheckBox::indicator:checked {
    background: #245f80;
    border-color: #245f80;
    image: url(assets/ui/checkmark.svg);
}
QCheckBox::indicator:disabled {
    background: #e7edf2;
    border-color: #aab7c1;
}
QToolTip { background: #ffffff; color: #24364a; border: 1px solid #9eb5c7; padding: 5px; }
QFrame#onboardingHero {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #dce9f4, stop:0.55 #edf2f7, stop:1 #f6eee7);
    border: 1px solid #b6c8d6;
    border-radius: 20px;
}
QFrame#onboardingContent {
    background: #ffffff;
    border: 1px solid #c4d1dc;
    border-radius: 20px;
}
QLabel#onboardingBrand { color: #17344f; font-size: 30px; font-weight: 700; }
QLabel#onboardingTagline { color: #435f73; font-size: 15px; line-height: 1.35; }
QLabel#onboardingTitle { color: #17344f; font-size: 28px; font-weight: 700; }
QFrame#onboardingContent QLabel { color: #263d50; font-size: 15px; }
QFrame#onboardingContent QLabel#onboardingTitle { color: #17344f; font-size: 28px; font-weight: 700; }
QFrame#onboardingContent QLabel#onboardingNote { color: #355d74; font-size: 14px; }
QFrame#onboardingContent QLineEdit,
QFrame#onboardingContent QComboBox {
    min-height: 34px;
    padding: 7px 10px;
    font-size: 15px;
}
QFrame#onboardingContent QPushButton {
    min-height: 38px;
    padding: 8px 20px;
    font-size: 16px;
}
QMenu {
    background: #ffffff;
    color: #000000;
    border: 1px solid #aeb6bd;
    border-radius: 8px;
    padding: 5px;
}
QMenu::item {
    color: #000000;
    background: transparent;
    padding: 7px 18px;
    border-radius: 6px;
}
QMenu::item:selected {
    color: #000000;
    background: #dce8ef;
}
QMenu::separator {
    height: 1px;
    background: #c9ced3;
    margin: 4px 8px;
}
"""


def application_ui_font() -> QFont:
    font = QFont()
    font.setFamilies(
        [
            "Microsoft JhengHei UI",
            "Microsoft YaHei UI",
            "Yu Gothic UI",
            "Segoe UI",
        ]
    )
    font.setPointSize(10)
    return font


RESOURCE_BASE = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
)


def resource_path(relative: str) -> Path:
    return RESOURCE_BASE / relative


def application_icon() -> QIcon:
    application = QApplication.instance()
    if application is not None and not application.windowIcon().isNull():
        return application.windowIcon()
    icon_path = resource_path(APP_ICON_PATH)
    icon = QIcon(str(icon_path))
    if icon.isNull():
        raise RuntimeError(f"MoHan application icon could not be loaded: {icon_path}")
    return icon


def data_dir(platform_services: PlatformServicePort | None = None) -> Path:
    root = resolved_data_dir(platform_services)
    root.mkdir(parents=True, exist_ok=True)
    return root


def profile_setting(db: StudioDB, key: str) -> str:
    return str(db.setting(key, DEFAULT_PROFILE[key])).strip()


def profile_window_title(db: StudioDB) -> str:
    custom = profile_setting(db, "window_title")
    if custom:
        return custom
    assistant = profile_setting(db, "assistant_name")
    organization = profile_setting(db, "organization_name")
    return "．".join(part for part in (assistant, organization) if part)


def persona_for_profile(db: StudioDB) -> str:
    """Apply editable identity fields without changing stored user prompts."""
    language = profile_setting(db, "ui_language")
    default_persona = default_persona_for_language(language)
    persona = (
        str(db.setting("persona_prompt", default_persona)).strip()
        or default_persona
    )
    assistant = profile_setting(db, "assistant_name")
    user_title = profile_setting(db, "user_title")
    organization = profile_setting(db, "organization_name")
    persona = (
        persona.replace("墨寒", assistant)
        .replace("MoHan", assistant)
        .replace("主上", user_title)
    )
    if organization:
        persona = persona.replace("炎劍文化工作室", organization)
        if is_english(language):
            persona += (
                f"\nThe user's configured organization or team is "
                f'"{organization}". Use that context for work assistance.'
            )
        elif is_simplified_chinese(language):
            persona += (
                f"\n用户当前设置的组织／团队名称是“{organization}”。"
                "处理工作事务时，请结合此组织背景提供协助。"
            )
        elif is_japanese(language):
            persona += (
                f"\nユーザーが設定した組織／チーム名は「{organization}」です。"
                "仕事を支援する際は、この組織の文脈を踏まえてください。"
            )
        else:
            persona += (
                f"\n使用者目前設定的組織／團隊名稱是「{organization}」。"
                "處理工作事務時，請依此組織背景提供協助。"
            )
    else:
        # Older personal profiles may contain the former studio-specific
        # default. A fresh public installation must remain organization-neutral.
        persona = persona.replace(
            "炎劍文化工作室的虛擬執行長、文膽與策士",
            "使用者身邊的虛擬執行長、文膽與策士",
        ).replace(
            "炎劍文化工作室首席文膽與策士",
            "首席文膽與策士",
        )
    return persona


def personalize_text(db: StudioDB, text: str) -> str:
    """Apply editable identity fields to built-in fallback copy."""
    replacements = {
        "墨寒": profile_setting(db, "assistant_name"),
        "主上": profile_setting(db, "user_title"),
    }
    organization = profile_setting(db, "organization_name")
    if organization:
        replacements["炎劍文化工作室"] = organization
    result = text
    for source, target in replacements.items():
        if target:
            result = result.replace(source, target)
    return result


def set_autostart(
    enabled: bool,
    platform_services: PlatformServicePort | None = None,
) -> None:
    command = f'"{sys.executable}"'
    if not getattr(sys, "frozen", False):
        command += f' "{Path(__file__).resolve()}"'
    (platform_services or current_platform_services()).set_autostart(
        enabled,
        application_id="MoHanStudio",
        command=command,
    )


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._press_position: QPoint | None = None
        self._dragged = False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._press_position = event.position().toPoint()
            self._dragged = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._press_position is not None
            and event.buttons() & Qt.LeftButton
            and (
                event.position().toPoint() - self._press_position
            ).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._dragged = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        release_position = event.position().toPoint()
        is_click = (
            event.button() == Qt.LeftButton
            and self._press_position is not None
            and not self._dragged
            and (
                release_position - self._press_position
            ).manhattanLength()
            < QApplication.startDragDistance()
        )
        self._press_position = None
        self._dragged = False
        if is_click:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ZoomTextBrowser(QTextBrowser):
    zoom_step_requested = Signal(int)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.zoom_step_requested.emit(1 if delta > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)


class TodoRow(QFrame):
    changed = Signal()

    def __init__(self, db: StudioDB, todo):
        super().__init__()
        self.setObjectName("todoCard")
        # A task card should keep its content height.  Letting QVBoxLayout
        # stretch every QFrame vertically makes cards overlap visually in a
        # tall or wide dashboard capture.
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.db = db
        self.todo_id = int(todo["id"])
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 10, 9)
        layout.setSpacing(10)
        done = QCheckBox()
        done.setToolTip("標記為已完成")
        done.setChecked(todo["status"] == "完成")
        text_column = QVBoxLayout()
        text_column.setSpacing(2)
        title = QLabel(to_taiwan_traditional(str(todo["title"])))
        title.setObjectName("todoTitle")
        title.setWordWrap(True)
        category = QLabel(f"{todo['category']} · 今日待辦")
        category.setObjectName("todoCategory")
        delete = QPushButton("刪除")
        delete.setToolTip("刪除這筆待辦")
        delete.setFixedWidth(64)
        done.toggled.connect(self._toggle)
        delete.clicked.connect(self._delete)
        text_column.addWidget(title)
        text_column.addWidget(category)
        layout.addWidget(done)
        layout.addLayout(text_column, 1)
        layout.addWidget(delete)

    def _toggle(self, checked: bool) -> None:
        self.db.set_todo_done(self.todo_id, checked)
        self.changed.emit()

    def _delete(self) -> None:
        self.db.delete_todo(self.todo_id)
        self.changed.emit()


class IdeaEditorDialog(QDialog):
    def __init__(self, title: str, content: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("編輯創作靈感")
        self.setMinimumSize(560, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>靈感標題</b>"))
        self.title_input = QLineEdit(to_taiwan_traditional(title))
        self.title_input.setPlaceholderText("替這則靈感取一個清楚的標題")
        layout.addWidget(self.title_input)
        layout.addWidget(QLabel("<b>靈感內文</b>"))
        self.content_input = QTextEdit()
        self.content_input.setPlainText(to_taiwan_traditional(content))
        self.content_input.setPlaceholderText(
            "記下情節、畫面、台詞、音樂方向或後續可執行的想法……"
        )
        layout.addWidget(self.content_input, 1)
        buttons = QHBoxLayout()
        cancel = QPushButton("取消")
        save = QPushButton("保存靈感")
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)

    def _save(self) -> None:
        if not self.title_input.text().strip():
            QMessageBox.information(self, "尚無標題", "請先填寫靈感標題。")
            self.title_input.setFocus()
            return
        self.accept()

    def values(self) -> tuple[str, str]:
        return (
            to_taiwan_traditional(self.title_input.text().strip()),
            to_taiwan_traditional(self.content_input.toPlainText().strip()),
        )


class MemoryEditorDialog(QDialog):
    def __init__(self, memory, parent=None):
        super().__init__(parent)
        self.setWindowTitle("編輯長期記憶")
        self.setMinimumSize(620, 500)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>記憶標題</b>"))
        self.title_input = QLineEdit(
            to_taiwan_traditional(str(memory["title"] or ""))
        )
        self.title_input.setPlaceholderText("用一句短標題辨識這則記憶")
        layout.addWidget(self.title_input)

        details = QHBoxLayout()
        category_box = QVBoxLayout()
        category_box.addWidget(QLabel("<b>類別</b>"))
        self.category_input = QComboBox()
        self.category_input.addItems(MEMORY_CATEGORIES)
        current_category = to_taiwan_traditional(str(memory["category"]))
        if self.category_input.findText(current_category) < 0:
            self.category_input.addItem(current_category)
        self.category_input.setCurrentText(current_category)
        category_box.addWidget(self.category_input)
        importance_box = QVBoxLayout()
        importance_box.addWidget(QLabel("<b>重要度</b>"))
        self.importance_input = QSpinBox()
        self.importance_input.setRange(1, 5)
        self.importance_input.setValue(int(memory["importance"]))
        self.importance_input.setSuffix("／5")
        importance_box.addWidget(self.importance_input)
        details.addLayout(category_box, 1)
        details.addLayout(importance_box, 1)
        layout.addLayout(details)

        layout.addWidget(QLabel("<b>記憶內容</b>"))
        self.content_input = QTextEdit()
        self.content_input.setPlainText(
            to_taiwan_traditional(str(memory["content"] or ""))
        )
        self.content_input.setPlaceholderText(
            "完整記錄人物背景、偏好、目標、工作流程或重要日期……"
        )
        layout.addWidget(self.content_input, 1)
        source_labels = {
            "manual": "手動建立",
            "conversation": "由對話明確記住",
        }
        source = source_labels.get(
            str(memory["source"]), str(memory["source"])
        )
        meta = QLabel(
            f"來源：{source}　建立：{str(memory['created_at'])[:16]}　"
            f"更新：{str(memory['updated_at'])[:16]}"
        )
        meta.setStyleSheet("color:#4c6b82;")
        layout.addWidget(meta)
        buttons = QHBoxLayout()
        cancel = QPushButton("取消")
        save = QPushButton("保存記憶")
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)

    def _save(self) -> None:
        if not self.title_input.text().strip():
            QMessageBox.information(self, "尚無標題", "請先填寫記憶標題。")
            self.title_input.setFocus()
            return
        if not self.content_input.toPlainText().strip():
            QMessageBox.information(self, "尚無內容", "請先填寫記憶內容。")
            self.content_input.setFocus()
            return
        self.accept()

    def values(self) -> tuple[str, str, str, int]:
        return (
            to_taiwan_traditional(self.title_input.text().strip()),
            to_taiwan_traditional(self.content_input.toPlainText().strip()),
            self.category_input.currentText(),
            self.importance_input.value(),
        )


class ArchivedMemoryDialog(QDialog):
    def __init__(self, db: StudioDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.changed = False
        self.setWindowTitle("已封存的長期記憶")
        self.setMinimumSize(720, 520)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "自動整理只會封存較舊、低重要度的對話記憶，不會直接銷毀。"
            "您可以在這裡隨時勾選還原。"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.archive_list = QListWidget()
        layout.addWidget(self.archive_list, 1)
        self.archive_status = QLabel()
        layout.addWidget(self.archive_status)
        buttons = QHBoxLayout()
        restore = QPushButton("還原勾選記憶")
        close = QPushButton("關閉")
        buttons.addWidget(restore)
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)
        restore.clicked.connect(self.restore_checked)
        close.clicked.connect(self.accept)
        self.refresh_archives()

    def refresh_archives(self) -> None:
        self.archive_list.clear()
        rows = self.db.list_archived_memories(1000)
        for row in rows:
            item = QListWidgetItem(
                f"【{to_taiwan_traditional(str(row['category']))}】"
                f"{to_taiwan_traditional(str(row['title']))}\n"
                f"{to_taiwan_traditional(str(row['content']))}\n"
                f"封存原因：{row['reason']}　時間：{str(row['archived_at'])[:16]}"
            )
            item.setData(Qt.UserRole, int(row["id"]))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.archive_list.addItem(item)
        self.archive_status.setText(f"目前共有 {len(rows)} 則可還原記憶")

    def restore_checked(self) -> None:
        selected = [
            int(self.archive_list.item(index).data(Qt.UserRole))
            for index in range(self.archive_list.count())
            if self.archive_list.item(index).checkState() == Qt.Checked
        ]
        if not selected:
            QMessageBox.information(self, "尚未選取", "請先勾選要還原的記憶。")
            return
        restored = sum(
            1 for archive_id in selected
            if self.db.restore_archived_memory(archive_id) > 0
        )
        self.changed = self.changed or restored > 0
        self.refresh_archives()
        self.archive_status.setText(f"已還原 {restored} 則記憶。")


class ChatHistoryDialog(QDialog):
    def __init__(self, db: StudioDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.changed = False
        self.setWindowTitle("管理／清除對話")
        self.setMinimumSize(720, 520)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "對話平時保存在本機，不會自動刪除。"
            "請只勾選確定要永久刪除的紀錄。"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.history_list = QListWidget()
        layout.addWidget(self.history_list, 1)
        self.history_status = QLabel()
        self.history_status.setStyleSheet("color: #356d88;")
        layout.addWidget(self.history_status)
        buttons = QHBoxLayout()
        delete = QPushButton("刪除勾選對話")
        close = QPushButton("關閉")
        buttons.addWidget(delete)
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)
        delete.clicked.connect(self.delete_checked)
        close.clicked.connect(self.accept)
        self.refresh_history()

    def refresh_history(self) -> None:
        self.history_list.clear()
        rows = self.db.chat_history(500)
        for row in rows:
            speaker = (
                profile_setting(self.db, "user_title")
                if row["role"] == "user"
                else profile_setting(self.db, "assistant_name")
            )
            content = " ".join(
                to_taiwan_traditional(row["content"]).split()
            )
            if len(content) > 110:
                content = content[:110] + "…"
            item = QListWidgetItem(
                f"{row['created_at'][5:16]}｜{speaker}\n{content}"
            )
            item.setData(Qt.UserRole, int(row["id"]))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setToolTip(to_taiwan_traditional(row["content"]))
            self.history_list.addItem(item)
        total = self.db.chat_count()
        suffix = "（管理視窗最多顯示最近 500 則）" if total > 500 else ""
        self.history_status.setText(f"本機共保存 {total} 則對話。{suffix}")

    def checked_chat_ids(self) -> list[int]:
        checked: list[int] = []
        for index in range(self.history_list.count()):
            item = self.history_list.item(index)
            if item.checkState() == Qt.Checked:
                checked.append(int(item.data(Qt.UserRole)))
        return checked

    def delete_checked(self) -> None:
        chat_ids = self.checked_chat_ids()
        if not chat_ids:
            QMessageBox.information(
                self, "尚未勾選", "請先勾選要刪除的對話。"
            )
            return
        answer = QMessageBox.question(
            self,
            "永久刪除對話",
            f"確定永久刪除勾選的 {len(chat_ids)} 則對話嗎？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.db.delete_chat_entries(chat_ids)
        self.changed = True
        self.refresh_history()


class FirstRunWizard(QDialog):
    """Collect identity and workflow choices without assuming one profession."""

    WORK_TYPES = (
        "一般辦公／行政",
        "專案管理",
        "自由工作者／接案",
        "創作／內容工作",
        "軟體開發／技術",
        "教育／研究",
        "銷售／客戶服務",
        "其他（可自行輸入）",
    )

    def __init__(
        self,
        db: StudioDB,
        parent=None,
        *,
        platform_services: PlatformServicePort | None = None,
    ):
        super().__init__(parent)
        self.db = db
        self.platform_services = (
            platform_services or current_platform_services()
        )
        self.language = profile_setting(db, "ui_language")
        self._configure_window()
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(18)
        root.addWidget(self._build_hero_panel())
        root.addWidget(self._build_content_panel(), 1)
        self.save_button.clicked.connect(self._save)
        self.ui_language.currentIndexChanged.connect(
            self._apply_language
        )
        self._apply_language()

    def _configure_window(self) -> None:
        self.setWindowIcon(application_icon())
        self.setMinimumSize(1100, 720)
        self.setFont(application_ui_font())
        self.setStyleSheet(STYLE)

    def _build_hero_panel(self) -> QFrame:
        hero_panel = QFrame()
        hero_panel.setObjectName("onboardingHero")
        hero_panel.setFixedWidth(360)
        hero_background = resource_path(
            "assets/onboarding/first-run-ink-tech.png"
        ).as_posix()
        hero_panel.setStyleSheet(
            f"""
            QFrame#onboardingHero {{
                border-image: url(\"{hero_background}\") 0 0 0 0 stretch stretch;
                border: 1px solid #aebfcd;
                border-radius: 20px;
            }}
            """
        )
        hero_layout = QVBoxLayout(hero_panel)
        hero_layout.setContentsMargins(16, 24, 16, 14)
        hero_layout.setSpacing(10)
        self.hero_brand = QLabel("墨寒  MoHan")
        self.hero_brand.setObjectName("onboardingBrand")
        self.hero_tagline = QLabel()
        self.hero_tagline.setObjectName("onboardingTagline")
        self.hero_tagline.setWordWrap(True)
        self.hero_image = QLabel()
        self.hero_image.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        hero_pixmap = QPixmap(
            str(
                resource_path(
                    "assets/onboarding/mohan-hero-rain-canonical.webp"
                )
            )
        )
        hero_scaled = hero_pixmap.scaled(
            330,
            590,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        self.hero_image.setPixmap(
            hero_scaled.copy(
                max(0, hero_scaled.width() - 330),
                max(0, (hero_scaled.height() - 590) // 2),
                330,
                590,
            )
        )
        hero_layout.addWidget(self.hero_brand)
        hero_layout.addWidget(self.hero_tagline)
        hero_layout.addStretch()
        hero_layout.addWidget(self.hero_image)
        return hero_panel

    def _initialize_profile_editors(self) -> None:
        db = self.db
        self.assistant_name = QLineEdit(
            profile_setting(db, "assistant_name")
        )
        self.assistant_name.setPlaceholderText(
            "例如：墨寒、Ava、Office Mate"
        )
        self.user_title = QLineEdit(profile_setting(db, "user_title"))
        self.user_title.setPlaceholderText(
            "助理如何稱呼你，例如：主上、Alex、主管"
        )
        self.organization_name = QLineEdit(
            profile_setting(db, "organization_name")
        )
        self.organization_name.setPlaceholderText(
            "公司、工作室或團隊名稱；個人使用可留空"
        )
        self.window_title = QLineEdit(
            profile_setting(db, "window_title")
        )
        self.window_title.setPlaceholderText(
            "留空時自動顯示「助理名稱．組織名稱」"
        )
        self._initialize_work_type()
        self._initialize_language()
        self.wake_word = QLineEdit(profile_setting(db, "wake_word"))
        self.wake_word.setPlaceholderText(
            "語音喚醒詞，例如：墨寒"
        )

    def _initialize_work_type(self) -> None:
        self.work_type = QComboBox()
        self.work_type.setEditable(True)
        for value in self.WORK_TYPES:
            self.work_type.addItem(
                display_label(
                    self.language,
                    value,
                    WORK_TYPE_LABELS,
                    SIMPLIFIED_WORK_TYPE_LABELS,
                    JAPANESE_WORK_TYPE_LABELS,
                ),
                value,
            )
        saved = profile_setting(self.db, "work_type")
        index = self.work_type.findData(saved)
        if index >= 0:
            self.work_type.setCurrentIndex(index)
        else:
            self.work_type.setCurrentText(saved)

    def _initialize_language(self) -> None:
        self.ui_language = QComboBox()
        self.ui_language.addItem("繁體中文（台灣）", "zh-TW")
        self.ui_language.addItem("简体中文（中国大陆）", "zh-CN")
        self.ui_language.addItem("English", "en")
        self.ui_language.addItem("日本語", "ja-JP")
        current = profile_setting(self.db, "ui_language")
        self.ui_language.setCurrentIndex(
            max(0, self.ui_language.findData(current))
        )

    def _build_profile_form(self) -> QFormLayout:
        self._initialize_profile_editors()
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.form_labels: dict[str, QLabel] = {}
        fields = (
            ("assistant_name", self.assistant_name),
            ("user_title", self.user_title),
            ("organization_name", self.organization_name),
            ("window_title", self.window_title),
            ("work_type", self.work_type),
            ("ui_language", self.ui_language),
            ("wake_word", self.wake_word),
        )
        for key, editor in fields:
            label = QLabel()
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            # Matching label and editor heights prevents mixed-font baseline
            # drift in the commercial onboarding dialog.
            editor.setFixedHeight(50)
            label.setFixedHeight(50)
            self.form_labels[key] = label
            form.addRow(label, editor)
        return form

    def _build_content_panel(self) -> QFrame:
        content_panel = QFrame()
        content_panel.setObjectName("onboardingContent")
        layout = QVBoxLayout(content_panel)
        layout.setContentsMargins(32, 30, 32, 26)
        layout.setSpacing(16)
        self.title_label = QLabel()
        self.title_label.setObjectName("onboardingTitle")
        self.intro_label = QLabel()
        self.intro_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.intro_label)
        layout.addLayout(self._build_profile_form())
        self.note_label = QLabel()
        self.note_label.setWordWrap(True)
        self.note_label.setObjectName("onboardingNote")
        layout.addWidget(self.note_label)
        layout.addStretch()
        buttons = QHBoxLayout()
        self.save_button = QPushButton()
        buttons.addStretch()
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)
        return content_panel

    def _t(self, key: str, chinese: str) -> str:
        return ui_text(self.language, key, chinese)

    def _apply_localized_identity_defaults(self) -> None:
        if is_english(self.language):
            replacements = (
                (self.assistant_name, {"墨寒"}, "MoHan"),
                (self.user_title, {"主上", "主様"}, "Commander"),
                (self.wake_word, {"墨寒"}, "MoHan"),
            )
        elif is_japanese(self.language):
            replacements = (
                (self.assistant_name, {"MoHan"}, "墨寒"),
                (self.user_title, {"主上", "Commander"}, "主様"),
                (self.wake_word, {"MoHan"}, "墨寒"),
            )
        else:
            replacements = (
                (self.assistant_name, {"MoHan"}, "墨寒"),
                (self.user_title, {"Commander", "主様"}, "主上"),
                (self.wake_word, {"MoHan"}, "墨寒"),
            )
        for editor, defaults, replacement in replacements:
            if editor.text().strip() in defaults:
                editor.setText(replacement)

    def _apply_language(self, _index: int | None = None) -> None:
        previous = self.language
        self.language = str(self.ui_language.currentData() or "zh-TW")
        if previous != self.language:
            self._apply_localized_identity_defaults()
        self._update_wizard_headings()
        self._update_wizard_form()
        self._update_work_type_labels()
        self.note_label.setText(
            self._t(
                "first_run_note",
                "工作平台頁一開始保持空白，由你自行新增公司系統、"
                "協作工具、客戶後台或網站。程式不會替你建立特定商業平台。",
            )
        )
        self.save_button.setText(
            self._t("finish_setup", "完成設定並開始使用")
        )

    def _update_wizard_headings(self) -> None:
        self.setWindowTitle(self._t("first_run_title", "首次啟動設定"))
        self.hero_tagline.setText(
            self._t(
                "first_run_hero_tagline",
                "北宋千年女劍魂，陪你說話、記憶，也陪你把工作做好。",
            )
        )
        self.title_label.setText(
            self._t(
                "first_run_heading",
                "<b>歡迎使用墨寒桌面陪伴工作助理</b>",
            )
        )
        self.intro_label.setText(
            self._t(
                "first_run_intro",
                "先建立你的使用者設定。以下內容日後都能在「設定」頁修改，"
                "不會綁定特定公司、職業或工作平台。",
            )
        )

    def _update_wizard_form(self) -> None:
        labels = {
            "assistant_name": "助理名稱",
            "user_title": "助理對你的稱呼",
            "organization_name": "公司／團隊名稱",
            "window_title": "完整視窗標題",
            "work_type": "工作類型",
            "ui_language": "介面語言",
            "wake_word": "語音喚醒詞",
        }
        for key, chinese in labels.items():
            self.form_labels[key].setText(self._t(key, chinese))
        self.assistant_name.setPlaceholderText(
            self._t("assistant_name_placeholder", "例如：墨寒、Ava、Office Mate")
        )
        self.user_title.setPlaceholderText(
            self._t(
                "user_title_placeholder",
                "助理如何稱呼你，例如：主上、Alex、主管",
            )
        )
        self.organization_name.setPlaceholderText(
            self._t(
                "organization_placeholder",
                "公司、工作室或團隊名稱；個人使用可留空",
            )
        )
        self.window_title.setPlaceholderText(
            self._t(
                "window_title_placeholder",
                "留空時自動顯示「助理名稱．組織名稱」",
            )
        )
        self.wake_word.setPlaceholderText(
            self._t("wake_word_placeholder", "語音喚醒詞，例如：墨寒")
        )

    def _update_work_type_labels(self) -> None:
        for index, value in enumerate(self.WORK_TYPES):
            self.work_type.setItemText(
                index,
                display_label(
                    self.language,
                    value,
                    WORK_TYPE_LABELS,
                    SIMPLIFIED_WORK_TYPE_LABELS,
                    JAPANESE_WORK_TYPE_LABELS,
                ),
                # Internal data remains Taiwan Traditional Chinese so saved
                # profiles and command rules are language-independent.
            )

    def _save(self) -> None:
        assistant = self.assistant_name.text().strip()
        user_title = self.user_title.text().strip()
        if not assistant or not user_title:
            QMessageBox.information(
                self,
                self._t("required_title", "尚缺必要資料"),
                self._t(
                    "required_identity",
                    "請填寫助理名稱，以及助理對你的稱呼。",
                ),
            )
            return
        values = {
            "assistant_name": assistant,
            "user_title": user_title,
            "organization_name": self.organization_name.text().strip(),
            "window_title": self.window_title.text().strip(),
            "work_type": combo_data_or_custom_text(self.work_type, "其他"),
            "ui_language": str(self.ui_language.currentData() or "zh-TW"),
            "wake_word": self.wake_word.text().strip() or assistant,
            "voice_engine": (
                VOICE_ENGINE_SYSTEM
                if self.platform_services.capabilities.system_local_speech
                else VOICE_ENGINE_OPENAI
            ),
            "onboarding_complete": True,
        }
        for key, value in values.items():
            self.db.set_setting(key, value)
        self.db.set_setting(
            "transcription_language",
            transcription_language_for_ui(values["ui_language"]),
        )
        self.db.set_setting(
            "transcription_prompt",
            localized_transcription_prompt(
                values["ui_language"],
                assistant_name=values["assistant_name"],
                user_title=values["user_title"],
                organization_name=values["organization_name"],
                wake_word=values["wake_word"],
            ),
        )
        self.db.set_setting(
            "voice_instructions",
            localized_voice_instructions(
                values["ui_language"],
                VOICE_GENERATION_PROMPT,
            ),
        )
        self.db.set_setting(
            "persona_prompt",
            default_persona_for_language(values["ui_language"]),
        )
        self.accept()


class Dashboard(QDialog):
    speak_requested = Signal(str, str)
    voice_preview_requested = Signal()
    realtime_toggle_requested = Signal(bool)
    state_requested = Signal(str)
    ai_wait_expression_requested = Signal(int, str, float)
    ai_wait_expression_finished = Signal(int)
    work_changed = Signal()
    settings_saved = Signal()
    volume_changed = Signal(int, bool)
    visibility_changed = Signal(bool)
    topmost_mode_changed = Signal(str)
    character_scale_preview = Signal(int)

    def __init__(
        self,
        db: StudioDB,
        dependencies: DashboardDependencies,
        parent=None,
    ):
        super().__init__(parent)
        self._initialize_dashboard_state(db, dependencies)
        self._configure_dashboard_window()
        root = QVBoxLayout(self)
        root.setSizeConstraint(QLayout.SetNoConstraint)
        start_button, stop_button = self._build_dashboard_header(root)
        self._mount_dashboard_tabs(root)
        self._connect_dashboard_signals(
            start_button,
            stop_button,
        )
        self._start_dashboard_timer()
        self.refresh_all()
        self._disable_implicit_default_buttons()
        self._apply_profile_texts()

    def _initialize_dashboard_state(
        self,
        db: StudioDB,
        dependencies: DashboardDependencies,
    ) -> None:
        self.db = db
        self.listener = dependencies.listener
        self.secret_store = dependencies.secret_store
        self.azure_secret_store = dependencies.azure_secret_store
        self.secret_store_factory = (
            dependencies.secret_store_factory
        )
        self.platform_services = (
            dependencies.platform_services
            or current_platform_services()
        )
        self.thread_pool = QThreadPool.globalInstance()
        self.ai_queue: deque[tuple[str, str]] = deque()
        self.ai_busy = False
        self.ai_wait_generation = 0
        self.active_ai_wait_generation = 0
        self.next_expression_metadata: tuple[str, float, str] | None = None
        self.chat_loaded_limit = 50
        self.chat_zoom_percent = int(
            self.db.setting("chat_zoom_percent", 100)
        )
        self.mode = str(db.setting("mode", "工作"))
        self.ui_language = profile_setting(db, "ui_language")
        self.assistant_name = profile_setting(db, "assistant_name")
        self.user_title = profile_setting(db, "user_title")
        self.organization_name = profile_setting(
            db, "organization_name"
        )

    def _configure_dashboard_window(self) -> None:
        db = self.db
        self.setWindowTitle(profile_window_title(db))
        self.resize(900, 660)
        self.setMinimumSize(720, 480)
        self.setStyleSheet(STYLE)
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        # Apply the icon after the native window flags are final. On Windows,
        # changing flags can recreate the native handle used by the taskbar.
        self.setWindowIcon(application_icon())
        self.front_raise_timer = QTimer(self)
        self.front_raise_timer.setSingleShot(True)
        self.front_raise_timer.timeout.connect(self._bring_to_front)
        self.emergency_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.emergency_shortcut.setContext(Qt.ApplicationShortcut)
        self.emergency_shortcut.activated.connect(self._emergency_stop)

    def _build_mode_combo(self) -> QComboBox:
        combo = QComboBox()
        for value in ("工作", "陪伴", "勿擾", "會議", "離席", "休眠"):
            combo.addItem(
                display_label(
                    self.ui_language,
                    value,
                    MODE_LABELS,
                    SIMPLIFIED_MODE_LABELS,
                    JAPANESE_MODE_LABELS,
                ),
                value,
            )
        combo.setCurrentIndex(max(0, combo.findData(self.mode)))
        return combo

    def _build_dashboard_header(
        self,
        root: QVBoxLayout,
    ) -> tuple[QPushButton, QPushButton]:
        header = QHBoxLayout()
        self.mode_combo = self._build_mode_combo()
        self.work_label = QLabel()
        self.work_label.setStyleSheet("font-size: 16px; color: #2f6987;")
        start_btn = QPushButton(self._t("start_work", "開始工作"))
        stop_btn = QPushButton(self._t("stop_work", "結束工作"))
        self.header_title = QLabel(
            f"<b>{html.escape(profile_window_title(self.db))}</b>"
        )
        header.addWidget(self.header_title)
        header.addStretch()
        header.addWidget(QLabel(self._t("mode", "模式")))
        header.addWidget(self.mode_combo)
        header.addWidget(self.work_label)
        header.addWidget(start_btn)
        header.addWidget(stop_btn)
        root.addLayout(header)
        return start_btn, stop_btn

    def _mount_dashboard_tabs(self, root: QVBoxLayout) -> None:
        self.tabs = QTabWidget()
        self.feature_registry = DashboardFeatureRegistry()
        self.feature_registry.register(
            "chat", self._t("tab_chat", "對話"), self._chat_tab
        )
        self.feature_registry.register(
            "today",
            self._t("tab_today", "今日待辦"),
            self._today_tab,
        )
        self.feature_registry.register(
            "platforms",
            self._t("tab_platforms", "工作平台"),
            self._platform_tab,
        )
        self.feature_registry.register(
            "memory",
            self._t("tab_memory", "長期記憶"),
            self._memory_tab,
        )
        self.feature_registry.register(
            "voice", self._t("tab_voice", "聲音"), self._voice_tab
        )
        self.feature_registry.register(
            "permissions",
            self._t("tab_permissions", "電腦權限"),
            self._permissions_tab,
        )
        self.feature_registry.register(
            "settings",
            self._t("tab_settings", "設定"),
            self._settings_tab,
        )
        self.feature_registry.mount(self.tabs)
        root.addWidget(self.tabs, 1)

    def _connect_dashboard_signals(
        self,
        start_button: QPushButton,
        stop_button: QPushButton,
    ) -> None:
        self.mode_combo.currentIndexChanged.connect(
            self._mode_index_changed
        )
        self.tabs.currentChanged.connect(self._tab_changed)
        start_button.clicked.connect(self.start_work)
        stop_button.clicked.connect(self.stop_work)
        self.listener.recognized.connect(self._voice_text)
        self.listener.failed.connect(self._voice_error)
        self.listener.listening_changed.connect(
            self._listening_changed
        )
        self.listener.recording_changed.connect(
            self._recording_changed
        )
        self.listener.status_changed.connect(self.set_voice_phase)
        self.listener.diagnostic_changed.connect(
            self._transcription_diagnostic
        )

    def _start_dashboard_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_work_time)
        self.timer.start(1000)

    def _disable_implicit_default_buttons(self) -> None:
        # QDialog otherwise makes the first push button ("開始工作") the
        # implicit Enter key target. Chat submission must never click an
        # unrelated action button.
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)

    def _t(self, key: str, chinese: str, **values: object) -> str:
        return ui_text(self.ui_language, key, chinese, **values)

    def _tab_changed(self, index: int) -> None:
        if getattr(self, "_today_split_initialized", False):
            return
        current = self.tabs.widget(index)
        if (
            current is None
            or current.findChild(QSplitter, "todaySplitter")
            is not self.today_splitter
        ):
            return
        QTimer.singleShot(0, self._initialize_today_equal_split)

    def _initialize_today_equal_split(self) -> None:
        if getattr(self, "_today_split_initialized", False):
            return
        available = (
            self.today_splitter.height()
            - self.today_splitter.handleWidth()
        )
        if available <= 20:
            QTimer.singleShot(20, self._initialize_today_equal_split)
            return
        first = available // 2
        self.today_splitter.setSizes([first, available - first])
        self._today_split_initialized = True

    def _apply_profile_texts(self) -> None:
        for widget in self.findChildren(QWidget):
            if isinstance(widget, (QLabel, QPushButton, QCheckBox)):
                template = widget.property("profileTextTemplate")
                if template is None:
                    template = widget.text()
                    widget.setProperty("profileTextTemplate", template)
                widget.setText(personalize_text(self.db, str(template)))
            tooltip = widget.property("profileTooltipTemplate")
            if tooltip is None and widget.toolTip():
                tooltip = widget.toolTip()
                widget.setProperty("profileTooltipTemplate", tooltip)
            if tooltip is not None:
                widget.setToolTip(
                    personalize_text(self.db, str(tooltip))
                )
            if isinstance(widget, QLineEdit):
                placeholder = widget.property(
                    "profilePlaceholderTemplate"
                )
                if placeholder is None and widget.placeholderText():
                    placeholder = widget.placeholderText()
                    widget.setProperty(
                        "profilePlaceholderTemplate", placeholder
                    )
                if placeholder is not None:
                    widget.setPlaceholderText(
                        personalize_text(self.db, str(placeholder))
                    )

    def _bring_to_front(self) -> None:
        if not self.isVisible() or self.isMinimized():
            return
        self.raise_()
        self.activateWindow()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.visibility_changed.emit(not self.isMinimized())
        self.front_raise_timer.start(0)

    def hideEvent(self, event) -> None:
        self.visibility_changed.emit(False)
        super().hideEvent(event)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self.visibility_changed.emit(
                self.isVisible() and not self.isMinimized()
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._bring_to_front()
        super().mousePressEvent(event)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        # Windows 原生標題列拖曳不一定送出 Qt 的 mousePressEvent。
        self.front_raise_timer.start(0)

    def _chat_history_controls(self) -> QHBoxLayout:
        history_row = QHBoxLayout()
        self.chat_retention = QLabel(
            self._t(
                "chat_retention",
                "對話保存在本機，不會自動刪除",
            )
        )
        self.chat_retention.setStyleSheet("color: #356d88;")
        self.load_older_chat_btn = QPushButton(
            self._t("load_older_chat", "載入較早對話")
        )
        self.load_older_chat_btn.setToolTip("每次向前載入 50 則本機對話")
        self.manage_chat_btn = QPushButton(
            self._t("manage_chat", "管理／清除對話")
        )
        self.manage_chat_btn.setToolTip("勾選並刪除指定對話，其他內容不受影響")
        self.chat_zoom_down = QPushButton("A－")
        self.chat_zoom_down.setToolTip("縮小對話文字（Ctrl＋滑鼠滾輪向下）")
        self.chat_zoom_down.setFixedWidth(48)
        self.chat_zoom_label = QLabel()
        self.chat_zoom_label.setMinimumWidth(48)
        self.chat_zoom_label.setAlignment(Qt.AlignCenter)
        self.chat_zoom_up = QPushButton("A＋")
        self.chat_zoom_up.setToolTip("放大對話文字（Ctrl＋滑鼠滾輪向上）")
        self.chat_zoom_up.setFixedWidth(48)
        history_row.addWidget(self.chat_retention)
        history_row.addStretch()
        history_row.addWidget(self.load_older_chat_btn)
        history_row.addWidget(self.manage_chat_btn)
        history_row.addWidget(self.chat_zoom_down)
        history_row.addWidget(self.chat_zoom_label)
        history_row.addWidget(self.chat_zoom_up)
        return history_row

    def _connect_chat_controls(self, send_button: QPushButton) -> None:
        send_button.clicked.connect(self.send_chat)
        self.chat_input.returnPressed.connect(self.send_chat)
        self.mic_btn.clicked.connect(self.listener.toggle_listening)
        self.load_older_chat_btn.clicked.connect(
            self.load_older_chat
        )
        self.manage_chat_btn.clicked.connect(
            self.manage_chat_history
        )
        self.chat_zoom_down.clicked.connect(
            lambda: self.adjust_chat_zoom(-1)
        )
        self.chat_zoom_up.clicked.connect(
            lambda: self.adjust_chat_zoom(1)
        )
        self.chat.zoom_step_requested.connect(self.adjust_chat_zoom)

    def _chat_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        history_row = self._chat_history_controls()
        self.chat = ZoomTextBrowser()
        self.chat.setOpenExternalLinks(True)
        self.chat_base_point_size = self.chat.font().pointSizeF()
        if self.chat_base_point_size <= 0:
            self.chat_base_point_size = 10.0
        row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText(
            self._t(
                "chat_placeholder",
                "對寒說話，例如：我開始工作了／幫我記一下……",
            )
        )
        self.mic_btn = QPushButton(self._t("microphone", "🎙 麥克風"))
        send = QPushButton(self._t("send_text", "送出文字"))
        row.addWidget(self.chat_input, 1)
        row.addWidget(self.mic_btn)
        row.addWidget(send)
        layout.addLayout(history_row)
        layout.addWidget(self.chat, 1)
        layout.addLayout(row)
        self.voice_phase = QLabel(
            self._t("voice_ready", "語音狀態：準備就緒")
        )
        self.voice_phase.setStyleSheet("color: #356d88; padding-left: 4px;")
        layout.addWidget(self.voice_phase)
        self._connect_chat_controls(send)
        self.apply_chat_zoom(self.chat_zoom_percent)
        return tab

    def _today_entry_row(
        self,
    ) -> tuple[QHBoxLayout, QPushButton, QPushButton]:
        entry = QHBoxLayout()
        self.todo_input = QLineEdit()
        self.todo_input.setPlaceholderText("輸入待辦標題，例如：完成漫畫第 3 話分鏡")
        self.todo_category = QComboBox()
        self.todo_category.addItems(["漫畫", "文章", "音樂", "貼圖", "出版", "行政", "其他"])
        add = QPushButton("＋ 加入待辦")
        idea = QPushButton("✦ 收入靈感")
        entry.addWidget(self.todo_input, 1)
        entry.addWidget(self.todo_category)
        entry.addWidget(add)
        entry.addWidget(idea)
        return entry, add, idea

    def _today_todo_pane(self) -> QWidget:
        self.todo_feedback = QLabel("")
        self.todo_feedback.setObjectName("entryFeedback")
        todo_header = QHBoxLayout()
        todo_header.addWidget(QLabel("<b>今天要做</b>"))
        self.todo_count = QLabel()
        self.todo_count.setObjectName("sectionCount")
        todo_header.addWidget(self.todo_count)
        todo_header.addStretch()

        self.todo_list = QVBoxLayout()
        self.todo_list.setAlignment(Qt.AlignTop)
        self.todo_list.setContentsMargins(8, 8, 8, 8)
        self.todo_list.setSpacing(7)
        container = QWidget()
        container.setObjectName("todoContainer")
        container.setLayout(self.todo_list)
        self.todo_scroll = QScrollArea()
        self.todo_scroll.setObjectName("todoScroll")
        self.todo_scroll.viewport().setObjectName("todoViewport")
        self.todo_scroll.setWidgetResizable(True)
        self.todo_scroll.setWidget(container)
        todo_pane = QWidget()
        todo_pane.setObjectName("todayPane")
        pane_layout = QVBoxLayout(todo_pane)
        pane_layout.setContentsMargins(0, 0, 0, 0)
        pane_layout.setSpacing(6)
        pane_layout.addLayout(todo_header)
        pane_layout.addWidget(self.todo_scroll, 1)
        return todo_pane

    def _today_idea_pane(
        self,
    ) -> tuple[QWidget, QPushButton, QPushButton]:
        idea_header = QHBoxLayout()
        idea_header.addWidget(QLabel("<b>創作靈感</b>"))
        self.idea_count = QLabel()
        self.idea_count.setObjectName("sectionCount")
        idea_header.addWidget(self.idea_count)
        idea_header.addStretch()
        edit_idea = QPushButton("編輯選取靈感")
        edit_idea.setToolTip("也可以直接雙擊下方任一靈感")
        idea_header.addWidget(edit_idea)
        delete_ideas = QPushButton("刪除勾選靈感")
        delete_ideas.setToolTip("只刪除已勾選的靈感，執行前會再次確認")
        idea_header.addWidget(delete_ideas)
        self.idea_list = QListWidget()
        self.idea_list.setObjectName("ideaList")
        self.idea_list.setMinimumHeight(0)
        self.idea_list.setSpacing(2)
        idea_pane = QWidget()
        idea_pane.setObjectName("todayPane")
        idea_pane_layout = QVBoxLayout(idea_pane)
        idea_pane_layout.setContentsMargins(0, 0, 0, 0)
        idea_pane_layout.setSpacing(6)
        idea_pane_layout.addLayout(idea_header)
        idea_pane_layout.addWidget(self.idea_list, 1)
        return idea_pane, edit_idea, delete_ideas

    def _today_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        entry, add, idea = self._today_entry_row()
        todo_pane = self._today_todo_pane()
        idea_pane, edit_idea, delete_ideas = (
            self._today_idea_pane()
        )
        self.today_splitter = QSplitter(Qt.Vertical)
        self.today_splitter.setObjectName("todaySplitter")
        self.today_splitter.setChildrenCollapsible(False)
        self.today_splitter.addWidget(todo_pane)
        self.today_splitter.addWidget(idea_pane)
        self.today_splitter.setStretchFactor(0, 1)
        self.today_splitter.setStretchFactor(1, 1)
        self._today_split_initialized = False
        layout.addLayout(entry)
        layout.addWidget(self.todo_feedback)
        layout.addWidget(self.today_splitter, 1)
        add.clicked.connect(self.add_todo)
        idea.clicked.connect(self.add_idea)
        edit_idea.clicked.connect(self.edit_selected_idea)
        delete_ideas.clicked.connect(self.delete_checked_ideas)
        self.idea_list.itemDoubleClicked.connect(self.edit_idea_item)
        self.todo_input.returnPressed.connect(self.add_todo)
        return tab

    def _platform_add_controls(
        self,
    ) -> tuple[QHBoxLayout, QPushButton]:
        add_row = QHBoxLayout()
        self.new_platform_name = QLineEdit()
        self.new_platform_name.setPlaceholderText(
            "平台、系統或工具名稱，例如：公司 ERP、Notion、客戶後台"
        )
        self.new_platform_url = QLineEdit()
        self.new_platform_url.setPlaceholderText(
            "網址（可留空，例如：https://example.com）"
        )
        add_platform = QPushButton("新增工作平台")
        add_row.addWidget(self.new_platform_name, 2)
        add_row.addWidget(self.new_platform_url, 2)
        add_row.addWidget(add_platform)
        return add_row, add_platform

    def _platform_filter_controls(
        self,
    ) -> tuple[QHBoxLayout, QPushButton]:
        header = QHBoxLayout()
        self.platform_summary = QLabel()
        self.platform_summary.setObjectName("sectionCount")
        self.platform_filter = QComboBox()
        self.platform_filter.addItems(
            [
                "全部平台",
                "進行中",
                "待補資料／阻礙",
                "已完成／已上架",
                "尚未開始",
            ]
        )
        save_all = QPushButton("立即保存全部")
        header.addWidget(self.platform_summary, 1)
        header.addWidget(QLabel("顯示"))
        header.addWidget(self.platform_filter)
        header.addWidget(save_all)
        return header, save_all

    def _platform_card_scroll(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.platform_card_host = QWidget()
        self.platform_card_layout = QVBoxLayout(
            self.platform_card_host
        )
        self.platform_card_layout.setContentsMargins(0, 4, 6, 4)
        self.platform_card_layout.setSpacing(10)
        self.platform_controls: dict[str, PlatformCardControls] = {}
        self._platform_loading = False
        self.platform_empty = QLabel(
            "尚未建立工作平台。\n"
            "請在上方輸入公司系統、協作工具、客戶後台或任何工作平台。"
        )
        self.platform_empty.setObjectName("emptyState")
        self.platform_empty.setAlignment(Qt.AlignCenter)
        self.platform_empty.setWordWrap(True)
        self.platform_card_layout.addWidget(self.platform_empty)
        self.platform_card_layout.addStretch()
        scroll.setWidget(self.platform_card_host)
        return scroll

    def _platform_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        intro = QLabel(
            "集中管理工作中使用的平台、系統、客戶入口或協作工具。"
            "每位使用者都可以建立自己的工作平台，不預設綁定任何產業。"
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#486d83;")
        layout.addWidget(intro)
        add_row, add_platform = self._platform_add_controls()
        layout.addLayout(add_row)
        header, save_all = self._platform_filter_controls()
        self.platform_feedback = QLabel(
            "修改後會自動保存；也可以使用每張卡片的保存按鈕。"
        )
        self.platform_feedback.setStyleSheet("color:#4c6b82;")
        self.platform_feedback.setWordWrap(True)
        layout.addLayout(header)
        layout.addWidget(self.platform_feedback)
        layout.addWidget(self._platform_card_scroll(), 1)
        add_platform.clicked.connect(self.add_custom_platform)
        self.new_platform_name.returnPressed.connect(self.add_custom_platform)
        self.platform_filter.currentTextChanged.connect(
            self._filter_platform_cards
        )
        save_all.clicked.connect(lambda: self.save_platforms())
        self._reload_platform_cards()
        self._refresh_platform_summary()
        return tab

    def _create_platform_card(self, platform: str, row=None) -> None:
        controls, grid = self._build_platform_card_controls()
        self._populate_platform_card_grid(grid, platform, controls)
        self._connect_platform_card(platform, controls)
        self.platform_controls[platform] = controls
        self.platform_card_layout.insertWidget(
            max(0, self.platform_card_layout.count() - 1),
            controls.card,
        )
        if row is not None:
            self._load_platform_row(row)

    def _build_platform_card_controls(
        self,
    ) -> tuple[PlatformCardControls, QGridLayout]:
        card = QFrame()
        card.setObjectName("platformCard")
        card.setStyleSheet(
            "QFrame#platformCard{background:#f5f8fb;"
            "border:1px solid #c3d0dc;border-radius:12px;}"
        )
        grid = QGridLayout(card)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        status = QComboBox()
        status.addItems(PLATFORM_STATUSES)
        controls = PlatformCardControls(
            card=card,
            status=status,
            item_name=self._platform_editor(
                "目前負責的工作項目、專案或案件"
            ),
            missing=self._platform_editor(
                "待補資料、等待他人回覆或其他阻礙；沒有可留空"
            ),
            next_action=self._platform_editor("下一個具體動作與期限"),
            notes=self._platform_editor("備註、規則、聯絡窗口或其他補充"),
            url=self._platform_editor("https://…（可留空）"),
            validation=QLabel(),
            updated=QLabel("尚未保存"),
            save_button=QPushButton("保存此平台"),
            timer=QTimer(self),
        )
        controls.validation.setWordWrap(True)
        controls.updated.setStyleSheet("color:#64788a;font-size:11px;")
        controls.timer.setSingleShot(True)
        controls.timer.setInterval(750)
        return controls, grid

    @staticmethod
    def _platform_editor(placeholder: str) -> QLineEdit:
        editor = QLineEdit()
        editor.setPlaceholderText(placeholder)
        return editor

    def _populate_platform_card_grid(
        self,
        grid: QGridLayout,
        platform: str,
        controls: PlatformCardControls,
    ) -> None:
        name = QLabel(f"<b>{html.escape(platform)}</b>")
        name.setStyleSheet("font-size:15px;color:#17344f;")
        grid.addWidget(name, 0, 0)
        grid.addWidget(controls.status, 0, 1)
        grid.addWidget(controls.updated, 0, 2)
        grid.addLayout(
            self._platform_card_actions(platform, controls.save_button),
            0,
            3,
        )
        fields = (
            ("工作項目／專案", controls.item_name),
            ("待補資料／阻礙", controls.missing),
            ("下一步", controls.next_action),
            ("備註", controls.notes),
            ("網址", controls.url),
        )
        for row, (label, editor) in enumerate(fields, start=1):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(editor, row, 1, 1, 3)
        grid.addWidget(controls.validation, 6, 0, 1, 4)

    def _platform_card_actions(
        self,
        platform: str,
        save_button: QPushButton,
    ) -> QHBoxLayout:
        open_button = QPushButton("開啟網站／工具")
        delete_button = QPushButton("刪除平台")
        delete_button.setObjectName("dangerButton")
        open_button.clicked.connect(
            lambda _checked=False, name=platform: self.open_platform(name)
        )
        delete_button.clicked.connect(
            lambda _checked=False, name=platform: (
                self.delete_custom_platform(name)
            )
        )
        actions = QHBoxLayout()
        for button in (open_button, save_button, delete_button):
            actions.addWidget(button)
        return actions

    def _connect_platform_card(
        self,
        platform: str,
        controls: PlatformCardControls,
    ) -> None:
        controls.status.currentTextChanged.connect(
            lambda _value, name=platform: self._platform_changed(name)
        )
        for editor in controls.editors:
            editor.textChanged.connect(
                lambda _value, name=platform: self._platform_changed(name)
            )
        controls.save_button.clicked.connect(
            lambda _checked=False, name=platform: self.save_platform(name)
        )
        controls.timer.timeout.connect(
            lambda name=platform: self.save_platform(name, silent=True)
        )

    def _load_platform_row(self, row) -> None:
        platform = row["platform"]
        controls = self.platform_controls.get(platform)
        if controls is None:
            return
        status = to_taiwan_traditional(row["status"])
        if controls.status.findText(status) < 0:
            controls.status.addItem(status)
        controls.status.setCurrentText(status)
        for field in ("item_name", "missing", "next_action", "notes", "url"):
            editor = getattr(controls, field)
            editor.setText(to_taiwan_traditional(row[field] or ""))
        controls.dirty = False
        controls.save_button.setText("保存此平台")
        controls.updated.setText(
            self._format_platform_updated(row["updated_at"])
        )
        self._validate_platform(platform)

    def _clear_platform_cards(self) -> None:
        for controls in self.platform_controls.values():
            controls.timer.stop()
            controls.card.deleteLater()
        self.platform_controls.clear()

    def _reload_platform_cards(self) -> None:
        self._platform_loading = True
        try:
            self._clear_platform_cards()
            for row in self.db.platform_rows():
                self._create_platform_card(row["platform"], row)
        finally:
            self._platform_loading = False
        self.platform_empty.setVisible(not self.platform_controls)
        self._refresh_platform_summary()
        self._filter_platform_cards()

    @staticmethod
    def _normalize_platform_url(value: str) -> str:
        value = value.strip()
        if value and "://" not in value:
            value = "https://" + value
        return value

    def add_custom_platform(self) -> None:
        platform = to_taiwan_traditional(self.new_platform_name.text().strip())
        url = self._normalize_platform_url(self.new_platform_url.text())
        if not platform:
            self.platform_feedback.setText("請先輸入平台、系統或工具名稱。")
            self.new_platform_name.setFocus()
            return
        if not self.db.add_platform(platform, url):
            self.platform_feedback.setText(
                f"「{platform}」已存在，請使用不同名稱。"
            )
            return
        row = next(
            row
            for row in self.db.platform_rows()
            if row["platform"].casefold() == platform.casefold()
        )
        self._platform_loading = True
        try:
            self._create_platform_card(row["platform"], row)
        finally:
            self._platform_loading = False
        self.new_platform_name.clear()
        self.new_platform_url.clear()
        self.platform_empty.hide()
        self.platform_feedback.setText(f"已新增工作平台：{platform}")
        self._refresh_platform_summary()
        self._filter_platform_cards()

    def delete_custom_platform(self, platform: str) -> None:
        answer = QMessageBox.question(
            self,
            "刪除工作平台",
            f"確定刪除「{platform}」及其工作進度嗎？此動作無法復原。",
        )
        if answer != QMessageBox.Yes:
            return
        controls = self.platform_controls.get(platform)
        if controls is not None:
            controls.timer.stop()
        if not self.db.delete_platform(platform):
            self.platform_feedback.setText(f"找不到工作平台：{platform}")
            return
        if controls is not None:
            controls.card.deleteLater()
            del self.platform_controls[platform]
        self.platform_empty.setVisible(not self.platform_controls)
        self.platform_feedback.setText(f"已刪除工作平台：{platform}")
        self._refresh_platform_summary()
        self._filter_platform_cards()

    def _memory_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        entry_row, add_button = self._memory_entry_row()
        filter_row, edit_button, delete_button = (
            self._memory_filter_row()
        )
        action_row, clear_button, optimize_button, archives_button = (
            self._memory_action_row()
        )
        self.memory_list = self._memory_list_widget()
        self.auto_memory = self._memory_auto_checkbox()
        layout.addWidget(self._memory_intro())
        layout.addLayout(entry_row)
        layout.addLayout(filter_row)
        layout.addWidget(self.memory_list, 1)
        layout.addWidget(self.auto_memory)
        layout.addLayout(action_row)
        self._connect_memory_actions(
            MemoryTabActions(
                add=add_button,
                edit=edit_button,
                delete=delete_button,
                clear=clear_button,
                optimize=optimize_button,
                archives=archives_button,
            )
        )
        return tab

    @staticmethod
    def _memory_intro() -> QLabel:
        intro = QLabel(
            "墨寒只保存主上允許留下的人物、偏好、目標、工作流程與"
            "重要日期。記憶存於本機，可分類瀏覽、逐項編輯或刪除。"
        )
        intro.setWordWrap(True)
        return intro

    def _memory_entry_row(self) -> tuple[QHBoxLayout, QPushButton]:
        entry = QHBoxLayout()
        self.memory_input = QLineEdit()
        self.memory_input.setPlaceholderText("例如：主上偏好先完成漫畫，再處理行政工作")
        self.memory_category = QComboBox()
        self.memory_category.addItems(MEMORY_CATEGORIES)
        self.memory_category.setCurrentText("偏好")
        add_button = QPushButton("讓寒記住")
        entry.addWidget(self.memory_input, 1)
        entry.addWidget(self.memory_category)
        entry.addWidget(add_button)
        return entry, add_button

    def _memory_filter_row(
        self,
    ) -> tuple[QHBoxLayout, QPushButton, QPushButton]:
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("分類瀏覽"))
        self.memory_filter = QComboBox()
        self.memory_filter.addItem("全部記憶", "")
        for category in MEMORY_CATEGORIES:
            self.memory_filter.addItem(category, category)
        self.memory_count = QLabel()
        self.memory_count.setObjectName("sectionCount")
        filter_row.addWidget(self.memory_filter)
        filter_row.addWidget(self.memory_count)
        filter_row.addStretch()
        edit_button = QPushButton("編輯選取記憶")
        edit_button.setToolTip("也可以直接雙擊下方任一記憶")
        delete_button = QPushButton("刪除勾選記憶")
        delete_button.setToolTip("只刪除已勾選的記憶，執行前會再次確認")
        filter_row.addWidget(edit_button)
        filter_row.addWidget(delete_button)
        return filter_row, edit_button, delete_button

    @staticmethod
    def _memory_list_widget() -> QListWidget:
        memory_list = QListWidget()
        memory_list.setObjectName("memoryList")
        memory_list.setSpacing(3)
        return memory_list

    @staticmethod
    def _memory_action_row(
    ) -> tuple[QHBoxLayout, QPushButton, QPushButton, QPushButton]:
        actions = QHBoxLayout()
        clear_button = QPushButton("清除全部記憶")
        optimize_button = QPushButton("安全整理記憶")
        optimize_button.setToolTip(
            "合併低重要度重複內容，超量舊記憶只會先封存"
        )
        archives_button = QPushButton("查看已封存記憶")
        actions.addWidget(clear_button)
        actions.addWidget(optimize_button)
        actions.addWidget(archives_button)
        actions.addStretch()
        return (
            actions,
            clear_button,
            optimize_button,
            archives_button,
        )

    def _memory_auto_checkbox(self) -> QCheckBox:
        checkbox = QCheckBox(
            "從「請記住／我喜歡／我習慣」等明確說法自動建立記憶"
        )
        checkbox.setChecked(bool(self.db.setting("auto_memory", True)))
        return checkbox

    def _connect_memory_actions(self, actions: MemoryTabActions) -> None:
        actions.add.clicked.connect(self.add_memory)
        self.memory_input.returnPressed.connect(self.add_memory)
        actions.edit.clicked.connect(self.edit_selected_memory)
        actions.delete.clicked.connect(self.delete_checked_memories)
        self.memory_list.itemDoubleClicked.connect(self.edit_memory_item)
        self.memory_filter.currentIndexChanged.connect(self.refresh_memories)
        actions.clear.clicked.connect(self.clear_memories)
        actions.optimize.clicked.connect(self.optimize_memories)
        actions.archives.clicked.connect(self.show_archived_memories)

    @staticmethod
    def _form_scroll_page() -> tuple[QScrollArea, QFormLayout]:
        page = QScrollArea()
        page.setObjectName("formScrollPage")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page.viewport().setStyleSheet("background:#ffffff;")
        content = QWidget()
        content.setObjectName("formScrollContent")
        content.setStyleSheet(
            "QWidget#formScrollContent{background:#ffffff;}"
        )
        form = QFormLayout(content)
        page.setWidget(content)
        return page, form

    @staticmethod
    def _editable_combo(
        items: Iterable[str],
        current_text: str,
    ) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(list(items))
        combo.setCurrentText(current_text)
        return combo

    @staticmethod
    def _select_combo_data(combo: QComboBox, value: str) -> None:
        combo.setCurrentIndex(max(0, combo.findData(value)))

    def _initialize_transcription_controls(
        self,
        capabilities: PlatformCapabilities,
    ) -> None:
        self.speech_recognition = self._speech_recognition_combo(
            capabilities
        )
        self.transcription_model = self._editable_combo(
            ("gpt-4o-mini-transcribe", "gpt-4o-transcribe"),
            str(
                self.db.setting(
                    "transcription_model",
                    SpeechListener.TRANSCRIPTION_MODEL,
                )
            ),
        )
        self.transcription_language = self._transcription_language_input()
        self.transcription_prompt = self._transcription_prompt_input()
        self.windows_transcription_fallback = (
            self._transcription_fallback_checkbox(capabilities)
        )
        self.transcription_diagnostic = (
            self._transcription_diagnostic_label()
        )

    def _speech_recognition_combo(
        self,
        capabilities: PlatformCapabilities,
    ) -> QComboBox:
        combo = QComboBox()
        combo.addItem(
            self._t(
                "openai_recognition",
                "OpenAI 高準確辨識（推薦）",
            ),
            "OpenAI 高準確辨識（推薦）",
        )
        if capabilities.offline_speech_recognition:
            combo.addItem(
                self._t("windows_recognition", "Windows 離線辨識"),
                "Windows 離線辨識",
            )
        self._select_combo_data(
            combo,
            str(
                self.db.setting(
                    "speech_recognition",
                    "OpenAI 高準確辨識（推薦）",
                )
            ),
        )
        return combo

    def _transcription_language_input(self) -> QLineEdit:
        language = QLineEdit(
            str(self.db.setting("transcription_language", "zh"))
        )
        language.setPlaceholderText(
            self._t(
                "transcription_language_placeholder",
                "ISO 語言代碼；留空可讓模型自動判斷",
            )
        )
        return language

    def _transcription_prompt_input(self) -> QTextEdit:
        prompt = QTextEdit()
        default_prompt = localized_transcription_prompt(
            self.ui_language,
            assistant_name=self.assistant_name,
            user_title=self.user_title,
            organization_name=self.organization_name,
            wake_word=profile_setting(self.db, "wake_word"),
        )
        prompt.setPlainText(
            str(self.db.setting("transcription_prompt", default_prompt))
        )
        prompt.setMaximumHeight(100)
        return prompt

    def _transcription_fallback_checkbox(
        self,
        capabilities: PlatformCapabilities,
    ) -> QCheckBox:
        fallback = QCheckBox(
            self._t(
                "openai_fallback",
                "OpenAI 失敗時使用 Windows 離線辨識",
            )
        )
        available = capabilities.offline_speech_recognition
        fallback.setChecked(
            bool(
                available
                and self.db.setting(
                    "windows_transcription_fallback",
                    True,
                )
            )
        )
        if available:
            return fallback
        fallback.setText(
            self._t(
                "platform_offline_fallback_unavailable",
                f"{capabilities.display_name} 離線辨識尚未完成實機驗證",
                platform=capabilities.display_name,
            )
        )
        fallback.setEnabled(False)
        return fallback

    def _transcription_diagnostic_label(self) -> QLabel:
        diagnostic = QLabel(
            str(
                self.db.setting(
                    "last_transcription_diagnostic",
                    self._t(
                        "no_transcription_error",
                        "尚無轉錄錯誤紀錄",
                    ),
                )
            )
        )
        diagnostic.setWordWrap(True)
        diagnostic.setStyleSheet("color:#2f6987; padding:6px;")
        return diagnostic

    def _initialize_voice_provider_controls(
        self,
        capabilities: PlatformCapabilities,
    ) -> None:
        self.voice_engine = self._voice_engine_combo(capabilities)
        self.windows_voice = self._windows_voice_combo(capabilities)
        migrate_voice_defaults(self.db)
        self.tts_voice = self._editable_combo(
            TTS_VOICES,
            str(
                self.db.setting(
                    "tts_voice",
                    self.db.setting("cloud_voice", "coral"),
                )
            ),
        )
        self.realtime_voice = self._editable_combo(
            REALTIME_VOICES,
            str(self.db.setting("realtime_voice", "coral")),
        )
        self._initialize_azure_voice_controls(capabilities)
        self.cloud_voice = self.tts_voice

    def _voice_engine_combo(
        self,
        capabilities: PlatformCapabilities,
    ) -> QComboBox:
        combo = QComboBox()
        if capabilities.system_local_speech:
            combo.addItem(
                self._t("windows_engine", "Windows 本機語音"),
                VOICE_ENGINE_SYSTEM,
            )
        cloud_engines = (
            (
                VOICE_ENGINE_OPENAI,
                self._t("openai_engine", "OpenAI 自然語音"),
            ),
            (
                VOICE_ENGINE_REALTIME,
                self._t("realtime_engine", "Realtime 即時語音"),
            ),
            (
                VOICE_ENGINE_AZURE,
                self._t("azure_engine", "Azure Speech（預覽）"),
            ),
        )
        for key, label in cloud_engines:
            combo.addItem(label, key)
        self._select_combo_data(
            combo,
            migrate_speech_provider_setting(self.db),
        )
        return combo

    def _windows_voice_combo(
        self,
        capabilities: PlatformCapabilities,
    ) -> QComboBox:
        combo = QComboBox()
        available = self._available_windows_voices(capabilities)
        if not available:
            combo.addItem(
                self._unavailable_windows_voice_label(capabilities),
                "",
            )
            combo.model().item(0).setEnabled(False)
        if not capabilities.system_local_speech:
            combo.setEnabled(False)
        saved_voice = str(self.db.setting("windows_voice", ""))
        preferred, force_default = self._preferred_windows_voice(
            available,
            saved_voice,
        )
        for name, culture in sorted(
            available,
            key=lambda voice: (
                voice[0] != preferred,
                voice[1].lower(),
                voice[0].lower(),
            ),
        ):
            combo.addItem(
                self._windows_voice_label(name, culture),
                name,
            )
        self._persist_windows_voice_migration(
            preferred,
            saved_voice,
            force_default,
        )
        preferred_index = combo.findData(preferred)
        if preferred_index >= 0:
            combo.setCurrentIndex(preferred_index)
        return combo

    @staticmethod
    def _available_windows_voices(
        capabilities: PlatformCapabilities,
    ) -> tuple[tuple[str, str], ...]:
        if not capabilities.system_local_speech:
            return ()
        return tuple(
            (name, culture)
            for name, culture in windows_voices()
            if not is_known_male_windows_voice(name)
        )

    def _unavailable_windows_voice_label(
        self,
        capabilities: PlatformCapabilities,
    ) -> str:
        if capabilities.system_local_speech:
            return self._t(
                "no_female_voice",
                "未偵測到已確認的女性 Windows 聲音",
            )
        return self._t(
            "platform_local_voice_unavailable",
            f"{capabilities.display_name} 本機語音尚未完成實機驗證",
            platform=capabilities.display_name,
        )

    def _preferred_windows_voice(
        self,
        available: tuple[tuple[str, str], ...],
        saved_voice: str,
    ) -> tuple[str, bool]:
        yating_available = any(
            "yating" in name.lower() and culture.lower() == "zh-tw"
            for name, culture in available
        )
        force_default = (
            self.ui_language.lower() in {"zh", "zh-tw"}
            and yating_available
            and not bool(
                self.db.setting(
                    "onecore_yating_v181_migrated",
                    False,
                )
            )
        )
        preferred = preferred_windows_voice(
            available,
            "" if force_default else saved_voice,
            self.ui_language,
        )
        return preferred, force_default

    @staticmethod
    def _windows_voice_label(name: str, culture: str) -> str:
        source = (
            "OneCore" if name.startswith("OneCore::") else "Desktop SAPI"
        )
        short_name = next(
            (
                keyword
                for keyword in ("Yating", "Hanhan")
                if keyword.lower() in name.lower()
            ),
            name,
        )
        return f"{short_name}（{culture}，{source}）"

    def _persist_windows_voice_migration(
        self,
        preferred: str,
        saved_voice: str,
        force_default: bool,
    ) -> None:
        if force_default:
            self.db.set_setting("onecore_yating_v181_migrated", True)
        if preferred and (force_default or not saved_voice):
            self.db.set_setting("windows_voice", preferred)

    def _initialize_azure_voice_controls(
        self,
        capabilities: PlatformCapabilities,
    ) -> None:
        azure_voices = azure_female_voices(self.ui_language)
        saved_voice = str(
            self.db.setting("azure_speech_voice", azure_voices[0])
        )
        selected_voice = (
            saved_voice if saved_voice in azure_voices else azure_voices[0]
        )
        self.azure_voice = self._editable_combo(
            azure_voices,
            selected_voice,
        )
        self.azure_voice.setEditable(False)
        self.azure_region = QLineEdit(
            str(self.db.setting("azure_speech_region", ""))
        )
        self.azure_region.setPlaceholderText(
            self._t("azure_region_placeholder", "例如：eastasia")
        )
        self._initialize_azure_key_controls(capabilities)

    def _initialize_azure_key_controls(
        self,
        capabilities: PlatformCapabilities,
    ) -> None:
        self.azure_key_input = QLineEdit()
        self.azure_key_input.setEchoMode(QLineEdit.Password)
        secure_storage = capabilities.secure_secret_storage
        key_saved = bool(
            secure_storage
            and self.azure_secret_store
            and self.azure_secret_store.load()
        )
        if secure_storage:
            placeholder = (
                self._t(
                    "azure_key_saved",
                    "已由 Windows 加密保存（留空不變）",
                )
                if key_saved
                else self._t(
                    "azure_key_missing",
                    "貼上 Azure Speech 資源金鑰",
                )
            )
        else:
            placeholder = self._t(
                "platform_secret_storage_unavailable",
                f"{capabilities.display_name} 安全金鑰保存尚未完成實機驗證",
                platform=capabilities.display_name,
            )
            self.azure_key_input.setEnabled(False)
        self.azure_key_input.setPlaceholderText(placeholder)
        self.azure_clear_key = QPushButton(
            self._t("azure_remove_key", "移除 Azure Speech 金鑰")
        )
        self.azure_clear_key.clicked.connect(
            self.clear_azure_speech_key
        )
        self.azure_clear_key.setEnabled(secure_storage)

    def _initialize_realtime_controls(self) -> None:
        self.realtime_model = self._editable_combo(
            ("gpt-realtime-2.1-mini", "gpt-realtime-2.1"),
            str(
                self.db.setting(
                    "realtime_model",
                    "gpt-realtime-2.1-mini",
                )
            ),
        )
        self.realtime_transcription_model = self._editable_combo(
            ("gpt-4o-mini-transcribe", "gpt-4o-transcribe"),
            str(
                self.db.setting(
                    "realtime_transcription_model",
                    "gpt-4o-mini-transcribe",
                )
            ),
        )
        self.realtime_noise_reduction = (
            self._realtime_noise_reduction_combo()
        )
        self.realtime_turn_detection = (
            self._realtime_turn_detection_combo()
        )
        self.realtime_echo_guard = self._realtime_echo_guard_checkbox()
        self.realtime_hybrid_transcription = (
            self._realtime_hybrid_transcription_checkbox()
        )

    def _realtime_noise_reduction_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem(
            self._t("near_field", "近距離麥克風（推薦）"),
            "near_field",
        )
        combo.addItem(
            self._t("far_field", "遠距離／筆電麥克風"),
            "far_field",
        )
        combo.addItem(
            self._t("noise_off", "關閉降噪"),
            "off",
        )
        self._select_combo_data(
            combo,
            str(
                self.db.setting(
                    "realtime_noise_reduction",
                    "near_field",
                )
            ),
        )
        return combo

    def _realtime_turn_detection_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem(
            self._t(
                "stable_vad",
                "穩定完整（推薦，停頓約 0.85 秒）",
            ),
            "server_vad",
        )
        combo.addItem(
            self._t(
                "semantic_vad",
                "自然語意（可能提早切段）",
            ),
            "semantic_vad",
        )
        self._select_combo_data(
            combo,
            str(
                self.db.setting(
                    "realtime_turn_detection",
                    "server_vad",
                )
            ),
        )
        return combo

    def _realtime_echo_guard_checkbox(self) -> QCheckBox:
        checkbox = QCheckBox(
            self._t(
                "echo_guard_option",
                "防止墨寒把自己的聲音誤認成主上（推薦）",
            )
        )
        checkbox.setChecked(
            bool(self.db.setting("realtime_echo_guard", True))
        )
        checkbox.setToolTip(
            "墨寒說話時暫停上傳麥克風，播放結束後再恢復；"
            "啟用時無法在她說話途中插話。"
        )
        return checkbox

    def _realtime_hybrid_transcription_checkbox(self) -> QCheckBox:
        checkbox = QCheckBox(
            self._t(
                "hybrid_transcript",
                "畫面採用高精度整句轉錄（推薦）",
            )
        )
        checkbox.setChecked(
            bool(
                self.db.setting(
                    "realtime_hybrid_transcription",
                    True,
                )
            )
        )
        checkbox.setToolTip(
            "Realtime 保留原生音訊理解；每句說完後，畫面文字改用"
            "完整錄音的 OpenAI 高精度轉錄。成功後才允許墨寒回答。"
        )
        return checkbox

    def _initialize_voice_rate_control(self) -> QWidget:
        self.voice_rate = QSpinBox()
        self.voice_rate.setRange(-5, 5)
        self.voice_rate.setValue(int(self.db.setting("voice_rate", -1)))
        self.voice_rate.setSuffix(self._t("level_suffix", " 級"))
        self.voice_rate.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.voice_rate.lineEdit().setReadOnly(True)
        self.voice_rate.setAlignment(Qt.AlignCenter)
        control = QWidget()
        layout = QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.voice_rate_down = QPushButton("－")
        self.voice_rate_down.setToolTip(
            self._t("rate_down", "降低本機朗讀速度")
        )
        self.voice_rate_down.setFixedWidth(48)
        self.voice_rate_up = QPushButton("＋")
        self.voice_rate_up.setToolTip(
            self._t("rate_up", "提高本機朗讀速度")
        )
        self.voice_rate_up.setFixedWidth(48)
        self.voice_rate_down.clicked.connect(self.voice_rate.stepDown)
        self.voice_rate_up.clicked.connect(self.voice_rate.stepUp)
        layout.addWidget(self.voice_rate_down)
        layout.addWidget(self.voice_rate, 1)
        layout.addWidget(self.voice_rate_up)
        return control

    def _initialize_voice_volume_control(self) -> QWidget:
        self.voice_volume = QSlider(Qt.Horizontal)
        self.voice_volume.setRange(0, 160)
        self.voice_volume.setSingleStep(5)
        self.voice_volume.setPageStep(10)
        self.voice_volume.setValue(
            int(self.db.setting("voice_volume_percent", 125))
        )
        self.voice_volume_label = QLabel()
        self.voice_volume_label.setMinimumWidth(52)
        self.voice_volume_label.setAlignment(Qt.AlignCenter)
        self.voice_muted = QCheckBox(self._t("mute", "靜音"))
        self.voice_muted.setChecked(
            bool(self.db.setting("voice_muted", False))
        )
        control = QWidget()
        layout = QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.voice_volume, 1)
        layout.addWidget(self.voice_volume_label)
        layout.addWidget(self.voice_muted)
        self.voice_volume.valueChanged.connect(
            self._voice_volume_changed
        )
        self.voice_muted.toggled.connect(self._voice_volume_changed)
        self._update_voice_volume_label()
        return control

    def _initialize_voice_action_controls(self) -> None:
        self.voice_instructions = QLineEdit(
            str(
                self.db.setting(
                    "voice_instructions",
                    VOICE_GENERATION_PROMPT,
                )
            )
        )
        self.voice_preview_button = QPushButton(
            self._t("preview_voice", "試聽：主上，妾在。")
        )
        self.voice_preview_button.clicked.connect(self._preview_voice)
        self.realtime_status = QLabel(
            self._t("realtime_disconnected", "Realtime：未連線")
        )
        self.realtime_btn = QPushButton(
            self._t("start_realtime", "啟動 Realtime 自然對話")
        )
        self.realtime_btn.setCheckable(True)
        self.realtime_btn.toggled.connect(
            self.realtime_toggle_requested.emit
        )

    @staticmethod
    def _voice_note(text: str) -> QLabel:
        note = QLabel(text)
        note.setWordWrap(True)
        return note

    def _recognition_note(
        self,
        capabilities: PlatformCapabilities,
    ) -> QLabel:
        if capabilities.offline_speech_recognition:
            text = self._t(
                "recognition_note",
                "單次麥克風預設使用 gpt-4o-mini-transcribe 與墨寒專用繁中詞庫；"
                "停止說話約 0.85 秒即送出，最長 10 秒；收音時再次點擊"
                "麥克風可立即送出。Windows 備援可自行關閉。",
            )
        else:
            text = self._t(
                "recognition_note_no_offline",
                "單次麥克風使用 OpenAI 高準確辨識；此平台的離線辨識尚未"
                "完成實機驗證，因此不會顯示或假裝提供離線備援。",
            )
        return self._voice_note(text)

    def _windows_voice_note(
        self,
        capabilities: PlatformCapabilities,
    ) -> QLabel:
        if capabilities.system_local_speech:
            text = self._t(
                "female_voice_note",
                "離線聲音僅列出 Windows 已明確標示為女性的聲音；"
                "台灣繁中仍優先使用 Yating（zh-TW）。",
            )
        else:
            text = self._t(
                "platform_local_voice_note",
                f"{capabilities.display_name} 本機語音尚未完成實機驗證；"
                "未支援前不會顯示其他平台的聲音或宣稱有離線朗讀。",
                platform=capabilities.display_name,
            )
        return self._voice_note(text)

    def _azure_voice_note(
        self,
        capabilities: PlatformCapabilities,
    ) -> QLabel:
        if capabilities.system_local_speech:
            text = self._t(
                "azure_speech_note",
                "預覽功能；需自備 Azure Speech 資源金鑰與相符區域。"
                "只列官方標示為女性的繁中、簡中或英文聲線；失敗時"
                "立即回到 Windows 本機女聲。F0 免費額度及計費以"
                " Microsoft 當期規則為準。",
            )
        else:
            text = self._t(
                "azure_speech_note_no_local_fallback",
                "預覽功能；需自備 Azure Speech 資源金鑰與相符區域。"
                "此平台尚無已驗證的本機語音，服務失敗時會安全停止播放，"
                "不會假裝已切換到離線聲音。",
            )
        return self._voice_note(text)

    def _model_access_note(self) -> QLabel:
        return self._voice_note(
            self._t(
                "model_access_note",
                "若後台已勾選模型但仍顯示無權限，請確認勾選模型與建立 API Key "
                "的是同一個 Project；在該 Project 重新建立金鑰後，到「設定」"
                "頁重新儲存。",
            )
        )

    def _echo_guard_note(self) -> QLabel:
        return self._voice_note(
            self._t(
                "echo_guard_note",
                "防回音開啟時，墨寒說話期間會停止上傳麥克風，並清除本機"
                "與伺服器端殘留音訊；結束約一秒後才恢復。對話頁只顯示"
                "高精度整句轉錄的最終結果，不顯示辨識中的暫定文字。",
            )
        )

    def _realtime_note(self) -> QLabel:
        return self._voice_note(
            self._t(
                "realtime_note",
                "Realtime 會持續使用麥克風。預設以穩定切段保留句首 500 毫秒，"
                "停止約 0.85 秒後才判定說完。高精度整句轉錄開啟時，"
                "Realtime 原生模型負責理解聲音，螢幕文字則使用與單次"
                "麥克風相同的 gpt-4o-mini-transcribe 與繁中詞庫；"
                "不會同時收取 Realtime 內建字幕的第二筆轉錄費。"
                "啟動時才會傳送聲音；關閉後立即停止。"
                "mini 較省費用並已設為預設；完整版適合品質優先時使用。",
            )
        )

    def _add_transcription_rows(
        self,
        form: QFormLayout,
        capabilities: PlatformCapabilities,
    ) -> None:
        form.addRow(
            self._t("speech_recognition", "單次麥克風辨識"),
            self.speech_recognition,
        )
        form.addRow(
            self._t("transcription_model", "轉錄模型"),
            self.transcription_model,
        )
        form.addRow(
            self._t("transcription_language", "轉錄語言"),
            self.transcription_language,
        )
        form.addRow(
            self._t("transcription_prompt", "轉錄提示／常用詞"),
            self.transcription_prompt,
        )
        fallback_label = (
            self._t(
                "windows_transcription_fallback",
                "Windows 備援",
            )
            if capabilities.offline_speech_recognition
            else self._t("offline_fallback", "離線備援")
        )
        form.addRow(fallback_label, self.windows_transcription_fallback)
        form.addRow(
            self._t("last_transcription", "最近一次轉錄"),
            self.transcription_diagnostic,
        )
        form.addRow("", self._recognition_note(capabilities))

    def _add_voice_provider_rows(
        self,
        form: QFormLayout,
        capabilities: PlatformCapabilities,
    ) -> None:
        form.addRow(
            self._t("voice_engine", "朗讀方式"),
            self.voice_engine,
        )
        voice_label = (
            self._t("windows_voice", "Windows 聲音")
            if capabilities.system_local_speech
            else self._t(
                "platform_local_voice",
                f"{capabilities.display_name} 本機聲音",
                platform=capabilities.display_name,
            )
        )
        form.addRow(voice_label, self.windows_voice)
        form.addRow("", self._windows_voice_note(capabilities))
        form.addRow(
            self._t("tts_voice", "OpenAI 文字朗讀聲音"),
            self.tts_voice,
        )
        form.addRow(
            self._t("azure_voice", "Azure Speech 女性聲線"),
            self.azure_voice,
        )
        form.addRow(
            self._t("azure_region", "Azure Speech 區域"),
            self.azure_region,
        )
        form.addRow(
            self._t("azure_key", "Azure Speech 金鑰"),
            self.azure_key_input,
        )
        form.addRow("", self.azure_clear_key)
        form.addRow("", self._azure_voice_note(capabilities))

    def _add_realtime_rows(self, form: QFormLayout) -> None:
        form.addRow(
            self._t("realtime_voice", "Realtime 對話聲音"),
            self.realtime_voice,
        )
        form.addRow(
            self._t("realtime_model", "Realtime 模型"),
            self.realtime_model,
        )
        form.addRow(
            self._t(
                "realtime_transcription_model",
                "Realtime 轉錄模型",
            ),
            self.realtime_transcription_model,
        )
        form.addRow(
            self._t("realtime_noise", "Realtime 麥克風降噪"),
            self.realtime_noise_reduction,
        )
        form.addRow(
            self._t("realtime_turn", "Realtime 發言切段"),
            self.realtime_turn_detection,
        )
        form.addRow(
            self._t(
                "realtime_screen_transcript",
                "Realtime 畫面轉錄",
            ),
            self.realtime_hybrid_transcription,
        )
        form.addRow("", self._model_access_note())
        form.addRow(
            self._t("echo_guard", "防回音"),
            self.realtime_echo_guard,
        )
        form.addRow("", self._echo_guard_note())

    def _add_voice_output_rows(
        self,
        form: QFormLayout,
        rate_control: QWidget,
        volume_control: QWidget,
    ) -> None:
        form.addRow(
            self._t("local_rate", "本機語速"),
            rate_control,
        )
        form.addRow(
            self._t("mohan_volume", "墨寒專屬音量"),
            volume_control,
        )
        form.addRow(
            self._t("voice_style", "聲音風格"),
            self.voice_instructions,
        )
        form.addRow("", self.voice_preview_button)
        form.addRow(
            self._t("realtime", "即時語音"),
            self.realtime_status,
        )
        form.addRow("", self.realtime_btn)
        form.addRow("", self._realtime_note())

    def _voice_tab(self) -> QWidget:
        tab, form = self._form_scroll_page()
        capabilities = self.platform_services.capabilities
        self._initialize_transcription_controls(capabilities)
        self._initialize_voice_provider_controls(capabilities)
        self._initialize_realtime_controls()
        rate_control = self._initialize_voice_rate_control()
        volume_control = self._initialize_voice_volume_control()
        self._initialize_voice_action_controls()
        self._add_transcription_rows(form, capabilities)
        self._add_voice_provider_rows(form, capabilities)
        self._add_realtime_rows(form)
        self._add_voice_output_rows(
            form,
            rate_control,
            volume_control,
        )
        self.windows_voice.currentIndexChanged.connect(
            self._windows_voice_changed
        )
        return tab

    def _permissions_tab(self) -> QWidget:
        tab = QScrollArea()
        tab.setObjectName("formScrollPage")
        tab.setWidgetResizable(True)
        tab.setFrameShape(QFrame.NoFrame)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tab.viewport().setStyleSheet("background:#ffffff;")
        content = QWidget()
        content.setObjectName("formScrollContent")
        content.setStyleSheet(
            "QWidget#formScrollContent{background:#ffffff;}"
        )
        form = QFormLayout(content)
        tab.setWidget(content)
        intro = QLabel(
            self._t(
                "permissions_intro",
                "每項能力分開授權。選擇「每次詢問」時，墨寒執行前會顯示確認視窗；"
                "刪除檔案預設禁止。",
            )
        )
        intro.setWordWrap(True)
        form.addRow(intro)
        stored = self.db.setting("tool_permissions", {})
        defaults = {
            "open_web": "每次詢問",
            "open_folder": "每次詢問",
            "launch_app": "每次詢問",
            "write_files": "每次詢問",
            "delete_files": "禁止",
        }
        labels = {
            "open_web": self._t("permission_open_web", "開啟指定網站"),
            "open_folder": self._t(
                "permission_open_folder", "開啟工作室資料夾"
            ),
            "launch_app": self._t(
                "permission_launch_app", "啟動其他程式"
            ),
            "write_files": self._t(
                "permission_write_files", "建立或修改檔案"
            ),
            "delete_files": self._t(
                "permission_delete_files", "刪除檔案"
            ),
        }
        self.permission_controls = {}
        for key, default in defaults.items():
            combo = QComboBox()
            combo.addItem(self._t("permission_deny", "禁止"), "禁止")
            combo.addItem(
                self._t("permission_ask", "每次詢問"),
                "每次詢問",
            )
            combo.addItem(self._t("permission_allow", "允許"), "允許")
            permission_index = combo.findData(str(stored.get(key, default)))
            combo.setCurrentIndex(max(0, permission_index))
            self.permission_controls[key] = combo
            form.addRow(labels[key], combo)
        warning = QLabel(
            self._t(
                "permissions_warning",
                "安全原則：墨寒不會因聊天內容自動取得更高權限；"
                "API 模型只能提出工具請求，真正執行仍由本機權限層決定。",
            )
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#8a5a13;")
        save = QPushButton(
            self._t("save_permissions", "保存工具權限")
        )
        save.clicked.connect(self.save_permissions)
        form.addRow(warning)
        form.addRow("", save)
        self.flagship_center = FlagshipControlCenter(
            self.db,
            self.db.path.parent,
            self,
            platform_services=self.platform_services,
            secret_store_factory=self.secret_store_factory,
        )
        self.flagship_center.setMinimumHeight(720)
        self.flagship_center.speak_requested.connect(
            self.speak_requested.emit
        )
        self.flagship_center.remote_command_received.connect(
            self._receive_remote_command
        )
        flagship_heading = QLabel("<b>旗艦控制中心</b>")
        flagship_heading.setStyleSheet(
            "color:#2f6987;font-size:16px;margin-top:12px;"
        )
        form.addRow(flagship_heading)
        form.addRow(self.flagship_center)
        return tab

    def _step_control(
        self,
        editor: QAbstractSpinBox,
        object_prefix: str,
    ) -> tuple[QWidget, QPushButton, QPushButton]:
        """Use explicit buttons so Windows/QSS cannot steal the up hit area."""
        editor.setButtonSymbols(QAbstractSpinBox.NoButtons)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        up = QPushButton("▲")
        down = QPushButton("▼")
        up.setObjectName(f"{object_prefix}Up")
        down.setObjectName(f"{object_prefix}Down")
        up.setToolTip("增加")
        down.setToolTip("減少")
        for button in (up, down):
            button.setFixedWidth(46)
            button.setAutoRepeat(True)
            button.setAutoRepeatDelay(420)
            button.setAutoRepeatInterval(110)
        up.clicked.connect(editor.stepUp)
        down.clicked.connect(editor.stepDown)
        layout.addWidget(editor, 1)
        layout.addWidget(up)
        layout.addWidget(down)
        return container, up, down

    def _add_profile_settings(
        self,
        form: QFormLayout,
        parent: QWidget,
    ) -> None:
        heading = QLabel(
            self._t("profile_heading", "<b>顯示名稱與使用者資料</b>")
        )
        heading.setStyleSheet("color:#2f6987;font-size:15px;")
        self.profile_assistant_name = QLineEdit(
            profile_setting(self.db, "assistant_name")
        )
        self.profile_user_title = QLineEdit(
            profile_setting(self.db, "user_title")
        )
        self.profile_organization_name = QLineEdit(
            profile_setting(self.db, "organization_name")
        )
        self.profile_window_title = QLineEdit(
            profile_setting(self.db, "window_title")
        )
        self.profile_window_title.setPlaceholderText(
            "留空時自動顯示「助理名稱．組織名稱」"
        )
        self.profile_work_type = self._profile_work_type_combo()
        self.profile_ui_language = self._profile_language_combo()
        self.profile_wake_word = QLineEdit(
            profile_setting(self.db, "wake_word")
        )
        form.addRow(heading)
        profile_rows = (
            ("assistant_name", "助理名稱", self.profile_assistant_name),
            ("user_title", "助理對你的稱呼", self.profile_user_title),
            (
                "organization_name",
                "公司／團隊名稱",
                self.profile_organization_name,
            ),
            ("window_title", "完整視窗標題", self.profile_window_title),
            ("work_type", "工作類型", self.profile_work_type),
            ("ui_language", "介面語言", self.profile_ui_language),
            ("wake_word", "語音喚醒詞", self.profile_wake_word),
        )
        for key, fallback, editor in profile_rows:
            form.addRow(self._t(key, fallback), editor)
        self.portable_profile_panel = PortableProfilePanel(
            self.db,
            parent,
            before_export=lambda: self.save_settings(silent=True),
        )
        form.addRow(self.portable_profile_panel)

    def _profile_work_type_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        for value in FirstRunWizard.WORK_TYPES:
            combo.addItem(
                display_label(
                    self.ui_language,
                    value,
                    WORK_TYPE_LABELS,
                    SIMPLIFIED_WORK_TYPE_LABELS,
                    JAPANESE_WORK_TYPE_LABELS,
                ),
                value,
            )
        saved_work_type = profile_setting(self.db, "work_type")
        saved_index = combo.findData(saved_work_type)
        if saved_index >= 0:
            combo.setCurrentIndex(saved_index)
        else:
            combo.setCurrentText(saved_work_type)
        return combo

    def _profile_language_combo(self) -> QComboBox:
        combo = QComboBox()
        for label, language in (
            ("繁體中文（台灣）", "zh-TW"),
            ("简体中文（中国大陆）", "zh-CN"),
            ("English", "en"),
            ("日本語", "ja-JP"),
        ):
            combo.addItem(label, language)
        self._select_combo_data(
            combo,
            profile_setting(self.db, "ui_language"),
        )
        return combo

    def _add_reminder_settings(self, form: QFormLayout) -> None:
        self.reminder_controls: dict[
            str,
            tuple[QCheckBox, QTimeEdit],
        ] = {}
        self.reminder_step_buttons: dict[
            str,
            tuple[QPushButton, QPushButton],
        ] = {}
        self.reminder_message_controls: dict[str, QLineEdit] = {}
        labels = frozendict(
            {
                "work": self._t("reminder_work", "工作開始"),
                "lunch": self._t("reminder_lunch", "午餐"),
                "dinner": self._t("reminder_dinner", "晚餐"),
                "offwork": self._t("reminder_offwork", "下班"),
            }
        )
        for row in self.db.reminders():
            kind = str(row["kind"])
            self._add_reminder_row(form, row, labels[kind])

    def _add_reminder_row(
        self,
        form: QFormLayout,
        row: sqlite3.Row,
        label: str,
    ) -> None:
        kind = str(row["kind"])
        enabled = QCheckBox(self._t("enabled", "啟用"))
        enabled.setChecked(bool(row["enabled"]))
        reminder_time = QTimeEdit()
        reminder_time.setDisplayFormat("HH:mm")
        parsed_time = clock_time.fromisoformat(str(row["time_of_day"]))
        reminder_time.setTime(QTime(parsed_time.hour, parsed_time.minute))
        time_control, up_button, down_button = self._step_control(
            reminder_time,
            f"{kind}Time",
        )
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(enabled)
        row_layout.addWidget(time_control)
        row_layout.addStretch()
        form.addRow(label, row_widget)
        message = QLineEdit(
            str(
                self.db.setting(
                    f"reminder_message_{kind}",
                    reminder_line(self.ui_language, kind),
                )
            )
        )
        message.setPlaceholderText(
            self._t(
                "reminder_message_placeholder",
                "此提醒觸發時要說的內容",
            )
        )
        form.addRow(
            self._t(
                "reminder_message_label",
                "{label}訊息",
                label=label,
            ),
            message,
        )
        self.reminder_controls[kind] = (enabled, reminder_time)
        self.reminder_step_buttons[kind] = (up_button, down_button)
        self.reminder_message_controls[kind] = message

    def _add_work_rhythm_settings(self, form: QFormLayout) -> None:
        self.break_minutes = QSpinBox()
        self.break_minutes.setRange(30, 240)
        self.break_minutes.setSuffix(self._t("minutes_suffix", " 分鐘"))
        self.break_minutes.setValue(
            int(self.db.setting("break_minutes", 90))
        )
        self.overwork_message = QLineEdit(
            str(
                self.db.setting(
                    "reminder_message_overwork",
                    reminder_line(self.ui_language, "overwork"),
                )
            )
        )
        (
            self.break_minutes_control,
            self.break_minutes_up,
            self.break_minutes_down,
        ) = self._step_control(self.break_minutes, "breakMinutes")
        self.tts_enabled = QCheckBox(
            self._t("read_replies", "讓寒讀出回覆")
        )
        self.tts_enabled.setChecked(
            bool(self.db.setting("tts_enabled", True))
        )
        form.addRow(
            self._t("continuous_work_reminder", "連續工作提醒"),
            self.break_minutes_control,
        )
        form.addRow(
            self._t("overwork_message", "久坐／過勞提醒訊息"),
            self.overwork_message,
        )
        form.addRow("語音", self.tts_enabled)

    def _add_desktop_settings(
        self,
        form: QFormLayout,
        capabilities: PlatformCapabilities,
    ) -> None:
        self.autostart = self._autostart_checkbox(capabilities)
        self.topmost_mode = QComboBox()
        self.topmost_mode.addItems(
            ["智慧置頂（推薦）", "永遠置頂", "不置頂"]
        )
        self.topmost_mode.setCurrentText(
            str(
                self.db.setting(
                    "topmost_mode",
                    "智慧置頂（推薦）",
                )
            )
        )
        self.topmost_mode.currentTextChanged.connect(
            self._topmost_mode_changed
        )
        character_scale = self._character_scale_control()
        self.proactive_mode = self._editable_combo(
            ("安靜（只提醒必要事項）", "平衡（推薦）", "積極（主動建議）"),
            str(self.db.setting("proactive_mode", "平衡（推薦）")),
        )
        self.proactive_mode.setEditable(False)
        autostart_label = (
            "自動啟動"
            if capabilities.desktop_autostart
            else self._t("autostart", "自動啟動")
        )
        form.addRow(autostart_label, self.autostart)
        form.addRow("桌面置頂方式", self.topmost_mode)
        form.addRow("桌面墨寒顯示大小", character_scale)
        form.addRow("主動協助程度", self.proactive_mode)

    def _autostart_checkbox(
        self,
        capabilities: PlatformCapabilities,
    ) -> QCheckBox:
        checkbox = QCheckBox(
            "Windows 登入後自動啟動"
            if capabilities.desktop_autostart
            else self._t(
                "platform_autostart_unavailable",
                f"{capabilities.display_name} 自動啟動尚未完成實機驗證",
                platform=capabilities.display_name,
            )
        )
        checkbox.setChecked(
            bool(
                capabilities.desktop_autostart
                and self.db.setting("autostart", False)
            )
        )
        checkbox.setEnabled(capabilities.desktop_autostart)
        return checkbox

    def _character_scale_control(self) -> QWidget:
        saved_scale = int(
            self.db.setting(
                "character_scale_percent",
                CHARACTER_SCALE_DEFAULT,
            )
        )
        scale = max(
            CHARACTER_SCALE_MIN,
            min(CHARACTER_SCALE_MAX, saved_scale),
        )
        self.character_scale_slider = QSlider(Qt.Horizontal)
        self.character_scale_slider.setRange(
            CHARACTER_SCALE_MIN,
            CHARACTER_SCALE_MAX,
        )
        self.character_scale_slider.setSingleStep(5)
        self.character_scale_slider.setPageStep(10)
        self.character_scale_slider.setTickInterval(5)
        self.character_scale_slider.setTickPosition(QSlider.TicksBelow)
        self.character_scale_slider.setValue(scale)
        self.character_scale_label = QLabel(f"{scale}%")
        self.character_scale_label.setMinimumWidth(48)
        self.character_scale_label.setAlignment(Qt.AlignCenter)
        reset_button = QPushButton("恢復 100%")
        reset_button.setToolTip("將桌面墨寒恢復為原始顯示大小")
        reset_button.clicked.connect(
            lambda: self.character_scale_slider.setValue(
                CHARACTER_SCALE_DEFAULT
            )
        )
        control = QWidget()
        layout = QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.character_scale_slider, 1)
        layout.addWidget(self.character_scale_label)
        layout.addWidget(reset_button)
        self.character_scale_slider.valueChanged.connect(
            self._character_scale_changed
        )
        return control

    def _add_background_settings(self, form: QFormLayout) -> None:
        self.background_assistant_enabled = QCheckBox(
            "啟用背景多工助理（預設關閉）"
        )
        self.background_assistant_enabled.setChecked(
            bool(self.db.setting("background_assistant_enabled", False))
        )
        self.background_watch_apps = QLineEdit(
            str(
                self.db.setting(
                    "background_watch_apps",
                    "Visual Studio Code,GitHub Desktop",
                )
            )
        )
        self.background_watch_apps.setPlaceholderText(
            "以逗號分隔，例如：Visual Studio Code,GitHub Desktop"
        )
        self.background_diagnostic_report = QLineEdit(
            str(self.db.setting("background_diagnostic_report", ""))
        )
        self.background_diagnostic_report.setPlaceholderText(
            "選填：IDE 匯出的 .txt 或 .log 診斷報告完整路徑"
        )
        note = QLabel(
            "背景助理只讀取可見程式名稱與您明確指定的診斷報告；"
            "不會截取編輯器內容、不會自動修改檔案，也會遵守勿擾模式與冷卻時間。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#356f8d;")
        form.addRow("背景多工助理", self.background_assistant_enabled)
        form.addRow("監測程式名稱", self.background_watch_apps)
        form.addRow("IDE 診斷報告", self.background_diagnostic_report)
        form.addRow("", note)

    def _add_physics_settings(self, form: QFormLayout) -> None:
        labels = frozendict(
            {
                "physics_sleeves": "袖擺呼吸與慣性",
                "physics_hair": "長髮柔性擺動",
                "physics_ornament": "髮飾與流蘇慣性",
                "physics_eye_tracking": "眼球追蹤滑鼠",
                "physics_face_parallax": "臉部柔和視差",
            }
        )
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.physics_controls: dict[str, QCheckBox] = {}
        for key, label in labels.items():
            control = QCheckBox(label)
            control.setChecked(bool(self.db.setting(key, True)))
            layout.addWidget(control)
            self.physics_controls[key] = control
        note = QLabel("旗艦物理預設全部開啟；可依效能需要個別關閉。")
        note.setWordWrap(True)
        note.setStyleSheet("color:#356f8d;")
        layout.addWidget(note)
        form.addRow("電影級物理", box)

    def _add_work_folder_settings(self, form: QFormLayout) -> None:
        self.work_folder = QLineEdit(
            str(self.db.setting("work_folder", ""))
        )
        self.work_folder.setPlaceholderText("常用工作資料夾路徑")
        open_button = QPushButton("開啟工作資料夾")
        open_button.clicked.connect(self.open_work_folder)
        form.addRow("工作資料夾", self.work_folder)
        form.addRow("", open_button)

    def _add_ai_settings(
        self,
        form: QFormLayout,
        capabilities: PlatformCapabilities,
    ) -> None:
        key_saved = bool(
            capabilities.secure_secret_storage
            and self.secret_store.load()
        )
        self.api_key_input = self._api_key_input(
            capabilities,
            key_saved,
        )
        self.ai_model = self._editable_combo(
            TEXT_MODELS,
            str(self.db.setting("ai_model", DEFAULT_TEXT_MODEL)),
        )
        self.persona_prompt = self._persona_prompt_input()
        clear_button = QPushButton(
            self._t("remove_api_key", "移除已保存的 API 金鑰")
        )
        clear_button.clicked.connect(self.clear_api_key)
        clear_button.setEnabled(capabilities.secure_secret_storage)
        self.api_status = QLabel(
            self._api_status_text(capabilities, key_saved)
        )
        form.addRow(
            self._t("api_key", "OpenAI API 金鑰"),
            self.api_key_input,
        )
        form.addRow(
            self._t("text_model", "文字模型"),
            self.ai_model,
        )
        form.addRow(
            self._t("persona_prompt", "AI 人格提示詞"),
            self.persona_prompt,
        )
        form.addRow(self._settings_language_note())
        form.addRow("", clear_button)
        form.addRow("智能核心", self.api_status)

    def _api_key_input(
        self,
        capabilities: PlatformCapabilities,
        key_saved: bool,
    ) -> QLineEdit:
        key_input = QLineEdit()
        key_input.setEchoMode(QLineEdit.Password)
        if capabilities.secure_secret_storage:
            placeholder = (
                self._t(
                    "api_key_saved",
                    "已安全保存（留空不變）",
                )
                if key_saved
                else self._t(
                    "api_key_missing",
                    "貼上 sk- 開頭的 OpenAI Project API Key",
                )
            )
        else:
            placeholder = self._t(
                "platform_secret_storage_unavailable",
                f"{capabilities.display_name} 安全金鑰保存尚未完成實機驗證",
                platform=capabilities.display_name,
            )
            key_input.setEnabled(False)
        key_input.setPlaceholderText(placeholder)
        return key_input

    def _api_status_text(
        self,
        capabilities: PlatformCapabilities,
        key_saved: bool,
    ) -> str:
        if os.getenv("OPENAI_API_KEY"):
            return self._t(
                "api_status_environment",
                "OpenAI API：使用環境變數提供的金鑰",
            )
        if key_saved:
            return self._t(
                "api_status_saved",
                "OpenAI API：金鑰已由 Windows 加密保存",
            )
        if not capabilities.secure_secret_storage:
            return self._t(
                "api_status_secret_unavailable",
                f"OpenAI API：{capabilities.display_name} 安全金鑰保存尚未完成實機驗證",
                platform=capabilities.display_name,
            )
        return self._t(
            "api_status_offline",
            "OpenAI API：未設定，使用離線人設",
        )

    def _persona_prompt_input(self) -> QTextEdit:
        prompt = QTextEdit()
        prompt.setPlainText(
            str(
                self.db.setting(
                    "persona_prompt",
                    default_persona_for_language(self.ui_language),
                )
            )
        )
        prompt.setMinimumHeight(160)
        prompt.setPlaceholderText(
            "設定助理的角色背景、語氣、工作方式與界線。"
        )
        return prompt

    def _settings_language_note(self) -> QLabel:
        note = QLabel(
            self._t(
                "restart_language_note",
                "變更介面語言後，重新啟動墨寒即可完整套用。",
            )
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#356f8d;")
        return note

    def _add_update_settings(
        self,
        form: QFormLayout,
        parent: QWidget,
    ) -> None:
        self.update_panel = UpdatePanel(
            self.db,
            data_dir(self.platform_services),
            parent,
        )
        save_button = QPushButton(
            self._t("save_settings", "保存設定")
        )
        save_button.clicked.connect(self.save_settings)
        form.addRow(self.update_panel)
        form.addRow("", save_button)

    def _settings_tab(self) -> QWidget:
        tab, form = self._form_scroll_page()
        capabilities = self.platform_services.capabilities
        self._add_profile_settings(form, tab)
        form.addRow(
            QLabel(self._t("system_heading", "<b>工作與系統設定</b>"))
        )
        self._add_reminder_settings(form)
        self._add_work_rhythm_settings(form)
        self._add_desktop_settings(form, capabilities)
        self._add_background_settings(form)
        self._add_physics_settings(form)
        self._add_work_folder_settings(form)
        self._add_ai_settings(form, capabilities)
        self._add_update_settings(form, tab)
        return tab
    def append_chat(self, speaker: str, text: str) -> None:
        color = (
            "#2f6987"
            if speaker == self.assistant_name
            else "#8a4f82"
        )
        normalized = normalize_for_language(
            personalize_text(self.db, text),
            self.ui_language,
        )
        safe_text = html.escape(normalized).replace("\n", "<br>")
        self.chat.append(
            f'<p><b style="color:{color}">{speaker}</b><br>{safe_text}</p>'
        )
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def refresh_all(self) -> None:
        self.refresh_chat()
        self.refresh_todos()
        self.refresh_ideas()
        self.refresh_memories()
        rows = self.db.platform_rows()
        if {
            row["platform"] for row in rows
        } != set(self.platform_controls):
            self._reload_platform_cards()
            rows = []
        self._platform_loading = True
        try:
            for row in rows:
                self._load_platform_row(row)
        finally:
            self._platform_loading = False
        self._refresh_platform_summary()
        self._filter_platform_cards()
        self.refresh_work_time()

    def apply_profile_from_database(self) -> None:
        """Refresh identity state through one public dashboard boundary."""
        self.assistant_name = profile_setting(
            self.db,
            "assistant_name",
        )
        self.user_title = profile_setting(self.db, "user_title")
        self.organization_name = profile_setting(
            self.db,
            "organization_name",
        )
        title = profile_window_title(self.db)
        self.setWindowTitle(title)
        self._apply_profile_texts()
        self.header_title.setText(f"<b>{html.escape(title)}</b>")

    def consume_expression_metadata(
        self,
        expected_state: str,
    ) -> tuple[str, float, str] | None:
        pending = self.next_expression_metadata
        if pending is None or pending[0] != expected_state:
            return None
        self.next_expression_metadata = None
        return pending

    def capture_explicit_memory(self, text: str) -> None:
        self._capture_explicit_memory(text)

    def reply_expression(self, text: str) -> str:
        return self._reply_expression(text)

    def bring_to_front(self) -> None:
        self._bring_to_front()

    def set_api_status(self, text: str) -> None:
        self.api_status.setText(text)

    def refresh_chat(self) -> None:
        self.chat.clear()
        total = self.db.chat_count()
        for row in self.db.recent_chat(self.chat_loaded_limit):
            self.append_chat(
                self.user_title
                if row["role"] == "user"
                else self.assistant_name,
                row["content"],
            )
        shown = min(total, self.chat_loaded_limit)
        self.chat_retention.setText(
            f"本機保存 {total} 則對話，目前顯示最近 {shown} 則"
        )
        self.load_older_chat_btn.setEnabled(shown < total)

    def load_older_chat(self) -> None:
        self.chat_loaded_limit += 50
        self.refresh_chat()

    def manage_chat_history(self) -> None:
        manager = ChatHistoryDialog(self.db, self)
        manager.exec()
        if manager.changed:
            self.refresh_chat()

    def adjust_chat_zoom(self, steps: int) -> None:
        self.apply_chat_zoom(self.chat_zoom_percent + (steps * 10))

    def apply_chat_zoom(self, percent: int) -> None:
        self.chat_zoom_percent = max(60, min(200, int(percent)))
        font = QFont(self.chat.font())
        font.setPointSizeF(
            self.chat_base_point_size * self.chat_zoom_percent / 100.0
        )
        self.chat.setFont(font)
        self.chat.document().setDefaultFont(font)
        self.chat_zoom_label.setText(f"{self.chat_zoom_percent}%")
        self.chat_zoom_down.setEnabled(self.chat_zoom_percent > 60)
        self.chat_zoom_up.setEnabled(self.chat_zoom_percent < 200)
        self.db.set_setting("chat_zoom_percent", self.chat_zoom_percent)

    def refresh_memories(self, *_args) -> None:
        if not hasattr(self, "memory_list"):
            return
        self.memory_list.clear()
        selected_category = (
            str(self.memory_filter.currentData() or "")
            if hasattr(self, "memory_filter")
            else ""
        )
        rows = self.db.list_memories(
            limit=1000,
            category=selected_category or None,
        )
        all_rows = self.db.list_memories(limit=1000)
        counts = {category: 0 for category in MEMORY_CATEGORIES}
        for row in all_rows:
            category = to_taiwan_traditional(str(row["category"]))
            counts[category] = counts.get(category, 0) + 1
        if hasattr(self, "memory_filter"):
            self.memory_filter.setItemText(0, f"全部記憶（{len(all_rows)}）")
            for index in range(1, self.memory_filter.count()):
                category = str(self.memory_filter.itemData(index))
                self.memory_filter.setItemText(
                    index, f"{category}（{counts.get(category, 0)}）"
                )
        self.memory_count.setText(f"{len(rows)} 則")
        if not rows:
            empty = QListWidgetItem("這個分類目前沒有記憶。")
            empty.setFlags(Qt.NoItemFlags)
            self.memory_list.addItem(empty)
            return
        source_labels = {
            "manual": "手動",
            "conversation": "對話",
        }
        for row in rows:
            content = " ".join(
                to_taiwan_traditional(str(row["content"])).split()
            )
            if len(content) > 90:
                content = content[:90].rstrip() + "…"
            title = to_taiwan_traditional(
                str(row["title"] or content or "未命名記憶")
            )
            source = source_labels.get(
                str(row["source"]), str(row["source"])
            )
            item = QListWidgetItem(
                f"【{to_taiwan_traditional(str(row['category']))}】"
                f"{title}　重要度 {int(row['importance'])}／5\n"
                f"{content}\n來源：{source}　更新：{str(row['updated_at'])[5:16]}"
            )
            item.setData(Qt.UserRole, int(row["id"]))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setToolTip(to_taiwan_traditional(str(row["content"])))
            self.memory_list.addItem(item)

    def refresh_todos(self) -> None:
        while self.todo_list.count():
            item = self.todo_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        rows = self.db.list_todos()
        self.todo_count.setText(f"{len(rows)} 件未完成")
        if not rows:
            empty = QLabel("今日卷冊尚空。\n主上先寫下一件真正重要的事。")
            empty.setObjectName("emptyState")
            empty.setAlignment(Qt.AlignCenter)
            self.todo_list.addWidget(empty)
        for row in rows:
            widget = TodoRow(self.db, row)
            widget.changed.connect(self.refresh_todos)
            self.todo_list.addWidget(widget)

    def refresh_ideas(self) -> None:
        self.idea_list.clear()
        rows = self.db.list_ideas()
        self.idea_count.setText(f"{len(rows)} 則")
        if not rows:
            empty = QListWidgetItem("尚無靈感紀錄；輸入上方文字後按「收入靈感」。")
            empty.setFlags(Qt.NoItemFlags)
            self.idea_list.addItem(empty)
        for row in rows:
            title = to_taiwan_traditional(row["title"] or row["text"])
            content = to_taiwan_traditional(row["content"] or "")
            preview = " ".join(content.split())
            if len(preview) > 58:
                preview = preview[:58] + "…"
            line = title
            if preview:
                line += f"\n{preview}"
            line += f"  ·  {row['updated_at'][5:16]}"
            item = QListWidgetItem(line)
            item.setData(Qt.UserRole, int(row["id"]))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setToolTip("雙擊開啟並編輯標題與內文")
            self.idea_list.addItem(item)

    def refresh_work_time(self) -> None:
        seconds = self.db.today_work_seconds()
        active = self.db.active_session() is not None
        if active:
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds_part = divmod(remainder, 60)
            total = f"{hours:02d}:{minutes:02d}:{seconds_part:02d}"
        else:
            total = format_duration(seconds)
        state = "計時中" if active else "未計時"
        self.work_label.setText(f"今日 {total}｜{state}")

    def add_todo(self) -> None:
        text = to_taiwan_traditional(self.todo_input.text().strip())
        if not text:
            self.todo_feedback.setText("請先輸入待辦標題。")
            self.todo_input.setFocus()
            return
        self.db.add_todo(text, self.todo_category.currentText())
        self.todo_input.clear()
        self.refresh_todos()
        self.todo_feedback.setText(f"✓ 已加入待辦：{text}")
        self.todo_input.setFocus()
        self.speak_requested.emit("已收入今日卷冊。", "happy")

    def add_idea(self) -> None:
        text = to_taiwan_traditional(self.todo_input.text().strip())
        if not text:
            self.todo_feedback.setText("請先輸入要收藏的靈感。")
            self.todo_input.setFocus()
            return
        self.db.add_idea(text)
        self.todo_input.clear()
        self.refresh_ideas()
        self.todo_feedback.setText(f"✓ 已收入靈感：{text}")
        self.todo_input.setFocus()
        self.speak_requested.emit("靈光稍縱即逝，妾已替主上收好。", "happy")

    def edit_selected_idea(self) -> None:
        item = self.idea_list.currentItem()
        if item is None or item.data(Qt.UserRole) is None:
            self.todo_feedback.setText("請先選取一則要編輯的靈感。")
            return
        self.edit_idea_item(item)

    def edit_idea_item(self, item: QListWidgetItem) -> None:
        idea_id = item.data(Qt.UserRole)
        if idea_id is None:
            return
        row = self.db.idea(int(idea_id))
        if row is None:
            self.todo_feedback.setText("找不到這則靈感，請重新整理後再試。")
            return
        editor = IdeaEditorDialog(
            str(row["title"] or row["text"]),
            str(row["content"] or ""),
            self,
        )
        if editor.exec() != QDialog.Accepted:
            return
        title, content = editor.values()
        self.db.update_idea(int(idea_id), title, content)
        self.refresh_ideas()
        self.todo_feedback.setText(f"✓ 已更新靈感：{title}")

    def checked_idea_ids(self) -> list[int]:
        checked: list[int] = []
        for index in range(self.idea_list.count()):
            item = self.idea_list.item(index)
            idea_id = item.data(Qt.UserRole)
            if idea_id is not None and item.checkState() == Qt.Checked:
                checked.append(int(idea_id))
        return checked

    def delete_checked_ideas(self) -> None:
        idea_ids = self.checked_idea_ids()
        if not idea_ids:
            self.todo_feedback.setText("請先勾選要刪除的靈感。")
            return
        answer = QMessageBox.question(
            self,
            "刪除創作靈感",
            f"確定永久刪除勾選的 {len(idea_ids)} 則靈感嗎？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        deleted = self.db.delete_ideas(idea_ids)
        self.refresh_ideas()
        self.todo_feedback.setText(f"✓ 已刪除 {deleted} 則靈感。")

    def start_work(self) -> None:
        if self.db.start_work():
            self.speak_requested.emit(
                reminder_line(self.ui_language, "work"),
                "speaking",
            )
            self.work_changed.emit()
            if hasattr(self, "flagship_center"):
                self.flagship_center.work_started()
        else:
            self.speak_requested.emit(
                self._t(
                    "work_timer_already_running",
                    "計時仍在進行，主上不必重複開局。",
                ),
                "idle",
            )
        self.refresh_work_time()

    def stop_work(self) -> None:
        if self.db.stop_work():
            self.speak_requested.emit(
                reminder_line(self.ui_language, "offwork"),
                "happy",
            )
            self.work_changed.emit()
        else:
            self.speak_requested.emit(
                self._t(
                    "work_timer_not_started",
                    "今日尚未開始計時。",
                ),
                "worried",
            )
        self.refresh_work_time()

    def _mode_index_changed(self, index: int) -> None:
        mode = str(self.mode_combo.itemData(index) or "工作")
        self._mode_changed(mode)

    def _mode_changed(self, mode: str) -> None:
        self.mode = mode
        self.db.set_setting("mode", mode)
        if is_english(self.ui_language):
            lines = {
                "工作": "Work mode enabled. I will interrupt only when necessary.",
                "陪伴": "Companion mode enabled. We need not speak of victory tonight.",
                "勿擾": "Do not disturb enabled. I will stay quiet unless it is urgent.",
                "會議": "Meeting mode enabled. I will record only what is necessary.",
                "離席": "Away mode enabled. I will brief you when you return.",
                "休眠": "Sleep mode enabled. Reminders and urgent alerts remain active.",
            }
            self.speak_requested.emit(
                lines.get(
                    mode,
                    f"{display_label(self.ui_language, mode, MODE_LABELS)} "
                    "mode enabled.",
                ),
                "speaking",
            )
            return
        if is_simplified_chinese(self.ui_language):
            lines = {
                "工作": "工作模式已启动。妾只在必要时打断主上。",
                "陪伴": "陪伴模式已启动。今夜不谈胜负，也无妨。",
                "勿擾": "勿扰模式已启动。除紧急事项外，妾不会打断主上。",
                "會議": "会议模式已启动。妾会保持安静，只记录必要事项。",
                "離席": "离席模式已启动。主上回来时，妾再呈上期间摘要。",
                "休眠": "休眠模式已启动。提醒与紧急警报仍会按规则处理。",
            }
            self.speak_requested.emit(
                lines.get(
                    mode,
                    f"{display_label(self.ui_language, mode, MODE_LABELS, SIMPLIFIED_MODE_LABELS)}"
                    "模式已启动。",
                ),
                "speaking",
            )
            return
        if is_japanese(self.ui_language):
            lines = {
                "工作": "仕事モードを開始しました。必要な時だけ主様にお声がけします。",
                "陪伴": "お供モードを開始しました。今宵は勝ち負けを語らずともよいでしょう。",
                "勿擾": "集中モードを開始しました。緊急時以外、妾は静かにしております。",
                "會議": "会議モードを開始しました。静かに、必要なことだけを記録します。",
                "離席": "離席モードを開始しました。お戻りの際に要点をお伝えします。",
                "休眠": "休眠モードを開始しました。リマインダーと緊急通知は規則どおり動きます。",
            }
            self.speak_requested.emit(
                lines.get(
                    mode,
                    f"{display_label(self.ui_language, mode, MODE_LABELS, SIMPLIFIED_MODE_LABELS, JAPANESE_MODE_LABELS)}モードを開始しました。",
                ),
                "speaking",
            )
            return
        lines = {
            "工作": "工作模式已啟。妾只在必要時打斷主上。",
            "陪伴": "陪伴模式已啟。今夜不談勝負，也無妨。",
            "勿擾": "勿擾模式已啟。除緊急事項外，妾不打斷主上。",
            "會議": "會議模式已啟。妾會保持安靜，只記錄必要事項。",
            "離席": "離席模式已啟。主上回來時，妾再呈上期間摘要。",
            "休眠": "休眠模式已啟。妾暫歸劍中，提醒與緊急警報仍照規則處理。",
        }
        line = lines.get(mode, f"{mode}模式已啟。")
        self.speak_requested.emit(line, "speaking")

    def send_chat(self) -> None:
        text = normalize_for_language(
            self.chat_input.text().strip(),
            self.ui_language,
        )
        if not text:
            QMessageBox.information(
                self,
                "尚未輸入內容",
                "請先在左側輸入文字，再按「送出文字」；"
                "也可以按麥克風直接說話。",
            )
            self.chat_input.setFocus()
            return
        self.chat_input.clear()
        self.append_chat(self.user_title, text)
        self.db.log_chat("user", text)
        self._capture_explicit_memory(text)
        source = getattr(self, "_input_source", "local")
        self._input_source = "local"
        if self._handle_command(text, source=source):
            return
        self.ai_queue.append((text, self.mode))
        self.set_voice_phase(f"{self.assistant_name}思考中…")
        self._start_next_ai_request()

    def _receive_remote_command(self, text: str) -> None:
        normalized = normalize_for_language(
            text.strip(),
            self.ui_language,
        )
        if not normalized:
            return
        # The remote server has already authenticated and audited the device.
        # It enters the same command path as local text so it cannot bypass
        # command parsing, conversation history, or the flagship policy layer.
        bracket = normalized.find("] ")
        command = normalized[bracket + 2 :] if bracket >= 0 else normalized
        self._input_source = "remote"
        self.chat_input.setText(command)
        self.send_chat()

    def _start_next_ai_request(self) -> None:
        if self.ai_busy or not self.ai_queue:
            return
        text, mode = self.ai_queue.popleft()
        self.ai_busy = True
        self.set_voice_phase(f"{self.assistant_name}思考中…")
        history = [{"role": row["role"], "content": row["content"]} for row in self.db.recent_chat()]
        worker = AIWorker(
            AIWorkerRequest(
                user_text=text,
                mode=mode,
                history=tuple(history),
                api_key=self.secret_store.load(),
                memories=self.db.memory_context(query=text),
                model=str(self.db.setting("ai_model", DEFAULT_TEXT_MODEL)),
                persona=persona_for_profile(self.db),
                assistant_name=self.assistant_name,
                user_title=self.user_title,
                response_language=profile_setting(
                    self.db, "ui_language"
                ),
            )
        )
        worker.signals.done.connect(self._ai_done)
        worker.signals.failed.connect(self._ai_failed)
        self.thread_pool.start(worker)
        self._schedule_ai_wait_expressions(text)

    def _schedule_ai_wait_expressions(self, text: str) -> None:
        """Schedule optional reactions; the status label is display-only."""
        self._finish_ai_wait_expression()
        self.ai_wait_generation += 1
        generation = self.ai_wait_generation
        self.active_ai_wait_generation = generation
        for cue in plan_wait_expressions(text):
            QTimer.singleShot(
                cue.delay_ms,
                lambda cue=cue: self._emit_ai_wait_expression(
                    generation,
                    cue.expression,
                    cue.intensity,
                ),
            )

    def _emit_ai_wait_expression(
        self,
        generation: int,
        expression: str,
        intensity: float,
    ) -> None:
        if (
            self.ai_busy
            and generation == self.active_ai_wait_generation
        ):
            self.ai_wait_expression_requested.emit(
                generation,
                expression,
                intensity,
            )

    def _finish_ai_wait_expression(self) -> None:
        generation = self.active_ai_wait_generation
        if not generation:
            return
        self.active_ai_wait_generation = 0
        self.ai_wait_expression_finished.emit(generation)

    def cancel_ai_wait_expression(self) -> None:
        """Invalidate pending visual reactions without cancelling the API."""
        self._finish_ai_wait_expression()

    def _capture_explicit_memory(self, text: str) -> None:
        if not bool(self.db.setting("auto_memory", True)):
            return
        markers = (
            "請記住",
            "你要記得",
            "我的偏好是",
            "我喜歡",
            "我不喜歡",
            "我習慣",
            "我的目標是",
            "我的生日是",
            "我的朋友",
            "我的家人",
            "我的同事",
            "我的客戶",
            "工作流程是",
        )
        if any(marker in text for marker in markers):
            category = classify_memory_text(text)
            self.db.add_memory(text, category, "conversation", 4)
            self.refresh_memories()

    def _handle_command(self, text: str, source: str = "local") -> bool:
        return (
            self._handle_emergency_command(text)
            or self._handle_teasing_command(text)
            or self._handle_work_status_command(text)
            or self._handle_quick_capture_command(text)
            or self._handle_tool_instruction(text, source)
        )

    def _handle_emergency_command(self, text: str) -> bool:
        normalized = text.replace("，", "").replace(",", "").strip()
        if normalized not in EMERGENCY_COMMANDS:
            return False
        self._emergency_stop()
        return True

    def _handle_teasing_command(self, text: str) -> bool:
        if not any(marker in text for marker in TEASING_COMMAND_MARKERS):
            return False
        self._reply(
            "主上莫要自作多情。妾不過是在觀察你的神色，"
            "好替你籌謀下一步。至於旁的……並無此事。",
            "caught",
        )
        return True

    def _handle_work_status_command(self, text: str) -> bool:
        if is_start_work_command(text):
            self.start_work()
        elif is_stop_work_command(text):
            self.stop_work()
        elif "今天" in text and any(
            marker in text for marker in TODAY_WORK_DURATION_MARKERS
        ):
            duration = format_duration(self.db.today_work_seconds())
            self._reply(f"主上今日已工作 {duration}。", "speaking")
        else:
            return False
        return True

    def _handle_quick_capture_command(self, text: str) -> bool:
        marker = "幫我記一下"
        if marker not in text:
            return False
        content = text.split(marker, 1)[1].lstrip("：:，, ").strip()
        if not content:
            self._reply("主上想讓妾記下什麼？", "worried")
        elif any(marker in content for marker in IDEA_CAPTURE_MARKERS):
            self.db.add_idea(content)
            self.refresh_ideas()
            self._reply("靈感已收入卷冊。", "happy")
        else:
            self.db.add_todo(content, "其他")
            self.refresh_todos()
            self._reply("已加入今日待辦。", "happy")
        return True

    def _handle_tool_instruction(self, text: str, source: str) -> bool:
        flagship_center = getattr(self, "flagship_center", None)
        if flagship_center is None:
            return False
        recognized = flagship_center.recognizes_safe_instruction(text)
        explicitly_requested = any(
            marker in text for marker in EXPLICIT_TOOL_COMMAND_MARKERS
        )
        if not (recognized or explicitly_requested):
            return False
        flagship_center.plan_instruction(text, source=source)
        self._reply(
            "妾先整理成安全計畫，確認權限與目標後再請主上過目。",
            "thinking_front",
        )
        return True
    def _emergency_stop(self) -> None:
        if hasattr(self, "flagship_center"):
            self.flagship_center.emergency_stop()

    def _reply(
        self,
        text: str,
        state: str,
        *,
        intensity: float = 0.5,
        source: str = "conversation",
    ) -> None:
        text = normalize_for_language(
            personalize_text(self.db, text),
            self.ui_language,
        )
        self.db.log_chat("assistant", text)
        self.append_chat(self.assistant_name, text)
        self.set_voice_phase("回答中…")
        self.next_expression_metadata = (
            state,
            max(0.0, min(1.0, float(intensity))),
            source,
        )
        self.speak_requested.emit(text, state)

    def _ai_done(self, text: str) -> None:
        self._finish_ai_wait_expression()
        tagged = parse_internal_emotion(text)
        clean = tagged.text or "妾在。主上方才所言，容妾再細想一遍。"
        expression = (
            tagged.expression
            if tagged.valid_tag and tagged.expression is not None
            else self._reply_expression(clean)
        )
        self._reply(
            clean,
            expression,
            intensity=tagged.intensity,
            source="ai_tag" if tagged.valid_tag else "fallback",
        )
        self.ai_busy = False
        self._start_next_ai_request()

    @staticmethod
    def _reply_expression(text: str) -> str:
        compact = "".join(str(text).split())
        rules = (
            (
                "mock_hit_front",
                (
                    "再胡說妾便敲你",
                    "再胡說妾可要敲你",
                    "當心妾敲你",
                    "放肆，妾可要",
                ),
            ),
            (
                "mock_scold",
                ("休得胡言", "莫要踰矩", "休要亂說"),
            ),
            (
                "shy_cute_front",
                (
                    "莫要自作多情",
                    "才沒有偷看",
                    "妾並未偷看",
                    "誰在注視你",
                    "並無此事，主上",
                ),
            ),
            (
                "eureka_front",
                ("妾想到了", "妾有辦法了", "關鍵原來在於"),
            ),
            (
                "protective_front",
                (
                    "妾會護著主上",
                    "不許任何人傷你",
                    "誰也不得傷主上",
                    "有妾護著主上",
                ),
            ),
            (
                "exasperated_front",
                (
                    "真拿主上沒辦法",
                    "主上又來了",
                    "讓妾省點心",
                ),
            ),
            (
                "restrained_amused_front",
                (
                    "妾忍俊不禁",
                    "主上是在逗妾",
                    "倒是有趣得很",
                ),
            ),
            (
                "attentive_front",
                ("妾在聽", "主上慢慢說", "請繼續說", "妾願聞其詳"),
            ),
            (
                "determined_front",
                ("計策已定", "便照此執行", "就這麼辦", "此事交給妾"),
            ),
            (
                "surprised_front",
                ("真沒想到", "出乎妾意料", "竟會如此"),
            ),
            (
                "worried_front",
                (
                    "妾很擔心",
                    "主上別逞強",
                    "主上莫要逞強",
                    "先處理傷勢",
                    "你已經很疲憊",
                    "妾放心不下",
                ),
            ),
            (
                "reminder",
                (
                    "該吃飯了",
                    "先去吃飯",
                    "該休息了",
                    "先休息片刻",
                    "喝些水",
                    "到了下班時辰",
                    "妾提醒主上",
                ),
            ),
            (
                "relieved_front",
                ("主上平安便好", "沒事就好", "妾總算放心"),
            ),
            (
                "proud_front",
                ("不出妾所料", "正如妾所料", "依妾之計"),
            ),
            (
                "gentle_smile_front",
                (
                    "主上做得很好",
                    "妾替主上高興",
                    "此事值得恭喜",
                ),
            ),
            (
                "thinking_front",
                (
                    "妾先分析",
                    "先分析風險",
                    "妾的建議是",
                    "先排優先順序",
                    "此事需從長計議",
                ),
            ),
        )
        for expression, phrases in rules:
            if any(phrase in compact for phrase in phrases):
                return expression
        return "speaking"

    def _ai_failed(self, error: str) -> None:
        self._finish_ai_wait_expression()
        if is_english(self.ui_language):
            message = (
                "The cloud connection is temporarily unavailable. I remain "
                "here, but cannot draw on external knowledge just now."
            )
        elif is_simplified_chinese(self.ui_language):
            message = "云端连接暂时中断。妾仍在，只是此刻无法借用外部知识。"
        elif is_japanese(self.ui_language):
            message = (
                "クラウドとの接続が一時的に途切れました。妾はここにおりますが、"
                "今は外部の知識を借りられません。"
            )
        else:
            message = "雲端傳音暫時中斷。妾仍在，只是此刻無法借用外部智識。"
        self._reply(message, "worried")
        self.api_status.setText(f"OpenAI API：連線失敗（{error[:70]}）")
        self.ai_busy = False
        self._start_next_ai_request()

    def _voice_text(self, text: str) -> None:
        text = normalize_for_language(text, self.ui_language)
        self.set_voice_phase("墨寒思考中…")
        wake_word = profile_setting(self.db, "wake_word")
        self.chat_input.setText(
            text.replace(wake_word, "", 1).strip() or text
        )
        self._input_source = "voice"
        self.send_chat()

    def _voice_error(self, message: str) -> None:
        self.set_voice_phase("準備就緒")
        self.append_chat("寒", message)
        self.speak_requested.emit(message, "worried")

    def _listening_changed(self, listening: bool) -> None:
        if not listening:
            self.mic_btn.setText("🎙 麥克風")
            self.mic_btn.setEnabled(True)
        elif self.listener.is_recording:
            self.mic_btn.setText("⏹ 立即送出")
            self.mic_btn.setEnabled(True)
        else:
            self.mic_btn.setText("辨識中…")
            self.mic_btn.setEnabled(False)

    def _recording_changed(self, recording: bool) -> None:
        if recording:
            self.mic_btn.setText("⏹ 立即送出")
            self.mic_btn.setEnabled(True)
        else:
            self.mic_btn.setText("辨識中…")
            self.mic_btn.setEnabled(False)

    def _transcription_diagnostic(self, message: str) -> None:
        self.db.set_setting("last_transcription_diagnostic", message)
        if hasattr(self, "transcription_diagnostic"):
            self.transcription_diagnostic.setText(message)

    def set_voice_phase(self, phase: str) -> None:
        self.voice_phase.setText(f"語音狀態：{phase}")

    @staticmethod
    def _format_platform_updated(value: str) -> str:
        try:
            updated = datetime.fromisoformat(value)
            return f"更新：{updated:%m/%d %H:%M}"
        except (TypeError, ValueError):
            return "更新時間不明"

    def _platform_update(self, platform: str) -> PlatformProgressUpdate:
        controls = self.platform_controls[platform]
        return PlatformProgressUpdate(
            platform=platform,
            status=controls.status.currentText(),
            item_name=controls.item_name.text(),
            missing=controls.missing.text(),
            next_action=controls.next_action.text(),
            notes=controls.notes.text(),
            url=self._normalize_platform_url(controls.url.text()),
        )

    def _platform_changed(self, platform: str) -> None:
        if self._platform_loading:
            return
        controls = self.platform_controls[platform]
        controls.dirty = True
        controls.save_button.setText("保存變更")
        controls.updated.setText("尚未保存")
        controls.timer.start()
        self.platform_feedback.setText(
            f"{platform} 有變更，正在等待自動保存……"
        )
        self._validate_platform(platform)
        self._refresh_platform_summary()
        self._filter_platform_cards()

    def _validate_platform(self, platform: str) -> None:
        controls = self.platform_controls[platform]
        status = controls.status.currentText()
        missing = controls.missing.text().strip()
        next_action = controls.next_action.text().strip()
        item_name = controls.item_name.text().strip()
        notes = controls.notes.text().strip()
        message = ""
        color = "#efc27f"
        if status in {"已完成", "已上架"} and missing:
            message = "注意：工作已完成，但仍列有待補資料或阻礙。"
        elif status == "需修正" and not (missing or next_action or notes):
            message = "請在待補資料／阻礙、下一步或備註中寫明需修正的內容。"
        elif status == "尚未開始" and any(
            (item_name, missing, next_action, notes)
        ):
            message = "已有工作資料，請確認狀態是否應改為「準備資料」。"
        elif status in {
            "待送出",
            "等待回覆",
            "審核中",
            "已排程",
            "已完成",
            "已上架",
        } and not item_name:
            message = "建議填寫工作項目、專案或案件名稱，日後較容易辨認。"
            color = "#356f8d"
        controls.validation.setText(message)
        controls.validation.setStyleSheet(f"color:{color};")

    def _refresh_platform_summary(self) -> None:
        if not hasattr(self, "platform_controls"):
            return
        statuses = [
            controls.status.currentText()
            for controls in self.platform_controls.values()
        ]
        missing_count = sum(
            bool(controls.missing.text().strip())
            for controls in self.platform_controls.values()
        )
        dirty_count = sum(
            controls.dirty
            for controls in self.platform_controls.values()
        )
        finished = sum(
            status in {"已完成", "已上架"} for status in statuses
        )
        not_started = statuses.count("尚未開始")
        in_progress = len(statuses) - finished - not_started
        dirty_text = f"｜未保存 {dirty_count}" if dirty_count else ""
        self.platform_summary.setText(
            f"{len(statuses)} 個平台｜已完成 {finished}｜"
            f"進行中 {in_progress}｜尚未開始 {not_started}｜"
            f"待補／阻礙 {missing_count}{dirty_text}"
        )

    def _filter_platform_cards(self, _value: str = "") -> None:
        if not hasattr(self, "platform_filter"):
            return
        selected = self.platform_filter.currentText()
        for controls in self.platform_controls.values():
            status = controls.status.currentText()
            has_missing = bool(controls.missing.text().strip())
            visible = (
                selected == "全部平台"
                or selected == "進行中"
                and status not in {"尚未開始", "已完成", "已上架"}
                or selected == "待補資料／阻礙"
                and has_missing
                or selected == "已完成／已上架"
                and status in {"已完成", "已上架"}
                or selected == "尚未開始"
                and status == "尚未開始"
            )
            controls.card.setVisible(visible)

    def save_platform(self, platform: str, silent: bool = False) -> None:
        controls = self.platform_controls[platform]
        controls.timer.stop()
        self.db.update_platforms([self._platform_update(platform)])
        controls.dirty = False
        controls.save_button.setText("保存此平台")
        controls.updated.setText(
            self._format_platform_updated(
                local_wall_time().isoformat(timespec="seconds")
            )
        )
        self._validate_platform(platform)
        self._refresh_platform_summary()
        self.platform_feedback.setText(
            f"{platform} 已{'自動' if silent else ''}保存。"
        )

    def save_platforms(self, silent: bool = False) -> None:
        entries = []
        for platform, controls in self.platform_controls.items():
            controls.timer.stop()
            entries.append(self._platform_update(platform))
        self.db.update_platforms(entries)
        now = local_wall_time().isoformat(timespec="seconds")
        for platform, controls in self.platform_controls.items():
            controls.dirty = False
            controls.save_button.setText("保存此平台")
            controls.updated.setText(
                self._format_platform_updated(now)
            )
            self._validate_platform(platform)
        self._refresh_platform_summary()
        missing_count = sum(
            bool(controls.missing.text().strip())
            for controls in self.platform_controls.values()
        )
        self.platform_feedback.setText(
            f"全部工作平台已保存；{missing_count} 個平台仍列有待補資料或阻礙。"
        )
        if not silent:
            self.speak_requested.emit(
                f"工作平台已保存。仍有 {missing_count} 個平台標有待補資料或阻礙。",
                "happy",
            )

    def add_memory(self) -> None:
        text = self.memory_input.text().strip()
        if not text:
            self.memory_input.setFocus()
            return
        self.db.add_memory(
            text,
            self.memory_category.currentText(),
            "manual",
            4,
        )
        self.memory_input.clear()
        self.refresh_memories()
        self.speak_requested.emit(
            "妾已記下。主上日後若要更改，也可逐項整理。",
            "happy",
        )

    def edit_selected_memory(self) -> None:
        item = self.memory_list.currentItem()
        if item is None or item.data(Qt.UserRole) is None:
            QMessageBox.information(
                self, "尚未選取", "請先選取一則要編輯的記憶。"
            )
            return
        self.edit_memory_item(item)

    def edit_memory_item(self, item: QListWidgetItem) -> None:
        memory_id = item.data(Qt.UserRole)
        if memory_id is None:
            return
        row = self.db.memory(int(memory_id))
        if row is None:
            QMessageBox.information(
                self, "找不到記憶", "這則記憶已不存在，清單將重新整理。"
            )
            self.refresh_memories()
            return
        editor = MemoryEditorDialog(row, self)
        if editor.exec() != QDialog.Accepted:
            return
        title, content, category, importance = editor.values()
        if not self.db.update_memory(
            int(memory_id), title, content, category, importance
        ):
            QMessageBox.warning(
                self,
                "無法保存記憶",
                "可能已有內容完全相同的記憶。原有資料未被變更。",
            )
            return
        self.refresh_memories()

    def checked_memory_ids(self) -> list[int]:
        checked: list[int] = []
        for index in range(self.memory_list.count()):
            item = self.memory_list.item(index)
            memory_id = item.data(Qt.UserRole)
            if memory_id is not None and item.checkState() == Qt.Checked:
                checked.append(int(memory_id))
        return checked

    def delete_checked_memories(self) -> None:
        memory_ids = self.checked_memory_ids()
        if not memory_ids:
            QMessageBox.information(
                self, "尚未勾選", "請先勾選要刪除的記憶。"
            )
            return
        answer = QMessageBox.question(
            self,
            "刪除長期記憶",
            f"確定永久刪除勾選的 {len(memory_ids)} 則記憶嗎？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.db.delete_memories(memory_ids)
        self.refresh_memories()

    def delete_memory(self) -> None:
        item = self.memory_list.currentItem()
        if not item or item.data(Qt.UserRole) is None:
            return
        self.db.delete_memory(int(item.data(Qt.UserRole)))
        self.refresh_memories()

    def clear_memories(self) -> None:
        answer = QMessageBox.question(
            self,
            "清除長期記憶",
            "確定要刪除墨寒保存的全部長期記憶嗎？此動作無法復原。",
        )
        if answer == QMessageBox.Yes:
            self.db.clear_memories()
            self.refresh_memories()

    def optimize_memories(self) -> None:
        result = self.db.optimize_memories()
        self.refresh_memories()
        QMessageBox.information(
            self,
            "記憶整理完成",
            f"合併 {result['deduplicated']} 則近似記憶，"
            f"封存 {result['pruned']} 則較舊低重要度記憶。\n"
            f"目前使用中 {result['active']} 則；"
            f"可還原封存 {result['archived']} 則。",
        )

    def show_archived_memories(self) -> None:
        dialog = ArchivedMemoryDialog(self.db, self)
        dialog.exec()
        if dialog.changed:
            self.refresh_memories()

    def _preview_voice(self) -> None:
        self.save_voice_settings(silent=True)
        self.voice_preview_requested.emit()

    def _windows_voice_changed(self, _index: int) -> None:
        self.db.set_setting(
            "windows_voice", str(self.windows_voice.currentData() or "")
        )

    def clear_azure_speech_key(self) -> None:
        if self.azure_secret_store is None:
            return
        platform = self.platform_services.capabilities
        answer = QMessageBox.question(
            self,
            self._t("azure_remove_key", "移除 Azure Speech 金鑰"),
            self._t(
                "azure_remove_key_confirm",
                f"確定移除由 {platform.display_name} 安全保存的 Azure Speech 金鑰嗎？",
            ),
        )
        if answer == QMessageBox.Yes:
            self.azure_secret_store.clear()
            self.azure_key_input.clear()
            self.azure_key_input.setPlaceholderText(
                self._t(
                    "azure_key_missing",
                    "貼上 Azure Speech 資源金鑰",
                )
            )

    def _update_voice_volume_label(self) -> None:
        self.voice_volume_label.setText(f"{self.voice_volume.value()}%")

    def _voice_volume_changed(self, _value=None) -> None:
        self._update_voice_volume_label()
        volume = self.voice_volume.value()
        muted = self.voice_muted.isChecked()
        self.db.set_setting("voice_volume_percent", volume)
        self.db.set_setting("voice_muted", muted)
        self.volume_changed.emit(volume, muted)

    def _topmost_mode_changed(self, mode: str) -> None:
        self.db.set_setting("topmost_mode", mode)
        self.topmost_mode_changed.emit(mode)

    def _character_scale_changed(self, value: int) -> None:
        value = max(
            CHARACTER_SCALE_MIN,
            min(CHARACTER_SCALE_MAX, int(value)),
        )
        self.character_scale_label.setText(f"{value}%")
        self.db.set_setting("character_scale_percent", value)
        self.character_scale_preview.emit(value)

    def save_voice_settings(self, silent: bool = False) -> None:
        self.db.set_setting(
            "speech_recognition",
            str(
                self.speech_recognition.currentData()
                or "OpenAI 高準確辨識（推薦）"
            ),
        )
        self.db.set_setting(
            "transcription_model",
            self.transcription_model.currentText().strip(),
        )
        self.db.set_setting(
            "transcription_language",
            self.transcription_language.text().strip(),
        )
        self.db.set_setting(
            "transcription_prompt",
            self.transcription_prompt.toPlainText().strip(),
        )
        self.db.set_setting(
            "windows_transcription_fallback",
            self.windows_transcription_fallback.isChecked(),
        )
        self.db.set_setting(
            "voice_engine",
            str(self.voice_engine.currentData() or VOICE_ENGINE_SYSTEM),
        )
        selected_windows_voice = str(
            self.windows_voice.currentData() or ""
        )
        if selected_windows_voice:
            self.db.set_setting("windows_voice", selected_windows_voice)
        self.db.set_setting("tts_voice", self.tts_voice.currentText())
        self.db.set_setting("cloud_voice", self.tts_voice.currentText())
        self.db.set_setting("realtime_voice", self.realtime_voice.currentText())
        self.db.set_setting(
            "azure_speech_voice",
            self.azure_voice.currentText(),
        )
        self.db.set_setting(
            "azure_speech_region",
            self.azure_region.text().strip().lower(),
        )
        azure_key = self.azure_key_input.text().strip()
        if azure_key and self.azure_secret_store is not None:
            try:
                self.azure_secret_store.save(azure_key)
                self.azure_key_input.clear()
                self.azure_key_input.setPlaceholderText(
                    self._t(
                        "azure_key_saved",
                        "已由作業系統安全保存（留空不變）",
                    )
                )
            except OSError as exc:
                if not silent:
                    QMessageBox.warning(
                        self,
                        "Azure Speech",
                        self._t(
                            "azure_key_save_failed",
                            "無法安全保存 Azure Speech 金鑰：{error}",
                            error=exc,
                        ),
                    )
        self.db.set_setting("realtime_model", self.realtime_model.currentText())
        self.db.set_setting(
            "realtime_transcription_model",
            self.realtime_transcription_model.currentText().strip(),
        )
        self.db.set_setting(
            "realtime_noise_reduction",
            str(self.realtime_noise_reduction.currentData() or "near_field"),
        )
        self.db.set_setting(
            "realtime_turn_detection",
            str(self.realtime_turn_detection.currentData() or "server_vad"),
        )
        self.db.set_setting(
            "realtime_echo_guard", self.realtime_echo_guard.isChecked()
        )
        self.db.set_setting(
            "realtime_hybrid_transcription",
            self.realtime_hybrid_transcription.isChecked(),
        )
        self.db.set_setting("voice_rate", self.voice_rate.value())
        self.db.set_setting(
            "voice_volume_percent",
            self.voice_volume.value(),
        )
        self.db.set_setting("voice_muted", self.voice_muted.isChecked())
        self.db.set_setting(
            "voice_instructions", self.voice_instructions.text().strip()
        )
        if not silent:
            self.speak_requested.emit(
                self._t("voice_settings_saved", "聲音設定已保存。"),
                "happy",
            )

    def set_realtime_status(self, status: str, active: bool | None = None) -> None:
        self.realtime_status.setText(f"Realtime：{status}")
        if active is not None:
            self.realtime_btn.blockSignals(True)
            self.realtime_btn.setChecked(active)
            self.realtime_btn.setText(
                self._t("stop_realtime", "停止 Realtime 自然對話")
                if active
                else self._t(
                    "start_realtime",
                    "啟動 Realtime 自然對話",
                )
            )
            self.realtime_btn.blockSignals(False)

    def save_permissions(self) -> None:
        permissions = {
            key: str(combo.currentData() or "禁止")
            for key, combo in self.permission_controls.items()
        }
        self.db.set_setting("tool_permissions", permissions)
        self.speak_requested.emit(
            self._t(
                "permission_saved_speech",
                "電腦工具權限已保存。妾會照此邊界行事。",
            ),
            "happy",
        )

    def _permission_allowed(self, key: str, action: str) -> bool:
        stored = self.db.setting("tool_permissions", {})
        default = "禁止" if key == "delete_files" else "每次詢問"
        mode = str(stored.get(key, default))
        if hasattr(self, "permission_controls") and key in self.permission_controls:
            mode = str(
                self.permission_controls[key].currentData() or default
            )
        if mode == "允許":
            return True
        if mode == "禁止":
            QMessageBox.information(
                self,
                self._t("permission_blocked", "權限已阻擋"),
                self._t(
                    "permission_blocked_message",
                    "墨寒目前無權{action}。",
                    action=action,
                ),
            )
            return False
        answer = QMessageBox.question(
            self,
            self._t(
                "permission_request",
                "墨寒請求電腦權限",
            ),
            self._t(
                "permission_request_message",
                "是否允許墨寒這一次{action}？",
                action=action,
            ),
        )
        return answer == QMessageBox.Yes

    def open_platform(self, platform: str) -> None:
        controls = self.platform_controls.get(platform)
        url = (
            self._normalize_platform_url(controls.url.text())
            if controls is not None
            else ""
        )
        if not url:
            row = next(
                (
                    row
                    for row in self.db.platform_rows()
                    if row["platform"] == platform
                ),
                None,
            )
            url = self._normalize_platform_url(row["url"] if row else "")
        if not url:
            QMessageBox.information(
                self,
                "尚未設定網址",
                f"請先在「{platform}」卡片填入網站或工具網址。",
            )
            return
        if not url.lower().startswith(("https://", "http://")):
            QMessageBox.warning(
                self,
                "網址格式不支援",
                "只允許開啟 http:// 或 https:// 網址。",
            )
            return
        if self._permission_allowed("open_web", f"開啟 {platform} 網站"):
            webbrowser.open(url)

    def _current_profile_localization(self) -> ProfileLocalizationContext:
        return ProfileLocalizationContext(
            assistant_name=self.assistant_name,
            user_title=self.user_title,
            organization_name=self.organization_name,
            wake_word=profile_setting(self.db, "wake_word"),
            ui_language=self.ui_language,
        )

    def _validated_profile_settings(
        self,
    ) -> ProfileSettingsValues | None:
        assistant_name = self.profile_assistant_name.text().strip()
        user_title = self.profile_user_title.text().strip()
        if not assistant_name or not user_title:
            QMessageBox.information(
                self,
                "尚缺必要資料",
                "助理名稱與助理對你的稱呼不可留空。",
            )
            return None
        return ProfileSettingsValues(
            assistant_name=assistant_name,
            user_title=user_title,
            organization_name=(
                self.profile_organization_name.text().strip()
            ),
            window_title=self.profile_window_title.text().strip(),
            work_type=combo_data_or_custom_text(
                self.profile_work_type,
                "其他",
            ),
            ui_language=str(
                self.profile_ui_language.currentData() or "zh-TW"
            ),
            wake_word=(
                self.profile_wake_word.text().strip() or assistant_name
            ),
        )

    def _persist_profile_settings(
        self,
        values: ProfileSettingsValues,
    ) -> None:
        for key, value in values.setting_items():
            self.db.set_setting(key, value)

    def _migrate_localized_profile_defaults(
        self,
        previous: ProfileLocalizationContext,
        current: ProfileSettingsValues,
    ) -> None:
        self._migrate_transcription_prompt(previous, current.localization)
        if current.ui_language == previous.ui_language:
            return
        self._migrate_transcription_language(current.ui_language)
        self._migrate_voice_instructions(current.ui_language)
        self._migrate_persona_prompt(current.ui_language)
        self._migrate_reminder_messages(current.ui_language)

    def _migrate_transcription_prompt(
        self,
        previous: ProfileLocalizationContext,
        current: ProfileLocalizationContext,
    ) -> None:
        prompt = self.transcription_prompt.toPlainText().strip()
        if not is_builtin_transcription_prompt(
            prompt,
            previous.ui_language,
            assistant_name=previous.assistant_name,
            user_title=previous.user_title,
            organization_name=previous.organization_name,
            wake_word=previous.wake_word,
        ):
            return
        self.transcription_prompt.setPlainText(
            localized_transcription_prompt(
                current.ui_language,
                assistant_name=current.assistant_name,
                user_title=current.user_title,
                organization_name=current.organization_name,
                wake_word=current.wake_word,
            )
        )

    def _migrate_transcription_language(self, ui_language: str) -> None:
        language = self.transcription_language.text().strip()
        if language in {"zh", "en", "ja"}:
            self.transcription_language.setText(
                transcription_language_for_ui(ui_language)
            )

    def _migrate_voice_instructions(self, ui_language: str) -> None:
        instructions = self.voice_instructions.text().strip()
        built_in_instructions = frozenset(
            {
                VOICE_GENERATION_PROMPT,
                english_voice_instructions(),
                simplified_chinese_voice_instructions(),
                japanese_voice_instructions(),
            }
        )
        if instructions in built_in_instructions:
            self.voice_instructions.setText(
                localized_voice_instructions(
                    ui_language,
                    VOICE_GENERATION_PROMPT,
                )
            )

    def _migrate_persona_prompt(self, ui_language: str) -> None:
        persona = self.persona_prompt.toPlainText().strip()
        built_in_personas = frozenset(
            {
                PERSONA.strip(),
                ENGLISH_PERSONA.strip(),
                SIMPLIFIED_CHINESE_PERSONA.strip(),
                JAPANESE_PERSONA.strip(),
            }
        )
        if persona in built_in_personas:
            self.persona_prompt.setPlainText(
                default_persona_for_language(ui_language)
            )

    def _migrate_reminder_messages(self, ui_language: str) -> None:
        for kind, message in self.reminder_message_controls.items():
            message.setText(
                migrate_builtin_reminder_line(
                    message.text(),
                    ui_language,
                    kind,
                    REMINDER_LINES[kind],
                )
            )
        self.overwork_message.setText(
            migrate_builtin_reminder_line(
                self.overwork_message.text(),
                ui_language,
                "overwork",
                REMINDER_LINES["overwork"],
            )
        )

    def _apply_saved_profile(self, values: ProfileSettingsValues) -> None:
        self.assistant_name = values.assistant_name
        self.user_title = values.user_title
        self.organization_name = values.organization_name
        title = profile_window_title(self.db)
        self.setWindowTitle(title)
        self.header_title.setText(f"<b>{html.escape(title)}</b>")

    def _save_reminder_settings(self, ui_language: str) -> None:
        for kind, (enabled, reminder_time) in self.reminder_controls.items():
            self.db.update_reminder(
                kind,
                reminder_time.time().toString("HH:mm"),
                enabled.isChecked(),
            )
            message = self.reminder_message_controls[kind].text().strip()
            self.db.set_setting(
                f"reminder_message_{kind}",
                message or reminder_line(ui_language, kind),
            )

    def _save_general_settings(self, ui_language: str) -> None:
        persona = self.persona_prompt.toPlainText().strip()
        overwork_message = self.overwork_message.text().strip()
        settings = (
            ("break_minutes", self.break_minutes.value()),
            (
                "reminder_message_overwork",
                overwork_message
                or reminder_line(ui_language, "overwork"),
            ),
            ("tts_enabled", self.tts_enabled.isChecked()),
            ("work_folder", self.work_folder.text().strip()),
            ("auto_memory", self.auto_memory.isChecked()),
            ("ai_model", self.ai_model.currentText()),
            (
                "persona_prompt",
                persona or default_persona_for_language(ui_language),
            ),
            ("topmost_mode", self.topmost_mode.currentText()),
            (
                "character_scale_percent",
                self.character_scale_slider.value(),
            ),
            ("proactive_mode", self.proactive_mode.currentText()),
            (
                "background_assistant_enabled",
                self.background_assistant_enabled.isChecked(),
            ),
            (
                "background_watch_apps",
                self.background_watch_apps.text().strip(),
            ),
            (
                "background_diagnostic_report",
                self.background_diagnostic_report.text().strip(),
            ),
        )
        for key, value in settings:
            self.db.set_setting(key, value)
        for key, control in self.physics_controls.items():
            self.db.set_setting(key, control.isChecked())

    def _save_api_key_if_provided(self) -> None:
        key = self.api_key_input.text().strip()
        if not key:
            return
        try:
            self.secret_store.save(key)
        except OSError as exc:
            QMessageBox.warning(
                self,
                "API 金鑰",
                f"無法安全保存金鑰：{exc}",
            )
            return
        self.api_key_input.clear()
        self.api_key_input.setPlaceholderText("已安全保存（留空不變）")
        self.api_status.setText("OpenAI API：金鑰已由作業系統安全保存")

    def _save_autostart_setting(self) -> None:
        if not self.platform_services.capabilities.desktop_autostart:
            self.db.set_setting("autostart", False)
            return
        enabled = self.autostart.isChecked()
        try:
            set_autostart(enabled, self.platform_services)
        except OSError as exc:
            QMessageBox.warning(
                self,
                "自動啟動",
                f"無法更新自動啟動：{exc}",
            )
            return
        self.db.set_setting("autostart", enabled)

    def _finish_settings_save(
        self,
        ui_language: str,
        silent: bool,
    ) -> None:
        self.settings_saved.emit()
        self.ui_language = ui_language
        if not silent:
            self.speak_requested.emit(
                self._t("settings_saved", "設定已保存。"),
                "happy",
            )

    def save_settings(self, silent: bool = False) -> bool:
        previous = self._current_profile_localization()
        values = self._validated_profile_settings()
        if values is None:
            return False
        self._persist_profile_settings(values)
        self._migrate_localized_profile_defaults(previous, values)
        self._apply_saved_profile(values)
        self._save_reminder_settings(values.ui_language)
        self._save_general_settings(values.ui_language)
        self.save_voice_settings(silent=True)
        self._save_api_key_if_provided()
        self._save_autostart_setting()
        self._finish_settings_save(values.ui_language, silent)
        return True
    def clear_api_key(self) -> None:
        platform = self.platform_services.capabilities
        answer = QMessageBox.question(
            self,
            "移除 API 金鑰",
            f"確定要移除由 {platform.display_name} 安全保存的 OpenAI API 金鑰嗎？",
        )
        if answer == QMessageBox.Yes:
            self.secret_store.clear()
            self.api_key_input.clear()
            self.api_key_input.setPlaceholderText("貼上新的 OpenAI Project API Key")
            self.api_status.setText("OpenAI API：未設定，使用離線人設")

    def open_work_folder(self) -> None:
        value = self.work_folder.text().strip()
        if value and Path(value).is_dir():
            if self._permission_allowed("open_folder", "開啟工作室資料夾"):
                self.platform_services.open_path(Path(value))
        else:
            QMessageBox.information(
                self, "工作資料夾", "請先填入有效的資料夾路徑。"
            )


class CompanionWindow(QMainWindow):
    def __init__(
        self,
        startup_speech: bool = True,
        services: CompanionServices | None = None,
        defer_visual_startup: bool = False,
    ):
        super().__init__()
        runtime_services = services or create_default_services(
            data_dir(),
            resource_path("voice_listener.ps1"),
            self,
        )
        self._initialize_runtime_services(runtime_services)
        self._run_first_run_wizard_if_needed(startup_speech)
        self.dashboard = self._create_dashboard()
        self._connect_dashboard_signals()
        self._connect_speech_service_signals()
        self._initialize_companion_state(startup_speech)
        self._configure_character_window()
        self._initialize_motion_state()
        self._build_ui(defer_visual_assets=defer_visual_startup)
        self._reload_background_agents()
        self._apply_character_scale(
            self.character_scale_percent,
            preserve_anchor=False,
        )
        self._position_corner()
        if not defer_visual_startup:
            self._finish_visual_startup()

    def _initialize_runtime_services(
        self,
        services: CompanionServices,
    ) -> None:
        self.db = services.db
        self.platform_services = (
            services.platform_services or current_platform_services()
        )
        self.backup_manager = services.backup_manager
        self.secret_store = services.secret_store
        self.azure_secret_store = services.azure_secret_store
        self.secret_store_factory = services.secret_store_factory
        self.tts = services.local_tts
        self.cloud_tts = services.cloud_tts
        self.azure_tts = services.azure_speech
        self.speech_providers = (
            services.speech_providers
            or create_builtin_speech_registry(
                self.tts,
                self.cloud_tts,
                self.azure_tts,
            )
        )
        self.realtime = services.realtime
        self.listener = services.listener

    def _run_first_run_wizard_if_needed(
        self,
        startup_speech: bool,
    ) -> None:
        should_run = (
            startup_speech
            and "--smoke-auto-exit" not in sys.argv
            and not bool(
                self.db.setting("onboarding_complete", False)
            )
        )
        if should_run:
            FirstRunWizard(
                self.db,
                platform_services=self.platform_services,
            ).exec()

    def _create_dashboard(self) -> Dashboard:
        return Dashboard(
            self.db,
            DashboardDependencies(
                listener=self.listener,
                secret_store=self.secret_store,
                azure_secret_store=self.azure_secret_store,
                secret_store_factory=self.secret_store_factory,
                platform_services=self.platform_services,
            ),
        )

    def _connect_dashboard_signals(self) -> None:
        self.dashboard.speak_requested.connect(self.speak)
        self.dashboard.voice_preview_requested.connect(self.preview_voice)
        self.dashboard.realtime_toggle_requested.connect(
            self.toggle_realtime
        )
        self.dashboard.volume_changed.connect(self._apply_voice_volume)
        self.dashboard.visibility_changed.connect(
            self._dashboard_visibility_changed
        )
        self.dashboard.topmost_mode_changed.connect(
            lambda _mode: self._topmost_policy_tick()
        )
        self.dashboard.character_scale_preview.connect(
            self._apply_character_scale
        )
        self.dashboard.state_requested.connect(self.set_state)
        self.dashboard.ai_wait_expression_requested.connect(
            self._start_ai_wait_expression
        )
        self.dashboard.ai_wait_expression_finished.connect(
            self._finish_ai_wait_expression
        )
        self._apply_voice_volume(
            int(self.db.setting("voice_volume_percent", 125)),
            bool(self.db.setting("voice_muted", False)),
        )
        self.background_scheduler: ManagerWorkerScheduler | None = None
        self.dashboard.settings_saved.connect(
            self._reload_physics_settings
        )
        self.dashboard.settings_saved.connect(self._reload_profile)
        self.dashboard.settings_saved.connect(
            self._reload_background_agents
        )

    def _connect_speech_service_signals(self) -> None:
        self.tts.finished.connect(self._speech_audio_finished)
        self.tts.failed.connect(self._windows_voice_failed)
        self.tts.viseme_cue.connect(self._audio_viseme_cue)
        self.cloud_tts.finished.connect(self._speech_audio_finished)
        self.cloud_tts.failed.connect(self._cloud_voice_failed)
        self.cloud_tts.viseme_cue.connect(self._audio_viseme_cue)
        if self.azure_tts is not None:
            self.azure_tts.finished.connect(self._speech_audio_finished)
            self.azure_tts.failed.connect(self._azure_voice_failed)
            self.azure_tts.viseme_cue.connect(self._audio_viseme_cue)
        self.realtime.status_changed.connect(self._realtime_status)
        self.realtime.user_transcript.connect(
            self._realtime_user_text
        )
        self.realtime.assistant_transcript.connect(
            self._realtime_assistant_text
        )
        self.realtime.speaking_changed.connect(
            self._realtime_speaking
        )
        self.realtime.viseme_cue.connect(self._audio_viseme_cue)
        self.realtime.failed.connect(self._realtime_failed)

    def _initialize_companion_state(self, startup_speech: bool) -> None:
        self.state = "idle"
        self.expression_generation = 0
        self.expression_arbiter = ExpressionArbiter(
            set(EXPRESSION_POSES) | {"idle", "speaking"}
        )
        self.active_ai_wait_generation = 0
        self.active_ai_wait_expression = ""
        self.speech_queue: deque[QueuedSpeech] = deque()
        self.speech_playing = False
        self.active_speech_text = ""
        self.active_speech_engine = ""
        self.cloud_fallback_active = False
        self.drag_offset: QPoint | None = None
        self.last_overwork_notice = ""
        self._startup_speech_requested = startup_speech
        self._visual_startup_complete = False
        self._closing = False

    def _configure_character_window(self) -> None:
        self.setWindowTitle(profile_window_title(self.db))
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.character_topmost_active = True
        self.character_behind_hwnd = 0
        self._smart_overlap_hwnd = 0

    def _initialize_motion_state(self) -> None:
        self.character_base_x = 2
        self.character_base_y = CHARACTER_BASE_Y
        self.motion_base_x = 0
        self.motion_base_y = self.character_base_y
        self.ambient_motion_x = 0.0
        self.ambient_motion_y = 0.0
        self.ambient_motion_target_x = 0.0
        self.ambient_motion_target_y = 0.0
        self.speech_motion_y = 0.0
        self.speech_motion_target_y = 0.0
        self.gesture_motion_x = 0.0
        self.gesture_motion_y = 0.0
        self.last_composed_body_position: tuple[int, int] | None = None
        saved_scale = int(
            self.db.setting(
                "character_scale_percent",
                CHARACTER_SCALE_DEFAULT,
            )
        )
        self.character_scale_percent = max(
            CHARACTER_SCALE_MIN,
            min(CHARACTER_SCALE_MAX, saved_scale),
        )
        self.character_scale = self.character_scale_percent / 100.0
        self.setFixedSize(
            CHARACTER_CANVAS_WIDTH,
            CHARACTER_BASE_Y + CHARACTER_IMAGE_SIZE,
        )
    def _finish_visual_startup(self) -> None:
        if self._visual_startup_complete:
            return
        self._load_expression_assets()
        self._build_physics_layers()
        self._build_attention_layers()
        self._build_mouth_frames()
        self._update_physics_pose("idle")
        self._apply_physics_visibility()
        self._render_attention_layers(force=True)
        self._setup_timers()
        self._setup_tray()
        self._visual_startup_complete = True
        if self._startup_speech_requested:
            self.speak(
                f"妾已就位。{profile_setting(self.db, 'user_title')}點妾，"
                "便可展開今日卷冊。",
                "idle",
            )

    def complete_deferred_startup(self) -> None:
        """Finish heavy visual preparation after the first window paint."""
        if self._closing or self._visual_startup_complete:
            return
        self._finish_visual_startup()
        self.dashboard.update_panel.start_automatic_check()

    def _load_expression_assets(self) -> None:
        for expression in EXPRESSION_IMAGE_ASSETS:
            if expression in self.expression_pixmaps:
                continue
            pix = QPixmap(
                str(resource_path(f"assets/expressions/{expression}.png"))
            )
            self.expression_pixmaps[expression] = pix.scaled(
                465, 465, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

    def _build_ui(self, defer_visual_assets: bool = False) -> None:
        root = QWidget()
        root.setAttribute(Qt.WA_TranslucentBackground)
        self.setCentralWidget(root)
        self._build_speech_bubble(root)
        self._build_character_widget(root, defer_visual_assets)
        self._build_expression_overlay(root)
        self._build_physics_overlay_widgets(root)
        self._build_attention_overlay_widgets(root)
        self.bubble.raise_()
        self.bubble.hide()

    def _build_speech_bubble(self, root: QWidget) -> None:
        self.bubble = QFrame(root)
        self.bubble.setObjectName("speechBubble")
        self.bubble.setGeometry(18, 8, 430, 96)
        self.bubble.setStyleSheet(
            "QFrame#speechBubble{background:rgba(15,29,40,225);"
            "border:1px solid #5b9bb8;border-radius:18px;}"
        )
        layout = QVBoxLayout(self.bubble)
        self.bubble_name = QLabel(
            profile_setting(self.db, "assistant_name")
        )
        self.bubble_name.setStyleSheet(
            "color:#8fc9e0;font-size:11px;"
        )
        self.bubble_text = QLabel()
        self.bubble_text.setWordWrap(True)
        self.bubble_text.setMaximumWidth(390)
        self.bubble_text.setStyleSheet(
            "color:#f3f8fa;font-size:14px;"
        )
        layout.addWidget(self.bubble_name)
        layout.addWidget(self.bubble_text, 1)

    def _build_character_widget(
        self,
        root: QWidget,
        defer_visual_assets: bool,
    ) -> None:
        self.character = ClickableLabel(root)
        self.expression_pixmaps: dict[str, QPixmap] = {}
        initial_assets = (
            ("idle",) if defer_visual_assets else EXPRESSION_IMAGE_ASSETS
        )
        for expression in initial_assets:
            source = QPixmap(
                str(
                    resource_path(
                        f"assets/expressions/{expression}.png"
                    )
                )
            )
            self.expression_pixmaps[expression] = source.scaled(
                465,
                465,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        self.safe_layer_rendering = True
        self.conservative_idle = True
        self.physics_features = {
            key: bool(self.db.setting(key, True))
            for key in (
                "physics_sleeves",
                "physics_hair",
                "physics_ornament",
                "physics_eye_tracking",
                "physics_face_parallax",
            )
        }
        self.current_expression = "idle"
        self.character.setPixmap(self.expression_pixmaps["idle"])
        self.character.setScaledContents(True)
        self.character.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        self.character.setGeometry(
            self.character_base_x,
            self.character_base_y,
            CHARACTER_IMAGE_SIZE,
            CHARACTER_IMAGE_SIZE,
        )
        self.character.clicked.connect(self._character_clicked)

    def _build_expression_overlay(self, root: QWidget) -> None:
        self.expression_overlay = QLabel(root)
        self._configure_character_overlay(self.expression_overlay)
        self.expression_overlay.hide()
        self.character_opacity = QGraphicsOpacityEffect(self.character)
        self.character.setGraphicsEffect(self.character_opacity)
        self.character_opacity.setOpacity(1.0)
        self.overlay_opacity = QGraphicsOpacityEffect(
            self.expression_overlay
        )
        self.expression_overlay.setGraphicsEffect(self.overlay_opacity)
        self.overlay_opacity.setOpacity(0.0)

    def _build_physics_overlay_widgets(self, root: QWidget) -> None:
        self.sleeve_left_overlay = QLabel(root)
        self.sleeve_right_overlay = QLabel(root)
        self.hair_left_overlay = QLabel(root)
        self.hair_right_overlay = QLabel(root)
        for overlay in (
            self.sleeve_left_overlay,
            self.sleeve_right_overlay,
            self.hair_left_overlay,
            self.hair_right_overlay,
        ):
            self._configure_character_overlay(overlay)
        self.physics_overlay = QLabel(root)
        self._configure_character_overlay(self.physics_overlay)

    def _build_attention_overlay_widgets(self, root: QWidget) -> None:
        self.face_overlay = QLabel(root)
        self.eye_overlay = QLabel(root)
        for overlay in (self.face_overlay, self.eye_overlay):
            self._configure_character_overlay(overlay)
            overlay.hide()

    def _configure_character_overlay(self, overlay: QLabel) -> None:
        overlay.setScaledContents(True)
        overlay.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        overlay.setGeometry(self.character.geometry())
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
    def _position_corner(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.right() - self.width() - 8,
            screen.bottom() - self.height() + 1,
        )

    def _apply_character_scale(
        self,
        percent: int,
        preserve_anchor: bool = True,
    ) -> None:
        percent = max(
            CHARACTER_SCALE_MIN,
            min(CHARACTER_SCALE_MAX, int(percent)),
        )
        previous_bottom_right = (
            self.frameGeometry().bottomRight()
            if preserve_anchor
            else None
        )
        self.character_scale_percent = percent
        self.character_scale = percent / 100.0
        display_size = max(
            1,
            round(CHARACTER_IMAGE_SIZE * self.character_scale),
        )
        window_width = max(
            CHARACTER_CANVAS_WIDTH,
            display_size + 5,
        )
        window_height = CHARACTER_BASE_Y + display_size
        self.setFixedSize(window_width, window_height)
        self.character_base_x = (window_width - display_size) // 2
        character_geometry = QRect(
            self.character_base_x,
            self.character_base_y,
            display_size,
            display_size,
        )
        for layer in (
            self.character,
            self.expression_overlay,
            self.sleeve_left_overlay,
            self.sleeve_right_overlay,
            self.hair_left_overlay,
            self.hair_right_overlay,
            self.physics_overlay,
            self.face_overlay,
            self.eye_overlay,
        ):
            layer.setGeometry(character_geometry)
        self.bubble.move(
            max(8, (window_width - self.bubble.width()) // 2),
            8,
        )
        self._position_character_layers(
            getattr(self, "motion_base_x", 0),
            getattr(
                self,
                "motion_base_y",
                self.character_base_y,
            ),
        )
        if previous_bottom_right is not None:
            proposed = QPoint(
                previous_bottom_right.x() - self.width() + 1,
                previous_bottom_right.y() - self.height() + 1,
            )
            screen = QApplication.screenAt(previous_bottom_right)
            if screen is None:
                screen = QApplication.primaryScreen()
            available = screen.availableGeometry()
            proposed.setX(
                max(
                    available.left(),
                    min(
                        proposed.x(),
                        available.right() - self.width() + 1,
                    ),
                )
            )
            proposed.setY(
                max(
                    available.top(),
                    min(
                        proposed.y(),
                        available.bottom() - self.height() + 1,
                    ),
                )
            )
            self.move(proposed)

    def _show_bubble(self, text: str) -> None:
        normalized = normalize_for_language(
            text.strip(),
            profile_setting(self.db, "ui_language"),
        )
        if len(normalized) > 230:
            display = (
                normalized[:227].rstrip()
                + "…\n（完整內容請見對話頁）"
            )
        else:
            display = normalized
        self.bubble_text.setText(display)
        text_height = self.bubble_text.fontMetrics().boundingRect(
            QRect(0, 0, 390, 1200),
            Qt.TextWordWrap,
            display,
        ).height()
        bubble_height = max(96, min(202, text_height + 48))
        self.bubble.setGeometry(
            max(8, (self.width() - 430) // 2),
            8,
            430,
            bubble_height,
        )
        self.bubble.show()
        self.bubble.raise_()

    def _setup_timers(self) -> None:
        self._initialize_idle_animation()
        self._initialize_mouth_animation_state()
        self._initialize_mouth_timers()
        self._initialize_physics_animation()
        self._initialize_motion_attention()
        self._initialize_service_timers()

    def _initialize_idle_animation(self) -> None:
        self.idle_phase = 0
        self.idle_pose = "front"
        self._set_expression(self._idle_expression(), fade=False)
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._idle_tick)
        self.idle_timer.start(90)
        self.pose_timer = QTimer(self)
        self.pose_timer.setSingleShot(True)
        self.pose_timer.timeout.connect(self._rotate_idle_pose)
        self._schedule_pose_change()
        self.blink_timer = QTimer(self)
        self.blink_timer.setSingleShot(True)
        self.blink_timer.timeout.connect(self._blink)
        self._schedule_blink()
        self.gaze_timer = QTimer(self)
        self.gaze_timer.setSingleShot(True)
        self.gaze_timer.timeout.connect(self._start_attention_glance)
        self._schedule_attention_glance()
        self.ambient_timer = QTimer(self)
        self.ambient_timer.setSingleShot(True)
        self.ambient_timer.timeout.connect(
            self._show_ambient_expression
        )
        self._schedule_ambient_expression()

    def _initialize_mouth_animation_state(self) -> None:
        self.mouth_open = False
        self.mouth_frame_index = 0
        self.idle_blinking = False
        self.speech_blinking = False
        self.blink_restore_pixmap = QPixmap()
        self.speech_blink_restore_pixmap = QPixmap()
        self.speech_visual_pixmap = QPixmap()
        self.blink_generation = 0
        self.audio_driven_mouth = False
        self.mouth_closing = False
        self.viseme_dynamics = VisemeDynamics()
        self.mouth_aperture_target = 0.0
        self.head_motion_y = 0.0
        self.after_speech_state = "idle"
        self.speech_closed_expression = "idle"
        self.speech_mid_expression = "mouth_mid"
        self.speech_open_expression = "speaking"
        self.speech_current_expression = "idle"
        self.speech_pose_suffix = "_front"
        self.speech_gesture_expression: str | None = None
        self.realtime_mouth_active = False
        self.mouth_transition_from = QPixmap()
        self.mouth_transition_to = QPixmap()
        self.mouth_transition_started = 0.0
        self.mouth_transition_duration = (
            VISEME_CHANGE_TRANSITION_SECONDS
        )
        self.realtime_after_speech_state = "idle"

    def _initialize_mouth_timers(self) -> None:
        self.mouth_timer = QTimer(self)
        self.mouth_timer.setSingleShot(True)
        self.mouth_timer.timeout.connect(self._mouth_tick)
        self.mouth_visual_timer = QTimer(self)
        self.mouth_visual_timer.setInterval(16)
        self.mouth_visual_timer.timeout.connect(
            self._render_audio_mouth_transition
        )
        self.speech_finish_timer = QTimer(self)
        self.speech_finish_timer.setSingleShot(True)
        self.speech_finish_timer.timeout.connect(
            self._complete_speech_audio_finished
        )
        self.realtime_finish_timer = QTimer(self)
        self.realtime_finish_timer.setSingleShot(True)
        self.realtime_finish_timer.timeout.connect(
            self._complete_realtime_speaking_stop
        )

    def _initialize_physics_animation(self) -> None:
        self._reset_physics_dynamics()
        self.physics_timer = QTimer(self)
        self.physics_timer.timeout.connect(self._physics_tick)
        self.physics_timer.start(33)

    def _initialize_motion_attention(self) -> None:
        self.gaze_x = 0.0
        self.gaze_y = 0.0
        self.gaze_target_x = 0.0
        self.gaze_target_y = 0.0
        self.motion_timer = QTimer(self)
        self.motion_timer.setInterval(16)
        self.motion_timer.timeout.connect(self._motion_tick)
        self.motion_timer.start()
        self.attention_pose = ""
        self.attention_timer = QTimer(self)
        self.attention_timer.timeout.connect(self._attention_tick)
        self.attention_timer.start(40)

    def _initialize_service_timers(self) -> None:
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(20_000)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(
            self.dashboard.refresh_work_time
        )
        self.clock_timer.start(1_000)
        self.topmost_timer = QTimer(self)
        self.topmost_timer.setInterval(100)
        self.topmost_timer.timeout.connect(self._topmost_policy_tick)
        self.topmost_timer.start()
        self.background_agent_timer = QTimer(self)
        self.background_agent_timer.setInterval(1_000)
        self.background_agent_timer.timeout.connect(
            self._background_agent_tick
        )
        self.background_agent_timer.start()
    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(
            application_icon(), self
        )
        self.tray.setToolTip(profile_window_title(self.db))
        menu = QMenu()
        self.tray_menu = menu
        open_action = QAction("開啟今日卷冊", self)
        quit_action = QAction("讓寒歸劍", self)
        open_action.triggered.connect(self.open_dashboard)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.open_dashboard()
            if reason == QSystemTrayIcon.Trigger
            else None
        )
        self.tray.show()

    def _idle_tick(self) -> None:
        if self.state != "idle":
            return
        self._ensure_idle_mouth_closed()
        self.idle_phase = (self.idle_phase + 1) % 720
        breath = (math.sin(self.idle_phase * math.tau / 72.0) + 1.0) / 2.0
        self.current_breath = breath
        sway = math.sin(self.idle_phase * math.tau / 210.0)
        self.ambient_motion_target_y = breath * 2.0
        self.ambient_motion_target_x = sway * 0.7

    def _physics_enabled(self, key: str) -> bool:
        return bool(self.physics_features.get(key, True))

    def _reload_physics_settings(self) -> None:
        for key in tuple(self.physics_features):
            self.physics_features[key] = bool(self.db.setting(key, True))
        self._apply_physics_visibility()
        self._render_attention_layers(force=True)

    def _reload_profile(self) -> None:
        title = profile_window_title(self.db)
        self.setWindowTitle(title)
        self.dashboard.apply_profile_from_database()
        self.bubble_name.setText(self.dashboard.assistant_name)
        if hasattr(self, "tray"):
            self.tray.setToolTip(title)

    def _reload_background_agents(self) -> None:
        scheduler = getattr(self, "background_scheduler", None)
        if scheduler is not None:
            scheduler.close()
        self.background_scheduler = None
        if not bool(self.db.setting("background_assistant_enabled", False)):
            return
        proactive_mode = str(
            self.db.setting("proactive_mode", "平衡（推薦）")
        )
        watched_names = [
            name.strip()[:80]
            for name in str(
                self.db.setting(
                    "background_watch_apps",
                    "Visual Studio Code,GitHub Desktop",
                )
            ).split(",")
            if name.strip()
        ][:12]
        workers = []
        if watched_names and not proactive_mode.startswith("安靜"):
            workers.append(
                VisibleAppWorker(
                    visible_windows,
                    {name: (name,) for name in watched_names},
                )
            )
        report_text = str(
            self.db.setting("background_diagnostic_report", "")
        ).strip()
        if report_text:
            report_path = Path(report_text)
            workers.append(
                DiagnosticReportWorker(lambda path=report_path: path)
            )
        if not workers:
            return
        event_cooldown = (
            1_800.0
            if proactive_mode.startswith("安靜")
            else 300.0
            if proactive_mode.startswith("積極")
            else 900.0
        )
        self.background_scheduler = ManagerWorkerScheduler(
            workers,
            max_workers=2,
            event_cooldown_seconds=event_cooldown,
            global_cooldown_seconds=max(180.0, event_cooldown / 3),
        )

    def _background_agent_tick(self) -> None:
        scheduler = getattr(self, "background_scheduler", None)
        if scheduler is None or self._closing:
            return
        scheduler.tick()
        quiet = (
            self.dashboard.mode in {"勿擾", "會議", "離席", "休眠"}
            or self.state != "idle"
            or self.speech_playing
            or self.realtime_mouth_active
        )
        for observation in scheduler.drain(now=local_wall_time(), quiet=quiet):
            if not self.set_state(
                observation.expression,
                source="ambient",
                intensity=0.28,
            ):
                continue
            self._show_bubble(observation.message)
            self._schedule_return_to_idle(2_800, observation.expression)
            QTimer.singleShot(
                3_400,
                lambda: None if self.speech_playing else self.bubble.hide(),
            )

    def _apply_physics_visibility(self, expression: str | None = None) -> None:
        if not hasattr(self, "physics_overlay"):
            return
        pose_supported = (
            (
                expression
                if expression is not None
                else getattr(self, "current_expression", "")
            )
            in getattr(self, "physics_expression_poses", {})
        )
        self.sleeve_left_overlay.setVisible(
            pose_supported and self._physics_enabled("physics_sleeves")
        )
        self.sleeve_right_overlay.setVisible(
            pose_supported and self._physics_enabled("physics_sleeves")
        )
        self.hair_left_overlay.setVisible(
            pose_supported and self._physics_enabled("physics_hair")
        )
        self.hair_right_overlay.setVisible(
            pose_supported and self._physics_enabled("physics_hair")
        )
        self.physics_overlay.setVisible(
            pose_supported and self._physics_enabled("physics_ornament")
        )

    def _build_physics_layers(self) -> None:
        self._reset_physics_dynamics()
        self.active_physics_pose = "front"
        self.physics_anchors = self._ornament_anchors()
        self.hair_anchors = self._hair_anchors()
        self.sleeve_anchors = self._sleeve_anchors()
        self.physics_sources: dict[str, QPixmap] = {}
        self.hair_sources: dict[str, dict[str, QPixmap]] = {}
        self.sleeve_sources: dict[str, dict[str, QPixmap]] = {}
        self._load_physics_sources()
        self.physics_expression_poses = (
            self._physics_expression_pose_map()
        )

    def _reset_physics_dynamics(self) -> None:
        self.physics_phase = 0
        self.ornament_angle = 0.0
        self.ornament_velocity = 0.0
        self.hair_left_angle = 0.0
        self.hair_right_angle = 0.0
        self.hair_left_velocity = 0.0
        self.hair_right_velocity = 0.0
        self.sleeve_left_angle = 0.0
        self.sleeve_right_angle = 0.0
        self.sleeve_left_velocity = 0.0
        self.sleeve_right_velocity = 0.0
        self.current_breath = 0.0
        self.last_rendered_ornament_angle = 99.0
        self.last_rendered_hair_angles = (99.0, 99.0)
        self.last_rendered_sleeves = (99.0, 99.0, 99.0)

    @staticmethod
    def _ornament_anchors() -> frozendict:
        return frozendict(
            {
                "cheek": QPoint(315, 96),
                "lean": QPoint(306, 96),
                "front": QPoint(293, 72),
            }
        )

    @staticmethod
    def _hair_anchors() -> frozendict:
        return frozendict(
            {
                "cheek": frozendict(
                    {
                        "left": QPoint(187, 178),
                        "right": QPoint(268, 168),
                    }
                ),
                "lean": frozendict(
                    {
                        "left": QPoint(177, 174),
                        "right": QPoint(254, 162),
                    }
                ),
                "front": frozendict(
                    {
                        "left": QPoint(183, 171),
                        "right": QPoint(278, 168),
                    }
                ),
            }
        )

    @staticmethod
    def _sleeve_anchors() -> frozendict:
        return frozendict(
            {
                "cheek": frozendict(
                    {
                        "left": QPoint(132, 253),
                        "right": QPoint(330, 239),
                    }
                ),
                "lean": frozendict(
                    {
                        "left": QPoint(130, 252),
                        "right": QPoint(326, 239),
                    }
                ),
                "front": frozendict(
                    {
                        "left": QPoint(131, 253),
                        "right": QPoint(333, 253),
                    }
                ),
            }
        )

    def _load_physics_sources(self) -> None:
        for pose, suffix in (
            ("cheek", ""),
            ("lean", "_lean"),
            ("front", "_front"),
        ):
            self.physics_sources[pose] = self._scaled_expression_asset(
                f"v120_ornament{suffix}.png"
            )
            self.hair_sources[pose] = {}
            self.sleeve_sources[pose] = {}
            for side in ("left", "right"):
                hair = self._scaled_expression_asset(
                    f"v120_hair_{side}{suffix}.png"
                )
                self.hair_sources[pose][side] = (
                    self._hair_texture_only(hair)
                )
                sleeve = self._scaled_expression_asset(
                    f"v120_sleeve_{side}{suffix}.png"
                )
                self.sleeve_sources[pose][side] = (
                    self._sleeve_texture_only(sleeve, side)
                )

    @staticmethod
    def _scaled_expression_asset(filename: str) -> QPixmap:
        source = QPixmap(
            str(resource_path(f"assets/expressions/{filename}"))
        )
        return source.scaled(
            465,
            465,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    def _physics_expression_pose_map(self) -> dict[str, str]:
        pose_map = {
            **{
                f"{prefix}{suffix}": pose
                for prefix in PHYSICS_SPEECH_FRAME_PREFIXES
            }
            for suffix, pose in PHYSICS_POSE_SUFFIXES
        }
        for expression, pose in EXPRESSION_POSES.items():
            self._register_expression_pose_frames(
                pose_map,
                expression,
                pose,
            )
        return pose_map

    def _register_expression_pose_frames(
        self,
        pose_map: dict[str, str],
        expression: str,
        pose: str,
    ) -> None:
        if expression in self.expression_pixmaps:
            pose_map[expression] = pose
        for frame in EXPRESSION_SPEECH_FRAMES[expression].values():
            if frame in self.expression_pixmaps:
                pose_map[frame] = pose
        for frame in EXPRESSION_DERIVED_VISEME_FRAMES[
            expression
        ].values():
            pose_map[frame] = pose
        blink_frame = EXPRESSION_BLINK_FRAMES.get(expression)
        if blink_frame is not None and blink_frame in self.expression_pixmaps:
            pose_map[blink_frame] = pose
    @staticmethod
    def _hair_texture_only(source: QPixmap) -> QPixmap:
        """Remove skin and clothing accidentally carried by a hair cutout.

        Rotating a complete cutout that contains cheek, neck or sleeve pixels
        produces dark seams across the face. Hair physics only needs the dark,
        low-chroma strands; all other opaque pixels are made transparent.
        """
        safe = QPixmap(source)
        mask = QPixmap(source.size())
        mask.fill(Qt.transparent)
        gradient = QLinearGradient(0, 278, 0, 318)
        gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
        gradient.setColorAt(1.0, QColor(255, 255, 255, 255))
        painter = QPainter(mask)
        painter.fillRect(
            QRect(0, 278, source.width(), source.height() - 278),
            gradient,
        )
        painter.end()
        painter = QPainter(safe)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, mask)
        painter.end()
        return safe

    @staticmethod
    def _sleeve_texture_only(source: QPixmap, side: str) -> QPixmap:
        """Keep only outer blue fabric so hands and hair never ghost."""
        safe = QPixmap(source)
        mask = QPixmap(source.size())
        mask.fill(Qt.transparent)
        painter = QPainter(mask)
        if side == "left":
            gradient = QLinearGradient(145, 0, 175, 0)
            gradient.setColorAt(0.0, QColor(255, 255, 255, 255))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.fillRect(QRect(0, 0, 175, source.height()), gradient)
        else:
            gradient = QLinearGradient(290, 0, 320, 0)
            gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 255))
            painter.fillRect(
                QRect(290, 0, source.width() - 290, source.height()),
                gradient,
            )
        painter.end()
        painter = QPainter(safe)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, mask)
        painter.end()
        return safe

    def _build_attention_layers(self) -> None:
        self.face_sources = {}
        self.eye_sources = {}
        for pose, suffix in (
            ("cheek", ""),
            ("lean", "_lean"),
            ("front", "_front"),
        ):
            self.face_sources[pose] = QPixmap(
                str(
                    resource_path(
                        f"assets/expressions/v120_face{suffix}.png"
                    )
                )
            ).scaled(465, 465, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.eye_sources[pose] = QPixmap(
                str(
                    resource_path(
                        f"assets/expressions/v120_eyes{suffix}.png"
                    )
                )
            ).scaled(465, 465, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _render_attention_layers(self, force: bool = False) -> None:
        if not hasattr(self, "face_overlay"):
            return
        render_base = self._render_base_expression()
        pose = self.physics_expression_poses.get(
            render_base,
            getattr(self, "idle_pose", "front"),
        )
        eye_expression = getattr(self, "current_expression", "")
        render_state = (
            pose,
            eye_expression,
            round(getattr(self, "gaze_x", 0.0), 2),
            round(getattr(self, "gaze_y", 0.0), 2),
        )
        if not force and render_state == getattr(
            self, "attention_render_state", None
        ):
            return
        self.attention_pose = pose
        self.attention_render_state = render_state
        face_source = self.expression_face_sources.get(
            render_base,
            self.face_sources[pose],
        )
        eye_source = getattr(self, "expression_eye_sources", {}).get(
            render_base,
            self.eye_sources[pose],
        )
        gaze_x = getattr(self, "gaze_x", 0.0)
        gaze_y = getattr(self, "gaze_y", 0.0)
        face_rendered = QPixmap(face_source.size())
        face_rendered.fill(Qt.transparent)
        face_painter = QPainter(face_rendered)
        face_painter.setRenderHint(QPainter.SmoothPixmapTransform)
        # Never translate a photographed face patch over the base portrait.
        # Even a sub-pixel offset creates a visible duplicate lip/eyelid seam.
        # Face parallax is represented by a gaze-dependent, alpha-clipped
        # lighting shift instead; the facial geometry remains registered.
        face_painter.drawPixmap(0, 0, face_source)
        face_painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        face_light = QLinearGradient(
            115 + gaze_x * 18,
            105 + gaze_y * 9,
            345 + gaze_x * 18,
            315 + gaze_y * 9,
        )
        face_light.setColorAt(0.0, QColor(175, 215, 235, 0))
        face_light.setColorAt(
            0.48,
            QColor(225, 242, 250, 7 + round(abs(gaze_x) * 3)),
        )
        face_light.setColorAt(
            1.0,
            QColor(20, 38, 58, 5 + round(abs(gaze_y) * 2)),
        )
        face_painter.fillRect(face_rendered.rect(), face_light)
        face_painter.end()
        eye_rendered = QPixmap(eye_source.size())
        eye_rendered.fill(Qt.transparent)
        # Do not paint synthetic catchlights or move a photographed eye patch.
        # Both approaches introduce white specks or duplicated eyelid edges.
        # Mouse attention is expressed through the registered face lighting
        # and body micro-turn below, leaving the canonical eye art untouched.
        self.face_overlay.setPixmap(face_rendered)
        self.eye_overlay.setPixmap(eye_rendered)

    def _attention_tick(self) -> None:
        if getattr(self, "pose_transition_active", False):
            self.face_overlay.hide()
            self.eye_overlay.hide()
            return
        active = (
            self.state in {"idle", "speaking"}
            or self._render_base_expression() in EXPRESSION_POSES
        )
        if active:
            face_center = self.mapToGlobal(
                QPoint(
                    self.character_base_x
                    + round(235 * self.character_scale),
                    self.character_base_y
                    + round(165 * self.character_scale),
                )
            )
            cursor = QCursor.pos()
            delta_x = cursor.x() - face_center.x()
            delta_y = cursor.y() - face_center.y()
            distance = math.hypot(delta_x, delta_y)
            if distance <= 1050:
                distance_weight = max(0.0, 1.0 - max(0.0, distance - 720) / 330)
                self.gaze_target_x = max(
                    -1.0,
                    min(1.0, delta_x / 520.0),
                ) * distance_weight
                self.gaze_target_y = max(
                    -1.0,
                    min(1.0, delta_y / 360.0),
                ) * distance_weight
            else:
                self.gaze_target_x = 0.0
                self.gaze_target_y = 0.0
        else:
            self.gaze_target_x = 0.0
            self.gaze_target_y = 0.0
        smoothing = 0.15 if active else 0.22
        self.gaze_x += (self.gaze_target_x - self.gaze_x) * smoothing
        self.gaze_y += (self.gaze_target_y - self.gaze_y) * smoothing
        if not active:
            self.face_overlay.hide()
            self.eye_overlay.hide()
            return
        self._render_attention_layers()
        self._compose_character_position()
        expression_dynamic = (
            self._render_base_expression() in self.physics_expression_poses
            and self.expression_overlay.isHidden()
        )
        self.face_overlay.setVisible(
            expression_dynamic
            and self._physics_enabled("physics_face_parallax")
        )
        # Speech and blink frames already contain the photographed eyes.
        # Keeping the gaze patch out of that path prevents duplicate eyelid
        # seams and white specks while preserving idle eye tracking.
        show_eye_layer = (
            expression_dynamic
            and self.state != "speaking"
            and not getattr(self, "idle_blinking", False)
            and not self.speech_blinking
            and self._physics_enabled("physics_eye_tracking")
        )
        self.eye_overlay.setVisible(show_eye_layer)
        if expression_dynamic:
            self.face_overlay.raise_()
        if show_eye_layer:
            self.eye_overlay.raise_()
        self.bubble.raise_()

    def _motion_tick(self) -> None:
        """Blend every motion source before moving any visible layer.

        Idle breathing, speech emphasis and emotional gestures used to write
        the character position independently.  Their timers could therefore
        pull the body between different coordinates on adjacent frames.  Each
        source now owns only its target offset and this compositor is the sole
        place that moves the complete layered character.
        """
        if self.state != "idle":
            self.ambient_motion_target_x = 0.0
            self.ambient_motion_target_y = 0.0
        if self.state != "speaking":
            self.speech_motion_target_y = 0.0
        self.ambient_motion_x += (
            self.ambient_motion_target_x - self.ambient_motion_x
        ) * 0.20
        self.ambient_motion_y += (
            self.ambient_motion_target_y - self.ambient_motion_y
        ) * 0.20
        self.speech_motion_y += (
            self.speech_motion_target_y - self.speech_motion_y
        ) * 0.34
        for attribute in (
            "ambient_motion_x",
            "ambient_motion_y",
            "speech_motion_y",
        ):
            value = getattr(self, attribute)
            if abs(value) < 0.015:
                setattr(self, attribute, 0.0)
        self._compose_character_position()

    def _compose_character_position(self) -> None:
        scale = getattr(self, "character_scale", 1.0)
        tracked_gaze_x = (
            getattr(self, "gaze_x", 0.0)
            if self._physics_enabled("physics_eye_tracking")
            else 0.0
        )
        body_turn_x = round(tracked_gaze_x * 1.6 * scale)
        composed_x = (
            self.ambient_motion_x + self.gesture_motion_x
        )
        composed_y = (
            self.ambient_motion_y
            + self.speech_motion_y
            + self.gesture_motion_y
        )
        self.motion_base_x = round(composed_x)
        self.motion_base_y = self.character_base_y + round(composed_y)
        body_x = (
            self.character_base_x
            + round(composed_x * scale)
            + body_turn_x
        )
        body_y = self.character_base_y + round(composed_y * scale)
        position = (body_x, body_y)
        if position == self.last_composed_body_position:
            return
        for layer in (
            self.character,
            self.expression_overlay,
            self.sleeve_left_overlay,
            self.sleeve_right_overlay,
            self.hair_left_overlay,
            self.hair_right_overlay,
            self.physics_overlay,
        ):
            layer.move(body_x, body_y)
        if hasattr(self, "face_overlay"):
            self.face_overlay.move(body_x, body_y)
            self.eye_overlay.move(body_x, body_y)
        self.last_composed_body_position = position

    def _position_character_layers(self, base_x: int, base_y: int) -> None:
        """Compatibility entry point for direct positioning and old tests."""
        self.ambient_motion_x = float(base_x)
        self.ambient_motion_y = float(base_y - self.character_base_y)
        self.ambient_motion_target_x = self.ambient_motion_x
        self.ambient_motion_target_y = self.ambient_motion_y
        self.last_composed_body_position = None
        self._compose_character_position()

    def _update_physics_pose(self, expression: str) -> None:
        pose = self.physics_expression_poses.get(expression)
        if pose is None:
            if hasattr(self, "physics_overlay"):
                self.physics_overlay.hide()
                self.hair_left_overlay.hide()
                self.hair_right_overlay.hide()
                self.sleeve_left_overlay.hide()
                self.sleeve_right_overlay.hide()
            return
        pose_changed = getattr(self, "active_physics_pose", None) != pose
        self.active_physics_pose = pose
        if hasattr(self, "physics_overlay"):
            self._apply_physics_visibility(expression)
            if pose_changed:
                self.ornament_velocity += (
                    0.45 if pose == "lean" else -0.35 if pose == "front" else 0.25
                )
                self.hair_left_velocity += (
                    0.12 if pose == "lean" else -0.09
                )
                self.hair_right_velocity += (
                    -0.1 if pose == "lean" else 0.08
                )
                self.sleeve_left_velocity += (
                    0.035 if pose == "lean" else -0.025
                )
                self.sleeve_right_velocity += (
                    -0.03 if pose == "lean" else 0.022
                )
            self._render_sleeve_layers(force=True)
            self._render_hair_layers(force=True)
            self._render_physics_layer(force=True)

    def _physics_tick(self) -> None:
        if not hasattr(self, "physics_overlay"):
            return
        if not any(
            self._physics_enabled(key)
            for key in (
                "physics_sleeves",
                "physics_hair",
                "physics_ornament",
            )
        ):
            return
        self.physics_phase = (self.physics_phase + 1) % 3600
        ambient = math.sin(self.physics_phase * math.tau / 190.0) * 0.38
        voice_motion = (
            (self.viseme_dynamics.smoothed_level - 0.18) * 0.75
            if self.state == "speaking"
            else 0.0
        )
        target = ambient + voice_motion
        acceleration = (
            (target - self.ornament_angle) * 0.085
            - self.ornament_velocity * 0.16
        )
        self.ornament_velocity += acceleration
        self.ornament_angle = max(
            -1.15,
            min(1.15, self.ornament_angle + self.ornament_velocity),
        )
        left_target = ambient * 0.42 + voice_motion * 0.20
        right_target = -ambient * 0.35 + voice_motion * 0.16
        left_acceleration = (
            (left_target - self.hair_left_angle) * 0.032
            - self.hair_left_velocity * 0.105
        )
        right_acceleration = (
            (right_target - self.hair_right_angle) * 0.038
            - self.hair_right_velocity * 0.115
        )
        self.hair_left_velocity += left_acceleration
        self.hair_right_velocity += right_acceleration
        self.hair_left_angle = max(
            -0.34,
            min(0.34, self.hair_left_angle + self.hair_left_velocity),
        )
        self.hair_right_angle = max(
            -0.32,
            min(0.32, self.hair_right_angle + self.hair_right_velocity),
        )
        breath_wave = math.sin(self.physics_phase * math.tau / 145.0)
        if self.state == "speaking":
            self.current_breath = max(
                0.0,
                min(
                    1.0,
                    self.viseme_dynamics.smoothed_level * 0.72 + 0.18,
                ),
            )
        sleeve_voice = voice_motion * 0.055
        sleeve_left_target = breath_wave * 0.075 + sleeve_voice
        sleeve_right_target = -breath_wave * 0.065 - sleeve_voice * 0.82
        self.sleeve_left_velocity += (
            (sleeve_left_target - self.sleeve_left_angle) * 0.020
            - self.sleeve_left_velocity * 0.12
        )
        self.sleeve_right_velocity += (
            (sleeve_right_target - self.sleeve_right_angle) * 0.022
            - self.sleeve_right_velocity * 0.125
        )
        self.sleeve_left_angle = max(
            -0.16,
            min(0.16, self.sleeve_left_angle + self.sleeve_left_velocity),
        )
        self.sleeve_right_angle = max(
            -0.15,
            min(0.15, self.sleeve_right_angle + self.sleeve_right_velocity),
        )
        self._render_sleeve_layers()
        self._render_hair_layers()
        self._render_physics_layer()

    def _render_sleeve_layers(self, force: bool = False) -> None:
        if not self._physics_enabled("physics_sleeves"):
            self.sleeve_left_overlay.hide()
            self.sleeve_right_overlay.hide()
            return
        breath_lift = (
            max(0.0, min(1.0, self.current_breath)) * 0.65
            + (
                self.viseme_dynamics.smoothed_level * 0.35
                if self.state == "speaking"
                else 0.0
            )
        )
        current = (
            self.sleeve_left_angle,
            self.sleeve_right_angle,
            breath_lift,
        )
        previous = self.last_rendered_sleeves
        if (
            not force
            and abs(current[0] - previous[0]) < 0.012
            and abs(current[1] - previous[1]) < 0.012
            and abs(current[2] - previous[2]) < 0.08
        ):
            return
        pose = getattr(self, "active_physics_pose", "front")
        for side, angle, overlay in (
            ("left", self.sleeve_left_angle, self.sleeve_left_overlay),
            ("right", self.sleeve_right_angle, self.sleeve_right_overlay),
        ):
            source = self._local_physics_source(
                f"sleeve_{side}",
                self.sleeve_sources[pose][side],
            )
            anchor = self.sleeve_anchors[pose][side]
            rendered = QPixmap(source.size())
            rendered.fill(Qt.transparent)
            painter = QPainter(rendered)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.translate(0.0, -breath_lift)
            painter.translate(anchor)
            painter.rotate(angle)
            painter.translate(-anchor)
            painter.drawPixmap(0, 0, source)
            painter.end()
            overlay.setPixmap(rendered)
            overlay.raise_()
        self.hair_left_overlay.raise_()
        self.hair_right_overlay.raise_()
        self.physics_overlay.raise_()
        self.bubble.raise_()
        self.last_rendered_sleeves = current

    def _render_hair_layers(self, force: bool = False) -> None:
        if not self._physics_enabled("physics_hair"):
            self.hair_left_overlay.hide()
            self.hair_right_overlay.hide()
            return
        current = (self.hair_left_angle, self.hair_right_angle)
        previous = self.last_rendered_hair_angles
        if (
            not force
            and abs(current[0] - previous[0]) < 0.025
            and abs(current[1] - previous[1]) < 0.025
        ):
            return
        pose = getattr(self, "active_physics_pose", "front")
        for side, angle, overlay in (
            ("left", self.hair_left_angle, self.hair_left_overlay),
            ("right", self.hair_right_angle, self.hair_right_overlay),
        ):
            source = self._local_physics_source(
                f"hair_{side}",
                self.hair_sources[pose][side],
            )
            anchor = self.hair_anchors[pose][side]
            rendered = QPixmap(source.size())
            rendered.fill(Qt.transparent)
            painter = QPainter(rendered)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.translate(anchor)
            painter.rotate(angle)
            painter.translate(-anchor)
            painter.drawPixmap(0, 0, source)
            painter.end()
            overlay.setPixmap(rendered)
            overlay.raise_()
        self.physics_overlay.raise_()
        self.bubble.raise_()
        self.last_rendered_hair_angles = current

    def _render_physics_layer(self, force: bool = False) -> None:
        if not self._physics_enabled("physics_ornament"):
            self.physics_overlay.hide()
            return
        pose = getattr(self, "active_physics_pose", "front")
        if (
            not force
            and abs(self.ornament_angle - self.last_rendered_ornament_angle)
            < 0.04
        ):
            return
        source = self._local_physics_source(
            "ornament",
            self.physics_sources[pose],
        )
        anchor = self.physics_anchors[pose]
        rendered = QPixmap(source.size())
        rendered.fill(Qt.transparent)
        painter = QPainter(rendered)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.translate(anchor)
        painter.rotate(self.ornament_angle)
        painter.translate(-anchor)
        painter.drawPixmap(0, 0, source)
        painter.end()
        self.physics_overlay.setPixmap(rendered)
        self.hair_left_overlay.raise_()
        self.hair_right_overlay.raise_()
        self.physics_overlay.raise_()
        self.bubble.raise_()
        self.last_rendered_ornament_angle = self.ornament_angle

    def _idle_expression(self) -> str:
        if self.idle_pose == "lean":
            return "idle_lean"
        if self.idle_pose == "front":
            return "idle_front"
        return "idle"

    def _speaking_expression(self) -> str:
        if self.idle_pose == "lean":
            return "speaking_lean"
        if self.idle_pose == "front":
            return "speaking_front"
        return "speaking"

    def _mouth_mid_expression(self) -> str:
        if self.idle_pose == "lean":
            return "mouth_mid_lean"
        if self.idle_pose == "front":
            return "mouth_mid_front"
        return "mouth_mid"

    def _closed_speech_expression(self) -> str:
        if self.idle_pose == "cheek":
            return CHEEK_SPEECH_CLOSED_EXPRESSION
        return self._idle_expression()

    def _build_mouth_frames(self) -> None:
        mouth_clips = self._mouth_clip_regions()
        self.mouth_clips = mouth_clips
        self._build_speech_mouth_masks(mouth_clips)
        self._build_cheek_neutral_speech_frame()
        self._build_gesture_mouth_masks()
        self._build_derived_expression_visemes()
        blink_regions = self._blink_regions()
        self._build_blink_masks(blink_regions)
        self._build_face_parallax_cutouts(
            blink_regions,
            mouth_clips,
        )
        self._normalize_base_speech_frames()
        self._build_pose_viseme_frames(mouth_clips)
        self._build_expression_anchor_profiles()
        self._build_expression_eye_layers()

    @staticmethod
    def _mouth_clip_regions() -> frozendict[str, QRect]:
        return frozendict(
            {
                "": QRect(168, 195, 64, 40),
                "_lean": QRect(162, 198, 54, 34),
                "_front": QRect(206, 199, 54, 35),
            }
        )

    @staticmethod
    def _soft_rounded_mask(
        regions: Iterable[QRect],
        alpha_steps: tuple[tuple[int, int], ...],
        radius: int,
    ) -> QPixmap:
        mask = QPixmap(465, 465)
        mask.fill(Qt.transparent)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        for region in regions:
            for inset, alpha in alpha_steps:
                painter.setBrush(QColor(255, 255, 255, alpha))
                painter.drawRoundedRect(
                    region.adjusted(inset, inset, -inset, -inset),
                    radius,
                    radius,
                )
        painter.end()
        return mask

    def _build_speech_mouth_masks(
        self,
        mouth_clips: frozendict[str, QRect],
    ) -> None:
        alpha_steps = (
            (0, 52),
            (1, 82),
            (2, 128),
            (3, 255),
        )
        self.mouth_masks = {
            suffix: self._soft_rounded_mask(
                (mouth_clip,),
                alpha_steps,
                9,
            )
            for suffix, mouth_clip in mouth_clips.items()
        }
        self.viseme_mouth_masks = dict(self.mouth_masks)
        self.viseme_mouth_masks[""] = self._soft_rounded_mask(
            (CHEEK_SPEECH_CENTRAL_MOUTH_RECT,),
            alpha_steps,
            9,
        )

    def _build_cheek_neutral_speech_frame(self) -> None:
        cheek_idle = self.expression_pixmaps["idle"]
        cheek_neutral = QPixmap(cheek_idle)
        painter = QPainter(cheek_neutral)
        painter.drawPixmap(
            0,
            0,
            self._masked_mouth_patch(
                self.expression_pixmaps["speaking"],
                "",
            ),
        )
        painter.drawPixmap(
            0,
            0,
            self._masked_region(
                cheek_idle,
                self.viseme_mouth_masks[""],
            ),
        )
        painter.end()
        self.expression_pixmaps[
            CHEEK_SPEECH_CLOSED_EXPRESSION
        ] = cheek_neutral
        self.physics_expression_poses[
            CHEEK_SPEECH_CLOSED_EXPRESSION
        ] = "cheek"

    def _build_gesture_mouth_masks(self) -> None:
        alpha_steps = (
            (0, 48),
            (1, 80),
            (2, 132),
            (3, 210),
            (4, 255),
        )
        self.gesture_mouth_masks = {
            expression: self._soft_rounded_mask(
                (mouth_rect,),
                alpha_steps,
                9,
            )
            for expression, mouth_rect in (
                EXPRESSION_SPEECH_MOUTH_RECTS.items()
            )
        }

    def _build_derived_expression_visemes(self) -> None:
        for expression in EXPRESSION_SPEECH_EXPRESSIONS:
            closed = self.expression_pixmaps[expression]
            source_frames = EXPRESSION_SPEECH_FRAMES[expression]
            for vowel, source_key, opacity in (
                ("I", "mid", 0.68),
                ("U", "round", 0.64),
            ):
                derived = QPixmap(closed)
                painter = QPainter(derived)
                painter.setOpacity(opacity)
                painter.drawPixmap(
                    0,
                    0,
                    self._masked_region(
                        self.expression_pixmaps[
                            source_frames[source_key]
                        ],
                        self.gesture_mouth_masks[expression],
                    ),
                )
                painter.end()
                derived_name = EXPRESSION_DERIVED_VISEME_FRAMES[
                    expression
                ][vowel]
                self.expression_pixmaps[derived_name] = derived

    @staticmethod
    def _blink_regions(
    ) -> frozendict[str, tuple[QRect, QRect]]:
        return frozendict(
            {
                "cheek": (
                    QRect(160, 153, 55, 34),
                    QRect(198, 153, 61, 34),
                ),
                "lean": (
                    QRect(153, 153, 55, 34),
                    QRect(191, 153, 61, 34),
                ),
                "front": (
                    QRect(180, 153, 53, 34),
                    QRect(220, 153, 56, 34),
                ),
            }
        )

    def _build_blink_masks(
        self,
        blink_regions: frozendict[str, tuple[QRect, QRect]],
    ) -> None:
        alpha_steps = (
            (0, 42),
            (1, 76),
            (2, 132),
            (3, 255),
        )
        self.blink_masks = {
            pose: self._soft_rounded_mask(
                regions,
                alpha_steps,
                10,
            )
            for pose, regions in blink_regions.items()
        }
        self.dedicated_blink_regions = blink_regions
        self.dedicated_blink_masks = self.blink_masks

    def _build_face_parallax_cutouts(
        self,
        blink_regions: frozendict[str, tuple[QRect, QRect]],
        mouth_clips: frozendict[str, QRect],
    ) -> None:
        self.face_parallax_cutouts = {}
        for pose, suffix in (
            ("cheek", ""),
            ("lean", "_lean"),
            ("front", "_front"),
        ):
            left_eye, right_eye = blink_regions[pose]
            cutouts = (
                left_eye.adjusted(-5, -4, 5, 4),
                right_eye.adjusted(-5, -4, 5, 4),
                mouth_clips[suffix].adjusted(-7, -6, 7, 6),
            )
            source = QPixmap(465, 465)
            source.fill(Qt.transparent)
            painter = QPainter(source)
            painter.setCompositionMode(
                QPainter.CompositionMode_Source
            )
            painter.drawPixmap(0, 0, self.face_sources[pose])
            painter.setCompositionMode(
                QPainter.CompositionMode_Clear
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.transparent)
            for region in cutouts:
                painter.drawRoundedRect(region, 11, 11)
            painter.end()
            self.face_sources[pose] = source
            self.face_parallax_cutouts[pose] = cutouts

    def _normalize_base_speech_frames(self) -> None:
        for closed_name, open_name, mid_name in (
            ("idle", "speaking", "mouth_mid"),
            ("idle_lean", "speaking_lean", "mouth_mid_lean"),
            ("idle_front", "speaking_front", "mouth_mid_front"),
        ):
            closed = self.expression_pixmaps[
                CHEEK_SPEECH_CLOSED_EXPRESSION
                if closed_name == "idle"
                else closed_name
            ]
            suffix = closed_name.removeprefix("idle")
            self.expression_pixmaps[open_name] = (
                self._compose_mouth_only(
                    closed,
                    self.expression_pixmaps[open_name],
                    suffix,
                )
            )
            mid_source = self.expression_pixmaps[
                "viseme_mid_front"
                if suffix == "_front"
                else f"viseme_i{suffix}"
            ]
            self.expression_pixmaps[mid_name] = (
                self._compose_mouth_only(
                    closed,
                    mid_source,
                    suffix,
                )
            )

    def _compose_mouth_only(
        self,
        closed: QPixmap,
        source: QPixmap,
        suffix: str,
    ) -> QPixmap:
        normalized = QPixmap(closed)
        painter = QPainter(normalized)
        painter.drawPixmap(
            0,
            0,
            self._masked_region(
                source,
                self.viseme_mouth_masks[suffix],
            ),
        )
        painter.end()
        return normalized

    def _build_pose_viseme_frames(
        self,
        mouth_clips: frozendict[str, QRect],
    ) -> None:
        for suffix in mouth_clips:
            closed = self.expression_pixmaps[
                CHEEK_SPEECH_CLOSED_EXPRESSION
                if suffix == ""
                else f"idle{suffix}"
            ]
            opened = self.expression_pixmaps[f"speaking{suffix}"]
            source_frames = (
                (
                    "mouth_wide",
                    self.expression_pixmaps.get(
                        f"viseme_wide{suffix}",
                        opened,
                    ),
                ),
                (
                    "mouth_round",
                    self.expression_pixmaps[f"viseme_round{suffix}"],
                ),
                ("mouth_i", self.expression_pixmaps[f"viseme_i{suffix}"]),
                ("mouth_o", self.expression_pixmaps[f"viseme_o{suffix}"]),
            )
            if suffix == "_front":
                self.expression_pixmaps["mouth_mid_front"] = (
                    self._compose_mouth_only(
                        closed,
                        self.expression_pixmaps["viseme_mid_front"],
                        suffix,
                    )
                )
            for frame_prefix, source in source_frames:
                self.expression_pixmaps[
                    f"{frame_prefix}{suffix}"
                ] = self._compose_mouth_only(
                    closed,
                    source,
                    suffix,
                )
            self._build_blink_viseme_frames(suffix)

    def _build_blink_viseme_frames(self, suffix: str) -> None:
        blink = self.expression_pixmaps[f"blink{suffix}"]
        frame_names = (
            (f"mouth_mid{suffix}", f"blink_mid{suffix}"),
            (f"speaking{suffix}", f"blink_open{suffix}"),
            (f"mouth_wide{suffix}", f"blink_wide{suffix}"),
            (f"mouth_round{suffix}", f"blink_round{suffix}"),
            (f"mouth_i{suffix}", f"blink_i{suffix}"),
            (f"mouth_o{suffix}", f"blink_o{suffix}"),
        )
        for mouth_name, result_name in frame_names:
            combined = QPixmap(blink.size())
            combined.fill(Qt.transparent)
            painter = QPainter(combined)
            painter.drawPixmap(0, 0, blink)
            painter.drawPixmap(
                0,
                0,
                self._masked_mouth_patch(
                    self.expression_pixmaps[mouth_name],
                    suffix,
                ),
            )
            painter.end()
            self.expression_pixmaps[result_name] = combined
    def _masked_mouth_patch(
        self,
        source: QPixmap,
        suffix: str,
        target_expression: str | None = None,
        source_already_aligned: bool = False,
    ) -> QPixmap:
        offset_x, offset_y = self._expression_mouth_offset(
            target_expression
        )
        mask = self.mouth_masks[suffix]
        if source_already_aligned and (offset_x or offset_y):
            mask = self._translated_pixmap(mask, offset_x, offset_y)
        patch = QPixmap(source.size())
        patch.fill(Qt.transparent)
        painter = QPainter(patch)
        painter.drawPixmap(0, 0, source)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, mask)
        painter.end()
        if (
            not source_already_aligned
            and target_expression is not None
            and (offset_x or offset_y)
        ):
            patch = self._translated_pixmap(
                patch,
                offset_x,
                offset_y,
            )
        return patch

    def _build_expression_anchor_profiles(self) -> None:
        """Register a measured facial alignment profile for every expression."""
        base_expressions = {
            "cheek": "idle",
            "lean": "idle_lean",
            "front": "idle_front",
        }
        face_regions = {
            "cheek": QRect(125, 92, 165, 165),
            "lean": QRect(120, 92, 165, 165),
            "front": QRect(150, 88, 165, 170),
        }
        profiles: dict[str, FaceAnchorProfile] = {}
        for expression, pose in self.physics_expression_poses.items():
            if expression not in self.expression_pixmaps:
                continue
            if expression == base_expressions[pose] or expression.startswith(
                (
                    "speaking",
                    "mouth_",
                    "blink",
                    "viseme_",
                )
            ):
                profiles[expression] = FaceAnchorProfile(
                    pose,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    1.0,
                    0.0,
                )
                continue
            offset_x, offset_y = EXPRESSION_FACE_OFFSETS.get(
                expression,
                (0, 0),
            )
            profiles[expression] = FaceAnchorProfile(
                pose,
                offset_x,
                offset_y,
                *EXPRESSION_EYE_OFFSETS.get(expression, (offset_x, offset_y)),
                *EXPRESSION_MOUTH_OFFSETS.get(
                    expression,
                    (offset_x, offset_y),
                ),
                1.0 if expression in EXPRESSION_FACE_OFFSETS else 0.0,
                0.0,
            )
        self.expression_anchor_profiles = profiles
        self.expression_anchor_base_expressions = base_expressions
        self.expression_anchor_face_regions = face_regions

    @staticmethod
    def _estimate_face_offset(
        base: QPixmap,
        target: QPixmap,
        region: QRect,
    ) -> tuple[int, int, float, float]:
        base_image = base.toImage()
        target_image = target.toImage()
        zero_score = CompanionWindow._face_offset_candidate_score(
            base_image,
            target_image,
            region,
            0,
            0,
        )
        best_x = 0
        best_y = 0
        best_score = zero_score
        for offset_y in range(-6, 7):
            for offset_x in range(-6, 7):
                score = CompanionWindow._face_offset_candidate_score(
                    base_image,
                    target_image,
                    region,
                    offset_x,
                    offset_y,
                )
                if score < best_score:
                    best_x = offset_x
                    best_y = offset_y
                    best_score = score
        improvement = (
            0.0
            if zero_score <= 0.0
            else max(0.0, (zero_score - best_score) / zero_score)
        )
        if improvement < 0.018:
            best_x = 0
            best_y = 0
        confidence = min(1.0, improvement / 0.16)
        return best_x, best_y, confidence, best_score

    @staticmethod
    def _face_offset_candidate_score(
        base: QImage,
        target: QImage,
        region: QRect,
        offset_x: int,
        offset_y: int,
    ) -> float:
        difference = 0
        samples = 0
        for y in range(region.top(), region.bottom() + 1, 5):
            target_y = y + offset_y
            if target_y < 0 or target_y >= target.height():
                continue
            for x in range(region.left(), region.right() + 1, 5):
                target_x = x + offset_x
                if target_x < 0 or target_x >= target.width():
                    continue
                pixel_difference = (
                    CompanionWindow._opaque_pixel_difference(
                        base.pixel(x, y),
                        target.pixel(target_x, target_y),
                    )
                )
                if pixel_difference is None:
                    continue
                difference += pixel_difference
                samples += 1
        return difference / max(1, samples)

    @staticmethod
    def _opaque_pixel_difference(
        first: int,
        second: int,
    ) -> int | None:
        alpha_first = (first >> 24) & 0xFF
        alpha_second = (second >> 24) & 0xFF
        if alpha_first < 180 or alpha_second < 180:
            return None
        return (
            abs(((first >> 16) & 0xFF) - ((second >> 16) & 0xFF))
            + abs(((first >> 8) & 0xFF) - ((second >> 8) & 0xFF))
            + abs((first & 0xFF) - (second & 0xFF))
        )
    def _expression_face_offset(
        self,
        expression: str | None,
    ) -> tuple[int, int]:
        profile = getattr(self, "expression_anchor_profiles", {}).get(
            expression or ""
        )
        if profile is None:
            return 0, 0
        return profile.offset_x, profile.offset_y

    def _expression_eye_offset(
        self,
        expression: str | None,
    ) -> tuple[int, int]:
        profile = getattr(self, "expression_anchor_profiles", {}).get(
            expression or ""
        )
        if profile is None:
            return 0, 0
        return profile.eye_offset_x, profile.eye_offset_y

    def _expression_mouth_offset(
        self,
        expression: str | None,
    ) -> tuple[int, int]:
        profile = getattr(self, "expression_anchor_profiles", {}).get(
            expression or ""
        )
        if profile is None:
            return 0, 0
        return profile.mouth_offset_x, profile.mouth_offset_y

    @staticmethod
    def _translated_pixmap(
        source: QPixmap,
        offset_x: int,
        offset_y: int,
    ) -> QPixmap:
        translated = QPixmap(source.size())
        translated.fill(Qt.transparent)
        painter = QPainter(translated)
        painter.drawPixmap(offset_x, offset_y, source)
        painter.end()
        return translated

    def _build_expression_eye_layers(self) -> None:
        """Match the tracking layer to every mouth frame.

        The cheek speaking frame has slightly different eye registration from
        its idle frame. Reusing an idle eye patch over rapidly changing mouth
        frames makes the whole eye area appear to wobble intermittently.
        """
        self.expression_eye_sources = {}
        self.expression_face_sources = {}
        self.expression_physics_sources = {}
        for expression, pose in self.physics_expression_poses.items():
            expression_source = self.expression_pixmaps.get(expression)
            if expression_source is None:
                continue
            offset_x, offset_y = self._expression_eye_offset(expression)
            eye_alpha = self._translated_pixmap(
                self.eye_sources[pose],
                offset_x,
                offset_y,
            )
            face_offset_x, face_offset_y = self._expression_face_offset(
                expression
            )
            face_alpha = self._translated_pixmap(
                self.face_sources[pose],
                face_offset_x,
                face_offset_y,
            )
            self.expression_eye_sources[expression] = self._masked_region(
                expression_source,
                eye_alpha,
            )
            self.expression_face_sources[expression] = self._masked_region(
                expression_source,
                face_alpha,
            )
            self.expression_physics_sources[expression] = {
                "ornament": self._masked_region(
                    expression_source,
                    self.physics_sources[pose],
                ),
                "hair_left": self._masked_region(
                    expression_source,
                    self.hair_sources[pose]["left"],
                ),
                "hair_right": self._masked_region(
                    expression_source,
                    self.hair_sources[pose]["right"],
                ),
                "sleeve_left": self._masked_region(
                    expression_source,
                    self.sleeve_sources[pose]["left"],
                ),
                "sleeve_right": self._masked_region(
                    expression_source,
                    self.sleeve_sources[pose]["right"],
                ),
            }

    @staticmethod
    def _masked_region(source: QPixmap, alpha_source: QPixmap) -> QPixmap:
        """Extract a matching local layer from the expression itself."""
        layer = QPixmap(source.size())
        layer.fill(Qt.transparent)
        painter = QPainter(layer)
        painter.drawPixmap(0, 0, source)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, alpha_source)
        painter.end()
        return layer

    def _render_base_expression(self) -> str:
        """Return the emotional base currently visible under transient layers."""
        if (
            self.state == "speaking"
            and self.speech_gesture_expression in self.expression_pixmaps
        ):
            return self.speech_gesture_expression
        if (
            self.state == "speaking"
            and self.speech_closed_expression in self.expression_pixmaps
        ):
            return self.speech_closed_expression
        return self.current_expression

    def _local_physics_source(
        self,
        part: str,
        fallback: QPixmap,
    ) -> QPixmap:
        return self.expression_physics_sources.get(
            self._render_base_expression(),
            {},
        ).get(part, fallback)

    def _blink_expression(self) -> str:
        if self.idle_pose == "lean":
            return "blink_lean"
        if self.idle_pose == "front":
            return "blink_front"
        return "blink"

    def _speaking_blink_expression(self) -> str:
        suffix = self._active_speech_pose_suffix()
        current = self.speech_current_expression
        blink_prefix = next(
            (
                blink
                for mouth, blink in SPEAKING_BLINK_PREFIXES
                if current.startswith(mouth)
            ),
            "blink",
        )
        return f"{blink_prefix}{suffix}"

    @staticmethod
    def _pose_suffix(pose: str) -> str:
        return "_lean" if pose == "lean" else "_front" if pose == "front" else ""

    def _blink_composite(
        self,
        base_pixmap: QPixmap,
        base_expression: str,
    ) -> QPixmap:
        # Emotional portraits are complete, identity-locked illustrations.
        # A neutral eye patch changes their eyelids, brows and face contour,
        # so they stay intact until a dedicated matching blink asset exists.
        if base_expression in EYES_CLOSED_EXPRESSIONS:
            return QPixmap(base_pixmap)
        is_expression_speech = (
            self.state == "speaking"
            and base_expression in EXPRESSION_SPEECH_EXPRESSIONS
        )
        if base_expression in EXPRESSION_POSES and not is_expression_speech:
            return QPixmap(base_pixmap)
        pose = self.physics_expression_poses.get(
            base_expression,
            getattr(self, "active_physics_pose", "front"),
        )
        suffix = self._pose_suffix(pose)
        offset_x, offset_y = self._expression_eye_offset(base_expression)
        dedicated_blink = EXPRESSION_BLINK_FRAMES.get(base_expression)
        if dedicated_blink is not None:
            blink_source = self.expression_pixmaps[dedicated_blink]
            eye_mask = self.blink_masks[pose]
            if offset_x or offset_y:
                eye_mask = self._translated_pixmap(
                    eye_mask,
                    offset_x,
                    offset_y,
                )
            blink_patch = self._masked_region(blink_source, eye_mask)
        else:
            blink_source = self.expression_pixmaps[f"blink{suffix}"]
            blink_patch = self._masked_eye_patch(blink_source, pose)
        if dedicated_blink is None and (offset_x or offset_y):
            blink_patch = self._translated_pixmap(
                blink_patch,
                offset_x,
                offset_y,
            )
        result = QPixmap(base_pixmap)
        painter = QPainter(result)
        painter.drawPixmap(
            0,
            0,
            blink_patch,
        )
        painter.end()
        return result

    def _masked_eye_patch(self, source: QPixmap, pose: str) -> QPixmap:
        return self._masked_region(source, self.blink_masks[pose])

    def _active_speech_pose_suffix(self) -> str:
        if self.state == "speaking":
            if self.speech_closed_expression.endswith("_lean"):
                return "_lean"
            if self.speech_closed_expression.endswith("_front"):
                return "_front"
            if self.speech_closed_expression == "idle":
                return ""
            return self.speech_pose_suffix
        return (
            "_lean"
            if self.idle_pose == "lean"
            else "_front"
            if self.idle_pose == "front"
            else ""
        )

    def _schedule_pose_change(self) -> None:
        delay = (
            random.randint(5_000, 9_000)
            if self.idle_pose == "front"
            else random.randint(16_000, 29_000)
        )
        self.pose_timer.start(delay)

    def _rotate_idle_pose(self) -> None:
        if self.state == "idle":
            if self.idle_pose == "cheek":
                self.idle_pose = random.choice(["lean", "front"])
            elif self.idle_pose == "lean" and random.random() < 0.55:
                self.idle_pose = "front"
            else:
                self.idle_pose = "cheek"
            self._set_expression(self._idle_expression())
        self._schedule_pose_change()

    def _schedule_blink(self) -> None:
        self.blink_timer.start(random.randint(2_800, 6_200))

    def _blink(self) -> None:
        if getattr(self, "pose_transition_active", False):
            self._schedule_blink()
            return
        self.blink_generation += 1
        generation = self.blink_generation
        render_base = self._render_base_expression()
        can_idle_blink = (
            self.state != "speaking"
            and render_base in self.physics_expression_poses
            and not self.idle_blinking
        )
        if can_idle_blink:
            base_expression = self.current_expression
            current = self.character.pixmap()
            if current is None or current.isNull():
                current = self.expression_pixmaps[base_expression]
            self.blink_restore_pixmap = QPixmap(current)
            self.idle_blinking = True
            self.eye_overlay.hide()
            self.character.setPixmap(
                self._blink_composite(current, render_base)
            )
            QTimer.singleShot(
                random.randint(95, 145),
                lambda: self._finish_blink(base_expression, generation),
            )
        elif self.state == "speaking" and not self.speech_blinking:
            current = self.speech_visual_pixmap
            if current.isNull():
                visible = self.character.pixmap()
                current = (
                    QPixmap(visible)
                    if visible is not None and not visible.isNull()
                    else QPixmap(
                        self.expression_pixmaps[
                            self.speech_closed_expression
                        ]
                    )
                )
            self.speech_blink_restore_pixmap = QPixmap(current)
            self.speech_blinking = True
            self.eye_overlay.hide()
            self._render_speech_pixmap(current)
            QTimer.singleShot(
                random.randint(95, 145),
                lambda: self._finish_speaking_blink(generation),
            )
        self._schedule_blink()

    def _finish_blink(
        self,
        base_expression: str,
        generation: int,
    ) -> None:
        if (
            generation != self.blink_generation
            or self.state == "speaking"
            or self.current_expression != base_expression
        ):
            self.idle_blinking = False
            return
        if not self.blink_restore_pixmap.isNull():
            self.character.setPixmap(self.blink_restore_pixmap)
        self.idle_blinking = False
        self._render_attention_layers(force=True)
        self._attention_tick()
        if random.random() < 0.16:
            QTimer.singleShot(170, self._blink)

    def _finish_speaking_blink(
        self,
        generation: int,
    ) -> None:
        if (
            self.state != "speaking"
            or generation != self.blink_generation
        ):
            self.speech_blinking = False
            return
        self.speech_blinking = False
        if not self.speech_visual_pixmap.isNull():
            self.character.setPixmap(self.speech_visual_pixmap)
        self._render_attention_layers(force=True)
        self._attention_tick()

    def _schedule_attention_glance(self) -> None:
        self.gaze_timer.start(random.randint(38_000, 78_000))

    def _schedule_ambient_expression(self) -> None:
        self.ambient_timer.start(random.randint(42_000, 88_000))

    def _show_ambient_expression(self) -> None:
        # Emotional expressions require conversational or event context.
        # Context-free idle variation is limited to pose, breath, gaze and
        # blinking so an unrelated smile, worry or scold can never appear.
        self._schedule_ambient_expression()

    def _start_attention_glance(self) -> None:
        if self.conservative_idle:
            self._schedule_attention_glance()
            return
        if self.state == "idle" and self.idle_pose == "cheek":
            self.set_state("glance", source="ambient")
            QTimer.singleShot(random.randint(2_600, 4_100), self._end_attention_glance)
        self._schedule_attention_glance()

    def _end_attention_glance(self) -> None:
        if self.state == "glance":
            self.set_state("idle")

    def _character_clicked(self) -> None:
        if self.state == "glance":
            self._show_caught_reaction()
            QTimer.singleShot(1_700, self.open_dashboard)
            return
        self.open_dashboard()

    def _show_caught_reaction(self) -> None:
        self.set_state("caught", source="user_direct")
        self._show_bubble(
            "主上莫要自作多情。妾只是在確認你是否又打算逞強，"
            "好替你把下一步算妥罷了。"
        )
        self._schedule_return_to_idle(2_800, "caught")
        QTimer.singleShot(3_400, self.bubble.hide)

    def _set_expression(self, expression: str, fade: bool = True) -> None:
        if expression not in self.expression_pixmaps:
            expression = "idle"
        self._cancel_expression_transition()
        if self._active_pose_transition_owns(expression):
            return
        if self._needs_pose_transition(expression, fade):
            target_pose = self.physics_expression_poses[expression]
            self._start_pose_transition(expression, target_pose)
            return
        self._prepare_expression_layers(expression, fade)
        if expression == self.current_expression:
            return
        if not fade:
            self.character.setPixmap(self.expression_pixmaps[expression])
            self.current_expression = expression
            return
        self._start_expression_crossfade(expression)

    def _active_pose_transition_owns(self, expression: str) -> bool:
        """Keep one in-flight pose transition or cancel it before replacement."""
        if not getattr(self, "pose_transition_active", False):
            return False
        # Timers for idle motion, blinking, and speech can all request the
        # same frame while a large-pose fade is already in flight. Restarting
        # that fade creates a visible flash although the target is unchanged.
        if expression == getattr(self, "pose_transition_expression", None):
            return True
        self._cancel_pose_transition()
        return False

    def _needs_pose_transition(self, expression: str, fade: bool) -> bool:
        current_pose = self.physics_expression_poses.get(
            self.current_expression
        )
        target_pose = self.physics_expression_poses.get(expression)
        return (
            fade
            and current_pose is not None
            and target_pose is not None
            and current_pose != target_pose
        )

    def _prepare_expression_layers(self, expression: str, fade: bool) -> None:
        if (
            hasattr(self, "face_overlay")
            and expression != self._idle_expression()
        ):
            self.face_overlay.hide()
            self.eye_overlay.hide()
        current_has_physics = (
            self.current_expression in self.physics_expression_poses
        )
        target_has_physics = expression in self.physics_expression_poses
        if not target_has_physics:
            # Hide local overlays before cross-fading to a special expression;
            # otherwise an idle sleeve/face can briefly float over that frame.
            self._update_physics_pose(expression)
        elif not fade or current_has_physics:
            self._update_physics_pose(expression)

    def _start_expression_crossfade(self, expression: str) -> None:
        pixmap = self.expression_pixmaps[expression]
        self.expression_overlay.setPixmap(pixmap)
        self.expression_overlay.show()
        self.expression_overlay.raise_()
        if not self.physics_overlay.isHidden():
            self.sleeve_left_overlay.raise_()
            self.sleeve_right_overlay.raise_()
            self.hair_left_overlay.raise_()
            self.hair_right_overlay.raise_()
            self.physics_overlay.raise_()
        self.bubble.raise_()
        self.overlay_opacity.setOpacity(0.0)
        self.character_opacity.setOpacity(1.0)
        fade_in = QPropertyAnimation(self.overlay_opacity, b"opacity", self)
        fade_out = QPropertyAnimation(self.character_opacity, b"opacity", self)
        for animation, start, end in (
            (fade_in, 0.0, 1.0),
            (fade_out, 1.0, 0.0),
        ):
            animation.setDuration(180)
            animation.setStartValue(start)
            animation.setEndValue(end)
            animation.setEasingCurve(QEasingCurve.InOutSine)
        group = QParallelAnimationGroup(self)
        group.addAnimation(fade_in)
        group.addAnimation(fade_out)
        group.finished.connect(lambda: self._finish_expression_change(expression))
        group.start()
        self.expression_animation = group

    def _cancel_expression_transition(self) -> None:
        animation = getattr(self, "expression_animation", None)
        if animation is not None and animation.state():
            animation.stop()
        if hasattr(self, "expression_overlay"):
            self.expression_overlay.hide()
        if hasattr(self, "character_opacity"):
            self.character_opacity.setOpacity(1.0)

    def _cancel_pose_transition(self) -> None:
        # Invalidate callbacks that may already be queued by Qt.  A boolean is
        # insufficient because an old animation can finish after a new
        # transition has set the boolean back to True.
        self.pose_transition_generation = (
            getattr(self, "pose_transition_generation", 0) + 1
        )
        for animation_name in (
            "pose_transition_out",
            "pose_transition_in",
        ):
            animation = getattr(self, animation_name, None)
            if animation is not None:
                animation.stop()
            setattr(self, animation_name, None)
        self.pose_transition_active = False
        self.pose_transition_expression = None
        self.pose_transition_target_pose = None
        self.character_opacity.setOpacity(1.0)

    def _start_pose_transition(
        self,
        expression: str,
        target_pose: str,
    ) -> None:
        """Switch large pose sprites without ever drawing both simultaneously."""
        self.pose_transition_generation = (
            getattr(self, "pose_transition_generation", 0) + 1
        )
        generation = self.pose_transition_generation
        self.pose_transition_active = True
        self.pose_transition_expression = expression
        self.pose_transition_target_pose = target_pose
        self.expression_overlay.hide()
        self.face_overlay.hide()
        self.eye_overlay.hide()
        for overlay in (
            self.sleeve_left_overlay,
            self.sleeve_right_overlay,
            self.hair_left_overlay,
            self.hair_right_overlay,
            self.physics_overlay,
        ):
            overlay.hide()
        fade_out = QPropertyAnimation(
            self.character_opacity,
            b"opacity",
            self,
        )
        fade_out.setDuration(75)
        fade_out.setStartValue(self.character_opacity.opacity())
        # The sprite must be fully transparent before its pixmap is replaced.
        # Swapping at partial opacity leaves both poses in visual persistence
        # and can also expose a stale QGraphicsOpacityEffect cache for a frame.
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InOutSine)
        fade_out.finished.connect(
            lambda: self._pose_transition_midpoint(
                expression,
                target_pose,
                generation,
            )
        )
        self.pose_transition_out = fade_out
        fade_out.start()

    def _pose_transition_midpoint(
        self,
        expression: str,
        target_pose: str,
        generation: int,
    ) -> None:
        if (
            not getattr(self, "pose_transition_active", False)
            or generation
            != getattr(self, "pose_transition_generation", -1)
            or expression
            != getattr(self, "pose_transition_expression", None)
            or target_pose
            != getattr(self, "pose_transition_target_pose", None)
        ):
            return
        self.character_opacity.setOpacity(0.0)
        self.character.setPixmap(self.expression_pixmaps[expression])
        self.current_expression = expression
        self.active_physics_pose = target_pose
        self._render_sleeve_layers(force=True)
        self._render_hair_layers(force=True)
        self._render_physics_layer(force=True)
        self.character.update()
        fade_in = QPropertyAnimation(
            self.character_opacity,
            b"opacity",
            self,
        )
        fade_in.setDuration(105)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.InOutSine)
        fade_in.finished.connect(
            lambda: self._finish_pose_transition(expression, generation)
        )
        self.pose_transition_in = fade_in
        fade_in.start()

    def _finish_pose_transition(
        self,
        expression: str,
        generation: int,
    ) -> None:
        if (
            not getattr(self, "pose_transition_active", False)
            or generation
            != getattr(self, "pose_transition_generation", -1)
            or expression
            != getattr(self, "pose_transition_expression", None)
        ):
            return
        self.pose_transition_active = False
        self.pose_transition_expression = None
        self.pose_transition_target_pose = None
        self.pose_transition_out = None
        self.pose_transition_in = None
        self.character_opacity.setOpacity(1.0)
        self._update_physics_pose(expression)
        self._render_attention_layers(force=True)
        self._attention_tick()

    def _finish_expression_change(self, expression: str) -> None:
        self.character.setPixmap(self.expression_pixmaps[expression])
        self.character_opacity.setOpacity(1.0)
        self.expression_overlay.hide()
        self.current_expression = expression
        self._update_physics_pose(expression)

    def _ensure_idle_mouth_closed(self) -> None:
        if self.state != "idle":
            return
        speaking_frame = self.current_expression.startswith(
            (
                "speaking",
                "mouth_",
                "viseme_",
                "blink_mid",
                "blink_open",
                "blink_wide",
                "blink_round",
                "blink_i",
                "blink_o",
            )
        )
        if not self.mouth_open and not speaking_frame:
            return
        self.mouth_timer.stop()
        self.speech_blinking = False
        self.audio_driven_mouth = False
        self.viseme_dynamics.reset()
        self.mouth_frame_index = 0
        self.mouth_open = False
        self.speech_current_expression = self._idle_expression()
        self._set_expression(self._idle_expression(), fade=False)

    def _mouth_tick(self) -> None:
        if (
            self.state != "speaking"
            or self.audio_driven_mouth
        ):
            return
        if self.mouth_frame_index == 0:
            self.mouth_frame_index = 1
        elif self.mouth_frame_index == 1:
            self.mouth_frame_index = random.choices(
                (0, 2), weights=(0.28, 0.72), k=1
            )[0]
        else:
            self.mouth_frame_index = 1
        self.mouth_open = self.mouth_frame_index > 0
        expression = (
            self.speech_closed_expression,
            self.speech_mid_expression,
            self.speech_open_expression,
        )[self.mouth_frame_index]
        self.speech_current_expression = expression
        aperture = (0.0, 0.48, 0.9)[self.mouth_frame_index]
        self._show_speech_frame(expression, aperture)
        delay_range = (
            (125, 235)
            if self.mouth_frame_index == 0
            else (75, 145)
            if self.mouth_frame_index == 1
            else (85, 165)
        )
        self.mouth_timer.start(random.randint(*delay_range))

    def _start_mouth_animation(self, audio_driven: bool = False) -> None:
        self.blink_generation += 1
        # Speech owns the visible character frame from its first sample.
        # A pending expression/pose cross-fade can otherwise leave the prior
        # pose above the new closed-mouth frame for one or two audio cues.
        self._cancel_expression_transition()
        self._cancel_pose_transition()
        self.expression_overlay.hide()
        self.mouth_timer.stop()
        self.mouth_visual_timer.stop()
        self.mouth_transition_from = QPixmap()
        self.mouth_transition_to = QPixmap()
        self.mouth_transition_started = 0.0
        self.speech_blinking = False
        self.audio_driven_mouth = audio_driven
        self.mouth_closing = False
        self.viseme_dynamics.reset()
        self.mouth_aperture_target = 0.0
        self.head_motion_y = 0.0
        self.speech_motion_target_y = 0.0
        self.mouth_frame_index = 0
        self.mouth_open = False
        self.speech_current_expression = self.speech_closed_expression
        self._set_expression(self.speech_closed_expression, fade=False)
        closed_frame = self._mouth_aperture_pixmap(
            self.speech_closed_expression,
            0.0,
        )
        self._render_speech_pixmap(closed_frame)
        if self.speech_gesture_expression is not None:
            self._update_physics_pose(
                self.speech_gesture_expression
            )
        if not audio_driven:
            self.mouth_timer.start(random.randint(70, 120))

    def _show_speech_frame(
        self,
        expression: str,
        aperture: float,
    ) -> None:
        """Render speech over its emotional base without a full-sprite swap."""
        if expression not in self.expression_pixmaps:
            expression = self.speech_mid_expression
        self._render_speech_pixmap(
            self._mouth_aperture_pixmap(
                expression,
                aperture,
            )
        )
        self.current_expression = expression
        self._update_physics_pose(expression)
        self._render_attention_layers(force=True)

    def _render_speech_pixmap(self, clean_pixmap: QPixmap) -> None:
        """Display the latest mouth frame with blink as an independent layer.

        Mouth animation keeps advancing while the eyelids are closed.  The
        clean frame is retained separately so ending a blink never restores a
        stale viseme from before the blink began.
        """
        self.speech_visual_pixmap = QPixmap(clean_pixmap)
        visible = (
            self._blink_composite(
                clean_pixmap,
                self.speech_closed_expression,
            )
            if self.speech_blinking
            else clean_pixmap
        )
        self.character.setPixmap(visible)

    def _stop_mouth_animation(self) -> None:
        self.blink_generation += 1
        self.mouth_timer.stop()
        self.mouth_visual_timer.stop()
        self.speech_blinking = False
        self.audio_driven_mouth = False
        self.mouth_closing = False
        self.viseme_dynamics.reset()
        self.mouth_aperture_target = 0.0
        self.head_motion_y = 0.0
        self.speech_motion_target_y = 0.0
        self.mouth_frame_index = 0
        self.mouth_open = False
        self.speech_current_expression = self.speech_closed_expression
        closed_frame = self._mouth_aperture_pixmap(
            self.speech_closed_expression,
            0.0,
        )
        self._set_expression(self.speech_closed_expression, fade=False)
        self._render_speech_pixmap(closed_frame)
        self.current_expression = self.speech_closed_expression
        self._compose_character_position()

    def _audio_viseme_cue(self, level: float, vowel: str) -> None:
        if (
            self.state != "speaking"
            or not self.audio_driven_mouth
            or self.mouth_closing
        ):
            return
        # A live viseme owns the full photographed face. Remove any gaze
        # overlay left by the preceding idle frame before drawing the mouth.
        self.eye_overlay.hide()
        frame: VisemeFrame = self.viseme_dynamics.advance(level, vowel)
        expression = self._viseme_expression(frame.selected)
        self.mouth_frame_index = frame.frame_index
        self.mouth_open = frame.mouth_open
        self.speech_current_expression = expression
        if (
            frame.selected != frame.previous
            or self.mouth_transition_to.isNull()
        ):
            self._queue_audio_mouth_transition(
                expression,
                frame.jaw_aperture,
            )
        target_motion = min(
            4.0,
            self.viseme_dynamics.smoothed_level * 3.0 + frame.jaw_weight,
        )
        self.head_motion_y = self.head_motion_y * 0.62 + target_motion * 0.38
        self.speech_motion_target_y = -self.head_motion_y
        self._motion_tick()

    def _viseme_expression(self, viseme: str) -> str:
        if viseme == "CLOSED":
            expression = self.speech_closed_expression
        elif viseme == "CONSONANT":
            expression = self.speech_mid_expression
        elif self.speech_gesture_expression is not None:
            expression = EXPRESSION_VISEME_FRAMES[
                self.speech_gesture_expression
            ].get(viseme, self.speech_mid_expression)
        else:
            stem = NEUTRAL_VISEME_ASSET_STEMS.get(viseme)
            expression = (
                self.speech_mid_expression
                if stem is None
                else f"{stem}{self._active_speech_pose_suffix()}"
            )
        return expression

    def _mouth_aperture_pixmap(
        self,
        expression: str,
        aperture: float,
    ) -> QPixmap:
        closed = self.expression_pixmaps[self.speech_closed_expression]
        if expression == self.speech_closed_expression or aperture <= 0.01:
            result = QPixmap(closed)
        else:
            suffix = self._active_speech_pose_suffix()
            result = QPixmap(closed)
            painter = QPainter(result)
            # Every viseme is already a purpose-built mouth shape. Applying
            # acoustic aperture a second time would create a double mouth.
            painter.setOpacity(max(0.0, min(1.0, aperture / 0.18)))
            patch = self._speech_mouth_patch(
                self.expression_pixmaps[expression],
                suffix,
            )
            painter.drawPixmap(0, 0, patch)
            painter.end()
        return result

    def _speech_mouth_patch(
        self,
        source: QPixmap,
        suffix: str,
        source_already_aligned: bool = False,
    ) -> QPixmap:
        """Use one mask path for target frames and in-between transitions."""
        if self.speech_gesture_expression is not None:
            return self._masked_region(
                source,
                self.gesture_mouth_masks[
                    self.speech_gesture_expression
                ],
            )
        if (
            suffix == ""
            and self.speech_closed_expression
            == CHEEK_SPEECH_CLOSED_EXPRESSION
        ):
            return self._masked_region(
                source,
                self.viseme_mouth_masks[""],
            )
        return self._masked_mouth_patch(
            source,
            suffix,
            self.speech_closed_expression,
            source_already_aligned=source_already_aligned,
        )

    def _queue_audio_mouth_transition(
        self,
        expression: str,
        aperture: float | None = None,
    ) -> None:
        if expression not in self.expression_pixmaps:
            expression = self.speech_mid_expression
        previous_aperture = getattr(
            self,
            "mouth_aperture_target",
            0.0,
        )
        # If a new phoneme arrives mid-transition, continue from the latest
        # clean rendered frame. Jumping from the previous target would skip
        # several visual milliseconds and make the lips appear to teleport.
        normalized_current = (
            QPixmap(self.speech_visual_pixmap)
            if (
                self.mouth_visual_timer.isActive()
                and not self.speech_visual_pixmap.isNull()
            )
            else self._mouth_aperture_pixmap(
                self.current_expression,
                previous_aperture,
            )
        )
        self.mouth_transition_from = normalized_current
        next_aperture = (
            0.0
            if expression == self.speech_closed_expression
            else 1.0
            if aperture is None
            else max(0.0, min(1.0, float(aperture)))
        )
        self.mouth_transition_to = self._mouth_aperture_pixmap(
            expression,
            next_aperture,
        )
        opening = previous_aperture <= 0.05 < next_aperture
        closing = next_aperture <= 0.05 < previous_aperture
        self.mouth_transition_duration = (
            VISEME_OPEN_TRANSITION_SECONDS
            if opening
            else VISEME_CLOSE_TRANSITION_SECONDS
            if closing
            else VISEME_CHANGE_TRANSITION_SECONDS
        )
        self.mouth_aperture_target = next_aperture
        self.mouth_transition_started = time.perf_counter()
        self._update_physics_pose(expression)
        self.current_expression = expression
        self.expression_overlay.hide()
        if not self.mouth_visual_timer.isActive():
            self.mouth_visual_timer.start()

    def _render_audio_mouth_transition(self) -> None:
        if (
            self.state != "speaking"
            or not self.audio_driven_mouth
            or self.mouth_transition_from.isNull()
            or self.mouth_transition_to.isNull()
        ):
            self.mouth_visual_timer.stop()
            return
        elapsed = time.perf_counter() - self.mouth_transition_started
        progress = max(
            0.0,
            min(1.0, elapsed / self.mouth_transition_duration),
        )
        eased = 0.5 - 0.5 * math.cos(progress * math.pi)
        suffix = self._active_speech_pose_suffix()
        blended = QPixmap(self.mouth_transition_from)
        painter = QPainter(blended)
        painter.setOpacity(eased)
        painter.drawPixmap(
            0,
            0,
            self._speech_mouth_patch(
                self.mouth_transition_to,
                suffix,
                source_already_aligned=True,
            ),
        )
        painter.end()
        self._render_speech_pixmap(blended)
        if progress >= 1.0:
            self._render_speech_pixmap(self.mouth_transition_to)
            self.mouth_visual_timer.stop()

    def set_state(
        self,
        state: str,
        *,
        source: str = "conversation",
        intensity: float = 0.5,
        force: bool = False,
    ) -> bool:
        decision = self.expression_arbiter.request(
            state,
            source=source,
            intensity=intensity,
            force=force or state in {"idle", "speaking"},
        )
        if not decision.accepted:
            return False
        previous_animation = getattr(self, "state_animation", None)
        if previous_animation is not None and previous_animation.state():
            previous_animation.stop()
        self.gesture_motion_x = 0.0
        self.gesture_motion_y = 0.0
        self._compose_character_position()
        self.expression_generation += 1
        self.state = state
        if state == "idle":
            expression = self._idle_expression()
        elif state == "speaking":
            expression = self._speaking_expression()
        else:
            expression = state
        self._set_expression(expression)
        expressive_states = {
            "happy",
            "reminder",
            "worried",
            "thinking_front",
            "caught",
            "gentle_smile_front",
            "worried_front",
            "shy_front",
            "mock_scold",
            "surprised_front",
            "relieved_front",
            "tired_front",
            "proud_front",
            *NEW_EXPRESSION_ASSETS,
        }
        if state in expressive_states:
            animation = QVariantAnimation(self)
            animation.setDuration(
                720
                if state in {"mock_scold", "mock_hit_front"}
                else 620
                if state
                in {
                    "thinking_front",
                    "shy_front",
                    "shy_cute_front",
                    "tired_front",
                    "exasperated_front",
                }
                else 500
            )
            animation.setStartValue(QPoint(0, 0))
            animation.setKeyValueAt(
                0.35,
                QPoint(
                    -5
                    if state in {"caught", "shy_front", "shy_cute_front"}
                    else 0,
                    -7
                    if state == "happy"
                    else -9
                    if state in {"mock_scold", "mock_hit_front"}
                    else -3
                    if state
                    in {
                        "reminder",
                        "thinking_front",
                        "surprised_front",
                        "proud_front",
                        "eureka_front",
                    }
                    else 0,
                ),
            )
            animation.setKeyValueAt(
                0.62,
                QPoint(
                    5
                    if state in {"worried", "worried_front", "caught"}
                    else 2
                    if state in {"mock_scold", "mock_hit_front"}
                    else 0,
                    -5
                    if state == "mock_scold"
                    else -2
                    if state in {"thinking_front", "proud_front"}
                    else 0,
                ),
            )
            animation.setEndValue(QPoint(0, 0))
            animation.valueChanged.connect(
                self._apply_gesture_motion
            )
            animation.finished.connect(self._finish_gesture_motion)
            animation.setEasingCurve(QEasingCurve.OutBack)
            animation.start()
            self.state_animation = animation
        return True

    def _start_ai_wait_expression(
        self,
        generation: int,
        expression: str,
        intensity: float,
    ) -> None:
        """Apply a low-priority wait pose only over a neutral visual state."""
        if expression not in {"attentive_front", "thinking_front"}:
            return
        if (
            self.speech_playing
            or self.realtime_mouth_active
            or self.realtime.running
            or self.state == "speaking"
        ):
            return
        if self.state not in {
            "idle",
            "glance",
            "attentive_front",
            "thinking_front",
        }:
            return
        if self.set_state(
            expression,
            source="ai_wait",
            intensity=intensity,
        ):
            self.active_ai_wait_generation = generation
            self.active_ai_wait_expression = expression

    def _finish_ai_wait_expression(self, generation: int) -> None:
        """Clear only the wait pose owned by this exact request."""
        if generation != self.active_ai_wait_generation:
            return
        expression = self.active_ai_wait_expression
        self.active_ai_wait_generation = 0
        self.active_ai_wait_expression = ""
        if (
            self.state == expression
            and not self.speech_playing
            and not self.realtime_mouth_active
        ):
            self.set_state("idle", source="ai_wait", force=True)

    def _apply_gesture_motion(self, value: QPoint) -> None:
        self.gesture_motion_x = float(value.x())
        self.gesture_motion_y = float(value.y())
        self._compose_character_position()

    def _finish_gesture_motion(self) -> None:
        self.gesture_motion_x = 0.0
        self.gesture_motion_y = 0.0
        self._compose_character_position()

    def speak(self, text: str, state: str = "speaking") -> None:
        text = personalize_text(self.db, text)
        if not text.strip():
            return
        intensity = 0.5
        source = "reminder" if state == "reminder" else "conversation"
        pending = self.dashboard.consume_expression_metadata(state)
        if pending is not None:
            _, intensity, source = pending
        self.speech_queue.append(
            QueuedSpeech(text, state, intensity, source)
        )
        self._start_next_speech()

    def _start_next_speech(self) -> None:
        if self.speech_playing or not self.speech_queue:
            return
        self.speech_finish_timer.stop()
        queued = self.speech_queue.popleft()
        self._begin_speech_presentation(queued)
        tts_enabled = bool(self.db.setting("tts_enabled", True))
        self._start_mouth_animation(audio_driven=tts_enabled)
        self.show()
        self.raise_()
        if tts_enabled:
            self._start_speech_provider(queued.text)
            return
        QTimer.singleShot(
            max(1200, min(5000, len(queued.text) * 80)),
            self._speech_audio_finished,
        )

    def _begin_speech_presentation(self, queued: QueuedSpeech) -> None:
        self.speech_playing = True
        self.active_speech_text = queued.text
        self.active_speech_engine = ""
        self.cloud_fallback_active = False
        self._show_bubble(queued.text)
        state = self._accepted_speech_state(queued)
        self.after_speech_state = state if state != "speaking" else "idle"
        self.after_speech_intensity = queued.intensity
        emotional_base = (
            state
            if state in EXPRESSION_POSES
            and state in self.expression_pixmaps
            else self._idle_expression()
        )
        self._configure_speech_frames(emotional_base)
        self.expression_generation += 1
        self.state = "speaking"
        self.expression_arbiter.request(
            "speaking",
            source="conversation",
            force=True,
        )

    def _accepted_speech_state(self, queued: QueuedSpeech) -> str:
        if queued.requested_state not in EXPRESSION_POSES:
            return queued.requested_state
        decision = self.expression_arbiter.request(
            queued.requested_state,
            source=queued.source,
            intensity=queued.intensity,
        )
        return queued.requested_state if decision.accepted else "speaking"

    def _configure_speech_frames(self, emotional_base: str) -> None:
        speech_pose = self.physics_expression_poses.get(
            emotional_base,
            self.idle_pose,
        )
        self.speech_pose_suffix = self._pose_suffix(speech_pose)
        self.speech_gesture_expression = (
            emotional_base
            if emotional_base in EXPRESSION_SPEECH_EXPRESSIONS
            else None
        )
        if self.speech_gesture_expression is not None:
            frames = EXPRESSION_SPEECH_FRAMES[
                self.speech_gesture_expression
            ]
            self.speech_closed_expression = self.speech_gesture_expression
            self.speech_mid_expression = frames["mid"]
            self.speech_open_expression = frames["open"]
        else:
            self.speech_closed_expression = (
                CHEEK_SPEECH_CLOSED_EXPRESSION
                if self.speech_pose_suffix == ""
                else f"idle{self.speech_pose_suffix}"
            )
            self.speech_mid_expression = (
                f"mouth_mid{self.speech_pose_suffix}"
            )
            self.speech_open_expression = (
                f"speaking{self.speech_pose_suffix}"
            )

    def _speech_credentials(self) -> SpeechCredentials:
        azure_api_key = (
            self.azure_secret_store.load()
            if self.azure_secret_store is not None
            else ""
        )
        return SpeechCredentials(
            openai_api_key=self.secret_store.load(),
            azure_api_key=azure_api_key,
            azure_region=str(
                self.db.setting("azure_speech_region", "")
            ).strip(),
        )

    def _configured_speech_providers(
        self,
        credentials: SpeechCredentials,
    ) -> tuple[str, ...]:
        availability = (
            (
                VOICE_ENGINE_SYSTEM,
                self.platform_services.capabilities.system_local_speech,
            ),
            (VOICE_ENGINE_OPENAI, bool(credentials.openai_api_key)),
            (
                VOICE_ENGINE_AZURE,
                bool(credentials.azure_api_key and credentials.azure_region),
            ),
        )
        return tuple(
            provider_id
            for provider_id, configured in availability
            if configured
        )

    def _start_speech_provider(self, text: str) -> None:
        credentials = self._speech_credentials()
        selected_provider_id = normalize_speech_provider_id(
            self.db.setting("voice_engine", VOICE_ENGINE_SYSTEM)
        )
        provider_id = self.speech_providers.output_provider_id(
            selected_provider_id,
            realtime_running=bool(self.realtime.running),
            cloud_available=bool(credentials.openai_api_key),
            configured_provider_ids=self._configured_speech_providers(
                credentials
            ),
        )
        self._report_azure_fallback(selected_provider_id, provider_id)
        self.active_speech_engine = provider_id
        voice, api_key = self._speech_voice_and_key(provider_id, credentials)
        request = SpeechRequest(
            text=text,
            voice=voice,
            rate=int(self.db.setting("voice_rate", -1)),
            api_key=api_key,
            instructions=str(
                self.db.setting(
                    "voice_instructions",
                    VOICE_GENERATION_PROMPT,
                )
            ),
            options={"region": credentials.azure_region},
        )
        self.speech_providers.provider(provider_id).speak(request)

    def _report_azure_fallback(
        self,
        selected_provider_id: str,
        provider_id: str,
    ) -> None:
        if (
            selected_provider_id != VOICE_ENGINE_AZURE
            or provider_id == VOICE_ENGINE_AZURE
        ):
            return
        fallback_available = (
            self.speech_providers.fallback_provider_id(VOICE_ENGINE_AZURE)
            is not None
        )
        message_key = (
            "azure_fallback_missing_settings"
            if fallback_available
            else "azure_missing_no_local_fallback"
        )
        default_message = (
            "Azure Speech 尚未完成設定；已直接使用 Windows "
            "女性語音，未送出雲端請求。"
            if fallback_available
            else "Azure Speech 尚未完成設定，且此平台沒有已驗證的"
            "本機語音；本次不會播放，也不會送出雲端請求。"
        )
        self.dashboard.set_api_status(
            ui_text(
                str(self.db.setting("ui_language", "zh-TW")),
                message_key,
                default_message,
            )
        )

    def _speech_voice_and_key(
        self,
        provider_id: str,
        credentials: SpeechCredentials,
    ) -> tuple[str, str]:
        if provider_id == VOICE_ENGINE_SYSTEM:
            voice = str(self.db.setting("windows_voice", ""))
            api_key = ""
        elif provider_id == VOICE_ENGINE_AZURE:
            voice = str(self.db.setting("azure_speech_voice", ""))
            api_key = credentials.azure_api_key
        else:
            voice = str(
                self.db.setting(
                    "tts_voice",
                    self.db.setting("cloud_voice", "coral"),
                )
            )
            api_key = credentials.openai_api_key
        return voice, api_key

    def preview_voice(self) -> None:
        language = profile_setting(self.db, "ui_language")
        if is_english(language):
            self.speak(
                f"{profile_setting(self.db, 'user_title')}, I am here. "
                "There is no need to look so surprised.",
                "happy",
            )
            return
        if is_simplified_chinese(language):
            self.speak(
                f"{profile_setting(self.db, 'user_title')}，妾在。"
                "今日的安排，交给妾与你一同理清。",
                "happy",
            )
            return
        if is_japanese(language):
            self.speak(
                f"{profile_setting(self.db, 'user_title')}、妾はここにおります。"
                "今日の予定も、ともに整えてまいりましょう。",
                "happy",
            )
            return
        self.speak(
            f"{profile_setting(self.db, 'user_title')}，妾在。"
            "今日的安排，交給妾與你一同理清。",
            "happy",
        )

    def _apply_voice_volume(
        self,
        volume_percent: int,
        muted: bool,
    ) -> None:
        engines = [self.tts, self.cloud_tts, self.realtime]
        if self.azure_tts is not None:
            engines.append(self.azure_tts)
        for engine in engines:
            engine.set_volume(volume_percent, muted)

    def _recent_realtime_context(
        self,
        transcription_prompt: str,
    ) -> str:
        safe_prompt = (
            RealtimeVoiceClient
            ._sanitize_realtime_transcription_prompt(
                transcription_prompt
            )
        )
        labels = {
            "user": profile_setting(self.db, "user_title"),
            "assistant": profile_setting(self.db, "assistant_name"),
        }
        lines = []
        for row in self.db.recent_chat(16):
            role = str(row["role"])
            content = str(row["content"]).strip()
            if not content or role not in labels:
                continue
            if (
                role == "user"
                and RealtimeVoiceClient
                .resembles_transcription_prompt(
                    content,
                    transcription_prompt,
                    safe_prompt,
                )
            ):
                continue
            normalized = normalize_for_language(
                content,
                profile_setting(self.db, "ui_language"),
            )
            lines.append(f"{labels[role]}：{normalized}")
        return "\n".join(lines)[-5000:]

    def toggle_realtime(self, enabled: bool) -> None:
        if not enabled:
            self.realtime.stop()
            self.dashboard.set_realtime_status("未連線", False)
            return
        self.dashboard.cancel_ai_wait_expression()
        self.dashboard.save_voice_settings(silent=True)
        voice_prompt = str(
            self.db.setting(
                "voice_instructions",
                VOICE_GENERATION_PROMPT,
            )
        ).strip() or VOICE_GENERATION_PROMPT
        transcription_prompt = str(
            self.db.setting(
                "transcription_prompt",
                SpeechListener.TRANSCRIPTION_PROMPT,
            )
        )
        self.realtime.start(
            RealtimeVoiceRequest(
                api_key=self.secret_store.load(),
                instructions=(
                    persona_for_profile(self.db)
                    + "\n\n## 語音生成指示\n"
                    + voice_prompt
                    + f"\n目前模式：{self.dashboard.mode}模式。"
                    + "\n助理名稱："
                    + profile_setting(self.db, "assistant_name")
                    + "。稱呼使用者為："
                    + profile_setting(self.db, "user_title")
                    + "。回覆語言／地區："
                    + profile_setting(self.db, "ui_language")
                    + "。"
                    + response_language_instruction(
                        profile_setting(self.db, "ui_language")
                    )
                ),
                memory_context=self.db.memory_context(),
                recent_context=self._recent_realtime_context(
                    transcription_prompt
                ),
                echo_guard=bool(
                    self.db.setting("realtime_echo_guard", True)
                ),
                session=RealtimeSessionConfig(
                    model=str(
                        self.db.setting(
                            "realtime_model",
                            "gpt-realtime-2.1-mini",
                        )
                    ),
                    voice=str(
                        self.db.setting("realtime_voice", "coral")
                    ),
                    transcription_model=str(
                        self.db.setting(
                            "realtime_transcription_model",
                            "gpt-4o-mini-transcribe",
                        )
                    ),
                    transcription_language=str(
                        self.db.setting(
                            "transcription_language",
                            "zh",
                        )
                    ),
                    transcription_prompt=transcription_prompt,
                    noise_reduction=str(
                        self.db.setting(
                            "realtime_noise_reduction",
                            "near_field",
                        )
                    ),
                    turn_detection=str(
                        self.db.setting(
                            "realtime_turn_detection",
                            "server_vad",
                        )
                    ),
                    external_transcription=bool(
                        self.db.setting(
                            "realtime_hybrid_transcription",
                            True,
                        )
                    ),
                ),
            ),
        )

    def _realtime_status(self, status: str) -> None:
        active = self.realtime.running and status != "未連線"
        self.dashboard.set_realtime_status(status, active)

    def _realtime_user_text(self, text: str) -> None:
        text = normalize_for_language(
            text,
            profile_setting(self.db, "ui_language"),
        )
        wake_word = profile_setting(self.db, "wake_word")
        clean = text.replace(wake_word, "", 1).strip() or text
        self.db.log_chat("user", clean)
        self.dashboard.append_chat(
            profile_setting(self.db, "user_title"), clean
        )
        self.dashboard.capture_explicit_memory(clean)
        self._handle_realtime_local_command(clean)

    def _handle_realtime_local_command(self, text: str) -> None:
        if is_start_work_command(text):
            self.db.start_work()
            self.dashboard.refresh_work_time()
        elif is_stop_work_command(text):
            self.db.stop_work()
            self.dashboard.refresh_work_time()
        elif "幫我記一下" in text:
            content = text.split("幫我記一下", 1)[1].lstrip("：:，, ").strip()
            if content:
                if any(word in content for word in ("靈感", "點子", "構想")):
                    self.db.add_idea(content)
                    self.dashboard.refresh_ideas()
                else:
                    self.db.add_todo(content, "其他")
                    self.dashboard.refresh_todos()
        elif "開啟工作室資料夾" in text:
            self.dashboard.open_work_folder()
        elif "開啟" in text:
            for platform in (
                row["platform"] for row in self.db.platform_rows()
            ):
                if platform.lower() in text.lower():
                    self.dashboard.open_platform(platform)
                    break

    def _realtime_assistant_text(self, text: str) -> None:
        tagged = parse_internal_emotion(text)
        text = normalize_for_language(
            tagged.text,
            profile_setting(self.db, "ui_language"),
        )
        if not text:
            return
        self.db.log_chat("assistant", text)
        self.dashboard.append_chat(
            profile_setting(self.db, "assistant_name"), text
        )
        reply_expression = (
            tagged.expression
            if tagged.valid_tag and tagged.expression is not None
            else self.dashboard.reply_expression(text)
        )
        self.realtime_after_speech_intensity = tagged.intensity
        # "speaking" is a mouth-animation state, not a valid expression after
        # playback. A neutral reply must return to the current idle pose.
        self.realtime_after_speech_state = (
            "idle" if reply_expression == "speaking" else reply_expression
        )
        self._show_bubble(text)
        QTimer.singleShot(3200, self.bubble.hide)

    def _realtime_speaking(self, speaking: bool) -> None:
        if self._closing:
            return
        if speaking:
            self.dashboard.cancel_ai_wait_expression()
            self.speech_gesture_expression = None
            self.realtime_mouth_active = True
            # Never carry an emotion selected for the preceding answer into a
            # new turn. The transcript may replace this with the new emotion.
            self.realtime_after_speech_state = "idle"
            self.realtime_after_speech_intensity = 0.5
            self.realtime_finish_timer.stop()
            self.expression_generation += 1
            self.state = "speaking"
            self.expression_arbiter.request(
                "speaking",
                source="conversation",
                force=True,
            )
            self.speech_pose_suffix = (
                "_lean"
                if self.idle_pose == "lean"
                else "_front"
                if self.idle_pose == "front"
                else ""
            )
            self.speech_closed_expression = (
                self._closed_speech_expression()
            )
            self.speech_mid_expression = self._mouth_mid_expression()
            self.speech_open_expression = self._speaking_expression()
            self._start_mouth_animation(audio_driven=True)
        else:
            is_realtime_mouth = (
                self.realtime_mouth_active
                or (
                    self.state == "speaking"
                    and self.audio_driven_mouth
                    and not self.speech_playing
                )
            )
            self.realtime_mouth_active = False
            if not is_realtime_mouth:
                return
            if self.realtime_finish_timer.isActive():
                return
            if (
                self.audio_driven_mouth
                and self.current_expression
                != self.speech_closed_expression
            ):
                self.mouth_closing = True
                self.viseme_dynamics.current = "CLOSED"
                self.mouth_open = False
                self.speech_current_expression = (
                    self.speech_closed_expression
                )
                self._queue_audio_mouth_transition(
                    self.speech_closed_expression
                )
                self.realtime_finish_timer.start(
                    MOUTH_CLOSE_DEADLINE_MS
                )
            else:
                self._complete_realtime_speaking_stop()

    def _complete_realtime_speaking_stop(self) -> None:
        self.realtime_finish_timer.stop()
        self.realtime_mouth_active = False
        was_realtime_speaking = (
            self.state == "speaking"
            and self.audio_driven_mouth
            and not self.speech_playing
        )
        if self.audio_driven_mouth or self.mouth_visual_timer.isActive():
            self._stop_mouth_animation()
        if not was_realtime_speaking:
            return
        final_state = self.realtime_after_speech_state
        self.realtime_after_speech_state = "idle"
        if (
            final_state == "speaking"
            or final_state.startswith(
                (
                    "mouth_",
                    "viseme_",
                    "blink_open",
                    "blink_mid",
                    "blink_wide",
                    "blink_round",
                    "blink_i",
                    "blink_o",
                )
            )
            or final_state not in self.expression_pixmaps
        ):
            final_state = "idle"
        final_intensity = getattr(
            self,
            "realtime_after_speech_intensity",
            0.5,
        )
        self.set_state(
            final_state,
            source="ai_tag",
            intensity=final_intensity,
            force=True,
        )
        if final_state != "idle":
            self._schedule_return_to_idle(
                self.expression_arbiter.hold_duration(
                    final_state,
                    final_intensity,
                ),
                final_state,
            )

    def _realtime_failed(self, message: str) -> None:
        self.dashboard.set_realtime_status(f"錯誤：{message[:90]}", False)
        self.realtime.stop()
        QMessageBox.warning(self.dashboard, "Realtime 語音", message)

    def _cloud_voice_failed(self, message: str) -> None:
        self._online_voice_failed(
            VOICE_ENGINE_OPENAI,
            "OpenAI 語音",
            message,
        )

    def _azure_voice_failed(self, message: str) -> None:
        self._online_voice_failed(
            VOICE_ENGINE_AZURE,
            "Azure Speech",
            message,
        )

    def _online_voice_failed(
        self,
        failed_provider_id: str,
        provider_label: str,
        message: str,
    ) -> None:
        fallback_provider_id = self.speech_providers.fallback_provider_id(
            failed_provider_id
        )
        if fallback_provider_id is not None:
            local_name = self.platform_services.capabilities.display_name
            self.dashboard.set_api_status(
                f"{provider_label}失敗，已切換 {local_name} 本機女聲："
                f"{message[:50]}"
            )
        else:
            self.dashboard.set_api_status(
                f"{provider_label}失敗；此平台沒有已驗證的本機語音備援："
                f"{message[:50]}"
            )
        if (
            self.speech_playing
            and self.active_speech_engine == failed_provider_id
            and not self.cloud_fallback_active
            and self.active_speech_text.strip()
        ):
            if fallback_provider_id is None:
                self._speech_audio_finished()
                return
            self.cloud_fallback_active = True
            self.active_speech_engine = fallback_provider_id
            self.speech_providers.provider(fallback_provider_id).speak(
                SpeechRequest(
                    text=self.active_speech_text,
                    voice=str(self.db.setting("windows_voice", "")),
                    rate=int(self.db.setting("voice_rate", -1)),
                )
            )
            return
        self._speech_audio_finished()

    def _windows_voice_failed(self, message: str) -> None:
        platform_name = self.platform_services.capabilities.display_name
        self.dashboard.set_api_status(
            f"{platform_name} 本機語音失敗：{message[:70]}"
        )

    def _speech_audio_finished(self) -> None:
        if not self.speech_playing:
            return
        if self.speech_finish_timer.isActive():
            return
        if (
            self.audio_driven_mouth
            and self.current_expression
            != self.speech_closed_expression
        ):
            self.mouth_closing = True
            self.viseme_dynamics.current = "CLOSED"
            self.mouth_open = False
            self.speech_current_expression = (
                self.speech_closed_expression
            )
            self._queue_audio_mouth_transition(
                self.speech_closed_expression
            )
            self.speech_finish_timer.start(
                MOUTH_CLOSE_DEADLINE_MS
            )
            return
        self._complete_speech_audio_finished()

    def _complete_speech_audio_finished(self) -> None:
        if not self.speech_playing:
            return
        self._stop_mouth_animation()
        final_state = self.after_speech_state
        final_intensity = getattr(self, "after_speech_intensity", 0.5)
        self.set_state(
            final_state,
            source="conversation",
            intensity=final_intensity,
            force=True,
        )
        self.speech_playing = False
        self.active_speech_text = ""
        self.active_speech_engine = ""
        self.cloud_fallback_active = False
        if self.speech_queue:
            QTimer.singleShot(120, self._start_next_speech)
        else:
            self.dashboard.set_voice_phase("準備就緒")
            if final_state != "idle":
                self._schedule_return_to_idle(
                    self.expression_arbiter.hold_duration(
                        final_state,
                        final_intensity,
                    ),
                    final_state,
                )
            QTimer.singleShot(
                2800,
                lambda: None if self.speech_playing else self.bubble.hide(),
            )

    def _schedule_return_to_idle(
        self,
        delay_ms: int,
        expected_state: str,
    ) -> None:
        generation = self.expression_generation
        QTimer.singleShot(
            delay_ms,
            lambda: self._return_to_idle_if_current(
                expected_state,
                generation,
            ),
        )

    def _return_to_idle_if_current(
        self,
        expected_state: str,
        generation: int,
    ) -> None:
        if (
            generation != self.expression_generation
            or self.state != expected_state
            or self.speech_playing
            or self.realtime_mouth_active
        ):
            return
        self.set_state("idle")

    def _return_to_idle(self) -> None:
        if (
            self.state == "speaking"
            or self.speech_playing
            or self.realtime_mouth_active
        ):
            return
        self.set_state("idle")

    def open_dashboard(self) -> None:
        self.dashboard.refresh_all()
        self.dashboard.show()
        self.dashboard.raise_()
        self.dashboard.activateWindow()

    def _dashboard_visibility_changed(self, active: bool) -> None:
        self._topmost_policy_tick()
        if active:
            QTimer.singleShot(0, self.dashboard.bring_to_front)

    def _external_foreground_window(self) -> int:
        if os.name != "nt":
            return 0
        user32 = ctypes.windll.user32
        foreground = int(user32.GetForegroundWindow() or 0)
        if not foreground:
            return 0
        foreground = int(user32.GetAncestor(foreground, 2) or foreground)

        class GUIThreadInfo(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("hwndActive", wintypes.HWND),
                ("hwndFocus", wintypes.HWND),
                ("hwndCapture", wintypes.HWND),
                ("hwndMenuOwner", wintypes.HWND),
                ("hwndMoveSize", wintypes.HWND),
                ("hwndCaret", wintypes.HWND),
                ("rcCaret", wintypes.RECT),
            ]

        thread_id = user32.GetWindowThreadProcessId(foreground, None)
        gui_info = GUIThreadInfo()
        gui_info.cbSize = ctypes.sizeof(GUIThreadInfo)
        if thread_id and user32.GetGUIThreadInfo(
            thread_id,
            ctypes.byref(gui_info),
        ):
            moving = int(gui_info.hwndMoveSize or 0)
            if moving:
                foreground = int(
                    user32.GetAncestor(moving, 2) or moving
                )
        own_windows = {
            int(self.winId()),
            int(self.dashboard.winId()),
        }
        if foreground in own_windows:
            return 0
        if not user32.IsWindowVisible(foreground) or user32.IsIconic(foreground):
            return 0
        class_name = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(foreground, class_name, len(class_name))
        if class_name.value in {
            "Progman",
            "WorkerW",
            "Shell_TrayWnd",
            "Shell_SecondaryTrayWnd",
        }:
            return 0
        return foreground

    @staticmethod
    def _rectangles_overlap_or_near(
        external: tuple[int, int, int, int],
        character: tuple[int, int, int, int],
        margin: int = 18,
    ) -> bool:
        ext_left, ext_top, ext_right, ext_bottom = external
        char_left, char_top, char_right, char_bottom = character
        char_left -= margin
        char_top -= margin
        char_right += margin
        char_bottom += margin
        overlap_width = max(
            0,
            min(ext_right, char_right) - max(ext_left, char_left),
        )
        overlap_height = max(
            0,
            min(ext_bottom, char_bottom) - max(ext_top, char_top),
        )
        return overlap_width * overlap_height >= 256

    def _external_foreground_overlaps_character(self) -> bool:
        self._smart_overlap_hwnd = 0
        if os.name != "nt":
            return False
        user32 = ctypes.windll.user32
        foreground = self._external_foreground_window()
        if not foreground:
            return False
        rect = wintypes.RECT()
        if not user32.GetWindowRect(foreground, ctypes.byref(rect)):
            return False
        character_rect = wintypes.RECT()
        if not user32.GetWindowRect(
            int(self.winId()),
            ctypes.byref(character_rect),
        ):
            return False
        overlaps = self._rectangles_overlap_or_near(
            (rect.left, rect.top, rect.right, rect.bottom),
            (
                character_rect.left,
                character_rect.top,
                character_rect.right,
                character_rect.bottom,
            ),
        )
        if overlaps:
            self._smart_overlap_hwnd = foreground
        return overlaps

    def _set_windows_character_z_order(
        self,
        enabled: bool,
        behind_hwnd: int = 0,
        user32=None,
        hwnd: int | None = None,
    ) -> None:
        user32 = user32 or ctypes.windll.user32
        hwnd = int(self.winId()) if hwnd is None else int(hwnd)
        flags = 0x0001 | 0x0002 | 0x0010
        if enabled:
            user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, flags)
            return
        # HWND_NOTOPMOST only removes the topmost style and may still leave
        # the character above every normal window. Explicitly insert it
        # behind the foreground/moving window afterwards.
        user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, flags)
        if behind_hwnd and user32.IsWindow(behind_hwnd):
            user32.SetWindowPos(
                hwnd,
                int(behind_hwnd),
                0,
                0,
                0,
                0,
                flags,
            )

    def _set_character_topmost(
        self,
        enabled: bool,
        behind_hwnd: int = 0,
    ) -> None:
        enabled = bool(enabled)
        behind_hwnd = 0 if enabled else int(behind_hwnd or 0)
        if (
            self.character_topmost_active == enabled
            and (
                enabled
                or self.character_behind_hwnd == behind_hwnd
            )
        ):
            return
        self.character_topmost_active = enabled
        self.character_behind_hwnd = behind_hwnd
        if os.name == "nt":
            self._set_windows_character_z_order(
                enabled,
                behind_hwnd,
            )
            return
        position = self.pos()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, enabled)
        self.move(position)
        self.show()

    def _topmost_policy_tick(self) -> None:
        dashboard_active = (
            self.dashboard.isVisible()
            and not self.dashboard.isMinimized()
        )
        mode = str(
            self.db.setting(
                "topmost_mode",
                "智慧置頂（推薦）",
            )
        )
        if dashboard_active or mode == "不置頂":
            should_stay_on_top = False
            behind_hwnd = (
                int(self.dashboard.winId())
                if dashboard_active
                else self._external_foreground_window()
            )
        elif mode == "永遠置頂":
            should_stay_on_top = True
            behind_hwnd = 0
        else:
            should_stay_on_top = (
                not self._external_foreground_overlaps_character()
            )
            behind_hwnd = self._smart_overlap_hwnd
        self._set_character_topmost(
            should_stay_on_top,
            behind_hwnd,
        )

    def check_reminders(self) -> None:
        now = local_wall_time()
        for row in self.db.due_reminders(now):
            self.db.mark_reminder_fired(row["kind"], now.date().isoformat())
            self.dashboard.show()
            self.dashboard.raise_()
            self.speak(
                str(
                    self.db.setting(
                        f"reminder_message_{row['kind']}",
                        reminder_line(
                            profile_setting(self.db, "ui_language"),
                            row["kind"],
                        ),
                    )
                ),
                "reminder",
            )

        active = self.db.active_session_seconds()
        threshold = int(self.db.setting("break_minutes", 90)) * 60
        bucket = active // threshold if threshold else 0
        notice_key = f"{now.date().isoformat()}-{bucket}"
        if active >= threshold and bucket and notice_key != self.last_overwork_notice:
            self.last_overwork_notice = notice_key
            self.dashboard.show()
            self.dashboard.raise_()
            self.speak(
                str(
                    self.db.setting(
                        "reminder_message_overwork",
                        reminder_line(
                            profile_setting(self.db, "ui_language"),
                            "overwork",
                        ),
                    )
                ),
                "worried",
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drag_offset and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.drag_offset = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:
        self._closing = True
        scheduler = getattr(self, "background_scheduler", None)
        if scheduler is not None:
            scheduler.close()
            self.background_scheduler = None
        self.blink_generation = getattr(self, "blink_generation", 0) + 1
        self._cancel_expression_transition()
        self._cancel_pose_transition()
        for animation_name in ("state_animation",):
            animation = getattr(self, animation_name, None)
            if animation is not None:
                animation.stop()
        self.realtime.stop()
        for timer_name in (
            "idle_timer",
            "pose_timer",
            "blink_timer",
            "gaze_timer",
            "ambient_timer",
            "mouth_timer",
            "mouth_visual_timer",
            "speech_finish_timer",
            "realtime_finish_timer",
            "physics_timer",
            "motion_timer",
            "attention_timer",
            "reminder_timer",
            "clock_timer",
            "topmost_timer",
            "background_agent_timer",
        ):
            timer = getattr(self, timer_name, None)
            if timer is not None:
                timer.stop()
        for dashboard_timer_name in ("timer", "front_raise_timer"):
            dashboard_timer = getattr(
                self.dashboard, dashboard_timer_name, None
            )
            if dashboard_timer is not None:
                dashboard_timer.stop()
        flagship_center = getattr(self.dashboard, "flagship_center", None)
        if flagship_center is not None:
            flagship_center.close_services()
        self.dashboard.close()
        self.db.close()
        tray = getattr(self, "tray", None)
        if tray is not None:
            tray.hide()
        event.accept()


def main() -> int:
    self_test = "--self-test" in sys.argv
    smoke_auto_exit = "--smoke-auto-exit" in sys.argv
    jit_status_arg = next(
        (arg for arg in sys.argv if arg.startswith("--jit-status-output=")),
        "",
    )
    if jit_status_arg:
        Path(jit_status_arg.split("=", 1)[1]).write_text(
            "PACKAGED_JIT_DEFAULT_OK"
            if jit_is_enabled()
            else "PACKAGED_JIT_DEFAULT_FAILED",
            encoding="utf-8",
        )
    if self_test or smoke_auto_exit:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    if sys.platform == "win32":
        # A restricted Windows session can still use the explicit Qt icon
        # below without preventing MoHan from starting.
        with suppress(AttributeError, OSError):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                WINDOWS_APP_USER_MODEL_ID
            )
    app = QApplication(sys.argv)
    app.setFont(application_ui_font())
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(application_icon())
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(STYLE)
    window = CompanionWindow(
        startup_speech=not self_test,
        defer_visual_startup=not self_test,
    )
    app.setApplicationName(profile_window_title(window.db))
    if self_test:
        physics_sources_ok = all(
            not window.physics_sources[pose].isNull()
            and not window.face_sources[pose].isNull()
            and not window.eye_sources[pose].isNull()
            and all(
                not window.hair_sources[pose][side].isNull()
                and not window.sleeve_sources[pose][side].isNull()
                for side in ("left", "right")
            )
            for pose in ("cheek", "lean", "front")
        )
        flagship_center = getattr(window.dashboard, "flagship_center", None)
        flagship_ok = (
            flagship_center is not None
            and flagship_center.tabs.count() == 7
            and not flagship_center.remote_enabled.isChecked()
            and not flagship_center.camera_enabled.isChecked()
            and flagship_center.camera_presence.camera is None
            and flagship_center.remote_server is None
            and "payment" not in flagship_center.executor.handlers
            and "shell" not in flagship_center.executor.handlers
        )
        ok = (
            window.character.pixmap() is not None
            and all(not pixmap.isNull() for pixmap in window.expression_pixmaps.values())
            and physics_sources_ok
            and all(
                window._physics_enabled(key)
                for key in (
                    "physics_sleeves",
                    "physics_hair",
                    "physics_ornament",
                    "physics_eye_tracking",
                    "physics_face_parallax",
                )
            )
            and window.character_opacity.opacity() == 1.0
            and window.dashboard.tabs.count() == 7
            and all(
                not button.autoDefault() and not button.isDefault()
                for button in window.dashboard.findChildren(QPushButton)
            )
            and flagship_ok
            and not (
                window.dashboard.windowFlags()
                & Qt.WindowStaysOnTopHint
            )
            and resource_path("voice_listener.ps1").exists()
            and resource_path(APP_ICON_PATH).exists()
            and not app.windowIcon().isNull()
            and not window.dashboard.windowIcon().isNull()
            and not window.tray.icon().isNull()
            and RealtimeVoiceClient.dependencies_available()
            and window.dashboard.windows_voice.currentData()
            == preferred_windows_voice(windows_voices())
            and window.dashboard.transcription_model.currentText()
            == SpeechListener.TRANSCRIPTION_MODEL
            and window.dashboard.realtime_transcription_model.currentText()
            == SpeechListener.TRANSCRIPTION_MODEL
            and window.dashboard.realtime_noise_reduction.currentData()
            == "near_field"
            and window.dashboard.realtime_turn_detection.currentData()
            == "server_vad"
            and window.dashboard.realtime_hybrid_transcription.isChecked()
            and window.dashboard.windows_transcription_fallback.isChecked()
            and SpeechListener.END_SILENCE_SECONDS == 0.85
            and SpeechListener.MAX_RECORD_SECONDS == 10.0
            and to_taiwan_traditional("打开软件") == "開啟軟體"
            and "請使用" not in (
                RealtimeVoiceClient
                ._sanitize_realtime_transcription_prompt(
                    SpeechListener.TRANSCRIPTION_PROMPT
                )
            )
            and "好呀你說" in (
                RealtimeVoiceClient._compose_instructions(
                    "人格",
                    "記憶",
                    "最近對話",
                )
            )
            and not (
                RealtimeVoiceClient._session_update_event(
                    RealtimeSessionConfig(
                        transcription_model=(
                            SpeechListener.TRANSCRIPTION_MODEL
                        ),
                    ),
                    "test",
                )["session"]["audio"]["input"]["turn_detection"][
                    "create_response"
                ]
            )
            and (
                RealtimeVoiceClient._session_update_event(
                    RealtimeSessionConfig(
                        transcription_model=(
                            SpeechListener.TRANSCRIPTION_MODEL
                        ),
                    ),
                    "test",
                )["session"]["audio"]["input"]["transcription"]
                is None
            )
        )
        output_arg = next(
            (arg for arg in sys.argv if arg.startswith("--self-test-output=")), ""
        )
        if output_arg:
            Path(output_arg.split("=", 1)[1]).write_text(
                "PACKAGED_SELFTEST_OK" if ok else "PACKAGED_SELFTEST_FAILED",
                encoding="utf-8",
            )
        window.close()
        app.processEvents()
        return 0 if ok else 2
    window.show()
    QTimer.singleShot(75, window.complete_deferred_startup)
    if smoke_auto_exit:
        output_arg = next(
            (
                arg
                for arg in sys.argv
                if arg.startswith("--smoke-output=")
            ),
            "",
        )
        QTimer.singleShot(2_500, window.close)
        QTimer.singleShot(2_700, app.quit)
        exit_code = app.exec()
        if output_arg:
            Path(output_arg.split("=", 1)[1]).write_text(
                "PACKAGED_EVENT_LOOP_OK"
                if exit_code == 0
                else "PACKAGED_EVENT_LOOP_FAILED",
                encoding="utf-8",
            )
        return exit_code
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
