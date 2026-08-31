"""One-command staging postprocess for exactly one canonical view master."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import uuid
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from build_canonical24_outfit_templates import SIZE, load_l, outfit_template


LAYERS = (
    "body", "hair_back", "base", "jaw", "oral_cavity", "teeth_tongue",
    "lip_lower", "lip_upper", "corner_left", "corner_right", "blush_left",
    "blush_right", "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "eyeliner_left", "eyeliner_right", "brow_left", "brow_right", "hair_left",
    "hair_right", "sleeve_left", "sleeve_right", "ornament",
)


def mask(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.size != SIZE:
            raise ValueError(f"mask must be {SIZE}: {path}")
        if image.mode == "RGBA":
            return np.asarray(image, dtype=np.uint8)[:, :, 3] > 0
        return np.asarray(image.convert("L"), dtype=np.uint8) > 0


def save_mask(path: Path, value: np.ndarray) -> None:
    Image.fromarray(value.astype(np.uint8) * 255, mode="L").save(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bbox(value: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(value)
    if not len(xs):
        raise ValueError("empty head geometry")
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def optional_bbox(value: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(value)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def load_control_contract(
    bundle: Path, view_id: str
) -> tuple[dict[str, object], tuple[int, int], Path, Path]:
    manifest_path = bundle / "control-bundle.json"
    registration_path = bundle / f"{view_id}_registration-anchor.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    if manifest.get("formal_view_id") != view_id:
        raise ValueError(f"control bundle view mismatch: {manifest_path}")
    if manifest.get("mirror") is not False:
        raise ValueError(f"mirrored controls are forbidden: {manifest_path}")
    if registration.get("view_id") != view_id:
        raise ValueError(f"registration view mismatch: {registration_path}")
    if registration.get("canvas") != [1024, 1536]:
        raise ValueError(f"registration canvas mismatch: {registration_path}")
    if registration.get("offset") != [0, 0] or not registration.get(
        "full_canvas_registered"
    ):
        raise ValueError(f"view is not full-canvas registered: {registration_path}")
    body_center = tuple(int(value) for value in registration["body_center"])
    if len(body_center) != 2:
        raise ValueError(f"invalid body center: {registration_path}")
    outfit_control = bundle / f"{view_id}_ownership-outfit.png"
    ornament_control = bundle / f"{view_id}_ornament_mask.png"
    return manifest, body_center, outfit_control, ornament_control


def visible_skin(rgb: np.ndarray) -> np.ndarray:
    """Conservatively retain only already-visible skin pixels; synthesize nothing."""
    red = rgb[:, :, 0].astype(np.int16)
    green = rgb[:, :, 1].astype(np.int16)
    blue = rgb[:, :, 2].astype(np.int16)
    maximum = np.maximum(np.maximum(red, green), blue)
    minimum = np.minimum(np.minimum(red, green), blue)
    return (
        (red > 72)
        & (green > 30)
        & (blue > 18)
        & ((maximum - minimum) > 12)
        & ((red - green) > 7)
        & (red > blue)
    )


def remove_small_components(value: np.ndarray, minimum_pixels: int) -> np.ndarray:
    count, labels, statistics, _ = cv2.connectedComponentsWithStats(
        value.astype(np.uint8), connectivity=8
    )
    kept = np.zeros(value.shape, dtype=bool)
    for label in range(1, count):
        if int(statistics[label, cv2.CC_STAT_AREA]) >= minimum_pixels:
            kept |= labels == label
    return kept


def yaw_of(view: str) -> int:
    return int(view[3:7])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--view-id", required=True)
    parser.add_argument("--master", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--control-bundles-root", type=Path)
    parser.add_argument("--birefnet-alpha", type=Path)
    parser.add_argument("--outfit-guard", type=Path)
    parser.add_argument("--hair-seed", type=Path, action="append", default=[])
    parser.add_argument("--ornament-seed", type=Path)
    parser.add_argument("--accepted", action="store_true")
    parser.add_argument(
        "--preflight-controls-only",
        action="store_true",
        help="validate dynamic 3D controls without a master or output files",
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    controls_root = args.control_bundles_root or (
        repo / "artifacts/pose-atlas-rebuild/2026-08-26/canonical24-control-bundles-agent-b/bundles"
    )
    bundle = controls_root / args.view_id
    part_id_path = bundle / f"{args.view_id}_part-id.png"
    silhouette_path = bundle / f"{args.view_id}_silhouette.png"
    control_manifest, body_center, outfit_control, ornament_control = (
        load_control_contract(bundle, args.view_id)
    )
    part_id = load_l(part_id_path)
    silhouette = load_l(silhouette_path)

    hx0, hy0, hx1, hy1 = bbox(part_id == 1)
    head_width = hx1 - hx0 + 1
    head_height = hy1 - hy0 + 1
    head_cx = (hx0 + hx1) // 2
    head_cy = (hy0 + hy1) // 2
    face = (
        f"{head_cx},{head_cy},{max(20, round(head_width * 0.42))},"
        f"{max(20, round(head_height * 0.45))}"
    )
    control_ornament = mask(ornament_control)
    ornament_box = optional_bbox(control_ornament)
    # Keep the accepted yaw000 v12 geometry formula, but evaluate it from each
    # view's own 3D head part-ID and formal yaw.  The projected ornament mask is
    # validated as a separate physical-side control; it is not allowed to
    # redefine accepted pixel ownership or to copy mask pixels into artwork.
    yaw = math.radians(yaw_of(args.view_id))
    ornament_x = round(head_cx + head_width * 0.38 * math.cos(yaw))
    ornament_y = round(hy0 - head_height * 0.15)
    ornament_rx = max(20, round(head_width * 0.95))
    ornament_ry = max(20, round(head_height * 0.74))
    ornament_source = "per_view_3d_part_id_head_and_formal_yaw"
    if ornament_box is None:
        raise ValueError(f"empty physical-side ornament control: {ornament_control}")
    ornament_anchor = (
        f"{ornament_x},{ornament_y},{ornament_rx},{ornament_ry}"
    )
    if args.preflight_controls_only:
        print(json.dumps({
            "status": "PASS_DYNAMIC_CONTROL_PREFLIGHT_NO_LAYERS_CREATED",
            "view_id": args.view_id,
            "part_id": str(part_id_path.resolve()),
            "silhouette": str(silhouette_path.resolve()),
            "body_center": list(body_center),
            "face_ellipse": face,
            "ornament_anchor": ornament_anchor,
            "ornament_anchor_source": ornament_source,
            "outfit_control_pixels": int(np.count_nonzero(mask(outfit_control))),
            "ornament_control_pixels": int(np.count_nonzero(control_ornament)),
            "mirror": control_manifest["mirror"],
            "layers_created": 0,
        }, ensure_ascii=False))
        return 0
    if args.master is None or args.output_root is None:
        parser.error("--master and --output-root are required outside control preflight")

    with Image.open(args.master) as image:
        if image.size != SIZE:
            raise ValueError(f"master must be {SIZE}: {args.master}")
        source = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    if args.birefnet_alpha is not None:
        source[:, :, 3] = np.where(mask(args.birefnet_alpha), source[:, :, 3], 0)
    source[source[:, :, 3] == 0, :3] = 0
    foreground = source[:, :, 3] > 0
    if not np.any(foreground):
        raise ValueError("cleaned master has empty alpha")

    run_root = args.output_root / f"postprocess-{args.view_id}-{uuid.uuid4().hex}"
    ownership_root = run_root / "ownership"
    ownership_root.mkdir(parents=True)
    clean_master = run_root / f"{args.view_id}.clean-rgba.png"
    Image.fromarray(source, mode="RGBA").save(clean_master)

    if args.outfit_guard is not None:
        preliminary_outfit = mask(args.outfit_guard) & foreground
    else:
        control_outfit = mask(outfit_control)
        preliminary_outfit = (
            control_outfit & foreground
            if np.any(control_outfit)
            else outfit_template(part_id, silhouette) & foreground
        )
    preliminary_outfit_path = run_root / f"{args.view_id}.outfit-guard.png"
    save_mask(preliminary_outfit_path, preliminary_outfit)

    extractor = Path(__file__).with_name("extract_hair_ornament_from_master.py")
    extract_command = [
        sys.executable, str(extractor), "--master", str(clean_master),
        "--output-root", str(ownership_root), "--view-id", args.view_id,
        "--face-ellipse", face, "--ornament-anchor", ornament_anchor,
    ]
    # The geometry outfit guard can include hair in front of the robe.  It is
    # therefore only a traceable body/clothing hint, never an exclusion mask
    # for hair extraction.  Hair/ornament claim their visible source pixels
    # first; the outfit receives the remaining foreground below.
    for seed in args.hair_seed:
        extract_command.extend(("--hair-seed", str(seed)))
    # The projected 3D ornament mask defines the physical-side anchor.  It is
    # not copied wholesale into pixel ownership because that would claim dark
    # hair or background pixels when the render and master silhouettes differ.
    # A caller may still provide a source-matched segmentation seed explicitly.
    if args.ornament_seed is not None:
        extract_command.extend(("--ornament-seed", str(args.ornament_seed)))
    subprocess.run(extract_command, check=True)

    hair_path = ownership_root / f"{args.view_id}_hair_mask.png"
    ornament_path = ownership_root / f"{args.view_id}_ornament_mask.png"
    hair = mask(hair_path) & foreground
    ornament = mask(ornament_path) & foreground
    yy, xx = np.ogrid[: SIZE[1], : SIZE[0]]
    face_rx = max(10.0, head_width * 0.46)
    face_ry = max(10.0, head_height * 0.47)
    face_owned = (
        ((xx - head_cx) / face_rx) ** 2 + ((yy - head_cy) / face_ry) ** 2 <= 1.0
    ) & foreground
    skin_owned = visible_skin(source[:, :, :3]) & foreground
    skin_owned &= yy < round(SIZE[1] * 0.72)
    skin_owned = remove_small_components(skin_owned, minimum_pixels=80)
    protected_existing_anatomy = face_owned | skin_owned | hair
    # All remaining visible pixels belong to the current outfit.  This removes
    # robe, belt, hem, and shoes from core without inventing hidden anatomy.
    outfit = foreground & ~protected_existing_anatomy & ~ornament
    outfit_path = ownership_root / f"{args.view_id}_default_outfit_mask.png"
    save_mask(outfit_path, outfit)
    save_mask(
        ownership_root / f"{args.view_id}_visible_anatomy_mask.png",
        protected_existing_anatomy,
    )
    if not np.any(outfit):
        raise ValueError("empty default outfit mask")
    if np.any(hair & ornament) or np.any(hair & outfit) or np.any(ornament & outfit):
        raise ValueError("hair/ornament/outfit ownership is not mutually exclusive")
    core = foreground & ~outfit & ~ornament
    core_path = ownership_root / f"{args.view_id}_core_mask.png"
    save_mask(core_path, core)

    legacy = repo / "assets/pose-atlas/v4-layered"
    canonical = repo / "assets/pose-atlas/v4" / f"{args.view_id}.png"
    job = [{
        "view_id": args.view_id,
        "master_rgba": str(clean_master),
        "part_id": str(part_id_path.resolve()),
        "outfit_mask": str(outfit_path.resolve()),
        "hair_mask": str(hair_path.resolve()),
        "ornament_mask": str(ornament_path.resolve()),
        "legacy_layer_dir": str(legacy.resolve()),
        "canonical_rgba": str(canonical.resolve()),
    }]
    job_path = run_root / "split-job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    splitter = Path(__file__).parents[1] / "yaw000-core25-yunchangge-staging-agent-c/split_poseatlas25_batch.py"
    subprocess.run(
        [
            sys.executable, str(splitter), "--jobs", str(job_path),
            "--batch-staging", str(run_root / "split"),
            "--exact-600-output", str(run_root / "DO-NOT-CREATE-exact600"),
            "--repo", str(repo),
        ],
        check=True,
    )
    batches = tuple((run_root / "split").glob("batch-*"))
    if len(batches) != 1:
        raise RuntimeError(f"expected one batch output, got {len(batches)}")
    result = json.loads((batches[0] / "batch-result.json").read_text(encoding="utf-8"))
    record = result["results"][0]
    if result["core_png_count"] != 25 or record["recompose_diff_pixels"] != 0:
        raise RuntimeError(f"postprocess split failed: {result}")
    view_root = batches[0] / args.view_id
    core_dir = view_root / "core25"
    pack_dir = view_root / "yunchangge-pack"
    layer_entries = []
    for layer in LAYERS:
        path = (core_dir / f"{args.view_id}_{layer}.png").resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        layer_entries.append({
            "id": layer,
            "path": str(path),
            "offset_x": 0,
            "offset_y": 0,
            "sha256": sha256(path),
        })
    outfit_overlay = (pack_dir / f"{args.view_id}_default_outfit.png").resolve()
    ornament_overlay = (pack_dir / f"{args.view_id}_ornament.png").resolve()
    fragment = {
        "schema": "mohan.pose_atlas.view_fragment",
        "version": "1.0",
        "view_id": args.view_id,
        "accepted": bool(args.accepted),
        "canvas": {"width": 1024, "height": 1536},
        "offset_x": 0,
        "offset_y": 0,
        "body_center": list(body_center),
        "layers": layer_entries,
        "ownership": {
            "core": {"mask": str(core_path.resolve()), "sha256": sha256(core_path)},
            "hair": {"mask": str(hair_path.resolve()), "sha256": sha256(hair_path)},
            "default_outfit": {
                "mask": str(outfit_path.resolve()), "mask_sha256": sha256(outfit_path),
                "overlay": str(outfit_overlay), "overlay_sha256": sha256(outfit_overlay),
            },
            "ornament": {
                "mask": str(ornament_path.resolve()), "mask_sha256": sha256(ornament_path),
                "overlay": str(ornament_overlay), "overlay_sha256": sha256(ornament_overlay),
            },
        },
        "controls": {
            "bundle": str(bundle.resolve()),
            "part_id": {"path": str(part_id_path.resolve()), "sha256": sha256(part_id_path)},
            "silhouette": {"path": str(silhouette_path.resolve()), "sha256": sha256(silhouette_path)},
            "ornament_anchor_source": ornament_source,
            "mirror": False,
        },
        "recomposition": {"diff_pixels": 0, "max_channel_error": 0},
    }
    fragment_path = run_root / f"{args.view_id}.manifest-fragment.json"
    fragment_path.write_text(json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "PASS_ONE_COMMAND_POSTPROCESS "
        f"view={args.view_id} core_png_count=25 recompose_diff_pixels=0 "
        f"hair_pixels={int(np.count_nonzero(hair))} "
        f"ornament_pixels={int(np.count_nonzero(ornament))} "
        f"outfit_pixels={int(np.count_nonzero(outfit))} "
        f"output={batches[0]} fragment={fragment_path} accepted={args.accepted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
