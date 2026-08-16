from __future__ import annotations

lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from body_pose_renderer import (
    LAYER_DEPTHS,
    BodyPoseFrame,
    BodyPoseLayer,
    BodyPoseRenderer,
    PoseAssetSet,
)
lazy from character_pose import ViewBlend, default_pose_registry

WIDTH = 2
HEIGHT = 2
FRONT_VIEW = "yaw+000-pitch+00"
LEFT_VIEW = "yaw-030-pitch+00"


@dataclass(frozen=True, slots=True)
class ViewRef:
    view_id: str
    yaw_degrees: int


def pixels(color: tuple[int, int, int, int]) -> bytes:
    return bytes(color) * (WIDTH * HEIGHT)


def transparent() -> bytes:
    return pixels((0, 0, 0, 0))


def single_pixel(color: tuple[int, int, int, int], index: int) -> bytes:
    data = bytearray(transparent())
    data[index * 4 : index * 4 + 4] = bytes(color)
    return bytes(data)


ORDERED_LAYERS = (
    "background",
    "hair-back",
    "body",
    "garment-back",
    "arm-left",
    "arm-right",
    "garment-front",
    "hand-left",
    "hand-right",
    "weapon",
    "hair-front",
    "foreground",
)
EXPECTED_FACE_VISIBLE_ORDER = (
    *ORDERED_LAYERS[:-1],
    "face",
    "foreground",
)


@dataclass(frozen=True, slots=True)
class AssetOptions:
    face_visible: bool = True
    corrections: frozenset[str] = frozenset(
        {"idle_front.png", "idle_lean.png"}
    )
    outfit_compatible: bool = True
    articulation_safe: bool = True
    extra_layers: tuple[BodyPoseLayer, ...] = ()


def asset_set(
    view_id: str,
    color: tuple[int, int, int, int],
    **overrides: object,
) -> PoseAssetSet:
    options = AssetOptions(**overrides)
    layers = tuple(
        BodyPoseLayer(name, LAYER_DEPTHS[name], single_pixel(color, index % 4))
        for index, name in enumerate(ORDERED_LAYERS)
    )
    if options.face_visible:
        layers += (BodyPoseLayer("face", LAYER_DEPTHS["face"], transparent()),)
    return PoseAssetSet(
        view_id=view_id,
        silhouette=(
            "front-crossed" if view_id == FRONT_VIEW else "left-neutral"
        ),
        width=WIDTH,
        height=HEIGHT,
        layers=(*layers, *options.extra_layers),
        available_corrections=options.corrections,
        outfit_compatible=options.outfit_compatible,
        face_visible=options.face_visible,
        articulation_safe=options.articulation_safe,
    )


class Source:
    def __init__(self, assets: dict[str, PoseAssetSet]) -> None:
        self.assets = assets

    def resolve(self, view_id: str) -> PoseAssetSet | None:
        return self.assets.get(view_id)


class Publisher:
    def __init__(self) -> None:
        self.frames: list[BodyPoseFrame] = []
        self.fail = False

    def publish(self, frame: BodyPoseFrame) -> None:
        self.frames.append(frame)
        if self.fail:
            raise RuntimeError("publish failed")


class Articulation:
    def __init__(self) -> None:
        self.continued: list[tuple[str, int]] = []
        self.paused: list[int] = []

    def continue_overlay(
        self, frame: bytes, view_id: str, generation: int
    ) -> bytes:
        self.continued.append((view_id, generation))
        return frame

    def pause(self, generation: int) -> None:
        self.paused.append(generation)


def adjacent_blend(weight: float = 0.5) -> ViewBlend:
    return ViewBlend(
        ViewRef(FRONT_VIEW, 0),
        ViewRef(LEFT_VIEW, -30),
        weight,
        True,
        "adjacent_crossfade",
    )


def poses():
    registry = default_pose_registry()
    return registry.get("front-crossed"), registry.get("left-neutral")


def renderer(
    assets: dict[str, PoseAssetSet],
) -> tuple[BodyPoseRenderer, Publisher, Articulation]:
    publisher = Publisher()
    articulation = Articulation()
    engine = BodyPoseRenderer(
        WIDTH,
        HEIGHT,
        Source(assets),
        publisher,
        articulation,
    )
    return engine, publisher, articulation


def assert_deterministic_atomic_crossfade_and_layer_order() -> None:
    first_pose, second_pose = poses()
    assets = {
        FRONT_VIEW: asset_set(FRONT_VIEW, (40, 80, 120, 255)),
        LEFT_VIEW: asset_set(LEFT_VIEW, (120, 80, 40, 255)),
    }
    engine, publisher, articulation = renderer(assets)
    generation = engine.begin_transition()
    result = engine.render(generation, adjacent_blend(), first_pose, second_pose)
    repeated = engine.render(generation, adjacent_blend(), first_pose, second_pose)
    assert result.rgba == repeated.rgba
    assert result.view_ids == (FRONT_VIEW, LEFT_VIEW)
    assert result.layer_order == EXPECTED_FACE_VISIBLE_ORDER
    assert result.contract == "legacy-v3"
    assert result.rig_id is None
    assert publisher.frames[-1] == repeated
    assert articulation.continued[-1] == (
        f"{FRONT_VIEW}|{LEFT_VIEW}",
        generation,
    )


def assert_fail_closed_keeps_last_known_good() -> None:
    first_pose, second_pose = poses()
    valid_assets = {
        FRONT_VIEW: asset_set(FRONT_VIEW, (20, 30, 40, 255)),
        LEFT_VIEW: asset_set(LEFT_VIEW, (40, 30, 20, 255)),
    }
    engine, publisher, _articulation = renderer(valid_assets)
    good = engine.render(
        engine.begin_transition(), adjacent_blend(), first_pose, second_pose
    )
    cases = (
        {FRONT_VIEW: valid_assets[FRONT_VIEW]},
        {
            **valid_assets,
            LEFT_VIEW: asset_set(LEFT_VIEW, (1, 2, 3, 255), corrections=frozenset()),
        },
        {
            **valid_assets,
            LEFT_VIEW: asset_set(LEFT_VIEW, (1, 2, 3, 255), outfit_compatible=False),
        },
    )
    for assets in cases:
        engine._source = Source(assets)
        result = engine.render(
            engine.begin_transition(), adjacent_blend(), first_pose, second_pose
        )
        assert result == good
        assert publisher.frames[-1] == good


def assert_non_adjacent_and_stale_generation_do_not_publish() -> None:
    first_pose, second_pose = poses()
    assets = {
        FRONT_VIEW: asset_set(FRONT_VIEW, (10, 20, 30, 255)),
        LEFT_VIEW: asset_set(LEFT_VIEW, (30, 20, 10, 255)),
    }
    engine, publisher, _articulation = renderer(assets)
    old_generation = engine.begin_transition()
    current_generation = engine.begin_transition()
    count = len(publisher.frames)
    assert engine.render(old_generation, adjacent_blend(), first_pose, second_pose) == engine.current_frame
    assert len(publisher.frames) == count
    unsafe = ViewBlend(
        adjacent_blend().first,
        adjacent_blend().second,
        0.5,
        False,
        "authored_gap",
    )
    assert engine.render(current_generation, unsafe, first_pose, second_pose) == engine.current_frame
    assert len(publisher.frames) == count


def assert_back_view_never_exposes_face_and_pauses_articulation() -> None:
    first_pose, second_pose = poses()
    assets = {
        FRONT_VIEW: asset_set(FRONT_VIEW, (10, 10, 10, 255), face_visible=False, articulation_safe=False),
        LEFT_VIEW: asset_set(LEFT_VIEW, (20, 20, 20, 255), face_visible=False, articulation_safe=False),
    }
    engine, _publisher, articulation = renderer(assets)
    generation = engine.begin_transition()
    frame = engine.render(generation, adjacent_blend(), first_pose, second_pose)
    assert "face" not in frame.layer_order
    assert articulation.paused == [generation]
    malicious = BodyPoseLayer(
        "face", LAYER_DEPTHS["face"], pixels((255, 0, 0, 255))
    )
    engine._source = Source(
        {**assets, LEFT_VIEW: asset_set(LEFT_VIEW, (20, 20, 20, 255), face_visible=False, extra_layers=(malicious,))}
    )
    assert engine.render(engine.begin_transition(), adjacent_blend(), first_pose, second_pose) == frame


def assert_publish_failure_preserves_complete_previous_frame() -> None:
    first_pose, second_pose = poses()
    assets = {
        FRONT_VIEW: asset_set(FRONT_VIEW, (10, 20, 30, 255)),
        LEFT_VIEW: asset_set(LEFT_VIEW, (30, 20, 10, 255)),
    }
    engine, publisher, _articulation = renderer(assets)
    good = engine.render(
        engine.begin_transition(), adjacent_blend(), first_pose, second_pose
    )
    publisher.fail = True
    try:
        engine.render(
            engine.begin_transition(), adjacent_blend(0.25), first_pose, second_pose
        )
    except RuntimeError as exc:
        assert str(exc) == "publish failed"
    else:
        raise AssertionError("publisher failure must remain visible")
    assert engine.current_frame == good
    assert publisher.frames[-1] == good


def run() -> None:
    assert_deterministic_atomic_crossfade_and_layer_order()
    assert_fail_closed_keeps_last_known_good()
    assert_non_adjacent_and_stale_generation_do_not_publish()
    assert_back_view_never_exposes_face_and_pauses_articulation()
    assert_publish_failure_preserves_complete_previous_frame()
    print("BODY_POSE_RENDERER_OK")


if __name__ == "__main__":
    run()
