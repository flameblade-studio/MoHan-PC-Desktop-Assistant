"""Build deterministic, temporary body frames from approved bald canvases."""
from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import sys
lazy import stat
lazy import zipfile
lazy from io import BytesIO
lazy from math import ceil
lazy from pathlib import Path, PurePosixPath
lazy from dataclasses import dataclass
lazy from PIL import Image, ImageChops, ImageFilter
lazy import numpy as np
lazy import cv2
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from collections.abc import Mapping
lazy from domain import body_pack as _body_pack
lazy from domain.body_pack import BodyPackManifest, parse_body_pack
lazy from domain.character_layer_plan import parse_character_layer_views
lazy from domain.constants import POSE_ATLAS_ROOT_NAME, POSE_ATLAS_LAYERED_ROOT_NAME


def compute_body_pack_fingerprint(value: BodyPackManifest | Mapping[str, object]) -> str:
    """Expose the canonical fingerprint function through a resolved lazy module."""
    return _body_pack.compute_body_pack_fingerprint(value)


FAMILIES = ("neutral", "small", "a", "o")
EYES = ("rest", "half", "closed")
MISSING_POSES = frozenset({"front-eureka", "front-mock-scold", "front-mock-hit"})
HALF_BASES = ("front-crossed", "left-neutral", "cheek-rest", "exasperated")
FULL_VIEW_COUNT = 24
APPROVED_LAYER_VIEW_COUNT = 203
APPROVED_LAYER_FILE_COUNT = 155
APPROVED_LAYER_DIRECTORY_COUNT = 31
BODY_PACK_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXPECTED_BODY_REFERENCE = {
    "id": "mohan-body-v2",
    "fingerprint": "6340691bfdca8f2eb6197f6237481a550f366ddb762905353703e1a513da778c",
}
MOTION_THRESHOLD = 8
OPAQUE_ALPHA = 255
CORE_ALPHA_THRESHOLD = 128
MOTION_LIMIT_PX = 6
HAIR_SPLIT_TOP = 450
LAYER_KINDS = ("hair-back", "body-fix", "garment", "hair-front")


def write_json(path: Path, value: object) -> None:
    """Use sorted keys, UTF-8 and LF without timestamps or host metadata."""
    _check_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def _check_output_path(path: Path) -> None:
    """Reject links at every output component before any write or mkdir."""
    for component in (path, *path.parents):
        if component.is_symlink() or component.is_junction():
            raise ValueError(f"Output paths must contain regular directories and files: {component}")


def _safe_file(root: Path, relative: str) -> Path:
    part = PurePosixPath(relative)
    if not relative or part.is_absolute() or ".." in part.parts or "\\" in relative:
        raise ValueError(f"Expected a relative POSIX file path: {relative}")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"File escapes its root: {relative}")
    return path


def read_image(path: Path, digest: str | None = None) -> Image.Image:
    """Snapshot and verify an RGBA PNG before using its pixels."""
    data = path.read_bytes()
    if digest is not None and hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"Input SHA-256 mismatch: {path}")
    with Image.open(BytesIO(data)) as image:
        if image.format != "PNG" or image.mode != "RGBA":
            raise ValueError(f"Expected an RGBA PNG: {path}")
        return image.copy()


def read_mask(path: Path) -> Image.Image:
    """Translate grayscale mask values to alpha; preserve authored RGBA alpha."""
    with Image.open(path) as image:
        if image.format != "PNG" or image.mode not in {"L", "RGBA"}:
            raise ValueError(f"Expected a grayscale or RGBA PNG mask: {path}")
        if image.mode == "RGBA":
            return image.copy()
        result = Image.new("RGBA", image.size, (255, 255, 255, 0))
        result.putalpha(image)
        return result


def transplant_face_core(base: Image.Image, source: Image.Image,
                         mask: Image.Image) -> Image.Image:
    """Replace facial pixels with the authored mask's original feather alpha."""
    if any(image.mode != "RGBA" for image in (base, source, mask)):
        raise ValueError("Face transplantation requires RGBA images")
    if base.size != source.size or base.size != mask.size:
        raise ValueError("Face transplantation requires one shared canvas")
    result = Image.composite(source, base, mask.getchannel("A"))
    # Invisible RGB has no visual authority; canonical bytes avoid hidden residue.
    transparent = result.getchannel("A").point(lambda alpha: 255 if alpha == 0 else 0)
    result.paste((0, 0, 0, 0), mask=transparent)
    return result


def head_roi(mask: Image.Image) -> tuple[int, int, int, int]:
    """Bound motion to the static face box with the owner's head margins."""
    box = mask.getchannel("A").getbbox()
    if box is None:
        raise ValueError("A dynamic face core requires a nonempty static mask")
    left, top, right, bottom = box
    horizontal = ceil((right - left) * 0.4)
    upper = ceil((bottom - top) * 0.4)
    lower = ceil((bottom - top) * 0.25)
    return (max(0, left - horizontal), max(0, top - upper),
            min(mask.width, right + horizontal), min(mask.height, bottom + lower))


def _face_motion(mask: Image.Image, rest: Image.Image,
                 frames: list[Image.Image]) -> Image.Image:
    """Open ROI state differences and limit motion to six pixels around S."""
    if mask.mode != "RGBA" or rest.mode != "RGBA" or mask.size != rest.size:
        raise ValueError("Dynamic face cores require one shared RGBA canvas")
    static = mask.getchannel("A").point(lambda alpha: 255 if alpha >= CORE_ALPHA_THRESHOLD else 0)
    if static.getbbox() is None:
        return Image.new("L", mask.size, 0)
    left, top, right, bottom = head_roi(mask)
    reference = np.asarray(rest, dtype=np.int16)
    changed = np.zeros(reference.shape[:2], dtype=bool)
    for frame in frames:
        if frame.mode != "RGBA" or frame.size != rest.size:
            raise ValueError("Dynamic face cores require one shared RGBA canvas")
        pixels = np.asarray(frame, dtype=np.int16)
        visible = (pixels[..., 3] > 0) | (reference[..., 3] > 0)
        difference = np.abs(pixels - reference)
        changed |= (difference[..., 3] > MOTION_THRESHOLD) | (
            np.any(difference[..., :3] > MOTION_THRESHOLD, axis=2) & visible
        )
    roi = Image.new("L", mask.size, 0)
    roi.paste(255, (left, top, right, bottom))
    movement = ImageChops.darker(Image.fromarray(changed.astype(np.uint8) * 255), roi)
    opened = movement.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    return ImageChops.darker(opened, static.filter(ImageFilter.MaxFilter(2 * MOTION_LIMIT_PX + 1)))


def _feather_face_union(mask: Image.Image, movement: Image.Image,
                       feather_radius: float) -> Image.Image:
    """Feather the complete binary S union M once using the static radius."""
    if feather_radius <= 0:
        raise ValueError("Face feather radius must be positive")
    static = mask.getchannel("A").point(lambda alpha: 255 if alpha >= CORE_ALPHA_THRESHOLD else 0)
    union = ImageChops.lighter(static, movement)
    result = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    if union.getbbox() is None:
        return result
    outside = (np.asarray(union) == 0).astype(np.uint8)
    distance = cv2.distanceTransform(outside, cv2.DIST_L2, 5)
    weight = np.clip(1 - distance / feather_radius, 0, 1)
    result.putalpha(Image.fromarray(np.rint(weight * 255).astype(np.uint8)))
    return result


def _static_feather_radius(source: Path) -> float:
    """Use the radius declared by the approved partition source."""
    manifest = _input_manifest(source / "manifest.json")
    settings = manifest.get("F", manifest.get("face_mask", {}))
    return float(settings.get("feather_px", 5))


def dynamic_face_core(mask: Image.Image, rest: Image.Image,
                      frames: list[Image.Image], *, feather_radius: float = 5) -> Image.Image:
    """Build S(alpha>=128) union opened ROI motion within dilate(S,6), then feather."""
    return _feather_face_union(mask, _face_motion(mask, rest, frames), feather_radius)


def _gesture_masks(source: Path, size: tuple[int, int]) -> dict[str, np.ndarray]:
    """Preserve the source's semantic ownership and hair depth split."""
    ys, xs = np.indices((size[1], size[0]))
    split = (ys > HAIR_SPLIT_TOP) & (
        (xs < np.interp(ys[:, 0], [450, 650, 800, 1100], [455, 435, 400, 360])[:, None]) |
        (xs > np.interp(ys[:, 0], [450, 650, 800, 1100], [775, 805, 860, 940])[:, None])
    )
    hair = np.asarray(read_mask(source / "hair-owned-mask.png"))[..., 3] > 0
    skin = np.asarray(read_mask(source / "skin-owned-mask.png"))[..., 3] > 0
    garment = np.asarray(read_mask(source / "garment-owned-mask.png"))[..., 3] > 0
    masks = {"hair-back": hair & split, "body-fix": skin,
             "garment": garment, "hair-front": hair & ~split}
    ownership = sum(mask.astype(np.uint8) for mask in masks.values())
    if np.any(ownership != 1):
        raise ValueError(f"Gesture ownership must partition the canvas: {source.name}")
    return masks


def _write_unweighted_layers(
    destination: Path, base: np.ndarray, approved: np.ndarray,
    masks: dict[str, np.ndarray],
) -> dict[str, str]:
    """Partition native A with empty F; only the compositor applies face weights."""
    base = base.copy()
    approved = approved.copy()
    base[base[..., 3] == 0] = 0
    approved[approved[..., 3] == 0] = 0
    hide = (base[..., 3] > 0) & (approved[..., 3] < OPAQUE_ALPHA)
    replace = np.any(approved != base, axis=2) | hide
    overlay = np.zeros_like(approved)
    overlay[replace] = approved[replace]
    ownership = sum(mask.astype(np.uint8) for mask in masks.values())
    if np.any((ownership != 1) & (overlay[..., 3] > 0)):
        raise ValueError("Semantic ownership must partition every visible overlay pixel")
    cleared = base.copy()
    cleared[hide] = 0
    rendered = Image.fromarray(cleared)
    outputs = {}
    for kind, mask in masks.items():
        pixels = np.zeros_like(overlay)
        pixels[mask] = overlay[mask]
        image = Image.fromarray(pixels)
        outputs[f"{kind}.png"] = write_frame(destination, f"{kind}.png", image)["sha256"]
        rendered = Image.alpha_composite(rendered, image)
    hide_mask = Image.new("RGBA", rendered.size, (255, 255, 255, 0))
    hide_mask.putalpha(Image.fromarray(hide.astype(np.uint8) * OPAQUE_ALPHA))
    for name, image in (("base-hide-mask.png", hide_mask),
                        ("composite.png", rendered), ("approved-unweighted.png", Image.fromarray(approved)),
                        ("L.png", Image.fromarray(overlay))):
        outputs[name] = write_frame(destination, name, image)["sha256"]
    delta = np.abs(np.asarray(rendered, dtype=np.int16) - approved.astype(np.int16))
    if int(delta.max()) > 1:
        raise ValueError(f"Unweighted reconstruction differs from approved A: {int(delta.max())}")
    return outputs


def recompute_gesture_layers(source: Path, target: Path, view: str) -> Path:
    """Repartition the candidate A against the owner's edge-corrected bald B."""
    destination = target / "recomputed" / view
    base = np.array(read_image(source / "bald-natural.png"))
    approved = np.array(read_image(source / "A.png"))
    base[base[..., 3] == 0] = 0
    approved[approved[..., 3] == 0] = 0
    core = read_mask(source / "face-core-mask.png")
    masks = _gesture_masks(source, core.size)
    outputs = _write_unweighted_layers(destination, base, approved, masks)
    outputs["face-core-mask.png"] = write_frame(destination, "face-core-mask.png", core)["sha256"]
    delta = np.abs(np.asarray(read_image(destination / "composite.png"), dtype=np.int16)
                   - approved.astype(np.int16))
    outside_delta = int(delta.max())
    write_json(destination / "manifest.json", {
        "z_order": ["hair-back", "base-with-H", "body-fix", "garment", "hair-front"],
        "outputs": outputs, "appearance_accepted": True,
        "H_definition": "B.alpha>0 and A.alpha<255", "outside_F_RGBA_max": outside_delta,
        "face_core_precleared": False, "approval": "林可芸三個手勢同意",
        "legacy_partition_checks": {},
    })
    write_json(destination / "builder-provenance.json", {
        "bald_sha256": hashlib.sha256((source / "bald-natural.png").read_bytes()).hexdigest(),
        "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source.glob("*.png"))},
        "appearance_accepted": True, "face_core_precleared": False,
        "approval": "林可芸三個手勢同意",
    })
    return destination


def _capture_partition_owners(text: str, partition: str, script: Path) -> str:
    # Capture the approved semantic partition independently of its legacy F weighting.
    capture = {
        "lk-hair-F1": (" r=bc.copy();union=np.zeros_like(l)",
                       " BUILD_OWNERS.update(dict(roles))\n r=bc.copy();union=np.zeros_like(l)"),
        "lk-hair-F2": ("    order=['hair-back','body-fix','garment','hair-front']",
                       "    BUILD_OWNERS.update(regions)\n    order=['hair-back','body-fix','garment','hair-front']"),
        "lk-hair-H": (" layers={}\n", " BUILD_OWNERS.update(masks)\n layers={}\n"),
    }
    original, replacement = capture[partition]
    if text.count(original) != 1:
        raise ValueError(f"Partition adapter requires the reviewed semantic boundary: {script}")
    return text.replace(original, replacement)


def recompute_layer_view(layers_root: Path, bald_root: Path, target: Path,
                         view: str) -> Path:
    """Run the approved partition algorithm with a new B and isolated output."""
    source = layer_directory(layers_root, view)
    partition = source.parents[1].name
    destination = target / "recomputed" / view
    _check_output_path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if partition == "lk-hair-F2":
        script = source.parents[1] / "exact-round9.py"
        text = script.read_text(encoding="utf-8")
        text = text.replace("out=ROOT/'round9'/v", "out=BUILD_DESTINATION")
        text = text.replace("(old/'manifest.json')", "(ROOT/'round9/prior-delivery'/v/'manifest.json')")
        for name in ("face-skin-mask", "hands-skin-mask", "feet-skin-mask", "hair-sam-mask",
                     "shirt-sam-mask", "pants-sam-mask", "shoes-sam-mask", "hair-front"):
            if not (source.parents[1] / view / f"{name}.png").is_file():
                raise ValueError(f"Missing F2 semantic input: {view}/{name}.png")
        args = [str(script), "--view", view, "--base", str(bald_root / view / "bald-natural.png")]
    elif partition == "lk-hair-F1":
        script = source.parent / "build_exact.py"
        text = script.read_text(encoding="utf-8")
        text = text.replace("ROOT=Path('.quality-tmp/lk-hair-F1'); OUT=ROOT/'round9'",
                            "ROOT=BUILD_SOURCE_ROOT; OUT=BUILD_DESTINATION.parent")
        # Matting stays in the original approved tree when the output is redirected.
        text = text.replace("mp=OUT/'matting'", "mp=BUILD_ROUND9/'matting'")
        # Clearing an identical soft-alpha B still requires repainting approved A.
        text = text.replace("different=np.any(a!=b,axis=2)", "different=np.any(a!=b,axis=2)|H")
        args = []
    else:
        script = source.parent / "build_exact.py"
        text = script.read_text(encoding="utf-8")
        translation = _input_manifest(source / "manifest.json")["alignment"]["translation"]
        args = [str(script), "--pose", view, "--bald", str(bald_root / view / "bald-natural.png"),
                "--dx", str(translation[0]), "--dy", str(translation[1]), "--output", str(destination)]
    text = _capture_partition_owners(text, partition, script)
    owners: dict[str, np.ndarray] = {}
    namespace = {"__file__": str(script.resolve()), "__name__": "body_partition_build",
                 "BUILD_SOURCE_ROOT": source.parents[1].resolve(),
                 "BUILD_ROUND9": source.parent.resolve(), "BUILD_DESTINATION": destination.resolve(),
                 "BUILD_OWNERS": owners}
    previous_argv = sys.argv
    previous_bytecode = sys.dont_write_bytecode
    previous_path = sys.path.copy()
    try:
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(source.parents[1].resolve()))
        exec(compile(text, str(script), "exec"), namespace)
        if partition == "lk-hair-F1":
            namespace["build"](view, bald_root / view / "bald-natural.png")
        else:
            sys.argv = args
            namespace["main"]()
    finally:
        sys.argv = previous_argv
        sys.dont_write_bytecode = previous_bytecode
        sys.path[:] = previous_path
    approved_name = "A-birefnet.png" if partition == "lk-hair-F1" else "approved-matted-aligned.png"
    outputs = _write_unweighted_layers(
        destination, np.asarray(read_image(bald_root / view / "bald-natural.png")),
        np.asarray(read_image(destination / approved_name)), owners,
    )
    metadata = _input_manifest(destination / "manifest.json")
    output_key = "files" if "files" in metadata else "outputs"
    metadata[output_key].update(outputs)
    metadata["legacy_partition_checks"] = metadata.pop("checks", metadata.pop("metrics", {}))
    metadata["face_core_precleared"] = False
    metadata["H_definition"] = "B.alpha>0 and A.alpha<255; no face-core preclear"
    metadata["layer_contract"] = "native-A-alpha; compositor-only-F-body"
    write_json(destination / "manifest.json", metadata)
    for metadata in destination.glob("*.json"):
        value = json.loads(metadata.read_text(encoding="utf-8"))
        write_json(metadata, value)
    write_json(destination / "builder-provenance.json", {
        "script": script.name, "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "bald_sha256": hashlib.sha256((bald_root / view / "bald-natural.png").read_bytes()).hexdigest(),
        "output_redirected": True, "face_core_precleared": False,
        "adapter": {"F1": "repaint H even when A equals B",
                    "F2": "prior-delivery registration; original semantic masks",
                    "H": "preserve approved translation"}[partition.removeprefix("lk-hair-")],
    })
    return destination


def write_frame(root: Path, relative: str, image: Image.Image) -> dict[str, str]:
    """Encode only pixel data with fixed PNG settings."""
    if image.mode != "RGBA":
        raise ValueError("Body-pack files require RGBA")
    path = _safe_file(root, relative)
    _check_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = Image.frombytes("RGBA", image.size, image.tobytes())
    data = BytesIO()
    clean.save(data, format="PNG", compress_level=9, optimize=False)
    payload = data.getvalue()
    path.write_bytes(payload)
    return {"path": relative, "sha256": hashlib.sha256(payload).hexdigest()}


def _zip_file_records(package_root: Path) -> list[dict[str, object]]:
    records = []
    for path in sorted(package_root.rglob("*")):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f"Release package contains a link: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(package_root).as_posix()
        pure = PurePosixPath(relative)
        if pure.is_absolute() or "\\" in relative or ".." in pure.parts or ":" in relative:
            raise ValueError(f"Unsafe release member path: {relative}")
        payload = path.read_bytes()
        records.append({
            "path": relative,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    return sorted(records, key=lambda item: str(item["path"]))


def build_reproducible_zip(package_root: Path, archive_path: Path) -> dict[str, object]:
    """Write sorted ZIP_STORED regular files with fixed timestamps and permissions."""
    root = package_root.resolve()
    destination = archive_path.resolve(strict=False)
    if destination.is_relative_to(root):
        raise ValueError("Release archive must be outside the package directory")
    _check_output_path(archive_path)
    records = _zip_file_records(root)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for record in records:
            relative = str(record["path"])
            info = zipfile.ZipInfo(relative, date_time=BODY_PACK_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.extra = b""
            info.comment = b""
            archive.writestr(info, (root / relative).read_bytes())
    payload = archive_path.read_bytes()
    return {
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "files": records,
    }


def _copy_release_legal_files(product_root: Path, package_root: Path) -> None:
    legal_root = product_root / "assets/body-packs/mohan-body-v2"
    for name in ("LICENSE.txt", "NOTICE.md"):
        source = legal_root / name
        if not source.is_file():
            raise ValueError(f"Required release legal text is missing: {source}")
        text = source.read_text(encoding="utf-8")
        (package_root / name).write_text(text, encoding="utf-8", newline="\n")


def layer_directory(root: Path, view: str) -> Path:
    """Resolve the owner's exact F1/F2/H partition, without recursive discovery."""
    if not view.startswith("yaw"):
        return root / "lk-hair-H/round9" / view
    front = root / "lk-hair-F1/round9" / view
    return front if front.is_dir() else root / "lk-hair-F2/round9" / view


def half_base(pose: str) -> str | None:
    """Preserve gestures; only expression variants share a reviewed silhouette."""
    if pose in MISSING_POSES:
        return None
    if pose in HALF_BASES:
        return pose
    if pose == "front-exasperated":
        return "exasperated"
    if pose.startswith("cheek-"):
        return "cheek-rest"
    if pose.startswith("front-"):
        return "front-crossed"
    return None


def _record_image(root: Path, record: dict) -> Image.Image:
    return read_image(_safe_file(root, record["path"]), record["sha256"])


def _input_manifest(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a manifest object: {path}")
    return value


def _load_approved_layer_views(root: Path, version: str, product_root: Path) -> dict:
    """Validate and retain the exact approved companion layer manifest."""
    manifest = _input_manifest(root / "manifest.json")
    if set(manifest) != {"body_pack", "layer_views"}:
        raise ValueError("The companion body manifest has unexpected fields")
    expected_reference = {**EXPECTED_BODY_REFERENCE, "version": version}
    if manifest["body_pack"] != expected_reference:
        raise ValueError("The companion layer manifest references a different body pack")
    layer_views = manifest["layer_views"]
    parse_character_layer_views(layer_views)
    if len(layer_views) != APPROVED_LAYER_VIEW_COUNT:
        raise ValueError(f"Expected 203 approved layer views, found {len(layer_views)}")
    unique_paths = set()
    view_directories = set()
    for view, plan in layer_views.items():
        for record in [*plan["layers"], plan["base_hide"]]:
            relative = record["path"]
            path = _safe_file(product_root, relative)
            if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
                raise ValueError(f"Companion layer SHA-256 mismatch: {view}/{relative}")
            unique_paths.add(relative)
            view_directories.add(PurePosixPath(relative).parent.as_posix())
    if (len(unique_paths) != APPROVED_LAYER_FILE_COUNT
            or len(view_directories) != APPROVED_LAYER_DIRECTORY_COUNT):
        raise ValueError(
            "Expected the approved 155 PNGs in 31 view directories; "
            f"found {len(unique_paths)} PNGs in {len(view_directories)} directories"
        )
    return layer_views


def verify_release_source_manifest(path: Path, product_root: Path) -> dict:
    """Verify the complete, portable, checked-in source tree before a release build."""
    value = _input_manifest(path)
    expected_fields = {
        "schema", "schema_version", "pack", "source_roots", "files",
        "metadata_receipts", "source_manifest_drift", "layer_dependency", "build_provenance",
    }
    if set(value) != expected_fields:
        raise ValueError("Release source manifest fields differ from the supported schema")
    if value["schema"] != "flameblade.body-pack-source.v1" or value["schema_version"] != 1:
        raise ValueError("Release source manifest uses an unsupported schema")
    pack = value["pack"]
    if set(pack) != {"id", "version", "license", "expected_fingerprint"}:
        raise ValueError("Release source pack identity fields differ from the schema")
    if (pack["id"], pack["license"], pack["expected_fingerprint"]) != (
        EXPECTED_BODY_REFERENCE["id"], "CC-BY-NC-ND-4.0", EXPECTED_BODY_REFERENCE["fingerprint"]
    ):
        raise ValueError("Release source manifest does not match the approved body identity")
    if not isinstance(pack["version"], str) or not pack["version"].strip():
        raise ValueError("Release source manifest must declare a non-empty pack version")
    source_root = product_root / "assets/body-packs/mohan-body-v2/source"
    records = value["files"]
    if not isinstance(records, list) or not records:
        raise ValueError("Release source manifest must declare its source files")
    declared = {}
    for row in records:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise ValueError("Release source file records require path, bytes and sha256")
        relative = row["path"]
        if not isinstance(relative, str) or relative in declared:
            raise ValueError("Release source file paths must be unique relative POSIX paths")
        source = _safe_file(source_root, relative)
        payload = source.read_bytes()
        if type(row["bytes"]) is not int or len(payload) != row["bytes"]:
            raise ValueError(f"Release source byte count changed: {relative}")
        digest = hashlib.sha256(payload).hexdigest()
        if row["sha256"] != digest:
            raise ValueError(f"Release source SHA-256 changed: {relative}")
        declared[relative] = digest
    actual = {
        item.relative_to(source_root).as_posix()
        for item in source_root.rglob("*")
        if item.is_file()
    }
    if actual != set(declared):
        raise ValueError(
            "Release source tree differs from its manifest: "
            f"unlisted={sorted(actual - set(declared))}, missing={sorted(set(declared) - actual)}"
        )
    serialized = json.dumps(value, ensure_ascii=False)
    if "C:" in serialized or "D:" in serialized:
        raise ValueError("Release source manifest contains a local absolute path")
    for field in ("source_roots", "metadata_receipts", "source_manifest_drift", "layer_dependency", "build_provenance"):
        if field not in value:
            raise ValueError(f"Release source manifest is missing {field}")
    return value


def _copy_layer_view(source: Path, target: Path, view: str) -> tuple[dict, Image.Image]:
    manifest = _input_manifest(source / "manifest.json")
    order = ["base" if stage == "base-with-H" else stage
             for stage in manifest["z_order"]]
    if "base" not in order:
        order.insert(0, "base")
    records = []
    for kind in LAYER_KINDS:
        record = write_frame(target, f"views/{view}/{kind}.png", read_image(source / f"{kind}.png"))
        records.append({"kind": kind, **record, "anchor": [0, 0]})
    hide = write_frame(target, f"views/{view}/base-hide-mask.png", read_mask(source / "base-hide-mask.png"))
    plan = {"order": order, "layers": records, "base_hide": {**hide, "anchor": [0, 0]}}
    parse_character_layer_views({view: plan})
    core_path = source / "face-feather-mask.png"
    if not core_path.exists():
        core_path = source / "face-core-mask.png"
    return plan, read_mask(core_path)


def _half_frames(root: Path, pose: str, declared: dict) -> dict:
    if pose in declared:
        return declared[pose]["frames"]
    # Cheek rest is a retained product frame set outside the active expression map.
    frames = {}
    for family in FAMILIES:
        frames[family] = {}
        for eye in EYES:
            relative = f"frames/{pose}-{family}-{eye}.rgba.png"
            payload = _safe_file(root, relative).read_bytes()
            frames[family][eye] = {"path": relative, "sha256": hashlib.sha256(payload).hexdigest()}
    return frames


def _states(frames: dict, *, halfbody: bool, mode: str) -> dict:
    selected = {}
    for family in FAMILIES if mode == "all" else ("neutral",):
        for eye in EYES:
            state = f"{family}-{eye}" if halfbody or family != "neutral" else eye
            selected[state] = frames[family][eye]
    return selected


def _directory_stats(root: Path, *, exclude_recomputed: bool = False) -> dict:
    rows = []
    for path in sorted(root.rglob("*")):
        if exclude_recomputed and path.relative_to(root).parts[0] == "recomputed":
            continue
        if path.is_file():
            data = path.read_bytes()
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest()})
    return {"files": len(rows), "bytes": sum(row["bytes"] for row in rows), "inventory": rows}


@dataclass(frozen=True)
class BuildRequest:
    """Immutable inputs for one legacy or release body-pack build."""

    product_root: Path
    bald_root: Path
    layers_root: Path
    output: Path
    license_text: str
    mode: str = "all"
    layer_mode: str = "copy"
    fixed_core_root: Path | None = None
    character_layers_root: Path | None = None
    source_manifest: Path | None = None
    version: str = "1.0.0"


class _Builder:
    """Own one build's source paths, bindings and deterministic output files."""

    def __init__(self, request: BuildRequest) -> None:
        product_root = request.product_root
        bald_root = request.bald_root
        layers_root = request.layers_root
        output = request.output
        license_text = request.license_text
        mode = request.mode
        layer_mode = request.layer_mode
        fixed_core_root = request.fixed_core_root
        character_layers_root = request.character_layers_root
        version = request.version
        self.mode = mode
        self.fixed_core_root = fixed_core_root
        self.character_layers_root = character_layers_root
        self.direct_source = fixed_core_root is not None
        if self.direct_source != (character_layers_root is not None):
            raise ValueError("Fixed core masks and companion layer assets must be supplied together")
        gestures_root = layers_root / "gestures3"
        self.gestures_root = gestures_root if gestures_root.is_dir() else None
        self.gestures = set()
        if self.gestures_root is not None:
            for pose in sorted(MISSING_POSES):
                source = gestures_root / pose
                for name in ("bald-natural.png", "bald-blink-half.png", "bald-blink-closed.png",
                             "A.png", "face-core-mask.png", "F-core.png",
                             "hair-owned-mask.png", "skin-owned-mask.png", "garment-owned-mask.png"):
                    if not (source / name).is_file():
                        raise ValueError(f"Missing gesture input: {pose}/{name}")
                self.gestures.add(pose)
        self.recompute = layer_mode == "recompute"
        self.reuse = layer_mode == "reuse"
        self.bald_root = bald_root
        self.layers_root = layers_root
        self.pack = output / "mohan-body-v2"
        self.character = output / "lin-keyun-layers"
        self.atlas = product_root / "assets/pose-atlas" / POSE_ATLAS_ROOT_NAME
        self.layered = product_root / "assets/pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME
        self.full_source = _input_manifest(self.layered / "complete_expression_manifest.json")["views"]
        self.half_root = product_root / "assets/expressions/complete-expressions"
        self.half_manifest = _input_manifest(self.half_root / "manifest.json")
        self.poses = sorted(set(self.half_manifest["poses"]) | {"cheek-rest"})
        self.views = sorted(path.parent.name for path in bald_root.glob("yaw*/bald-natural.png"))
        if len(self.views) != FULL_VIEW_COUNT:
            raise ValueError(f"Expected 24 approved full-body canvases, found {len(self.views)}")
        bald_manifest = _input_manifest(bald_root / "manifest.json")
        self.bald_hashes = {row["view"]: row["sha256"] for row in bald_manifest["views"]}
        if self.direct_source and self.gestures != MISSING_POSES:
            raise ValueError("The locked release source requires all three approved gesture inputs")
        self.manifest = {"schema": "mohan.body-pack.v1", "id": "mohan-body-v2", "version": version,
                         "license": license_text, "missing_body_poses": {pose: {"status": "missing_body_pose"}
                         for pose in sorted(MISSING_POSES - self.gestures)}, "full_body": {}, "half_body": {}, "face_core_masks": {}}
        self.layer_views = _load_approved_layer_views(character_layers_root, version, product_root) if self.direct_source else {}
        self.inventory = {"full_body": {}, "half_body": {}, "expressions": {}, "missing_body_poses": []}

    def base_pose(self, pose: str) -> str | None:
        return pose if pose in self.gestures else half_base(pose)

    def bald_image(self, view: str) -> Image.Image:
        if view in self.gestures:
            return read_image(self.gestures_root / view / "bald-natural.png")
        return read_image(self.bald_root / view / "bald-natural.png", self.bald_hashes[view])

    def layer_source(self, view: str) -> Path:
        if view in self.gestures:
            return recompute_gesture_layers(self.gestures_root / view, self.character, view)
        if self.recompute:
            return recompute_layer_view(self.layers_root, self.bald_root, self.character, view)
        if self.reuse:
            source = self.character / "recomputed" / view
            provenance = _input_manifest(source / "builder-provenance.json")
            if provenance.get("face_core_precleared") is not False:
                raise ValueError(f"Recomputed layers require the unweighted face-core contract: {view}")
            if provenance["bald_sha256"] != self.bald_hashes[view]:
                raise ValueError(f"Recomputed layers use a different bald body: {view}")
            metadata = _input_manifest(source / "manifest.json")
            outputs = metadata.get("outputs", metadata.get("files", {}))
            names = [f"{kind}.png" for kind in LAYER_KINDS]
            names.extend(["base-hide-mask.png", "face-core-mask.png"])
            if (source / "face-feather-mask.png").exists():
                names.append("face-feather-mask.png")
            for name in names:
                if name not in outputs or hashlib.sha256((source / name).read_bytes()).hexdigest() != outputs[name]:
                    raise ValueError(f"Recomputed layer hash mismatch: {view}/{name}")
            return source
        source = layer_directory(self.layers_root, view)
        if _input_manifest(source / "manifest.json").get("face_core_precleared") is not False:
            raise ValueError(f"Copy requires unweighted layers; use --recompute-layers: {view}")
        return source

    def build_full_body(self) -> None:
        for view in self.views:
            if self.direct_source:
                plan = self.layer_views[view]
                core = read_mask(_safe_file(self.fixed_core_root, f"{view}.png"))
            else:
                source_dir = self.layer_source(view)
                plan, core = _copy_layer_view(source_dir, self.character, view)
            base = read_image(self.bald_root / view / "bald-natural.png", self.bald_hashes[view])
            if core.size != base.size:
                raise ValueError(f"Core canvas mismatch: {view}")
            group = self.full_source.get(view)
            if group is None:
                raw = read_image(self.atlas / f"{view}.png")
                if not self.direct_source:
                    core = dynamic_face_core(core, raw, [], feather_radius=_static_feather_radius(source_dir))
                states = {"rest": write_frame(self.pack, f"full-body/{view}/rest.png",
                                               transplant_face_core(base, raw, core))}
            else:
                families = {"neutral": group["neutral_frames"], "small": group["frames"]["I"],
                            "a": group["frames"]["A"], "o": group["frames"]["O"]}
                all_records = _states(families, halfbody=False, mode="all")
                originals = {state: _record_image(self.layered, record) for state, record in all_records.items()}
                if not self.direct_source:
                    core = dynamic_face_core(core, originals["rest"], list(originals.values()),
                                             feather_radius=_static_feather_radius(source_dir))
                states = {}
                for state in _states(families, halfbody=False, mode=self.mode):
                    image = transplant_face_core(base, originals[state], core)
                    states[state] = write_frame(self.pack, f"full-body/{view}/{state}.png", image)
            self.manifest["full_body"][view] = states
            self.manifest["face_core_masks"][view] = write_frame(self.pack, f"face-core/{view}.png", core)
            if not self.direct_source:
                self.layer_views[view] = plan
            self.inventory["full_body"][view] = {"states": sorted(states), "rest_only": group is None,
                                            "source_visemes": [] if group is None else sorted(group["frames"])}

    def build_half_body(self) -> None:
        for pose in self.poses:
            base_pose = self.base_pose(pose)
            if base_pose is None:
                self.inventory["missing_body_poses"].append(pose)
                self.inventory["half_body"][pose] = {"body_pose": None, "status": "missing_body_pose"}
                continue
            if self.direct_source:
                core = read_mask(_safe_file(self.fixed_core_root, f"{base_pose}.png"))
                self.manifest["face_core_masks"][base_pose] = write_frame(
                    self.pack, f"face-core/{base_pose}.png", core
                )
            elif base_pose not in self.layer_views:
                source_dir = self.layer_source(base_pose)
                plan, core = _copy_layer_view(source_dir, self.character, base_pose)
                # Recomputing B may change eligibility; retain the approved static F.
                authored_source = (self.gestures_root / base_pose if base_pose in self.gestures
                                   else layer_directory(self.layers_root, base_pose))
                authored_core = read_mask(authored_source / "face-core-mask.png")
                if authored_core.size != core.size:
                    raise ValueError(f"Authored core canvas mismatch: {base_pose}")
                core.putalpha(ImageChops.lighter(core.getchannel("A"), authored_core.getchannel("A")))
                # Expression poses sharing one bald silhouette also share the union F.
                static_core = core.copy()
                movement = Image.new("L", core.size, 0)
                for sibling in self.poses:
                    if self.base_pose(sibling) != base_pose:
                        continue
                    records = _states(_half_frames(self.half_root, sibling, self.half_manifest["poses"]),
                                      halfbody=True, mode="all")
                    originals = {state: _record_image(self.half_root, record) for state, record in records.items()}
                    movement = ImageChops.lighter(
                        movement, _face_motion(static_core, originals["neutral-rest"], list(originals.values())),
                    )
                core = _feather_face_union(static_core, movement, _static_feather_radius(source_dir))
                self.layer_views[base_pose] = plan
                self.manifest["face_core_masks"][base_pose] = write_frame(
                    self.pack, f"face-core/{base_pose}.png", core
                )
            core = read_image(self.pack / self.manifest["face_core_masks"][base_pose]["path"])
            base = self.bald_image(base_pose)
            states = {}
            for state, record in _states(_half_frames(self.half_root, pose, self.half_manifest["poses"]),
                                         halfbody=True, mode=self.mode).items():
                image = transplant_face_core(base, _record_image(self.half_root, record), core)
                states[state] = write_frame(self.pack, f"half-body/{pose}/{state}.png", image)
            self.manifest["half_body"][pose] = states
            self.manifest["face_core_masks"][pose] = self.manifest["face_core_masks"][base_pose]
            if self.direct_source:
                if self.layer_views.get(pose) != self.layer_views[base_pose]:
                    raise ValueError(f"Approved companion layer alias differs from the body binding: {pose}")
            else:
                self.layer_views[pose] = self.layer_views[base_pose]
            self.inventory["half_body"][pose] = {"body_pose": base_pose, "states": sorted(states), "status": "built"}
            if pose in self.gestures:
                self.inventory["half_body"][pose]["appearance_accepted"] = True

    def bind_aliases(self) -> None:
        # Exasperated uses its authored product pose, while the layer input uses a short ID.
        for alias, pose in {"exasperated": "front-exasperated", "front": "front-crossed",
                            "lean": "left-neutral", "cheek": "cheek-rest"}.items():
            self.manifest["half_body"][alias] = self.manifest["half_body"][pose]
            self.manifest["face_core_masks"][alias] = self.manifest["face_core_masks"][pose]
            if self.direct_source:
                if self.layer_views.get(alias) != self.layer_views[pose]:
                    raise ValueError(f"Approved companion alias differs from the body binding: {alias}")
            else:
                self.layer_views[alias] = self.layer_views[pose]
        for expression, binding in sorted(self.half_manifest["expressions"].items()):
            pose = binding["pose"]
            built = pose in self.manifest["half_body"]
            self.inventory["expressions"][expression] = {**binding, "body_pose": self.base_pose(pose),
                                                    "status": "built" if built else "missing_body_pose"}
            if built:
                self.manifest["half_body"][expression] = self.manifest["half_body"][pose]
                self.manifest["face_core_masks"][expression] = self.manifest["face_core_masks"][pose]
                if self.direct_source:
                    if self.layer_views.get(expression) != self.layer_views[pose]:
                        raise ValueError(
                            f"Approved companion expression alias differs from the body binding: {expression}"
                        )
                else:
                    self.layer_views[expression] = self.layer_views[pose]


def _build_body_pack_request(request: BuildRequest) -> dict:
    """Build reviewed views and expression aliases from one validated request."""
    product_root = request.product_root
    bald_root = request.bald_root
    layers_root = request.layers_root
    output = request.output
    license_text = request.license_text
    mode = request.mode
    layer_mode = request.layer_mode
    fixed_core_root = request.fixed_core_root
    character_layers_root = request.character_layers_root
    source_manifest = request.source_manifest
    version = request.version
    if layer_mode not in {"copy", "recompute", "reuse"}:
        raise ValueError("Layer mode must be copy, recompute or reuse")
    if mode not in {"all", "eyes"}:
        raise ValueError("Build mode must be all or eyes")
    if not license_text.strip():
        raise ValueError("Provide the rights holder's license text")
    if (fixed_core_root is None) != (character_layers_root is None):
        raise ValueError("Fixed core masks and companion layer assets must be supplied together")
    if fixed_core_root is not None and source_manifest is None:
        raise ValueError("Fixed-source release builds require a source manifest")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("Provide a non-empty body-pack version")
    if source_manifest is not None:
        source_document = verify_release_source_manifest(source_manifest, product_root)
        if source_document["pack"]["version"] != version:
            raise ValueError("Requested build version differs from the release source manifest")
    _check_output_path(output)
    roots = [(product_root / "assets").resolve(), bald_root.resolve(), layers_root.resolve()]
    roots.extend(root.resolve() for root in (fixed_core_root, character_layers_root) if root is not None)
    resolved_output = output.resolve()
    if any(resolved_output.is_relative_to(root) or root.is_relative_to(resolved_output) for root in roots):
        raise ValueError("Output must be separate from every read-only input root")
    receipt = output / "build-receipt.json"
    if receipt.exists() and _input_manifest(receipt)["mode"] != mode:
        raise ValueError("Use a separate output directory for a different build mode")
    builder = _Builder(request)
    builder.build_full_body()
    builder.build_half_body()
    builder.bind_aliases()
    manifest = builder.manifest
    manifest["fingerprint"] = compute_body_pack_fingerprint(manifest)
    parse_body_pack(manifest)
    if builder.direct_source and manifest["fingerprint"] != EXPECTED_BODY_REFERENCE["fingerprint"]:
        raise ValueError(
            "Rebuilt body fingerprint differs from the approved source reference: "
            f"{manifest['fingerprint']}"
        )
    write_json(builder.pack / "manifest.json", manifest)
    reference = {key: manifest[key] for key in ("id", "version", "fingerprint")}
    write_json(builder.character / "manifest.json", {"body_pack": reference, "layer_views": builder.layer_views})
    write_json(output / "inventory.json", builder.inventory)
    stats = {"mode": mode, "body_pack": _directory_stats(builder.pack),
             "character_layers": _directory_stats(
                 builder.character_layers_root if builder.direct_source else builder.character,
                 exclude_recomputed=True,
             ),
             "fingerprint": manifest["fingerprint"],
             "missing_body_poses": builder.inventory["missing_body_poses"],
             "pending_appearance_approval": [],
             "approved_gestures": sorted(builder.gestures),
             "face_core_precleared": False}
    write_json(receipt, stats)
    return stats


def build_body_pack(product_root: Path, bald_root: Path, layers_root: Path,
                    output: Path, license_text: str, mode: str = "all", *,
                    layer_mode: str = "copy") -> dict:
    """Preserve the original public builder API for existing callers."""
    return _build_body_pack_request(BuildRequest(
        product_root=product_root, bald_root=bald_root, layers_root=layers_root,
        output=output, license_text=license_text, mode=mode, layer_mode=layer_mode,
    ))


def build_release_body_pack(request: BuildRequest) -> dict:
    """Build from the complete pinned release-source request."""
    return _build_body_pack_request(request)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("product-root", "bald-root", "layers-root", "output"):
        parser.add_argument(f"--{option}", type=Path, required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--fixed-core-root", type=Path)
    parser.add_argument("--character-layers-root", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--version")
    parser.add_argument("--zip-output", type=Path)
    partition_options = parser.add_mutually_exclusive_group()
    partition_options.add_argument("--recompute-layers", action="store_true")
    partition_options.add_argument("--reuse-recomputed-layers", action="store_true")
    parser.add_argument("--mode", choices=("all", "eyes"), default="all")
    args = parser.parse_args()
    version = args.version or "1.0.0"
    if args.source_manifest is not None:
        source = verify_release_source_manifest(args.source_manifest, args.product_root)
        source_version = source["pack"]["version"]
        if args.version is not None and args.version != source_version:
            parser.error("--version must match the version declared in --source-manifest")
        version = source_version
    stats = build_release_body_pack(BuildRequest(
        product_root=args.product_root,
        bald_root=args.bald_root,
        layers_root=args.layers_root,
        output=args.output,
        license_text=args.license,
        mode=args.mode,
        layer_mode=("recompute" if args.recompute_layers else
                    "reuse" if args.reuse_recomputed_layers else "copy"),
        fixed_core_root=args.fixed_core_root,
        character_layers_root=args.character_layers_root,
        source_manifest=args.source_manifest,
        version=version,
    ))
    archive_info = None
    archive_path = None
    if args.zip_output is not None:
        package_root = args.output / "mohan-body-v2"
        _copy_release_legal_files(args.product_root, package_root)
        archive_name = f"flameblade.mohan-body-v2-{version}.zip"
        archive_path = args.zip_output
        if archive_path.suffix.lower() != ".zip":
            archive_path = archive_path / archive_name
        elif archive_path.name != archive_name:
            parser.error(f"--zip-output filename must be {archive_name}")
        archive_info = build_reproducible_zip(package_root, archive_path)
    print(json.dumps({key: value for key, value in stats.items() if key not in {"body_pack", "character_layers"}},
                     sort_keys=True))
    print(json.dumps({key: {"files": stats[key]["files"], "bytes": stats[key]["bytes"]}
                      for key in ("body_pack", "character_layers")}, sort_keys=True))
    if archive_info is not None:
        print(json.dumps({"archive": archive_path.as_posix(),
                          "archive_bytes": archive_info["bytes"],
                          "archive_sha256": archive_info["sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
