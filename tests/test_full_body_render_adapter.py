from __future__ import annotations

lazy import hashlib
lazy import sys
lazy from dataclasses import replace
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.body_pose_renderer import LAYER_DEPTHS, BodyPoseFrame, BodyPoseLayer
lazy from application.full_body_render_adapter import (
    AUTHORED_FULL_BODY_SLOT,
    SPEECH_LAYER_SLOTS,
    V4_STATIC_LAYER_SLOTS,
    FullBodyLayerEvidence,
    FullBodyRenderAdapter,
    FullBodyRenderLayer,
    FullBodyRenderSpec,
    NormalizedCrop,
)

WIDTH = 3
HEIGHT = 4


def pixels(color: tuple[int, int, int, int]) -> bytes:
    return bytes(color) * WIDTH * HEIGHT


def layer(slot: str, shade: int = 1) -> FullBodyRenderLayer:
    rgba = pixels((shade, shade, shade, 255 if slot == "body" else 0))
    return FullBodyRenderLayer(
        BodyPoseLayer(slot, LAYER_DEPTHS[slot], rgba),
        FullBodyLayerEvidence(
            slot,
            hashlib.sha256(rgba).hexdigest(),
            f"verified-{slot}",
        ),
    )


def specification(view_id: str = "yaw+000-pitch+00") -> FullBodyRenderSpec:
    return FullBodyRenderSpec(
        view_id,
        WIDTH,
        HEIGHT,
        "mohan-body-v2",
        (2, 3),
        "mohan-full-body-v1",
        (1, 2),
        (0.5, 0.485, 0.37, 0.215, 0.11, 0.005),
        NormalizedCrop(0.1, 0.0, 0.8, 1.0),
        tuple(layer(slot) for slot in V4_STATIC_LAYER_SLOTS),
        "source-proof-v4",
    )


def atomic_specification() -> FullBodyRenderSpec:
    rgba = pixels((10, 20, 30, 255))
    atomic = FullBodyRenderLayer(
        BodyPoseLayer(
            AUTHORED_FULL_BODY_SLOT,
            LAYER_DEPTHS[AUTHORED_FULL_BODY_SLOT],
            rgba,
        ),
        FullBodyLayerEvidence(
            AUTHORED_FULL_BODY_SLOT,
            hashlib.sha256(rgba).hexdigest(),
            "verified-authored-full-body",
        ),
    )
    return replace(specification(), static_layers=(atomic,))


class Publisher:
    def __init__(self) -> None:
        self.frames: list[BodyPoseFrame] = []
        self.fail = False

    def publish(self, frame: BodyPoseFrame) -> None:
        self.frames.append(frame)
        if self.fail:
            raise RuntimeError("publish failed")


def assert_v4_frame_is_complete_and_atomic() -> None:
    publisher = Publisher()
    adapter = FullBodyRenderAdapter(WIDTH, HEIGHT, publisher)
    frame = adapter.render_full_body(adapter.begin_transition(), specification())
    assert frame.contract == "full-body-v4"
    assert frame.body_profile_id == "mohan-body-v2"
    assert frame.rig_id == "mohan-full-body-v1"
    assert set(frame.layer_order) == V4_STATIC_LAYER_SLOTS
    assert frame.crop == (0.1, 0.0, 0.8, 1.0)
    assert adapter.static_compositions == 1
    assert publisher.frames == [frame]


def assert_authored_full_body_is_an_explicit_atomic_contract() -> None:
    publisher = Publisher()
    adapter = FullBodyRenderAdapter(WIDTH, HEIGHT, publisher)
    frame = adapter.render_full_body(
        adapter.begin_transition(),
        atomic_specification(),
    )
    assert frame.layer_order == (AUTHORED_FULL_BODY_SLOT,)
    assert frame.rgba == pixels((10, 20, 30, 255))
    mixed = replace(
        specification(),
        static_layers=(
            *specification().static_layers,
            atomic_specification().static_layers[0],
        ),
    )
    assert adapter.render_full_body(adapter.begin_transition(), mixed) == frame


def assert_missing_layer_or_evidence_keeps_lkg() -> None:
    publisher = Publisher()
    adapter = FullBodyRenderAdapter(WIDTH, HEIGHT, publisher)
    good = adapter.render_full_body(adapter.begin_transition(), specification())
    incomplete = specification("yaw+015-pitch+00")
    incomplete = replace(incomplete, static_layers=incomplete.static_layers[:-1])
    assert adapter.render_full_body(adapter.begin_transition(), incomplete) == good
    wrong_profile = replace(specification(), body_profile_id="another-body")
    assert adapter.render_full_body(adapter.begin_transition(), wrong_profile) == good
    wrong_rig = replace(specification(), rig_version_range=(2, 3))
    assert adapter.render_full_body(adapter.begin_transition(), wrong_rig) == good
    assert publisher.frames == [good]


def assert_50hz_speech_only_recomposes_dynamic_layers() -> None:
    publisher = Publisher()
    adapter = FullBodyRenderAdapter(WIDTH, HEIGHT, publisher)
    generation = adapter.begin_transition()
    base = adapter.render_full_body(generation, specification())
    static_revision = base.static_revision
    static_count = adapter.static_compositions
    frames = []
    for tick in range(50):
        dynamic = tuple(layer(slot, tick + 2) for slot in SPEECH_LAYER_SLOTS)
        frames.append(adapter.update_speech_layers(generation, dynamic))
    assert adapter.static_compositions == static_count
    assert all(frame.static_revision == static_revision for frame in frames)
    assert all(frame.geometry_signature == base.geometry_signature for frame in frames)
    assert all(frame.crop == base.crop for frame in frames)
    assert all(frame.articulation_active for frame in frames)
    assert all(
        len(frame.layer_order) == len(V4_STATIC_LAYER_SLOTS) + len(SPEECH_LAYER_SLOTS)
        for frame in frames
    )


def assert_generation_barrier_and_transition_prevent_sudden_scale() -> None:
    publisher = Publisher()
    adapter = FullBodyRenderAdapter(WIDTH, HEIGHT, publisher)
    first_generation = adapter.begin_transition()
    good = adapter.render_full_body(first_generation, specification())
    current_generation = adapter.begin_transition()
    stale = adapter.update_speech_layers(
        first_generation,
        (layer("mouth", 99),),
    )
    assert stale == good
    scaled = replace(
        specification("yaw+015-pitch+00"),
        geometry_signature=(0.7, 0.6),
    )
    assert adapter.crossfade_full_body(
        current_generation,
        specification(),
        scaled,
        0.5,
    ) == good
    cropped = replace(
        specification("yaw+015-pitch+00"),
        crop=NormalizedCrop(0.0, 0.0, 1.0, 1.0),
    )
    assert adapter.crossfade_full_body(
        current_generation,
        specification(),
        cropped,
        0.5,
    ) == good
    safe = adapter.crossfade_full_body(
        current_generation,
        specification(),
        specification("yaw+015-pitch+00"),
        0.5,
    )
    assert safe.view_ids == ("yaw+000-pitch+00", "yaw+015-pitch+00")
    assert safe.geometry_signature == good.geometry_signature
    assert safe.crop == good.crop


def assert_publish_failure_restores_lkg() -> None:
    publisher = Publisher()
    adapter = FullBodyRenderAdapter(WIDTH, HEIGHT, publisher)
    good = adapter.render_full_body(adapter.begin_transition(), specification())
    publisher.fail = True
    try:
        adapter.render_full_body(adapter.begin_transition(), specification())
    except RuntimeError as error:
        assert str(error) == "publish failed"
    else:
        raise AssertionError("Publisher failure must remain visible.")
    assert adapter.current_frame == good
    assert publisher.frames[-1] == good


def run() -> None:
    assert_v4_frame_is_complete_and_atomic()
    assert_authored_full_body_is_an_explicit_atomic_contract()
    assert_missing_layer_or_evidence_keeps_lkg()
    assert_50hz_speech_only_recomposes_dynamic_layers()
    assert_generation_barrier_and_transition_prevent_sudden_scale()
    assert_publish_failure_restores_lkg()
    print("FULL_BODY_RENDER_ADAPTER_OK")


if __name__ == "__main__":
    run()
