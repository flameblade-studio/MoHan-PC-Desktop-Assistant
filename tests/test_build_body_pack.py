"""Contracts for deterministic body-pack face transplantation and file output."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy from pathlib import Path

lazy import pytest
lazy from PIL import Image

lazy from tools import build_body_pack as builder
lazy from tools import verify_body_pack_build as verifier


GESTURE_POSES = ("front-eureka", "front-mock-scold", "front-mock-hit")


def test_transplant_face_core_uses_feather_alpha_and_covers_face_features() -> None:
    base = Image.new("RGBA", (6, 3), (10, 20, 30, 255))
    source = Image.new("RGBA", (6, 3), (210, 220, 230, 255))
    mask = Image.new("RGBA", (6, 3), (0, 0, 0, 0))

    left_eye = (1, 0)
    right_eye = (4, 0)
    mouth = (2, 2)
    source.putpixel(left_eye, (240, 80, 90, 255))
    source.putpixel(right_eye, (70, 180, 100, 255))
    source.putpixel(mouth, (130, 40, 200, 255))
    for point in (left_eye, right_eye, mouth):
        mask.putpixel(point, (0, 0, 0, 255))

    feathered_edge = (2, 0)
    mask.putpixel(feathered_edge, (0, 0, 0, 128))
    outside = (0, 1)
    transparent_outside = (5, 2)
    base.putpixel(transparent_outside, (90, 80, 70, 0))

    result = builder.transplant_face_core(base, source, mask)

    assert result.mode == "RGBA"
    assert result.getpixel(left_eye) == source.getpixel(left_eye)
    assert result.getpixel(right_eye) == source.getpixel(right_eye)
    assert result.getpixel(mouth) == source.getpixel(mouth)
    assert result.getpixel(feathered_edge) == (110, 120, 130, 255)
    assert result.getpixel(outside) == base.getpixel(outside)
    assert result.getpixel(transparent_outside) == (0, 0, 0, 0)


@pytest.mark.parametrize("bad_image", ["base", "source", "mask"])
def test_transplant_face_core_rejects_non_rgba_inputs(bad_image: str) -> None:
    images = [Image.new("RGBA", (2, 2), (1, 2, 3, 255)) for _ in range(3)]
    images[("base", "source", "mask").index(bad_image)] = Image.new(
        "RGB", (2, 2), (1, 2, 3)
    )

    with pytest.raises(ValueError, match="RGBA"):
        builder.transplant_face_core(*images)


@pytest.mark.parametrize("mismatched_image", ["base", "source", "mask"])
def test_transplant_face_core_rejects_different_canvas_sizes(
    mismatched_image: str,
) -> None:
    sizes = {
        image_name: (3, 2) if image_name == mismatched_image else (2, 2)
        for image_name in ("base", "source", "mask")
    }
    base, source, mask = (
        Image.new("RGBA", sizes["base"], (0, 0, 0, 255)),
        Image.new("RGBA", sizes["source"], (0, 0, 0, 255)),
        Image.new("RGBA", sizes["mask"], (0, 0, 0, 255)),
    )

    with pytest.raises(ValueError, match="shared canvas"):
        builder.transplant_face_core(base, source, mask)


def test_write_frame_is_reproducible_and_discards_input_metadata(
    tmp_path: Path,
) -> None:
    relative = "views/front/frame.png"
    outputs = []
    records = []

    for index, profile in enumerate((b"profile-one", b"profile-two")):
        image = Image.new("RGBA", (2, 2), (12, 34, 56, 255))
        image.info["icc_profile"] = profile
        image.info["dpi"] = (72 + index, 72 + index)
        image.info["Description"] = f"source {index}"
        root = tmp_path / f"output-{index}"
        record = builder.write_frame(root, relative, image)
        outputs.append((root / relative).read_bytes())
        records.append(record)

    assert outputs[0] == outputs[1]
    assert records[0] == records[1]
    assert records[0]["path"] == relative
    assert records[0]["sha256"] == hashlib.sha256(outputs[0]).hexdigest()
    with Image.open(tmp_path / "output-0" / relative) as saved:
        assert saved.mode == "RGBA"
        assert saved.info == {}


def test_write_json_is_sorted_utf8_and_uses_lf(tmp_path: Path) -> None:
    first = tmp_path / "first" / "manifest.json"
    second = tmp_path / "second" / "manifest.json"
    first_value: dict[str, object] = {"z": 1, "\u540d\u7a31": "\u58a8\u5bd2", "a": {"b": 2}}
    reordered_value: dict[str, object] = {
        "a": {"b": 2},
        "z": 1,
        "\u540d\u7a31": "\u58a8\u5bd2",
    }

    assert builder.write_json(first, first_value) is None
    builder.write_json(second, reordered_value)

    expected = (
        json.dumps(first_value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    payload = first.read_bytes()
    assert payload == expected
    assert second.read_bytes() == payload
    assert b"\r" not in payload
    assert payload.endswith(b"\n")
    assert "\u58a8\u5bd2".encode("utf-8") in payload


def test_body_pack_fingerprint_includes_face_core_mask_bindings() -> None:
    bindings: dict[str, object] = {
        "full_body": {
            "front": {"rest": {"path": "full/front.png", "sha256": "a" * 64}},
        },
        "half_body": {
            "front": {"rest": {"path": "half/front.png", "sha256": "b" * 64}},
        },
    }
    without_mask = builder.compute_body_pack_fingerprint(bindings)
    with_mask = {
        **bindings,
        "face_core_masks": {
            "front": {"path": "masks/front.png", "sha256": "c" * 64},
        },
    }
    changed_mask = {
        **bindings,
        "face_core_masks": {
            "front": {"path": "masks/front.png", "sha256": "d" * 64},
        },
    }

    assert builder.compute_body_pack_fingerprint(with_mask) != without_mask
    assert builder.compute_body_pack_fingerprint(changed_mask) != (
        builder.compute_body_pack_fingerprint(with_mask)
    )


@pytest.mark.parametrize(
    ("pose", "expected"),
    [
        ("front-crossed", "front-crossed"),
        ("left-neutral", "left-neutral"),
        ("cheek-rest", "cheek-rest"),
        ("exasperated", "exasperated"),
        ("front-exasperated", "exasperated"),
        ("cheek-smile", "cheek-rest"),
        ("front-happy", "front-crossed"),
    ],
)
def test_half_base_preserves_or_aliases_reviewed_silhouettes(
    pose: str,
    expected: str,
) -> None:
    assert builder.half_base(pose) == expected


@pytest.mark.parametrize(
    "pose",
    GESTURE_POSES,
)
def test_half_base_leaves_three_gestures_without_body_silhouettes(
    pose: str,
) -> None:
    assert builder.half_base(pose) is None


def test_half_base_returns_none_for_unknown_pose() -> None:
    assert builder.half_base("unreviewed-pose") is None


HALF_ALPHA = 128
FULL_ALPHA = 255
ZERO_ALPHA = 0
HALF_BODY_STATE_COUNT = 12


def _write_body_pack_fixture_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.write_bytes(payload.encode("utf-8"))


def _write_body_pack_fixture_image(
    path: Path,
    color: tuple[int, int, int, int],
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (2, 2), color)
    image.save(path, format="PNG")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_body_pack_fixture_core_mask(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
    image.putpixel((0, 0), (255, 255, 255, FULL_ALPHA))
    image.putpixel((1, 0), (255, 255, 255, HALF_ALPHA))
    image.save(path, format="PNG")


def _write_half_body_fixture_frames(
    root: Path,
    pose: str,
    pose_index: int,
) -> dict[str, dict[str, dict[str, str]]]:
    families = ("neutral", "small", "a", "o")
    eyes = ("rest", "half", "closed")
    frames: dict[str, dict[str, dict[str, str]]] = {}
    for family_index, family in enumerate(families):
        frames[family] = {}
        for eye_index, eye in enumerate(eyes):
            relative = f"frames/{pose}-{family}-{eye}.rgba.png"
            color = (40 + pose_index, 60 + family_index * 10, 80 + eye_index * 20, 255)
            digest = _write_body_pack_fixture_image(root / relative, color)
            frames[family][eye] = {"path": relative, "sha256": digest}
    return frames


def _make_body_pack_fixture_inputs(
    root: Path,
) -> tuple[Path, Path, Path, str]:
    product_root = root / "product"
    bald_root = root / "bald"
    layers_root = root / "layers"
    view = "yaw+000-pitch+00"
    half_bases = ("front-crossed", "left-neutral", "cheek-rest", "exasperated")

    bald_views = []
    for index, source_view in enumerate((view, *half_bases)):
        relative = Path(source_view) / "bald-natural.png"
        digest = _write_body_pack_fixture_image(
            bald_root / relative,
            (20 + index, 30 + index, 40 + index, FULL_ALPHA),
        )
        bald_views.append({"view": source_view, "sha256": digest})
    _write_body_pack_fixture_json(bald_root / "manifest.json", {"views": bald_views})

    atlas_root = product_root / "assets" / "pose-atlas" / builder.POSE_ATLAS_ROOT_NAME
    _write_body_pack_fixture_image(
        atlas_root / f"{view}.png",
        (220, 10, 20, FULL_ALPHA),
    )
    layered_root = (
        product_root
        / "assets"
        / "pose-atlas"
        / builder.POSE_ATLAS_LAYERED_ROOT_NAME
    )
    _write_body_pack_fixture_json(
        layered_root / "complete_expression_manifest.json",
        {"views": {}},
    )

    half_root = product_root / "assets" / "expressions" / "complete-expressions"
    poses: dict[str, object] = {}
    authored_poses = ("front-crossed", "left-neutral", "front-exasperated")
    for index, pose in enumerate(authored_poses):
        poses[pose] = {"frames": _write_half_body_fixture_frames(half_root, pose, index)}
    poses.update({pose: {} for pose in GESTURE_POSES})
    _write_half_body_fixture_frames(half_root, "cheek-rest", len(authored_poses))
    _write_body_pack_fixture_json(
        half_root / "manifest.json",
        {
            "poses": poses,
            "expressions": {"proud_front": {"pose": "front-crossed"}},
        },
    )

    layer_views = [
        (view, "lk-hair-F1"),
        *((pose, "lk-hair-H") for pose in half_bases),
    ]
    for source_view, partition in layer_views:
        source = layers_root / partition / "round9" / source_view
        _write_body_pack_fixture_json(
            source / "manifest.json",
            {
                "face_core_precleared": False,
                "z_order": [
                    "hair-back",
                    "base-with-H",
                    "body-fix",
                    "garment",
                    "hair-front",
                ],
            },
        )
        for index, kind in enumerate(builder.LAYER_KINDS):
            _write_body_pack_fixture_image(
                source / f"{kind}.png",
                (90 + index, 100 + index, 110 + index, FULL_ALPHA),
            )
        _write_body_pack_fixture_image(
            source / "base-hide-mask.png",
            (0, 0, 0, 64),
        )
        _write_body_pack_fixture_core_mask(source / "face-core-mask.png")

    return product_root, bald_root, layers_root, view


def _write_gesture_fixture_inputs(
    product_root: Path,
    layers_root: Path,
) -> dict[str, tuple[int, int, int, int]]:
    half_root = product_root / "assets" / "expressions" / "complete-expressions"
    manifest_path = half_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bald_colors = {}

    for index, pose in enumerate(GESTURE_POSES):
        manifest["poses"][pose] = {
            "frames": _write_half_body_fixture_frames(half_root, pose, index + 10)
        }
        source = layers_root / "gestures3" / pose
        bald_color = (70 + index, 80 + index, 90 + index, FULL_ALPHA)
        bald_colors[pose] = bald_color
        for name, color in (
            ("bald-natural.png", bald_color),
            ("bald-blink-half.png", (100 + index, 110, 120, FULL_ALPHA)),
            ("bald-blink-closed.png", (130 + index, 140, 150, FULL_ALPHA)),
            ("A.png", bald_color),
        ):
            _write_body_pack_fixture_image(source / name, color)
        _write_body_pack_fixture_core_mask(source / "face-core-mask.png")
        _write_body_pack_fixture_core_mask(source / "F-core.png")

        hair = Image.new("RGBA", (2, 2), (255, 255, 255, FULL_ALPHA))
        hair.save(source / "hair-owned-mask.png", format="PNG")
        transparent = Image.new("RGBA", (2, 2), (255, 255, 255, ZERO_ALPHA))
        transparent.save(source / "skin-owned-mask.png", format="PNG")
        transparent.save(source / "garment-owned-mask.png", format="PNG")

    _write_body_pack_fixture_json(manifest_path, manifest)
    return bald_colors


def _body_pack_tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _assert_body_pack_assembly(output: Path, view: str) -> None:
    pack_root = output / "mohan-body-v2"
    body_manifest = json.loads(
        (pack_root / "manifest.json").read_text(encoding="utf-8")
    )
    assert body_manifest["fingerprint"] == (
        builder.compute_body_pack_fingerprint(body_manifest)
    )
    full_rest = body_manifest["full_body"][view]["rest"]
    with Image.open(pack_root / full_rest["path"]) as full_image:
        assert full_image.getpixel((0, 0)) == (220, 10, 20, FULL_ALPHA)
        assert full_image.getpixel((1, 1)) == (180, 14, 24, FULL_ALPHA)

    full_core = body_manifest["face_core_masks"][view]
    with Image.open(pack_root / full_core["path"]) as mask:
        assert mask.getpixel((0, 0))[3] == FULL_ALPHA
        assert mask.getpixel((1, 0))[3] == FULL_ALPHA
        one_pixel_feather_alpha = round(FULL_ALPHA * 4 / 5)
        assert mask.getpixel((1, 1))[3] == one_pixel_feather_alpha

    front_crossed = body_manifest["half_body"]["front-crossed"]
    proud_front = body_manifest["half_body"]["proud_front"]
    assert len(front_crossed) == HALF_BODY_STATE_COUNT
    assert proud_front == front_crossed
    assert {
        record["path"] for record in proud_front.values()
    } == {
        record["path"] for record in front_crossed.values()
    }
    assert not (pack_root / "half-body" / "proud_front").exists()

    cheek_rest = body_manifest["half_body"]["cheek-rest"]
    assert len(cheek_rest) == HALF_BODY_STATE_COUNT
    crossed_rest = front_crossed["neutral-rest"]
    with Image.open(pack_root / crossed_rest["path"]) as half_image:
        assert half_image.getpixel((0, 0)) == (40, 60, 80, FULL_ALPHA)
        assert half_image.getpixel((1, 1)) == (40, 60, 80, FULL_ALPHA)

    inventory = json.loads(
        (output / "inventory.json").read_text(encoding="utf-8")
    )
    assert inventory["missing_body_poses"] == sorted(GESTURE_POSES)
    for pose in GESTURE_POSES:
        assert pose not in body_manifest["half_body"]
        assert not (pack_root / "half-body" / pose).exists()
        assert inventory["half_body"][pose]["status"] == "missing_body_pose"

    character_manifest = json.loads(
        (output / "lin-keyun-layers" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    plan = character_manifest["layer_views"][view]
    assert plan["order"] == [
        "hair-back",
        "base",
        "body-fix",
        "garment",
        "hair-front",
    ]
    assert [layer["kind"] for layer in plan["layers"]] == list(builder.LAYER_KINDS)


def test_build_body_pack_assembles_small_synthetic_sources_deterministically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builder, "FULL_VIEW_COUNT", 1)
    product_root, bald_root, layers_root, view = _make_body_pack_fixture_inputs(
        tmp_path / "inputs"
    )
    first_output = tmp_path / "first-output"
    second_output = tmp_path / "second-output"

    first_stats = builder.build_body_pack(
        product_root,
        bald_root,
        layers_root,
        first_output,
        "Synthetic fixture license",
    )
    second_stats = builder.build_body_pack(
        product_root,
        bald_root,
        layers_root,
        second_output,
        "Synthetic fixture license",
    )

    assert first_stats == second_stats
    first_files = _body_pack_tree_bytes(first_output)
    assert first_files == _body_pack_tree_bytes(second_output)
    assert "build-receipt.json" in first_files
    _assert_body_pack_assembly(first_output, view)


def test_complete_gesture_sources_build_independent_approved_body_poses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builder, "FULL_VIEW_COUNT", 1)
    product_root, bald_root, layers_root, _view = _make_body_pack_fixture_inputs(
        tmp_path / "inputs"
    )
    bald_colors = _write_gesture_fixture_inputs(product_root, layers_root)
    output = tmp_path / "gesture-output"

    stats = builder.build_body_pack(
        product_root,
        bald_root,
        layers_root,
        output,
        "Synthetic fixture license",
    )

    pack_root = output / "mohan-body-v2"
    body_manifest = json.loads(
        (pack_root / "manifest.json").read_text(encoding="utf-8")
    )
    inventory = json.loads(
        (output / "inventory.json").read_text(encoding="utf-8")
    )
    receipt = json.loads(
        (output / "build-receipt.json").read_text(encoding="utf-8")
    )
    character_manifest = json.loads(
        (output / "lin-keyun-layers" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt == stats
    assert set(character_manifest) == {"body_pack", "layer_views"}
    assert stats["missing_body_poses"] == []
    assert stats["pending_appearance_approval"] == []
    assert stats["approved_gestures"] == sorted(GESTURE_POSES)
    assert inventory["missing_body_poses"] == []
    assert not (set(GESTURE_POSES) & set(body_manifest["missing_body_poses"]))
    frame_paths = set()
    for pose in GESTURE_POSES:
        assert inventory["half_body"][pose]["status"] == "built"
        assert inventory["half_body"][pose]["body_pose"] == pose
        assert inventory["half_body"][pose]["appearance_accepted"] is True
        states = body_manifest["half_body"][pose]
        assert len(states) == HALF_BODY_STATE_COUNT
        frame_paths.add(states["neutral-rest"]["path"])
        with Image.open(pack_root / states["neutral-rest"]["path"]) as frame:
            source_root = product_root / "assets/expressions/complete-expressions"
            source_manifest = json.loads((source_root / "manifest.json").read_text(encoding="utf-8"))
            source_record = source_manifest["poses"][pose]["frames"]["neutral"]["rest"]
            with Image.open(source_root / source_record["path"]) as source_frame:
                assert frame.getpixel((1, 1)) == source_frame.getpixel((1, 1))
        with Image.open(layers_root / "gestures3" / pose / "bald-natural.png") as bald_frame:
            assert bald_frame.getpixel((1, 1)) == bald_colors[pose]

        gesture_manifest = json.loads(
            (
                output
                / "lin-keyun-layers"
                / "recomputed"
                / pose
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        assert gesture_manifest["appearance_accepted"] is True
        provenance = json.loads(
            (
                output
                / "lin-keyun-layers"
                / "recomputed"
                / pose
                / "builder-provenance.json"
            ).read_text(encoding="utf-8")
        )
        assert provenance["appearance_accepted"] is True

    assert len(frame_paths) == len(GESTURE_POSES)


def test_incomplete_gesture_sources_reject_the_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builder, "FULL_VIEW_COUNT", 1)
    product_root, bald_root, layers_root, _view = _make_body_pack_fixture_inputs(
        tmp_path / "inputs"
    )
    _write_gesture_fixture_inputs(product_root, layers_root)
    missing_source = (
        layers_root / "gestures3" / GESTURE_POSES[0] / "F-core.png"
    )
    missing_source.unlink()

    with pytest.raises(ValueError, match="Missing gesture input"):
        builder.build_body_pack(
            product_root,
            bald_root,
            layers_root,
            tmp_path / "incomplete-output",
            "Synthetic fixture license",
        )


def _create_directory_symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as error:
        if os.name == "nt" and getattr(error, "winerror", None) in {5, 1314}:
            pytest.skip("Windows denied symbolic-link creation for this account.")
        raise


def test_write_helpers_reject_symlinked_pack_root_without_touching_target(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    pack_link = output_dir / "mohan-body-v2"
    _create_directory_symlink_or_skip(pack_link, source_dir)
    image = Image.new("RGBA", (2, 2), (1, 2, 3, 255))

    with pytest.raises(ValueError, match="Output paths"):
        builder.write_frame(pack_link, "frames/front.png", image)
    with pytest.raises(ValueError, match="Output paths"):
        builder.write_json(pack_link / "manifest.json", {"id": "mohan-body-v2"})

    assert list(source_dir.iterdir()) == []


def test_head_roi_expands_the_static_alpha_bounds_with_ceil_margins() -> None:
    mask = Image.new("RGBA", (40, 30), (255, 255, 255, ZERO_ALPHA))
    mask.putpixel((10, 8), (255, 255, 255, HALF_ALPHA))
    mask.putpixel((18, 17), (255, 255, 255, FULL_ALPHA))
    assert builder.head_roi(mask) == (6, 4, 23, 21)

    edge_mask = Image.new("RGBA", (40, 30), (255, 255, 255, ZERO_ALPHA))
    edge_mask.putpixel((0, 0), (255, 255, 255, FULL_ALPHA))
    edge_mask.putpixel((2, 2), (255, 255, 255, FULL_ALPHA))
    assert builder.head_roi(edge_mask) == (0, 0, 5, 4)


def test_dynamic_core_limits_opened_motion_before_feathering_the_union() -> None:
    rest = Image.new("RGBA", (64, 64), (50, 60, 70, FULL_ALPHA))
    static = Image.new("RGBA", rest.size, (255, 255, 255, ZERO_ALPHA))
    static.paste((255, 255, 255, FULL_ALPHA), (20, 20, 40, 40))
    static.putpixel((19, 30), (255, 255, 255, 127))
    state = rest.copy()
    # Accepted motion within six pixels, with a soft transition outside U.
    state.paste((59, 60, 70, FULL_ALPHA), (42, 25, 45, 28))
    # This opened patch straddles the six-pixel limit: x=45 is retained, x=46 is not.
    state.paste((59, 60, 70, FULL_ALPHA), (45, 32, 48, 35))
    # Below-threshold RGB, isolated noise and distant ROI motion are excluded.
    state.paste((58, 60, 70, FULL_ALPHA), (22, 42, 25, 45))
    state.putpixel((30, 44), (200, 210, 220, FULL_ALPHA))
    state.paste((59, 60, 70, FULL_ALPHA), (49, 25, 52, 28))
    state.paste((200, 210, 220, FULL_ALPHA), (3, 3, 6, 6))
    # Differences from separate states form one 3x3 component before opening.
    upper, lower = rest.copy(), rest.copy()
    upper.paste((50, 60, 70, 240), (42, 36, 45, 38))
    lower.paste((50, 60, 70, 240), (42, 38, 45, 39))

    core = builder.dynamic_face_core(static, rest, [state, upper, lower])
    assert core.getpixel((30, 30))[3] == FULL_ALPHA
    assert core.getpixel((43, 26))[3] == FULL_ALPHA
    assert core.getpixel((45, 33))[3] == FULL_ALPHA
    assert 0 < core.getpixel((46, 33))[3] < FULL_ALPHA
    assert core.getpixel((43, 37))[3] == FULL_ALPHA
    assert 0 < core.getpixel((18, 30))[3] < FULL_ALPHA
    assert core.getpixel((50, 26))[3] == ZERO_ALPHA
    assert core.getpixel((23, 44))[3] < FULL_ALPHA
    assert core.getpixel((30, 44))[3] < FULL_ALPHA
    assert core.getpixel((4, 4))[3] == ZERO_ALPHA


def test_dynamic_core_ignores_invisible_rgb_and_keeps_empty_core_empty() -> None:
    rest = Image.new("RGBA", (32, 32), (10, 20, 30, ZERO_ALPHA))
    static = Image.new("RGBA", rest.size, (255, 255, 255, ZERO_ALPHA))
    static.paste((255, 255, 255, FULL_ALPHA), (12, 12, 20, 20))
    moved = rest.copy()
    moved.paste((200, 210, 220, ZERO_ALPHA), (20, 14, 23, 17))
    core = builder.dynamic_face_core(static, rest, [moved], feather_radius=4)
    assert core.getpixel((21, 15))[3] < FULL_ALPHA
    assert core.getpixel((23, 15))[3] == ZERO_ALPHA
    empty = Image.new("RGBA", rest.size, (255, 255, 255, ZERO_ALPHA))
    assert builder.dynamic_face_core(empty, rest, [moved]).getchannel("A").getbbox() is None


def test_dynamic_core_feathers_motion_on_every_edge_with_static_radius() -> None:
    rest = Image.new("RGBA", (48, 48), (10, 20, 30, FULL_ALPHA))
    static = Image.new("RGBA", rest.size, (255, 255, 255, ZERO_ALPHA))
    static.paste((255, 255, 255, FULL_ALPHA), (15, 15, 25, 25))
    moved = rest.copy()
    moved.paste((30, 40, 50, FULL_ALPHA), (27, 18, 30, 21))
    core = builder.dynamic_face_core(static, rest, [moved], feather_radius=4)
    assert core.getpixel((28, 19))[3] == FULL_ALPHA
    one_pixel_feather_alpha = round(FULL_ALPHA * 3 / 4)
    assert core.getpixel((30, 19))[3] == one_pixel_feather_alpha
    assert core.getpixel((28, 17))[3] == one_pixel_feather_alpha
    assert core.getpixel((28, 21))[3] == one_pixel_feather_alpha
    assert core.getpixel((33, 19))[3] == ZERO_ALPHA


def test_recomputed_layer_reuse_rejects_a_different_bald_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builder, "FULL_VIEW_COUNT", 1)
    product, bald, layers, view = _make_body_pack_fixture_inputs(tmp_path / "inputs")
    output = tmp_path / "output"
    builder.write_json(output / "lin-keyun-layers/recomputed" / view / "builder-provenance.json",
                       {"bald_sha256": "0" * 64, "face_core_precleared": False})
    build = builder._Builder(product, bald, layers, output, "Fixture license", "all", "reuse")
    with pytest.raises(ValueError, match="different bald body"):
        build.layer_source(view)


@pytest.mark.parametrize("delta,expected", [(0, True), (1, True), (2, False)])
def test_formula_feather_acceptance_enforces_one_level_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, delta: int, expected: bool,
) -> None:
    core = Image.new("RGBA", (3, 1), (255, 255, 255, 0))
    core.putpixel((1, 0), (255, 255, 255, 128))
    core.putpixel((2, 0), (255, 255, 255, 255))
    protected = verifier.np.tile(
        verifier.np.array([[[0, 0, 255, 255]]], dtype=verifier.np.uint8), (1, 3, 1),
    )
    character = verifier.np.tile(
        verifier.np.array([[[255, 0, 0, 255]]], dtype=verifier.np.uint8), (1, 3, 1),
    )
    rendered = Image.new("RGBA", (3, 1), (0, 0, 255, 255))
    rendered.putpixel((1, 0), (127 + delta, 0, 128, 255))
    monkeypatch.setattr(verifier, "_read_source", lambda _path: core)
    monkeypatch.setattr(
        verifier, "_formula_endpoints",
        lambda _context, _case: (protected, character, "rest"),
    )
    case = verifier.ComparisonRequest(
        "tiny-feather", "tiny", Path("A.png"), rendered, rendered,
        verifier.CoreEvidence(
            verifier.np.asarray(core)[..., 3] > 0, Path("core.png"), "synthetic",
        ), "full",
    )
    context = verifier.VerificationContext(
        tmp_path, tmp_path, tmp_path, tmp_path, tmp_path, None, {}, None,
    )

    feather, opaque = verifier._formula_acceptance(context, case)
    metrics = feather["metrics"]["premultiplied_rgb"]
    assert feather["passed"] is expected
    assert feather["requires_visual_review"] is True
    assert metrics["compared_pixels"] == 1
    assert metrics["max_abs_channel_delta"] == delta
    assert opaque["passed"] is True


def test_unweighted_partition_retains_face_pixels_and_repaints_hidden_soft_alpha(tmp_path: Path) -> None:
    base = builder.np.array(Image.new("RGBA", (3, 1), (10, 20, 30, 255)))
    approved = base.copy()
    approved[0, 0] = [200, 90, 80, 255]
    approved[0, 1] = [80, 60, 40, 128]
    base[0, 1] = approved[0, 1]
    owners = {"hair-front": builder.np.array([[True, True, False]]),
              "body-fix": builder.np.array([[False, False, True]])}
    builder._write_unweighted_layers(tmp_path, base, approved, owners)
    with Image.open(tmp_path / "hair-front.png") as layer:
        assert layer.getpixel((0, 0)) == (200, 90, 80, 255)
        assert layer.getpixel((1, 0)) == (80, 60, 40, 128)
        assert layer.getpixel((2, 0)) == (0, 0, 0, 0)
    with Image.open(tmp_path / "base-hide-mask.png") as hide:
        assert [hide.getpixel((x, 0))[3] for x in range(3)] == [0, 255, 0]
    with Image.open(tmp_path / "composite.png") as composite:
        assert builder.np.array_equal(builder.np.asarray(composite), approved)


@pytest.mark.parametrize("delta,expected", [(0, True), (1, True), (2, False)])
def test_opaque_core_formula_acceptance_uses_body_plus_makeup_endpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, delta: int, expected: bool,
) -> None:
    core = Image.new("RGBA", (3, 1), (255, 255, 255, 0))
    core.putpixel((2, 0), (255, 255, 255, 255))
    protected = verifier.np.tile(
        verifier.np.array([[[0, 0, 255, 255]]], dtype=verifier.np.uint8), (1, 3, 1),
    )
    protected[0, 2] = [128, 0, 127, 255]
    character = verifier.np.tile(
        verifier.np.array([[[255, 0, 0, 255]]], dtype=verifier.np.uint8), (1, 3, 1),
    )
    rendered = Image.new("RGBA", (3, 1), (0, 0, 255, 255))
    rendered.putpixel((2, 0), (128 + delta, 0, 127, 255))
    monkeypatch.setattr(verifier, "_read_source", lambda _path: core)
    monkeypatch.setattr(
        verifier, "_formula_endpoints",
        lambda _context, _case: (protected, character, "rest"),
    )
    case = verifier.ComparisonRequest(
        "tiny-opaque", "tiny", Path("A.png"), rendered, rendered,
        verifier.CoreEvidence(
            verifier.np.asarray(core)[..., 3] > 0, Path("core.png"), "synthetic",
        ), "full",
    )
    context = verifier.VerificationContext(
        tmp_path, tmp_path, tmp_path, tmp_path, tmp_path, None, {}, None,
    )

    _feather, opaque = verifier._formula_acceptance(context, case)
    metrics = opaque["metrics"]["premultiplied_rgb"]
    assert opaque["reference"] == "selected-body-plus-SourceAtop-makeup"
    assert opaque["passed"] is expected
    assert metrics["compared_pixels"] == 1
    assert metrics["max_abs_channel_delta"] == delta


@pytest.mark.parametrize("precleared", [True, None])
def test_reuse_rejects_layers_without_explicit_native_alpha_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, precleared: bool | None,
) -> None:
    monkeypatch.setattr(builder, "FULL_VIEW_COUNT", 1)
    product, bald, layers, view = _make_body_pack_fixture_inputs(tmp_path / "inputs")
    output = tmp_path / "output"
    builder.write_json(output / "lin-keyun-layers/recomputed" / view / "builder-provenance.json",
                       {"bald_sha256": "0" * 64, "face_core_precleared": precleared})
    build = builder._Builder(product, bald, layers, output, "Fixture license", "all", "reuse")
    with pytest.raises(ValueError, match="unweighted face-core contract"):
        build.layer_source(view)
