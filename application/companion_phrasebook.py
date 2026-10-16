from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass

lazy from application.multisensory_interaction import WelcomeStyle
lazy from application.special_occasion import OccasionKind, OccasionStage
lazy from application.wellbeing_reminder import ReminderStage, WellbeingKind
lazy from domain.character_source import active_character_data
lazy from domain.language_support import canonical_ui_language

PHRASEBOOK_SETTING = "multisensory_phrasebook_v1"
PHRASEBOOK_VERSION = 2
WARDROBE_REVEAL_QUESTION = "wardrobe.reveal.question"
WARDROBE_REVEAL_ORIGIN = "wardrobe.reveal.origin"
WARDROBE_PHRASE_KEYS = (WARDROBE_REVEAL_QUESTION, WARDROBE_REVEAL_ORIGIN)

_DIALOGUES = active_character_data().dialogues


def wellbeing_phrase_key(kind: WellbeingKind, stage: ReminderStage) -> str:
    return f"wellbeing.{kind.value}.{stage.value}"


def occasion_phrase_key(kind: OccasionKind, stage: OccasionStage) -> str:
    return f"occasion.{kind.value}.{stage.value}"


WELLBEING_PHRASE_KEYS = tuple(
    wellbeing_phrase_key(kind, stage)
    for kind in WellbeingKind
    for stage in ReminderStage
)
OCCASION_PHRASE_KEYS = tuple(
    occasion_phrase_key(kind, stage)
    for kind in OccasionKind
    for stage in OccasionStage
)
PUBLIC_COMPANION_LINES = frozendict(
    {
        locale: frozendict(
            {
                key: dialogue.phrasebook[key]
                for key in (*WELLBEING_PHRASE_KEYS, *OCCASION_PHRASE_KEYS)
            }
        )
        for locale, dialogue in _DIALOGUES.items()
    }
)
WARDROBE_PUBLIC_LINES = frozendict(
    {
        locale: frozendict(
            {key: dialogue.phrasebook[key] for key in WARDROBE_PHRASE_KEYS}
        )
        for locale, dialogue in _DIALOGUES.items()
    }
)


@dataclass(frozen=True, slots=True)
class CompanionPhrasebook:
    welcomes: Mapping[str, tuple[str, ...]]
    check_ins: tuple[str, ...]
    scenarios: Mapping[str, tuple[str, ...]]

    @classmethod
    def from_setting(cls, value: object) -> CompanionPhrasebook:
        if not isinstance(value, dict):
            return cls({}, (), {})
        welcome_value = value.get("welcomes", {})
        if not isinstance(welcome_value, dict):
            welcome_value = {}
        welcomes = {
            str(key): _clean_lines(lines)
            for key, lines in welcome_value.items()
        }
        scenario_value = value.get("scenarios", {})
        if not isinstance(scenario_value, dict):
            scenario_value = {}
        scenarios = {
            str(key): _clean_lines(lines)
            for key, lines in scenario_value.items()
            if str(key) in {
                *WELLBEING_PHRASE_KEYS,
                *OCCASION_PHRASE_KEYS,
                *WARDROBE_PHRASE_KEYS,
            }
        }
        return cls(
            welcomes,
            _clean_lines(value.get("check_ins", ())),
            scenarios,
        )

    def as_setting(self) -> dict[str, object]:
        return {
            "version": PHRASEBOOK_VERSION,
            "welcomes": dict(self.welcomes),
            "check_ins": self.check_ins,
            "scenarios": dict(self.scenarios),
        }

    def lines_for(
        self,
        language: str,
        key: str,
    ) -> tuple[str, ...]:
        custom = self.scenarios.get(key, ())
        if custom:
            return custom
        locale = canonical_ui_language(language)
        return (
            PUBLIC_COMPANION_LINES[locale].get(key, ())
            or WARDROBE_PUBLIC_LINES[locale].get(key, ())
        )


def public_companion_line(
    language: str,
    key: str,
    *,
    variation_index: int = 0,
    phrasebook: CompanionPhrasebook | None = None,
) -> str:
    lines = (phrasebook or CompanionPhrasebook({}, (), {})).lines_for(language, key)
    return lines[variation_index % len(lines)] if lines else ""


def _label(key: str) -> str:
    return _DIALOGUES["zh-TW"].labels[key]


def phrasebook_categories() -> tuple[tuple[str, str], ...]:
    return (
        *((style.value, _label(f"welcome.{style.value}")) for style in WelcomeStyle),
        ("check_ins", _label("check_ins")),
        *wellbeing_phrasebook_categories(),
        *occasion_phrasebook_categories(),
        *wardrobe_phrasebook_categories(),
    )


def grouped_phrasebook_categories(
) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    return (
        (
            "歸來問候",
            tuple(
                (style.value, _label(f"welcome.{style.value}"))
                for style in WelcomeStyle
            ),
        ),
        ("日常關心", (("check_ins", _label("check_ins")),)),
        ("健康提醒", wellbeing_phrasebook_categories()),
        ("特殊節日", occasion_phrasebook_categories()),
        ("新裝互動", wardrobe_phrasebook_categories()),
    )


def wellbeing_phrasebook_categories() -> tuple[tuple[str, str], ...]:
    return tuple(
        (
            wellbeing_phrase_key(kind, stage),
            f"{_label(f'wellbeing.{kind.value}')}・{_label(f'stage.{stage.value}')}",
        )
        for kind in WellbeingKind
        for stage in ReminderStage
    )


def occasion_phrasebook_categories() -> tuple[tuple[str, str], ...]:
    return tuple(
        (
            occasion_phrase_key(kind, stage),
            f"{_label(f'occasion.{kind.value}')}・"
            f"{_label(f'occasion_stage.{stage.value}')}",
        )
        for kind in OccasionKind
        for stage in OccasionStage
    )


def wardrobe_phrasebook_categories() -> tuple[tuple[str, str], ...]:
    return tuple((key, _label(key)) for key in WARDROBE_PHRASE_KEYS)


def _clean_lines(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        source = value.splitlines()
    elif isinstance(value, (tuple, list)):
        source = value
    else:
        return ()
    return tuple(line for item in source if (line := str(item).strip()))
