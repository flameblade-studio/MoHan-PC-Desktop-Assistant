from __future__ import annotations

lazy import sys
lazy import threading
lazy from dataclasses import dataclass
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.cloud_vision_runtime import (
    CloudVisionFrame,
    CloudVisionResult,
    CloudVisionRuntime,
    CloudVisionStatus,
    CloudVisionTrigger,
    SavedVisionAuthorization,
    WebLookupDisposition,
)
lazy from integrations.openai_vision_provider import (
    VisionProviderResult,
    VisionResultStatus,
)
lazy from domain.openai_vision_preferences import (
    PREFERENCES_VERSION,
    OpenAIVisionPreferences,
    VisionTriggerPolicy,
)

TRIO_LENGTH = 3
EXPECTED_GENERATION = 7


def assert_legacy_sdk_status_migrates_to_transport() -> None:
    assert CloudVisionStatus("sdk_unavailable") is (
        CloudVisionStatus.TRANSPORT_UNAVAILABLE
    )
    assert CloudVisionStatus.SDK_UNAVAILABLE is (
        CloudVisionStatus.TRANSPORT_UNAVAILABLE
    )
    assert CloudVisionStatus.TRANSPORT_UNAVAILABLE.value == (
        "transport_unavailable"
    )


class Clock:
    def __init__(self) -> None:
        self.value = 1_800_000_000.0

    def __call__(self) -> float:
        return self.value


class AuthorizationSource:
    def __init__(self, authorization: SavedVisionAuthorization) -> None:
        self.authorization = authorization

    def load(self) -> SavedVisionAuthorization:
        return self.authorization


class Provider:
    def __init__(self) -> None:
        self.requests: list[object] = []
        self.cancelled: list[int] = []
        self.status = VisionResultStatus.SUCCESS
        self.started = threading.Event()
        self.release = threading.Event()
        self.block = False

    def analyze(self, request: object) -> VisionProviderResult:
        self.requests.append(request)
        self.started.set()
        if self.block:
            self.release.wait(2.0)
        return VisionProviderResult(
            request.operation_id,
            self.status,
            request.model or "",
            request.detail,
        )

    def cancel(self, operation_id: int) -> None:
        self.cancelled.append(operation_id)


@dataclass(frozen=True, slots=True)
class AuthorizationOptions:
    enabled: bool = True
    saved: bool = True
    daily_limit: int = 20
    per_minute_limit: int = 2
    trigger_policy: VisionTriggerPolicy = VisionTriggerPolicy.MANUAL


DEFAULT_AUTHORIZATION_OPTIONS = AuthorizationOptions()


def authorization(
    generation: int = 1,
    *,
    options: AuthorizationOptions = DEFAULT_AUTHORIZATION_OPTIONS,
) -> SavedVisionAuthorization:
    return SavedVisionAuthorization(
        OpenAIVisionPreferences(
            enabled=options.enabled,
            cloud_vision_enabled=options.enabled,
            daily_limit=options.daily_limit,
            per_minute_limit=options.per_minute_limit,
            trigger_policy=options.trigger_policy,
        ),
        PREFERENCES_VERSION,
        generation,
        options.saved,
    )


def frame(
    operation_id: int,
    trigger: CloudVisionTrigger = CloudVisionTrigger.MANUAL,
) -> CloudVisionFrame:
    return CloudVisionFrame(
        operation_id,
        b"private-frame",
        2,
        2,
        "image/jpeg",
        "Describe visible context.",
        trigger,
    )


def assert_saved_enable_allows_repeated_requests_without_consent() -> None:
    clock = Clock()
    source = AuthorizationSource(
        authorization(options=AuthorizationOptions(per_minute_limit=4))
    )
    provider = Provider()
    runtime = CloudVisionRuntime(provider, source, clock=clock)
    for operation_id in range(1, 4):
        result = runtime.analyze(frame(operation_id))
        assert result.status is CloudVisionStatus.SUCCESS
        clock.value += 2.0
    assert len(provider.requests) == TRIO_LENGTH


def assert_unsaved_draft_never_enables_cloud() -> None:
    source = AuthorizationSource(
        authorization(options=AuthorizationOptions(saved=False))
    )
    provider = Provider()
    runtime = CloudVisionRuntime(provider, source)
    assert runtime.analyze(frame(1)).status is CloudVisionStatus.UNSAVED
    assert provider.requests == []


def assert_disable_immediately_cancels_inflight_and_blocks_new() -> None:
    source = AuthorizationSource(authorization())
    provider = Provider()
    provider.block = True
    runtime = CloudVisionRuntime(provider, source)
    result: list[object] = []
    worker = threading.Thread(target=lambda: result.append(runtime.analyze(frame(1))))
    worker.start()
    assert provider.started.wait(1.0)
    source.authorization = authorization(
        2,
        options=AuthorizationOptions(enabled=False),
    )
    runtime.refresh_saved_authorization()
    assert provider.cancelled == [1]
    blocked = runtime.analyze(frame(2))
    assert blocked.status is CloudVisionStatus.DISABLED
    provider.release.set()
    worker.join(2.0)
    assert result[0].status is CloudVisionStatus.STALE


def assert_new_request_cancels_old_without_starting_second_inflight() -> None:
    source = AuthorizationSource(authorization())
    provider = Provider()
    provider.block = True
    runtime = CloudVisionRuntime(provider, source)
    worker = threading.Thread(target=lambda: runtime.analyze(frame(1)))
    worker.start()
    assert provider.started.wait(1.0)
    replacement = runtime.analyze(frame(2))
    assert replacement.status is CloudVisionStatus.PREVIOUS_REQUEST_CANCELLED
    assert provider.cancelled == [1]
    assert len(provider.requests) == 1
    provider.release.set()
    worker.join(2.0)


def assert_repeated_cancel_and_stale_completion_never_revive_active_work() -> None:
    source = AuthorizationSource(authorization())
    provider = Provider()
    provider.block = True
    runtime = CloudVisionRuntime(provider, source)
    results: list[CloudVisionResult] = []
    worker = threading.Thread(target=lambda: results.append(runtime.analyze(frame(1))))
    worker.start()
    assert provider.started.wait(1.0)
    for generation in range(2, 2_002):
        source.authorization = authorization(generation)
        runtime.refresh_saved_authorization()
    runtime.close()
    assert runtime._active_operation is None
    provider.release.set()
    worker.join(2.0)
    assert results[0].status is CloudVisionStatus.STALE
    assert runtime._active_operation is None


def assert_minute_and_daily_quotas_are_enforced() -> None:
    clock = Clock()
    source = AuthorizationSource(
        authorization(options=AuthorizationOptions(daily_limit=2, per_minute_limit=1))
    )
    provider = Provider()
    runtime = CloudVisionRuntime(provider, source, clock=clock)
    assert runtime.analyze(frame(1)).succeeded
    assert runtime.analyze(frame(2)).status is CloudVisionStatus.MINUTE_QUOTA_EXHAUSTED
    clock.value += 61.0
    assert runtime.analyze(frame(3)).succeeded
    clock.value += 61.0
    assert runtime.analyze(frame(4)).status is CloudVisionStatus.DAILY_QUOTA_EXHAUSTED


def assert_restart_loads_persisted_authorization() -> None:
    source = AuthorizationSource(authorization(7))
    first = CloudVisionRuntime(Provider(), source)
    assert first.authorization.generation == EXPECTED_GENERATION
    restarted_provider = Provider()
    restarted = CloudVisionRuntime(restarted_provider, source)
    result = restarted.analyze(frame(1))
    assert result.succeeded and result.authorization_generation == EXPECTED_GENERATION


def assert_event_trigger_requires_saved_event_policy() -> None:
    provider = Provider()
    source = AuthorizationSource(authorization())
    runtime = CloudVisionRuntime(provider, source)
    assert runtime.analyze(frame(1, CloudVisionTrigger.EVENT)).status is CloudVisionStatus.DISABLED
    assert provider.requests == []
    source.authorization = authorization(
        2,
        options=AuthorizationOptions(
            trigger_policy=VisionTriggerPolicy.EVENT_WITH_NOTICE
        ),
    )
    assert runtime.analyze(frame(2, CloudVisionTrigger.EVENT)).succeeded


def assert_safe_degradation_and_privacy() -> None:
    private_input = frame(99)
    assert "private-frame" not in repr(private_input)
    for status, expected in (
        (VisionResultStatus.KEY_MISSING, CloudVisionStatus.KEY_MISSING),
        (
            VisionResultStatus.TRANSPORT_UNAVAILABLE,
            CloudVisionStatus.TRANSPORT_UNAVAILABLE,
        ),
        (VisionResultStatus.NETWORK_UNAVAILABLE, CloudVisionStatus.NETWORK_UNAVAILABLE),
        (VisionResultStatus.RATE_LIMITED, CloudVisionStatus.PROVIDER_RATE_LIMITED),
    ):
        provider = Provider()
        provider.status = status
        result = CloudVisionRuntime(provider, AuthorizationSource(authorization())).analyze(frame(1))
        assert result.status is expected
        representation = repr(result)
        assert "private-frame" not in representation
        assert "base64" not in representation.lower()
        assert "api_key" not in representation.lower()
    runtime = CloudVisionRuntime(Provider(), AuthorizationSource(authorization()))
    suggestion = runtime.suggest_web_lookup()
    assert suggestion.web_lookup is WebLookupDisposition.SUGGEST_ASK_USER


def run() -> None:
    assert_legacy_sdk_status_migrates_to_transport()
    assert_saved_enable_allows_repeated_requests_without_consent()
    assert_unsaved_draft_never_enables_cloud()
    assert_disable_immediately_cancels_inflight_and_blocks_new()
    assert_new_request_cancels_old_without_starting_second_inflight()
    assert_repeated_cancel_and_stale_completion_never_revive_active_work()
    assert_minute_and_daily_quotas_are_enforced()
    assert_restart_loads_persisted_authorization()
    assert_event_trigger_requires_saved_event_policy()
    assert_safe_degradation_and_privacy()
    print("CLOUD_VISION_RUNTIME_OK")


if __name__ == "__main__":
    run()
