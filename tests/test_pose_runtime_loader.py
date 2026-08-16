from __future__ import annotations

lazy import hashlib
lazy import sys
lazy import threading
lazy from dataclasses import replace
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from character_pose import CANONICAL_YAWS, canonical_view_id
lazy from pose_runtime_loader import (
    AtlasApproval,
    DecodedRgba,
    PoseAtlasManifest,
    PoseRuntimeAtlas,
    PoseRuntimeLimits,
    PoseRuntimeLoader,
    PoseViewSpec,
)

WIDTH = 2
HEIGHT = 2


def encoded(yaw: int, *, invalid: bool = False) -> bytes:
    if invalid:
        return b"broken"
    shade = (yaw + 180) // 15
    return b"RGBA" + bytes((WIDTH, HEIGHT)) + bytes((shade, 20, 30, 255)) * 4


def manifest(
    *,
    omit: int | None = None,
    duplicate: bool = False,
    bad_path: bool = False,
    bad_hash: bool = False,
) -> PoseAtlasManifest:
    views = []
    for yaw in CANONICAL_YAWS:
        if yaw == omit:
            continue
        path = f"assets/{canonical_view_id(yaw)}.rgba"
        if bad_path and yaw == 0:
            path = "../escape.rgba"
        digest = hashlib.sha256(encoded(yaw)).hexdigest()
        if bad_hash and yaw == 0:
            digest = "0" * 64
        views.append(
            PoseViewSpec(
                canonical_view_id(yaw),
                yaw,
                path,
                digest,
                WIDTH,
                HEIGHT,
                "identity-lock-v1",
                "source-proof-v1",
                "mohan-body-v1",
                "mohan-full-body-v1",
                (1, 2),
                frozenset({
                    "left-leg-correction",
                    "right-leg-correction",
                    "left-foot-correction",
                    "right-foot-correction",
                    "left-sole-correction",
                    "right-sole-correction",
                }),
            )
        )
    if duplicate:
        views.append(views[0])
    return PoseAtlasManifest(
        "atlas-a",
        "source-proof-v1",
        tuple(views),
        "full-body-v4",
        2,
        "mohan-body-v1",
        (1, 2),
        "mohan-full-body-v1",
        (1, 2),
    )


class Source:
    def __init__(self, data: dict[str, bytes]) -> None:
        self.data = data
        self.revision_value = "revision-1"
        self.change_after_reads: int | None = None
        self.reads = 0

    def revision(self) -> str:
        return self.revision_value

    def read(self, path: str) -> bytes:
        self.reads += 1
        if self.change_after_reads == self.reads:
            self.revision_value = "revision-2"
        return self.data[path]


class Decoder:
    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.block = False

    def decode(self, data: bytes) -> DecodedRgba:
        if self.block:
            self.entered.set()
            assert self.release.wait(timeout=2.0)
        if len(data) < 6 or data[:4] != b"RGBA":
            raise ValueError("invalid image")
        width, height = data[4], data[5]
        rgba = data[6:]
        if len(rgba) != width * height * 4:
            raise ValueError("invalid image size")
        return DecodedRgba(width, height, rgba)


class Auditor:
    def __init__(self) -> None:
        self.passed = True
        self.problems: tuple[str, ...] = ()
        self.calls: list[PoseRuntimeAtlas] = []

    def audit(self, atlas: PoseRuntimeAtlas) -> AtlasApproval:
        self.calls.append(atlas)
        return AtlasApproval(self.passed, "audit-proof-v1", self.problems)


class Activator:
    def __init__(self) -> None:
        self.calls: list[PoseRuntimeAtlas] = []
        self.fail = False

    def activate(self, atlas: PoseRuntimeAtlas) -> None:
        self.calls.append(atlas)
        if self.fail:
            raise RuntimeError("activation failed")


def source_for(specification: PoseAtlasManifest) -> Source:
    return Source({
        view.path: encoded(view.yaw_degrees)
        for view in specification.views
        if ".." not in view.path
    })


def legacy_atlas() -> PoseRuntimeAtlas:
    return PoseRuntimeAtlas(
        "builtin-three-view",
        "builtin",
        "builtin-audit",
        tuple(
            (yaw, DecodedRgba(WIDTH, HEIGHT, bytes((1, 2, 3, 255)) * 4))
            for yaw in (-30, 0, 30)
        ),
        "legacy-v3",
        "mohan-body-v1",
        None,
    )


def loader(
    specification: PoseAtlasManifest | None = None,
) -> tuple[PoseRuntimeLoader, Source, Decoder, Auditor, Activator]:
    selected = specification or manifest()
    source = source_for(selected)
    decoder = Decoder()
    auditor = Auditor()
    activator = Activator()
    engine = PoseRuntimeLoader(legacy_atlas(), source, decoder, auditor, activator)
    return engine, source, decoder, auditor, activator


def assert_complete_atlas_activates_atomically() -> None:
    specification = manifest()
    engine, _source, _decoder, auditor, activator = loader(specification)
    result = engine.load(engine.begin_load(), specification)
    assert result.status == "activated"
    assert result.active_atlas.complete_360
    assert result.active_atlas.full_body
    assert not result.active_atlas.legacy_fallback
    assert len(result.active_atlas.views) == 24
    assert result.active_atlas.audit_evidence == "audit-proof-v1"
    assert auditor.calls[0].source_evidence == "source-proof-v1"
    assert activator.calls == [result.active_atlas]


def assert_invalid_inputs_keep_legacy() -> None:
    cases = (
        manifest(omit=165),
        manifest(duplicate=True),
        manifest(bad_path=True),
        manifest(bad_hash=True),
    )
    for specification in cases:
        engine, _source, _decoder, _auditor, activator = loader(specification)
        result = engine.load(engine.begin_load(), specification)
        assert result.status == "rejected"
        assert result.active_atlas.pack_id == "builtin-three-view"
        assert result.active_atlas.legacy_fallback
        assert not result.active_atlas.complete_360
        assert activator.calls == []


def assert_v4_full_body_evidence_fails_closed() -> None:
    base = manifest()
    cases = (
        replace(base, rig_id="unknown-rig"),
        replace(base, rig_version_range=(2, 3)),
        replace(base, body_profile_id="another-body"),
        replace(base, body_profile_version_range=(2, 3)),
        replace(
            base,
            views=(
                replace(base.views[0], correction_layers=frozenset()),
                *base.views[1:],
            ),
        ),
        replace(
            base,
            views=(
                replace(base.views[0], rig_id="unknown-rig"),
                *base.views[1:],
            ),
        ),
    )
    for specification in cases:
        engine, _source, _decoder, _auditor, activator = loader(specification)
        result = engine.load(engine.begin_load(), specification)
        assert result.status == "rejected"
        assert result.active_atlas.legacy_fallback
        assert activator.calls == []


def assert_legacy_v3_loads_only_as_explicit_fallback() -> None:
    source_spec = manifest()
    views = tuple(
        replace(
            view,
            rig_id=None,
            rig_version_range=None,
            correction_layers=frozenset(),
        )
        for view in source_spec.views
        if view.yaw_degrees in {-30, 0, 30}
    )
    legacy = PoseAtlasManifest(
        "legacy-external",
        source_spec.source_evidence,
        views,
        contract="legacy-v3",
        schema_version=1,
        body_profile_id="mohan-body-v1",
        body_profile_version_range=(1, 2),
        rig_id=None,
        rig_version_range=None,
    )
    engine, _source, _decoder, _auditor, _activator = loader(legacy)
    result = engine.load(engine.begin_load(), legacy)
    assert result.status == "activated"
    assert result.active_atlas.legacy_fallback
    assert not result.active_atlas.complete_360
    assert not result.active_atlas.full_body
    assert tuple(yaw for yaw, _image in result.active_atlas.views) == (-30, 0, 30)

    lying_legacy = replace(
        legacy,
        views=(
            replace(
                legacy.views[0],
                rig_id="mohan-full-body-v1",
                rig_version_range=(1, 2),
                correction_layers=frozenset({"left-leg-correction"}),
            ),
            *legacy.views[1:],
        ),
    )
    engine, _source, _decoder, _auditor, activator = loader(lying_legacy)
    rejected = engine.load(engine.begin_load(), lying_legacy)
    assert rejected.status == "rejected"
    assert "legacy_claims_full_body" in rejected.problems
    assert activator.calls == []


def assert_bad_image_hand_failure_and_asset_change_roll_back() -> None:
    specification = manifest()
    engine, source, _decoder, auditor, activator = loader(specification)
    source.data[specification.views[0].path] = encoded(-180, invalid=True)
    assert engine.load(engine.begin_load(), specification).status == "rejected"
    source.data[specification.views[0].path] = encoded(-180)
    auditor.passed = False
    auditor.problems = ("hand_audit_failed",)
    result = engine.load(engine.begin_load(), specification)
    assert result.status == "rejected"
    assert "hand_audit_failed" in result.problems
    auditor.passed = True
    source.change_after_reads = source.reads + 12
    result = engine.load(engine.begin_load(), specification)
    assert result.status == "rejected"
    assert "source_changed" in result.problems
    assert activator.calls == []


def assert_activation_failure_restores_previous() -> None:
    specification = manifest()
    engine, _source, _decoder, _auditor, activator = loader(specification)
    activator.fail = True
    try:
        engine.load(engine.begin_load(), specification)
    except RuntimeError as exc:
        assert str(exc) == "activation failed"
    else:
        raise AssertionError("activation failure must remain visible")
    assert engine.active_atlas.pack_id == "builtin-three-view"
    assert activator.calls[-1] == engine.active_atlas


def assert_parallel_stale_and_cancelled_loads_never_switch() -> None:
    specification = manifest()
    engine, _source, decoder, _auditor, activator = loader(specification)
    decoder.block = True
    old_generation = engine.begin_load()
    holder: list[object] = []
    worker = threading.Thread(
        target=lambda: holder.append(engine.load(old_generation, specification))
    )
    worker.start()
    assert decoder.entered.wait(timeout=1.0)
    new_generation = engine.begin_load()
    decoder.block = False
    decoder.release.set()
    worker.join(timeout=2.0)
    assert not worker.is_alive()
    assert holder[0].status == "stale"
    assert activator.calls == []
    engine.cancel(new_generation)
    result = engine.load(new_generation, specification)
    assert result.status == "cancelled"
    assert engine.active_atlas.pack_id == "builtin-three-view"


def assert_resource_limits_fail_closed() -> None:
    specification = manifest()
    tiny_limits = PoseRuntimeLimits(
        max_asset_bytes=8,
        max_total_bytes=64,
        max_width=WIDTH,
        max_height=HEIGHT,
    )
    _engine, source, decoder, auditor, activator = loader(specification)
    limited = PoseRuntimeLoader(
        legacy_atlas(), source, decoder, auditor, activator, tiny_limits
    )
    result = limited.load(limited.begin_load(), specification)
    assert result.status == "rejected"
    assert "asset_size_limit" in result.problems
    assert limited.active_atlas.pack_id == "builtin-three-view"


def run() -> None:
    assert_complete_atlas_activates_atomically()
    assert_invalid_inputs_keep_legacy()
    assert_v4_full_body_evidence_fails_closed()
    assert_legacy_v3_loads_only_as_explicit_fallback()
    assert_bad_image_hand_failure_and_asset_change_roll_back()
    assert_activation_failure_restores_previous()
    assert_parallel_stale_and_cancelled_loads_never_switch()
    assert_resource_limits_fail_closed()
    print("POSE_RUNTIME_LOADER_OK")


if __name__ == "__main__":
    run()
