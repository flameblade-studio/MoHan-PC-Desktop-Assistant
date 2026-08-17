from __future__ import annotations

lazy import sys
lazy from dataclasses import replace
lazy from datetime import UTC, datetime
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from companion_phrasebook import CompanionPhrasebook
lazy from companion_proactivity_preferences import CompanionProactivityPreferences
lazy from multisensory_interaction import InteractionKind, ProactiveInteraction
lazy from proactive_companion_app_bridge import (
    ProactiveAppDisposition,
    ProactiveAppEvent,
    ProactiveAppState,
    ProactiveCompanionAppBridge,
)
lazy from proactive_companion_runtime import (
    CandidatePriority,
    ProactiveCompanionRequest,
    ProactiveSource,
)
lazy from visual_perception import PresenceState
lazy from wellbeing_app_bridge import ReminderTrigger, SpeakRequest

NOW = datetime(2027, 1, 8, 12, tzinfo=UTC)


class Preferences:
    def __init__(self) -> None:
        self.value = CompanionProactivityPreferences()
        self.fail = False

    def load(self):
        if self.fail:
            raise RuntimeError("settings failed")
        return self.value


class Phrasebook:
    def __init__(self) -> None:
        self.value = CompanionPhrasebook({}, (), {})
        self.loads = 0

    def load(self):
        self.loads += 1
        return self.value


class Runtime:
    def __init__(self) -> None:
        self.environments = []
        self.reports: list[tuple[str, bool]] = []
        self.return_request = True

    def propose(self, environment, _preferences):
        self.environments.append(environment)
        if not self.return_request:
            return None
        token = f"token-{len(self.environments)}"
        speak = SpeakRequest("A neutral reminder.", "wellbeing", token)
        performance = ProactiveInteraction(InteractionKind.GENTLE_CHECK_IN, "gentle")
        return ProactiveCompanionRequest(
            speak,
            performance,
            ProactiveSource.WELLBEING,
            CandidatePriority.MEAL,
            token,
        )

    def report_spoken(self, token, *, succeeded):
        self.reports.append((token, succeeded))
        return succeeded


class Factory:
    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime
        self.phrasebooks = []

    def __call__(self, phrasebook):
        self.phrasebooks.append(phrasebook)
        return self.runtime


class Speech:
    def __init__(self) -> None:
        self.submissions = []
        self.accept = True

    def submit(self, request, performance, *, generation, completed):
        self.submissions.append((request, performance, generation, completed))
        return self.accept

    def finish(self, index: int, succeeded: bool) -> None:
        self.submissions[index][3](succeeded)


def state(**changes: object) -> ProactiveAppState:
    value = ProactiveAppState(
        generation=1,
        now=NOW,
        language="en",
        user_title="there",
        session_user_active=True,
        camera_enabled=False,
    )
    return replace(value, **changes)


def bridge():
    runtime = Runtime()
    preferences = Preferences()
    phrasebook = Phrasebook()
    speech = Speech()
    factory = Factory(runtime)
    app_bridge = ProactiveCompanionAppBridge(
        factory,
        preferences,
        phrasebook,
        speech,
    )
    return app_bridge, runtime, preferences, phrasebook, speech, factory


def assert_timer_triggers_normalize_without_visual_identity_claim() -> None:
    triggers = tuple(ReminderTrigger)
    for trigger in triggers:
        app_bridge, runtime, _prefs, _phrases, speech, _factory = bridge()
        result = app_bridge.dispatch(ProactiveAppEvent(state(), trigger))
        assert result.disposition is ProactiveAppDisposition.SUBMITTED
        environment = runtime.environments[-1]
        assert environment.reminder_trigger is trigger
        assert environment.user_present
        assert environment.absence_duration_seconds == 0.0
        assert len(speech.submissions) == 1


def assert_visual_presence_and_absence_are_normalized_only_when_enabled() -> None:
    app_bridge, runtime, *_ = bridge()
    visual = state(
        camera_enabled=True,
        camera_presence=PresenceState.PRESENT,
        camera_absence_seconds=600.0,
        recognized_user=True,
        visual_presence_arrival=True,
    )
    app_bridge.dispatch(ProactiveAppEvent(visual))
    environment = runtime.environments[-1]
    assert environment.user_present
    assert environment.absence_duration_seconds == 600.0
    assert environment.visual_presence_arrival
    try:
        state(recognized_user=True)
    except ValueError:
        pass
    else:
        raise AssertionError("Disabled camera must not claim user recognition")


def assert_speech_port_is_used_and_two_phase_commit_waits_for_callback() -> None:
    app_bridge, runtime, _prefs, _phrases, speech, _factory = bridge()
    result = app_bridge.dispatch(
        ProactiveAppEvent(state(), ReminderTrigger.LUNCH)
    )
    assert result.request is not None
    assert runtime.reports == []
    submitted = speech.submissions[0]
    assert submitted[0] is result.request.speak
    assert submitted[1] is result.request.performance
    speech.finish(0, True)
    assert runtime.reports == [(result.request.delivery_token, True)]
    speech.finish(0, True)
    assert len(runtime.reports) == 1


def assert_failure_does_not_commit_and_releases_pending() -> None:
    app_bridge, runtime, _prefs, _phrases, speech, _factory = bridge()
    result = app_bridge.dispatch(ProactiveAppEvent(state()))
    assert result.request is not None
    speech.finish(0, False)
    assert runtime.reports == [(result.request.delivery_token, False)]
    app_bridge, runtime, _prefs, _phrases, speech, _factory = bridge()
    speech.accept = False
    result = app_bridge.dispatch(ProactiveAppEvent(state()))
    assert result.disposition is ProactiveAppDisposition.LKG
    assert runtime.reports == [("token-1", False)]


def assert_generation_stale_dedupe_and_lkg() -> None:
    app_bridge, runtime, preferences, _phrases, speech, _factory = bridge()
    current = ProactiveAppEvent(state(generation=3))
    assert app_bridge.dispatch(current).disposition is ProactiveAppDisposition.SUBMITTED
    assert app_bridge.dispatch(current).disposition is ProactiveAppDisposition.DUPLICATE
    stale = app_bridge.dispatch(ProactiveAppEvent(state(generation=2)))
    assert stale.disposition is ProactiveAppDisposition.STALE
    assert len(speech.submissions) == 1
    speech.finish(0, True)
    preferences.fail = True
    failed = app_bridge.dispatch(
        ProactiveAppEvent(state(generation=4, now=NOW.replace(minute=1)))
    )
    assert failed.disposition is ProactiveAppDisposition.LKG
    assert failed.request is app_bridge.last_known_good
    assert len(runtime.environments) == 1


def assert_disabled_and_close_are_complete_bypasses() -> None:
    app_bridge, runtime, _prefs, phrasebook, speech, factory = bridge()
    assert phrasebook.loads == 1 and factory.phrasebooks == [phrasebook.value]
    disabled = app_bridge.dispatch(ProactiveAppEvent(state(enabled=False)))
    assert disabled.disposition is ProactiveAppDisposition.BYPASSED
    assert not runtime.environments and not speech.submissions
    active = app_bridge.dispatch(
        ProactiveAppEvent(state(generation=2), ReminderTrigger.REST)
    )
    assert active.request is not None
    app_bridge.close()
    assert runtime.reports == [(active.request.delivery_token, False)]
    closed = app_bridge.dispatch(ProactiveAppEvent(state(generation=3)))
    assert closed.disposition is ProactiveAppDisposition.CLOSED
    assert len(speech.submissions) == 1


def assert_stale_completion_cannot_commit() -> None:
    app_bridge, runtime, *_rest = bridge()
    first = app_bridge.dispatch(ProactiveAppEvent(state(generation=1)))
    assert first.request is not None
    second = app_bridge.dispatch(
        ProactiveAppEvent(state(generation=2, now=NOW.replace(minute=1)))
    )
    assert second.request is not None
    speech = _rest[2]
    speech.finish(0, True)
    assert runtime.reports[0] == (first.request.delivery_token, False)
    speech.finish(1, True)
    assert runtime.reports[1] == (second.request.delivery_token, True)


def assert_newer_bypass_does_not_invalidate_active_delivery() -> None:
    app_bridge, runtime, _preferences, _phrases, speech, _factory = bridge()
    first = app_bridge.dispatch(ProactiveAppEvent(state(generation=1)))
    assert first.request is not None
    runtime.return_request = False
    bypass = app_bridge.dispatch(
        ProactiveAppEvent(state(generation=2, now=NOW.replace(minute=1)))
    )
    assert bypass.disposition is ProactiveAppDisposition.BYPASSED
    speech.finish(0, True)
    assert runtime.reports == [(first.request.delivery_token, True)]


def assert_timer_uses_active_session_even_when_camera_reports_away() -> None:
    app_bridge, runtime, *_ = bridge()
    away = state(
        camera_enabled=True,
        camera_presence=PresenceState.AWAY,
        camera_absence_seconds=600.0,
        session_user_active=True,
    )
    app_bridge.dispatch(ProactiveAppEvent(away, ReminderTrigger.HYDRATION))
    environment = runtime.environments[-1]
    assert environment.user_present
    assert environment.absence_duration_seconds == 600.0


def assert_focus_meeting_fullscreen_and_speech_pass_through() -> None:
    app_bridge, runtime, *_ = bridge()
    app_bridge.dispatch(
        ProactiveAppEvent(
            state(
                focus_active=True,
                meeting_active=True,
                fullscreen_active=True,
                speech_active=True,
            ),
            ReminderTrigger.OVERWORK,
        )
    )
    environment = runtime.environments[-1]
    assert environment.focus_active
    assert environment.meeting_active
    assert environment.fullscreen_active
    assert environment.speech_active


def assert_pending_speech_is_bounded_superseded_and_expires() -> None:
    app_bridge, runtime, _prefs, _phrases, speech, _factory = bridge()
    first = app_bridge.dispatch(ProactiveAppEvent(state(generation=1)))
    assert first.request is not None
    same_generation = app_bridge.dispatch(
        ProactiveAppEvent(state(generation=1, now=NOW.replace(minute=1)))
    )
    assert same_generation.disposition is ProactiveAppDisposition.DUPLICATE
    assert len(app_bridge._pending) == 1

    replacement = app_bridge.dispatch(
        ProactiveAppEvent(state(generation=2, now=NOW.replace(minute=2)))
    )
    assert replacement.request is not None
    assert runtime.reports == [(first.request.delivery_token, False)]
    assert len(app_bridge._pending) == 1

    expired = app_bridge.dispatch(
        ProactiveAppEvent(state(generation=3, now=NOW.replace(minute=8)))
    )
    assert expired.request is not None
    assert runtime.reports[-1] == (replacement.request.delivery_token, False)
    assert len(app_bridge._pending) == 1
    speech.finish(0, True)
    speech.finish(1, True)
    assert len(runtime.reports) == 2


def run() -> None:
    assert_timer_triggers_normalize_without_visual_identity_claim()
    assert_visual_presence_and_absence_are_normalized_only_when_enabled()
    assert_speech_port_is_used_and_two_phase_commit_waits_for_callback()
    assert_failure_does_not_commit_and_releases_pending()
    assert_generation_stale_dedupe_and_lkg()
    assert_disabled_and_close_are_complete_bypasses()
    assert_stale_completion_cannot_commit()
    assert_newer_bypass_does_not_invalidate_active_delivery()
    assert_timer_uses_active_session_even_when_camera_reports_away()
    assert_focus_meeting_fullscreen_and_speech_pass_through()
    assert_pending_speech_is_bounded_superseded_and_expires()
    print("PROACTIVE_COMPANION_APP_BRIDGE_OK")


if __name__ == "__main__":
    run()
