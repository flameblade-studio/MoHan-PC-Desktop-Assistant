from __future__ import annotations

lazy from collections.abc import Mapping

lazy from immutable_config import deep_freeze
lazy from language_support import is_english, is_japanese, is_simplified_chinese
lazy from ui_localization_ja import JAPANESE_UI

_ENGLISH: Mapping[str, str] = deep_freeze({
    "first_run_title": "First-run setup",
    "first_run_heading": "<b>Welcome to MoHan Desktop Assistant</b>",
    "first_run_hero_tagline": (
        "A thousand-year-old Northern Song sword spirit who listens, "
        "remembers, and helps you get things done."
    ),
    "first_run_intro": (
        "Create your profile first. You can change these choices later in "
        "Settings; they are not tied to a specific company or profession."
    ),
    "assistant_name": "Assistant name",
    "user_title": "How the assistant addresses you",
    "organization_name": "Company / team name",
    "window_title": "Full window title",
    "work_type": "Work type",
    "ui_language": "Interface and reply language",
    "wake_word": "Voice wake word",
    "assistant_name_placeholder": "For example: MoHan, Ava, Office Mate",
    "user_title_placeholder": "For example: Commander, Alex, Manager",
    "organization_placeholder": "Optional company, studio, or team name",
    "window_title_placeholder": (
        "Leave blank to use Assistant name · Organization"
    ),
    "wake_word_placeholder": "For example: MoHan",
    "first_run_note": (
        "The Work Platforms page starts empty. Add only the company systems, "
        "collaboration tools, admin panels, or websites you use."
    ),
    "finish_setup": "Finish setup and start",
    "required_title": "Required information missing",
    "required_identity": (
        "Enter an assistant name and how the assistant should address you."
    ),
    "mode": "Mode",
    "start_work": "Start work",
    "stop_work": "Stop work",
    "tab_chat": "Chat",
    "tab_today": "Today",
    "tab_platforms": "Work platforms",
    "tab_memory": "Long-term memory",
    "tab_voice": "Voice",
    "tab_permissions": "Computer permissions",
    "tab_settings": "Settings",
    "chat_retention": "Chats stay on this computer and are not auto-deleted",
    "load_older_chat": "Load older chats",
    "manage_chat": "Manage / clear chats",
    "chat_placeholder": "Talk to MoHan…",
    "microphone": "🎙 Microphone",
    "send_text": "Send",
    "voice_ready": "Voice status: Ready",
    "speech_recognition": "Single-use microphone recognition",
    "transcription_model": "Transcription model",
    "transcription_language": "Transcription language",
    "transcription_prompt": "Transcription prompt / common terms",
    "windows_transcription_fallback": "Windows fallback",
    "offline_fallback": "Offline fallback",
    "platform_offline_fallback_unavailable": (
        "{platform} offline recognition has not completed device verification"
    ),
    "last_transcription": "Latest transcription diagnostic",
    "voice_engine": "Speech method",
    "windows_voice": "Windows voice",
    "platform_local_voice": "{platform} local voice",
    "platform_local_voice_unavailable": (
        "{platform} local voice has not completed device verification"
    ),
    "tts_voice": "OpenAI text-to-speech voice",
    "realtime_voice": "Realtime conversation voice",
    "realtime_model": "Realtime model",
    "realtime_transcription_model": "Realtime transcription model",
    "realtime_noise": "Realtime microphone noise reduction",
    "realtime_turn": "Realtime turn detection",
    "realtime_screen_transcript": "Realtime screen transcript",
    "echo_guard": "Echo guard",
    "local_rate": "Local speech rate",
    "mohan_volume": "MoHan volume",
    "voice_style": "Voice style",
    "realtime": "Realtime voice",
    "windows_engine": "Windows local voice",
    "openai_engine": "OpenAI natural voice",
    "realtime_engine": "Realtime voice",
    "azure_engine": "Azure Speech (Preview)",
    "azure_voice": "Azure Speech female voice",
    "azure_region": "Azure Speech region",
    "azure_key": "Azure Speech key",
    "azure_region_placeholder": "For example: eastasia",
    "azure_key_saved": "Encrypted by Windows; leave blank to keep it",
    "azure_key_missing": "Paste the Azure Speech resource key",
    "azure_remove_key": "Remove Azure Speech key",
    "azure_remove_key_confirm": (
        "Remove the Azure Speech key encrypted by Windows?"
    ),
    "azure_key_save_failed": (
        "Could not securely save the Azure Speech key: {error}"
    ),
    "azure_speech_note": (
        "Preview feature. Bring your own Azure Speech resource key and its "
        "matching region. Only verified female voices are listed. Missing "
        "settings or a service failure falls back to a Windows female voice. "
        "Azure usage and charges are governed by Microsoft."
    ),
    "azure_speech_note_no_local_fallback": (
        "Preview feature. Bring your own Azure Speech resource key and "
        "matching region. This platform has no verified local voice yet; "
        "playback stops safely if the service fails."
    ),
    "azure_fallback_missing_settings": (
        "Azure Speech is not fully configured; using the Windows female "
        "voice without sending a cloud request."
    ),
    "azure_missing_no_local_fallback": (
        "Azure Speech is not fully configured, and this platform has no "
        "verified local voice. Nothing will be played or sent to the cloud."
    ),
    "no_female_voice": "No verified female Windows voice detected",
    "female_voice_note": (
        "Only installed voices explicitly marked as female are listed. "
        "Voices matching the selected interface language are preferred."
    ),
    "platform_local_voice_note": (
        "{platform} local voice has not completed device verification. "
        "MoHan will not show another platform's voices or claim offline "
        "speech support."
    ),
    "transcription_language_placeholder": (
        "ISO language code; leave blank for automatic detection"
    ),
    "openai_fallback": "Use Windows offline recognition if OpenAI fails",
    "openai_recognition": "OpenAI accurate recognition (recommended)",
    "windows_recognition": "Windows offline recognition",
    "no_transcription_error": "No transcription errors recorded",
    "preview_voice": "Preview: Commander, I am here.",
    "realtime_disconnected": "Realtime: Disconnected",
    "start_realtime": "Start Realtime conversation",
    "stop_realtime": "Stop Realtime conversation",
    "near_field": "Close microphone (recommended)",
    "far_field": "Distant / laptop microphone",
    "noise_off": "Noise reduction off",
    "stable_vad": "Stable complete turns (about 0.85 s pause)",
    "semantic_vad": "Semantic turns (may cut speech early)",
    "echo_guard_option": "Prevent MoHan from hearing her own voice",
    "hybrid_transcript": "Use accurate final transcripts on screen",
    "mute": "Mute",
    "rate_down": "Decrease local speech rate",
    "rate_up": "Increase local speech rate",
    "level_suffix": " level",
    "realtime_note": (
        "Realtime keeps the microphone active only while enabled. Stable turn "
        "detection waits about 0.85 seconds after you stop speaking. Accurate "
        "final transcripts use the selected transcription model; turning "
        "Realtime off stops audio transmission immediately."
    ),
    "model_access_note": (
        "If a model is enabled in the OpenAI dashboard but access still fails, "
        "make sure the model and API key belong to the same Project, then save "
        "the new key in Settings."
    ),
    "echo_guard_note": (
        "With echo guard enabled, microphone upload pauses while MoHan speaks "
        "and resumes after playback. Only the final accurate transcript is "
        "shown in Chat."
    ),
    "recognition_note": (
        "The single-use microphone sends audio after about 0.85 seconds of "
        "silence, up to 10 seconds. Click the microphone again to send early."
    ),
    "recognition_note_no_offline": (
        "Single-use microphone input uses OpenAI accurate recognition. "
        "Offline recognition is hidden until it completes device verification "
        "on this platform."
    ),
    "platform_secret_storage_unavailable": (
        "{platform} secure secret storage has not completed device verification"
    ),
    "platform_autostart_unavailable": (
        "{platform} automatic startup has not completed device verification"
    ),
    "autostart": "Automatic startup",
    "permissions_intro": (
        "Grant each capability separately. With Ask every time, MoHan shows a "
        "confirmation before acting. File deletion is denied by default."
    ),
    "permission_open_web": "Open a specified website",
    "permission_open_folder": "Open the workspace folder",
    "permission_launch_app": "Launch another application",
    "permission_write_files": "Create or modify files",
    "permission_delete_files": "Delete files",
    "permission_deny": "Deny",
    "permission_ask": "Ask every time",
    "permission_allow": "Allow",
    "permissions_warning": (
        "Safety rule: conversation cannot grant MoHan additional authority. "
        "The AI may propose a tool request, but local permissions decide what "
        "can actually run."
    ),
    "save_permissions": "Save tool permissions",
    "permission_blocked": "Permission blocked",
    "permission_blocked_message": "MoHan is not allowed to {action}.",
    "permission_request": "MoHan requests computer permission",
    "permission_request_message": "Allow MoHan to {action} this time?",
    "permission_saved_speech": (
        "Computer permissions saved. I will remain within these boundaries."
    ),
    "profile_heading": "<b>Identity and profile</b>",
    "system_heading": "<b>Work and system settings</b>",
    "api_key": "OpenAI API key",
    "text_model": "Text model",
    "persona_prompt": "AI persona prompt",
    "remove_api_key": "Remove saved API key",
    "save_settings": "Save settings",
    "api_key_saved": "Safely stored; leave blank to keep it unchanged",
    "api_key_missing": "Paste an OpenAI Project API key beginning with sk-",
    "api_status_saved": "OpenAI API: Key encrypted by Windows",
    "api_status_environment": "OpenAI API: Key supplied by an environment variable",
    "api_status_secret_unavailable": (
        "OpenAI API: {platform} secure secret storage has not completed "
        "device verification"
    ),
    "api_status_offline": "OpenAI API: Not configured; using offline persona",
    "restart_language_note": (
        "The interface language will be fully applied after restarting MoHan."
    ),
    "reminder_work": "Start work",
    "reminder_lunch": "Lunch",
    "reminder_dinner": "Dinner",
    "reminder_offwork": "Finish work",
    "enabled": "Enabled",
    "reminder_message_label": "{label} message",
    "reminder_message_placeholder": "What MoHan says when this reminder fires",
    "continuous_work_reminder": "Continuous work reminder",
    "overwork_message": "Sitting / overwork reminder message",
    "minutes_suffix": " minutes",
    "read_replies": "Read MoHan's replies aloud",
    "save_voice_settings": "Save voice settings",
    "voice_settings_saved": "Voice settings saved.",
    "settings_saved": "Settings saved.",
    "work_timer_already_running": (
        "The work timer is already running. There is no need to start it twice."
    ),
    "work_timer_not_started": "Today's work timer has not started yet.",
})

_SIMPLIFIED_CHINESE: Mapping[str, str] = deep_freeze({
    "first_run_title": "首次启动设置",
    "first_run_heading": "<b>欢迎使用墨寒桌面助手</b>",
    "first_run_hero_tagline": (
        "来自北宋的千年女剑魂，陪您说话、记忆，也陪您把工作做好。"
    ),
    "first_run_intro": (
        "请先建立用户设置。以下内容以后都能在“设置”页修改，不会绑定"
        "特定公司、职业或工作平台。"
    ),
    "assistant_name": "助手名称",
    "user_title": "助手对您的称呼",
    "organization_name": "公司／团队名称",
    "window_title": "完整窗口标题",
    "work_type": "工作类型",
    "ui_language": "界面与回复语言",
    "wake_word": "语音唤醒词",
    "assistant_name_placeholder": "例如：墨寒、Ava、Office Mate",
    "user_title_placeholder": "例如：主上、Alex、主管",
    "organization_placeholder": "公司、工作室或团队名称；个人使用可留空",
    "window_title_placeholder": "留空时自动使用“助手名称 · 组织名称”",
    "wake_word_placeholder": "例如：墨寒",
    "first_run_note": (
        "工作平台页初始为空。请只添加您实际使用的公司系统、协作工具、"
        "管理后台或网站。"
    ),
    "finish_setup": "完成设置并开始使用",
    "required_title": "缺少必要信息",
    "required_identity": "请填写助手名称，以及助手对您的称呼。",
    "mode": "模式",
    "start_work": "开始工作",
    "stop_work": "结束工作",
    "tab_chat": "对话",
    "tab_today": "今日待办",
    "tab_platforms": "工作平台",
    "tab_memory": "长期记忆",
    "tab_voice": "语音",
    "tab_permissions": "电脑权限",
    "tab_settings": "设置",
    "chat_retention": "对话保存在本机，不会自动删除",
    "load_older_chat": "加载更早对话",
    "manage_chat": "管理／清除对话",
    "chat_placeholder": "对墨寒说话……",
    "microphone": "🎙 麦克风",
    "send_text": "发送",
    "voice_ready": "语音状态：就绪",
    "speech_recognition": "单次麦克风识别",
    "transcription_model": "转录模型",
    "transcription_language": "转录语言",
    "transcription_prompt": "转录提示词／常用词",
    "windows_transcription_fallback": "Windows 备用识别",
    "offline_fallback": "离线备用识别",
    "platform_offline_fallback_unavailable": (
        "{platform} 离线识别尚未完成设备实测"
    ),
    "last_transcription": "最近转录诊断",
    "voice_engine": "朗读方式",
    "windows_voice": "Windows 本机声音",
    "platform_local_voice": "{platform} 本机声音",
    "platform_local_voice_unavailable": (
        "{platform} 本机语音尚未完成设备实测"
    ),
    "tts_voice": "OpenAI 文字转语音声音",
    "realtime_voice": "Realtime 对话声音",
    "realtime_model": "Realtime 模型",
    "realtime_transcription_model": "Realtime 转录模型",
    "realtime_noise": "Realtime 麦克风降噪",
    "realtime_turn": "Realtime 轮次检测",
    "realtime_screen_transcript": "Realtime 屏幕转录",
    "echo_guard": "回声防护",
    "local_rate": "本机语速",
    "mohan_volume": "墨寒音量",
    "voice_style": "语音风格",
    "realtime": "Realtime 语音",
    "windows_engine": "Windows 本机语音",
    "openai_engine": "OpenAI 自然语音",
    "realtime_engine": "Realtime 即时语音",
    "azure_engine": "Azure Speech（预览）",
    "azure_voice": "Azure Speech 女性声线",
    "azure_region": "Azure Speech 区域",
    "azure_key": "Azure Speech 密钥",
    "azure_region_placeholder": "例如：eastasia",
    "azure_key_saved": "已由 Windows 加密保存；留空即可保留",
    "azure_key_missing": "贴上 Azure Speech 资源密钥",
    "azure_remove_key": "移除 Azure Speech 密钥",
    "azure_remove_key_confirm": (
        "确定移除由 Windows 加密保存的 Azure Speech 密钥吗？"
    ),
    "azure_key_save_failed": "无法安全保存 Azure Speech 密钥：{error}",
    "azure_speech_note": (
        "预览功能；需自备 Azure Speech 资源密钥与相符区域。仅列出已确认的"
        "女性声线；设定不完整或服务失败时会立即切换到 Windows 女性语音。"
        "Azure 用量与费用以 Microsoft 官方规则为准。"
    ),
    "azure_speech_note_no_local_fallback": (
        "预览功能；需自备 Azure Speech 资源密钥与相符区域。此平台尚无已验证的"
        "本机语音，服务失败时会安全停止播放。"
    ),
    "azure_fallback_missing_settings": (
        "Azure Speech 尚未完成设定；已直接使用 Windows 女性语音，未发送云端请求。"
    ),
    "azure_missing_no_local_fallback": (
        "Azure Speech 尚未完成设置，且此平台没有已验证的本机语音；"
        "本次不会播放，也不会发送云端请求。"
    ),
    "no_female_voice": "未检测到已确认的女性 Windows 声音",
    "female_voice_note": (
        "只显示 Windows 明确标示为女性的已安装声音，并优先选择与界面"
        "语言相符的声音。"
    ),
    "platform_local_voice_note": (
        "{platform} 本机语音尚未完成设备实测；在完成前不会显示其他平台的"
        "声音，也不会宣称支持离线朗读。"
    ),
    "transcription_language_placeholder": "ISO 语言代码；留空则自动检测",
    "openai_fallback": "OpenAI 失败时使用 Windows 离线识别",
    "openai_recognition": "OpenAI 高准确度识别（推荐）",
    "windows_recognition": "Windows 离线识别",
    "no_transcription_error": "没有转录错误记录",
    "preview_voice": "试听：主上，妾在。",
    "realtime_disconnected": "Realtime：未连接",
    "start_realtime": "启动 Realtime 自然对话",
    "stop_realtime": "停止 Realtime 自然对话",
    "near_field": "近距离麦克风（推荐）",
    "far_field": "远距离／笔记本麦克风",
    "noise_off": "关闭降噪",
    "stable_vad": "稳定完整句（停顿约 0.85 秒）",
    "semantic_vad": "语义轮次（可能提前截断）",
    "echo_guard_option": "防止墨寒听见自己的声音",
    "hybrid_transcript": "屏幕使用高准确度最终转录",
    "mute": "静音",
    "rate_down": "降低本机语速",
    "rate_up": "提高本机语速",
    "level_suffix": " 级",
    "realtime_note": (
        "Realtime 只在启用期间保持麦克风开启。稳定轮次会在您停止说话约 "
        "0.85 秒后送出；关闭 Realtime 会立即停止传送音频。"
    ),
    "model_access_note": (
        "若 OpenAI 控制台已经启用模型却仍无法访问，请确认模型与 API Key "
        "属于同一个 Project，再到设置页保存新密钥。"
    ),
    "echo_guard_note": (
        "启用回声防护后，墨寒说话时会暂停上传麦克风音频，播放结束后再"
        "恢复。对话页只显示最终准确转录。"
    ),
    "recognition_note": (
        "单次麦克风会在约 0.85 秒静音后送出音频，最长录制 10 秒；再次"
        "点击麦克风可提前送出。"
    ),
    "recognition_note_no_offline": (
        "单次麦克风使用 OpenAI 高准确度识别；此平台的离线识别尚未完成"
        "设备实测，因此暂不显示离线备用识别。"
    ),
    "platform_secret_storage_unavailable": (
        "{platform} 安全密钥保存尚未完成设备实测"
    ),
    "platform_autostart_unavailable": (
        "{platform} 自动启动尚未完成设备实测"
    ),
    "autostart": "自动启动",
    "permissions_intro": (
        "请分别授权每项能力。选择“每次询问”时，墨寒会在执行前请求确认；"
        "删除文件默认禁止。"
    ),
    "permission_open_web": "打开指定网站",
    "permission_open_folder": "打开工作文件夹",
    "permission_launch_app": "启动其他应用程序",
    "permission_write_files": "建立或修改文件",
    "permission_delete_files": "删除文件",
    "permission_deny": "禁止",
    "permission_ask": "每次询问",
    "permission_allow": "允许",
    "permissions_warning": (
        "安全规则：对话内容不能扩大墨寒的权限。AI 可以提出工具请求，"
        "但实际能否执行只由本机权限设置决定。"
    ),
    "save_permissions": "保存工具权限",
    "permission_blocked": "权限已阻止",
    "permission_blocked_message": "墨寒目前无权{action}。",
    "permission_request": "墨寒请求电脑权限",
    "permission_request_message": "是否允许墨寒本次{action}？",
    "permission_saved_speech": "电脑权限已保存。妾会守住这些边界。",
    "profile_heading": "<b>身份与用户设置</b>",
    "system_heading": "<b>工作与系统设置</b>",
    "api_key": "OpenAI API 密钥",
    "text_model": "文字模型",
    "persona_prompt": "AI 人格提示词",
    "remove_api_key": "删除已保存的 API 密钥",
    "save_settings": "保存设置",
    "api_key_saved": "已安全保存；留空则保持不变",
    "api_key_missing": "粘贴以 sk- 开头的 OpenAI Project API Key",
    "api_status_saved": "OpenAI API：密钥已由 Windows 加密保存",
    "api_status_environment": "OpenAI API：使用环境变量提供的密钥",
    "api_status_secret_unavailable": (
        "OpenAI API：{platform} 安全密钥保存尚未完成设备实测"
    ),
    "api_status_offline": "OpenAI API：未设置，使用离线人格",
    "restart_language_note": "保存界面语言后，重新启动墨寒即可完整应用。",
    "reminder_work": "开始工作",
    "reminder_lunch": "午餐",
    "reminder_dinner": "晚餐",
    "reminder_offwork": "下班",
    "enabled": "启用",
    "reminder_message_label": "{label}消息",
    "reminder_message_placeholder": "此提醒触发时墨寒要说的内容",
    "continuous_work_reminder": "连续工作提醒",
    "overwork_message": "久坐／过劳提醒消息",
    "minutes_suffix": " 分钟",
    "read_replies": "让墨寒读出回复",
    "save_voice_settings": "保存语音设置",
    "voice_settings_saved": "语音设置已保存。",
    "settings_saved": "设置已保存。",
    "work_timer_already_running": "计时仍在进行，不必重复开始。",
    "work_timer_not_started": "今日尚未开始计时。",
})


MODE_LABELS: Mapping[str, str] = frozendict({
    "工作": "Work",
    "陪伴": "Companion",
    "勿擾": "Do not disturb",
    "會議": "Meeting",
    "離席": "Away",
    "休眠": "Sleep",
})

WORK_TYPE_LABELS: Mapping[str, str] = frozendict({
    "一般辦公／行政": "General office / administration",
    "專案管理": "Project management",
    "自由工作者／接案": "Freelance / contract work",
    "創作／內容工作": "Creative / content work",
    "軟體開發／技術": "Software development / technology",
    "教育／研究": "Education / research",
    "銷售／客戶服務": "Sales / customer service",
    "其他（可自行輸入）": "Other (enter your own)",
})

SIMPLIFIED_MODE_LABELS: Mapping[str, str] = frozendict({
    "工作": "工作",
    "陪伴": "陪伴",
    "勿擾": "勿扰",
    "會議": "会议",
    "離席": "离席",
    "休眠": "休眠",
})

SIMPLIFIED_WORK_TYPE_LABELS: Mapping[str, str] = frozendict({
    "一般辦公／行政": "一般办公／行政",
    "專案管理": "项目管理",
    "自由工作者／接案": "自由职业／承接项目",
    "創作／內容工作": "创作／内容工作",
    "軟體開發／技術": "软件开发／技术",
    "教育／研究": "教育／研究",
    "銷售／客戶服務": "销售／客户服务",
    "其他（可自行輸入）": "其他（可自行输入）",
})


def ui_text(language: str, key: str, chinese: str, **values: object) -> str:
    if is_english(language):
        text = _ENGLISH.get(key, chinese)
    elif is_simplified_chinese(language):
        text = _SIMPLIFIED_CHINESE.get(key, chinese)
    elif is_japanese(language):
        text = JAPANESE_UI.get(key, chinese)
    else:
        text = chinese
    return text.format(**values) if values else text


def display_label(
    language: str,
    value: str,
    english: Mapping[str, str],
    simplified: Mapping[str, str] | None = None,
    japanese: Mapping[str, str] | None = None,
) -> str:
    if is_english(language):
        return english.get(value, value)
    if is_simplified_chinese(language) and simplified is not None:
        return simplified.get(value, value)
    if is_japanese(language) and japanese is not None:
        return japanese.get(value, value)
    return value
