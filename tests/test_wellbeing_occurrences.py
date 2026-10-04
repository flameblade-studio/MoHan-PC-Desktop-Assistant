from __future__ import annotations

lazy import copy
lazy from dataclasses import replace
lazy from datetime import UTC, datetime, timedelta

lazy import pytest

lazy from application.wellbeing_app_bridge import (
    ReminderCommand,
    ReminderTrigger,
    WellbeingAppBridge,
)
lazy from application.wellbeing_reminder import ReminderResponse, ReminderStage, WellbeingKind
lazy from application.wellbeing_runtime import (
    RuntimePolicies,
    WellbeingRuntime,
    WellbeingRuntimeError,
)
lazy from infrastructure.db import StudioDB, StudioDBSettingsPort
lazy from infrastructure.profile_transfer import PortableProfileManager, ProfileTransferError
lazy from infrastructure.special_occasion_store import SpecialOccasionStore
lazy from infrastructure.wellbeing_reminder_store import (
    WELLBEING_STATE_KEY,
    WELLBEING_STATE_VERSION,
    WellbeingReminderStore,
    WellbeingReminderStoreError,
)
lazy from tests.test_wellbeing_runtime import ATTENTION, MutableClock, runtime_at

NOW = datetime(2027, 1, 9, 12, tzinfo=UTC)
LEGACY_COOLDOWN_SECONDS = 7200
MEAL_REINFORCEMENT_BUDGET = 2
EXPECTED_OCCURRENCE_PAIR_COUNT = 2


def request(bridge, trigger):
    return bridge.request(trigger, attention=ATTENTION, language="en")


def restarted_bridge(settings, occasion, clock):
    runtime = WellbeingRuntime(
        WellbeingReminderStore(settings),
        SpecialOccasionStore(occasion),
        clock=clock,
        policies=RuntimePolicies(wellbeing_eligibility=lambda *_args: True),
    )
    return WellbeingAppBridge(runtime, clock=clock)


@pytest.mark.parametrize("command", tuple(ReminderCommand))
def test_lunch_response_leaves_dinner_independent_after_restart(command):
    runtime, clock, settings, occasion = runtime_at(NOW)
    bridge = WellbeingAppBridge(runtime, clock=clock)
    lunch = request(bridge, ReminderTrigger.LUNCH)
    assert lunch is not None
    assert bridge.report_spoken(lunch.cue_token, succeeded=True)
    bridge.command("lunch", command, snooze_until=NOW + timedelta(hours=8))
    clock.now += timedelta(hours=6)
    bridge = restarted_bridge(settings, occasion, clock)
    assert request(bridge, "lunch") is None
    dinner = request(bridge, "dinner")
    assert dinner is not None, "A#11: lunch response suppressed same-day dinner"
    assert dinner.cue_token != lunch.cue_token
    assert bridge.report_spoken(dinner.cue_token, succeeded=True)
    assert bridge.report_spoken(dinner.cue_token, succeeded=True) is False
    bridge = restarted_bridge(settings, occasion, clock)
    assert request(bridge, "dinner") is None


@pytest.mark.parametrize("budget", [1, 2])
def test_occurrences_share_kind_budget_and_cooldown_at_decision_and_delivery(budget):
    runtime, clock, settings, _occasion = runtime_at(NOW)
    store = WellbeingReminderStore(settings)
    store.save(store.update_kind(
        store.load(NOW), WellbeingKind.MEAL, maximum_daily_reinforcements=budget
    ))
    for name in ("lunch", "dinner"):
        cue = runtime.decide_wellbeing(
            WellbeingKind.MEAL, ATTENTION, event_id=f"2027-01-09:trigger:{name}"
        )
        assert cue is not None
        assert runtime.record_delivery(cue, succeeded=True)
    clock.now += timedelta(minutes=16)
    lunch = runtime.decide_wellbeing(
        WellbeingKind.MEAL, ATTENTION, event_id="2027-01-09:trigger:lunch"
    )
    dinner = runtime.decide_wellbeing(
        WellbeingKind.MEAL, ATTENTION, event_id="2027-01-09:trigger:dinner"
    )
    assert lunch is not None and dinner is not None
    assert lunch.cue.stage is ReminderStage.RESTRAINED_REINFORCEMENT
    assert runtime.record_delivery(lunch, succeeded=True)
    # Dinner's decision preceded lunch's delivery. Recheck the shared limits
    # when committing this now-stale decision, as well as on the next request.
    assert runtime.record_delivery(dinner, succeeded=True) is False
    assert runtime.decide_wellbeing(
        WellbeingKind.MEAL, ATTENTION, event_id="2027-01-09:trigger:dinner"
    ) is None
    clock.now += timedelta(hours=3)
    next_cue = runtime.decide_wellbeing(
        WellbeingKind.MEAL, ATTENTION, event_id="2027-01-09:trigger:dinner"
    )
    if budget == 1:
        assert next_cue is None
    else:
        assert next_cue is not None
        assert runtime.record_delivery(next_cue, succeeded=True)
    item = store.load(clock.now).for_kind(WellbeingKind.MEAL)
    assert item.daily_reinforcement_count == budget


def test_snooze_rollover_retains_only_that_occurrence_and_expires_after_restart():
    runtime, clock, settings, occasion = runtime_at(NOW)
    bridge = WellbeingAppBridge(runtime, clock=clock)
    deadline = NOW + timedelta(days=1, hours=1)
    bridge.command("lunch", "snooze", snooze_until=deadline)
    clock.now += timedelta(days=1)
    bridge = restarted_bridge(settings, occasion, clock)
    assert request(bridge, "lunch") is None
    dinner = request(bridge, "dinner")
    assert dinner is not None
    assert bridge.report_spoken(dinner.cue_token, succeeded=True)
    clock.now = deadline
    bridge = restarted_bridge(settings, occasion, clock)
    lunch = request(bridge, "lunch")
    assert lunch is not None
    assert bridge.approved_cue(lunch.cue_token).stage is ReminderStage.INITIAL
    assert bridge.report_spoken(lunch.cue_token, succeeded=True)
    state = WellbeingReminderStore(settings).load(clock.now)
    assert set(state.occurrences) == {"2027-01-10:trigger:lunch", "2027-01-10:trigger:dinner"}


def test_failed_delivery_and_failed_persistence_do_not_consume_an_occurrence():
    runtime, clock, settings, _occasion = runtime_at(NOW)
    bridge = WellbeingAppBridge(runtime, clock=clock)
    lunch = request(bridge, "lunch")
    assert lunch is not None
    assert bridge.report_spoken(lunch.cue_token, succeeded=False) is False
    assert settings.values == {}
    lunch = request(bridge, "lunch")
    assert lunch is not None
    settings.fail_write = True
    with pytest.raises(WellbeingReminderStoreError):
        bridge.report_spoken(lunch.cue_token, succeeded=True)
    assert settings.values == {}
    settings.fail_write = False
    lunch = request(bridge, "lunch")
    assert lunch is not None
    assert bridge.report_spoken(lunch.cue_token, succeeded=True)


@pytest.mark.parametrize("response", tuple(ReminderResponse))
def test_v1_kind_state_is_read_conservatively_and_migrates_without_guessing(response):
    _runtime, clock, settings, occasion = runtime_at(NOW)
    store = WellbeingReminderStore(settings)
    state = store.update_kind(
        store.load(NOW), WellbeingKind.MEAL,
        response=response, initial_delivered_at=NOW,
        snooze_until=NOW + timedelta(hours=8) if response is ReminderResponse.SNOOZED else None,
        daily_reinforcement_count=1, last_same_kind_reinforcement_at=NOW,
    )
    store.save(state)
    legacy = copy.deepcopy(settings.values[WELLBEING_STATE_KEY])
    legacy["version"] = 1
    legacy.pop("occurrences")
    settings.values[WELLBEING_STATE_KEY] = legacy
    assert store.load(NOW) == state
    bridge = restarted_bridge(settings, occasion, clock)
    # V1 cannot identify a meal. Never turn a delivered/completed legacy meal
    # into two fresh initial reminders during that same local day.
    assert request(bridge, "lunch") is None
    assert request(bridge, "dinner") is None
    migrated = store.export_portable(NOW)
    assert migrated["version"] == WELLBEING_STATE_VERSION
    assert migrated["kinds"] == legacy["kinds"]
    assert migrated["occurrences"] == {}
    assert store.import_portable(migrated, NOW) == state
    clock.now += timedelta(days=1)
    bridge = restarted_bridge(settings, occasion, clock)
    lunch = request(bridge, "lunch")
    assert lunch is not None
    assert bridge.report_spoken(lunch.cue_token, succeeded=True)
    bridge.command("lunch", "complete")
    assert request(bridge, "dinner") is not None


def test_legacy_cross_day_snooze_and_kind_preferences_remain_shared():
    _runtime, clock, settings, occasion = runtime_at(NOW)
    store = WellbeingReminderStore(settings)
    state = store.update_kind(
        store.load(NOW), WellbeingKind.MEAL,
        snooze_until=NOW + timedelta(days=2), response=ReminderResponse.SNOOZED,
        maximum_daily_reinforcements=1, same_kind_cooldown_seconds=LEGACY_COOLDOWN_SECONDS,
    )
    store.save(state)
    legacy = settings.values[WELLBEING_STATE_KEY]
    legacy["version"] = 1
    legacy.pop("occurrences")
    clock.now += timedelta(days=1)
    bridge = restarted_bridge(settings, occasion, clock)
    assert request(bridge, "lunch") is None
    assert request(bridge, "dinner") is None
    item = store.load(clock.now).for_kind(WellbeingKind.MEAL)
    assert item.maximum_daily_reinforcements == 1
    assert item.same_kind_cooldown_seconds == LEGACY_COOLDOWN_SECONDS


@pytest.mark.parametrize("damage", ["missing", "kind", "date", "response", "history", "naive"])
def test_invalid_v2_occurrences_fail_closed_without_replacing_saved_state(damage):
    runtime, clock, settings, _occasion = runtime_at(NOW)
    bridge = WellbeingAppBridge(runtime, clock=clock)
    lunch = request(bridge, "lunch")
    assert lunch is not None
    assert bridge.report_spoken(lunch.cue_token, succeeded=True)
    payload = copy.deepcopy(settings.values[WELLBEING_STATE_KEY])
    entry = payload["occurrences"]["2027-01-09:trigger:lunch"]
    if damage == "missing":
        payload.pop("occurrences")
    elif damage in {"kind", "date"}:
        key = "2027-01-09:trigger:unknown" if damage == "kind" else "2027-01-08:trigger:lunch"
        payload["occurrences"] = {key: entry}
    elif damage == "response":
        entry["response"] = "unknown"
    elif damage == "history":
        entry["reinforcement_delivered_at"] = (NOW - timedelta(hours=1)).isoformat()
    else:
        entry["snooze_until"] = "2027-01-09T14:00:00"
    before = copy.deepcopy(settings.values)
    store = WellbeingReminderStore(settings)
    with pytest.raises(WellbeingReminderStoreError):
        store.import_portable(payload, NOW)
    assert settings.values == before
    settings.values[WELLBEING_STATE_KEY] = payload
    with pytest.raises(WellbeingReminderStoreError):
        request(bridge, "dinner")


def test_wrong_kind_stale_day_and_tampered_occurrence_are_rejected():
    runtime, clock, _settings, _occasion = runtime_at(NOW)
    for event_id in ("2027-01-09:trigger:hydration", "2027-01-08:trigger:lunch", ""):
        with pytest.raises(WellbeingRuntimeError):
            runtime.decide_wellbeing(WellbeingKind.MEAL, ATTENTION, event_id=event_id)
    cue = runtime.decide_wellbeing(
        WellbeingKind.MEAL, ATTENTION, event_id="2027-01-09:trigger:lunch"
    )
    assert cue is not None
    tampered = replace(cue, cue=replace(cue.cue, event_id="2027-01-09:trigger:dinner"))
    with pytest.raises(WellbeingRuntimeError):
        runtime.record_delivery(tampered, succeeded=True)
    clock.now += timedelta(days=1)
    assert runtime.record_delivery(cue, succeeded=True) is False


def test_sqlite_restart_profile_transfer_and_snapshot_delivery_deduplication(tmp_path):
    clock = MutableClock(NOW)
    source_path = tmp_path / "source.db"
    source = StudioDB(source_path)
    port = StudioDBSettingsPort(source)
    bridge = restarted_bridge(port, port, clock)
    lunch = request(bridge, "lunch")
    assert lunch is not None
    assert bridge.report_spoken(lunch.cue_token, succeeded=True)
    clock.now += timedelta(minutes=16)
    reinforcement = request(bridge, "lunch")
    assert reinforcement is not None
    assert bridge.report_spoken(reinforcement.cue_token, succeeded=True)
    bridge.command("lunch", "complete")
    clock.now = NOW + timedelta(hours=6)
    dinner = request(bridge, "dinner")
    assert dinner is not None
    assert bridge.report_spoken(dinner.cue_token, succeeded=True)
    bridge.command("dinner", "snooze", snooze_until=clock.now + timedelta(minutes=30))
    expected = WellbeingReminderStore(port).export_portable(clock.now)
    source.close()

    source = StudioDB(source_path)
    target = StudioDB(tmp_path / "target.db")
    try:
        port = StudioDBSettingsPort(source)
        bridge = restarted_bridge(port, port, clock)
        assert request(bridge, "lunch") is None
        assert request(bridge, "dinner") is None
        assert WellbeingReminderStore(port).export_portable(clock.now) == expected
        bundle, _manifest = PortableProfileManager(
            source, tmp_path / "source-backups"
        ).export_profile(tmp_path / "reminders")
        manager = PortableProfileManager(target, tmp_path / "target-backups")
        manager.import_profile(bundle)
        target_port = StudioDBSettingsPort(target)
        store = WellbeingReminderStore(target_port)
        assert store.export_portable(clock.now) == expected
        before = target.setting(WELLBEING_STATE_KEY)
        with pytest.raises(ProfileTransferError, match="已匯入過"):
            manager.import_profile(bundle)
        assert target.setting(WELLBEING_STATE_KEY) == before
        bridge = restarted_bridge(target_port, target_port, clock)
        assert request(bridge, "lunch") is None
        assert request(bridge, "dinner") is None
        clock.now += timedelta(minutes=30)
        bridge = restarted_bridge(target_port, target_port, clock)
        resumed = request(bridge, "dinner")
        assert resumed is not None
        assert bridge.approved_cue(resumed.cue_token).stage is ReminderStage.RESTRAINED_REINFORCEMENT
        assert bridge.report_spoken(resumed.cue_token, succeeded=True)
        assert bridge.report_spoken(resumed.cue_token, succeeded=True) is False
        assert (
            store.load(clock.now).for_kind(WellbeingKind.MEAL).daily_reinforcement_count
            == MEAL_REINFORCEMENT_BUDGET
        )
        bridge = restarted_bridge(target_port, target_port, clock)
        assert request(bridge, "lunch") is None
        assert request(bridge, "dinner") is None
    finally:
        source.close()
        target.close()


def test_pending_lunch_and_dinner_have_distinct_delivery_tokens():
    runtime, clock, _settings, _occasion = runtime_at(NOW)
    bridge = WellbeingAppBridge(runtime, clock=clock)
    lunch = request(bridge, "lunch")
    dinner = request(bridge, "dinner")
    assert lunch is not None
    assert dinner is not None, "A#11: separate pending occurrences share a token"
    assert dinner.cue_token != lunch.cue_token
    assert request(bridge, "lunch") is None
    assert request(bridge, "dinner") is None
    assert bridge.report_spoken(lunch.cue_token, succeeded=True)
    assert bridge.report_spoken(dinner.cue_token, succeeded=True)


def test_delivery_deduplicates_after_runtime_restart_and_reinforcement_rollback():
    runtime, clock, settings, occasion = runtime_at(NOW)
    event_id = "2027-01-09:trigger:lunch"
    initial = runtime.decide_wellbeing(WellbeingKind.MEAL, ATTENTION, event_id=event_id)
    assert initial is not None
    assert runtime.record_delivery(initial, succeeded=True)
    runtime = WellbeingRuntime(
        WellbeingReminderStore(settings), SpecialOccasionStore(occasion), clock=clock,
        policies=RuntimePolicies(wellbeing_eligibility=lambda *_args: True),
    )
    assert runtime.record_delivery(initial, succeeded=True) is False
    clock.now += timedelta(minutes=16)
    cue = runtime.decide_wellbeing(WellbeingKind.MEAL, ATTENTION, event_id=event_id)
    assert cue is not None
    before = copy.deepcopy(settings.values)
    settings.fail_write = True
    with pytest.raises(WellbeingReminderStoreError):
        runtime.record_delivery(cue, succeeded=True)
    assert settings.values == before
    settings.fail_write = False
    assert runtime.record_delivery(cue, succeeded=True)
    assert runtime.record_delivery(cue, succeeded=True) is False
    state = WellbeingReminderStore(settings).load(clock.now)
    assert state.for_kind(WellbeingKind.MEAL).daily_reinforcement_count == 1
    assert state.for_occurrence(WellbeingKind.MEAL, event_id).reinforcement_delivered_at == clock.now


def test_v1_profile_transfer_retains_legacy_suppression_and_upgrades_on_save(tmp_path):
    source = StudioDB(tmp_path / "source.db")
    target = StudioDB(tmp_path / "target.db")
    try:
        source_store = WellbeingReminderStore(StudioDBSettingsPort(source))
        legacy = source_store.export_portable(NOW)
        legacy["version"] = 1
        legacy.pop("occurrences")
        legacy["kinds"]["meal"]["response"] = "completed"
        legacy["kinds"]["meal"]["initial_delivered_at"] = NOW.isoformat()
        source.set_setting(WELLBEING_STATE_KEY, legacy)
        bundle, _manifest = PortableProfileManager(
            source, tmp_path / "source-backups"
        ).export_profile(tmp_path / "legacy")
        PortableProfileManager(target, tmp_path / "target-backups").import_profile(bundle)
        port = StudioDBSettingsPort(target)
        clock = MutableClock(NOW)
        bridge = restarted_bridge(port, port, clock)
        assert request(bridge, "lunch") is None
        assert request(bridge, "dinner") is None
        store = WellbeingReminderStore(port)
        store.save(store.load(NOW))
        assert target.setting(WELLBEING_STATE_KEY)["version"] == WELLBEING_STATE_VERSION
        assert store.export_portable(NOW)["kinds"] == legacy["kinds"]
    finally:
        source.close()
        target.close()


@pytest.mark.parametrize("first,second", [
    ("overwork", "prolonged_sitting"), ("prolonged_sitting", "overwork"),
])
def test_same_kind_triggers_are_independent_in_both_orders(first, second):
    runtime, clock, settings, _occasion = runtime_at(NOW)
    bridge = WellbeingAppBridge(runtime, clock=clock)
    initial = request(bridge, first)
    assert initial is not None
    assert bridge.report_spoken(initial.cue_token, succeeded=True)
    bridge.command(first, "complete")
    next_request = request(bridge, second)
    assert next_request is not None
    assert bridge.approved_cue(next_request.cue_token).stage is ReminderStage.INITIAL
    assert bridge.report_spoken(next_request.cue_token, succeeded=True)
    assert len(WellbeingReminderStore(settings).load(NOW).occurrences) == EXPECTED_OCCURRENCE_PAIR_COUNT


def test_every_bridge_trigger_persists_as_an_occurrence():
    runtime, clock, settings, _occasion = runtime_at(NOW)
    bridge = WellbeingAppBridge(runtime, clock=clock)
    for trigger in ReminderTrigger:
        bridge.command(trigger, "snooze", snooze_until=NOW + timedelta(hours=1))
    state = WellbeingReminderStore(settings).load(NOW)
    assert len(state.occurrences) == len(ReminderTrigger)
    assert all(item.response is ReminderResponse.NONE for item in state.kinds.values())
