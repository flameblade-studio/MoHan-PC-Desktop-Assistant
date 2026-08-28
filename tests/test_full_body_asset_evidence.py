from __future__ import annotations

lazy import json
lazy import struct
lazy import sys
lazy import zlib
lazy from dataclasses import replace
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.character_pose import canonical_view_id
lazy from domain.full_body_asset_evidence import (
    FullBodyAssetManifestView,
    ImageBackendUnavailable,
    build_full_body_asset_evidence,
)

WIDTH = 64
HEIGHT = 64
YAW = 0
VIEW_ID = canonical_view_id(YAW)
EXPECTED_PERSON_HEIGHT = 48
EXPECTED_SOLE_Y = 55


def landmarks() -> dict[str, list[int]]:
    return {
        "crown": [32, 8],
        "left_hip": [27, 30],
        "left_knee": [26, 42],
        "left_ankle": [25, 52],
        "left_heel": [24, 54],
        "left_toe": [28, 54],
        "left_sole": [26, 55],
        "right_hip": [37, 30],
        "right_knee": [38, 42],
        "right_ankle": [39, 52],
        "right_heel": [40, 54],
        "right_toe": [36, 54],
        "right_sole": [38, 55],
    }


def rgba(*, opaque_background: bool = False, touches_edge: bool = False) -> bytes:
    data = bytearray(WIDTH * HEIGHT * 4)
    if opaque_background:
        for index in range(WIDTH * HEIGHT):
            data[index * 4 : index * 4 + 4] = bytes((10, 20, 30, 255))
        return bytes(data)
    left = 0 if touches_edge else 20
    for y in range(8, 56):
        for x in range(left, 45):
            index = (y * WIDTH + x) * 4
            data[index : index + 4] = bytes((80, 100, 130, 255))
    return bytes(data)


def write_png(path: Path, pixels: bytes) -> None:
    rows = b"".join(
        b"\x00" + pixels[y * WIDTH * 4 : (y + 1) * WIDTH * 4]
        for y in range(HEIGHT)
    )
    signature = b"\x89PNG\r\n\x1a\n"
    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0)
    path.write_bytes(
        signature
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))


def write_sidecar(path: Path, *, body: dict[str, object] | None = None) -> None:
    payload = body or {
        "schema_version": 1,
        "view_id": VIEW_ID,
        "yaw_degrees": YAW,
        "landmarks": landmarks(),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def manifest() -> FullBodyAssetManifestView:
    return FullBodyAssetManifestView(VIEW_ID, YAW, WIDTH, HEIGHT)


class MissingDecoder:
    def decode(self, _path: Path):
        raise ImageBackendUnavailable


def fixture_paths(root: Path) -> tuple[Path, Path]:
    png = root / f"{VIEW_ID}.png"
    sidecar = root / f"{VIEW_ID}.landmarks.json"
    write_png(png, rgba())
    write_sidecar(sidecar)
    return png, sidecar


def assert_real_rgba_png_produces_non_image_evidence() -> None:
    with TemporaryDirectory() as temporary:
        png, sidecar = fixture_paths(Path(temporary))
        result = build_full_body_asset_evidence(png, sidecar, manifest())
    assert result.passed
    evidence = result.evidence
    assert evidence is not None
    assert evidence.person_height == EXPECTED_PERSON_HEIGHT
    assert evidence.left_sole_y == evidence.right_sole_y == EXPECTED_SOLE_Y
    assert evidence.limbs_unclipped
    serialized = repr(result)
    assert "PNG" not in serialized
    assert "embedding" not in serialized
    assert "rgba" not in serialized.lower()


def assert_identity_requires_filename_manifest_and_sidecar_agreement() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        png, sidecar = fixture_paths(root)
        wrong_name = root / "not-canonical.png"
        png.rename(wrong_name)
        result = build_full_body_asset_evidence(wrong_name, sidecar, manifest())
        assert "filename_identity_mismatch:+000" in result.problems
        write_png(png, rgba())
        write_sidecar(
            sidecar,
            body={
                "schema_version": 1,
                "view_id": canonical_view_id(15),
                "yaw_degrees": 15,
                "landmarks": landmarks(),
            },
        )
        result = build_full_body_asset_evidence(png, sidecar, manifest())
        assert "sidecar_identity_mismatch:+000" in result.problems


def assert_transparency_canvas_and_decode_fail_closed() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        png, sidecar = fixture_paths(root)
        write_png(png, rgba(opaque_background=True))
        result = build_full_body_asset_evidence(png, sidecar, manifest())
        assert "missing_true_transparency:+000" in result.problems
        write_png(png, rgba())
        result = build_full_body_asset_evidence(
            png, sidecar, replace(manifest(), canvas_width=65)
        )
        assert "canvas_mismatch:+000" in result.problems
        result = build_full_body_asset_evidence(
            png, sidecar, manifest(), decoder=MissingDecoder()
        )
        assert "image_backend_unavailable:+000" in result.problems


def assert_landmarks_are_complete_on_subject_and_versioned() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        png, sidecar = fixture_paths(root)
        incomplete = landmarks()
        del incomplete["left_sole"]
        write_sidecar(
            sidecar,
            body={
                "schema_version": 1,
                "view_id": VIEW_ID,
                "yaw_degrees": YAW,
                "landmarks": incomplete,
            },
        )
        assert "invalid_landmarks:+000" in build_full_body_asset_evidence(
            png, sidecar, manifest()
        ).problems
        off_subject = landmarks()
        off_subject["right_toe"] = [60, 60]
        write_sidecar(
            sidecar,
            body={
                "schema_version": 1,
                "view_id": VIEW_ID,
                "yaw_degrees": YAW,
                "landmarks": off_subject,
            },
        )
        assert "landmark_outside_subject:+000" in build_full_body_asset_evidence(
            png, sidecar, manifest()
        ).problems
        write_sidecar(
            sidecar,
            body={
                "schema_version": 3,
                "view_id": VIEW_ID,
                "yaw_degrees": YAW,
                "landmarks": landmarks(),
            },
        )
        assert "unsupported_sidecar_version:+000" in build_full_body_asset_evidence(
            png, sidecar, manifest()
        ).problems


def assert_natural_occlusion_requires_explicit_declarations() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        png, sidecar = fixture_paths(root)
        visible = landmarks()
        hidden = {
            name: visible.pop(name)
            for name in tuple(visible)
            if name.startswith("right_")
        }
        write_sidecar(
            sidecar,
            body={
                "schema_version": 2,
                "view_id": VIEW_ID,
                "yaw_degrees": YAW,
                "landmarks": visible,
                "occluded_landmarks": [
                    {
                        "name": name,
                        "reason": "The sleeve and torso hide this side in the authored view.",
                        "occluder_id": "body-and-sleeve",
                    }
                    for name in hidden
                ],
            },
        )
        result = build_full_body_asset_evidence(png, sidecar, manifest())
    assert result.passed
    assert result.evidence is not None
    assert result.evidence.occluded_sides == frozenset({"right"})
    assert result.evidence.right_sole_y is None

    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        png, sidecar = fixture_paths(root)
        incomplete = landmarks()
        del incomplete["right_sole"]
        write_sidecar(
            sidecar,
            body={
                "schema_version": 2,
                "view_id": VIEW_ID,
                "yaw_degrees": YAW,
                "landmarks": incomplete,
            },
        )
        result = build_full_body_asset_evidence(png, sidecar, manifest())
    assert "invalid_landmarks:+000" in result.problems


def assert_edge_contact_cannot_be_hidden_by_landmark_names() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        png, sidecar = fixture_paths(root)
        write_png(png, rgba(touches_edge=True))
        result = build_full_body_asset_evidence(png, sidecar, manifest())
    assert not result.passed
    assert result.evidence is None
    assert "unsafe_subject_margin:+000" in result.problems


def run() -> None:
    assert_real_rgba_png_produces_non_image_evidence()
    assert_identity_requires_filename_manifest_and_sidecar_agreement()
    assert_transparency_canvas_and_decode_fail_closed()
    assert_landmarks_are_complete_on_subject_and_versioned()
    assert_natural_occlusion_requires_explicit_declarations()
    assert_edge_contact_cannot_be_hidden_by_landmark_names()
    print("FULL_BODY_ASSET_EVIDENCE_OK")


if __name__ == "__main__":
    run()
