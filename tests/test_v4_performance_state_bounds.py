from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.appearance_session import (
    APPEARANCE_SLOTS,
    AppearanceComponent,
    AppearanceSelection,
    AppearanceSession,
)
lazy from application.behavior_director import (
    BehaviorDirector,
    BehaviorInput,
    SemanticEmotion,
    SpeechLifecycle,
)
lazy from application.cloud_vision_runtime import (
    CloudVisionFrame,
    CloudVisionRuntime,
    CloudVisionStatus,
    SavedVisionAuthorization,
)
lazy from integrations.openai_vision_provider import (
    VisionProviderResult,
    VisionResultStatus,
)
lazy from domain.openai_vision_preferences import PREFERENCES_VERSION, OpenAIVisionPreferences

RECENT_HISTORY_BOUND = 3
EXPECTED_PREVIEW_CALLS = 2_000


def test_behavior_director_recent_history_has_a_hard_three_item_bound() -> None:
    director = BehaviorDirector(clock=lambda: 10_000.0, seed=7, cooldown_ms=0)
    for index in range(2_000):
        director.direct(_behavior_input(f"action-{index}"))

    assert director._recent.maxlen == RECENT_HISTORY_BOUND
    assert len(director._recent) == RECENT_HISTORY_BOUND
    assert tuple(director._recent) == (
        "action-1997",
        "action-1998",
        "action-1999",
    )


def test_cloud_vision_quota_history_never_exceeds_saved_limits() -> None:
    clock = _Clock()
    preferences = OpenAIVisionPreferences(
        enabled=True,
        cloud_vision_enabled=True,
        daily_limit=80,
        per_minute_limit=4,
    )
    runtime = CloudVisionRuntime(
        _VisionProvider(),
        _AuthorizationSource(
            SavedVisionAuthorization(preferences, PREFERENCES_VERSION, 1, True)
        ),
        clock=clock,
    )

    operation_id = 0
    for minute in range(30):
        clock.now = 1_800_000_000.0 + minute * 61.0
        for _ in range(12):
            operation_id += 1
            runtime.analyze(_cloud_frame(operation_id))
        assert len(runtime._minute_requests) <= preferences.per_minute_limit
        assert len(runtime._daily_requests) <= preferences.daily_limit

    assert len(runtime._daily_requests) == preferences.daily_limit
    assert runtime.analyze(_cloud_frame(operation_id + 1)).status is (
        CloudVisionStatus.DAILY_QUOTA_EXHAUSTED
    )


def test_appearance_session_state_is_fixed_to_declared_slots() -> None:
    selection = AppearanceSelection(*(None for _slot in APPEARANCE_SLOTS))
    preview = _Preview()
    session = AppearanceSession(selection, _Resolver(), preview, _Committer())

    for index in range(2_000):
        slot = APPEARANCE_SLOTS[index % len(APPEARANCE_SLOTS)]
        session.preview_slot(
            slot,
            AppearanceComponent(f"pack-{index}", f"item-{index}", "default"),
        )

    assert len(session._statuses) == len(APPEARANCE_SLOTS)
    assert set(session._statuses) == set(APPEARANCE_SLOTS)
    assert set(vars(session)) == {
        "_persisted",
        "_requested",
        "_preview",
        "_resolver",
        "_preview_callback",
        "_commit_callback",
        "_statuses",
        "_last_commit",
    }
    assert preview.calls == EXPECTED_PREVIEW_CALLS


def test_cloud_runtime_retains_no_frame_or_provider_response_payload() -> None:
    clock = _Clock()
    runtime = CloudVisionRuntime(
        _VisionProvider(),
        _AuthorizationSource(
            SavedVisionAuthorization(
                OpenAIVisionPreferences(
                    enabled=True,
                    cloud_vision_enabled=True,
                    daily_limit=20,
                    per_minute_limit=2,
                ),
                PREFERENCES_VERSION,
                1,
                True,
            )
        ),
        clock=clock,
    )
    private_frame = b"v4-private-frame-evidence"
    result = runtime.analyze(
        CloudVisionFrame(
            1,
            private_frame,
            1,
            1,
            "image/jpeg",
            "Describe visible context.",
        )
    )

    assert result.succeeded
    assert not _object_graph_contains(runtime, private_frame)
    assert not any(
        name in vars(runtime)
        for name in ("_frames", "_results", "_responses", "_raw_images")
    )


def _behavior_input(previous_action: str) -> BehaviorInput:
    return BehaviorInput(
        SpeechLifecycle.IDLE,
        SemanticEmotion.NEUTRAL,
        0.4,
        1,
        True,
        True,
        0.0,
        "front-crossed",
        previous_action,
    )


class _Clock:
    def __init__(self) -> None:
        self.now = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now


class _AuthorizationSource:
    def __init__(self, value: SavedVisionAuthorization) -> None:
        self.value = value

    def load(self) -> SavedVisionAuthorization:
        return self.value


class _VisionProvider:
    def analyze(self, request: object) -> VisionProviderResult:
        return VisionProviderResult(
            request.operation_id,  # type: ignore[attr-defined]
            VisionResultStatus.SUCCESS,
            request.model,  # type: ignore[attr-defined]
            request.detail,  # type: ignore[attr-defined]
        )

    def cancel(self, _operation_id: int) -> None:
        return None


def _cloud_frame(operation_id: int) -> CloudVisionFrame:
    return CloudVisionFrame(
        operation_id,
        b"x",
        1,
        1,
        "image/jpeg",
        "Describe visible context.",
    )


class _Resolver:
    def resolve(
        self,
        _slot: str,
        requested: AppearanceComponent,
    ) -> AppearanceComponent:
        return requested


class _Preview:
    def __init__(self) -> None:
        self.calls = 0

    def preview(self, _selection: AppearanceSelection) -> None:
        self.calls += 1


class _Committer:
    def commit(self, _payload: object) -> None:
        return None


def _object_graph_contains(owner: object, target: object) -> bool:
    return any(value is target for value in vars(owner).values())


def run() -> None:
    test_behavior_director_recent_history_has_a_hard_three_item_bound()
    test_cloud_vision_quota_history_never_exceeds_saved_limits()
    test_appearance_session_state_is_fixed_to_declared_slots()
    test_cloud_runtime_retains_no_frame_or_provider_response_payload()
    print("V4_PERFORMANCE_STATE_BOUNDS_OK")


if __name__ == "__main__":
    run()
