from __future__ import annotations

lazy import json
lazy import struct
lazy import subprocess
lazy import sys
lazy import zlib
lazy from itertools import pairwise
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from importlib import import_module

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from domain.hand_asset_audit import FINGERS, Point

WIDTH = 1024
HEIGHT = 1536
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_SKIN = (214, 155, 126, 255)
ROOT = Path(__file__).resolve().parents[1]
audit_tool = import_module("tools.audit_pose_atlas_working")


def _chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(
        ">I", zlib.crc32(body) & 0xFFFFFFFF
    )


def _encode_rgba(width: int, height: int, pixels: bytes) -> bytes:
    raw = b"".join(
        b"\x00" + pixels[y * width * 4 : (y + 1) * width * 4]
        for y in range(height)
    )
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def _points(side: str) -> tuple[Point, ...]:
    if side == "left":
        wrist = Point(27, 61)
        bases = {
            "thumb": Point(47, 50),
            "index": Point(40, 49),
            "middle": Point(31, 48),
            "ring": Point(22, 49),
            "pinky": Point(13, 51),
        }
        tips = {
            "thumb": Point(56, 38),
            "index": Point(40, 25),
            "middle": Point(31, 21),
            "ring": Point(22, 26),
            "pinky": Point(13, 35),
        }
    else:
        wrist = Point(105, 61)
        bases = {
            "thumb": Point(85, 50),
            "index": Point(92, 49),
            "middle": Point(101, 48),
            "ring": Point(110, 49),
            "pinky": Point(119, 51),
        }
        tips = {
            "thumb": Point(76, 38),
            "index": Point(92, 25),
            "middle": Point(101, 21),
            "ring": Point(110, 26),
            "pinky": Point(119, 35),
        }

    result = [wrist]
    for finger in ("thumb", "index", "middle", "ring", "pinky"):
        base = bases[finger]
        tip = tips[finger]
        for step in range(4):
            result.append(
                Point(
                    base.x + (tip.x - base.x) * step / 3,
                    base.y + (tip.y - base.y) * step / 3,
                ),
            )
    return tuple(result)


def _disk(pixels: bytearray, center: Point, radius: int = 2) -> None:
    for y in range(round(center.y) - radius, round(center.y) + radius + 1):
        for x in range(round(center.x) - radius, round(center.x) + radius + 1):
            if (x - center.x) ** 2 + (y - center.y) ** 2 <= radius**2:
                if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                    offset = (y * WIDTH + x) * 4
                    pixels[offset : offset + 4] = bytes(PNG_SKIN)


def _line(
    pixels: bytearray,
    first: Point,
    second: Point,
    radius: int = 1,
) -> None:
    steps = max(1, round(max(abs(second.x - first.x), abs(second.y - first.y))))
    for step in range(steps + 1):
        scale = step / steps
        x = first.x + (second.x - first.x) * scale
        y = first.y + (second.y - first.y) * scale
        _disk(pixels, Point(x, y), radius)


def _draw_hands(pixels: bytearray) -> None:
    for side in ("left", "right"):
        hand = _points(side)
        _disk(pixels, hand[0], 3)
        for finger, indices in FINGERS.items():
            _line(pixels, hand[0], hand[indices[0]])
            for first, second in pairwise(indices):
                _line(pixels, hand[first], hand[second])
            for index in indices:
                _disk(pixels, hand[index])


def _build_base_png() -> bytes:
    pixels = bytearray(WIDTH * HEIGHT * 4)
    _draw_hands(pixels)
    return _encode_rgba(WIDTH, HEIGHT, bytes(pixels))


BASE_PNG_BYTES = _build_base_png()


def _hands_sidecar(view_id: str, yaw: int) -> bytes:
    return json.dumps(
        {
            "schema_version": 1,
            "view_id": view_id,
            "yaw_degrees": yaw,
            "width": WIDTH,
            "height": HEIGHT,
            "hands": [
                {
                    "side": "left",
                    "roi": [8, 16, 54, 51],
                    "landmarks": [[point.x, point.y] for point in _points("left")],
                },
                {
                    "side": "right",
                    "roi": [70, 16, 54, 51],
                    "landmarks": [[point.x, point.y] for point in _points("right")],
                },
            ],
            "occluded_hands": [],
            "protected_regions": [
                {"label": "face", "rect": [62, 2, 8, 14]},
                {"label": "body", "rect": [55, 68, 23, 52]},
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _write_view_set(
    root: Path,
    *,
    missing_yaw: int | None = None,
    mismatch_yaw: int | None = None,
    mismatch_size: tuple[int, int] | None = None,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for yaw in CANONICAL_YAWS:
        if yaw == missing_yaw:
            continue
        view_id = canonical_view_id(yaw)
        sidecar = _hands_sidecar(view_id, yaw)
        if mismatch_yaw == yaw:
            width = mismatch_size[0] if mismatch_size else WIDTH
            height = mismatch_size[1] if mismatch_size else HEIGHT
            png_bytes = _encode_rgba(width, height, bytes(width * height * 4))
        else:
            png_bytes = BASE_PNG_BYTES
        (root / f"{view_id}.png").write_bytes(png_bytes)
        (root / f"{view_id}.hands.json").write_text(sidecar.decode("utf-8"), encoding="utf-8")


def _run_audit(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(sys.executable),
            str(ROOT / "tools" / "audit_pose_atlas_working.py"),
            "--root",
            str(root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _load_payload(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.returncode in (0, 1), result.stderr
    return json.loads(result.stdout)


def test_valid_working_directory_passes() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        _write_view_set(root)
        result = _run_audit(root)
        payload = _load_payload(result)
        assert result.returncode == 0
        assert payload["passed"] is True
        assert payload["view_count"] == len(CANONICAL_YAWS)
        assert payload["passed_view_count"] == len(CANONICAL_YAWS)


def test_missing_file_fails_with_stem() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        missing = canonical_view_id(CANONICAL_YAWS[-1])
        _write_view_set(root, missing_yaw=CANONICAL_YAWS[-1])
        result = _run_audit(root)
        payload = _load_payload(result)
        assert result.returncode == 1
        assert payload["passed"] is False
        missing_view = next(item for item in payload["views"] if item["view_id"] == missing)
        assert "asset_missing" in missing_view["issues"]
        assert missing in result.stdout


def test_dimension_mismatch_fails_closed() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        mismatch = CANONICAL_YAWS[5]
        _write_view_set(root)
        _write_view_set(root, mismatch_yaw=mismatch, mismatch_size=(WIDTH - 1, HEIGHT))
        result = _run_audit(root)
        payload = _load_payload(result)
        assert result.returncode == 1
        assert payload["passed"] is False
        target = canonical_view_id(mismatch)
        failed = next(item for item in payload["views"] if item["view_id"] == target)
        assert "dimension_mismatch" in failed["issues"]


def _run_with_custom_count(root: Path, extra_yaw: int, extra_view_id: str) -> dict[str, object]:
    original_yaws = audit_tool.CANONICAL_YAWS
    original_view_id = audit_tool.canonical_view_id
    try:
        audit_tool.CANONICAL_YAWS = (*original_yaws, extra_yaw)

        def patched_view_id(value: int) -> str:
            if value == extra_yaw:
                return extra_view_id
            return original_view_id(value)

        audit_tool.canonical_view_id = patched_view_id
        return audit_tool.audit(root)
    finally:
        audit_tool.CANONICAL_YAWS = original_yaws
        audit_tool.canonical_view_id = original_view_id


def test_view_count_mismatch_fails_for_missing_or_extra_angles() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        _write_view_set(root, missing_yaw=CANONICAL_YAWS[3])
        payload = _load_payload(_run_audit(root))
        assert payload["passed"] is False
        assert payload["failed_view_count"] == 1

    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        _write_view_set(root)
        extra_view_id = "yaw+999-pitch+000"
        payload = _run_with_custom_count(root, 999, extra_view_id)
        assert payload["passed"] is False
        assert payload["view_count"] == len(CANONICAL_YAWS) + 1
        extra_view = next(
            item for item in payload["views"] if item["view_id"] == extra_view_id
        )
        assert "asset_missing" in extra_view["issues"]


def main() -> int:
    tests = [
        test_valid_working_directory_passes,
        test_missing_file_fails_with_stem,
        test_dimension_mismatch_fails_closed,
        test_view_count_mismatch_fails_for_missing_or_extra_angles,
    ]
    for test_case in tests:
        test_case()
    print("AUDIT_POSE_ATLAS_WORKING_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
