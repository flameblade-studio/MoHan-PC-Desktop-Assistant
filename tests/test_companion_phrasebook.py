from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from companion_phrasebook import (
    OCCASION_PHRASE_KEYS,
    PUBLIC_COMPANION_LINES,
    WARDROBE_PHRASE_KEYS,
    WARDROBE_PUBLIC_LINES,
    WELLBEING_PHRASE_KEYS,
    CompanionPhrasebook,
    grouped_phrasebook_categories,
    occasion_phrase_key,
    public_companion_line,
    wellbeing_phrase_key,
)
lazy from special_occasion import OccasionKind, OccasionStage
lazy from wellbeing_reminder import ReminderStage, WellbeingKind


def run() -> None:
    phrasebook = CompanionPhrasebook.from_setting(
        {
            "welcomes": {"warm": [" 歡迎回來 ", "", "又見面了"]},
            "check_ins": "還順利嗎？\n\n想聊聊嗎？",
            "scenarios": {
                "wellbeing.meal.initial": [" 先用膳吧 ", ""],
                "unknown.future": ["must be ignored"],
            },
        }
    )
    assert phrasebook.welcomes["warm"] == ("歡迎回來", "又見面了")
    assert phrasebook.check_ins == ("還順利嗎？", "想聊聊嗎？")
    assert phrasebook.scenarios["wellbeing.meal.initial"] == ("先用膳吧",)
    assert "unknown.future" not in phrasebook.scenarios
    restored = CompanionPhrasebook.from_setting(phrasebook.as_setting())
    assert restored == phrasebook
    malformed = CompanionPhrasebook.from_setting(
        {"welcomes": "not-a-mapping", "check_ins": 7}
    )
    assert malformed == CompanionPhrasebook({}, (), {})

    assert len(WELLBEING_PHRASE_KEYS) == 8
    assert len(OCCASION_PHRASE_KEYS) == 10
    groups = grouped_phrasebook_categories()
    assert tuple(group for group, _ in groups) == (
        "歸來問候",
        "日常關心",
        "健康提醒",
        "特殊節日",
        "新裝互動",
    )
    grouped_keys = tuple(
        key
        for _, categories in groups
        for key, _ in categories
    )
    assert len(grouped_keys) == len(set(grouped_keys)) == 28
    for locale in ("zh-TW", "zh-CN", "en", "ja-JP"):
        assert set(PUBLIC_COMPANION_LINES[locale]) == {
            *WELLBEING_PHRASE_KEYS,
            *OCCASION_PHRASE_KEYS,
        }
        assert all(
            len(lines) >= 2
            for lines in PUBLIC_COMPANION_LINES[locale].values()
        )
        assert set(WARDROBE_PUBLIC_LINES[locale]) == set(WARDROBE_PHRASE_KEYS)
        assert all(
            len(lines) >= 2
            for lines in WARDROBE_PUBLIC_LINES[locale].values()
        )
    meal_key = wellbeing_phrase_key(
        WellbeingKind.MEAL,
        ReminderStage.RESTRAINED_REINFORCEMENT,
    )
    assert public_companion_line("en", meal_key)
    assert public_companion_line(
        "zh-TW",
        "wellbeing.meal.initial",
        phrasebook=phrasebook,
    ) == "先用膳吧"
    birthday_key = occasion_phrase_key(
        OccasionKind.MOHAN_BIRTHDAY,
        OccasionStage.RESTRAINED_GRUMBLE,
    )
    assert "主上" not in public_companion_line("zh-TW", birthday_key)
    assert "主様" not in public_companion_line("ja-JP", birthday_key)


if __name__ == "__main__":
    run()
    print("COMPANION_PHRASEBOOK_OK")
