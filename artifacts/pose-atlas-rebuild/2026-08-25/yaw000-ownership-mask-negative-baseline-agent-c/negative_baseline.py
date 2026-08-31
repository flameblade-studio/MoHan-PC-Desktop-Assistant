from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
ATLAS = ROOT / "assets" / "pose-atlas" / "v4-layered"
PREVIOUS_GATE = (
    ROOT / "artifacts" / "pose-atlas-rebuild" / "2026-08-25"
    / "three-domain-promotion-gate-agent-c" / "yaw000-promotion-gate-result.json"
)
VIEW = "yaw+000-pitch+00"
SIZE = (1024, 1536)
Z_ORDER = [
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
]
DOMAINS = {
    "human_core": [
        "base", "jaw", "oral_cavity", "teeth_tongue", "lip_lower", "lip_upper",
        "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
        "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left",
        "eyeliner_right", "brow_left", "brow_right",
    ],
    "garment_dlc": ["body", "sleeve_left", "sleeve_right"],
    "hair_ornament": ["hair_back", "hair_left", "hair_right", "ornament"],
}
DOMAIN_RECOMPOSE_ORDER = ["garment_dlc", "human_core", "hair_ornament"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def alpha_union(images: list[Image.Image]) -> Image.Image:
    result = Image.new("L", SIZE, 0)
    for image in images:
        binary = image.getchannel("A").point(lambda value: 255 if value else 0)
        result = ImageChops.lighter(result, binary)
    return result


def alpha_composite(images: list[Image.Image]) -> Image.Image:
    result = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    for image in images:
        result.alpha_composite(image)
    return result


def count_nonzero(mask: Image.Image) -> int:
    return sum(1 for value in mask.getdata() if value)


def diff_stats(left: Image.Image, right: Image.Image) -> tuple[int, int]:
    difference = ImageChops.difference(left, right)
    pixels = difference.getdata()
    changed = 0
    maximum = 0
    for pixel in pixels:
        pixel_max = max(pixel)
        if pixel_max:
            changed += 1
            maximum = max(maximum, pixel_max)
    return changed, maximum


def checker(image: Image.Image) -> Image.Image:
    background = Image.new("RGB", SIZE, (45, 45, 45))
    block = 64
    draw = ImageDraw.Draw(background)
    for y in range(0, SIZE[1], block):
        for x in range(0, SIZE[0], block):
            if (x // block + y // block) % 2:
                draw.rectangle((x, y, x + block - 1, y + block - 1), fill=(72, 72, 72))
    background.paste(image, mask=image.getchannel("A"))
    return background


def main() -> int:
    output = Path.cwd()
    images: dict[str, Image.Image] = {}
    sources = []
    for layer in Z_ORDER:
        path = ATLAS / f"{VIEW}_{layer}.png"
        with Image.open(path) as opened:
            if opened.mode != "RGBA" or opened.size != SIZE:
                raise ValueError(f"invalid source {path}: {opened.mode} {opened.size}")
            images[layer] = opened.copy()
        sources.append({"layer": layer, "path": str(path), "sha256": sha256(path)})

    target = alpha_composite([images[layer] for layer in Z_ORDER])
    domain_images: dict[str, Image.Image] = {}
    domain_masks: dict[str, Image.Image] = {}
    mask_records = {}
    for domain, layers in DOMAINS.items():
        ordered = [images[layer] for layer in Z_ORDER if layer in layers]
        domain_images[domain] = alpha_composite(ordered)
        domain_masks[domain] = alpha_union(ordered)
        mask_path = output / f"{VIEW}_{domain}_legacy-union-mask.png"
        domain_masks[domain].save(mask_path)
        mask_records[domain] = {
            "layers": layers,
            "mask_path": str(mask_path),
            "mask_sha256": sha256(mask_path),
            "owned_pixels": count_nonzero(domain_masks[domain]),
        }

    target_mask = target.getchannel("A").point(lambda value: 255 if value else 0)
    raw_masks = [domain_masks[name] for name in DOMAINS]
    target_data = bytes(target_mask.getdata())
    mask_data = [bytes(mask.getdata()) for mask in raw_masks]
    overlap_pixels = 0
    uncovered_target_pixels = 0
    owned_outside_target_pixels = 0
    overlap_visual = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    overlap_pixels_rgba = bytearray(SIZE[0] * SIZE[1] * 4)
    for index, target_value in enumerate(target_data):
        owner_count = sum(1 for data in mask_data if data[index])
        if owner_count > 1:
            overlap_pixels += 1
            start = index * 4
            overlap_pixels_rgba[start:start + 4] = bytes((255, 0, 255, 255))
        if target_value and owner_count == 0:
            uncovered_target_pixels += 1
        if not target_value and owner_count:
            owned_outside_target_pixels += 1
    overlap_visual.frombytes(bytes(overlap_pixels_rgba))

    grouped = alpha_composite([domain_images[name] for name in DOMAIN_RECOMPOSE_ORDER])
    changed_pixels, max_error = diff_stats(target, grouped)
    diff = ImageChops.difference(target, grouped)
    enhanced_diff = diff.point(lambda value: min(255, value * 4))

    target_path = output / f"{VIEW}_legacy-25layer-target.png"
    grouped_path = output / f"{VIEW}_three-domain-grouped-recomposition.png"
    diff_path = output / f"{VIEW}_exact-diff-x4.png"
    overlap_path = output / f"{VIEW}_raw-domain-overlap.png"
    target.save(target_path)
    grouped.save(grouped_path)
    enhanced_diff.save(diff_path)
    overlap_visual.save(overlap_path)

    mask_rgb = Image.merge(
        "RGB",
        (domain_masks["human_core"], domain_masks["garment_dlc"], domain_masks["hair_ornament"]),
    )
    panels = [checker(target), checker(grouped), checker(enhanced_diff), checker(overlap_visual), mask_rgb]
    titles = [
        "legacy 25-layer target", "grouped 3-domain recomposition", "exact diff x4",
        "raw mask overlaps", "mask RGB: core/garment/hair",
    ]
    board = Image.new("RGB", (5 * 280, 445), (28, 31, 35))
    draw = ImageDraw.Draw(board)
    for index, (panel, title) in enumerate(zip(panels, titles)):
        thumb = panel.resize((256, 384), Image.Resampling.LANCZOS)
        x = index * 280 + 12
        board.paste(thumb, (x, 34))
        draw.text((x, 10), title, fill=(235, 235, 235))
    draw.text((12, 425), "NEGATIVE BASELINE: mathematical masks do not prove semantic ownership", fill=(255, 110, 90))
    board_path = output / "yaw000-ownership-mask-negative-baseline-board.png"
    board.save(board_path)

    previous = json.loads(PREVIOUS_GATE.read_text(encoding="utf-8"))
    report = {
        "schema": "mohan.pose_atlas.ownership_mask_negative_baseline.v1",
        "view_id": VIEW,
        "status": "FAIL_NEGATIVE_BASELINE",
        "promotion_allowed": False,
        "truth_boundary": (
            "These masks are unions of legacy layer alpha, not verified semantic ownership masks. "
            "A mathematical coverage result cannot override known cross-domain content."
        ),
        "domain_layer_mapping": DOMAINS,
        "domain_recomposition_order": DOMAIN_RECOMPOSE_ORDER,
        "source_layers": sources,
        "mask_records": mask_records,
        "metrics": {
            "target_visible_pixels": count_nonzero(target_mask),
            "raw_domain_overlap_pixels": overlap_pixels,
            "uncovered_target_pixels": uncovered_target_pixels,
            "owned_outside_target_pixels": owned_outside_target_pixels,
            "grouped_recomposition_changed_pixels": changed_pixels,
            "grouped_recomposition_max_channel_error": max_error,
        },
        "technical_gates": {
            "full_canvas_masks": True,
            "mutually_exclusive": overlap_pixels == 0,
            "complete_visible_coverage": uncovered_target_pixels == 0,
            "no_owned_pixels_outside_target": owned_outside_target_pixels == 0,
            "exact_rgba_recomposition": changed_pixels == 0 and max_error == 0,
        },
        "semantic_gate": {
            "status": "FAIL",
            "previous_gate_path": str(PREVIOUS_GATE),
            "previous_gate_sha256": sha256(PREVIOUS_GATE),
            "known_cross_domain_violations": previous["violations"],
        },
        "artifacts": {
            "target": {"path": str(target_path), "sha256": sha256(target_path)},
            "grouped": {"path": str(grouped_path), "sha256": sha256(grouped_path)},
            "diff": {"path": str(diff_path), "sha256": sha256(diff_path)},
            "overlap": {"path": str(overlap_path), "sha256": sha256(overlap_path)},
            "board": {"path": str(board_path), "sha256": sha256(board_path)},
        },
        "required_resolution": [
            "replace legacy alpha unions with verified semantic ownership masks",
            "supply clean human core independent of all garments",
            "split hands from sleeves and shoes from body",
            "remove face/skin from fixed ornament",
            "preserve original cross-domain z-order or prove exact RGBA equivalence",
        ],
    }
    report_path = output / "yaw000-ownership-mask-negative-baseline.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], **report["metrics"], "promotion_allowed": False}))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
