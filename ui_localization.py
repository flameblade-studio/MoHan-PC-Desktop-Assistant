from __future__ import annotations

from collections.abc import Mapping

from language_support import is_english



_ENGLISH: Mapping[str, str] = {
    "first_run_title": "First-run setup",
    "first_run_heading": "<b>Welcome to MoHan Desktop Assistant</b>",
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
    "last_transcription": "Latest transcription diagnostic",
    "voice_engine": "Speech method",
    "windows_voice": "Windows voice",
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
    "no_female_voice": "No verified female Windows voice detected",
    "female_voice_note": (
        "Only installed voices explicitly marked as female are listed. "
        "Voices matching the selected interface language are preferred."
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
    "voice_settings_saved": "Voice settings saved.",
    "settings_saved": "Settings saved.",
    "work_timer_already_running": (
        "The work timer is already running. There is no need to start it twice."
    ),
    "work_timer_not_started": "Today's work timer has not started yet.",
}


MODE_LABELS: Mapping[str, str] = {
    "工作": "Work",
    "陪伴": "Companion",
    "勿擾": "Do not disturb",
    "會議": "Meeting",
    "離席": "Away",
    "休眠": "Sleep",
}

WORK_TYPE_LABELS: Mapping[str, str] = {
    "一般辦公／行政": "General office / administration",
    "專案管理": "Project management",
    "自由工作者／接案": "Freelance / contract work",
    "創作／內容工作": "Creative / content work",
    "軟體開發／技術": "Software development / technology",
    "教育／研究": "Education / research",
    "銷售／客戶服務": "Sales / customer service",
    "其他（可自行輸入）": "Other (enter your own)",
}


def ui_text(language: str, key: str, chinese: str, **values: object) -> str:
    text = _ENGLISH.get(key, chinese) if is_english(language) else chinese
    return text.format(**values) if values else text


def display_label(language: str, value: str, english: Mapping[str, str]) -> str:
    return english.get(value, value) if is_english(language) else value
