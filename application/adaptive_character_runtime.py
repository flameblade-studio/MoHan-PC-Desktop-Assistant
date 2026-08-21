from __future__ import annotations

lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from typing import Protocol

lazy from application.body_pose_renderer import BodyPoseFrame
lazy from application.character_framing_app_bridge import (
    AppFramingState,
    AtomicFramingCommand,
    FramingBridgeDisposition,
    FramingBridgeInput,
    FramingBridgeResult,
)
lazy from application.framing_orchestrator import ApprovedWellbeingPerformance
lazy from application.full_body_performance_bridge import (
    FramingCommand,
    FullBodyBridgeDisposition,
    FullBodyBridgeRequest,
    FullBodyBridgeResult,
    LoadedV4Assets,
)
lazy from application.full_body_render_adapter import NormalizedCrop
lazy from application.performance_runtime import AtomicPerformanceFrame
lazy from domain.face_rig import FaceMotionFrame
lazy from domain.framing_preferences import FramingPreferences


class AdaptiveCharacterDisposition(StrEnum):
    PUBLISHED = "published"
    BYPASSED = "bypassed"
    STALE = "stale"
    CANCELLED = "cancelled"
    DEDUPED = "deduped"
    LKG = "last-known-good"


@dataclass(frozen=True, slots=True)
class AdaptiveCharacterRequest:
    operation_generation: int
    atomic_frame: AtomicPerformanceFrame
    framing_state: AppFramingState
    framing_preferences: FramingPreferences
    assets: LoadedV4Assets | None
    approved_wellbeing_cue: ApprovedWellbeingPerformance | None = None
    v4_enabled: bool = True
    face_motion: FaceMotionFrame | None = None

    def __post_init__(self) -> None:
        if self.operation_generation < 0:
            raise ValueError("Adaptive operation generation must not be negative.")


@dataclass(frozen=True, slots=True)
class AtomicCharacterPublishDecision:
    generation: int
    disposition: AdaptiveCharacterDisposition
    should_publish: bool
    frame: BodyPoseFrame
    framing: AtomicFramingCommand | None
    used_legacy: bool


class CharacterFramingBridgePort(Protocol):
    @property
    def last_known_good(self) -> AtomicFramingCommand | None: ...

    def dispatch(self, value: FramingBridgeInput) -> FramingBridgeResult: ...


class FullBodyPerformanceBridgePort(Protocol):
    @property
    def last_known_good(self) -> BodyPoseFrame | None: ...

    def begin_operation(self) -> int: ...

    def cancel(self, operation_generation: int) -> None: ...

    def dispatch(self, request: FullBodyBridgeRequest) -> FullBodyBridgeResult: ...


class AdaptiveCharacterRuntime:
    """Atomically coordinate approved performance, framing, and loaded v4 assets."""

    def __init__(
        self,
        framing: CharacterFramingBridgePort,
        full_body: FullBodyPerformanceBridgePort,
    ) -> None:
        self._framing = framing
        self._full_body = full_body
        self._generation = 0
        self._cancelled_generation: int | None = None
        self._last_input_signature: tuple[object, ...] | None = None
        self._last_publish_signature: tuple[object, ...] | None = None
        self._last_good: AtomicCharacterPublishDecision | None = None

    @property
    def last_known_good(self) -> AtomicCharacterPublishDecision | None:
        return self._last_good

    def begin_operation(self) -> int:
        self._generation = self._full_body.begin_operation()
        self._cancelled_generation = None
        return self._generation

    def cancel(self, operation_generation: int) -> None:
        if operation_generation != self._generation:
            return
        self._cancelled_generation = operation_generation
        self._full_body.cancel(operation_generation)

    def dispatch(
        self,
        request: AdaptiveCharacterRequest,
    ) -> AtomicCharacterPublishDecision:
        signature, framing, terminal = self._prepare(request)
        if terminal is not None:
            return terminal
        if framing is None:
            raise AssertionError("Prepared adaptive framing is missing.")
        try:
            body_result = self._full_body.dispatch(
                FullBodyBridgeRequest(
                    request.operation_generation,
                    request.atomic_frame,
                    _body_framing(framing),
                    request.assets,
                    True,
                    request.face_motion,
                )
            )
        except (LookupError, RuntimeError, TypeError, ValueError):
            return self._fallback(request)
        disposition = _body_disposition(body_result.disposition)
        decision = AtomicCharacterPublishDecision(
            request.operation_generation,
            disposition,
            disposition is AdaptiveCharacterDisposition.PUBLISHED,
            body_result.frame,
            framing,
            body_result.used_legacy,
        )
        if disposition is AdaptiveCharacterDisposition.PUBLISHED:
            return self._accept_publish(signature, decision)
        return decision

    def _prepare(
        self,
        request: AdaptiveCharacterRequest,
    ) -> tuple[
        tuple[object, ...],
        AtomicFramingCommand | None,
        AtomicCharacterPublishDecision | None,
    ]:
        signature = _input_signature(request)
        state = self._operation_state(request.operation_generation)
        if state is not None:
            return signature, None, self._nonpublishing(request, state)
        if (
            not request.v4_enabled
            or request.assets is None
            or not request.assets.enabled
            or not request.framing_state.enabled
        ):
            return signature, None, self._legacy_bypass(request)

        if signature == self._last_input_signature:
            return (
                signature,
                None,
                self._nonpublishing(
                    request,
                    AdaptiveCharacterDisposition.DEDUPED,
                ),
            )
        framing_result = self._framing.dispatch(
            FramingBridgeInput(
                request.framing_state,
                request.framing_preferences,
                request.approved_wellbeing_cue,
            )
        )
        framing_state = _framing_state(framing_result.disposition)
        if framing_state is not None:
            return (
                signature,
                None,
                self._nonpublishing(request, framing_state),
            )
        framing = framing_result.command or self._framing.last_known_good
        if framing is None:
            return signature, None, self._fallback(request)
        return signature, framing, None

    def _accept_publish(
        self,
        signature: tuple[object, ...],
        decision: AtomicCharacterPublishDecision,
    ) -> AtomicCharacterPublishDecision:
        publish_signature = _publish_signature(decision)
        self._last_input_signature = signature
        if publish_signature == self._last_publish_signature:
            return AtomicCharacterPublishDecision(
                decision.generation,
                AdaptiveCharacterDisposition.DEDUPED,
                False,
                decision.frame,
                decision.framing,
                decision.used_legacy,
            )
        self._last_publish_signature = publish_signature
        self._last_good = decision
        return decision

    def _operation_state(
        self,
        generation: int,
    ) -> AdaptiveCharacterDisposition | None:
        if generation == self._cancelled_generation:
            return AdaptiveCharacterDisposition.CANCELLED
        if generation != self._generation:
            return AdaptiveCharacterDisposition.STALE
        return None

    def _legacy_bypass(
        self,
        request: AdaptiveCharacterRequest,
    ) -> AtomicCharacterPublishDecision:
        return AtomicCharacterPublishDecision(
            request.operation_generation,
            AdaptiveCharacterDisposition.BYPASSED,
            False,
            request.atomic_frame.body,
            None,
            True,
        )

    def _fallback(
        self,
        request: AdaptiveCharacterRequest,
    ) -> AtomicCharacterPublishDecision:
        if self._last_good is not None:
            return AtomicCharacterPublishDecision(
                request.operation_generation,
                AdaptiveCharacterDisposition.LKG,
                False,
                self._last_good.frame,
                self._last_good.framing,
                self._last_good.used_legacy,
            )
        return self._legacy_bypass(request)

    def _nonpublishing(
        self,
        request: AdaptiveCharacterRequest,
        disposition: AdaptiveCharacterDisposition,
    ) -> AtomicCharacterPublishDecision:
        if self._last_good is None:
            return AtomicCharacterPublishDecision(
                request.operation_generation,
                disposition,
                False,
                request.atomic_frame.body,
                None,
                True,
            )
        return AtomicCharacterPublishDecision(
            request.operation_generation,
            disposition,
            False,
            self._last_good.frame,
            self._last_good.framing,
            self._last_good.used_legacy,
        )


def _framing_state(
    disposition: FramingBridgeDisposition,
) -> AdaptiveCharacterDisposition | None:
    return {
        FramingBridgeDisposition.BYPASSED: AdaptiveCharacterDisposition.BYPASSED,
        FramingBridgeDisposition.STALE: AdaptiveCharacterDisposition.STALE,
        FramingBridgeDisposition.FALLBACK: AdaptiveCharacterDisposition.LKG,
    }.get(disposition)


def _body_disposition(
    disposition: FullBodyBridgeDisposition,
) -> AdaptiveCharacterDisposition:
    return {
        FullBodyBridgeDisposition.PUBLISHED: AdaptiveCharacterDisposition.PUBLISHED,
        FullBodyBridgeDisposition.DEDUPED: AdaptiveCharacterDisposition.DEDUPED,
        FullBodyBridgeDisposition.STALE: AdaptiveCharacterDisposition.STALE,
        FullBodyBridgeDisposition.CANCELLED: AdaptiveCharacterDisposition.CANCELLED,
        FullBodyBridgeDisposition.LKG: AdaptiveCharacterDisposition.LKG,
        FullBodyBridgeDisposition.BYPASS: AdaptiveCharacterDisposition.BYPASSED,
    }[disposition]


def _body_framing(command: AtomicFramingCommand) -> FramingCommand:
    crop = command.crop
    return FramingCommand(
        command.generation,
        NormalizedCrop(crop.left, crop.top, crop.right, crop.bottom),
    )


def _input_signature(request: AdaptiveCharacterRequest) -> tuple[object, ...]:
    performance = request.atomic_frame.performance
    return (
        request.operation_generation,
        performance.speech_generation,
        performance.behavior_generation,
        performance.pose,
        performance.view,
        performance.face,
        performance.viseme,
        performance.mouth_closed,
        request.framing_state,
        request.framing_preferences,
        request.approved_wellbeing_cue,
        request.assets.generation if request.assets is not None else None,
    )


def _publish_signature(
    decision: AtomicCharacterPublishDecision,
) -> tuple[object, ...]:
    frame = decision.frame
    return (
        frame.width,
        frame.height,
        frame.rgba,
        frame.view_ids,
        frame.layer_order,
        frame.articulation_active,
        frame.crop,
        frame.static_revision,
        decision.framing,
    )
