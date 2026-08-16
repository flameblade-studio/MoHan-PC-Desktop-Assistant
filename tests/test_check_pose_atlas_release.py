from __future__ import annotations

lazy import json
lazy import struct
lazy import sys
lazy import zlib
lazy from itertools import pairwise
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from character_pose import CANONICAL_YAWS, canonical_view_id
lazy from hand_asset_audit import FINGERS, Point
lazy from tools.check_pose_atlas_release import requires_v4_gate, run_preflight

WIDTH = 132
HEIGHT = 128


def landmarks() -> dict[str, list[int]]:
    return {
        "crown": [66, 8],
        "left_hip": [61, 70], "left_knee": [60, 92], "left_ankle": [59, 114],
        "left_heel": [57, 117], "left_toe": [62, 117], "left_sole": [60, 119],
        "right_hip": [71, 70], "right_knee": [72, 92], "right_ankle": [73, 114],
        "right_heel": [75, 117], "right_toe": [70, 117], "right_sole": [72, 119],
    }


def chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))


def png_bytes() -> bytes:
    pixels = bytearray(WIDTH * HEIGHT * 4)
    for y in range(8, 120):
        for x in range(55, 78):
            offset = (y * WIDTH + x) * 4
            pixels[offset : offset + 4] = bytes((80, 100, 130, 255))
    for side in ("left", "right"):
        hand = hand_points(side)
        disk(pixels, hand[0], 3)
        for indices in FINGERS.values():
            line(pixels, hand[0], hand[indices[0]])
            for first, second in pairwise(indices):
                line(pixels, hand[first], hand[second])
            for index in indices:
                disk(pixels, hand[index])
    rows = b"".join(
        b"\x00" + pixels[y * WIDTH * 4 : (y + 1) * WIDTH * 4]
        for y in range(HEIGHT)
    )
    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def hand_points(side: str) -> tuple[Point, ...]:
    if side == "left":
        wrist, bases, tips = Point(27, 61), ((47, 50), (40, 49), (31, 48), (22, 49), (13, 51)), ((56, 38), (40, 25), (31, 21), (22, 26), (13, 35))
    else:
        wrist, bases, tips = Point(105, 61), ((85, 50), (92, 49), (101, 48), (110, 49), (119, 51)), ((76, 38), (92, 25), (101, 21), (110, 26), (119, 35))
    result = [wrist]
    for base, tip in zip(bases, tips):
        result.extend(Point(base[0] + (tip[0] - base[0]) * step / 3, base[1] + (tip[1] - base[1]) * step / 3) for step in range(4))
    return tuple(result)


def disk(pixels: bytearray, point: Point, radius: int = 2) -> None:
    for y in range(round(point.y) - radius, round(point.y) + radius + 1):
        for x in range(round(point.x) - radius, round(point.x) + radius + 1):
            if (x - point.x) ** 2 + (y - point.y) ** 2 <= radius**2:
                offset = (y * WIDTH + x) * 4
                pixels[offset : offset + 4] = bytes((214, 155, 126, 255))


def line(pixels: bytearray, first: Point, second: Point) -> None:
    steps = max(1, round(max(abs(second.x - first.x), abs(second.y - first.y))))
    for step in range(steps + 1):
        scale = step / steps
        disk(pixels, Point(first.x + (second.x - first.x) * scale, first.y + (second.y - first.y) * scale), 1)


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


def write_assets(root: Path) -> None:
    for yaw in CANONICAL_YAWS:
        view_id = canonical_view_id(yaw)
        (root / f"{view_id}.png").write_bytes(png_bytes())
        (root / f"{view_id}.landmarks.json").write_text(
            json.dumps({
                "schema_version": 1,
                "view_id": view_id,
                "yaw_degrees": yaw,
                "landmarks": landmarks(),
            }),
            encoding="utf-8",
        )
        (root / f"{view_id}.hands.json").write_text(
            json.dumps(hands_sidecar(view_id, yaw)),
            encoding="utf-8",
        )


def write_audits(path: Path, *, identity_passed: bool = True) -> None:
    path.write_text(
        json.dumps({
            "schema_version": 1,
            "manifest": {
                "pack_id": "atlas-v4",
                "source_evidence": "source-proof",
                "identity_evidence": "identity-proof",
                "body_profile_id": "mohan-body-v1",
                "body_profile_version_range": [1, 2],
                "rig_id": "mohan-full-body-v1",
                "rig_version_range": [1, 2],
            },
            "load": {"passed": True, "source_revision_sha256": "a" * 64, "problems": []},
            "identity": {"passed": identity_passed, "problems": [] if identity_passed else ["face_geometry_drift:+000"]},
            "pose_atlas": {"passed": True, "problems": []},
            "hands": {canonical_view_id(yaw): {"passed": True} for yaw in CANONICAL_YAWS},
        }),
        encoding="utf-8",
    )


def assert_v3_bypasses_without_reading_v4_paths() -> None:
    code, output = run_preflight(
        "3.1.2",
        Path("C:/does-not-exist/private-assets"),
        Path("C:/does-not-exist/private-audits.json"),
    )
    assert code == 0
    assert json.loads(output) == {
        "schema_version": 1,
        "status": "not-required",
        "version": "3.1.2",
    }
    assert "C:/" not in output


def assert_v4_missing_assets_and_failed_audit_block() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        audits = root / "audits.json"
        write_audits(audits)
        code, output = run_preflight("4.0.0", root / "missing", audits)
        assert code == 1
        assert json.loads(output)["status"] == "blocked"
        write_assets(root)
        write_audits(audits, identity_passed=False)
        code, output = run_preflight("4.0.0", root, audits)
        assert code == 1
        assert "identity_audit_failed" in output
        assert str(root.resolve()) not in output


def assert_v4_missing_pose_atlas_inputs_fail_closed() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        code, output = run_preflight(
            "4.0.0",
            root / "missing-assets",
            root / "missing-audits.json",
        )
        assert code == 1
        payload = json.loads(output)
        assert payload["status"] == "blocked"
        assert payload["issues"] == [{"code": "audit_evidence_invalid"}]

        audits = root / "audits.json"
        write_audits(audits)
        code, output = run_preflight(
            "4.0.0",
            root / "missing-assets",
            audits,
        )
        assert code == 1
        assert json.loads(output)["status"] == "blocked"


def assert_v4_complete_evidence_passes_deterministically() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        audits = root / "audits.json"
        write_assets(root)
        write_audits(audits)
        first = run_preflight("4.0.0", root, audits)
        second = run_preflight("4.0.0", root, audits)
    assert first == second
    assert first[0] == 0
    assert json.loads(first[1])["status"] == "releasable"


def assert_boolean_hands_cannot_replace_physical_sidecars() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        audits = root / "audits.json"
        write_assets(root)
        write_audits(audits)
        missing = canonical_view_id(0)
        (root / f"{missing}.hands.json").unlink()
        code, output = run_preflight("4.0.0", root, audits)
        assert code == 1
        assert "hands_sidecar_missing" in output
        assert "landmark" not in output
        assert str(root.resolve()) not in output


def assert_physical_hand_hash_or_missing_digit_blocks() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        audits = root / "audits.json"
        write_assets(root)
        write_audits(audits)
        target = canonical_view_id(15)
        sidecar = root / f"{target}.hands.json"
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        payload["hands"][0]["landmarks"] = payload["hands"][0]["landmarks"][:-1]
        sidecar.write_text(json.dumps(payload), encoding="utf-8")
        code, output = run_preflight("4.0.0", root, audits)
        assert code == 1
        assert "hand_evidence_failed" in output


def assert_explicit_v4_flag_gates_older_versions() -> None:
    assert not requires_v4_gate("3.1.2")
    assert requires_v4_gate("3.1.2", explicit_flag=True)
    assert requires_v4_gate("4.0.0-rc.1")


def run() -> None:
    assert_v3_bypasses_without_reading_v4_paths()
    assert_v4_missing_assets_and_failed_audit_block()
    assert_v4_missing_pose_atlas_inputs_fail_closed()
    assert_v4_complete_evidence_passes_deterministically()
    assert_boolean_hands_cannot_replace_physical_sidecars()
    assert_physical_hand_hash_or_missing_digit_blocks()
    assert_explicit_v4_flag_gates_older_versions()
    print("CHECK_POSE_ATLAS_RELEASE_OK")


if __name__ == "__main__":
    run()
