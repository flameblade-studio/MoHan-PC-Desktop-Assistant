"""Seed source-owned defaults for a newly created character profile."""

from __future__ import annotations

lazy import json

lazy from application.companion_phrasebook import PHRASEBOOK_SETTING
lazy from domain.character_source import CharacterSource, character_voice_profile
lazy from domain.contracts import ProfileDatabasePort


def seed_character_profile_settings(
    db: ProfileDatabasePort,
    character_source: CharacterSource,
    language: str,
    *,
    protect_source_voice: bool,
) -> None:
    """Insert source defaults without replacing explicitly saved choices."""

    persona = character_source.persona
    voice = character_voice_profile(character_source)
    dialogue = persona.dialogue_locale(language)
    welcomes = {
        key.removeprefix("welcome."): tuple(lines)
        for key, lines in dialogue.line_sets.items()
        if key.startswith("welcome.")
    }
    phrasebook = {
        "version": 2,
        "welcomes": welcomes,
        "check_ins": tuple(
            dialogue.line_sets.get("interaction.gentle_check_in", ())
        ),
        "scenarios": {
            key: tuple(lines)
            for key, lines in dialogue.phrasebook.items()
        },
    }
    defaults: dict[str, object] = {
        "ui_language": language,
        "assistant_name": persona.display_name(language),
        "user_title": persona.default_user_title(language),
        "wake_word": next(iter(persona.aliases), persona.canonical_name),
        "persona_prompt": persona.persona_prompt(language),
        PHRASEBOOK_SETTING: phrasebook,
        "voice_engine": voice.default_provider,
        "voice_rate": voice.default_rate,
        "voice_volume_percent": voice.default_volume_percent,
        "tts_voice": voice.default_tts_voice,
        "cloud_voice": voice.default_cloud_voice,
        "realtime_voice": voice.default_realtime_voice,
        "voice_instructions": voice.instructions[language],
    }
    windows_voice = voice.system_local.preferred_voice_ids.get(language, "")
    if windows_voice:
        defaults["windows_voice"] = windows_voice
    azure_voices = voice.azure.voices.get(language, ())
    if azure_voices:
        defaults["azure_speech_voice"] = azure_voices[0]
    azure_hd_voices = voice.azure.hd_voices.get(language, ())
    if azure_hd_voices:
        defaults["azure_hd_speech_voice"] = azure_hd_voices[0]
    defaults.update(
        {
            f"reminder_message_{kind}": message
            for kind, message in dialogue.reminder_lines.items()
        }
    )
    with db.conn:
        db.conn.executemany(
            "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
            tuple(
                (key, json.dumps(value, ensure_ascii=False))
                for key, value in defaults.items()
            ),
        )
        if protect_source_voice:
            # Prevent the legacy dashboard initializer from replacing a new
            # or external source-owned voice profile with MoHan defaults.
            db.conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("voice_prompt_v1204_migrated", "true"),
            )


__all__ = ("seed_character_profile_settings",)
