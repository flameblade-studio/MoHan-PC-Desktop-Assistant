from __future__ import annotations

lazy from dataclasses import dataclass, replace
lazy from enum import StrEnum
lazy from typing import Protocol

lazy from application.body_pose_renderer import BodyPoseFrame
lazy from application.full_body_render_adapter import (
    FullBodyRenderAdapter,
    FullBodyRenderLayer,
    FullBodyRenderSpec,
    NormalizedCrop,
)
lazy from application.performance_runtime import AtomicPerformanceFrame
lazy from domain.face_rig import FaceMotionFrame

_RECOVERABLE_BOUNDARY_ERRORS = (
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


class FullBodyBridgeDisposition(StrEnum):
    PUBLISHED = "published"
    DEDUPED = "deduped"
    STALE = "stale"
    CANCELLED = "cancelled"
    LKG = "last-known-good"
    BYPASS = "bypass"


@dataclass(frozen=True, slots=True)
class FramingCommand:
    generation: int
    crop: NormalizedCrop

    def __post_init__(self) -> None:
        if self.generation < 0:
            raise ValueError("Framing generation must not be negative.")


class LoadedV4Assets(Protocol):
    @property
    def generation(self) -> int: ...

    @property
    def enabled(self) -> bool: ...

    def resolve_static(
        self,
        pose_id: str,
        view_id: str,
        motion: FaceMotionFrame | None = None,
    ) -> FullBodyRenderSpec | None: ...

    def resolve_speech(
        self,
        face: str | None,
        viseme: str,
        mouth_closed: bool,
        motion: FaceMotionFrame | None,
    ) -> tuple[FullBodyRenderLayer, ...] | None: ...


@dataclass(frozen=True, slots=True)
class FullBodyBridgeRequest:
    operation_generation: int
    atomic_frame: AtomicPerformanceFrame
    framing: FramingCommand
    assets: LoadedV4Assets | None
    v4_enabled: bool = True
    face_motion: FaceMotionFrame | None = None

    def __post_init__(self) -> None:
        if self.operation_generation < 0:
            raise ValueError("Operation generation must not be negative.")


@dataclass(frozen=True, slots=True)
class FullBodyBridgeResult:
    disposition: FullBodyBridgeDisposition
    frame: BodyPoseFrame
    used_legacy: bool


@dataclass(frozen=True, slots=True)
class _PreparedLayers:
    specification: FullBodyRenderSpec
    static_signature: tuple[object, ...]
    dynamic_layers: tuple[FullBodyRenderLayer, ...]
    dynamic_signature: tuple[object, ...]


class FullBodyPerformanceBridge:
    """Join atomic performance, framing, and loaded v4 assets without UI state."""

    def __init__(self, adapter: FullBodyRenderAdapter) -> None:
        self._adapter = adapter
        self._operation_generation = 0
        self._cancelled_generation: int | None = None
        self._speech_generation = -1
        self._behavior_generation = -1
        self._framing_generation = -1
        self._assets_generation = -1
        self._adapter_generation = 0
        self._static_signature: tuple[object, ...] | None = None
        self._dynamic_signature: tuple[object, ...] | None = None
        self._last_good: BodyPoseFrame | None = None

    @property
    def last_known_good(self) -> BodyPoseFrame | None:
        return self._last_good

    def begin_operation(self) -> int:
        self._operation_generation += 1
        self._cancelled_generation = None
        return self._operation_generation

    def cancel(self, operation_generation: int) -> None:
        if operation_generation == self._operation_generation:
            self._cancelled_generation = operation_generation

    def dispatch(self, request: FullBodyBridgeRequest) -> FullBodyBridgeResult:
        legacy = request.atomic_frame.body
        terminal = self._preflight(request)
        if terminal is not None:
            return terminal
        prepared = self._prepare_assets(request)
        if isinstance(prepared, FullBodyBridgeResult):
            return prepared
        terminal = self._dedupe_or_cancel(
            request.operation_generation,
            prepared.static_signature,
            prepared.dynamic_signature,
            legacy,
        )
        if terminal is not None:
            return terminal
        rendered = self._render_layers(
            request.operation_generation,
            prepared,
            legacy,
        )
        if isinstance(rendered, FullBodyBridgeResult):
            return rendered
        performance = request.atomic_frame.performance
        self._speech_generation = performance.speech_generation
        self._behavior_generation = performance.behavior_generation
        self._framing_generation = request.framing.generation
        assert request.assets is not None
        self._assets_generation = request.assets.generation
        self._dynamic_signature = prepared.dynamic_signature
        self._last_good = rendered
        return FullBodyBridgeResult(
            FullBodyBridgeDisposition.PUBLISHED,
            rendered,
            False,
        )

    def _preflight(
        self,
        request: FullBodyBridgeRequest,
    ) -> FullBodyBridgeResult | None:
        legacy = request.atomic_frame.body
        operation_state = self._operation_state(request.operation_generation)
        if operation_state is not None:
            return self._result(operation_state, legacy)
        assets = request.assets
        if not request.v4_enabled or assets is None or not assets.enabled:
            return FullBodyBridgeResult(FullBodyBridgeDisposition.BYPASS, legacy, True)
        performance = request.atomic_frame.performance
        if self._is_stale(
            performance.speech_generation,
            performance.behavior_generation,
            request.framing.generation,
            assets.generation,
        ):
            return self._result(FullBodyBridgeDisposition.STALE, legacy)
        return None

    def _prepare_assets(
        self,
        request: FullBodyBridgeRequest,
    ) -> _PreparedLayers | FullBodyBridgeResult:
        assets = request.assets
        assert assets is not None
        performance = request.atomic_frame.performance
        legacy = request.atomic_frame.body
        try:
            specification = assets.resolve_static(
                performance.pose,
                performance.view,
                request.face_motion,
            )
            dynamic_layers = assets.resolve_speech(
                performance.face,
                performance.viseme,
                performance.mouth_closed,
                request.face_motion,
            )
        except _RECOVERABLE_BOUNDARY_ERRORS:
            return self._asset_failure(legacy)
        if specification is None or dynamic_layers is None:
            return FullBodyBridgeResult(FullBodyBridgeDisposition.BYPASS, legacy, True)
        specification = replace(specification, crop=request.framing.crop)
        return _PreparedLayers(
            specification,
            self._static_frame_signature(
                performance.behavior_generation,
                request.framing,
                assets.generation,
                specification,
            ),
            dynamic_layers,
            self._dynamic_frame_signature(
                performance.speech_generation,
                performance.face,
                performance.viseme,
                performance.mouth_closed,
                request.face_motion,
                dynamic_layers,
            ),
        )

    def _dedupe_or_cancel(
        self,
        operation_generation: int,
        static_signature: tuple[object, ...],
        dynamic_signature: tuple[object, ...],
        legacy: BodyPoseFrame,
    ) -> FullBodyBridgeResult | None:
        state = self._operation_state(operation_generation)
        if state is not None:
            return self._result(state, legacy)
        if (
            static_signature == self._static_signature
            and dynamic_signature == self._dynamic_signature
        ):
            return self._result(FullBodyBridgeDisposition.DEDUPED, legacy)
        return None

    def _render_layers(
        self,
        operation_generation: int,
        prepared: _PreparedLayers,
        legacy: BodyPoseFrame,
    ) -> BodyPoseFrame | FullBodyBridgeResult:
        previous = self._adapter.current_frame
        if prepared.static_signature != self._static_signature:
            static = self._render_static(prepared.specification, previous, legacy)
            if isinstance(static, FullBodyBridgeResult):
                return static
            previous = static
            self._static_signature = prepared.static_signature
            self._dynamic_signature = None
        state = self._operation_state(operation_generation)
        if state is not None:
            return self._result(state, legacy)
        if prepared.dynamic_signature != self._dynamic_signature:
            dynamic = self._render_dynamic(
                prepared.dynamic_layers,
                previous,
                legacy,
            )
            if isinstance(dynamic, FullBodyBridgeResult):
                return dynamic
            previous = dynamic
        state = self._operation_state(operation_generation)
        return self._result(state, legacy) if state is not None else previous

    def _render_static(
        self,
        specification: FullBodyRenderSpec,
        previous: BodyPoseFrame,
        legacy: BodyPoseFrame,
    ) -> BodyPoseFrame | FullBodyBridgeResult:
        try:
            self._adapter_generation = self._adapter.begin_transition()
            candidate = self._adapter.render_full_body(
                self._adapter_generation,
                specification,
            )
        except _RECOVERABLE_BOUNDARY_ERRORS:
            return self._result(FullBodyBridgeDisposition.LKG, legacy)
        if candidate == previous or candidate.contract != "full-body-v4":
            return self._result(FullBodyBridgeDisposition.LKG, legacy)
        return candidate

    def _render_dynamic(
        self,
        dynamic_layers: tuple[FullBodyRenderLayer, ...],
        previous: BodyPoseFrame,
        legacy: BodyPoseFrame,
    ) -> BodyPoseFrame | FullBodyBridgeResult:
        try:
            candidate = self._adapter.update_speech_layers(
                self._adapter_generation,
                dynamic_layers,
            )
        except _RECOVERABLE_BOUNDARY_ERRORS:
            return self._result(FullBodyBridgeDisposition.LKG, legacy)
        if candidate == previous and dynamic_layers:
            return self._result(FullBodyBridgeDisposition.LKG, legacy)
        return candidate

    def _asset_failure(self, legacy: BodyPoseFrame) -> FullBodyBridgeResult:
        if self._last_good is None:
            return FullBodyBridgeResult(
                FullBodyBridgeDisposition.BYPASS,
                legacy,
                True,
            )
        return self._result(FullBodyBridgeDisposition.LKG, legacy)

    def _operation_state(
        self,
        generation: int,
    ) -> FullBodyBridgeDisposition | None:
        if generation == self._cancelled_generation:
            return FullBodyBridgeDisposition.CANCELLED
        if generation != self._operation_generation:
            return FullBodyBridgeDisposition.STALE
        return None

    def _is_stale(
        self,
        speech: int,
        behavior: int,
        framing: int,
        assets: int,
    ) -> bool:
        return bool(
            speech < self._speech_generation
            or behavior < self._behavior_generation
            or framing < self._framing_generation
            or assets < self._assets_generation
        )

    def _result(
        self,
        disposition: FullBodyBridgeDisposition,
        legacy: BodyPoseFrame,
    ) -> FullBodyBridgeResult:
        if self._last_good is not None:
            return FullBodyBridgeResult(disposition, self._last_good, False)
        return FullBodyBridgeResult(disposition, legacy, True)

    @staticmethod
    def _static_frame_signature(
        behavior_generation: int,
        framing: FramingCommand,
        assets_generation: int,
        specification: FullBodyRenderSpec,
    ) -> tuple[object, ...]:
        return (
            behavior_generation,
            framing.generation,
            framing.crop,
            assets_generation,
            specification.view_id,
            specification.body_profile_id,
            specification.body_profile_version_range,
            specification.rig_id,
            specification.rig_version_range,
            specification.geometry_signature,
            specification.source_evidence,
            tuple(
                (
                    item.layer.name,
                    item.evidence.sha256,
                    item.evidence.evidence,
                )
                for item in specification.static_layers
            ),
        )

    @staticmethod
    def _dynamic_frame_signature(
        speech_generation: int,
        face: str | None,
        viseme: str,
        mouth_closed: bool,
        motion: FaceMotionFrame | None,
        layers: tuple[FullBodyRenderLayer, ...],
    ) -> tuple[object, ...]:
        return (
            speech_generation,
            face,
            viseme,
            mouth_closed,
            _face_motion_signature(motion),
            tuple(
                (item.layer.name, item.evidence.sha256, item.evidence.evidence)
                for item in layers
            ),
        )


def _face_motion_signature(motion: FaceMotionFrame | None) -> tuple[object, ...]:
    """Reduce a continuous face frame to a dedupe-safe signature.

    The full-body renderer deforms the mouth, eyelids, brows, irises, blush and
    lips from the continuous controls in :class:`FaceMotionFrame`.  Two frames
    that differ only in those controls must not be deduplicated, so the
    signature captures every continuous value (rounded to a stable precision)
    alongside the discrete pose/expression/viseme labels.
    """
    if motion is None:
        return ()
    mouth = motion.mouth
    shape = motion.expression_shape
    return (
        motion.pose,
        motion.expression,
        motion.viseme,
        round(mouth.aperture, 6),
        round(mouth.width, 6),
        round(mouth.rounding, 6),
        round(mouth.jaw, 6),
        round(mouth.corner_smile, 6),
        round(shape.blink, 6),
        round(shape.eye_smile, 6),
        round(shape.brow_lift, 6),
        round(shape.brow_tension, 6),
        round(shape.blush, 6),
        round(motion.gaze_x, 6),
        round(motion.gaze_y, 6),
        round(motion.breath, 6),
    )
