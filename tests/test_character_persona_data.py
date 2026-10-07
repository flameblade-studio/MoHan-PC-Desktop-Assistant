from __future__ import annotations

lazy import json
lazy import shutil
lazy from collections.abc import Mapping
lazy from dataclasses import asdict
lazy from datetime import UTC, datetime
lazy from pathlib import Path
lazy from unittest.mock import Mock

lazy import pytest

lazy from application.companion_phrasebook import (
    PUBLIC_COMPANION_LINES,
    WARDROBE_PUBLIC_LINES,
)
lazy from application.multisensory_interaction import (
    InteractionKind,
    InteractionTextContext,
    ProactiveInteraction,
    WelcomeStyle,
    interaction_text,
)
lazy from application.presentation_ports import (
    azure_female_voices,
    azure_hd_female_voices,
    preferred_windows_voice,
)
lazy from application.proactive_companion_runtime import _visual_activity_text
lazy from application.special_occasion import OCCASIONS
lazy from domain.app_profile import DEFAULT_PROFILE, default_persona_for_language
lazy from domain.character_pack.character_data import (
    CharacterDataError,
    load_mohan_character_data,
)
lazy from domain.chronicle import Chronicle, MilestoneKind
lazy from domain.command_parser import is_start_work_command, is_stop_work_command
lazy from domain.language_support import (
    LEGACY_AUTHOR_ORGANIZATION,
    LEGACY_TRANSCRIPTION_PROMPT,
    TRANSCRIPTION_PROMPT_BASES,
    localized_reminder_line,
    localized_voice_instructions,
    response_language_instruction,
)
lazy from domain.somniloquy import somniloquy_lines
lazy from domain.speech_configuration import (
    DEFAULT_VOICE_VOLUME_PERCENT,
    DEFAULT_VOICE_RATE,
    OPENAI_VOICE_ORDER,
    REALTIME_VOICES,
    TTS_VOICES,
    VOICE_GENERATION_PROMPT,
    migrate_voice_defaults,
)
lazy from domain.wardrobe_intuition import ComfortVerdict, complaint_line
lazy from integrations.ai_client import OFFLINE_NOTICE, offline_reply
lazy from integrations import speech as speech_module
lazy from integrations.speech import WindowsTTS
lazy from presentation.companion_platform import REMINDER_LINES
lazy from presentation.ui_localization import ui_text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHARACTER_ROOT = PROJECT_ROOT / "assets/characters/mohan"
LOCALES = ("zh-TW", "zh-CN", "en", "ja-JP")


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _interaction_snapshot() -> dict[str, object]:
    wall_time = datetime(2026, 1, 8, 12, tzinfo=UTC)
    result: dict[str, object] = {}
    for locale in LOCALES:
        by_kind: dict[str, object] = {}
        for style in WelcomeStyle:
            by_kind[f"welcome.{style.value}"] = [
                interaction_text(
                    locale,
                    ProactiveInteraction(
                        InteractionKind.WELCOME_BACK,
                        "idle",
                        style,
                    ),
                    InteractionTextContext(
                        "主上",
                        wall_time=wall_time,
                        variation_index=index,
                    ),
                )
                for index in range(3)
            ]
        by_kind[InteractionKind.LIGHTING_CARE.value] = interaction_text(
            locale,
            ProactiveInteraction(InteractionKind.LIGHTING_CARE, "worried"),
            InteractionTextContext("主上", wall_time=wall_time),
        )
        by_kind[InteractionKind.GENTLE_CHECK_IN.value] = [
            interaction_text(
                locale,
                ProactiveInteraction(InteractionKind.GENTLE_CHECK_IN, "idle"),
                InteractionTextContext(
                    "主上",
                    wall_time=wall_time,
                    variation_index=index,
                ),
            )
            for index in range(3)
        ]
        result[locale] = by_kind
    return result


def _offline_snapshot() -> dict[str, object]:
    cases = {
        "zh-TW": (
            ("analysis", "幫我分析這件事", "工作"),
            ("exhausted", "我好累", "工作"),
            ("start", "我開始工作了", "工作"),
            ("tired", "有點疲倦", "陪伴"),
            ("stop", "我下班了", "工作"),
            ("romantic", "我想你", "陪伴"),
            ("work", "整理資料", "工作"),
            ("companion", "隨便聊聊", "陪伴"),
        ),
        "zh-CN": (
            ("analysis", "帮我分析这件事", "工作"),
            ("exhausted", "我好累", "工作"),
            ("start", "我開始工作了", "工作"),
            ("tired", "有点疲倦", "陪伴"),
            ("stop", "我下班了", "工作"),
            ("work", "整理资料", "工作"),
            ("companion", "随便聊聊", "陪伴"),
        ),
        "en": (
            ("start", "start work", "工作"),
            ("stop", "clock out", "工作"),
            ("tired", "I am exhausted", "陪伴"),
            ("work", "organize this", "工作"),
            ("companion", "let us talk", "陪伴"),
        ),
        "ja-JP": (
            ("start", "仕事を始めます", "工作"),
            ("stop", "今日はここまで", "工作"),
            ("tired", "疲れた", "陪伴"),
            ("analysis", "相談があります", "陪伴"),
            ("work", "資料を整理", "工作"),
            ("companion", "話したい", "陪伴"),
        ),
    }
    return {
        locale: {
            name: offline_reply(text, mode, locale)
            for name, text, mode in locale_cases
        }
        for locale, locale_cases in cases.items()
    }


def _runtime_snapshot() -> dict[str, object]:
    traditional_reminders = dict(REMINDER_LINES)
    character_data = load_mohan_character_data()
    return {
        "schema": "mohan.p4-persona-before.v1",
        "personas": {
            locale: default_persona_for_language(locale)
            for locale in LOCALES
        },
        "profile_defaults": dict(DEFAULT_PROFILE),
        "identity_ui": {
            locale: {
                key: ui_text(locale, key, "")
                for key in (
                    "first_run_brand",
                    "first_run_heading",
                    "first_run_hero_tagline",
                    "assistant_name_placeholder",
                    "user_title_placeholder",
                    "wake_word_placeholder",
                    "navigation_brand",
                    "mohan_volume",
                    "preview_voice",
                    "reminder_message_placeholder",
                )
            }
            for locale in LOCALES
        },
        "ui_speech": {
            locale: {
                key: ui_text(locale, key, "", count=3)
                for key in (
                    "todo_added_speech",
                    "idea_added_speech",
                    "all_platforms_saved_speech",
                    "memory_added_speech",
                    "permission_saved_speech",
                )
            }
            for locale in LOCALES
        },
        "language": {
            "legacy_transcription_prompt": LEGACY_TRANSCRIPTION_PROMPT,
            "legacy_author_organization": LEGACY_AUTHOR_ORGANIZATION,
            "transcription_prompt_bases": dict(TRANSCRIPTION_PROMPT_BASES),
            "response_instructions": {
                locale: response_language_instruction(locale)
                for locale in LOCALES
            },
            "reminders": {
                locale: {
                    kind: localized_reminder_line(locale, kind, text)
                    for kind, text in traditional_reminders.items()
                }
                for locale in LOCALES
            },
            "voice_instructions": {
                locale: localized_voice_instructions(locale, VOICE_GENERATION_PROMPT)
                for locale in LOCALES
            },
        },
        "dialogue": {
            "public_phrasebook": _plain(PUBLIC_COMPANION_LINES),
            "wardrobe_phrasebook": _plain(WARDROBE_PUBLIC_LINES),
            "offline_notice": dict(OFFLINE_NOTICE),
            "offline_replies": _offline_snapshot(),
            "interactions": _interaction_snapshot(),
            "visual_activity": {
                locale: [
                    _visual_activity_text(locale, "主上", index)
                    for index in range(3)
                ]
                for locale in LOCALES
            },
            "chronicle": {
                locale: {
                    kind.value: Chronicle().record(kind, 1).recollection(locale, 1)
                    for kind in MilestoneKind
                }
                for locale in LOCALES
            },
            "somniloquy": {
                locale: list(somniloquy_lines(locale))
                for locale in LOCALES
            },
            "wardrobe_complaints": {
                locale: {
                    verdict.value: complaint_line(locale, verdict)
                    for verdict in (
                        ComfortVerdict.TOO_COLD,
                        ComfortVerdict.TOO_HOT,
                    )
                }
                for locale in LOCALES
            },
            "caught_glance": {
                locale: ui_text(
                    locale,
                    "caught_glance_dialogue",
                    "妾只是望向窗外，才不是在偷看主上。",
                )
                for locale in LOCALES
            },
            "startup_runtime_zh_tw": {
                "first": character_data.dialogues["zh-TW"].templates["startup.first"],
                "returning": character_data.dialogues["zh-TW"].templates[
                    "startup.returning"
                ],
            },
        },
        "occasions": [asdict(occasion) for occasion in OCCASIONS],
        "commands": {
            text: {
                "start": is_start_work_command(text),
                "stop": is_stop_work_command(text),
            }
            for text in (
                "我開始工作",
                "墨寒我開始工作",
                "墨寒開始工作",
                "我下班",
                "墨寒我下班",
                "墨寒我收工",
                "start work",
            )
        },
        "voice": {
            "generation_prompt": VOICE_GENERATION_PROMPT,
            "volume_percent": DEFAULT_VOICE_VOLUME_PERCENT,
            "openai_order": list(OPENAI_VOICE_ORDER),
            "realtime_voices": list(REALTIME_VOICES),
            "tts_voices": list(TTS_VOICES),
            "azure": {
                locale: list(azure_female_voices(locale))
                for locale in LOCALES
            },
            "azure_hd": {
                locale: list(azure_hd_female_voices(locale))
                for locale in LOCALES
            },
            "preferred_windows": preferred_windows_voice(
                (
                    ("Microsoft Hanhan Desktop", "zh-TW"),
                    ("OneCore::Microsoft Yating", "zh-TW"),
                    ("Microsoft Zhiwei Desktop", "zh-TW"),
                )
            ),
        },
    }


def _copied_character_root(tmp_path: Path) -> Path:
    target = tmp_path / "mohan"
    shutil.copytree(CHARACTER_ROOT, target)
    return target


def _rewrite_json(path: Path, mutate) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_runtime_snapshot_matches_pre_migration_bytes() -> None:
    expected = json.loads(
        (PROJECT_ROOT / "tests/data/p4-persona-before.json").read_text(
            encoding="utf-8"
        )
    )
    assert _runtime_snapshot() == expected


@pytest.mark.parametrize("fault", ("missing", "extra", "wrong_type"))
def test_character_data_rejects_schema_shape_drift(
    tmp_path: Path,
    fault: str,
) -> None:
    root = _copied_character_root(tmp_path)
    path = root / "persona/profile.json"
    if fault == "missing":
        _rewrite_json(path, lambda value: value.pop("defaults"))
    elif fault == "extra":
        _rewrite_json(path, lambda value: value.__setitem__("unexpected", True))
    else:
        _rewrite_json(
            path,
            lambda value: value["defaults"].__setitem__("assistant_name", 7),
        )
    with pytest.raises(CharacterDataError):
        load_mohan_character_data(root)


def test_character_data_requires_all_four_locales(tmp_path: Path) -> None:
    root = _copied_character_root(tmp_path)
    (root / "dialogue/ja-JP.json").unlink()
    with pytest.raises(CharacterDataError):
        load_mohan_character_data(root)


class _VoiceSettings:
    def __init__(self) -> None:
        self.values: dict[str, object] = {
            "voice_prompt_v1204_migrated": True,
            "tts_voice": "sage",
            "cloud_voice": "verse",
            "realtime_voice": "marin",
            "voice_rate": 3,
        }

    def setting(self, key: str, default: object = None) -> object:
        return self.values.get(key, default)

    def set_setting(self, key: str, value: object) -> None:
        self.values[key] = value


def test_existing_user_voice_overrides_stay_authoritative() -> None:
    settings = _VoiceSettings()
    before = dict(settings.values)
    migrate_voice_defaults(settings)
    assert settings.values == before
    voices = (
        ("OneCore::Microsoft Yating", "zh-TW"),
        ("OneCore::Custom Owner Voice", "zh-TW"),
    )
    assert (
        preferred_windows_voice(
            voices,
            saved="OneCore::Custom Owner Voice",
            target_language="zh-TW",
        )
        == "OneCore::Custom Owner Voice"
    )


def test_yating_uses_onecore_without_changing_rate(monkeypatch) -> None:
    tts = WindowsTTS()
    generation = tts._begin_generation()
    monkeypatch.setattr(
        speech_module,
        "windows_voices",
        lambda: [("OneCore::Microsoft Yating", "zh-TW")],
    )
    run_onecore = Mock()
    run_sapi = Mock()
    monkeypatch.setattr(tts, "_run_onecore", run_onecore)
    monkeypatch.setattr(tts, "_run_sapi", run_sapi)
    monkeypatch.setattr(tts, "_emit_finished", Mock())

    tts._run("主上，妾在。", "", DEFAULT_VOICE_RATE, generation)

    run_onecore.assert_called_once_with(
        "主上，妾在。",
        "Microsoft Yating",
        generation,
    )
    run_sapi.assert_not_called()
