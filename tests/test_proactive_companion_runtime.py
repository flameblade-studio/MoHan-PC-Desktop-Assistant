from __future__ import annotations

lazy import sys
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from companion_phrasebook import CompanionPhrasebook
lazy from companion_proactivity_preferences import CompanionProactivityPreferences
lazy from proactive_companion_runtime import (
    CandidatePriority,
    NormalizedCompanionEnvironment,
    ProactiveCompanionRuntime,
    ProactiveSource,
)
lazy from special_occasion import (
    OccasionCue,
    OccasionDelivery,
    OccasionExpression,
    OccasionFraming,
    OccasionGaze,
    OccasionKind,
    OccasionStage,
)
lazy from wellbeing_app_bridge import ReminderTrigger, SpeakRequest
lazy from wellbeing_reminder import (
    ReminderExpression,
    ReminderFraming,
    ReminderGaze,
    ReminderGesture,
    ReminderStage,
    WellbeingCue,
    WellbeingKind,
)
lazy from wellbeing_runtime import RuntimeCue, RuntimeSource

NOW = datetime(2027, 1, 8, 20, tzinfo=UTC)


class Wellbeing:
    def __init__(self) -> None:
        self.requests = 0
        self.reports: list[tuple[str, bool]] = []

    def request(self, trigger, **_kwargs):
        self.requests += 1
        return SpeakRequest("Please take care.", trigger.value, f"wb-{trigger.value}")

    def report_spoken(self, token, *, succeeded):
        self.reports.append((token, succeeded))
        return succeeded


class CueResolver:
    def __init__(self) -> None:
        self.approved = True

    def approved_cue(self, token):
        if not self.approved:
            return None
        kind = {
            "lunch": WellbeingKind.MEAL,
            "dinner": WellbeingKind.MEAL,
            "hydration": WellbeingKind.HYDRATION,
            "rest": WellbeingKind.REST,
            "overwork": WellbeingKind.PROLONGED_SITTING,
            "prolonged_sitting": WellbeingKind.PROLONGED_SITTING,
        }[token.removeprefix("wb-")]
        return WellbeingCue(
            token,
            kind,
            ReminderStage.INITIAL,
            ReminderExpression.GENTLE,
            ReminderGaze.NEAR_USER,
            ReminderGesture.OPEN_HAND,
            ReminderFraming.HALF,
            f"wellbeing.{kind.value}.initial",
            "approved",
        )


class Occasions:
    def __init__(self) -> None:
        self.cue: RuntimeCue | None = None
        self.reports: list[tuple[str, bool]] = []

    def decide_special_occasion(self, _attention):
        return self.cue

    def record_delivery(self, cue, *, succeeded):
        self.reports.append((cue.delivery_token, succeeded))
        return succeeded


def occasion(
    *,
    kind: OccasionKind = OccasionKind.MOHAN_BIRTHDAY,
    stage: OccasionStage = OccasionStage.SUBTLE_HINT,
) -> RuntimeCue:
    cue = OccasionCue(
        kind,
        stage,
        OccasionExpression.QUIETLY_HOPEFUL,
        OccasionGaze.NEAR_USER,
        OccasionDelivery.GENTLE,
        OccasionFraming.HALF,
        f"occasion.{kind.value}.{stage.value}",
        "occasion-approved",
    )
    return RuntimeCue(
        RuntimeSource.SPECIAL_OCCASION,
        f"2027-01-08:{kind.value}",
        cue.line_key,
        0,
        cue,
        f"occasion-{kind.value}-{stage.value}",
    )


def environment(**changes: object) -> NormalizedCompanionEnvironment:
    values = {
        "now": NOW,
        "user_present": True,
        "absence_duration_seconds": 0.0,
        "focus_active": False,
        "meeting_active": False,
        "fullscreen_active": False,
        "seconds_since_user_interaction": 0.0,
        "reminder_trigger": None,
        "language": "en",
        "user_title": "there",
        "speech_active": False,
    }
    values.update(changes)
    return NormalizedCompanionEnvironment(**values)


def runtime(phrasebook=None):
    wellbeing = Wellbeing()
    resolver = CueResolver()
    occasions = Occasions()
    value = ProactiveCompanionRuntime(
        wellbeing,
        resolver,
        occasions,
        phrasebook=phrasebook,
    )
    return value, wellbeing, resolver, occasions


def runtime_with_occasion(cue: RuntimeCue):
    value, wellbeing, resolver, occasions = runtime()
    occasions.cue = cue
    return value, wellbeing, resolver, occasions


def assert_conflict_priority_is_explicit_and_deterministic() -> None:
    engine, _wellbeing, _resolver, occasions = runtime()
    occasions.cue = occasion(stage=OccasionStage.RESTRAINED_GRUMBLE)
    value = environment(
        absence_duration_seconds=8 * 60 * 60,
        seconds_since_user_interaction=3 * 60 * 60,
        reminder_trigger=ReminderTrigger.LUNCH,
    )
    selected = engine.propose(value, CompanionProactivityPreferences())
    assert selected is not None
    assert selected.priority is CandidatePriority.OCCASION_GRUMBLE
    assert selected.source is ProactiveSource.SPECIAL_OCCASION
    second, *_ = runtime_with_occasion(occasions.cue)
    assert second.propose(value, CompanionProactivityPreferences()) == selected


def assert_unselected_wellbeing_candidate_is_released_without_commit() -> None:
    engine, wellbeing, _resolver, _occasions = runtime_with_occasion(occasion())
    selected = engine.propose(
        environment(reminder_trigger=ReminderTrigger.LUNCH),
        CompanionProactivityPreferences(),
    )
    assert selected is not None
    assert selected.source is ProactiveSource.SPECIAL_OCCASION
    assert wellbeing.reports == [("wb-lunch", False)]


def assert_birthday_then_wellbeing_then_return_priority() -> None:
    engine, _wellbeing, _resolver, occasions = runtime()
    occasions.cue = occasion()
    selected = engine.propose(
        environment(
            reminder_trigger=ReminderTrigger.LUNCH,
            absence_duration_seconds=8 * 60 * 60,
        ),
        CompanionProactivityPreferences(),
    )
    assert selected is not None and selected.priority is CandidatePriority.BIRTHDAY_HINT

    engine, _wellbeing, _resolver, _occasions = runtime()
    selected = engine.propose(
        environment(
            reminder_trigger=ReminderTrigger.LUNCH,
            absence_duration_seconds=8 * 60 * 60,
        ),
        CompanionProactivityPreferences(),
    )
    assert selected is not None and selected.priority is CandidatePriority.MEAL


def assert_all_attention_and_preference_guards_block() -> None:
    changes = (
        {"user_present": False},
        {"focus_active": True},
        {"meeting_active": True},
        {"fullscreen_active": True},
        {"speech_active": True},
    )
    for state in changes:
        engine, wellbeing, _resolver, occasions = runtime()
        occasions.cue = occasion()
        assert engine.propose(
            environment(reminder_trigger=ReminderTrigger.LUNCH, **state),
            CompanionProactivityPreferences(),
        ) is None
        assert wellbeing.requests == 0
    engine, *_ = runtime()
    assert engine.propose(
        environment(reminder_trigger=ReminderTrigger.LUNCH),
        CompanionProactivityPreferences(enabled=False),
    ) is None


def assert_unapproved_wellbeing_cue_never_escapes() -> None:
    engine, wellbeing, resolver, _occasions = runtime()
    resolver.approved = False
    assert engine.propose(
        environment(reminder_trigger=ReminderTrigger.LUNCH),
        CompanionProactivityPreferences(),
    ) is None
    assert wellbeing.reports == [("wb-lunch", False)]


def assert_all_wellbeing_triggers_and_preference_guards() -> None:
    cases = (
        (ReminderTrigger.LUNCH, CandidatePriority.MEAL, {"meal_enabled": False}),
        (ReminderTrigger.DINNER, CandidatePriority.MEAL, {"meal_enabled": False}),
        (
            ReminderTrigger.HYDRATION,
            CandidatePriority.HYDRATION,
            {"hydration_enabled": False},
        ),
        (ReminderTrigger.REST, CandidatePriority.REST, {"rest_enabled": False}),
        (
            ReminderTrigger.OVERWORK,
            CandidatePriority.PROLONGED_SITTING,
            {"prolonged_sitting_enabled": False},
        ),
        (
            ReminderTrigger.PROLONGED_SITTING,
            CandidatePriority.PROLONGED_SITTING,
            {"prolonged_sitting_enabled": False},
        ),
    )
    for trigger, priority, disabled in cases:
        engine, *_ = runtime()
        selected = engine.propose(
            environment(reminder_trigger=trigger),
            CompanionProactivityPreferences(),
        )
        assert selected is not None and selected.priority is priority
        engine, wellbeing, *_ = runtime()
        assert engine.propose(
            environment(reminder_trigger=trigger),
            CompanionProactivityPreferences(**disabled),
        ) is None
        assert wellbeing.requests == 0


def assert_two_phase_commit_failure_does_not_consume_budget() -> None:
    engine, wellbeing, _resolver, _occasions = runtime()
    prefs = CompanionProactivityPreferences(daily_limit=1)
    first = engine.propose(
        environment(reminder_trigger=ReminderTrigger.LUNCH), prefs
    )
    assert first is not None
    assert wellbeing.reports == []
    assert not engine.report_spoken(first.delivery_token, succeeded=False)
    assert wellbeing.reports == [(first.delivery_token, False)]
    retry = engine.propose(
        environment(reminder_trigger=ReminderTrigger.LUNCH), prefs
    )
    assert retry is not None
    assert engine.report_spoken(retry.delivery_token, succeeded=True)
    assert engine.propose(
        environment(reminder_trigger=ReminderTrigger.HYDRATION), prefs
    ) is None


def assert_return_thresholds_checkin_and_neutral_public_text() -> None:
    prefs = CompanionProactivityPreferences()
    engine, *_ = runtime()
    assert engine.propose(environment(absence_duration_seconds=59), prefs) is None
    brief = engine.propose(
        environment(absence_duration_seconds=prefs.brief_absence_seconds), prefs
    )
    assert brief is not None and brief.priority is CandidatePriority.BRIEF_RETURN
    assert "system" not in brief.speak.text.casefold()
    engine, *_ = runtime()
    long_wait = engine.propose(
        environment(absence_duration_seconds=prefs.long_wait_seconds), prefs
    )
    assert long_wait is not None and long_wait.priority is CandidatePriority.LONG_RETURN
    engine, *_ = runtime()
    check_in = engine.propose(
        environment(seconds_since_user_interaction=45 * 60), prefs
    )
    assert check_in is not None and check_in.priority is CandidatePriority.CHECK_IN


def assert_visual_presence_arrival_uses_the_approved_speech_path() -> None:
    engine, *_ = runtime()
    selected = engine.propose(
        environment(visual_presence_arrival=True),
        CompanionProactivityPreferences(),
    )
    assert selected is not None
    assert selected.source is ProactiveSource.VISUAL_PRESENCE
    assert selected.priority is CandidatePriority.VISUAL_PRESENCE
    assert selected.performance.expression == "happy"


def assert_visual_activity_uses_warm_localized_speech_with_quiet_guard() -> None:
    engine, *_ = runtime()
    selected = engine.propose(
        environment(
            visual_activity=True,
            language="zh-TW",
            user_title="主人",
        ),
        CompanionProactivityPreferences(),
    )
    assert selected is not None
    assert selected.source is ProactiveSource.VISUAL_ACTIVITY
    assert selected.priority is CandidatePriority.VISUAL_ACTIVITY
    assert selected.performance.expression == "happy"
    assert "主人" in selected.speak.text

    engine, *_ = runtime()
    quiet = engine.propose(
        environment(visual_activity=True, proactive_mode="quiet"),
        CompanionProactivityPreferences(),
    )
    assert quiet is None


def assert_proactive_mode_shapes_candidate_scope_and_frequency() -> None:
    prefs = CompanionProactivityPreferences()

    # 安靜：只保留必要提醒（wellbeing／scheduled），不寒暄、不歡迎回來。
    engine, *_ = runtime()
    assert engine.propose(
        environment(
            proactive_mode="quiet",
            seconds_since_user_interaction=3 * 60 * 60,
        ),
        prefs,
    ) is None
    engine, *_ = runtime()
    assert engine.propose(
        environment(
            proactive_mode="quiet",
            absence_duration_seconds=8 * 60 * 60,
        ),
        prefs,
    ) is None
    engine, *_ = runtime()
    quiet_wellbeing = engine.propose(
        environment(
            proactive_mode="quiet",
            reminder_trigger=ReminderTrigger.LUNCH,
        ),
        prefs,
    )
    assert quiet_wellbeing is not None
    assert quiet_wellbeing.source is ProactiveSource.WELLBEING

    # 積極：縮短寒暄沉默門檻（15 分鐘即主動關心）。
    engine, *_ = runtime()
    active = engine.propose(
        environment(
            proactive_mode="active",
            seconds_since_user_interaction=15 * 60,
        ),
        prefs,
    )
    assert active is not None
    assert active.priority is CandidatePriority.CHECK_IN

    # 平衡：維持原 45 分鐘門檻。
    engine, *_ = runtime()
    assert engine.propose(
        environment(
            proactive_mode="balanced",
            seconds_since_user_interaction=30 * 60,
        ),
        prefs,
    ) is None


def assert_private_phrasebook_is_injected_not_built_in() -> None:
    private = CompanionPhrasebook(
        {"warm": ("Private welcome.",)},
        ("Private check-in.",),
        {},
    )
    engine, *_ = runtime(private)
    welcome = engine.propose(
        environment(absence_duration_seconds=120),
        CompanionProactivityPreferences(),
    )
    assert welcome is not None and welcome.speak.text == "Private welcome."


def assert_day_rollover_resets_budget() -> None:
    engine, *_ = runtime()
    prefs = CompanionProactivityPreferences(daily_limit=1)
    first = engine.propose(environment(absence_duration_seconds=120), prefs)
    assert first is not None and engine.report_spoken(first.delivery_token, succeeded=True)
    assert engine.propose(environment(seconds_since_user_interaction=3600), prefs) is None
    tomorrow = NOW + timedelta(days=1)
    next_day = engine.propose(
        environment(now=tomorrow, seconds_since_user_interaction=3600), prefs
    )
    assert next_day is not None


def assert_pending_delivery_is_bounded_and_expires() -> None:
    engine, wellbeing, _resolver, _occasions = runtime()
    first = engine.propose(
        environment(reminder_trigger=ReminderTrigger.LUNCH),
        CompanionProactivityPreferences(),
    )
    assert first is not None
    blocked = engine.propose(
        environment(
            now=NOW.replace(minute=1),
            reminder_trigger=ReminderTrigger.HYDRATION,
        ),
        CompanionProactivityPreferences(),
    )
    assert blocked is None
    retry = engine.propose(
        environment(
            now=NOW.replace(minute=6),
            reminder_trigger=ReminderTrigger.HYDRATION,
        ),
        CompanionProactivityPreferences(),
    )
    assert retry is not None
    assert wellbeing.reports == [(first.delivery_token, False)]
    assert len(engine._pending) == 1
    assert len(engine._pending_signatures) == 1


def run() -> None:
    assert_conflict_priority_is_explicit_and_deterministic()
    assert_unselected_wellbeing_candidate_is_released_without_commit()
    assert_birthday_then_wellbeing_then_return_priority()
    assert_all_attention_and_preference_guards_block()
    assert_unapproved_wellbeing_cue_never_escapes()
    assert_all_wellbeing_triggers_and_preference_guards()
    assert_two_phase_commit_failure_does_not_consume_budget()
    assert_return_thresholds_checkin_and_neutral_public_text()
    assert_visual_presence_arrival_uses_the_approved_speech_path()
    assert_visual_activity_uses_warm_localized_speech_with_quiet_guard()
    assert_proactive_mode_shapes_candidate_scope_and_frequency()
    assert_private_phrasebook_is_injected_not_built_in()
    assert_day_rollover_resets_budget()
    assert_pending_delivery_is_bounded_and_expires()
    print("PROACTIVE_COMPANION_RUNTIME_OK")


if __name__ == "__main__":
    run()
