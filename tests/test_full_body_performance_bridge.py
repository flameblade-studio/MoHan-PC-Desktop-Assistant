from __future__ import annotations

lazy import hashlib
lazy import sys
lazy from dataclasses import dataclass, replace
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from behavior_director import BreathStyle, GazeTarget, TransitionStyle
lazy from body_pose_renderer import LAYER_DEPTHS, BodyPoseFrame, BodyPoseLayer
lazy from full_body_performance_bridge import (
    FramingCommand,
    FullBodyBridgeDisposition,
    FullBodyBridgeRequest,
    FullBodyPerformanceBridge,
)
lazy from full_body_render_adapter import (
    SPEECH_LAYER_SLOTS,
    V4_STATIC_LAYER_SLOTS,
    FullBodyLayerEvidence,
    FullBodyRenderAdapter,
    FullBodyRenderLayer,
    FullBodyRenderSpec,
    NormalizedCrop,
)
lazy from performance_coordinator import PerformanceFrame
lazy from performance_runtime import AtomicPerformanceFrame
lazy from speech_performance import (
    SpeechEventKind,
    SpeechPerformancePhase,
)

WIDTH = 2
HEIGHT = 2


def pixels(color: tuple[int, int, int, int]) -> bytes:
    return bytes(color) * WIDTH * HEIGHT


def render_layer(slot: str, shade: int = 1) -> FullBodyRenderLayer:
    alpha = 255 if slot == "body" or slot in SPEECH_LAYER_SLOTS else 0
    rgba = pixels((shade, shade, shade, alpha))
    return FullBodyRenderLayer(
        BodyPoseLayer(slot, LAYER_DEPTHS[slot], rgba),
        FullBodyLayerEvidence(
            slot,
            hashlib.sha256(rgba).hexdigest(),
            f"evidence-{slot}-{shade}",
        ),
    )


def spec(view: str = "yaw+000-pitch+00") -> FullBodyRenderSpec:
    return FullBodyRenderSpec(
        view,
        WIDTH,
        HEIGHT,
        "mohan-body-v1",
        (1, 2),
        "mohan-full-body-v1",
        (1, 2),
        (0.5, 0.48, 0.36, 0.21, 0.1),
        NormalizedCrop(0.0, 0.0, 1.0, 1.0),
        tuple(render_layer(slot) for slot in V4_STATIC_LAYER_SLOTS),
        "v4-source-proof",
    )


def performance(
    *,
    speech_generation: int = 1,
    behavior_generation: int = 1,
    viseme: str = "A",
    mouth_closed: bool = False,
) -> AtomicPerformanceFrame:
    pose = "front-crossed"
    view = "yaw+000-pitch+00"
    frame = PerformanceFrame(
        speech_generation,
        behavior_generation,
        SpeechEventKind.VISEME,
        SpeechPerformancePhase.SPEAKING,
        pose,
        view,
        "neutral",
        "relaxed-left",
        "relaxed-right",
        GazeTarget.USER,
        BreathStyle.SPEAKING,
        TransitionStyle.HOLD,
        20,
        viseme,
        mouth_closed,
        0.4,
        False,
        False,
    )
    legacy = BodyPoseFrame(
        WIDTH,
        HEIGHT,
        pixels((9, 9, 9, 255)),
        behavior_generation,
        (view,),
        ("body",),
        True,
    )
    return AtomicPerformanceFrame(frame, legacy)


@dataclass
class Assets:
    generation: int = 1
    enabled: bool = True
    missing_static: bool = False
    missing_dynamic: bool = False
    fail_static: bool = False
    fail_dynamic: bool = False
    on_static: object | None = None

    def resolve_static(self, _pose: str, view: str) -> FullBodyRenderSpec | None:
        if callable(self.on_static):
            self.on_static()
        if self.fail_static:
            raise OSError("asset source unavailable")
        return None if self.missing_static else spec(view)

    def resolve_speech(
        self,
        _face: str | None,
        viseme: str,
        _mouth_closed: bool,
    ) -> tuple[FullBodyRenderLayer, ...] | None:
        if self.missing_dynamic:
            return None
        if self.fail_dynamic:
            raise ValueError("invalid dynamic asset")
        shade = max(1, sum(ord(character) for character in viseme) % 255)
        return tuple(render_layer(slot, shade) for slot in SPEECH_LAYER_SLOTS)


class Publisher:
    def __init__(self) -> None:
        self.frames: list[BodyPoseFrame] = []

    def publish(self, frame: BodyPoseFrame) -> None:
        self.frames.append(frame)


def bridge() -> tuple[FullBodyPerformanceBridge, FullBodyRenderAdapter, Publisher]:
    publisher = Publisher()
    adapter = FullBodyRenderAdapter(WIDTH, HEIGHT, publisher)
    return FullBodyPerformanceBridge(adapter), adapter, publisher


def request(
    engine: FullBodyPerformanceBridge,
    frame: AtomicPerformanceFrame | None = None,
    *,
    assets: Assets | None = None,
    framing_generation: int = 1,
    operation_generation: int | None = None,
) -> FullBodyBridgeRequest:
    operation = (
        engine.begin_operation()
        if operation_generation is None
        else operation_generation
    )
    return FullBodyBridgeRequest(
        operation,
        frame or performance(),
        FramingCommand(
            framing_generation,
            NormalizedCrop(0.1, 0.0, 0.8, 1.0),
        ),
        assets if assets is not None else Assets(),
        True,
    )


def assert_atomic_input_produces_one_publishable_v4_frame() -> None:
    engine, adapter, publisher = bridge()
    result = engine.dispatch(request(engine))
    assert result.disposition is FullBodyBridgeDisposition.PUBLISHED
    assert not result.used_legacy
    assert result.frame.contract == "full-body-v4"
    assert result.frame.crop == (0.1, 0.0, 0.8, 1.0)
    assert adapter.static_compositions == 1
    assert publisher.frames[-1] == result.frame


def assert_50hz_speech_does_not_rebuild_static_body() -> None:
    engine, adapter, _publisher = bridge()
    first = engine.dispatch(request(engine))
    assert first.disposition is FullBodyBridgeDisposition.PUBLISHED
    static_count = adapter.static_compositions
    static_revision = first.frame.static_revision
    for tick in range(2, 52):
        frame = performance(speech_generation=tick, viseme=f"V{tick}")
        result = engine.dispatch(request(engine, frame))
        assert result.disposition is FullBodyBridgeDisposition.PUBLISHED
        assert result.frame.static_revision == static_revision
    assert adapter.static_compositions == static_count


def assert_body_framing_or_assets_generation_rebuilds_static_once() -> None:
    engine, adapter, _publisher = bridge()
    assert (
        engine.dispatch(request(engine)).disposition
        is FullBodyBridgeDisposition.PUBLISHED
    )
    assert adapter.static_compositions == 1
    behavior = performance(speech_generation=2, behavior_generation=2)
    assert (
        engine.dispatch(request(engine, behavior)).disposition
        is FullBodyBridgeDisposition.PUBLISHED
    )
    assert adapter.static_compositions == 2
    speech_only = performance(speech_generation=3, behavior_generation=2, viseme="E")
    assert (
        engine.dispatch(request(engine, speech_only)).disposition
        is FullBodyBridgeDisposition.PUBLISHED
    )
    assert adapter.static_compositions == 2
    assert (
        engine.dispatch(request(engine, speech_only, framing_generation=2)).disposition
        is FullBodyBridgeDisposition.PUBLISHED
    )
    assert adapter.static_compositions == 3
    assert (
        engine.dispatch(
            request(
                engine, speech_only, assets=Assets(generation=2), framing_generation=2
            )
        ).disposition
        is FullBodyBridgeDisposition.PUBLISHED
    )
    assert adapter.static_compositions == 4


def assert_stale_cancel_dedupe_and_lkg_are_explicit() -> None:
    engine, adapter, _publisher = bridge()
    current_request = request(engine)
    first = engine.dispatch(current_request)
    duplicate_operation = engine.begin_operation()
    duplicate = replace(current_request, operation_generation=duplicate_operation)
    assert engine.dispatch(duplicate).disposition is FullBodyBridgeDisposition.DEDUPED
    stale_operation = duplicate_operation
    engine.begin_operation()
    assert (
        engine.dispatch(
            replace(duplicate, operation_generation=stale_operation)
        ).disposition
        is FullBodyBridgeDisposition.STALE
    )
    cancelled_operation = engine.begin_operation()
    engine.cancel(cancelled_operation)
    assert (
        engine.dispatch(
            replace(duplicate, operation_generation=cancelled_operation)
        ).disposition
        is FullBodyBridgeDisposition.CANCELLED
    )
    stale_frame = performance(speech_generation=0, behavior_generation=0)
    assert (
        engine.dispatch(request(engine, stale_frame)).disposition
        is FullBodyBridgeDisposition.STALE
    )
    before = adapter.current_frame
    invalid = Assets()
    original = invalid.resolve_static
    invalid.resolve_static = lambda pose, view: replace(
        original(pose, view), rig_id="bad"
    )  # type: ignore[arg-type,method-assign]
    result = engine.dispatch(
        request(engine, performance(speech_generation=2), assets=invalid)
    )
    assert result.disposition is FullBodyBridgeDisposition.LKG
    assert result.frame == first.frame == before


def assert_disabled_or_missing_assets_bypass_to_legacy() -> None:
    for assets, enabled in (
        (Assets(), False),
        (Assets(enabled=False), True),
        (Assets(missing_static=True), True),
        (Assets(missing_dynamic=True), True),
        (None, True),
    ):
        engine, _adapter, publisher = bridge()
        operation = engine.begin_operation()
        frame = performance()
        result = engine.dispatch(
            FullBodyBridgeRequest(
                operation,
                frame,
                FramingCommand(1, NormalizedCrop(0.0, 0.0, 1.0, 1.0)),
                assets,
                enabled,
            )
        )
        assert result.disposition is FullBodyBridgeDisposition.BYPASS
        assert result.used_legacy
        assert result.frame == frame.body
        assert publisher.frames == []


def assert_asset_errors_and_mid_resolution_cancel_never_crash() -> None:
    for assets in (Assets(fail_static=True), Assets(fail_dynamic=True)):
        engine, _adapter, publisher = bridge()
        result = engine.dispatch(request(engine, assets=assets))
        assert result.disposition is FullBodyBridgeDisposition.BYPASS
        assert result.used_legacy
        assert publisher.frames == []

    engine, _adapter, publisher = bridge()
    operation = engine.begin_operation()
    assets = Assets(on_static=lambda: engine.cancel(operation))
    result = engine.dispatch(
        request(engine, assets=assets, operation_generation=operation)
    )
    assert result.disposition is FullBodyBridgeDisposition.CANCELLED
    assert result.used_legacy
    assert publisher.frames == []

    engine, _adapter, _publisher = bridge()
    assert (
        engine.dispatch(request(engine)).disposition
        is FullBodyBridgeDisposition.PUBLISHED
    )
    failed = engine.dispatch(
        request(
            engine, performance(speech_generation=2), assets=Assets(fail_static=True)
        )
    )
    assert failed.disposition is FullBodyBridgeDisposition.LKG
    assert not failed.used_legacy


def run() -> None:
    assert_atomic_input_produces_one_publishable_v4_frame()
    assert_50hz_speech_does_not_rebuild_static_body()
    assert_body_framing_or_assets_generation_rebuilds_static_once()
    assert_stale_cancel_dedupe_and_lkg_are_explicit()
    assert_disabled_or_missing_assets_bypass_to_legacy()
    assert_asset_errors_and_mid_resolution_cancel_never_crash()
    print("FULL_BODY_PERFORMANCE_BRIDGE_OK")


if __name__ == "__main__":
    run()
