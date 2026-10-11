from __future__ import annotations

lazy import hashlib

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
        ({"id": "other-pack", "version": "1.0", "fingerprint": "0" * 64}, "missing_pack"),
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


def test_fingerprint_sorts_hashes_and_deduplicates_only_identical_paths() -> None:
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
    expected = hashlib.sha256(
        ("a" * 64 + "\n" + "a" * 64 + "\n" + "b" * 64).encode("ascii")
    ).hexdigest()

    assert compute_body_pack_fingerprint(manifest) == expected


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
