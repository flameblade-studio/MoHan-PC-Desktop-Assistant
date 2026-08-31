"""Deterministic RGB-only decontamination for conservative low-alpha outer edges."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
PYPNG = (
    PROJECT
    / "artifacts/pose-atlas-rebuild/2026-08-25/third-party-notices-candidate"
    / "pypng-smoke-agent-c/extracted"
)
sys.path.insert(0, str(PYPNG))
import png  # type: ignore


VIEW = "yaw-015-pitch+00.geometry-mother-c044"
SOURCE = HERE / f"{VIEW}.birefnet-rgba.png"
OUTPUT = HERE / f"{VIEW}.low-alpha-rgb-decontaminated-v1.png"
MASK = HERE / f"{VIEW}.low-alpha-rgb-decontaminated-v1.changed-mask.png"
REPORT = HERE / "decontamination-qa.json"
ALPHA_MAX = 64
SEED_ALPHA_MIN = 160
SEARCH_RADIUS = 12

# Inclusive-exclusive rectangles. Face center is deliberately absent.
ROIS = {
    "ornament_top": (380, 65, 660, 195),
    "hair_left_outer": (350, 120, 475, 680),
    "hair_right_outer": (565, 120, 665, 680),
    "sleeve_left": (240, 300, 475, 1040),
    "sleeve_right": (590, 300, 795, 1040),
    "skirt": (235, 820, 775, 1420),
    "shoes": (395, 1340, 675, 1490),
}
FACE_PROTECTED = (465, 145, 595, 365)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_rgba(path: Path) -> tuple[int, int, list[bytearray]]:
    width, height, rows, metadata = png.Reader(filename=str(path)).asRGBA8()
    if metadata["planes"] != 4 or metadata["bitdepth"] != 8:
        raise ValueError("RGBA8 required")
    return width, height, [bytearray(row) for row in rows]


def inside(rect: tuple[int, int, int, int], x: int, y: int) -> bool:
    left, top, right, bottom = rect
    return left <= x < right and top <= y < bottom


def roi_name(x: int, y: int) -> str | None:
    for name, rect in ROIS.items():
        if inside(rect, x, y):
            return name
    return None


def alpha(rows: list[bytearray], x: int, y: int) -> int:
    return rows[y][x * 4 + 3]


def touches_transparency(rows: list[bytearray], width: int, height: int, x: int, y: int) -> bool:
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and alpha(rows, nx, ny) == 0:
                return True
    return False


def nearest_seed(rows: list[bytearray], width: int, height: int, x: int, y: int) -> tuple[int, int, int] | None:
    best: tuple[int, int, int, int, int] | None = None
    for radius in range(1, SEARCH_RADIUS + 1):
        candidates: list[tuple[int, int, int, int, int]] = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                nx, ny = x + dx, y + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    continue
                seed_alpha = alpha(rows, nx, ny)
                if seed_alpha < SEED_ALPHA_MIN:
                    continue
                offset = nx * 4
                distance_sq = dx * dx + dy * dy
                # Tie break is deterministic: distance, higher alpha, y, x.
                candidates.append((distance_sq, -seed_alpha, ny, nx, offset))
        if candidates:
            best = min(candidates)
            break
    if best is None:
        return None
    _, _, seed_y, _, offset = best
    return tuple(rows[seed_y][offset : offset + 3])  # type: ignore[return-value]


def write_rgba(path: Path, width: int, height: int, rows: list[bytearray]) -> None:
    with path.open("wb") as stream:
        png.Writer(width, height, greyscale=False, alpha=True, bitdepth=8).write(stream, rows)


def write_mask(path: Path, width: int, height: int, changed: set[tuple[int, int]]) -> None:
    rows: list[bytearray] = []
    for y in range(height):
        row = bytearray(width)
        for x in range(width):
            row[x] = 255 if (x, y) in changed else 0
        rows.append(row)
    with path.open("wb") as stream:
        png.Writer(width, height, greyscale=True, alpha=False, bitdepth=8).write(stream, rows)


def write_composite(path: Path, rows: list[bytearray], width: int, height: int, background: tuple[int, int, int]) -> None:
    output_rows: list[bytearray] = []
    for row in rows:
        output = bytearray(width * 3)
        for x in range(width):
            offset = x * 4
            pixel_alpha = row[offset + 3]
            inverse = 255 - pixel_alpha
            for channel in range(3):
                output[x * 3 + channel] = (row[offset + channel] * pixel_alpha + background[channel] * inverse + 127) // 255
        output_rows.append(output)
    with path.open("wb") as stream:
        png.Writer(width, height, greyscale=False, alpha=False, bitdepth=8).write(stream, output_rows)


def main() -> int:
    width, height, source = read_rgba(SOURCE)
    output = [bytearray(row) for row in source]
    changed: set[tuple[int, int]] = set()
    changed_by_roi = {name: 0 for name in ROIS}
    skipped_no_seed = 0
    max_rgb_delta = 0
    changed_alpha_values: list[int] = []

    for y in range(height):
        for x in range(width):
            name = roi_name(x, y)
            if name is None or inside(FACE_PROTECTED, x, y):
                continue
            pixel_alpha = alpha(source, x, y)
            if not (1 <= pixel_alpha <= ALPHA_MAX):
                continue
            if not touches_transparency(source, width, height, x, y):
                continue
            seed = nearest_seed(source, width, height, x, y)
            if seed is None:
                skipped_no_seed += 1
                continue
            offset = x * 4
            before = tuple(source[y][offset : offset + 3])
            if before == seed:
                continue
            output[y][offset : offset + 3] = bytes(seed)
            changed.add((x, y))
            changed_by_roi[name] += 1
            changed_alpha_values.append(pixel_alpha)
            max_rgb_delta = max(max_rgb_delta, *(abs(before[channel] - seed[channel]) for channel in range(3)))

    write_rgba(OUTPUT, width, height, output)
    write_mask(MASK, width, height, changed)
    previews: dict[str, Path] = {}
    for name, color in {"black": (0, 0, 0), "green": (0, 255, 0), "magenta": (255, 0, 255)}.items():
        path = HERE / f"{VIEW}.low-alpha-rgb-decontaminated-v1.preview-{name}.png"
        write_composite(path, output, width, height, color)
        previews[name] = path

    output_width, output_height, reread = read_rgba(OUTPUT)
    changed_pixels_verified = 0
    alpha_changed_pixels = 0
    changed_outside_roi = 0
    changed_face_pixels = 0
    changed_above_alpha_limit = 0
    transparent_rgb_nonzero = 0
    for y in range(height):
        for x in range(width):
            offset = x * 4
            before = source[y][offset : offset + 4]
            after = reread[y][offset : offset + 4]
            if before[3] != after[3]:
                alpha_changed_pixels += 1
            if before != after:
                changed_pixels_verified += 1
                if roi_name(x, y) is None:
                    changed_outside_roi += 1
                if inside(FACE_PROTECTED, x, y):
                    changed_face_pixels += 1
                if before[3] > ALPHA_MAX:
                    changed_above_alpha_limit += 1
            if after[3] == 0 and any(after[:3]):
                transparent_rgb_nonzero += 1

    gates = {
        "dimensions_preserved": [output_width, output_height] == [width, height] == [1024, 1536],
        "changed_pixels_nonzero": changed_pixels_verified > 0,
        "all_changes_accounted": changed_pixels_verified == len(changed),
        "alpha_byte_exact": alpha_changed_pixels == 0,
        "no_changes_outside_rois": changed_outside_roi == 0,
        "face_byte_exact": changed_face_pixels == 0,
        "visible_main_body_rgb_exact": changed_above_alpha_limit == 0,
        "transparent_rgb_zero": transparent_rgb_nonzero == 0,
        "hair_and_shoes_not_cut": alpha_changed_pixels == 0,
    }
    result = {
        "schema": "mohan.pose-atlas.low-alpha-rgb-decontamination.v1",
        "source": str(SOURCE),
        "source_sha256": sha256(SOURCE),
        "output": str(OUTPUT),
        "output_sha256": sha256(OUTPUT),
        "changed_mask": str(MASK),
        "changed_mask_sha256": sha256(MASK),
        "algorithm": {
            "alpha_range_changed_rgb_only": [1, ALPHA_MAX],
            "outer_edge_requires_alpha_zero_within_chebyshev_radius": 2,
            "nearest_seed_alpha_min": SEED_ALPHA_MIN,
            "nearest_seed_search_radius": SEARCH_RADIUS,
            "alpha_modification_allowed": False,
            "face_protected_xyxy": list(FACE_PROTECTED),
            "rois_xyxy": {name: list(rect) for name, rect in ROIS.items()},
        },
        "changed_pixels": changed_pixels_verified,
        "changed_pixels_by_roi": changed_by_roi,
        "changed_alpha_range": [min(changed_alpha_values), max(changed_alpha_values)] if changed_alpha_values else None,
        "max_rgb_channel_delta": max_rgb_delta,
        "max_alpha_delta": 0,
        "skipped_no_seed": skipped_no_seed,
        "alpha_changed_pixels": alpha_changed_pixels,
        "changed_outside_roi": changed_outside_roi,
        "changed_face_pixels": changed_face_pixels,
        "changed_above_alpha_limit": changed_above_alpha_limit,
        "transparent_rgb_nonzero_pixels": transparent_rgb_nonzero,
        "previews": {name: {"path": str(path), "sha256": sha256(path)} for name, path in previews.items()},
        "gates": gates,
        "technical_exit_code": 0 if all(gates.values()) else 4,
        "manual_visual_gate": "PENDING",
        "formal_asset_gate": "NOT_RUN",
    }
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["technical_exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
