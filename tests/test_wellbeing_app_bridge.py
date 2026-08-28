from __future__ import annotations

lazy import sys
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.companion_phrasebook import CompanionPhrasebook
lazy from application.wellbeing_app_bridge import (
    ReminderCommand,
    ReminderTrigger,
    WellbeingAppBridge,
    WellbeingAppBridgeError,
    normalize_occurrence,
)
lazy from application.wellbeing_reminder import (
    ReminderExpression,
    ReminderFraming,
    ReminderGaze,
    ReminderGesture,
    ReminderStage,
    WellbeingCue,
    WellbeingKind,
)
lazy from application.wellbeing_runtime import RuntimeAttention, RuntimeCue, RuntimeSource


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class FakeRuntime:
    def __init__(self) -> None:
        self.decisions: list[WellbeingKind] = []
        self.delivery_results: list[tuple[str, bool]] = []
        self.commands: list[tuple[str, WellbeingKind, datetime | None]] = []
        self.return_cue = True

    def decide_wellbeing(self, kind, _attention):
        self.decisions.append(kind)
        if not self.return_cue:
            return None
        stage = ReminderStage.INITIAL
        line_key = f"wellbeing.{kind.value}.{stage.value}"
        cue = WellbeingCue(
            f"runtime:{kind.value}",
            kind,
            stage,
            ReminderExpression.GENTLE,
            ReminderGaze.NEAR_USER,
            ReminderGesture.OPEN_HAND,
            ReminderFraming.HALF,
            line_key,
            "fixture",
        )
        return RuntimeCue(
            RuntimeSource.WELLBEING,
            f"2027-01-09:{kind.value}",
            line_key,
            1,
            cue,
            f"token-{kind.value}",
        )

    def record_delivery(self, cue, *, succeeded):
        self.delivery_results.append((cue.delivery_token, succeeded))
        return succeeded

    def acknowledge_wellbeing(self, kind):
        self.commands.append(("acknowledge", kind, None))

    def complete_wellbeing(self, kind):
        self.commands.append(("complete", kind, None))

    def snooze_wellbeing(self, kind, until):
        self.commands.append(("snooze", kind, until))

    def dismiss_wellbeing(self, kind):
        self.commands.append(("dismiss", kind, None))


NOW = datetime(2027, 1, 9, 12, tzinfo=UTC)
ATTENTION = RuntimeAttention(proactive_enabled=True, user_present=True)


def bridge_at(now=NOW):
    runtime = FakeRuntime()
    clock = MutableClock(now)
    return WellbeingAppBridge(runtime, clock=clock), runtime, clock


def assert_trigger_normalization_and_stable_occurrences() -> None:
    expected = {
        ReminderTrigger.LUNCH: WellbeingKind.MEAL,
        ReminderTrigger.DINNER: WellbeingKind.MEAL,
        ReminderTrigger.OVERWORK: WellbeingKind.PROLONGED_SITTING,
        ReminderTrigger.HYDRATION: WellbeingKind.HYDRATION,
        ReminderTrigger.REST: WellbeingKind.REST,
        ReminderTrigger.PROLONGED_SITTING: WellbeingKind.PROLONGED_SITTING,
    }
    for trigger, kind in expected.items():
        first = normalize_occurrence(trigger, NOW)
        second = normalize_occurrence(trigger.value, NOW + timedelta(hours=1))
        assert first == second
        assert first.kind is kind
        assert first.event_id == f"2027-01-09:{trigger.value}"


def assert_four_languages_and_private_override() -> None:
    for language in ("zh-TW", "zh-CN", "en", "ja-JP"):
        bridge, runtime, _clock = bridge_at()
        request = bridge.request(
            ReminderTrigger.HYDRATION,
            attention=ATTENTION,
            language=language,
        )
        assert request is not None
        assert request.text.strip()
        assert request.source == "hydration"
        assert runtime.delivery_results == []

    custom = "Private hydration reminder."
    phrasebook = CompanionPhrasebook(
        {},
        (),
        {"wellbeing.hydration.initial": (custom,)},
    )
    bridge, _runtime, _clock = bridge_at()
    request = bridge.request(
        ReminderTrigger.HYDRATION,
        attention=ATTENTION,
        language="zh-TW",
        phrasebook=phrasebook,
    )
    assert request is not None
    assert request.text == custom


def assert_success_failure_dedupe_and_retry() -> None:
    bridge, runtime, _clock = bridge_at()
    request = bridge.request(
        ReminderTrigger.LUNCH,
        attention=ATTENTION,
        language="en",
    )
    assert request is not None
    duplicate = bridge.request(
        ReminderTrigger.LUNCH,
        attention=ATTENTION,
        language="en",
    )
    assert duplicate is None
    assert bridge.report_spoken(request.cue_token, succeeded=False) is False
    assert runtime.delivery_results == [(request.cue_token, False)]
    retry = bridge.request(
        ReminderTrigger.LUNCH,
        attention=ATTENTION,
        language="en",
    )
    assert retry is not None
    assert bridge.report_spoken(retry.cue_token, succeeded=True) is True
    assert bridge.report_spoken(retry.cue_token, succeeded=True) is False


def assert_legacy_meal_triggers_dedupe_by_runtime_cue() -> None:
    bridge, runtime, _clock = bridge_at()
    lunch = bridge.request(
        ReminderTrigger.LUNCH,
        attention=ATTENTION,
        language="en",
    )
    assert lunch is not None
    assert bridge.request(
        ReminderTrigger.DINNER,
        attention=ATTENTION,
        language="en",
    ) is None
    assert runtime.decisions == [WellbeingKind.MEAL, WellbeingKind.MEAL]


def assert_stale_and_date_rollover_do_not_commit() -> None:
    bridge, runtime, clock = bridge_at(
        datetime(2027, 1, 9, 23, 59, tzinfo=UTC)
    )
    old = bridge.request(
        ReminderTrigger.REST,
        attention=ATTENTION,
        language="en",
    )
    assert old is not None
    clock.now += timedelta(minutes=2)
    assert bridge.report_spoken(old.cue_token, succeeded=True) is False
    assert runtime.delivery_results == []
    new = bridge.request(
        ReminderTrigger.REST,
        attention=ATTENTION,
        language="en",
    )
    assert new is not None


def assert_disabled_bypass_never_calls_runtime() -> None:
    bridge, runtime, _clock = bridge_at()
    for trigger in ReminderTrigger:
        assert bridge.request(
            trigger,
            attention=ATTENTION,
            language="en",
            enabled=False,
        ) is None
        bridge.command(trigger, ReminderCommand.DISMISS, enabled=False)
    assert runtime.decisions == []
    assert runtime.commands == []


def assert_command_mapping() -> None:
    bridge, runtime, _clock = bridge_at()
    deadline = NOW + timedelta(minutes=30)
    bridge.command("lunch", "acknowledge")
    bridge.command("dinner", "complete")
    bridge.command("overwork", "snooze", snooze_until=deadline)
    bridge.command("rest", "dismiss")
    assert runtime.commands == [
        ("acknowledge", WellbeingKind.MEAL, None),
        ("complete", WellbeingKind.MEAL, None),
        ("snooze", WellbeingKind.PROLONGED_SITTING, deadline),
        ("dismiss", WellbeingKind.REST, None),
    ]
    try:
        bridge.command("hydration", "snooze")
    except WellbeingAppBridgeError:
        pass
    else:
        raise AssertionError("snooze without deadline unexpectedly accepted")


def assert_no_secret_or_sensor_boundary_exists() -> None:
    bridge, _runtime, _clock = bridge_at()
    assert not hasattr(bridge, "api_key")
    assert not hasattr(bridge, "camera")
    assert not hasattr(bridge, "face_identities")
    request = bridge.request(
        ReminderTrigger.HYDRATION,
        attention=ATTENTION,
        language="en",
    )
    assert request is not None
    assert set(request.__dataclass_fields__) == {"text", "source", "cue_token"}


def run() -> None:
    assert_trigger_normalization_and_stable_occurrences()
    assert_four_languages_and_private_override()
    assert_success_failure_dedupe_and_retry()
    assert_legacy_meal_triggers_dedupe_by_runtime_cue()
    assert_stale_and_date_rollover_do_not_commit()
    assert_disabled_bypass_never_calls_runtime()
    assert_command_mapping()
    assert_no_secret_or_sensor_boundary_exists()
    print("WELLBEING_APP_BRIDGE_OK")


if __name__ == "__main__":
    run()
