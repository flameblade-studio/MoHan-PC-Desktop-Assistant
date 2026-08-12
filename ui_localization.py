from __future__ import annotations

lazy from collections.abc import Mapping

lazy from immutable_config import deep_freeze
lazy from language_support import is_english, is_japanese, is_simplified_chinese
lazy from ui_localization_ja import JAPANESE_UI

_ENGLISH: Mapping[str, str] = deep_freeze({
    "first_run_title": "First-run setup",
    "first_run_brand": "MoHan",
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
    "today_input_placeholder": (
        "Enter a task, for example: Finish the storyboard for chapter 3"
    ),
    "todo_category_comic": "Comic",
    "todo_category_article": "Article",
    "todo_category_music": "Music",
    "todo_category_stickers": "Stickers",
    "todo_category_publishing": "Publishing",
    "todo_category_administration": "Administration",
    "todo_category_other": "Other",
    "add_todo": "＋ Add task",
    "save_as_idea": "✦ Save idea",
    "today_tasks_heading": "<b>Tasks for today</b>",
    "creative_ideas_heading": "<b>Creative ideas</b>",
    "edit_selected_idea": "Edit selected idea",
    "edit_selected_idea_tooltip": (
        "You can also double-click an idea below"
    ),
    "delete_checked_ideas": "Delete checked ideas",
    "delete_checked_ideas_tooltip": (
        "Deletes only checked ideas and asks for confirmation first"
    ),
    "todo_complete_tooltip": "Mark as completed",
    "todo_category_suffix": "Task for today",
    "delete": "Delete",
    "delete_todo_tooltip": "Delete this task",
    "idea_editor_title": "Edit creative idea",
    "idea_title": "<b>Idea title</b>",
    "idea_title_placeholder": "Give this idea a clear title",
    "idea_content": "<b>Idea details</b>",
    "idea_content_placeholder": (
        "Record the scene, dialogue, music direction, or next action…"
    ),
    "cancel": "Cancel",
    "save_idea": "Save idea",
    "idea_title_required_title": "Title required",
    "idea_title_required": "Enter an idea title first.",
    "todo_count": "{count} open",
    "todo_empty": (
        "No tasks yet today.\nWrite down the one thing that matters most."
    ),
    "idea_count": "{count} saved",
    "idea_empty": (
        "No ideas saved yet. Enter text above and choose “Save idea”."
    ),
    "idea_edit_tooltip": "Double-click to edit the title and details",
    "today_time": "Today {total} | {state}",
    "timing_active": "Timing",
    "timing_inactive": "Not timing",
    "todo_title_required": "Enter a task title first.",
    "todo_added": "✓ Task added: {text}",
    "todo_added_speech": "Added to today's tasks.",
    "idea_capture_required": "Enter an idea to save first.",
    "idea_added": "✓ Idea saved: {text}",
    "idea_added_speech": "I saved that idea before it slipped away.",
    "idea_select_edit": "Select an idea to edit first.",
    "idea_not_found": (
        "That idea could not be found. Refresh and try again."
    ),
    "idea_updated": "✓ Idea updated: {title}",
    "idea_select_delete": "Check one or more ideas to delete first.",
    "idea_delete_title": "Delete creative ideas",
    "idea_delete_confirm": "Permanently delete the {count} checked ideas?",
    "idea_deleted": "✓ Deleted {count} ideas.",
    "platform_name_placeholder": (
        "Platform, system, or tool name, for example: ERP, Notion, client portal"
    ),
    "platform_url_placeholder": "URL (optional, for example: https://example.com)",
    "add_platform": "Add work platform",
    "platform_filter_all": "All platforms",
    "platform_filter_active": "In progress",
    "platform_filter_blocked": "Missing information / blocked",
    "platform_filter_finished": "Completed / published",
    "platform_filter_not_started": "Not started",
    "save_all_platforms": "Save all now",
    "show": "Show",
    "platform_empty": (
        "No work platforms yet.\nAdd a company system, collaboration tool, "
        "client portal, or any platform you use above."
    ),
    "platform_intro": (
        "Manage the platforms, systems, client portals, and collaboration "
        "tools you use. Each user creates their own list; no industry is assumed."
    ),
    "platform_auto_save_note": (
        "Changes save automatically. You can also use each card's Save button."
    ),
    "platform_item_placeholder": "Current task, project, or case",
    "platform_missing_placeholder": (
        "Missing information, pending replies, or blockers; leave blank if none"
    ),
    "platform_next_placeholder": "Next concrete action and deadline",
    "platform_notes_placeholder": "Notes, rules, contacts, or other details",
    "platform_url_card_placeholder": "https://… (optional)",
    "platform_not_saved": "Not saved",
    "save_platform": "Save platform",
    "platform_field_item": "Task / project",
    "platform_field_missing": "Missing / blocked",
    "platform_field_next": "Next action",
    "platform_field_notes": "Notes",
    "platform_field_url": "URL",
    "open_platform": "Open website / tool",
    "delete_platform": "Delete platform",
    "platform_updated": "Updated: {updated}",
    "platform_updated_unknown": "Update time unknown",
    "save_changes": "Save changes",
    "platform_waiting_auto_save": "{platform} changed; waiting to auto-save…",
    "platform_validation_finished_blocked": (
        "This work is completed but still lists missing information or blockers."
    ),
    "platform_validation_revision_details": (
        "Describe the needed revision under Missing, Next action, or Notes."
    ),
    "platform_validation_not_started_data": (
        "This card already has work details. Consider changing its status to "
        "Preparing materials."
    ),
    "platform_validation_item_name": (
        "Add a task, project, or case name so it is easy to identify later."
    ),
    "platform_summary_unsaved": " | Unsaved {count}",
    "platform_summary": (
        "{total} platforms | Completed {finished} | In progress {active} | "
        "Not started {not_started} | Missing / blocked {blocked}{unsaved}"
    ),
    "platform_saved": "{platform} saved.",
    "platform_saved_automatic": "{platform} saved automatically.",
    "all_platforms_saved": (
        "All work platforms saved; {count} still list missing information or blockers."
    ),
    "all_platforms_saved_speech": (
        "Work platforms saved. {count} still have missing information or blockers."
    ),
    "memory_intro": (
        "MoHan stores only people, preferences, goals, workflows, and important "
        "dates that you allow. Memories stay on this computer and can be "
        "browsed by category, edited individually, or deleted."
    ),
    "memory_input_placeholder": (
        "For example: Finish the comic before administrative work"
    ),
    "remember": "Remember this",
    "memory_filter_label": "Browse by category",
    "all_memories": "All memories",
    "edit_selected_memory": "Edit selected memory",
    "edit_memory_tooltip": "You can also double-click a memory below",
    "delete_checked_memories": "Delete checked memories",
    "delete_checked_memories_tooltip": (
        "Deletes only checked memories and asks for confirmation first"
    ),
    "clear_all_memories": "Clear all memories",
    "optimize_memories": "Safely organize memories",
    "optimize_memories_tooltip": (
        "Merges low-importance duplicates and archives older overflow first"
    ),
    "view_archived_memories": "View archived memories",
    "auto_memory": (
        "Create memories from explicit phrases such as “remember this”, "
        "“I like”, or “I usually”"
    ),
    "memory_count": "{count} saved",
    "memory_empty": "There are no memories in this category.",
    "memory_source_manual_short": "Manual",
    "memory_source_conversation_short": "Conversation",
    "memory_untitled": "Untitled memory",
    "memory_item": (
        "[{category}] {title}  Importance {importance}/5\n{content}\n"
        "Source: {source}  Updated: {updated}"
    ),
    "memory_added_speech": (
        "I saved that. You can review or change it individually later."
    ),
    "memory_select_edit_title": "No memory selected",
    "memory_select_edit": "Select a memory to edit first.",
    "memory_not_found_title": "Memory not found",
    "memory_not_found": (
        "That memory no longer exists. The list will be refreshed."
    ),
    "memory_save_failed_title": "Memory could not be saved",
    "memory_save_failed": (
        "An identical memory may already exist. Existing data was not changed."
    ),
    "memory_select_delete_title": "No memories checked",
    "memory_select_delete": "Check one or more memories to delete first.",
    "memory_delete_title": "Delete long-term memories",
    "memory_delete_confirm": (
        "Permanently delete the {count} checked memories?"
    ),
    "memory_clear_title": "Clear long-term memory",
    "memory_clear_confirm": (
        "Delete every long-term memory stored by MoHan? This cannot be undone."
    ),
    "memory_optimize_title": "Memory organization complete",
    "memory_optimize_result": (
        "Merged {deduplicated} similar memories and archived {pruned} older, "
        "low-importance memories.\nActive: {active}; archived and restorable: "
        "{archived}."
    ),
    "memory_editor_title": "Edit long-term memory",
    "memory_title_label": "<b>Memory title</b>",
    "memory_title_placeholder": "Use a short title to identify this memory",
    "memory_category_label": "<b>Category</b>",
    "memory_importance_label": "<b>Importance</b>",
    "memory_content_label": "<b>Memory details</b>",
    "memory_content_placeholder": (
        "Record the person, preference, goal, workflow, or important date…"
    ),
    "memory_source_manual": "Created manually",
    "memory_source_conversation": "Explicitly remembered from a conversation",
    "memory_metadata": (
        "Source: {source}  Created: {created}  Updated: {updated}"
    ),
    "save_memory": "Save memory",
    "memory_title_required_title": "Title required",
    "memory_title_required": "Enter a memory title first.",
    "memory_content_required_title": "Details required",
    "memory_content_required": "Enter the memory details first.",
    "archived_memory_title": "Archived long-term memories",
    "archived_memory_intro": (
        "Automatic organization only archives older, low-importance "
        "conversation memories; it does not destroy them. Check any item here "
        "to restore it."
    ),
    "restore_checked_memories": "Restore checked memories",
    "close": "Close",
    "archived_memory_item": (
        "[{category}] {title}\n{content}\nArchive reason: {reason}  "
        "Archived: {archived}"
    ),
    "archived_memory_count": "{count} memories can be restored",
    "archived_memory_select_title": "No memories checked",
    "archived_memory_select": "Check one or more memories to restore first.",
    "archived_memory_restored": "Restored {count} memories.",
    "chat_history_title": "Manage / clear chats",
    "chat_history_intro": (
        "Chats stay on this computer and are not deleted automatically. Check "
        "only the entries you are certain you want to delete permanently."
    ),
    "delete_checked_chats": "Delete checked chats",
    "chat_history_item": "{created} | {speaker}\n{content}",
    "chat_history_truncated_suffix": (
        " (This window shows only the 500 most recent entries.)"
    ),
    "chat_history_status": "{count} chats are stored on this computer.{suffix}",
    "chat_select_delete_title": "No chats checked",
    "chat_select_delete": "Check one or more chats to delete first.",
    "chat_delete_title": "Permanently delete chats",
    "chat_delete_confirm": "Permanently delete the {count} checked chats?",
    "load_older_chat_tooltip": "Load 50 earlier chats from this computer",
    "manage_chat_tooltip": (
        "Select and delete specific chats without affecting the others"
    ),
    "chat_zoom_out_tooltip": "Make chat text smaller (Ctrl + wheel down)",
    "chat_zoom_in_tooltip": "Make chat text larger (Ctrl + wheel up)",
    "chat_retention_status": (
        "{total} chats stored locally; showing the most recent {shown}"
    ),
    "platform_name_required": "Enter a platform, system, or tool name first.",
    "platform_duplicate": "“{platform}” already exists. Use a different name.",
    "platform_added": "Work platform added: {platform}",
    "platform_delete_title": "Delete work platform",
    "platform_delete_confirm": (
        "Delete “{platform}” and its work progress? This cannot be undone."
    ),
    "platform_not_found": "Work platform not found: {platform}",
    "platform_deleted": "Work platform deleted: {platform}",
    "platform_url_missing_title": "URL not set",
    "platform_url_missing": (
        "Enter the website or tool URL on the “{platform}” card first."
    ),
    "platform_url_unsupported_title": "Unsupported URL format",
    "platform_url_unsupported": "Only http:// or https:// URLs can be opened.",
    "permission_open_platform": "open the {platform} website",
    "echo_guard_tooltip": (
        "Pauses microphone upload while MoHan speaks and resumes after playback; "
        "you cannot interrupt while this option is enabled."
    ),
    "hybrid_transcript_tooltip": (
        "Realtime keeps native audio understanding. After each utterance, the "
        "screen text uses a high-accuracy OpenAI transcription of the complete "
        "recording, and MoHan replies only after it succeeds."
    ),
    "flagship_heading": "<b>Flagship control center</b>",
    "increase": "Increase",
    "decrease": "Decrease",
    "voice_section": "Voice",
    "profile_required_title": "Required profile details missing",
    "profile_required": (
        "Assistant name and how the assistant addresses you cannot be blank."
    ),
    "send_chat_required_title": "No message entered",
    "send_chat_required": (
        "Enter text on the left and choose Send; you can also use the microphone."
    ),
    "thinking_status": "{assistant} is thinking…",
    "answering_status": "Answering…",
    "api_connection_failed": "OpenAI API: connection failed ({error})",
    "voice_ready_short": "Ready",
    "microphone_idle": "🎙 Microphone",
    "microphone_send_now": "⏹ Send now",
    "microphone_recognizing": "Recognizing…",
    "voice_status_format": "Voice status: {phase}",
    "bubble_full_content": "…\n(See the Chat page for the complete message.)",
    "tray_open_today": "Open Today",
    "tray_quit": "Quit MoHan",
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
    "realtime_output_source": "Realtime response voice source",
    "realtime_output_openai": (
        "Native OpenAI Realtime voice (lowest latency, existing default)"
    ),
    "realtime_output_azure": "Azure Speech female voice (gentle streaming)",
    "realtime_output_azure_hd": (
        "Azure Dragon HD female voice (requires S0)"
    ),
    "realtime_output_note_openai": (
        "Uses the OpenAI Realtime native voice below. This is the lowest-"
        "latency option and preserves native OpenAI Realtime speech output."
    ),
    "realtime_output_note_azure": (
        "Uses the Azure Speech female voice, region, and key configured above. "
        "OpenAI Realtime handles live understanding while Azure streams the "
        "spoken response."
    ),
    "realtime_output_note_azure_hd": (
        "Uses the Dragon HD female voice, S0 region, and separate key "
        "configured above. OpenAI Realtime handles live understanding while "
        "Dragon HD streams the spoken response."
    ),
    "realtime_voice": "Native OpenAI Realtime voice",
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
    "azure_hd_engine": "Azure Dragon HD (Preview, requires S0)",
    "azure_voice": "Azure Speech female voice",
    "azure_region": "Azure Speech region",
    "azure_key": "Azure Speech key",
    "azure_region_choose": "Choose the region where the Azure resource was created",
    "azure_region_saved": "Existing setting · {region}",
    "azure_key_saved": "Encrypted by Windows; leave blank to keep it",
    "azure_key_missing": "Paste the Azure Speech resource key",
    "azure_remove_key": "Remove Azure Speech key",
    "azure_remove_key_confirm": (
        "Remove the Azure Speech key encrypted by Windows?"
    ),
    "azure_key_save_failed": (
        "Could not securely save the Azure Speech key: {error}"
    ),
    "azure_hd_voice": "Dragon HD female voice",
    "azure_hd_region": "Dragon HD resource region",
    "azure_hd_key": "Dragon HD S0 resource key",
    "azure_hd_key_saved": "Dragon HD S0 key encrypted by Windows; leave blank to keep it",
    "azure_hd_key_missing": "Paste the separate Dragon HD S0 resource key",
    "azure_hd_remove_key": "Remove Dragon HD S0 key",
    "azure_hd_remove_key_confirm": (
        "Remove the Dragon HD S0 key securely stored by {platform}?"
    ),
    "azure_hd_key_save_failed": (
        "Could not securely save the Dragon HD S0 key: {error}"
    ),
    "azure_hd_speech_note": (
        "Optional Preview. Use a separate S0 Speech resource, key, and "
        "matching supported region. Dragon HD has no viseme events, so "
        "MoHan retains audio-driven lip sync. Speech-start delay depends on "
        "network and region distance. Failures fall back once each to "
        "standard Azure Speech and then Windows local speech."
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
    "realtime_status_format": "Realtime: {status}",
    "realtime_disconnected_status": "Disconnected",
    "realtime_error_status": "Error: {error}",
    "realtime_voice_title": "Realtime voice",
    "realtime_output_unavailable": (
        "Realtime Azure speech output is unavailable, so the live "
        "conversation was not started."
    ),
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
    "remove_api_key_confirm": (
        "Remove the OpenAI API key stored securely by {platform}?"
    ),
    "save_settings": "Save settings",
    "api_key_saved": "Safely stored; leave blank to keep it unchanged",
    "api_key_missing": "Paste an OpenAI Project API key beginning with sk-",
    "api_key_save_failed": "Could not store the OpenAI API key securely: {error}",
    "secret_auto_save_hint": (
        "Press Enter or leave the field to store the key securely and automatically."
    ),
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
    "voice_settings_saved": "Voice settings saved.",
    "settings_saved": "Settings saved.",
    "work_timer_already_running": (
        "The work timer is already running. There is no need to start it twice."
    ),
    "work_timer_not_started": "Today's work timer has not started yet.",
})

_SIMPLIFIED_CHINESE: Mapping[str, str] = deep_freeze({
    "first_run_title": "首次启动设置",
    "first_run_brand": "墨寒  MoHan",
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
    "today_input_placeholder": (
        "输入待办标题，例如：完成漫画第 3 话分镜"
    ),
    "todo_category_comic": "漫画",
    "todo_category_article": "文章",
    "todo_category_music": "音乐",
    "todo_category_stickers": "贴图",
    "todo_category_publishing": "出版",
    "todo_category_administration": "行政",
    "todo_category_other": "其他",
    "add_todo": "＋ 添加待办",
    "save_as_idea": "✦ 保存灵感",
    "today_tasks_heading": "<b>今天要做</b>",
    "creative_ideas_heading": "<b>创作灵感</b>",
    "edit_selected_idea": "编辑选中灵感",
    "edit_selected_idea_tooltip": "也可以双击下方任一灵感",
    "delete_checked_ideas": "删除勾选灵感",
    "delete_checked_ideas_tooltip": "只删除已勾选的灵感，执行前会再次确认",
    "todo_complete_tooltip": "标记为已完成",
    "todo_category_suffix": "今日待办",
    "delete": "删除",
    "delete_todo_tooltip": "删除这项待办",
    "idea_editor_title": "编辑创作灵感",
    "idea_title": "<b>灵感标题</b>",
    "idea_title_placeholder": "为这则灵感填写清楚的标题",
    "idea_content": "<b>灵感内容</b>",
    "idea_content_placeholder": (
        "记录情节、画面、对白、音乐方向或后续可执行的想法……"
    ),
    "cancel": "取消",
    "save_idea": "保存灵感",
    "idea_title_required_title": "缺少标题",
    "idea_title_required": "请先填写灵感标题。",
    "todo_count": "{count} 项未完成",
    "todo_empty": "今日待办尚空。\n请先写下一件真正重要的事。",
    "idea_count": "{count} 则",
    "idea_empty": (
        "尚无灵感记录；输入上方文字后点击“保存灵感”。"
    ),
    "idea_edit_tooltip": "双击打开并编辑标题与内容",
    "today_time": "今日 {total}｜{state}",
    "timing_active": "计时中",
    "timing_inactive": "未计时",
    "todo_title_required": "请先输入待办标题。",
    "todo_added": "✓ 已添加待办：{text}",
    "todo_added_speech": "已收入今日待办。",
    "idea_capture_required": "请先输入要保存的灵感。",
    "idea_added": "✓ 已保存灵感：{text}",
    "idea_added_speech": "灵感稍纵即逝，妾已替您收好。",
    "idea_select_edit": "请先选择一则要编辑的灵感。",
    "idea_not_found": "找不到这则灵感，请刷新后再试。",
    "idea_updated": "✓ 已更新灵感：{title}",
    "idea_select_delete": "请先勾选要删除的灵感。",
    "idea_delete_title": "删除创作灵感",
    "idea_delete_confirm": "确定永久删除勾选的 {count} 则灵感吗？",
    "idea_deleted": "✓ 已删除 {count} 则灵感。",
    "platform_name_placeholder": "平台、系统或工具名称，例如：公司 ERP、Notion、客户后台",
    "platform_url_placeholder": "网址（可留空，例如：https://example.com）",
    "add_platform": "添加工作平台",
    "platform_filter_all": "全部平台",
    "platform_filter_active": "进行中",
    "platform_filter_blocked": "待补资料／受阻",
    "platform_filter_finished": "已完成／已发布",
    "platform_filter_not_started": "尚未开始",
    "save_all_platforms": "立即保存全部",
    "show": "显示",
    "platform_empty": (
        "尚未建立工作平台。\n请在上方输入公司系统、协作工具、客户后台或任何工作平台。"
    ),
    "platform_intro": (
        "集中管理工作中使用的平台、系统、客户入口或协作工具。"
        "每位用户都可以建立自己的工作平台，不预设绑定任何行业。"
    ),
    "platform_auto_save_note": "修改后会自动保存；也可以使用每张卡片的保存按钮。",
    "platform_item_placeholder": "当前负责的工作事项、项目或案件",
    "platform_missing_placeholder": "待补资料、等待他人回复或其他阻碍；没有可留空",
    "platform_next_placeholder": "下一个具体动作与期限",
    "platform_notes_placeholder": "备注、规则、联系窗口或其他补充",
    "platform_url_card_placeholder": "https://…（可留空）",
    "platform_not_saved": "尚未保存",
    "save_platform": "保存此平台",
    "platform_field_item": "工作事项／项目",
    "platform_field_missing": "待补资料／阻碍",
    "platform_field_next": "下一步",
    "platform_field_notes": "备注",
    "platform_field_url": "网址",
    "open_platform": "打开网站／工具",
    "delete_platform": "删除平台",
    "platform_updated": "更新：{updated}",
    "platform_updated_unknown": "更新时间未知",
    "save_changes": "保存修改",
    "platform_waiting_auto_save": "{platform} 有修改，正在等待自动保存……",
    "platform_validation_finished_blocked": "注意：工作已完成，但仍列有待补资料或阻碍。",
    "platform_validation_revision_details": "请在待补资料／阻碍、下一步或备注中写明需修改的内容。",
    "platform_validation_not_started_data": "已有工作资料，请确认状态是否应改为“准备资料”。",
    "platform_validation_item_name": "建议填写工作事项、项目或案件名称，日后较容易辨认。",
    "platform_summary_unsaved": "｜未保存 {count}",
    "platform_summary": (
        "{total} 个平台｜已完成 {finished}｜进行中 {active}｜"
        "尚未开始 {not_started}｜待补／阻碍 {blocked}{unsaved}"
    ),
    "platform_saved": "{platform} 已保存。",
    "platform_saved_automatic": "{platform} 已自动保存。",
    "all_platforms_saved": "全部工作平台已保存；{count} 个平台仍列有待补资料或阻碍。",
    "all_platforms_saved_speech": "工作平台已保存。仍有 {count} 个平台标有待补资料或阻碍。",
    "memory_intro": (
        "墨寒只保存您允许留下的人物、偏好、目标、工作流程与重要日期。"
        "记忆保存在本机，可按分类浏览、逐项编辑或删除。"
    ),
    "memory_input_placeholder": "例如：先完成漫画，再处理行政工作",
    "remember": "让墨寒记住",
    "memory_filter_label": "分类浏览",
    "all_memories": "全部记忆",
    "edit_selected_memory": "编辑选中记忆",
    "edit_memory_tooltip": "也可以双击下方任一记忆",
    "delete_checked_memories": "删除勾选记忆",
    "delete_checked_memories_tooltip": "只删除已勾选的记忆，执行前会再次确认",
    "clear_all_memories": "清除全部记忆",
    "optimize_memories": "安全整理记忆",
    "optimize_memories_tooltip": "合并低重要度重复内容，超量旧记忆只会先封存",
    "view_archived_memories": "查看已封存记忆",
    "auto_memory": "从“请记住／我喜欢／我习惯”等明确说法自动建立记忆",
    "memory_count": "{count} 则",
    "memory_empty": "这个分类目前没有记忆。",
    "memory_source_manual_short": "手动",
    "memory_source_conversation_short": "对话",
    "memory_untitled": "未命名记忆",
    "memory_item": (
        "【{category}】{title}　重要度 {importance}／5\n{content}\n"
        "来源：{source}　更新：{updated}"
    ),
    "memory_added_speech": "妾已记下。您日后若要更改，也可逐项整理。",
    "memory_select_edit_title": "尚未选中",
    "memory_select_edit": "请先选择一则要编辑的记忆。",
    "memory_not_found_title": "找不到记忆",
    "memory_not_found": "这则记忆已不存在，列表将重新整理。",
    "memory_save_failed_title": "无法保存记忆",
    "memory_save_failed": "可能已有内容完全相同的记忆。原有数据未被更改。",
    "memory_select_delete_title": "尚未勾选",
    "memory_select_delete": "请先勾选要删除的记忆。",
    "memory_delete_title": "删除长期记忆",
    "memory_delete_confirm": "确定永久删除勾选的 {count} 则记忆吗？",
    "memory_clear_title": "清除长期记忆",
    "memory_clear_confirm": "确定删除墨寒保存的全部长期记忆吗？此操作无法恢复。",
    "memory_optimize_title": "记忆整理完成",
    "memory_optimize_result": (
        "合并 {deduplicated} 则近似记忆，封存 {pruned} 则较旧低重要度记忆。\n"
        "目前使用中 {active} 则；可恢复封存 {archived} 则。"
    ),
    "memory_editor_title": "编辑长期记忆",
    "memory_title_label": "<b>记忆标题</b>",
    "memory_title_placeholder": "用一句短标题识别这则记忆",
    "memory_category_label": "<b>分类</b>",
    "memory_importance_label": "<b>重要度</b>",
    "memory_content_label": "<b>记忆内容</b>",
    "memory_content_placeholder": "完整记录人物背景、偏好、目标、工作流程或重要日期……",
    "memory_source_manual": "手动建立",
    "memory_source_conversation": "由对话明确记住",
    "memory_metadata": "来源：{source}　建立：{created}　更新：{updated}",
    "save_memory": "保存记忆",
    "memory_title_required_title": "尚无标题",
    "memory_title_required": "请先填写记忆标题。",
    "memory_content_required_title": "尚无内容",
    "memory_content_required": "请先填写记忆内容。",
    "archived_memory_title": "已封存的长期记忆",
    "archived_memory_intro": (
        "自动整理只会封存较旧、低重要度的对话记忆，不会直接销毁。"
        "您可以在这里随时勾选恢复。"
    ),
    "restore_checked_memories": "恢复勾选记忆",
    "close": "关闭",
    "archived_memory_item": (
        "【{category}】{title}\n{content}\n封存原因：{reason}　时间：{archived}"
    ),
    "archived_memory_count": "目前共有 {count} 则可恢复记忆",
    "archived_memory_select_title": "尚未选中",
    "archived_memory_select": "请先勾选要恢复的记忆。",
    "archived_memory_restored": "已恢复 {count} 则记忆。",
    "chat_history_title": "管理／清除对话",
    "chat_history_intro": (
        "对话平时保存在本机，不会自动删除。请只勾选确定要永久删除的记录。"
    ),
    "delete_checked_chats": "删除勾选对话",
    "chat_history_item": "{created}｜{speaker}\n{content}",
    "chat_history_truncated_suffix": "（管理窗口最多显示最近 500 则）",
    "chat_history_status": "本机共保存 {count} 则对话。{suffix}",
    "chat_select_delete_title": "尚未勾选",
    "chat_select_delete": "请先勾选要删除的对话。",
    "chat_delete_title": "永久删除对话",
    "chat_delete_confirm": "确定永久删除勾选的 {count} 则对话吗？",
    "load_older_chat_tooltip": "每次向前加载 50 则本机对话",
    "manage_chat_tooltip": "勾选并删除指定对话，其他内容不受影响",
    "chat_zoom_out_tooltip": "缩小对话文字（Ctrl＋鼠标滚轮向下）",
    "chat_zoom_in_tooltip": "放大对话文字（Ctrl＋鼠标滚轮向上）",
    "chat_retention_status": "本机保存 {total} 则对话，目前显示最近 {shown} 则",
    "platform_name_required": "请先输入平台、系统或工具名称。",
    "platform_duplicate": "“{platform}”已存在，请使用不同名称。",
    "platform_added": "已添加工作平台：{platform}",
    "platform_delete_title": "删除工作平台",
    "platform_delete_confirm": "确定删除“{platform}”及其工作进度吗？此操作无法恢复。",
    "platform_not_found": "找不到工作平台：{platform}",
    "platform_deleted": "已删除工作平台：{platform}",
    "platform_url_missing_title": "尚未设置网址",
    "platform_url_missing": "请先在“{platform}”卡片填写网站或工具网址。",
    "platform_url_unsupported_title": "网址格式不支持",
    "platform_url_unsupported": "只允许打开 http:// 或 https:// 网址。",
    "permission_open_platform": "打开 {platform} 网站",
    "echo_guard_tooltip": "墨寒说话时暂停上传麦克风，播放结束后再恢复；启用时无法在她说话途中插话。",
    "hybrid_transcript_tooltip": (
        "Realtime 保留原生音频理解；每句说完后，界面文字改用完整录音的 "
        "OpenAI 高精度转录。成功后才允许墨寒回答。"
    ),
    "flagship_heading": "<b>旗舰控制中心</b>",
    "increase": "增加",
    "decrease": "减少",
    "voice_section": "语音",
    "profile_required_title": "尚缺必要资料",
    "profile_required": "助手名称与助手对您的称呼不可留空。",
    "send_chat_required_title": "尚未输入内容",
    "send_chat_required": "请先在左侧输入文字，再点击“发送”；也可以直接使用麦克风。",
    "thinking_status": "{assistant}思考中……",
    "answering_status": "回答中……",
    "api_connection_failed": "OpenAI API：连接失败（{error}）",
    "voice_ready_short": "准备就绪",
    "microphone_idle": "🎙 麦克风",
    "microphone_send_now": "⏹ 立即发送",
    "microphone_recognizing": "识别中……",
    "voice_status_format": "语音状态：{phase}",
    "bubble_full_content": "……\n（完整内容请见对话页）",
    "tray_open_today": "打开今日待办",
    "tray_quit": "退出墨寒",
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
    "realtime_output_source": "Realtime 回复声音来源",
    "realtime_output_openai": (
        "OpenAI Realtime 原生语音（最低延迟，现有默认）"
    ),
    "realtime_output_azure": "Azure Speech 女性声线（柔和流式播放）",
    "realtime_output_azure_hd": (
        "Azure Dragon HD 女性声线（需 S0）"
    ),
    "realtime_output_note_openai": (
        "使用下方“OpenAI Realtime 原生声线”；延迟最低，完整保留 "
        "OpenAI Realtime 的原生实时语音输出。"
    ),
    "realtime_output_note_azure": (
        "沿用上方“Azure Speech 女性声线”、区域与密钥。OpenAI Realtime "
        "负责实时理解，Azure 以流式方式发声。"
    ),
    "realtime_output_note_azure_hd": (
        "沿用上方“Dragon HD 女性声线”、S0 区域与独立密钥。OpenAI "
        "Realtime 负责实时理解，Dragon HD 以流式方式发声。"
    ),
    "realtime_voice": "OpenAI Realtime 原生声线",
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
    "azure_hd_engine": "Azure Dragon HD（预览，需 S0）",
    "azure_voice": "Azure Speech 女性声线",
    "azure_region": "Azure Speech 区域",
    "azure_key": "Azure Speech 密钥",
    "azure_region_choose": "请选择创建 Azure 资源时所在的区域",
    "azure_region_saved": "现有设置 · {region}",
    "azure_key_saved": "已由 Windows 加密保存；留空即可保留",
    "azure_key_missing": "贴上 Azure Speech 资源密钥",
    "azure_remove_key": "移除 Azure Speech 密钥",
    "azure_remove_key_confirm": (
        "确定移除由 Windows 加密保存的 Azure Speech 密钥吗？"
    ),
    "azure_key_save_failed": "无法安全保存 Azure Speech 密钥：{error}",
    "azure_hd_voice": "Dragon HD 女性声线",
    "azure_hd_region": "Dragon HD 资源区域",
    "azure_hd_key": "Dragon HD S0 资源密钥",
    "azure_hd_key_saved": "Dragon HD S0 密钥已由 Windows 加密保存；留空即可保留",
    "azure_hd_key_missing": "贴上独立的 Dragon HD S0 资源密钥",
    "azure_hd_remove_key": "移除 Dragon HD S0 密钥",
    "azure_hd_remove_key_confirm": (
        "确定移除由 {platform} 安全保存的 Dragon HD S0 密钥吗？"
    ),
    "azure_hd_key_save_failed": "无法安全保存 Dragon HD S0 密钥：{error}",
    "azure_hd_speech_note": (
        "可选预览功能；请使用独立的 S0 语音资源、密钥与相符区域。"
        "Dragon HD 不提供 viseme，因此墨寒会沿用音频分析维持嘴型同步。"
        "发话前等待时间取决于网络与区域距离。若 HD 失败，会依序退回一般 "
        "Azure 与 Windows 本机语音，"
        "每一层只尝试一次，避免重复计费。"
    ),
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
    "realtime_status_format": "Realtime：{status}",
    "realtime_disconnected_status": "未连接",
    "realtime_error_status": "错误：{error}",
    "realtime_voice_title": "Realtime 语音",
    "realtime_output_unavailable": (
        "Realtime Azure 语音输出服务尚未建立，未启动实时对话。"
    ),
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
    "remove_api_key_confirm": "确定移除由 {platform} 安全保存的 OpenAI API 密钥吗？",
    "save_settings": "保存设置",
    "api_key_saved": "已安全保存；留空则保持不变",
    "api_key_missing": "粘贴以 sk- 开头的 OpenAI Project API Key",
    "api_key_save_failed": "无法安全保存 OpenAI API 密钥：{error}",
    "secret_auto_save_hint": "输入后按 Enter 或移开焦点，即会自动安全保存。",
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

PLATFORM_STATUS_LABELS: Mapping[str, str] = frozendict({
    "尚未開始": "Not started",
    "準備資料": "Preparing materials",
    "進行中": "In progress",
    "待送出": "Ready to submit",
    "等待回覆": "Waiting for response",
    "審核中": "Under review",
    "需修正": "Needs revision",
    "已排程": "Scheduled",
    "已完成": "Completed",
    "已上架": "Published",
    "暫停": "Paused",
})

MEMORY_CATEGORY_LABELS: Mapping[str, str] = frozendict({
    "人物": "People",
    "偏好": "Preferences",
    "目標": "Goals",
    "工作流程": "Workflows",
    "重要日期": "Important dates",
    "其他": "Other",
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

SIMPLIFIED_PLATFORM_STATUS_LABELS: Mapping[str, str] = frozendict({
    "尚未開始": "尚未开始",
    "準備資料": "准备资料",
    "進行中": "进行中",
    "待送出": "待提交",
    "等待回覆": "等待回复",
    "審核中": "审核中",
    "需修正": "需修改",
    "已排程": "已排期",
    "已完成": "已完成",
    "已上架": "已发布",
    "暫停": "暂停",
})

SIMPLIFIED_MEMORY_CATEGORY_LABELS: Mapping[str, str] = frozendict({
    "人物": "人物",
    "偏好": "偏好",
    "目標": "目标",
    "工作流程": "工作流程",
    "重要日期": "重要日期",
    "其他": "其他",
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
