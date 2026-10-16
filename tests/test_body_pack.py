from __future__ import annotations

lazy import hashlib
lazy import json

lazy import pytest

lazy from domain.body_pack import (
    BodyPackError,
    BodyPackMismatchError,
    BodyPackReference,
    compute_body_pack_fingerprint,
    parse_body_pack,
    parse_body_pack_reference,
)


def _file(path: str, digest: str) -> dict[str, str]:
    return {"path": path, "sha256": digest}


def _manifest() -> dict[str, object]:
    return {
        "schema": "mohan.body-pack.v1",
        "id": "mohan-body-test",
        "version": "1.0",
        "license": "CC BY-NC-ND 4.0",
        "full_body": {
            "yaw+000-pitch+00": _file("full/front.png", "a" * 64),
        },
        "half_body": {
            "front": {
                "rest": _file("half/front-rest.png", "b" * 64),
                "pose-a": {
                    "small": {
                        "closed": _file("half/front-pose-a-small-closed.png", "c" * 64),
                    },
                },
            },
        },
        "face_core_masks": {
            "front": _file("masks/front-face-core.png", "d" * 64),
        },
    }


def _with_fingerprint(manifest: dict[str, object]) -> dict[str, object]:
    manifest["fingerprint"] = compute_body_pack_fingerprint(manifest)
    return manifest


def test_parse_body_pack_preserves_views_states_and_optional_masks() -> None:
    parsed = parse_body_pack(_with_fingerprint(_manifest()))

    assert parsed.schema == "mohan.body-pack.v1"
    assert parsed.id == "mohan-body-test"
    assert parsed.version == "1.0"
    assert parsed.full_body[0].view_id == "yaw+000-pitch+00"
    assert tuple(key for key, _ in parsed.full_body[0].frames) == ("rest",)
    assert parsed.full_body[0].frames[0][1].path == "full/front.png"
    assert tuple(key for key, _ in parsed.half_body[0].frames) == (
        "rest",
        "pose-a/small/closed",
    )
    assert parsed.half_body[0].frames[1][1].path == (
        "half/front-pose-a-small-closed.png"
    )
    assert parsed.face_core_masks[0][0] == "front"


def test_parse_body_pack_accepts_matching_reference() -> None:
    manifest = _with_fingerprint(_manifest())
    reference = {
        "id": manifest["id"],
        "version": manifest["version"],
        "fingerprint": manifest["fingerprint"],
    }

    assert parse_body_pack_reference(reference) == BodyPackReference(
        "mohan-body-test",
        "1.0",
        str(manifest["fingerprint"]),
    )
    assert parse_body_pack(manifest, reference).id == "mohan-body-test"


@pytest.mark.parametrize(
    ("reference", "code"),
    [
        ({"id": "other-pack", "version": "1.0", "fingerprint": "0" * 64}, "id_mismatch"),
        ({"id": "mohan-body-test", "version": "2.0", "fingerprint": "0" * 64}, "version_mismatch"),
        ({"id": "mohan-body-test", "version": "1.0", "fingerprint": "0" * 64}, "fingerprint_mismatch"),
    ],
)
def test_parse_body_pack_reports_reference_mismatch(
    reference: dict[str, str],
    code: str,
) -> None:
    manifest = _with_fingerprint(_manifest())

    with pytest.raises(BodyPackMismatchError) as error:
        parse_body_pack(manifest, reference)

    assert error.value.code == code
    assert error.value.path is None


def test_declared_fingerprint_must_match_distinct_files() -> None:
    manifest = _manifest()
    manifest["fingerprint"] = "0" * 64

    with pytest.raises(BodyPackMismatchError) as error:
        parse_body_pack(manifest)

    assert error.value.code == "fingerprint_mismatch"


def test_fingerprint_sorts_normalized_frame_bindings_and_includes_core_masks() -> None:
    manifest: dict[str, object] = {
        "full_body": {
            "front": _file("z.png", "a" * 64),
        },
        "half_body": {
            "front": {
                "rest": _file("a.png", "b" * 64),
                "closed": _file("a.png", "b" * 64),
            },
        },
        "face_core_masks": {
            "front": _file("z.png", "a" * 64),
            "side": _file("b.png", "a" * 64),
        },
    }
    records = [
        ("full_body", "front", "rest", "z.png", "a" * 64),
        ("half_body", "front", "rest", "a.png", "b" * 64),
        ("half_body", "front", "closed", "a.png", "b" * 64),
        ("face_core_masks", "front", "mask", "z.png", "a" * 64),
        ("face_core_masks", "side", "mask", "b.png", "a" * 64),
    ]
    expected = hashlib.sha256(
        json.dumps(sorted(records), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    assert compute_body_pack_fingerprint(manifest) == expected


def test_fingerprint_changes_when_view_or_state_bindings_change() -> None:
    manifest: dict[str, object] = {
        "full_body": {
            "front": _file("front.png", "a" * 64),
            "side": _file("side.png", "b" * 64),
        },
        "half_body": {
            "front": {
                "rest": _file("half-rest.png", "c" * 64),
                "blink": _file("half-blink.png", "d" * 64),
            },
        },
        "face_core_masks": {"front": _file("face.png", "e" * 64)},
    }
    original = compute_body_pack_fingerprint(manifest)
    reordered: dict[str, object] = {
        "full_body": {
            "side": _file("side.png", "b" * 64),
            "front": _file("front.png", "a" * 64),
        },
        "half_body": {
            "front": {
                "blink": _file("half-blink.png", "d" * 64),
                "rest": _file("half-rest.png", "c" * 64),
            },
        },
        "face_core_masks": {"front": _file("face.png", "e" * 64)},
    }
    assert compute_body_pack_fingerprint(reordered) == original

    swapped_views = dict(manifest)
    swapped_views["full_body"] = {
        "front": _file("side.png", "b" * 64),
        "side": _file("front.png", "a" * 64),
    }
    assert compute_body_pack_fingerprint(swapped_views) != original

    swapped_states = dict(manifest)
    swapped_states["half_body"] = {
        "front": {
            "rest": _file("half-blink.png", "d" * 64),
            "blink": _file("half-rest.png", "c" * 64),
        },
    }
    assert compute_body_pack_fingerprint(swapped_states) != original


def test_fingerprint_preserves_case_sensitive_view_and_state_ids() -> None:
    manifest = {
        "full_body": {"front": _file("front.png", "a" * 64)},
        "half_body": {"portrait": _file("half.png", "b" * 64)},
    }
    changed_case = {
        "full_body": {"Front": _file("front.png", "a" * 64)},
        "half_body": {"portrait": _file("half.png", "b" * 64)},
    }

    assert compute_body_pack_fingerprint(manifest) != compute_body_pack_fingerprint(changed_case)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../escape.png",
        "/absolute.png",
        "assets\\\\face.png",
        "C:/face.png",
        "assets//face.png",
        "assets/CON.png",
    ],
)
def test_unsafe_file_paths_are_rejected(unsafe_path: str) -> None:
    manifest = _manifest()
    manifest["full_body"] = {
        "front": _file(unsafe_path, "a" * 64),
    }

    with pytest.raises(BodyPackError):
        compute_body_pack_fingerprint(manifest)


def test_same_path_cannot_declare_two_hashes() -> None:
    manifest: dict[str, object] = {
        "full_body": {"front": _file("shared.png", "a" * 64)},
        "half_body": {"front": _file("shared.png", "b" * 64)},
    }

    with pytest.raises(BodyPackError, match="conflicting SHA-256"):
        compute_body_pack_fingerprint(manifest)


def test_face_core_masks_are_optional() -> None:
    manifest = _manifest()
    del manifest["face_core_masks"]
    parsed = parse_body_pack(_with_fingerprint(manifest))

    assert parsed.face_core_masks == ()


def test_missing_body_pose_metadata_preserves_frame_fingerprint() -> None:
    payload = _with_fingerprint(_manifest())
    payload["missing_body_poses"] = {"front-eureka": {"status": "missing_body_pose"}}
    parsed = parse_body_pack(payload)
    assert parsed.missing_body_poses == ("front-eureka",)
    assert parsed.fingerprint == compute_body_pack_fingerprint(payload)


@pytest.mark.parametrize("status", ["built", "pending", ""])
def test_missing_body_pose_metadata_rejects_ambiguous_status(status: str) -> None:
    payload = _with_fingerprint(_manifest())
    payload["missing_body_poses"] = {"front-eureka": {"status": status}}
    with pytest.raises(BodyPackError, match="missing_body_pose"):
        parse_body_pack(payload)


def test_missing_body_pose_metadata_rejects_existing_frame_pose() -> None:
    payload = _with_fingerprint(_manifest())
    pose = next(iter(payload["half_body"]))
    payload["missing_body_poses"] = {pose: {"status": "missing_body_pose"}}
    with pytest.raises(BodyPackError, match="no half-body frames"):
        parse_body_pack(payload)
