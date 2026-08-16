from __future__ import annotations

lazy import hashlib
lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from appearance_dynamics import (
    AppearanceDynamics,
    DynamicsConfiguration,
    DynamicsInput,
    DynamicsMode,
)
lazy from appearance_renderer import (
    AppearanceLayer,
    AppearanceRenderer,
    AppearanceRenderError,
    CoreAppearanceManifest,
    PixelMask,
    ResolvedLayerAsset,
)

WIDTH = 8
HEIGHT = 8


def rgba(width: int, height: int, color: tuple[int, int, int, int]) -> bytes:
    return bytes(color) * (width * height)


def mask(*points: tuple[int, int]) -> PixelMask:
    values = bytearray(WIDTH * HEIGHT)
    for x, y in points:
        values[y * WIDTH + x] = 1
    return PixelMask(WIDTH, HEIGHT, bytes(values))


def region(x1: int, y1: int, x2: int, y2: int) -> PixelMask:
    return mask(
        *((x, y) for y in range(y1, y2) for x in range(x1, x2))
    )


def core_manifest() -> CoreAppearanceManifest:
    core = rgba(WIDTH, HEIGHT, (30, 40, 50, 255))
    identity = region(2, 1, 6, 4)
    hands = region(1, 4, 7, 6)
    return CoreAppearanceManifest(
        width=WIDTH,
        height=HEIGHT,
        core_rgba=core,
        immutable_identity=identity,
        approved_regions={
            "body": region(0, 3, 8, 8),
            "hair": region(0, 0, 8, 5),
            "head-attachment": region(0, 0, 8, 3),
            "hand-attachment": region(0, 3, 8, 7),
            "foreground": region(0, 0, 8, 8),
        },
        occlusion_masks={"face-safe": identity, "hands-safe": hands},
    )


class Resolver:
    def __init__(self, assets: dict[str, ResolvedLayerAsset]) -> None:
        self.assets = assets

    def resolve(self, path: str) -> ResolvedLayerAsset | None:
        return self.assets.get(path)


class Publisher:
    def __init__(self) -> None:
        self.frames: list[bytes] = []
        self.fail = False

    def publish(self, frame: bytes) -> None:
        self.frames.append(frame)
        if self.fail:
            raise RuntimeError("publish failed")


def asset(path: str, color: tuple[int, int, int, int]) -> ResolvedLayerAsset:
    pixels = bytearray(rgba(3, 3, (0, 0, 0, 0)))
    pixels[16:20] = bytes(color)
    data = bytes(pixels)
    return ResolvedLayerAsset(path, 3, 3, data)


def layer(  # noqa: PLR0913 -- mirrors the immutable layer contract
    path: str,
    *,
    slot: str,
    z_order: int,
    anchor: tuple[int, int],
    approved_region: str,
    occlusion_masks: tuple[str, ...] = (),
) -> AppearanceLayer:
    payload = ASSETS[path]
    return AppearanceLayer(
        slot=slot,
        path=path,
        sha256=hashlib.sha256(payload.rgba).hexdigest(),
        width=payload.width,
        height=payload.height,
        anchor_x=anchor[0],
        anchor_y=anchor[1],
        z_order=z_order,
        approved_region=approved_region,
        occlusion_masks=occlusion_masks,
    )


ASSETS = {
    "garment": asset("garment", (120, 20, 30, 255)),
    "hair": asset("hair", (20, 20, 25, 255)),
    "headwear": asset("headwear", (180, 180, 190, 255)),
    "weapon": asset("weapon", (90, 100, 110, 255)),
    "handheld": asset("handheld", (220, 150, 30, 255)),
}


def assert_core_identity_never_changes_and_order_is_deterministic() -> None:
    manifest = core_manifest()
    renderer = AppearanceRenderer(manifest, Resolver(ASSETS))
    layers = (
        layer("garment", slot="garment", z_order=10, anchor=(0, 5), approved_region="body"),
        layer("hair", slot="hair", z_order=20, anchor=(0, 0), approved_region="hair", occlusion_masks=("face-safe",)),
        layer("headwear", slot="headwear", z_order=30, anchor=(0, 0), approved_region="head-attachment", occlusion_masks=("face-safe",)),
        layer("weapon", slot="weapon", z_order=40, anchor=(0, 4), approved_region="hand-attachment", occlusion_masks=("hands-safe",)),
        layer("handheld", slot="handheld", z_order=50, anchor=(5, 4), approved_region="hand-attachment", occlusion_masks=("hands-safe",)),
    )
    frame = renderer.render("front-crossed", tuple(reversed(layers)))
    assert frame.applied_slots == (
        "garment", "hair", "headwear", "weapon", "handheld"
    )
    for index, protected in enumerate(manifest.immutable_identity.values):
        if protected:
            start = index * 4
            assert frame.rgba[start : start + 4] == manifest.core_rgba[start : start + 4]


def assert_face_and_hand_occlusion_masks_clip_layers() -> None:
    manifest = core_manifest()
    renderer = AppearanceRenderer(manifest, Resolver(ASSETS))
    hair = layer(
        "hair", slot="hair", z_order=10, anchor=(2, 1),
        approved_region="hair", occlusion_masks=("face-safe",),
    )
    weapon = layer(
        "weapon", slot="weapon", z_order=20, anchor=(2, 3),
        approved_region="hand-attachment", occlusion_masks=("hands-safe",),
    )
    frame = renderer.render("front-crossed", (hair, weapon))
    assert frame.rgba == manifest.core_rgba


def assert_missing_conflict_and_malicious_assets_fail_closed() -> None:
    renderer = AppearanceRenderer(core_manifest(), Resolver(ASSETS))
    valid = layer(
        "garment", slot="garment", z_order=10, anchor=(0, 5),
        approved_region="body",
    )
    cases = [
        ("", (valid,)),
        ("front-crossed", (valid, valid)),
        ("front-crossed", (valid.replace(path="missing"),)),
        ("front-crossed", (valid.replace(width=4),)),
        ("front-crossed", (valid.replace(sha256="0" * 64),)),
        ("front-crossed", (valid.replace(anchor_x=7),)),
    ]
    for silhouette, layers in cases:
        try:
            renderer.render(silhouette, layers)
        except AppearanceRenderError:
            pass
        else:
            raise AssertionError("invalid layer set must fail closed")
    oversized = ResolvedLayerAsset(
        "oversized", WIDTH + 1, HEIGHT + 1,
        rgba(WIDTH + 1, HEIGHT + 1, (1, 2, 3, 255)),
    )
    oversized_layer = AppearanceLayer(
        "garment", "oversized", hashlib.sha256(oversized.rgba).hexdigest(),
        oversized.width, oversized.height, 0, 0, 60, "body", (),
    )
    try:
        AppearanceRenderer(core_manifest(), Resolver({"oversized": oversized})).render(
            "front-crossed", (oversized_layer,)
        )
    except AppearanceRenderError:
        pass
    else:
        raise AssertionError("oversized asset must fail closed")


def assert_alpha_edges_and_approved_regions_fail_closed() -> None:
    hard_edge = ResolvedLayerAsset("hard-edge", 2, 2, rgba(2, 2, (1, 2, 3, 255)))
    hidden_rgb = ResolvedLayerAsset("hidden-rgb", 2, 2, rgba(2, 2, (1, 2, 3, 0)))
    for payload in (hard_edge, hidden_rgb):
        declaration = AppearanceLayer(
            "garment", payload.path, hashlib.sha256(payload.rgba).hexdigest(),
            2, 2, 3, 5, 10, "body", (),
        )
        try:
            AppearanceRenderer(core_manifest(), Resolver({payload.path: payload})).render(
                "front-crossed", (declaration,)
            )
        except AppearanceRenderError:
            pass
        else:
            raise AssertionError("unsafe alpha edge must fail closed")


def assert_publish_failure_preserves_previous_frame() -> None:
    publisher = Publisher()
    renderer = AppearanceRenderer(core_manifest(), Resolver(ASSETS), publisher)
    first = renderer.render("front-crossed", ())
    publisher.fail = True
    garment = layer(
        "garment", slot="garment", z_order=10, anchor=(0, 5),
        approved_region="body",
    )
    try:
        renderer.render("front-crossed", (garment,))
    except RuntimeError as exc:
        assert str(exc) == "publish failed"
    else:
        raise AssertionError("publish failure must be visible")
    assert renderer.current_frame == first
    assert publisher.frames[-1] == first.rgba


def assert_static_default_preserves_legacy_result_exactly() -> None:
    renderer = AppearanceRenderer(core_manifest(), Resolver(ASSETS))
    garment = layer(
        "garment", slot="garment", z_order=10, anchor=(0, 5),
        approved_region="body",
    )
    frame = renderer.render(
        "front-crossed",
        (garment,),
        DynamicsInput(1.0),
    )
    legacy = AppearanceRenderer(core_manifest(), Resolver(ASSETS)).render(
        "front-crossed", (garment,)
    )
    assert frame.rgba == legacy.rgba
    assert frame.applied_slots == legacy.applied_slots
    assert frame.layer_transforms == ()


def assert_dynamic_modes_emit_bounded_known_slot_descriptions() -> None:
    layers = (
        layer(
            "garment", slot="garment", z_order=10, anchor=(0, 5),
            approved_region="body",
        ),
        layer(
            "hair", slot="hair", z_order=20, anchor=(0, 0),
            approved_region="hair", occlusion_masks=("face-safe",),
        ),
        layer(
            "headwear", slot="unknown-slot", z_order=30, anchor=(0, 0),
            approved_region="head-attachment", occlusion_masks=("face-safe",),
        ),
    )
    for mode, expected_slots in (
        (DynamicsMode.REDUCED, ("garment", "hair")),
        (DynamicsMode.FULL, ("garment", "hair")),
    ):
        dynamics = AppearanceDynamics(
            DynamicsConfiguration(enabled=True, mode=mode)
        )
        renderer = AppearanceRenderer(
            core_manifest(), Resolver(ASSETS), dynamics=dynamics
        )
        frame = renderer.render(
            "front-crossed",
            layers,
            DynamicsInput(1.0 / 60.0, motion_x=0.8),
        )
        assert tuple(item.slot for item in frame.layer_transforms) == expected_slots
        assert all(abs(item.transform.offset_x) <= 10 for item in frame.layer_transforms)
        assert all(abs(item.transform.rotation_degrees) <= 12 for item in frame.layer_transforms)
        assert frame.rgba == AppearanceRenderer(
            core_manifest(), Resolver(ASSETS)
        ).render("front-crossed", layers).rgba


def assert_unavailable_backend_and_publish_failure_are_static_or_atomic() -> None:
    garment = layer(
        "garment", slot="garment", z_order=10, anchor=(0, 5),
        approved_region="body",
    )
    unavailable = AppearanceRenderer(
        core_manifest(),
        Resolver(ASSETS),
        dynamics=AppearanceDynamics(
            DynamicsConfiguration(enabled=True), backend_available=False
        ),
    )
    assert unavailable.render(
        "front-crossed", (garment,), DynamicsInput(1.0)
    ).layer_transforms == ()

    publisher = Publisher()
    dynamics = AppearanceDynamics(DynamicsConfiguration(enabled=True))
    renderer = AppearanceRenderer(
        core_manifest(), Resolver(ASSETS), publisher, dynamics
    )
    before = dynamics.snapshot()
    publisher.fail = True
    try:
        renderer.render(
            "front-crossed",
            (garment,),
            DynamicsInput(1.0 / 60.0, motion_x=1.0),
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("failed publish must remain visible")
    assert dynamics.snapshot() == before


def run() -> None:
    assert_core_identity_never_changes_and_order_is_deterministic()
    assert_face_and_hand_occlusion_masks_clip_layers()
    assert_missing_conflict_and_malicious_assets_fail_closed()
    assert_alpha_edges_and_approved_regions_fail_closed()
    assert_publish_failure_preserves_previous_frame()
    assert_static_default_preserves_legacy_result_exactly()
    assert_dynamic_modes_emit_bounded_known_slot_descriptions()
    assert_unavailable_backend_and_publish_failure_are_static_or_atomic()
    print("APPEARANCE_RENDERER_OK")


if __name__ == "__main__":
    run()
