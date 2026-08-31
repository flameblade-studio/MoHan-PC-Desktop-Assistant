#!/usr/bin/env python3
"""Project B00 pixels through the verified Candidate3 mesh without welding asset domains."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


WIDTH, HEIGHT = 1024, 1536


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_faces(path: Path) -> np.ndarray:
    faces: list[tuple[int, int, int]] = []
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.startswith("f "):
                continue
            fields = line.split()[1:]
            if len(fields) != 3:
                raise ValueError("Only triangular OBJ topology is accepted")
            faces.append(tuple(int(field.split("/", 1)[0]) - 1 for field in fields))
    if not faces:
        raise ValueError("OBJ contains no triangle faces")
    return np.asarray(faces, dtype=np.int32)


def raster_maps(
    faces: np.ndarray,
    target_xy: np.ndarray,
    target_depth: np.ndarray,
    source_xy: np.ndarray,
    *,
    keep_largest_depth: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    initial = -np.inf if keep_largest_depth else np.inf
    zbuffer = np.full((HEIGHT, WIDTH), initial, dtype=np.float32)
    map_x = np.full((HEIGHT, WIDTH), -1.0, dtype=np.float32)
    map_y = np.full((HEIGHT, WIDTH), -1.0, dtype=np.float32)
    for face in faces:
        triangle = target_xy[face]
        x0 = max(0, int(np.floor(triangle[:, 0].min())))
        x1 = min(WIDTH - 1, int(np.ceil(triangle[:, 0].max())))
        y0 = max(0, int(np.floor(triangle[:, 1].min())))
        y1 = min(HEIGHT - 1, int(np.ceil(triangle[:, 1].max())))
        if x1 < x0 or y1 < y0:
            continue
        ax, ay = triangle[0]
        bx, by = triangle[1]
        cx, cy = triangle[2]
        denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(float(denominator)) < 1e-10:
            continue
        grid_x, grid_y = np.meshgrid(
            np.arange(x0, x1 + 1, dtype=np.float32) + 0.5,
            np.arange(y0, y1 + 1, dtype=np.float32) + 0.5,
        )
        weight_a = ((by - cy) * (grid_x - cx) + (cx - bx) * (grid_y - cy)) / denominator
        weight_b = ((cy - ay) * (grid_x - cx) + (ax - cx) * (grid_y - cy)) / denominator
        weight_c = 1.0 - weight_a - weight_b
        inside = (weight_a >= -1e-5) & (weight_b >= -1e-5) & (weight_c >= -1e-5)
        if not np.any(inside):
            continue
        depth = (
            weight_a * target_depth[face[0]]
            + weight_b * target_depth[face[1]]
            + weight_c * target_depth[face[2]]
        )
        destination = zbuffer[y0 : y1 + 1, x0 : x1 + 1]
        nearer = depth > destination if keep_largest_depth else depth < destination
        update = inside & nearer
        if not np.any(update):
            continue
        source_x = (
            weight_a * source_xy[face[0], 0]
            + weight_b * source_xy[face[1], 0]
            + weight_c * source_xy[face[2], 0]
        )
        source_y = (
            weight_a * source_xy[face[0], 1]
            + weight_b * source_xy[face[1], 1]
            + weight_c * source_xy[face[2], 1]
        )
        destination[update] = depth[update]
        map_x[y0 : y1 + 1, x0 : x1 + 1][update] = source_x[update]
        map_y[y0 : y1 + 1, x0 : x1 + 1][update] = source_y[update]
    return map_x, map_y, zbuffer


def read_l(path: Path) -> np.ndarray:
    image = Image.open(path).convert("L")
    if image.size != (WIDTH, HEIGHT):
        raise ValueError(f"mask size mismatch: {path}: {image.size}")
    return np.asarray(image)


def read_rgba(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGBA")
    if image.size != (WIDTH, HEIGHT):
        raise ValueError(f"RGBA size mismatch: {path}: {image.size}")
    return np.asarray(image)


def source_domains_from_fragment(source: np.ndarray, fragment_path: Path) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """Load independent B00 asset domains; never bake outfit/ornament into anatomy."""
    fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
    ownership = fragment.get("ownership")
    if not isinstance(ownership, dict):
        raise ValueError("fragment has no ownership object")
    specs = {
        "core": ownership.get("core"),
        "outfit": ownership.get("default_outfit"),
        "hair": ownership.get("hair"),
        "ornament": ownership.get("ornament"),
    }
    domains: dict[str, np.ndarray] = {}
    provenance: dict[str, str] = {}
    for name, spec in specs.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("mask"), str):
            raise ValueError(f"fragment missing ownership mask: {name}")
        mask_path = Path(spec["mask"])
        mask = read_l(mask_path) > 0
        overlay_value = spec.get("overlay")
        if isinstance(overlay_value, str):
            overlay_path = Path(overlay_value)
            layer = read_rgba(overlay_path).copy()
            provenance[name] = str(overlay_path.resolve())
        else:
            layer = source.copy()
            provenance[name] = f"{args_source_marker(source)} * {mask_path.resolve()}"
        layer[~mask] = 0
        layer[layer[:, :, 3] == 0, :3] = 0
        domains[name] = layer
    return domains, provenance


def args_source_marker(_source: np.ndarray) -> str:
    # Avoid hiding the distinction between a real overlay file and a masked authority source.
    return "authority_rgba"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-ownership", type=Path, required=True)
    parser.add_argument(
        "--source-fragment",
        type=Path,
        help="Manifest fragment containing independent core/outfit/hair/ornament sources.",
    )
    parser.add_argument("--projections", type=Path, required=True)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--target-bundle", type=Path, required=True)
    parser.add_argument("--target-renderer-yaw", type=int, default=-45)
    parser.add_argument("--view-id", default="yaw+045-pitch+00")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    source = read_rgba(args.source)
    if source.shape != (HEIGHT, WIDTH, 4):
        raise ValueError(f"source must be 1024x1536 RGBA, got {source.shape}")
    projections = np.load(args.projections)
    yaws = projections["yaw_degrees"]
    source_matches = np.flatnonzero(yaws == 0)
    target_matches = np.flatnonzero(yaws == args.target_renderer_yaw)
    if len(source_matches) != 1 or len(target_matches) != 1:
        raise ValueError("requested source/target yaw missing from projection archive")
    source_index, target_index = int(source_matches[0]), int(target_matches[0])
    xy = projections["screen_xy"].astype(np.float32)
    depth = projections["camera_depth"].astype(np.float32)
    faces = load_faces(args.mesh)
    if int(faces.max()) >= xy.shape[1]:
        raise ValueError("mesh/projection vertex mismatch")

    # Candidate3 control space is deliberately wider/shorter than the approved
    # painted authority. Register only the source sampling coordinates to the
    # authority alpha bbox; target geometry remains the verified 3D projection.
    source_alpha_y, source_alpha_x = np.nonzero(source[:, :, 3] > 0)
    if not len(source_alpha_x):
        raise ValueError("source has empty alpha")
    registered_source_xy = xy[source_index].copy()
    mesh_min = registered_source_xy.min(axis=0)
    mesh_max = registered_source_xy.max(axis=0)
    art_min = np.asarray([source_alpha_x.min(), source_alpha_y.min()], dtype=np.float32)
    art_max = np.asarray([source_alpha_x.max(), source_alpha_y.max()], dtype=np.float32)
    registered_source_xy = art_min + (registered_source_xy - mesh_min) * (
        (art_max - art_min) / (mesh_max - mesh_min)
    )

    map_x, map_y, _ = raster_maps(
        faces,
        xy[target_index],
        depth[target_index],
        registered_source_xy,
        keep_largest_depth=True,
    )
    valid_map = (map_x >= 0) & (map_y >= 0)
    target_silhouette = read_l(args.target_bundle / f"{args.view_id}_silhouette.png") > 0
    if args.source_fragment:
        source_domains, domain_provenance = source_domains_from_fragment(source, args.source_fragment)
    else:
        prefix = "yaw+000-pitch+00"
        masks = {
            "outfit": read_l(args.source_ownership / f"{prefix}_default_outfit_mask.png") > 0,
            "hair": read_l(args.source_ownership / f"{prefix}_hair_mask.png") > 0,
            "ornament": read_l(args.source_ownership / f"{prefix}_ornament_mask.png") > 0,
        }
        masks["core"] = (source[:, :, 3] > 0) & ~masks["outfit"] & ~masks["hair"] & ~masks["ornament"]
        source_domains = {}
        domain_provenance = {}
        for name, mask in masks.items():
            layer = source.copy()
            layer[~mask] = 0
            source_domains[name] = layer
            domain_provenance[name] = f"{args.source.resolve()} * {name}_mask"

    warped_domains: dict[str, np.ndarray] = {}
    visible_domains: dict[str, np.ndarray] = {}
    for name, layer in source_domains.items():
        warped_layer = cv2.remap(layer, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        warped_layer[~(valid_map & target_silhouette)] = 0
        warped_layer[warped_layer[:, :, 3] == 0, :3] = 0
        warped_domains[name] = warped_layer
        visible_domains[name] = warped_layer[:, :, 3] > 0

    # Physical asset priority after independent projection. The layers remain replaceable.
    ornament = visible_domains["ornament"]
    outfit = visible_domains["outfit"] & ~ornament
    hair = visible_domains["hair"] & ~ornament & ~outfit
    core = visible_domains["core"] & ~ornament & ~outfit & ~hair
    domains = {"core": core, "outfit": outfit, "hair": hair, "ornament": ornament}
    warped = np.zeros_like(source)
    for name in ("core", "outfit", "hair", "ornament"):
        warped[domains[name]] = warped_domains[name][domains[name]]
    visible = warped[:, :, 3] > 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    for name, mask in domains.items():
        layer = np.zeros_like(warped)
        layer[mask] = warped_domains[name][mask]
        output = args.output_dir / f"{args.view_id}_{name}-ownership-rgba.png"
        Image.fromarray(layer, "RGBA").save(output)
        outputs[name] = output
        Image.fromarray((mask.astype(np.uint8) * 255), "L").save(
            args.output_dir / f"{args.view_id}_{name}-ownership-mask.png"
        )

    recomposed = np.zeros_like(warped)
    for name in ("core", "outfit", "hair", "ornament"):
        mask = domains[name]
        recomposed[mask] = warped[mask]
    warp_path = args.output_dir / f"{args.view_id}_b00-zbuffer-warp-rgba.png"
    recompose_path = args.output_dir / f"{args.view_id}_ownership-recomposed-rgba.png"
    Image.fromarray(warped, "RGBA").save(warp_path)
    Image.fromarray(recomposed, "RGBA").save(recompose_path)

    overlap = sum(int(np.count_nonzero(domains[a] & domains[b])) for index, a in enumerate(domains) for b in list(domains)[index + 1 :])
    diff = np.abs(recomposed.astype(np.int16) - warped.astype(np.int16))
    coverage = int(np.count_nonzero(visible))
    silhouette_pixels = int(np.count_nonzero(target_silhouette))
    evidence = {
        "schema": "mohan.layered-3d-turntable-texture-projection.v2",
        "view_id": args.view_id,
        "formal": False,
        "accepted": False,
        "identity_checkpoint_contract": "checkpoint-16",
        "source": str(args.source.resolve()),
        "source_sha256": sha256(args.source),
        "source_fragment": str(args.source_fragment.resolve()) if args.source_fragment else None,
        "source_fragment_sha256": sha256(args.source_fragment) if args.source_fragment else None,
        "domain_source_provenance": domain_provenance,
        "generation_model_used": False,
        "mesh": str(args.mesh.resolve()),
        "projection_archive": str(args.projections.resolve()),
        "target_renderer_yaw": args.target_renderer_yaw,
        "source_registration": {
            "method": "mesh_bbox_to_authority_alpha_bbox",
            "mesh_bbox": [float(mesh_min[0]), float(mesh_min[1]), float(mesh_max[0]), float(mesh_max[1])],
            "authority_alpha_bbox": [int(art_min[0]), int(art_min[1]), int(art_max[0]), int(art_max[1])],
        },
        "target_bundle": str(args.target_bundle.resolve()),
        "canvas": [WIDTH, HEIGHT],
        "visible_warp_pixels": coverage,
        "target_silhouette_pixels": silhouette_pixels,
        "silhouette_coverage_ratio": coverage / silhouette_pixels if silhouette_pixels else 0.0,
        "ownership_pixels": {name: int(np.count_nonzero(mask)) for name, mask in domains.items()},
        "ownership_overlap_pixels": overlap,
        "recompose_max_channel_diff": int(diff.max()),
        "recompose_changed_pixels": int(np.count_nonzero(np.any(diff != 0, axis=2))),
        "outputs": {name: {"path": str(path.resolve()), "sha256": sha256(path)} for name, path in outputs.items()},
        "warp": {"path": str(warp_path.resolve()), "sha256": sha256(warp_path)},
        "recomposed": {"path": str(recompose_path.resolve()), "sha256": sha256(recompose_path)},
    }
    evidence_path = args.output_dir / f"{args.view_id}_b00-zbuffer-warp.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    if overlap != 0 or evidence["recompose_max_channel_diff"] != 0 or coverage == 0:
        return 3
    print(json.dumps(evidence, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
