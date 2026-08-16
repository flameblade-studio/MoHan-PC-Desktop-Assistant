from __future__ import annotations

lazy import sys
lazy from datetime import UTC, datetime
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.companion_phrasebook import (
    WARDROBE_REVEAL_ORIGIN,
    WARDROBE_REVEAL_QUESTION,
    public_companion_line,
)
lazy from application.outfit_reveal import (
    LAST_REVEALED_OUTFIT_KEY,
    PENDING_OUTFIT_KEY,
    OutfitRevealContext,
    OutfitRevealStateStore,
    decide_outfit_reveal,
    is_outfit_origin_question,
    outfit_origin_reply,
)
lazy from application.proactive_companion_runtime import (
    NormalizedCompanionEnvironment,
    ProactiveCompanionRuntime,
    ProactiveSource,
)
lazy from domain.companion_proactivity_preferences import (
    CompanionProactivityPreferences,
)


class Settings:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def read(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def write(self, values: dict[str, object]) -> None:
        self.values.update(values)


class NoWellbeing:
    def request(self, *_args, **_kwargs):
        return None

    def report_spoken(self, *_args, **_kwargs):
        return False

    def approved_cue(self, *_args, **_kwargs):
        return None


class NoOccasion:
    def decide_special_occasion(self, *_args, **_kwargs):
        return None

    def record_delivery(self, *_args, **_kwargs):
        return False


def run() -> None:
    ready = OutfitRevealContext("modern", True, True, True, False, False)
    cue = decide_outfit_reveal(ready)
    assert cue is not None
    assert cue.expression == "shy_cute_front"
    assert cue.gesture == "show-outfit"
    assert cue.framing == "full-body"
    for language in ("zh-TW", "zh-CN", "en", "ja-JP"):
        assert public_companion_line(language, WARDROBE_REVEAL_QUESTION)
        assert public_companion_line(language, WARDROBE_REVEAL_ORIGIN)
    for changes in (
        {"first_reveal_pending": False},
        {"user_present": False},
        {"user_looking": False},
        {"speech_busy": True},
        {"do_not_disturb": True},
    ):
        values = {
            "outfit_id": "modern",
            "first_reveal_pending": True,
            "user_present": True,
            "user_looking": True,
            "speech_busy": False,
            "do_not_disturb": False,
        }
        values.update(changes)
        assert decide_outfit_reveal(OutfitRevealContext(**values)) is None
    settings = Settings()
    store = OutfitRevealStateStore(settings)
    store.mark_pending("modern")
    assert store.pending_outfit_id() == "modern"
    assert not store.record_reveal("modern", succeeded=False)
    assert store.pending_outfit_id() == "modern"
    assert store.record_reveal("modern", succeeded=True)
    assert store.pending_outfit_id() == ""
    assert settings.values[LAST_REVEALED_OUTFIT_KEY] == "modern"
    assert settings.values[PENDING_OUTFIT_KEY] == ""
    questions = {
        "zh-TW": "妳什麼時候有這件新衣服的？",
        "zh-CN": "你什么时候有这件新衣服的？",
        "en": "Where did you get this new outfit?",
        "ja-JP": "その新しい衣装はどこで買ったの？",
    }
    for language, question in questions.items():
        assert is_outfit_origin_question(question, language)
        assert outfit_origin_reply(language)
    assert "網購" in outfit_origin_reply("zh-TW")
    assert "网购" in outfit_origin_reply("zh-CN")
    assert "bought it online" in outfit_origin_reply("en")
    assert "ネット通販" in outfit_origin_reply("ja-JP")
    store.mark_pending("modern")
    empty = NoWellbeing()
    runtime = ProactiveCompanionRuntime(
        empty,
        empty,
        NoOccasion(),
        outfit_reveals=store,
    )
    request = runtime.propose(
        NormalizedCompanionEnvironment(
            now=datetime(2027, 3, 20, 10, tzinfo=UTC),
            user_present=True,
            absence_duration_seconds=0.0,
            focus_active=False,
            meeting_active=False,
            fullscreen_active=False,
            seconds_since_user_interaction=0.0,
            reminder_trigger=None,
            language="zh-TW",
            user_title="主上",
            pending_outfit_id="modern",
            user_looking=True,
        ),
        CompanionProactivityPreferences(),
    )
    assert request is not None
    assert request.source is ProactiveSource.WARDROBE
    assert request.performance.framing == "full-body"
    assert store.pending_outfit_id() == "modern"
    assert runtime.report_spoken(request.delivery_token, succeeded=True)
    assert store.pending_outfit_id() == ""
    print("OUTFIT_REVEAL_OK")


if __name__ == "__main__":
    run()
