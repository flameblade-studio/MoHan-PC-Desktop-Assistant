from __future__ import annotations

lazy import hashlib
lazy import json
lazy import struct
lazy import sys
lazy import zlib
lazy from dataclasses import replace
lazy from itertools import pairwise
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.character_pose import canonical_view_id
lazy from domain.hand_asset_audit import FINGERS, Point
lazy from domain.hand_asset_evidence import (
    HandAssetManifestEvidence,
    build_hand_asset_evidence,
)

WIDTH, HEIGHT = 132, 72
VIEW_ID = canonical_view_id(0)
SKIN = (214, 155, 126, 255)


def points(side: str) -> tuple[Point, ...]:
    if side == "left":
        wrist = Point(27, 61)
        bases = {"thumb": Point(47, 50), "index": Point(40, 49), "middle": Point(31, 48), "ring": Point(22, 49), "pinky": Point(13, 51)}
        tips = {"thumb": Point(56, 38), "index": Point(40, 25), "middle": Point(31, 21), "ring": Point(22, 26), "pinky": Point(13, 35)}
    else:
        wrist = Point(105, 61)
        bases = {"thumb": Point(85, 50), "index": Point(92, 49), "middle": Point(101, 48), "ring": Point(110, 49), "pinky": Point(119, 51)}
        tips = {"thumb": Point(76, 38), "index": Point(92, 25), "middle": Point(101, 21), "ring": Point(110, 26), "pinky": Point(119, 35)}
    result = [wrist]
    for finger in ("thumb", "index", "middle", "ring", "pinky"):
        base, tip = bases[finger], tips[finger]
        result.extend(Point(base.x + (tip.x - base.x) * step / 3, base.y + (tip.y - base.y) * step / 3) for step in range(4))
    return tuple(result)


def disk(pixels: bytearray, point: Point, radius: int = 2) -> None:
    for y in range(round(point.y) - radius, round(point.y) + radius + 1):
        for x in range(round(point.x) - radius, round(point.x) + radius + 1):
            if 0 <= x < WIDTH and 0 <= y < HEIGHT and (x - point.x) ** 2 + (y - point.y) ** 2 <= radius**2:
                offset = (y * WIDTH + x) * 4
                pixels[offset : offset + 4] = bytes(SKIN)


def line(pixels: bytearray, start: Point, end: Point, radius: int = 1) -> None:
    steps = max(1, round(max(abs(end.x - start.x), abs(end.y - start.y))))
    for step in range(steps + 1):
        scale = step / steps
        disk(pixels, Point(start.x + (end.x - start.x) * scale, start.y + (end.y - start.y) * scale), radius)


def png(
    *,
    omit: tuple[str, str] | None = None,
    omit_hand: str | None = None,
    omit_hands: frozenset[str] = frozenset(),
    fused: bool = False,
    outside_fake_hand: bool = False,
    inside_extra_finger: bool = False,
) -> bytes:
    pixels = bytearray(WIDTH * HEIGHT * 4)
    draw_hands(pixels, omit, omit_hand, omit_hands, fused)
    draw_body_skin(pixels)
    draw_extra_skin(pixels, outside_fake_hand, inside_extra_finger)
    raw = b"".join(b"\0" + pixels[y * WIDTH * 4 : (y + 1) * WIDTH * 4] for y in range(HEIGHT))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def draw_hands(pixels, omit, omit_hand, omit_hands, fused) -> None:
    for side in ("left", "right"):
        if side == omit_hand or side in omit_hands:
            continue
        hand = points(side)
        disk(pixels, hand[0], 3)
        for finger, indices in FINGERS.items():
            if omit == (side, finger):
                continue
            line(pixels, hand[0], hand[indices[0]])
            for first, second in pairwise(indices):
                line(pixels, hand[first], hand[second])
            for index in indices:
                disk(pixels, hand[index])
        if fused:
            for first_name, second_name in zip(("index", "middle", "ring"), ("middle", "ring", "pinky"), strict=False):
                for position in (1, 2, 3):
                    line(pixels, hand[FINGERS[first_name][position]], hand[FINGERS[second_name][position]], 2)


def draw_body_skin(pixels) -> None:
    for y in range(3, 15):
        for x in range(63, 69):
            disk(pixels, Point(x, y), 0)
    for y in range(20, 67):
        for x in range(63, 69):
            disk(pixels, Point(x, y), 0)


def draw_extra_skin(pixels, outside_fake_hand, inside_extra_finger) -> None:
    if outside_fake_hand:
        line(pixels, Point(65, 25), Point(65, 45), 2)
    if inside_extra_finger:
        line(pixels, Point(10, 60), Point(10, 30), 2)


def chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def sidecar(
    *,
    hands: list[dict[str, object]] | None = None,
    skin_background: object = None,
    occluded_hands: list[dict[str, object]] | None = None,
) -> bytes:
    configured = [
        {
            "side": "left",
            "roi": [8, 16, 54, 51],
            "landmarks": [[point.x, point.y] for point in points("left")],
        },
        {
            "side": "right",
            "roi": [70, 16, 54, 51],
            "landmarks": [[point.x, point.y] for point in points("right")],
        },
    ] if hands is None else hands
    return json.dumps({
        "schema_version": 1,
        "view_id": VIEW_ID,
        "yaw_degrees": 0,
        "width": WIDTH,
        "height": HEIGHT,
        "hands": configured,
        "occluded_hands": occluded_hands or [],
        "protected_regions": [
            {"label": "face", "rect": [62, 2, 8, 14]},
            {"label": "body", "rect": [62, 20, 8, 47]},
        ],
        **({} if skin_background is None else {"skin_background": skin_background}),
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_fixture(root: Path, *, png_data: bytes | None = None, sidecar_data: bytes | None = None):
    png_path = root / "views" / f"{VIEW_ID}.png"
    sidecar_path = root / "evidence" / f"{VIEW_ID}.hands.json"
    png_path.parent.mkdir()
    sidecar_path.parent.mkdir()
    png_bytes = png_data or png()
    sidecar_bytes = sidecar_data or sidecar()
    png_path.write_bytes(png_bytes)
    sidecar_path.write_bytes(sidecar_bytes)
    return HandAssetManifestEvidence(
        VIEW_ID, 0, f"views/{VIEW_ID}.png", f"evidence/{VIEW_ID}.hands.json",
        WIDTH, HEIGHT, hashlib.sha256(png_bytes).hexdigest(), hashlib.sha256(sidecar_bytes).hexdigest(),
    )


def assert_valid_evidence_is_release_compatible_and_deterministic() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root)
        first = build_hand_asset_evidence(root, manifest)
        second = build_hand_asset_evidence(root, manifest)
        root_text = str(root.resolve())
    assert first.passed
    assert first.to_json_bytes() == second.to_json_bytes()
    assert root_text.encode() not in first.to_json_bytes()
    assert "landmark" not in first.to_json_bytes().decode()


def assert_missing_digit_wrong_thumb_and_fusion_fail() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root, png_data=png(omit=("left", "pinky")))
        assert "hand_missing_digit" in build_hand_asset_evidence(root, manifest).problems
    wrong = [
        {
            "side": side,
            "roi": [8, 16, 54, 51] if side == "left" else [70, 16, 54, 51],
            "landmarks": [[point.x, point.y] for point in points(side)],
        }
        for side in ("left", "right")
    ]
    wrong[0]["landmarks"][4] = [20, wrong[0]["landmarks"][4][1]]
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root, sidecar_data=sidecar(hands=wrong))
        assert "hand_thumb_wrong_side" in build_hand_asset_evidence(root, manifest).problems
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root, png_data=png(fused=True))
        assert "hand_fused_digits" in build_hand_asset_evidence(root, manifest).problems


def assert_body_occlusion_is_explicit_without_inventing_hidden_landmarks() -> None:
    hidden = [{
        "side": "right",
        "status": "occluded",
        "occluder_id": "body",
        "reason": "right_hand_hidden_by_body",
        "region": [70, 20, 54, 47],
    }]
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        visible = [{
            "side": "left",
            "roi": [8, 16, 54, 51],
            "landmarks": [[point.x, point.y] for point in points("left")],
        }]
        manifest = write_fixture(
            root,
            png_data=png(omit_hand="right"),
            sidecar_data=sidecar(hands=visible, occluded_hands=hidden),
        )
        result = build_hand_asset_evidence(root, manifest)
    assert result.passed
    assert result.visible_sides == frozenset({"left"})
    assert result.occluded_sides == frozenset({"right"})
    assert "landmark" not in result.to_json_bytes().decode()


def assert_fully_occluded_hands_are_explicit_and_safe() -> None:
    hidden = [
        {
            "side": side,
            "status": "occluded",
            "occluder_id": "sleeve-and-body",
            "reason": "Both hands are hidden by the rear-facing sleeves.",
            "region": [8, 20, 116, 42],
        }
        for side in ("left", "right")
    ]
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(
            root,
            png_data=png(omit_hands=frozenset({"left", "right"})),
            sidecar_data=sidecar(hands=[], occluded_hands=hidden),
        )
        result = build_hand_asset_evidence(root, manifest)
    assert result.passed
    assert result.visible_sides == frozenset()
    assert result.occluded_sides == frozenset({"left", "right"})


def assert_hash_missing_hand_and_path_attacks_fail_closed() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root)
        wrong_hash = replace(manifest, png_sha256="0" * 64)
        assert build_hand_asset_evidence(root, wrong_hash).problems == ("png_hash_mismatch",)
        only_left = [{
            "side": "left",
            "roi": [8, 16, 54, 51],
            "landmarks": [[point.x, point.y] for point in points("left")],
        }]
        missing_sidecar = sidecar(hands=only_left)
        (root / manifest.sidecar_path).write_bytes(missing_sidecar)
        missing = replace(manifest, sidecar_sha256=hashlib.sha256(missing_sidecar).hexdigest())
        assert build_hand_asset_evidence(root, missing).problems == ("sidecar_invalid",)
        escaped = replace(manifest, png_path="../private.png")
        result = build_hand_asset_evidence(root, escaped)
        assert result.problems == ("asset_path_invalid",)
        assert str(root.resolve()) not in result.to_json_bytes().decode()


def assert_coordinate_range_and_sidecar_hash_are_enforced() -> None:
    hands = [
        {
            "side": side,
            "roi": [8, 16, 54, 51] if side == "left" else [70, 16, 54, 51],
            "landmarks": [[point.x, point.y] for point in points(side)],
        }
        for side in ("left", "right")
    ]
    hands[1]["landmarks"][8] = [WIDTH, 20]
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root, sidecar_data=sidecar(hands=hands))
        assert build_hand_asset_evidence(root, manifest).problems == ("sidecar_invalid",)
        assert build_hand_asset_evidence(root, replace(manifest, sidecar_sha256="f" * 64)).problems == ("sidecar_hash_mismatch",)


def assert_full_body_skin_and_roi_boundaries_are_isolated() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root, png_data=png(outside_fake_hand=True))
        result = build_hand_asset_evidence(root, manifest)
        assert result.passed
        assert "hand_extra_digit" not in result.problems
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root, png_data=png(inside_extra_finger=True))
        result = build_hand_asset_evidence(root, manifest)
        assert not result.passed
        assert "hand_extra_digit" in result.problems


def assert_missing_or_unsafe_roi_fails_closed() -> None:
    hands = [
        {
            "side": side,
            "roi": [8, 16, 54, 51] if side == "left" else [70, 16, 54, 51],
            "landmarks": [[point.x, point.y] for point in points(side)],
        }
        for side in ("left", "right")
    ]
    del hands[0]["roi"]
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root, sidecar_data=sidecar(hands=hands))
        assert build_hand_asset_evidence(root, manifest).problems == ("sidecar_invalid",)
    hands[0]["roi"] = [60, 0, 12, 20]
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root, sidecar_data=sidecar(hands=hands))
        assert build_hand_asset_evidence(root, manifest).problems == ("sidecar_invalid",)


def assert_skin_background_declaration_skips_extra_digit_and_reports_it() -> None:
    # 裸臂裸腿的素體：手部 ROI 內合法有皮膚。extra-digit 的皮膚啟發式是在長袖 v4 上
    # 校準的，對裸體 24 視角誤報 19 個。宣告後不跑該檢查，但必須列在 skipped_checks，
    # 其他檢查照跑，非布林宣告 fail closed，沒有宣告時行為與以前完全相同。
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(
            root,
            png_data=png(inside_extra_finger=True),
            sidecar_data=sidecar(skin_background=True),
        )
        result = build_hand_asset_evidence(root, manifest)
        assert result.passed
        assert "hand_extra_digit" not in result.problems
        assert result.skipped_checks == ("extra-digit:skin-background",)
        assert b'"skipped_checks":["extra-digit:skin-background"]' in result.to_json_bytes()
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(
            root, png_data=png(fused=True), sidecar_data=sidecar(skin_background=True)
        )
        result = build_hand_asset_evidence(root, manifest)
        assert not result.passed
        assert "hand_fused_digits" in result.problems
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root, sidecar_data=sidecar(skin_background="yes"))
        assert build_hand_asset_evidence(root, manifest).problems == ("sidecar_invalid",)
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root, png_data=png(inside_extra_finger=True))
        result = build_hand_asset_evidence(root, manifest)
        assert result.skipped_checks == ()
        assert "hand_extra_digit" in result.problems


def run() -> None:
    assert_valid_evidence_is_release_compatible_and_deterministic()
    assert_skin_background_declaration_skips_extra_digit_and_reports_it()
    assert_missing_digit_wrong_thumb_and_fusion_fail()
    assert_body_occlusion_is_explicit_without_inventing_hidden_landmarks()
    assert_fully_occluded_hands_are_explicit_and_safe()
    assert_hash_missing_hand_and_path_attacks_fail_closed()
    assert_coordinate_range_and_sidecar_hash_are_enforced()
    assert_full_body_skin_and_roi_boundaries_are_isolated()
    assert_missing_or_unsafe_roi_fails_closed()
    print("HAND_ASSET_EVIDENCE_OK")


if __name__ == "__main__":
    run()
