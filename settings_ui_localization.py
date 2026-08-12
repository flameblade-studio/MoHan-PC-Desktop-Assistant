from __future__ import annotations

lazy from collections.abc import Mapping
lazy from enum import StrEnum
lazy from string import Formatter

lazy from language_support import canonical_ui_language


class SettingsText(StrEnum):
    """Complete, typed text contract for desktop and work settings."""

    AUTOSTART_LABEL = "autostart_label"
    AUTOSTART_WINDOWS = "autostart_windows"
    AUTOSTART_UNAVAILABLE = "autostart_unavailable"
    AUTOSTART_ERROR_TITLE = "autostart_error_title"
    AUTOSTART_ERROR = "autostart_error"
    TOPMOST_LABEL = "topmost_label"
    TOPMOST_SMART = "topmost_smart"
    TOPMOST_ALWAYS = "topmost_always"
    TOPMOST_NEVER = "topmost_never"
    CHARACTER_SCALE_LABEL = "character_scale_label"
    CHARACTER_SCALE_RESET = "character_scale_reset"
    CHARACTER_SCALE_RESET_TOOLTIP = "character_scale_reset_tooltip"
    PROACTIVE_LABEL = "proactive_label"
    PROACTIVE_QUIET = "proactive_quiet"
    PROACTIVE_BALANCED = "proactive_balanced"
    PROACTIVE_ACTIVE = "proactive_active"
    BACKGROUND_ASSISTANT_LABEL = "background_assistant_label"
    BACKGROUND_ASSISTANT_ENABLED = "background_assistant_enabled"
    BACKGROUND_MODE_LABEL = "background_mode_label"
    BACKGROUND_MODE_FOLLOWS_PROACTIVE = (
        "background_mode_follows_proactive"
    )
    BACKGROUND_WATCH_APPS_LABEL = "background_watch_apps_label"
    BACKGROUND_WATCH_APPS_PLACEHOLDER = (
        "background_watch_apps_placeholder"
    )
    BACKGROUND_DIAGNOSTIC_LABEL = "background_diagnostic_label"
    BACKGROUND_DIAGNOSTIC_PLACEHOLDER = (
        "background_diagnostic_placeholder"
    )
    BACKGROUND_SAFETY_NOTE = "background_safety_note"
    PHYSICS_LABEL = "physics_label"
    PHYSICS_SLEEVES_NAME = "physics_sleeves_name"
    PHYSICS_SLEEVES_DESCRIPTION = "physics_sleeves_description"
    PHYSICS_HAIR_NAME = "physics_hair_name"
    PHYSICS_HAIR_DESCRIPTION = "physics_hair_description"
    PHYSICS_ORNAMENT_NAME = "physics_ornament_name"
    PHYSICS_ORNAMENT_DESCRIPTION = "physics_ornament_description"
    PHYSICS_EYE_TRACKING_NAME = "physics_eye_tracking_name"
    PHYSICS_EYE_TRACKING_DESCRIPTION = "physics_eye_tracking_description"
    PHYSICS_FACE_PARALLAX_NAME = "physics_face_parallax_name"
    PHYSICS_FACE_PARALLAX_DESCRIPTION = (
        "physics_face_parallax_description"
    )
    PHYSICS_NOTE = "physics_note"
    WORK_FOLDER_LABEL = "work_folder_label"
    WORK_FOLDER_PLACEHOLDER = "work_folder_placeholder"
    WORK_FOLDER_BROWSE = "work_folder_browse"
    WORK_FOLDER_OPEN = "work_folder_open"
    WORK_FOLDER_BROWSE_TITLE = "work_folder_browse_title"
    WORK_FOLDER_INVALID_TITLE = "work_folder_invalid_title"
    WORK_FOLDER_INVALID_MESSAGE = "work_folder_invalid_message"
    AI_CORE_LABEL = "ai_core_label"
    PERSONA_LABEL = "persona_label"
    PERSONA_PLACEHOLDER = "persona_placeholder"
    PROFILE_REQUIRED_TITLE = "profile_required_title"
    PROFILE_REQUIRED_MESSAGE = "profile_required_message"


LANGUAGE_ORDER = ("zh-TW", "zh-CN", "en", "ja-JP")

TOPMOST_MODE_KEYS = (
    SettingsText.TOPMOST_SMART,
    SettingsText.TOPMOST_ALWAYS,
    SettingsText.TOPMOST_NEVER,
)

PROACTIVE_MODE_KEYS = (
    SettingsText.PROACTIVE_QUIET,
    SettingsText.PROACTIVE_BALANCED,
    SettingsText.PROACTIVE_ACTIVE,
)

PHYSICS_TEXT_KEYS: Mapping[
    str,
    tuple[SettingsText, SettingsText],
] = frozendict({
    "physics_sleeves": (
        SettingsText.PHYSICS_SLEEVES_NAME,
        SettingsText.PHYSICS_SLEEVES_DESCRIPTION,
    ),
    "physics_hair": (
        SettingsText.PHYSICS_HAIR_NAME,
        SettingsText.PHYSICS_HAIR_DESCRIPTION,
    ),
    "physics_ornament": (
        SettingsText.PHYSICS_ORNAMENT_NAME,
        SettingsText.PHYSICS_ORNAMENT_DESCRIPTION,
    ),
    "physics_eye_tracking": (
        SettingsText.PHYSICS_EYE_TRACKING_NAME,
        SettingsText.PHYSICS_EYE_TRACKING_DESCRIPTION,
    ),
    "physics_face_parallax": (
        SettingsText.PHYSICS_FACE_PARALLAX_NAME,
        SettingsText.PHYSICS_FACE_PARALLAX_DESCRIPTION,
    ),
})


_ZH_TW: Mapping[SettingsText, str] = frozendict({
    SettingsText.AUTOSTART_LABEL: "自動啟動",
    SettingsText.AUTOSTART_WINDOWS: "Windows 登入後自動啟動",
    SettingsText.AUTOSTART_UNAVAILABLE: (
        "{platform} 自動啟動尚未完成實機驗證"
    ),
    SettingsText.AUTOSTART_ERROR_TITLE: "自動啟動",
    SettingsText.AUTOSTART_ERROR: "無法更新自動啟動：{reason}",
    SettingsText.TOPMOST_LABEL: "桌面置頂方式",
    SettingsText.TOPMOST_SMART: "智慧置頂（推薦）",
    SettingsText.TOPMOST_ALWAYS: "永遠置頂",
    SettingsText.TOPMOST_NEVER: "不置頂",
    SettingsText.CHARACTER_SCALE_LABEL: "桌面{assistant}顯示大小",
    SettingsText.CHARACTER_SCALE_RESET: "恢復 100%",
    SettingsText.CHARACTER_SCALE_RESET_TOOLTIP: (
        "將桌面{assistant}恢復為原始顯示大小"
    ),
    SettingsText.PROACTIVE_LABEL: "主動協助程度",
    SettingsText.PROACTIVE_QUIET: "安靜（只提醒必要事項）",
    SettingsText.PROACTIVE_BALANCED: "平衡（推薦）",
    SettingsText.PROACTIVE_ACTIVE: "積極（主動建議）",
    SettingsText.BACKGROUND_ASSISTANT_LABEL: "背景多工助理",
    SettingsText.BACKGROUND_ASSISTANT_ENABLED: (
        "啟用背景多工助理（預設關閉）"
    ),
    SettingsText.BACKGROUND_MODE_LABEL: "背景助理模式",
    SettingsText.BACKGROUND_MODE_FOLLOWS_PROACTIVE: (
        "依照主動協助程度"
    ),
    SettingsText.BACKGROUND_WATCH_APPS_LABEL: "監測程式名稱",
    SettingsText.BACKGROUND_WATCH_APPS_PLACEHOLDER: (
        "以逗號分隔，例如：Visual Studio Code, GitHub Desktop"
    ),
    SettingsText.BACKGROUND_DIAGNOSTIC_LABEL: "IDE 診斷報告",
    SettingsText.BACKGROUND_DIAGNOSTIC_PLACEHOLDER: (
        "選填：IDE 匯出的 .txt 或 .log 診斷報告完整路徑"
    ),
    SettingsText.BACKGROUND_SAFETY_NOTE: (
        "背景助理只讀取可見程式名稱與您明確指定的診斷報告；"
        "不會截取編輯器內容、不會自動修改檔案，也會遵守勿擾模式與冷卻時間。"
    ),
    SettingsText.PHYSICS_LABEL: "電影級物理",
    SettingsText.PHYSICS_SLEEVES_NAME: "袖擺呼吸與慣性",
    SettingsText.PHYSICS_SLEEVES_DESCRIPTION: (
        "依呼吸與移動柔和帶動袖擺，呈現布料重量與慣性。"
    ),
    SettingsText.PHYSICS_HAIR_NAME: "長髮柔性擺動",
    SettingsText.PHYSICS_HAIR_DESCRIPTION: (
        "讓長髮隨姿勢與移動自然擺動，避免僵硬晃動。"
    ),
    SettingsText.PHYSICS_ORNAMENT_NAME: "髮飾與流蘇慣性",
    SettingsText.PHYSICS_ORNAMENT_DESCRIPTION: (
        "讓髮飾與流蘇以較小幅度延遲跟隨頭部動作。"
    ),
    SettingsText.PHYSICS_EYE_TRACKING_NAME: "眼球追蹤滑鼠",
    SettingsText.PHYSICS_EYE_TRACKING_DESCRIPTION: (
        "讓視線平滑追蹤滑鼠位置，不會影響實際游標操作。"
    ),
    SettingsText.PHYSICS_FACE_PARALLAX_NAME: "臉部柔和視差",
    SettingsText.PHYSICS_FACE_PARALLAX_DESCRIPTION: (
        "依視線與姿勢加入輕微臉部視差，提升 2.5D 深度感。"
    ),
    SettingsText.PHYSICS_NOTE: (
        "旗艦物理預設全部開啟；可依效能需要個別關閉。"
    ),
    SettingsText.WORK_FOLDER_LABEL: "工作資料夾",
    SettingsText.WORK_FOLDER_PLACEHOLDER: "常用工作資料夾路徑",
    SettingsText.WORK_FOLDER_BROWSE: "瀏覽…",
    SettingsText.WORK_FOLDER_OPEN: "開啟工作資料夾",
    SettingsText.WORK_FOLDER_BROWSE_TITLE: "選擇工作資料夾",
    SettingsText.WORK_FOLDER_INVALID_TITLE: "工作資料夾",
    SettingsText.WORK_FOLDER_INVALID_MESSAGE: (
        "請先填入有效的資料夾路徑。"
    ),
    SettingsText.AI_CORE_LABEL: "AI 智能核心",
    SettingsText.PERSONA_LABEL: "AI 人格提示詞",
    SettingsText.PERSONA_PLACEHOLDER: (
        "設定助理的角色背景、語氣、工作方式與界線。"
    ),
    SettingsText.PROFILE_REQUIRED_TITLE: "尚缺必要資料",
    SettingsText.PROFILE_REQUIRED_MESSAGE: (
        "助理名稱與助理對你的稱呼不可留空。"
    ),
})


_ZH_CN: Mapping[SettingsText, str] = frozendict({
    SettingsText.AUTOSTART_LABEL: "自动启动",
    SettingsText.AUTOSTART_WINDOWS: "Windows 登录后自动启动",
    SettingsText.AUTOSTART_UNAVAILABLE: (
        "{platform} 自动启动尚未完成真机验证"
    ),
    SettingsText.AUTOSTART_ERROR_TITLE: "自动启动",
    SettingsText.AUTOSTART_ERROR: "无法更新自动启动：{reason}",
    SettingsText.TOPMOST_LABEL: "桌面置顶方式",
    SettingsText.TOPMOST_SMART: "智能置顶（推荐）",
    SettingsText.TOPMOST_ALWAYS: "始终置顶",
    SettingsText.TOPMOST_NEVER: "不置顶",
    SettingsText.CHARACTER_SCALE_LABEL: "桌面{assistant}显示大小",
    SettingsText.CHARACTER_SCALE_RESET: "恢复 100%",
    SettingsText.CHARACTER_SCALE_RESET_TOOLTIP: (
        "将桌面{assistant}恢复为原始显示大小"
    ),
    SettingsText.PROACTIVE_LABEL: "主动协助程度",
    SettingsText.PROACTIVE_QUIET: "安静（仅提醒必要事项）",
    SettingsText.PROACTIVE_BALANCED: "均衡（推荐）",
    SettingsText.PROACTIVE_ACTIVE: "积极（主动建议）",
    SettingsText.BACKGROUND_ASSISTANT_LABEL: "后台多任务助手",
    SettingsText.BACKGROUND_ASSISTANT_ENABLED: (
        "启用后台多任务助手（默认关闭）"
    ),
    SettingsText.BACKGROUND_MODE_LABEL: "后台助手模式",
    SettingsText.BACKGROUND_MODE_FOLLOWS_PROACTIVE: (
        "跟随主动协助程度"
    ),
    SettingsText.BACKGROUND_WATCH_APPS_LABEL: "监测程序名称",
    SettingsText.BACKGROUND_WATCH_APPS_PLACEHOLDER: (
        "用逗号分隔，例如：Visual Studio Code, GitHub Desktop"
    ),
    SettingsText.BACKGROUND_DIAGNOSTIC_LABEL: "IDE 诊断报告",
    SettingsText.BACKGROUND_DIAGNOSTIC_PLACEHOLDER: (
        "可选：IDE 导出的 .txt 或 .log 诊断报告完整路径"
    ),
    SettingsText.BACKGROUND_SAFETY_NOTE: (
        "后台助手只读取可见程序名称和您明确指定的诊断报告；"
        "不会截取编辑器内容，不会自动修改文件，并会遵守免打扰模式和冷却时间。"
    ),
    SettingsText.PHYSICS_LABEL: "电影级物理效果",
    SettingsText.PHYSICS_SLEEVES_NAME: "袖摆呼吸与惯性",
    SettingsText.PHYSICS_SLEEVES_DESCRIPTION: (
        "根据呼吸与移动柔和带动袖摆，呈现布料重量与惯性。"
    ),
    SettingsText.PHYSICS_HAIR_NAME: "长发柔性摆动",
    SettingsText.PHYSICS_HAIR_DESCRIPTION: (
        "让长发随姿势与移动自然摆动，避免僵硬晃动。"
    ),
    SettingsText.PHYSICS_ORNAMENT_NAME: "发饰与流苏惯性",
    SettingsText.PHYSICS_ORNAMENT_DESCRIPTION: (
        "让发饰与流苏以较小幅度延迟跟随头部动作。"
    ),
    SettingsText.PHYSICS_EYE_TRACKING_NAME: "眼球跟踪鼠标",
    SettingsText.PHYSICS_EYE_TRACKING_DESCRIPTION: (
        "让视线平滑跟踪鼠标位置，不会影响实际指针操作。"
    ),
    SettingsText.PHYSICS_FACE_PARALLAX_NAME: "脸部柔和视差",
    SettingsText.PHYSICS_FACE_PARALLAX_DESCRIPTION: (
        "根据视线与姿势加入轻微脸部视差，提升 2.5D 深度感。"
    ),
    SettingsText.PHYSICS_NOTE: (
        "旗舰物理效果默认全部启用；可根据性能需要单独关闭。"
    ),
    SettingsText.WORK_FOLDER_LABEL: "工作文件夹",
    SettingsText.WORK_FOLDER_PLACEHOLDER: "常用工作文件夹路径",
    SettingsText.WORK_FOLDER_BROWSE: "浏览…",
    SettingsText.WORK_FOLDER_OPEN: "打开工作文件夹",
    SettingsText.WORK_FOLDER_BROWSE_TITLE: "选择工作文件夹",
    SettingsText.WORK_FOLDER_INVALID_TITLE: "工作文件夹",
    SettingsText.WORK_FOLDER_INVALID_MESSAGE: (
        "请先填写有效的文件夹路径。"
    ),
    SettingsText.AI_CORE_LABEL: "AI 智能核心",
    SettingsText.PERSONA_LABEL: "AI 人格提示词",
    SettingsText.PERSONA_PLACEHOLDER: (
        "设置助手的角色背景、语气、工作方式与界限。"
    ),
    SettingsText.PROFILE_REQUIRED_TITLE: "缺少必要信息",
    SettingsText.PROFILE_REQUIRED_MESSAGE: (
        "助手名称和助手对你的称呼不能为空。"
    ),
})


_EN: Mapping[SettingsText, str] = frozendict({
    SettingsText.AUTOSTART_LABEL: "Start automatically",
    SettingsText.AUTOSTART_WINDOWS: (
        "Start automatically after Windows sign-in"
    ),
    SettingsText.AUTOSTART_UNAVAILABLE: (
        "Autostart on {platform} has not been verified on a physical device"
    ),
    SettingsText.AUTOSTART_ERROR_TITLE: "Autostart",
    SettingsText.AUTOSTART_ERROR: "Could not update autostart: {reason}",
    SettingsText.TOPMOST_LABEL: "Keep on top",
    SettingsText.TOPMOST_SMART: "Smart on top (Recommended)",
    SettingsText.TOPMOST_ALWAYS: "Always on top",
    SettingsText.TOPMOST_NEVER: "Never on top",
    SettingsText.CHARACTER_SCALE_LABEL: "Desktop {assistant} size",
    SettingsText.CHARACTER_SCALE_RESET: "Reset to 100%",
    SettingsText.CHARACTER_SCALE_RESET_TOOLTIP: (
        "Restore desktop {assistant} to its original display size"
    ),
    SettingsText.PROACTIVE_LABEL: "Proactive assistance",
    SettingsText.PROACTIVE_QUIET: "Quiet (Essential reminders only)",
    SettingsText.PROACTIVE_BALANCED: "Balanced (Recommended)",
    SettingsText.PROACTIVE_ACTIVE: "Active (Proactive suggestions)",
    SettingsText.BACKGROUND_ASSISTANT_LABEL: (
        "Background multitasking assistant"
    ),
    SettingsText.BACKGROUND_ASSISTANT_ENABLED: (
        "Enable background multitasking assistant (Off by default)"
    ),
    SettingsText.BACKGROUND_MODE_LABEL: "Background assistant mode",
    SettingsText.BACKGROUND_MODE_FOLLOWS_PROACTIVE: (
        "Follow proactive assistance level"
    ),
    SettingsText.BACKGROUND_WATCH_APPS_LABEL: "Apps to monitor",
    SettingsText.BACKGROUND_WATCH_APPS_PLACEHOLDER: (
        "Comma-separated, for example: Visual Studio Code, GitHub Desktop"
    ),
    SettingsText.BACKGROUND_DIAGNOSTIC_LABEL: "IDE diagnostic report",
    SettingsText.BACKGROUND_DIAGNOSTIC_PLACEHOLDER: (
        "Optional: full path to an IDE-exported .txt or .log diagnostic report"
    ),
    SettingsText.BACKGROUND_SAFETY_NOTE: (
        "The background assistant reads only visible app names and diagnostic "
        "reports you explicitly select. It does not capture editor content or "
        "modify files automatically, and it respects Do Not Disturb and cooldowns."
    ),
    SettingsText.PHYSICS_LABEL: "Cinematic physics",
    SettingsText.PHYSICS_SLEEVES_NAME: "Sleeve breathing and inertia",
    SettingsText.PHYSICS_SLEEVES_DESCRIPTION: (
        "Gently moves the sleeves with breathing and motion to convey fabric "
        "weight and inertia."
    ),
    SettingsText.PHYSICS_HAIR_NAME: "Soft long-hair movement",
    SettingsText.PHYSICS_HAIR_DESCRIPTION: (
        "Moves long hair naturally with pose and motion while avoiding rigid "
        "movement."
    ),
    SettingsText.PHYSICS_ORNAMENT_NAME: "Hair ornament and tassel inertia",
    SettingsText.PHYSICS_ORNAMENT_DESCRIPTION: (
        "Lets hair ornaments and tassels follow head movement with a subtle delay."
    ),
    SettingsText.PHYSICS_EYE_TRACKING_NAME: "Mouse eye tracking",
    SettingsText.PHYSICS_EYE_TRACKING_DESCRIPTION: (
        "Moves the gaze smoothly toward the pointer without affecting mouse input."
    ),
    SettingsText.PHYSICS_FACE_PARALLAX_NAME: "Gentle facial parallax",
    SettingsText.PHYSICS_FACE_PARALLAX_DESCRIPTION: (
        "Adds subtle facial parallax from gaze and pose to enhance 2.5D depth."
    ),
    SettingsText.PHYSICS_NOTE: (
        "All flagship physics effects are enabled by default and can be "
        "disabled individually when needed for performance."
    ),
    SettingsText.WORK_FOLDER_LABEL: "Work folder",
    SettingsText.WORK_FOLDER_PLACEHOLDER: "Path to your usual work folder",
    SettingsText.WORK_FOLDER_BROWSE: "Browse…",
    SettingsText.WORK_FOLDER_OPEN: "Open work folder",
    SettingsText.WORK_FOLDER_BROWSE_TITLE: "Choose work folder",
    SettingsText.WORK_FOLDER_INVALID_TITLE: "Work folder",
    SettingsText.WORK_FOLDER_INVALID_MESSAGE: (
        "Enter a valid folder path first."
    ),
    SettingsText.AI_CORE_LABEL: "AI core",
    SettingsText.PERSONA_LABEL: "AI persona prompt",
    SettingsText.PERSONA_PLACEHOLDER: (
        "Define the assistant's background, tone, working style, and boundaries."
    ),
    SettingsText.PROFILE_REQUIRED_TITLE: "Required information missing",
    SettingsText.PROFILE_REQUIRED_MESSAGE: (
        "Assistant name and how the assistant addresses you are required."
    ),
})


_JA: Mapping[SettingsText, str] = frozendict({
    SettingsText.AUTOSTART_LABEL: "自動起動",
    SettingsText.AUTOSTART_WINDOWS: "Windows サインイン後に自動起動",
    SettingsText.AUTOSTART_UNAVAILABLE: (
        "{platform} の自動起動は実機での動作確認が完了していません"
    ),
    SettingsText.AUTOSTART_ERROR_TITLE: "自動起動",
    SettingsText.AUTOSTART_ERROR: "自動起動を更新できませんでした：{reason}",
    SettingsText.TOPMOST_LABEL: "常に手前に表示",
    SettingsText.TOPMOST_SMART: "スマート表示（推奨）",
    SettingsText.TOPMOST_ALWAYS: "常に手前に表示",
    SettingsText.TOPMOST_NEVER: "手前に固定しない",
    SettingsText.CHARACTER_SCALE_LABEL: (
        "デスクトップ上の{assistant}の表示サイズ"
    ),
    SettingsText.CHARACTER_SCALE_RESET: "100% に戻す",
    SettingsText.CHARACTER_SCALE_RESET_TOOLTIP: (
        "デスクトップ上の{assistant}を元の表示サイズに戻します"
    ),
    SettingsText.PROACTIVE_LABEL: "先回り支援の程度",
    SettingsText.PROACTIVE_QUIET: "静か（必要な通知のみ）",
    SettingsText.PROACTIVE_BALANCED: "バランス（推奨）",
    SettingsText.PROACTIVE_ACTIVE: "積極的（先回りして提案）",
    SettingsText.BACKGROUND_ASSISTANT_LABEL: (
        "バックグラウンド・マルチタスク支援"
    ),
    SettingsText.BACKGROUND_ASSISTANT_ENABLED: (
        "バックグラウンド・マルチタスク支援を有効にする（初期設定：無効）"
    ),
    SettingsText.BACKGROUND_MODE_LABEL: "バックグラウンド支援モード",
    SettingsText.BACKGROUND_MODE_FOLLOWS_PROACTIVE: (
        "先回り支援の程度に従う"
    ),
    SettingsText.BACKGROUND_WATCH_APPS_LABEL: "監視するアプリ名",
    SettingsText.BACKGROUND_WATCH_APPS_PLACEHOLDER: (
        "カンマ区切り（例：Visual Studio Code, GitHub Desktop）"
    ),
    SettingsText.BACKGROUND_DIAGNOSTIC_LABEL: "IDE 診断レポート",
    SettingsText.BACKGROUND_DIAGNOSTIC_PLACEHOLDER: (
        "任意：IDE から出力した .txt または .log 診断レポートの完全なパス"
    ),
    SettingsText.BACKGROUND_SAFETY_NOTE: (
        "バックグラウンド支援は、表示中のアプリ名と明示的に指定した診断レポート"
        "のみを読み取ります。エディターの内容を取得したり、ファイルを自動変更したり"
        "せず、通知抑制モードとクールダウン時間も守ります。"
    ),
    SettingsText.PHYSICS_LABEL: "映画品質の物理表現",
    SettingsText.PHYSICS_SLEEVES_NAME: "袖の呼吸連動と慣性",
    SettingsText.PHYSICS_SLEEVES_DESCRIPTION: (
        "呼吸や動きに合わせて袖を穏やかに揺らし、布の重さと慣性を表現します。"
    ),
    SettingsText.PHYSICS_HAIR_NAME: "長髪の柔らかな揺れ",
    SettingsText.PHYSICS_HAIR_DESCRIPTION: (
        "姿勢や動きに合わせて長い髪を自然に揺らし、硬い動きを抑えます。"
    ),
    SettingsText.PHYSICS_ORNAMENT_NAME: "髪飾りと房飾りの慣性",
    SettingsText.PHYSICS_ORNAMENT_DESCRIPTION: (
        "頭の動きに少し遅れて、髪飾りと房飾りを小さく揺らします。"
    ),
    SettingsText.PHYSICS_EYE_TRACKING_NAME: "視線のマウス追従",
    SettingsText.PHYSICS_EYE_TRACKING_DESCRIPTION: (
        "実際のマウス操作に影響を与えず、視線をポインターへ滑らかに追従させます。"
    ),
    SettingsText.PHYSICS_FACE_PARALLAX_NAME: "顔の穏やかな視差",
    SettingsText.PHYSICS_FACE_PARALLAX_DESCRIPTION: (
        "視線と姿勢に応じて顔へ控えめな視差を加え、2.5D の奥行きを高めます。"
    ),
    SettingsText.PHYSICS_NOTE: (
        "主要な物理効果はすべて初期状態で有効です。性能に応じて個別に無効化できます。"
    ),
    SettingsText.WORK_FOLDER_LABEL: "作業フォルダー",
    SettingsText.WORK_FOLDER_PLACEHOLDER: "通常使用する作業フォルダーのパス",
    SettingsText.WORK_FOLDER_BROWSE: "参照…",
    SettingsText.WORK_FOLDER_OPEN: "作業フォルダーを開く",
    SettingsText.WORK_FOLDER_BROWSE_TITLE: "作業フォルダーを選択",
    SettingsText.WORK_FOLDER_INVALID_TITLE: "作業フォルダー",
    SettingsText.WORK_FOLDER_INVALID_MESSAGE: (
        "有効なフォルダーのパスを先に入力してください。"
    ),
    SettingsText.AI_CORE_LABEL: "AI コア",
    SettingsText.PERSONA_LABEL: "AI ペルソナプロンプト",
    SettingsText.PERSONA_PLACEHOLDER: (
        "アシスタントの背景、口調、仕事の進め方、守るべき境界を設定します。"
    ),
    SettingsText.PROFILE_REQUIRED_TITLE: "必須情報が不足しています",
    SettingsText.PROFILE_REQUIRED_MESSAGE: (
        "アシスタント名と、アシスタントからの呼び名を入力してください。"
    ),
})


TRANSLATIONS: Mapping[str, Mapping[SettingsText, str]] = frozendict({
    "zh-TW": _ZH_TW,
    "zh-CN": _ZH_CN,
    "en": _EN,
    "ja-JP": _JA,
})


def _format_fields(template: str) -> tuple[str, ...]:
    return tuple(
        field_name
        for _literal, field_name, _format_spec, _conversion in Formatter().parse(
            template
        )
        if field_name is not None
    )


def _validate_translation_contract() -> None:
    expected_keys = frozenset(SettingsText)
    reference_fields = {
        key: _format_fields(template)
        for key, template in _ZH_TW.items()
    }
    for language, translations in TRANSLATIONS.items():
        actual_keys = frozenset(translations)
        if actual_keys != expected_keys:
            missing = sorted(key.value for key in expected_keys - actual_keys)
            extra = sorted(key.value for key in actual_keys - expected_keys)
            raise RuntimeError(
                f"Incomplete settings UI translations for {language}: "
                f"missing={missing}, extra={extra}"
            )
        mismatched_fields = sorted(
            key.value
            for key, template in translations.items()
            if _format_fields(template) != reference_fields[key]
        )
        if mismatched_fields:
            raise RuntimeError(
                f"Inconsistent settings UI format fields for {language}: "
                f"keys={mismatched_fields}"
            )


_validate_translation_contract()


def settings_text(
    language: str,
    key: SettingsText,
    **values: object,
) -> str:
    """Return one localized settings string from the complete key set."""

    template = TRANSLATIONS[canonical_ui_language(language)][key]
    return template.format(**values)


__all__ = (
    "LANGUAGE_ORDER",
    "PHYSICS_TEXT_KEYS",
    "PROACTIVE_MODE_KEYS",
    "TOPMOST_MODE_KEYS",
    "TRANSLATIONS",
    "SettingsText",
    "settings_text",
)
