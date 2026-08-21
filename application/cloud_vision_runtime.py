from __future__ import annotations

lazy import threading
lazy import time
lazy from collections import deque
lazy from collections.abc import Callable
lazy from dataclasses import dataclass, field
lazy from enum import StrEnum
lazy from typing import Protocol

lazy from domain.openai_vision_preferences import (
    PREFERENCES_VERSION,
    OpenAIVisionPreferences,
    VisionDetail,
    VisionTriggerPolicy,
)
lazy from domain.vision_provider_contracts import (
    VisionFrameRequest,
    VisionProviderResult,
    VisionResultStatus,
    VisualUnderstanding,
)

MINUTE_WINDOW_SECONDS = 60.0


class CloudVisionStatus(StrEnum):
    SUCCESS = "success"
    DISABLED = "disabled"
    UNSAVED = "unsaved"
    SETTINGS_UNSUPPORTED = "settings_unsupported"
    DAILY_QUOTA_EXHAUSTED = "daily_quota_exhausted"
    MINUTE_QUOTA_EXHAUSTED = "minute_quota_exhausted"
    PREVIOUS_REQUEST_CANCELLED = "previous_request_cancelled"
    STALE = "stale"
    CANCELLED = "cancelled"
    KEY_MISSING = "key_missing"
    TRANSPORT_UNAVAILABLE = "transport_unavailable"
    SDK_UNAVAILABLE = "transport_unavailable"  # compatibility alias
    NETWORK_UNAVAILABLE = "network_unavailable"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    TIMED_OUT = "timed_out"
    INVALID_INPUT = "invalid_input"
    INVALID_RESPONSE = "invalid_response"
    SERVICE_UNAVAILABLE = "service_unavailable"

    @classmethod
    def _missing_(cls, value: object) -> CloudVisionStatus | None:
        if value == "sdk_unavailable":
            return cls.TRANSPORT_UNAVAILABLE
        return None


class WebLookupDisposition(StrEnum):
    NOT_REQUESTED = "not_requested"
    SUGGEST_ASK_USER = "suggest_ask_user"


class CloudVisionTrigger(StrEnum):
    MANUAL = "manual"
    EVENT = "event"


@dataclass(frozen=True, slots=True)
class SavedVisionAuthorization:
    preferences: OpenAIVisionPreferences
    settings_version: int
    generation: int
    saved: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.preferences, OpenAIVisionPreferences):
            raise TypeError("Saved cloud vision preferences are invalid.")
        if type(self.settings_version) is not int or self.settings_version < 1:
            raise ValueError("Saved cloud vision settings version is invalid.")
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("Saved cloud vision generation is invalid.")
        if type(self.saved) is not bool:
            raise TypeError("Saved cloud vision state must be boolean.")

    @property
    def enabled(self) -> bool:
        return bool(
            self.saved
            and self.settings_version == PREFERENCES_VERSION
            and self.preferences.enabled
            and self.preferences.cloud_vision_enabled
        )


@dataclass(frozen=True, slots=True)
class CloudVisionFrame:
    operation_id: int
    image_bytes: bytes = field(repr=False)
    width: int
    height: int
    media_type: str
    prompt: str
    trigger: CloudVisionTrigger = CloudVisionTrigger.MANUAL


@dataclass(frozen=True, slots=True)
class CloudVisionResult:
    operation_id: int
    status: CloudVisionStatus
    authorization_generation: int
    understanding: VisualUnderstanding | None = None
    web_lookup: WebLookupDisposition = WebLookupDisposition.NOT_REQUESTED

    @property
    def succeeded(self) -> bool:
        return self.status is CloudVisionStatus.SUCCESS


class SavedAuthorizationSource(Protocol):
    def load(self) -> SavedVisionAuthorization: ...


class VisionProviderPort(Protocol):
    def analyze(self, request: VisionFrameRequest) -> VisionProviderResult: ...

    def cancel(self, operation_id: int) -> None: ...


Clock = Callable[[], float]


_PROVIDER_STATUS = {
    "success": CloudVisionStatus.SUCCESS,
    "key_missing": CloudVisionStatus.KEY_MISSING,
    "authentication_failed": CloudVisionStatus.KEY_MISSING,
    "transport_unavailable": CloudVisionStatus.TRANSPORT_UNAVAILABLE,
    "network_unavailable": CloudVisionStatus.NETWORK_UNAVAILABLE,
    "rate_limited": CloudVisionStatus.PROVIDER_RATE_LIMITED,
    "timed_out": CloudVisionStatus.TIMED_OUT,
    "cancelled": CloudVisionStatus.CANCELLED,
    "invalid_input": CloudVisionStatus.INVALID_INPUT,
    "invalid_response": CloudVisionStatus.INVALID_RESPONSE,
    "service_unavailable": CloudVisionStatus.SERVICE_UNAVAILABLE,
}
_NON_NETWORK_STATUS_VALUES = frozenset({
    "key_missing",
    "authentication_failed",
    "transport_unavailable",
    "invalid_input",
})


class CloudVisionRuntime:
    """Coordinate persisted cloud authorization without retaining private frames."""

    def __init__(
        self,
        provider: VisionProviderPort,
        authorization_source: SavedAuthorizationSource,
        *,
        clock: Clock = time.time,
    ) -> None:
        self._provider = provider
        self._authorization_source = authorization_source
        self._clock = clock
        self._lock = threading.Lock()
        self._authorization = self._safe_load()
        self._active_operation: int | None = None
        self._minute_requests: deque[float] = deque()
        self._daily_requests: deque[float] = deque()

    @property
    def authorization(self) -> SavedVisionAuthorization:
        with self._lock:
            return self._authorization

    def refresh_saved_authorization(self) -> SavedVisionAuthorization:
        """Apply the latest committed settings and cancel work from older generations."""

        loaded = self._safe_load()
        active: int | None = None
        with self._lock:
            previous = self._authorization
            self._authorization = loaded
            changed = (
                loaded.generation != previous.generation
                or loaded.settings_version != previous.settings_version
                or loaded.preferences != previous.preferences
                or loaded.saved != previous.saved
            )
            if changed or not loaded.enabled:
                active = self._active_operation
        if active is not None:
            self._provider.cancel(active)
        return loaded

    def analyze(self, frame: CloudVisionFrame) -> CloudVisionResult:
        authorization = self.refresh_saved_authorization()
        blocked = self._authorization_status(authorization)
        if blocked is not None:
            return self._result(frame.operation_id, blocked, authorization.generation)
        if not self._trigger_permitted(frame.trigger, authorization.preferences):
            return self._result(
                frame.operation_id,
                CloudVisionStatus.DISABLED,
                authorization.generation,
            )
        accepted = self._begin(frame.operation_id, authorization)
        if accepted is not None:
            return self._result(frame.operation_id, accepted, authorization.generation)
        provider_result: VisionProviderResult
        try:
            preferences = authorization.preferences
            provider_result = self._provider.analyze(
                VisionFrameRequest(
                    frame.operation_id,
                    frame.image_bytes,
                    frame.width,
                    frame.height,
                    frame.media_type,
                    frame.prompt,
                    VisionDetail(preferences.detail.value),
                    preferences.model_id,
                )
            )
        except (ConnectionError, OSError, RuntimeError, TypeError, ValueError):
            provider_result = VisionProviderResult(
                frame.operation_id,
                VisionResultStatus("service_unavailable"),
                authorization.preferences.model_id,
                VisionDetail(authorization.preferences.detail.value),
            )
        return self._complete(frame.operation_id, authorization, provider_result)

    def suggest_web_lookup(self) -> CloudVisionResult:
        """Never search automatically; request explicit user direction instead."""

        authorization = self.authorization
        return CloudVisionResult(
            0,
            CloudVisionStatus.DISABLED,
            authorization.generation,
            web_lookup=WebLookupDisposition.SUGGEST_ASK_USER,
        )

    def close(self) -> None:
        active: int | None
        with self._lock:
            active = self._active_operation
            self._active_operation = None
        if active is not None:
            self._provider.cancel(active)

    def _begin(
        self,
        operation_id: int,
        authorization: SavedVisionAuthorization,
    ) -> CloudVisionStatus | None:
        previous: int | None = None
        now = self._clock()
        with self._lock:
            if operation_id < 0:
                return CloudVisionStatus.INVALID_INPUT
            if self._active_operation is not None:
                previous = self._active_operation
            else:
                self._prune_quotas(now)
                preferences = authorization.preferences
                if len(self._daily_requests) >= preferences.daily_limit:
                    return CloudVisionStatus.DAILY_QUOTA_EXHAUSTED
                if len(self._minute_requests) >= preferences.per_minute_limit:
                    return CloudVisionStatus.MINUTE_QUOTA_EXHAUSTED
                self._active_operation = operation_id
                self._daily_requests.append(now)
                self._minute_requests.append(now)
        if previous is not None:
            self._provider.cancel(previous)
            return CloudVisionStatus.PREVIOUS_REQUEST_CANCELLED
        return None

    def _complete(
        self,
        operation_id: int,
        authorization: SavedVisionAuthorization,
        provider_result: VisionProviderResult,
    ) -> CloudVisionResult:
        current = self._safe_load()
        with self._lock:
            active = self._active_operation
            if active == operation_id:
                self._active_operation = None
            stale = bool(
                active != operation_id
                or current.generation != authorization.generation
                or current.settings_version != authorization.settings_version
                or not current.enabled
            )
            self._authorization = current
            provider_status = _provider_status_value(provider_result.status)
            if provider_status in _NON_NETWORK_STATUS_VALUES:
                self._rollback_latest_quota()
        if stale:
            return self._result(
                operation_id,
                CloudVisionStatus.STALE,
                current.generation,
            )
        status = _PROVIDER_STATUS.get(
            provider_status,
            CloudVisionStatus.SERVICE_UNAVAILABLE,
        )
        return CloudVisionResult(
            operation_id,
            status,
            authorization.generation,
            provider_result.understanding if status is CloudVisionStatus.SUCCESS else None,
        )

    def _safe_load(self) -> SavedVisionAuthorization:
        try:
            loaded = self._authorization_source.load()
        except (LookupError, OSError, RuntimeError, TypeError, ValueError):
            return _disabled_authorization()
        return loaded if isinstance(loaded, SavedVisionAuthorization) else _disabled_authorization()

    @staticmethod
    def _trigger_permitted(
        trigger: CloudVisionTrigger,
        preferences: OpenAIVisionPreferences,
    ) -> bool:
        if not isinstance(trigger, CloudVisionTrigger):
            return False
        return bool(
            trigger is CloudVisionTrigger.MANUAL
            or preferences.trigger_policy is VisionTriggerPolicy.EVENT_WITH_NOTICE
        )

    @staticmethod
    def _authorization_status(
        authorization: SavedVisionAuthorization,
    ) -> CloudVisionStatus | None:
        if not authorization.saved:
            return CloudVisionStatus.UNSAVED
        if authorization.settings_version != PREFERENCES_VERSION:
            return CloudVisionStatus.SETTINGS_UNSUPPORTED
        if not authorization.enabled:
            return CloudVisionStatus.DISABLED
        return None

    def _prune_quotas(self, now: float) -> None:
        while self._minute_requests and now - self._minute_requests[0] >= MINUTE_WINDOW_SECONDS:
            self._minute_requests.popleft()
        day_start = now - (now % 86_400.0)
        while self._daily_requests and self._daily_requests[0] < day_start:
            self._daily_requests.popleft()

    def _rollback_latest_quota(self) -> None:
        if self._daily_requests:
            self._daily_requests.pop()
        if self._minute_requests:
            self._minute_requests.pop()

    @staticmethod
    def _result(
        operation_id: int,
        status: CloudVisionStatus,
        generation: int,
    ) -> CloudVisionResult:
        return CloudVisionResult(operation_id, status, generation)


def _disabled_authorization() -> SavedVisionAuthorization:
    return SavedVisionAuthorization(
        OpenAIVisionPreferences(),
        PREFERENCES_VERSION,
        0,
    )


def _provider_status_value(status: object) -> str:
    value = getattr(status, "value", None)
    return value if isinstance(value, str) else ""
