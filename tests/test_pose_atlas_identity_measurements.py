from __future__ import annotations

lazy import hashlib
lazy import json
lazy import struct
lazy import zlib
lazy from pathlib import Path

lazy import pytest

lazy from domain.character_identity_audit import REAR_YAW
lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from tools import build_pose_atlas_identity_measurements as measurements


ROOT = Path(__file__).resolve().parents[1]
CURRENT_ATLAS = ROOT / "assets" / "pose-atlas" / "v5-base"
MISSING_NATIVE_FACE_YAWS = frozenset({-165, -150, -135, -90, 135, 150, 165})
REAR_VIEW_YAW = -REAR_YAW
AVAILABLE_NATIVE_FACE_COUNT = 16
MISSING_REAR_THREE_QUARTER_COUNT = 6
NON_REAR_SIGNATURE_COUNT = 23
CURRENT_SCALE_PROBLEM_COUNT = 29


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _write_rgba_png(path: Path, *, red: int) -> None:
    width = 8
    height = 10
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    pixel = bytes((red, 0, 0, 255))
    scanlines = b"".join(b"\x00" + pixel * width for _ in range(height))
    path.write_bytes(
        measurements.PNG_SIGNATURE
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(scanlines))
        + _png_chunk(b"IEND", b"")
    )


def _write_sidecar(
    path: Path,
    *,
    yaw: int,
    png_sha: str,
    source_path: str,
    artifact_path: str | None,
    artifact_sha: str | None,
    target_height: float = 9.0,
) -> None:
    view_id = canonical_view_id(yaw)
    landmark_count = (
        0 if yaw == REAR_VIEW_YAW or yaw in MISSING_NATIVE_FACE_YAWS else 478
    )
    native_face = {
        "landmark_count": landmark_count,
        "source": {"path": source_path, "sha256": png_sha},
    }
    if artifact_path is not None and artifact_sha is not None:
        native_face["artifact"] = {"path": artifact_path, "sha256": artifact_sha}
    path.write_text(
        json.dumps({
            "view_id": view_id,
            "yaw_degrees": yaw,
            "width": 8,
            "height": 10,
            "measurement": {
                "source_sha256": png_sha,
                "target_subject_height": target_height,
            },
            "native_face_landmarks": native_face,
        }),
        encoding="utf-8",
    )


def _write_face_artifact(
    path: Path,
    *,
    source_path: str,
    png_sha: str,
    landmark_count: int = 478,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "confidence": 0.9,
            "size": [8, 10],
            "source": {"path": source_path, "sha256": png_sha},
            "landmarks": [
                {"x": 0.5, "y": 0.5, "z": 0.0}
                for _ in range(landmark_count)
            ],
        }),
        encoding="utf-8",
    )


def _fixture_atlas(tmp_path: Path) -> Path:
    atlas = tmp_path / "atlas"
    atlas.mkdir()
    records = []
    for yaw in CANONICAL_YAWS:
        view_id = canonical_view_id(yaw)
        png = atlas / f"{view_id}.png"
        _write_rgba_png(png, red=(yaw + 180) % 255)
        png_sha = _sha256(png)
        source_path = png.relative_to(tmp_path).as_posix()
        artifact = tmp_path / "native-face-artifacts" / f"{view_id}.json"
        has_artifact = yaw != REAR_VIEW_YAW and yaw not in MISSING_NATIVE_FACE_YAWS
        if has_artifact:
            _write_face_artifact(
                artifact,
                source_path=source_path,
                png_sha=png_sha,
            )
        sidecar = atlas / f"{view_id}.landmarks.json"
        _write_sidecar(
            sidecar,
            yaw=yaw,
            png_sha=png_sha,
            source_path=source_path,
            artifact_path=(artifact.relative_to(tmp_path).as_posix() if has_artifact else None),
            artifact_sha=(_sha256(artifact) if has_artifact else None),
        )
        landmark_count = (
            0 if yaw == REAR_VIEW_YAW or yaw in MISSING_NATIVE_FACE_YAWS else 478
        )
        records.append({
            "view_id": view_id,
            "yaw_degrees": yaw,
            "normalized_sha256": png_sha,
            "body_sidecar": f"provenance/{sidecar.name}",
            "body_sidecar_sha256": _sha256(sidecar),
            "native_face": {
                "landmark_count": landmark_count,
                "source_sha256": png_sha,
            },
        })
    (atlas / "BUILD-METADATA.json").write_text(
        json.dumps({
            "native_face_evidence": {
                "model": "fixture-native-face-provider",
                "coordinates": "normalized_xy_plus_relative_z",
                "model_sha256": {"fixture.model": "0" * 64},
            },
            "views": records,
        }),
        encoding="utf-8",
    )
    return atlas


def _refresh_sidecar_declaration(atlas: Path, yaw: int) -> None:
    metadata_path = atlas / "BUILD-METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    view_id = canonical_view_id(yaw)
    record = next(item for item in metadata["views"] if item["yaw_degrees"] == yaw)
    record["body_sidecar_sha256"] = _sha256(atlas / f"{view_id}.landmarks.json")
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")


def _sync_artifact_declaration(atlas: Path, yaw: int) -> None:
    view_id = canonical_view_id(yaw)
    sidecar_path = atlas / f"{view_id}.landmarks.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    artifact_path = atlas.parent / sidecar["native_face_landmarks"]["artifact"]["path"]
    sidecar["native_face_landmarks"]["artifact"]["sha256"] = _sha256(artifact_path)
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    _refresh_sidecar_declaration(atlas, yaw)


def test_builder_records_available_missing_and_rear_without_geometry(
    tmp_path: Path,
) -> None:
    report = measurements.build_measurements(
        _fixture_atlas(tmp_path),
        project_root=tmp_path,
    )

    faces = report["native_face_landmarks"]
    assert len(faces["available_478"]) == AVAILABLE_NATIVE_FACE_COUNT
    assert len(faces["missing_rear_three_quarter"]) == MISSING_REAR_THREE_QUARTER_COUNT
    assert faces["rear_none"] == ["yaw-180-pitch+00"]
    assert report["geometry"]["required_non_rear_signatures"] == NON_REAR_SIGNATURE_COUNT
    assert report["geometry"]["complete_signatures"] == 0
    assert report["scale_audit"] == {"passed": True, "problems": []}
    assert all(view["face_geometry_signature"] is None for view in report["views"])
    artifacts = [
        view["native_face_artifact"]
        for view in report["views"]
        if view["native_face_artifact"] is not None
    ]
    assert len(artifacts) == AVAILABLE_NATIVE_FACE_COUNT
    assert all(
        artifact["landmark_count"] == measurements.FACE_LANDMARK_COUNT
        for artifact in artifacts
    )
    assert report["native_face_landmarks"]["provider"]["model"] == (
        "fixture-native-face-provider"
    )


@pytest.mark.parametrize(
    ("suffix", "message"),
    [
        (".png", "PNG.*SHA256"),
        (".landmarks.json", "body sidecar.*SHA256"),
    ],
)
def test_builder_rejects_source_sha_mismatch(
    tmp_path: Path,
    suffix: str,
    message: str,
) -> None:
    atlas = _fixture_atlas(tmp_path)
    (atlas / f"yaw+000-pitch+00{suffix}").write_bytes(b"changed")

    with pytest.raises(measurements.SourceContractError, match=message):
        measurements.build_measurements(atlas, project_root=tmp_path)


def test_builder_rejects_missing_view(tmp_path: Path) -> None:
    atlas = _fixture_atlas(tmp_path)
    (atlas / "yaw+030-pitch+00.png").unlink()

    with pytest.raises(measurements.SourceContractError, match="missing view PNG"):
        measurements.build_measurements(atlas, project_root=tmp_path)


def test_changed_height_surfaces_domain_scale_errors(tmp_path: Path) -> None:
    atlas = _fixture_atlas(tmp_path)
    yaw = 15
    view_id = canonical_view_id(yaw)
    sidecar_path = atlas / f"{view_id}.landmarks.json"
    png_sha = _sha256(atlas / f"{view_id}.png")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    artifact = sidecar["native_face_landmarks"]["artifact"]
    _write_sidecar(
        sidecar_path,
        yaw=yaw,
        png_sha=png_sha,
        source_path=f"atlas/{view_id}.png",
        artifact_path=artifact["path"],
        artifact_sha=artifact["sha256"],
        target_height=9.9,
    )
    _refresh_sidecar_declaration(atlas, yaw)

    report = measurements.build_measurements(atlas, project_root=tmp_path)

    assert "subject_scale_drift:+015" in report["scale_audit"]["problems"]
    assert "mirror_scale_drift:+015" in report["scale_audit"]["problems"]
    assert not report["scale_audit"]["passed"]


def test_synced_sidecar_hash_cannot_hide_wrong_canvas(tmp_path: Path) -> None:
    atlas = _fixture_atlas(tmp_path)
    yaw = 0
    view_id = canonical_view_id(yaw)
    sidecar_path = atlas / f"{view_id}.landmarks.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["width"] = 9
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
    _refresh_sidecar_declaration(atlas, yaw)

    with pytest.raises(measurements.SourceContractError, match="canvas does not match PNG"):
        measurements.build_measurements(atlas, project_root=tmp_path)


def test_builder_rejects_missing_native_face_artifact(tmp_path: Path) -> None:
    atlas = _fixture_atlas(tmp_path)
    view_id = canonical_view_id(0)
    sidecar = json.loads(
        (atlas / f"{view_id}.landmarks.json").read_text(encoding="utf-8")
    )
    artifact = tmp_path / sidecar["native_face_landmarks"]["artifact"]["path"]
    artifact.unlink()

    with pytest.raises(measurements.SourceContractError, match="missing native face artifact"):
        measurements.build_measurements(atlas, project_root=tmp_path)


def test_synced_hashes_cannot_hide_wrong_actual_point_count(tmp_path: Path) -> None:
    atlas = _fixture_atlas(tmp_path)
    yaw = 0
    view_id = canonical_view_id(yaw)
    sidecar = json.loads(
        (atlas / f"{view_id}.landmarks.json").read_text(encoding="utf-8")
    )
    artifact_path = tmp_path / sidecar["native_face_landmarks"]["artifact"]["path"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["landmarks"].pop()
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    _sync_artifact_declaration(atlas, yaw)

    with pytest.raises(measurements.SourceContractError, match="point count mismatch"):
        measurements.build_measurements(atlas, project_root=tmp_path)


def test_synced_hashes_cannot_hide_non_finite_actual_point(tmp_path: Path) -> None:
    atlas = _fixture_atlas(tmp_path)
    yaw = 0
    view_id = canonical_view_id(yaw)
    sidecar = json.loads(
        (atlas / f"{view_id}.landmarks.json").read_text(encoding="utf-8")
    )
    artifact_path = tmp_path / sidecar["native_face_landmarks"]["artifact"]["path"]
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["landmarks"][0]["x"] = float("nan")
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
    _sync_artifact_declaration(atlas, yaw)

    with pytest.raises(measurements.SourceContractError, match="non-finite"):
        measurements.build_measurements(atlas, project_root=tmp_path)


def test_current_formal_sources_report_actual_measurement_boundary() -> None:
    report = measurements.build_measurements(CURRENT_ATLAS, project_root=ROOT)

    assert (
        len(report["native_face_landmarks"]["available_478"])
        == AVAILABLE_NATIVE_FACE_COUNT
    )
    assert (
        len(report["native_face_landmarks"]["missing_rear_three_quarter"])
        == MISSING_REAR_THREE_QUARTER_COUNT
    )
    assert report["native_face_landmarks"]["rear_none"] == ["yaw-180-pitch+00"]
    assert len(report["scale_audit"]["problems"]) == CURRENT_SCALE_PROBLEM_COUNT
    assert report["geometry"]["complete_signatures"] == 0
