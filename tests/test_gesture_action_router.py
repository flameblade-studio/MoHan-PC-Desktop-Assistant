from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.gesture_action_router import (
    GestureActionDisposition,
    GestureActionRouter,
    GestureActionSafety,
    GestureTrigger,
)
lazy from domain.gesture_configuration import (
    GestureAction,
    GestureBinding,
    GestureConfiguration,
)


def configured(
    gesture_id: str,
    binding: GestureBinding,
) -> GestureConfiguration:
    configuration = GestureConfiguration(enabled=True)
    definition = configuration.definition(gesture_id).with_binding(binding)
    return configuration.replace_definition(definition)


def assert_disabled_unknown_low_confidence_and_no_action_fail_closed() -> None:
    router = GestureActionRouter()
    disabled = router.route(GestureTrigger("wave", 1.0, 1.0), GestureConfiguration())
    assert disabled.disposition is GestureActionDisposition.DISABLED
    unknown = router.route(
        GestureTrigger("custom:missing", 1.0, 2.0),
        GestureConfiguration(enabled=True),
    )
    assert unknown.disposition is GestureActionDisposition.UNKNOWN_GESTURE
    low = router.route(
        GestureTrigger("wave", 0.77, 3.0),
        GestureConfiguration(enabled=True),
    )
    assert low.disposition is GestureActionDisposition.LOW_CONFIDENCE
    none = router.route(
        GestureTrigger("closed-fist", 0.99, 4.0),
        GestureConfiguration(enabled=True),
    )
    assert none.disposition is GestureActionDisposition.NO_ACTION
    assert not any(decision.executable for decision in (disabled, unknown, low, none))


def assert_local_actions_are_debounced_and_never_execute_in_router() -> None:
    router = GestureActionRouter(cooldown_seconds=2.0)
    configuration = configured("wave", GestureBinding(GestureAction.SHOW_DASHBOARD))
    first = router.route(GestureTrigger("wave", 0.95, 10.0), configuration)
    assert first.executable
    assert first.action is GestureAction.SHOW_DASHBOARD
    assert first.safety is GestureActionSafety.LOCAL_REVERSIBLE
    assert first.command_text == ""
    duplicate = router.route(GestureTrigger("wave", 0.99, 11.0), configuration)
    assert duplicate.disposition is GestureActionDisposition.COOLDOWN
    later = router.route(GestureTrigger("wave", 0.99, 12.0), configuration)
    assert later.executable


def assert_device_cloud_and_custom_commands_preserve_security_boundaries() -> None:
    cases = (
        (
            "open-palm",
            GestureBinding(GestureAction.TOGGLE_LISTENING),
            GestureActionSafety.DEVICE_ACCESS,
        ),
        (
            "open-palm",
            GestureBinding(GestureAction.START_REALTIME),
            GestureActionSafety.CLOUD_SESSION,
        ),
        (
            "open-palm",
            GestureBinding(GestureAction.CUSTOM_COMMAND, "切換陪伴模式"),
            GestureActionSafety.POLICY_ROUTED,
        ),
    )
    for index, (gesture_id, binding, expected_safety) in enumerate(cases, start=1):
        decision = GestureActionRouter().route(
            GestureTrigger(gesture_id, 0.95, float(index)),
            configured(gesture_id, binding),
        )
        assert decision.executable
        assert decision.safety is expected_safety
        assert decision.requires_explicit_runtime_confirmation is (
            expected_safety in {
                GestureActionSafety.DEVICE_ACCESS,
                GestureActionSafety.CLOUD_SESSION,
            }
        )
        assert decision.requires_policy_pipeline is (
            expected_safety is GestureActionSafety.POLICY_ROUTED
        )
    assert cases[-1][1].custom_command == "切換陪伴模式"


def assert_time_order_and_reset_are_explicit() -> None:
    router = GestureActionRouter()
    configuration = GestureConfiguration(enabled=True)
    router.route(GestureTrigger("silence", 1.0, 2.0), configuration)
    try:
        router.route(GestureTrigger("silence", 1.0, 1.0), configuration)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-order gesture trigger was accepted")
    router.reset()
    assert router.route(GestureTrigger("silence", 1.0, 1.0), configuration).executable


def run() -> None:
    assert_disabled_unknown_low_confidence_and_no_action_fail_closed()
    assert_local_actions_are_debounced_and_never_execute_in_router()
    assert_device_cloud_and_custom_commands_preserve_security_boundaries()
    assert_time_order_and_reset_are_explicit()
    print("GESTURE_ACTION_ROUTER_OK")


if __name__ == "__main__":
    run()
