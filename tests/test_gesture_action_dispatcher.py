from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.gesture_action_dispatcher import (
    GestureActionDispatcher,
    GestureDispatchDisposition,
)
lazy from application.gesture_action_router import (
    GestureActionDecision,
    GestureActionDisposition,
    GestureActionSafety,
)
lazy from domain.gesture_configuration import GestureAction, GestureSource


class ActionRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def show_control_center(self) -> None:
        self.calls.append(("show", None))

    def hide_control_center(self) -> None:
        self.calls.append(("hide", None))

    def set_audio_muted(self, muted: bool) -> None:
        self.calls.append(("muted", muted))

    def stop_current_speech(self) -> None:
        self.calls.append(("stop-speech", None))

    def toggle_listening(self) -> None:
        self.calls.append(("toggle-listening", None))

    def set_realtime_enabled(self, enabled: bool) -> None:
        self.calls.append(("realtime", enabled))

    def set_interaction_mode(self, mode: str) -> None:
        self.calls.append(("mode", mode))

    def acknowledge_positive(self) -> None:
        self.calls.append(("positive", None))

    def submit_safe_text_command(self, command: str) -> None:
        self.calls.append(("safe-command", command))


def ready(
    action: GestureAction,
    safety: GestureActionSafety,
    *,
    command: str = "",
) -> GestureActionDecision:
    return GestureActionDecision(
        GestureActionDisposition.READY,
        "custom:test" if command else "wave",
        action,
        safety,
        command,
        GestureSource.CUSTOM if command else GestureSource.BUILTIN,
    )


def assert_local_actions_use_one_explicit_port() -> None:
    recorder = ActionRecorder()
    dispatcher = GestureActionDispatcher(recorder)
    cases = (
        (GestureAction.SHOW_DASHBOARD, ("show", None)),
        (GestureAction.HIDE_DASHBOARD, ("hide", None)),
        (GestureAction.MUTE_AUDIO, ("muted", True)),
        (GestureAction.UNMUTE_AUDIO, ("muted", False)),
        (GestureAction.STOP_SPEECH, ("stop-speech", None)),
        (GestureAction.STOP_REALTIME, ("realtime", False)),
        (GestureAction.WORK_MODE, ("mode", "work")),
        (GestureAction.COMPANION_MODE, ("mode", "companion")),
        (GestureAction.DO_NOT_DISTURB_MODE, ("mode", "do-not-disturb")),
        (GestureAction.POSITIVE_ACKNOWLEDGEMENT, ("positive", None)),
    )
    for action, expected in cases:
        result = dispatcher.dispatch(
            ready(action, GestureActionSafety.LOCAL_REVERSIBLE)
        )
        assert result.executed
        assert recorder.calls[-1] == expected


def assert_device_and_cloud_actions_require_authorization() -> None:
    recorder = ActionRecorder()
    listening = ready(
        GestureAction.TOGGLE_LISTENING,
        GestureActionSafety.DEVICE_ACCESS,
    )
    missing = GestureActionDispatcher(recorder).dispatch(listening)
    assert missing.disposition is GestureDispatchDisposition.CONFIRMATION_REQUIRED
    assert recorder.calls == []
    denied = GestureActionDispatcher(
        recorder,
        authorize=lambda _decision: False,
    ).dispatch(listening)
    assert denied.disposition is GestureDispatchDisposition.DENIED
    assert recorder.calls == []
    realtime = ready(
        GestureAction.START_REALTIME,
        GestureActionSafety.CLOUD_SESSION,
    )
    accepted = GestureActionDispatcher(
        recorder,
        authorize=lambda _decision: True,
    ).dispatch(realtime)
    assert accepted.executed
    assert recorder.calls == [("realtime", True)]


def assert_custom_text_only_enters_the_existing_safe_command_port() -> None:
    recorder = ActionRecorder()
    decision = ready(
        GestureAction.CUSTOM_COMMAND,
        GestureActionSafety.POLICY_ROUTED,
        command="幫我開啟工作資料夾",
    )
    result = GestureActionDispatcher(recorder).dispatch(decision)
    assert result.executed
    assert recorder.calls == [("safe-command", "幫我開啟工作資料夾")]


def assert_blocked_and_failed_decisions_never_escape() -> None:
    recorder = ActionRecorder()
    blocked = GestureActionDecision(
        GestureActionDisposition.LOW_CONFIDENCE,
        "wave",
    )
    ignored = GestureActionDispatcher(recorder).dispatch(blocked)
    assert ignored.disposition is GestureDispatchDisposition.IGNORED
    assert recorder.calls == []

    class FailingRecorder(ActionRecorder):
        def show_control_center(self) -> None:
            raise RuntimeError("private backend detail")

    failed = GestureActionDispatcher(FailingRecorder()).dispatch(
        ready(
            GestureAction.SHOW_DASHBOARD,
            GestureActionSafety.LOCAL_REVERSIBLE,
        )
    )
    assert failed.disposition is GestureDispatchDisposition.FAILED
    assert failed.reason_code == "action-boundary-failed"
    assert "private" not in failed.reason_code


def run() -> None:
    assert_local_actions_use_one_explicit_port()
    assert_device_and_cloud_actions_require_authorization()
    assert_custom_text_only_enters_the_existing_safe_command_port()
    assert_blocked_and_failed_decisions_never_escape()
    print("GESTURE_ACTION_DISPATCHER_OK")


if __name__ == "__main__":
    run()
