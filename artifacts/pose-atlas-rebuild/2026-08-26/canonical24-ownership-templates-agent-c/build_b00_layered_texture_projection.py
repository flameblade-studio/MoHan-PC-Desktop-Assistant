#!/usr/bin/env python3
"""Project separated B00 appearance domains into a target-view geometry mask.

This intentionally does not project anatomy/face pixels.  Outfit, hair and
ornament use separate target masks, and uncertain or excessive-stretch pixels
are emitted as a repair mask for a later local inpaint pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageFilter


CANVAS = (1024, 1536)
DOMAINS = ("anatomy", "outfit", "hair", "ornament")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_rgba(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGBA")
    if image.size != CANVAS:
        raise ValueError(f"expected {CANVAS}, got {image.size}: {path}")
    return np.asarray(image, dtype=np.uint8)


def alpha_mask(path: Path) -> np.ndarray:
    return load_rgba(path)[:, :, 3] > 0


def merge_rgba(paths: list[Path]) -> np.ndarray:
    canvas = np.zeros((CANVAS[1], CANVAS[0], 4), dtype=np.uint8)
    for path in paths:
        layer = load_rgba(path)
        take = layer[:, :, 3] > 0
        canvas[take] = layer[take]
    return canvas


def appearance_mask(image: np.ndarray, mode: str) -> np.ndarray:
    rgb = image[:, :, :3].astype(np.int16)
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    high = rgb.max(axis=2)
    low = rgb.min(axis=2)
    chroma = high - low
    visible = image[:, :, 3] > 0
    skin = visible & (red > 92) & (red > green + 8) & (green > blue + 5)
    hair = visible & (high < 105) & (chroma < 58)
    yy = np.arange(CANVAS[1])[:, None]
    blue_cloth = visible & (blue > red + 12) & (blue >= green - 3)
    white_cloth = visible & (low > 145) & (chroma < 52) & (yy > 250)
    if mode == "anatomy":
        return skin
    if mode == "hair":
        return hair & (yy < 1050)
    if mode == "outfit":
        return (blue_cloth | white_cloth) & ~skin & ~hair
    raise ValueError(f"unknown appearance mask mode: {mode}")


def apply_mask(
    image: np.ndarray, mask_path: Path | None, mask_mode: str | None = None
) -> np.ndarray:
    if mask_mode:
        mask = appearance_mask(image, mask_mode)
    elif mask_path is not None:
        mask = alpha_mask(mask_path)
    else:
        return image
    output = image.copy()
    output[~mask] = 0
    output[:, :, 3] = np.where(mask, output[:, :, 3], 0)
    return output


def bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        raise ValueError("empty ownership mask")
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def row_span(mask: np.ndarray, y: int) -> tuple[int, int] | None:
    xs = np.flatnonzero(mask[y])
    if len(xs) == 0:
        return None
    return int(xs[0]), int(xs[-1])


def nearest_nonempty_row(mask: np.ndarray, y: int, low: int, high: int) -> int | None:
    if row_span(mask, y) is not None:
        return y
    for distance in range(1, max(y - low, high - y) + 1):
        for candidate in (y - distance, y + distance):
            if low <= candidate <= high and row_span(mask, candidate) is not None:
                return candidate
    return None


def project_domain(
    source: np.ndarray,
    target_mask: np.ndarray,
    *,
    max_horizontal_stretch: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    source_mask = source[:, :, 3] > 0
    sx0, sy0, sx1, sy1 = bbox(source_mask)
    tx0, ty0, tx1, ty1 = bbox(target_mask)
    output = np.zeros_like(source)
    repair = np.zeros(target_mask.shape, dtype=bool)
    target_height = max(1, ty1 - ty0)
    source_height = max(1, sy1 - sy0)

    for target_y in range(ty0, ty1 + 1):
        target_span = row_span(target_mask, target_y)
        if target_span is None:
            continue
        relative_y = (target_y - ty0) / target_height
        requested_source_y = int(round(sy0 + relative_y * source_height))
        source_y = nearest_nonempty_row(source_mask, requested_source_y, sy0, sy1)
        if source_y is None:
            repair[target_y, target_mask[target_y]] = True
            continue
        source_span = row_span(source_mask, source_y)
        assert source_span is not None
        source_left, source_right = source_span
        target_left, target_right = target_span
        source_width = max(1, source_right - source_left)
        target_width = max(1, target_right - target_left)
        horizontal_stretch = target_width / source_width
        xs = np.flatnonzero(target_mask[target_y])
        source_xs = np.rint(
            source_left + ((xs - target_left) / target_width) * source_width
        ).astype(np.int32)
        source_xs = np.clip(source_xs, source_left, source_right)
        sampled = source[source_y, source_xs]
        valid = sampled[:, 3] > 0
        output[target_y, xs[valid]] = sampled[valid]
        output[target_y, xs[valid], 3] = 255
        invalid_xs = xs[~valid]
        repair[target_y, invalid_xs] = True
        if horizontal_stretch > max_horizontal_stretch:
            repair[target_y, xs] = True

    repair |= target_mask & (output[:, :, 3] == 0)
    stats = {
        "source_bbox": [sx0, sy0, sx1, sy1],
        "target_bbox": [tx0, ty0, tx1, ty1],
        "source_pixels": int(source_mask.sum()),
        "target_pixels": int(target_mask.sum()),
        "projected_pixels": int((output[:, :, 3] > 0).sum()),
        "repair_pixels": int(repair.sum()),
    }
    return output, repair, stats


def project_domain_multi(
    sources: list[tuple[str, int, np.ndarray]],
    target_mask: np.ndarray,
    visibility_mask: np.ndarray,
    domain: str,
    target_yaw: int,
    max_horizontal_stretch: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    output = np.zeros((CANVAS[1], CANVAS[0], 4), dtype=np.uint8)
    source_map = np.zeros((CANVAS[1], CANVAS[0], 4), dtype=np.uint8)
    repair = target_mask.copy()
    source_stats: list[dict[str, object]] = []
    colors = ((255, 64, 64, 255), (64, 255, 64, 255), (64, 128, 255, 255))
    ranked = sorted(sources, key=lambda item: abs(target_yaw - item[1]))
    for index, (source_id, source_yaw, source) in enumerate(ranked):
        difference = abs(target_yaw - source_yaw)
        if difference > 45:
            continue
        source_mask = source[:, :, 3] > 0
        if domain in {"anatomy", "ornament"}:
            accepted = np.zeros_like(target_mask)
            source_labels_count, source_labels, source_stats_cv, source_centres = cv2.connectedComponentsWithStats(
                source_mask.astype(np.uint8), 8
            )
            target_labels_count, target_labels, target_stats_cv, target_centres = cv2.connectedComponentsWithStats(
                target_mask.astype(np.uint8), 8
            )
            source_components = [
                label for label in range(1, source_labels_count)
                if source_stats_cv[label, cv2.CC_STAT_AREA] >= 6
            ]
            target_components = [
                label for label in range(1, target_labels_count)
                if target_stats_cv[label, cv2.CC_STAT_AREA] >= 6
            ]
            unused = set(source_components)
            for target_label in sorted(
                target_components,
                key=lambda value: target_stats_cv[value, cv2.CC_STAT_AREA],
                reverse=True,
            ):
                if not unused:
                    break
                target_area = float(target_stats_cv[target_label, cv2.CC_STAT_AREA])
                target_centre = target_centres[target_label]
                source_label = min(
                    unused,
                    key=lambda value: (
                        abs(source_centres[value][1] - target_centre[1]) / CANVAS[1]
                        + 0.35 * abs(
                            np.log((source_stats_cv[value, cv2.CC_STAT_AREA] + 1) / (target_area + 1))
                        )
                    ),
                )
                unused.remove(source_label)
                shift_x = int(round(target_centre[0] - source_centres[source_label][0]))
                shift_y = int(round(target_centre[1] - source_centres[source_label][1]))
                component_source = np.zeros_like(source)
                component_source[source_labels == source_label] = source[source_labels == source_label]
                shifted = np.zeros_like(source)
                sy0c, sy1c = max(0, -shift_y), min(CANVAS[1], CANVAS[1] - shift_y)
                sx0c, sx1c = max(0, -shift_x), min(CANVAS[0], CANVAS[0] - shift_x)
                shifted[sy0c + shift_y:sy1c + shift_y, sx0c + shift_x:sx1c + shift_x] = component_source[
                    sy0c:sy1c, sx0c:sx1c
                ]
                target_component = target_labels == target_label
                trusted_component = (
                    target_component & visibility_mask & (shifted[:, :, 3] > 0)
                    & (output[:, :, 3] == 0)
                )
                output[trusted_component] = shifted[trusted_component]
                source_map[trusted_component] = colors[index % len(colors)]
                repair[trusted_component] = False
                accepted |= trusted_component
            source_stats.append({
                "source_id": source_id,
                "source_yaw": source_yaw,
                "angular_difference": abs(target_yaw - source_yaw),
                "transform": "connected_component_translation_only",
                "source_components": len(source_components),
                "target_components": len(target_components),
                "accepted_pixels": int(accepted.sum()),
                "source_map_rgba": list(colors[index % len(colors)]),
            })
            continue
        sx0, sy0, sx1, sy1 = bbox(source_mask)
        tx0, ty0, tx1, ty1 = bbox(target_mask)
        # The source canvases are registered full-body views.  Preserve their
        # real pixels and only translate their ownership bbox onto the target
        # bbox.  Scaling a whole view (the old path) duplicated faces, shoes
        # and sleeves and is intentionally forbidden here.
        source_centre_x = (sx0 + sx1) // 2
        target_centre_x = (tx0 + tx1) // 2
        shift_x = target_centre_x - source_centre_x
        if domain == "outfit":
            shift_y = ty1 - sy1
        elif domain == "hair":
            shift_y = ty0 - sy0
        else:
            shift_y = ((ty0 + ty1) // 2) - ((sy0 + sy1) // 2)
        projected = np.zeros_like(output)
        source_y0 = max(0, -shift_y)
        source_y1 = min(CANVAS[1], CANVAS[1] - shift_y)
        source_x0 = max(0, -shift_x)
        source_x1 = min(CANVAS[0], CANVAS[0] - shift_x)
        target_y0 = source_y0 + shift_y
        target_y1 = source_y1 + shift_y
        target_x0 = source_x0 + shift_x
        target_x1 = source_x1 + shift_x
        projected[target_y0:target_y1, target_x0:target_x1] = source[
            source_y0:source_y1, source_x0:source_x1
        ]
        projected[~target_mask] = 0
        uncertain = target_mask & (
            (projected[:, :, 3] == 0) | ~visibility_mask
        )
        stats = {
            "source_bbox": [sx0, sy0, sx1, sy1],
            "target_bbox": [tx0, ty0, tx1, ty1],
            "source_pixels": int(source_mask.sum()),
            "target_pixels": int(target_mask.sum()),
            "transform": "registered_canvas_translation_only",
            "shift_xy": [shift_x, shift_y],
            "horizontal_scale": 1.0,
            "vertical_scale": 1.0,
        }
        # Only use the central overlap band.  Side pixels with no observed
        # source angle remain explicitly missing instead of being extrapolated.
        coverage_fraction = max(0.35, 1.0 - difference / 90.0)
        x0, _, x1, _ = bbox(target_mask)
        centre = (x0 + x1) / 2.0
        half_width = max(1.0, (x1 - x0) * coverage_fraction / 2.0)
        columns = np.arange(CANVAS[0])[None, :]
        trusted_band = np.abs(columns - centre) <= half_width
        trusted = (
            target_mask
            & trusted_band
            & visibility_mask
            & ~uncertain
            & (projected[:, :, 3] > 0)
            & (output[:, :, 3] == 0)
        )
        output[trusted] = projected[trusted]
        source_map[trusted] = colors[index % len(colors)]
        repair[trusted] = False
        stats.update(
            {
                "source_id": source_id,
                "source_yaw": source_yaw,
                "angular_difference": difference,
                "trusted_coverage_fraction": coverage_fraction,
                "accepted_pixels": int(trusted.sum()),
                "source_map_rgba": list(colors[index % len(colors)]),
            }
        )
        source_stats.append(stats)
    return output, repair, source_map, {"sources": source_stats}


def save_rgba(array: np.ndarray, path: Path) -> None:
    Image.fromarray(array, "RGBA").save(path)


def save_mask(mask: np.ndarray, path: Path) -> None:
    rgba = np.zeros((CANVAS[1], CANVAS[0], 4), dtype=np.uint8)
    rgba[mask] = (255, 255, 255, 255)
    save_rgba(rgba, path)


def dilate_mask(mask: np.ndarray, radius: int = 2) -> np.ndarray:
    size = radius * 2 + 1
    image = Image.fromarray((mask.astype(np.uint8) * 255), "L")
    return np.asarray(image.filter(ImageFilter.MaxFilter(size))) > 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-spec-json", type=Path, required=True)
    parser.add_argument("--target-outfit-mask", type=Path, required=True)
    parser.add_argument("--target-anatomy-mask", type=Path, required=True)
    parser.add_argument("--target-hair-mask", type=Path, required=True)
    parser.add_argument("--target-ornament-mask", type=Path, required=True)
    parser.add_argument("--target-depth", type=Path, required=True)
    parser.add_argument("--target-normal", type=Path, required=True)
    parser.add_argument("--target-softedge", type=Path, required=True)
    parser.add_argument("--target-part-id", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--view-id", default="yaw+045-pitch+00")
    parser.add_argument("--target-yaw", type=int, default=45)
    parser.add_argument("--max-horizontal-stretch", type=float, default=1.65)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=False)
    source_spec = json.loads(args.source_spec_json.read_text(encoding="utf-8"))
    sources: dict[str, list[tuple[str, int, np.ndarray]]] = {domain: [] for domain in DOMAINS}
    source_legend: dict[str, object] = {}
    for entry in source_spec["sources"]:
        source_id = str(entry["source_id"])
        source_yaw = int(entry["yaw"])
        source_legend[source_id] = {"yaw": source_yaw, "domains": sorted(entry["domains"])}
        for domain, domain_spec in entry["domains"].items():
            if domain not in DOMAINS:
                continue
            if "layers" in domain_spec:
                image = merge_rgba([Path(value) for value in domain_spec["layers"]])
            else:
                image = load_rgba(Path(domain_spec["image"]))
            mask_value = domain_spec.get("mask")
            image = apply_mask(
                image,
                Path(mask_value) if mask_value else None,
                domain_spec.get("mask_mode"),
            )
            sources[domain].append((source_id, source_yaw, image))
    for domain in DOMAINS:
        if not sources[domain]:
            raise ValueError(f"no sources for domain: {domain}")
    target_masks = {
        "anatomy": alpha_mask(args.target_anatomy_mask),
        "outfit": alpha_mask(args.target_outfit_mask),
        "hair": alpha_mask(args.target_hair_mask),
        "ornament": alpha_mask(args.target_ornament_mask),
    }
    overlap = np.zeros((CANVAS[1], CANVAS[0]), dtype=bool)
    for index, left in enumerate(DOMAINS):
        for right in DOMAINS[index + 1 :]:
            overlap |= target_masks[left] & target_masks[right]
    if np.any(overlap):
        raise ValueError(f"target ownership overlap: {int(overlap.sum())} pixels")

    depth_image = np.asarray(Image.open(args.target_depth).convert("L"), dtype=np.uint8)
    normal_image = np.asarray(Image.open(args.target_normal).convert("RGB"), dtype=np.uint8)
    # Both maps were rendered with front-face culling and a per-pixel z-buffer.
    # Requiring a valid sample in each map is a conservative visibility gate;
    # it never creates coverage where geometry has no observed front surface.
    visibility_mask = (depth_image > 0) & np.any(normal_image > 0, axis=2)
    visibility_path = args.output_dir / f"{args.view_id}_front-surface-confidence-mask.png"
    save_mask(visibility_mask, visibility_path)

    outputs: dict[str, str] = {}
    statistics: dict[str, object] = {}
    combined = np.zeros((CANVAS[1], CANVAS[0], 4), dtype=np.uint8)
    combined_repair = np.zeros((CANVAS[1], CANVAS[0]), dtype=bool)
    for domain in DOMAINS:
        projected, repair, source_map, stats = project_domain_multi(
            sources[domain],
            target_masks[domain],
            visibility_mask,
            domain,
            target_yaw=args.target_yaw,
            max_horizontal_stretch=args.max_horizontal_stretch,
        )
        # Two-pixel seam halo is kept in the repair mask for later local fill.
        # No RGB is blurred across anatomy/outfit/hair/ornament boundaries.
        repair = dilate_mask(repair, radius=2) & target_masks[domain]
        projected_path = args.output_dir / f"{args.view_id}_{domain}-projected-rgba.png"
        repair_path = args.output_dir / f"{args.view_id}_{domain}-repair-mask.png"
        save_rgba(projected, projected_path)
        save_mask(repair, repair_path)
        source_map_path = args.output_dir / f"{args.view_id}_{domain}-source-map.png"
        save_rgba(source_map, source_map_path)
        take = projected[:, :, 3] > 0
        combined[take] = projected[take]
        combined_repair |= repair
        outputs[f"{domain}_projected"] = str(projected_path.resolve())
        outputs[f"{domain}_repair_mask"] = str(repair_path.resolve())
        outputs[f"{domain}_source_map"] = str(source_map_path.resolve())
        statistics[domain] = stats

    combined_path = args.output_dir / f"{args.view_id}_layered-texture-projection-rgba.png"
    repair_path = args.output_dir / f"{args.view_id}_combined-repair-mask.png"
    save_rgba(combined, combined_path)
    save_mask(combined_repair, repair_path)
    outputs["combined_projection"] = str(combined_path.resolve())
    outputs["combined_repair_mask"] = str(repair_path.resolve())
    outputs["front_surface_confidence_mask"] = str(visibility_path.resolve())

    geometry = {
        "depth": args.target_depth,
        "normal": args.target_normal,
        "softedge": args.target_softedge,
        "part_id": args.target_part_id,
    }
    for label, source_path in geometry.items():
        with Image.open(source_path) as image:
            if image.size != CANVAS:
                raise ValueError(f"{label} size {image.size}, expected {CANVAS}")

    job_path = args.output_dir / f"{args.view_id}.layered-texture-projection-job.json"
    job = {
        "schema": "mohan.stage-a.layered-texture-projection-job.v1",
        "view_id": args.view_id,
        "accepted": False,
        "formal": False,
        "reference_view_id": "yaw+000-pitch+00",
        "source_legend": source_legend,
        "appearance_domains": outputs,
        "geometry": {key: str(value.resolve()) for key, value in geometry.items()},
        "ownership": {
            "domains": list(DOMAINS),
            "target_overlap_pixels": 0,
            "anatomy_is_separate": True,
        },
        "statistics": statistics,
        "policy": {
            "projection_is_guidance_only": True,
            "repair_mask_requires_local_fill": True,
            "do_not_redraw_unmasked_outfit": True,
            "do_not_promote_without_owner_review": True,
            "no_rgb_scaling_or_extrapolation": True,
            "seam_repair_dilation_pixels": 2,
        },
    }
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    hashes = {str(path): sha256(Path(path)) for path in outputs.values()}
    hashes.update({str(value.resolve()): sha256(value) for value in geometry.values()})
    hashes[str(job_path.resolve())] = sha256(job_path)
    (args.output_dir / "sha256.json").write_text(
        json.dumps(hashes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"job": str(job_path.resolve()), "outputs": outputs}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
