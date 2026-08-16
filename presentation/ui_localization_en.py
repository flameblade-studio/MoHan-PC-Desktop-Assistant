from __future__ import annotations

lazy from collections.abc import Mapping

lazy from domain.immutable_config import deep_freeze

ENGLISH_UI_TEXT: Mapping[str, str] = deep_freeze({
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
    "window_title_placeholder": ("Leave blank to use Assistant name · Organization"),
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
    "tab_wardrobe": "Wardrobe Pavilion",
    "cancel_without_saving": "Cancel without saving",
    "wardrobe_import": "Import outfit package",
    "wardrobe_apply": "Apply selected outfit",
    "wardrobe_restore_builtin": "Restore built-in outfit",
    "wardrobe_package_list": "Package list",
    "wardrobe_compatibility_status": "Compatibility status",
    "wardrobe_status": "Status",
    "wardrobe_no_packages": "No outfit packages installed",
    "wardrobe_default_outfit": "Built-in default outfit",
    "wardrobe_compatible": "Compatible",
    "wardrobe_incompatible": "Incompatible",
    "wardrobe_status_ready": "Wardrobe system is ready",
    "wardrobe_validator_pending": (
        "The package failed complete all-view and security validation and was not installed."
    ),
    "wardrobe_assets_pending": (
        "This outfit does not include complete assets for every view and cannot be applied."
    ),
    "wardrobe_builtin_applied": "Built-in default outfit applied.",
    "wardrobe_outfit_applied": "Selected complete outfit applied.",
    "wardrobe_autonomous_enabled": "Allow MoHan to choose outfits autonomously",
    "wardrobe_self_generation_enabled": "Allow MoHan to create cloud-generated outfits (charges may apply)",
    "wardrobe_trend_search_enabled": "Allow fashion trend search for original inspiration",
    "wardrobe_generated_limit": "Generated outfit retention limit",
    "wardrobe_storage_limit": "Generated outfit storage limit",
    "wardrobe_pavilion_subtitle": (
        "Let MoHan choose a complete look for the weather, mood, and occasion "
        "while preserving your final say."
    ),
    "wardrobe_source_policy": (
        "Separated sources: Flameblade official · User imports · MoHan creations"
    ),
    "dashboard_brand_line": "Ink in her bones · Cold light in her heart",
    "wardrobe_character_preview": "MoHan appearance preview",
    "wardrobe_view_front": "Front",
    "wardrobe_view_left": "Left",
    "wardrobe_view_right": "Right",
    "wardrobe_view_back": "Back",
    "wardrobe_upload_single_file": "Upload one file",
    "wardrobe_installed_inactive": "Installed, not active",
    "wardrobe_outfit_preview": "Outfit preview",
    "wardrobe_hairstyle_preview": "Hairstyle preview",
    "wardrobe_headwear_accessories": "Headwear and accessories",
    "wardrobe_preview_complete_look": "Preview complete look",
    "wardrobe_changes_after_save": "Takes effect after saving",
    "wardrobe_cancel_restores": "Cancel to restore",
    "wardrobe_remove_package": "Remove add-on",
    "wardrobe_delete_confirm": "Remove {package}?",
    "wardrobe_builtin_not_removable": "Built-in packages cannot be removed",
    "wardrobe_switch_before_remove": "Switch packages before removing the active one",
    "wardrobe_missing_package_fallback": "Package missing; kept the current look",
    "theme_preview": "Theme preview",
    "theme_restore": "Restore theme",
    "theme_source_official": "Flameblade official",
    "theme_source_user": "User-created",
    "package_rejected_unsafe_or_missing": "Package rejected: unsafe or missing files",
    "appearance_category_outfit": "Outfit",
    "appearance_category_hairstyle": "Hairstyle",
    "appearance_category_headwear": "Headwear",
    "appearance_category_accessory": "Accessory",
    "appearance_no_headwear": "No headwear",
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
    "edit_selected_idea_tooltip": ("You can also double-click an idea below"),
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
    "todo_empty": ("No tasks yet today.\nWrite down the one thing that matters most."),
    "idea_count": "{count} saved",
    "idea_empty": ("No ideas saved yet. Enter text above and choose ‘Save idea’."),
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
    "idea_not_found": ("That idea could not be found. Refresh and try again."),
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
    "memory_not_found": ("That memory no longer exists. The list will be refreshed."),
    "memory_save_failed_title": "Memory could not be saved",
    "memory_save_failed": (
        "An identical memory may already exist. Existing data was not changed."
    ),
    "memory_select_delete_title": "No memories checked",
    "memory_select_delete": "Check one or more memories to delete first.",
    "memory_delete_title": "Delete long-term memories",
    "memory_delete_confirm": ("Permanently delete the {count} checked memories?"),
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
    "memory_metadata": ("Source: {source}  Created: {created}  Updated: {updated}"),
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
    "realtime_output_azure_hd": ("Azure Dragon HD female voice (requires S0)"),
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
    "azure_remove_key_confirm": ("Remove the Azure Speech key encrypted by Windows?"),
    "azure_key_save_failed": ("Could not securely save the Azure Speech key: {error}"),
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

__all__ = ("ENGLISH_UI_TEXT",)
