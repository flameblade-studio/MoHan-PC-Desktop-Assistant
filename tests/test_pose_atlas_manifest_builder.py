from __future__ import annotations

lazy import json
lazy import struct
lazy import sys
lazy import zlib
lazy from dataclasses import dataclass
lazy from itertools import pairwise
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from character_pose import CANONICAL_YAWS, canonical_view_id
lazy from hand_asset_audit import FINGERS, Point
lazy from pose_atlas_manifest_builder import (
    PoseAtlasBuildConfig,
    build_pose_atlas_manifest,
)
lazy from pose_atlas_release_gate import (
    PoseAtlasAuditInputs,
    PoseLoadReleaseEvidence,
    audit_pose_atlas_release,
    manifest_sha256,
)

SHA256_HEX_LENGTH = 64
VIEW_COUNT = 24

WIDTH = 132
HEIGHT = 128


@dataclass(frozen=True)
class HandReport:
    passed: bool


@dataclass(frozen=True)
class Report:
    passed: bool
    problems: tuple[str, ...] = ()


def landmarks() -> dict[str, list[int]]:
    return {
        "crown": [66, 8],
        "left_hip": [61, 70], "left_knee": [60, 92], "left_ankle": [59, 114],
        "left_heel": [57, 117], "left_toe": [62, 117], "left_sole": [60, 119],
        "right_hip": [71, 70], "right_knee": [72, 92], "right_ankle": [73, 114],
        "right_heel": [75, 117], "right_toe": [70, 117], "right_sole": [72, 119],
    }


def rgba() -> bytes:
    data = bytearray(WIDTH * HEIGHT * 4)
    for y in range(8, 120):
        for x in range(55, 78):
            offset = (y * WIDTH + x) * 4
            data[offset : offset + 4] = bytes((80, 100, 130, 255))
    for side in ("left", "right"):
        hand = hand_points(side)
        _disk(data, hand[0], 3)
        for indices in FINGERS.values():
            _line(data, hand[0], hand[indices[0]])
            for first, second in pairwise(indices):
                _line(data, hand[first], hand[second])
            for index in indices:
                _disk(data, hand[index])
    return bytes(data)


def hand_points(side: str) -> tuple[Point, ...]:
    if side == "left":
        wrist, bases, tips = Point(27, 61), ((47, 50), (40, 49), (31, 48), (22, 49), (13, 51)), ((56, 38), (40, 25), (31, 21), (22, 26), (13, 35))
    else:
        wrist, bases, tips = Point(105, 61), ((85, 50), (92, 49), (101, 48), (110, 49), (119, 51)), ((76, 38), (92, 25), (101, 21), (110, 26), (119, 35))
    result = [wrist]
    for base, tip in zip(bases, tips, strict=False):
        result.extend(Point(base[0] + (tip[0] - base[0]) * step / 3, base[1] + (tip[1] - base[1]) * step / 3) for step in range(4))
    return tuple(result)


def _disk(data: bytearray, point: Point, radius: int = 2) -> None:
    for y in range(round(point.y) - radius, round(point.y) + radius + 1):
        for x in range(round(point.x) - radius, round(point.x) + radius + 1):
            if (x - point.x) ** 2 + (y - point.y) ** 2 <= radius**2:
                offset = (y * WIDTH + x) * 4
                data[offset : offset + 4] = bytes((214, 155, 126, 255))


def _line(data: bytearray, first: Point, second: Point) -> None:
    steps = max(1, round(max(abs(second.x - first.x), abs(second.y - first.y))))
    for step in range(steps + 1):
        scale = step / steps
        _disk(data, Point(first.x + (second.x - first.x) * scale, first.y + (second.y - first.y) * scale), 1)


def hands_sidecar(view_id: str, yaw: int) -> dict[str, object]:
    return {
        "schema_version": 1, "view_id": view_id, "yaw_degrees": yaw,
        "width": WIDTH, "height": HEIGHT,
        "hands": [
            {"side": "left", "roi": [8, 16, 54, 51], "landmarks": [[point.x, point.y] for point in hand_points("left")]},
            {"side": "right", "roi": [70, 16, 54, 51], "landmarks": [[point.x, point.y] for point in hand_points("right")]},
        ],
        "protected_regions": [
            {"label": "face", "rect": [62, 2, 8, 14]},
            {"label": "body", "rect": [55, 68, 23, 52]},
        ],
    }


def chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))


def png_bytes() -> bytes:
    pixels = rgba()
    rows = b"".join(
        b"\x00" + pixels[y * WIDTH * 4 : (y + 1) * WIDTH * 4]
        for y in range(HEIGHT)
    )
    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def write_ring(root: Path) -> None:
    for yaw in reversed(CANONICAL_YAWS):
        view_id = canonical_view_id(yaw)
        (root / f"{view_id}.png").write_bytes(png_bytes())
        sidecar = {
            "schema_version": 1,
            "view_id": view_id,
            "yaw_degrees": yaw,
            "landmarks": landmarks(),
        }
        (root / f"{view_id}.landmarks.json").write_text(
            json.dumps(sidecar, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        (root / f"{view_id}.hands.json").write_text(
            json.dumps(hands_sidecar(view_id, yaw), sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )


def config() -> PoseAtlasBuildConfig:
    return PoseAtlasBuildConfig("atlas-v4", "source-proof", "identity-proof")


def assert_complete_ring_is_sorted_deterministic_and_relative() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        write_ring(root)
        first = build_pose_atlas_manifest(root, config())
        second = build_pose_atlas_manifest(root, config())
        root_text = str(root.resolve())
    assert first.passed
    assert first.manifest is not None
    assert tuple(record.yaw_degrees for record in first.records) == CANONICAL_YAWS
    assert first.to_json_bytes() == second.to_json_bytes()
    assert root_text.encode("utf-8") not in first.to_json_bytes()
    assert all(not Path(record.rgba_path).is_absolute() for record in first.records)
    assert all(len(record.rgba_sha256) == SHA256_HEX_LENGTH for record in first.records)
    assert all(len(record.sidecar_sha256) == SHA256_HEX_LENGTH for record in first.records)
    assert all(len(record.hands_sha256) == SHA256_HEX_LENGTH for record in first.records)


def assert_missing_or_mismatched_assets_fail_closed() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        write_ring(root)
        missing = canonical_view_id(15)
        (root / f"{missing}.png").unlink()
        result = build_pose_atlas_manifest(root, config())
        assert not result.passed
        assert result.manifest is None
        assert result.records == ()
        assert any(issue.code == "rgba_missing" and issue.view_id == missing for issue in result.issues)
        write_ring(root)
        target = canonical_view_id(30)
        sidecar = root / f"{target}.landmarks.json"
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        payload["yaw_degrees"] = 45
        sidecar.write_text(json.dumps(payload), encoding="utf-8")
        result = build_pose_atlas_manifest(root, config())
        assert not result.passed
        assert any(issue.code == "asset_pair_invalid" and issue.view_id == target for issue in result.issues)


def assert_no_landmarks_or_hand_evidence_are_invented() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        write_ring(root)
        target = canonical_view_id(0)
        sidecar = root / f"{target}.landmarks.json"
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        del payload["landmarks"]["left_sole"]
        sidecar.write_text(json.dumps(payload), encoding="utf-8")
        result = build_pose_atlas_manifest(root, config())
        assert not result.passed
        assert result.release_views() == ()
        write_ring(root)
        result = build_pose_atlas_manifest(root, config())
        assert len(result.release_views()) == VIEW_COUNT


def assert_output_feeds_release_gate_without_adapter_guessing() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        write_ring(root)
        result = build_pose_atlas_manifest(root, config())
        views = result.release_views()
    assert result.manifest is not None
    assert len(views) == VIEW_COUNT
    load = PoseLoadReleaseEvidence(
        True,
        manifest_sha256(result.manifest),
        "a" * 64,
    )
    release = audit_pose_atlas_release(
        result.manifest,
        load,
        views,
        PoseAtlasAuditInputs(Report(True), Report(True), Report(True)),
    )
    assert release.releasable


def assert_invalid_config_never_builds_a_manifest() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        write_ring(root)
        result = build_pose_atlas_manifest(
            root,
            PoseAtlasBuildConfig("", "", ""),
        )
    assert not result.passed
    assert result.manifest is None
    assert {issue.code for issue in result.issues} >= {
        "pack_id_missing", "source_evidence_missing", "identity_evidence_missing"
    }


def run() -> None:
    assert_complete_ring_is_sorted_deterministic_and_relative()
    assert_missing_or_mismatched_assets_fail_closed()
    assert_no_landmarks_or_hand_evidence_are_invented()
    assert_output_feeds_release_gate_without_adapter_guessing()
    assert_invalid_config_never_builds_a_manifest()
    print("POSE_ATLAS_MANIFEST_BUILDER_OK")


if __name__ == "__main__":
    run()
