"""Assemble the official default appearance pack and the built-in makeup pack from pipeline layers.

The layer pipeline (generation-4 reference art re-drawn on the generation-2
bare base, then subtracted step by step) leaves one directory per silhouette::

    <layers>/<silhouette>/L2_garment.png        robe (rear views include the shoes)
    <layers>/<silhouette>/L3_hair.png           loose hair, already lying over the robe
    <layers>/<silhouette>/L4_headwear.png       silver hairpiece
    <layers>/<silhouette>/L1_makeup.{eyes,cheeks,lips}.png
    <layers>/<silhouette>/report.json           pixel counts and registration shifts
    <layers>/<silhouette>/base.png              the bare base the layers were cut from (probes only)

This tool never invents art.  It maps the layers onto the v2 pack format,
crops exactly the pixels the runtime would reject (a garment pixel on the
protected face, hair on the feature core -- the eye and mouth rig cut-outs
dilated by the runtime's margin, never the whole face box, so strands keep
falling over the brow and cheeks -- headwear on the eyes and lips, makeup
outside its safe region), records every cropped pixel in a JSON report, seals
both archives with
``application.outfit_pack_builder`` and proves they parse.  Missing input is an
error, not a transparent placeholder.

Example::

    py -3.15 tools/assemble_official_default_pack.py --layers work/default-pack-layers \\
        --outfit-authoring work/blue-white-hanfu --makeup-authoring assets/makeup/builtin \\
        --official-root assets/official-packs --report work/default-pack-report.json
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import sys
lazy from dataclasses import asdict, dataclass, field
lazy from pathlib import Path

lazy import numpy as np
lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QGuiApplication, QImage, QPixmap, QRegion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from application.outfit_pack_builder import build_outfit_pack
lazy from domain.constants import POSE_ATLAS_LAYERED_ROOT_NAME
lazy from domain.outfit_pack import (
    APP_RANGE,
    OFFICIAL_PACK_ROOT,
    AUTHORING_TEMPLATE,
    AUTHORING_VERSION,
    BODY_PROFILE_ID,
    BODY_PROFILE_VERSION,
    BODY_REGIONS,
    FORMAT,
    MANIFEST,
    POSE_ATLAS_SILHOUETTES,
    VERSION,
    inspect_outfit_pack,
    official_pose_template,
)
lazy from domain.outfit_pack_makeup import (
    FEATURE_CORE_LAYERS,
    HAIRSTYLE_FEATURE_CORE_DILATION_PX,
    HALF_BODY_RIGS,
    load_makeup_safe_regions,
)
lazy from domain.outfit_pack_official import OFFICIAL_OUTFIT_ENSEMBLE_ID, OFFICIAL_OUTFIT_PACK_ID

# Character art is studio property; see ASSETS-LICENSE.md (the manifest field only
# admits letters, digits, spaces and ``.()+-``).
ASSETS_LICENSE_NAME = "All Rights Reserved - see ASSETS-LICENSE.md"
AUTHOR = "Flameblade Studio"
PACK_VERSION = "1.0.0"
APP_VERSION_RANGE = ">=4.0.0,<5.0.0"
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
PACK_NAMES = ("藍白漢服", "蓝白汉服", "Blue-and-White Hanfu", "藍白漢服")
GARMENT_ITEM, GARMENT_VARIANT = "hanfu-robe", "blue-white"
GARMENT_NAMES = ("藍白漢服袍", "蓝白汉服袍", "Blue-and-White Hanfu Robe", "藍白漢服の袍")
GARMENT_VARIANT_NAMES = ("藍白", "蓝白", "Blue and white", "藍白")
HAIR_ITEM, HAIR_VARIANT = "loose-hair", "ink-black"
HAIR_NAMES = ("散髮", "散发", "Loose Hair", "下ろし髪")
HAIR_VARIANT_NAMES = ("墨黑", "墨黑", "Ink black", "墨黒")
HEADWEAR_ITEM, HEADWEAR_VARIANT = "silver-hairpiece", "silver"
HEADWEAR_NAMES = ("銀髮飾", "银发饰", "Silver Hairpiece", "銀の髪飾り")
HEADWEAR_VARIANT_NAMES = ("銀", "银", "Silver", "銀")
# Paint order inside the pack: robe, then the hair that already lies over it, then the hairpiece.
GARMENT_Z, HAIR_BACK_Z, HAIR_FRONT_Z, HEADWEAR_Z = 10, 0, 20, 30
# The robe leaves the neck bare; every other official skin region is covered.
VISIBLE_REGIONS = frozenset({"neck"})
# The ``light`` makeup variant is the classic layer set with its alpha scaled by this factor.
LIGHT_ALPHA_FACTOR = 0.55
LIGHT_VARIANT, CLASSIC_VARIANT = "light", "classic"
OPAQUE = 255
# A pipeline registration shift above this many pixels is reported as flagged.
REGISTRATION_FLAG_PX = 3.0
# Mirrors ActiveOutfitOverlay._forbidden_face_region: the slice of the protected face the
# crown mask may touch, as (numerator, denominator) of the bbox.
CROWN_HEIGHT = (1, 5)
# Hair declares no face rule: the runtime clips it out of the feature core only (and
# feathers that edge), so the assembler crops exactly that dilated core and nothing else.
HAIR_FACE_MASK = "none"
# Mirrors domain.outfit_pack_makeup.EXCLUSION_RIG_LAYERS: (painted, covering) pairs whose difference never receives makeup.
MAKEUP_EXCLUSIONS = ((("iris_left", "iris_right"), ("eyelid_left", "eyelid_right")), (("oral_cavity", "teeth_tongue"), ("lip_upper", "lip_lower")))
MAKEUP_SLOTS = ("eyes", "cheeks", "lips")
LAYER_FILES = {
    "garment": "L2_garment.png",
    "hair": "L3_hair.png",
    "headwear": "L4_headwear.png",
    "eyes": "L1_makeup.eyes.png",
    "cheeks": "L1_makeup.cheeks.png",
    "lips": "L1_makeup.lips.png",
}
GREY_TOLERANCE = 10
GREY_MIN, GREY_MAX = 70, 200
NO_CANDIDATE = -1_000_000
GREY_PREFERENCE = 1000


@dataclass(frozen=True, slots=True)
class Forbidden:
    """Per-silhouette pixel masks a layer of each category may not paint (True = forbidden)."""

    garment: np.ndarray
    hair: np.ndarray
    headwear: np.ndarray
    makeup_excluded: np.ndarray
    face_bbox: tuple[int, int, int, int]


@dataclass(slots=True)
class SilhouetteResult:
    silhouette: str
    source_sha256: dict[str, str] = field(default_factory=dict)
    opaque_pixels: dict[str, int] = field(default_factory=dict)
    cropped_pixels: dict[str, int] = field(default_factory=dict)
    hair_face_mask: str = "none"
    face_bbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    headwear_bbox: tuple[int, int, int, int] | None = None
    registration_flags: dict[str, list[float]] = field(default_factory=dict)
    probes: dict[str, object] = field(default_factory=dict)


def names(values: tuple[str, str, str, str]) -> dict[str, str]:
    return dict(zip(LANGUAGES, values, strict=True))


def read_rgba(path: Path) -> np.ndarray:
    image = QImage(str(path))
    if image.isNull():
        raise SystemExit(f"Unreadable layer: {path}")
    image = image.convertToFormat(QImage.Format_RGBA8888)
    width, height = image.width(), image.height()
    rows = np.frombuffer(bytes(image.constBits()), np.uint8).reshape(height, image.bytesPerLine())
    return rows[:, : width * 4].reshape(height, width, 4).copy()


def write_png(path: Path, rgba: np.ndarray) -> bytes:
    height, width = rgba.shape[:2]
    payload = np.ascontiguousarray(rgba).tobytes()
    image = QImage(payload, width, height, width * 4, QImage.Format_RGBA8888).copy()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(path), "PNG"):
        raise SystemExit(f"Could not write {path}")
    return path.read_bytes()


def region_mask(region: QRegion, shape: tuple[int, int]) -> np.ndarray:
    mask = np.zeros(shape, dtype=bool)
    for rect in region:
        mask[rect.y() : rect.y() + rect.height(), rect.x() : rect.x() + rect.width()] = True
    return mask


def rig_region(rig_root: Path, prefix: str, layer: str) -> QRegion:
    source = QPixmap(str(rig_root / f"{prefix}_{layer}.png"))
    return QRegion() if source.isNull() else QRegion(source.mask())


def rect_mask(shape: tuple[int, int], rect: QRect) -> np.ndarray:
    return region_mask(QRegion(rect), shape)


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    """Chebyshev dilation by ``radius`` pixels: 8-neighbour steps, exactly like the runtime."""
    grown = mask.copy()
    height, width = mask.shape
    for _step in range(radius):
        padded = np.pad(grown, 1)
        grown = np.zeros_like(grown)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                grown |= padded[dy : dy + height, dx : dx + width]
    return grown


def _scaled(value: int, fraction: tuple[int, int]) -> int:
    return max(1, value * fraction[0] // fraction[1])


def forbidden_regions(silhouette: str, shape: tuple[int, int]) -> Forbidden:
    """Rebuild the runtime's protected-face and feature clips for one silhouette."""
    full_body = silhouette in POSE_ATLAS_SILHOUETTES
    rig_root = ROOT / "assets" / "pose-atlas" / POSE_ATLAS_LAYERED_ROOT_NAME if full_body else ROOT / "assets" / "expressions" / "layered"
    prefix = silhouette if full_body else HALF_BODY_RIGS[silhouette]
    face = rig_region(rig_root, prefix, "base")
    features = QRegion()
    for layer in FEATURE_CORE_LAYERS:
        features = features.united(rig_region(rig_root, prefix, layer))
    face_mask, feature_mask = region_mask(face, shape), region_mask(features, shape)
    excluded = QRegion()
    for painted_layers, covering_layers in MAKEUP_EXCLUSIONS:
        painted, covering = QRegion(), QRegion()
        for layer in painted_layers:
            painted = painted.united(rig_region(rig_root, prefix, layer))
        for layer in covering_layers:
            covering = covering.united(rig_region(rig_root, prefix, layer))
        excluded = excluded.united(painted.subtracted(covering))
    bounds = face.boundingRect()
    crown = np.zeros(shape, dtype=bool)
    if not face.isEmpty():
        crown = rect_mask(shape, QRect(bounds.x(), bounds.y(), bounds.width(), _scaled(bounds.height(), CROWN_HEIGHT)))
    return Forbidden(
        garment=face_mask,
        hair=dilate(feature_mask, HAIRSTYLE_FEATURE_CORE_DILATION_PX),
        headwear=(face_mask & ~crown) | feature_mask,
        makeup_excluded=region_mask(excluded, shape),
        face_bbox=(bounds.x(), bounds.y(), bounds.width(), bounds.height()),
    )


def crop(layer: np.ndarray, forbidden: np.ndarray) -> tuple[np.ndarray, int]:
    """Clear every non-transparent pixel inside ``forbidden``; returns the count removed."""
    hit = (layer[:, :, 3] > 0) & forbidden
    cleared = layer.copy()
    cleared[hit] = 0
    return cleared, int(hit.sum())


def alpha_bbox(layer: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(layer[:, :, 3])
    if not len(xs):
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))


def scale_alpha(layer: np.ndarray, factor: float) -> np.ndarray:
    scaled = layer.copy()
    scaled[:, :, 3] = np.rint(layer[:, :, 3].astype(np.float64) * factor).astype(np.uint8)
    scaled[scaled[:, :, 3] == 0] = 0
    return scaled


def _probe(candidates: np.ndarray, score: np.ndarray) -> tuple[int, int] | None:
    scored = np.where(candidates, score, NO_CANDIDATE)
    if scored.max() == NO_CANDIDATE:
        return None
    y, x = np.unravel_index(int(scored.argmax()), scored.shape)
    return (int(x), int(y))


def probes(base: np.ndarray, layers: dict[str, np.ndarray], makeup_excluded: np.ndarray) -> dict[str, object]:
    """Test anchors: a blue robe pixel over grey base, a hair pixel, a hairpiece pixel and the strongest lip pixel."""
    garment, hair, headwear, lips = (layers[key] for key in ("garment", "hair", "headwear", "lips"))
    channels = base[:, :, :3].astype(np.int16)
    grey = (
        (base[:, :, 3] == OPAQUE)
        & (np.abs(channels[:, :, 0] - channels[:, :, 1]) < GREY_TOLERANCE)
        & (np.abs(channels[:, :, 1] - channels[:, :, 2]) < GREY_TOLERANCE)
        & (channels[:, :, 0] > GREY_MIN)
        & (channels[:, :, 0] < GREY_MAX)
    )
    uncovered = (hair[:, :, 3] == 0) & (headwear[:, :, 3] == 0)
    blueness = garment[:, :, 2].astype(np.int32) - garment[:, :, 0]
    # Hair and hairpiece probes prefer a pixel over the grey base top, well away from the protected face.
    prefer_grey = grey.astype(np.int32) * GREY_PREFERENCE
    found = {
        "garment_blue_on_grey": _probe((garment[:, :, 3] == OPAQUE) & grey & uncovered, blueness),
        "hair": _probe((hair[:, :, 3] == OPAQUE) & (headwear[:, :, 3] == 0), prefer_grey),
        "headwear": _probe(headwear[:, :, 3] == OPAQUE, prefer_grey),
        "lips": _probe((lips[:, :, 3] > 0) & ~makeup_excluded & (garment[:, :, 3] == 0) & uncovered, lips[:, :, 3].astype(np.int32)),
    }
    return {
        key: None if point is None else {"xy": list(point), "layer_rgba": layers[key.split("_")[0]][point[1], point[0]].tolist()}
        for key, point in found.items()
    }


def asset_entry(slot: str, path: str, z_order: int) -> dict[str, object]:
    # sha256/width/height are sealed in by tools/build_outfit_pack.py from the PNG bytes.
    return {"slot": slot, "path": path, "sha256": "", "width": 0, "height": 0, "anchor": [0, 0], "z_order": z_order}


def registration_flags(report_path: Path) -> dict[str, list[float]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    flags = {}
    for step, entry in report.get("layers", {}).items():
        shift = entry.get("registration_shift_px") if isinstance(entry, dict) else None
        if shift is not None and max(abs(shift[0]), abs(shift[1])) > REGISTRATION_FLAG_PX:
            flags[step] = shift
    return flags


def process_silhouette(source: Path, silhouette: str, outfit_assets: Path, makeup_root: Path, makeup_paths: dict) -> SilhouetteResult:
    """Crop, split and write every layer of one silhouette; returns what was done."""
    result = SilhouetteResult(silhouette)
    layers = {}
    for key, filename in LAYER_FILES.items():
        path = source / filename
        if not path.is_file():
            raise SystemExit(f"Missing pipeline layer for {silhouette}: {path}")
        result.source_sha256[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        layers[key] = read_rgba(path)
    shape = layers["garment"].shape[:2]
    forbidden = forbidden_regions(silhouette, shape)
    result.face_bbox = forbidden.face_bbox
    layers["garment"], result.cropped_pixels["garment"] = crop(layers["garment"], forbidden.garment)
    result.hair_face_mask = HAIR_FACE_MASK
    layers["hair"], result.cropped_pixels["hair"] = crop(layers["hair"], forbidden.hair)
    layers["headwear"], result.cropped_pixels["headwear"] = crop(layers["headwear"], forbidden.headwear)
    result.headwear_bbox = alpha_bbox(layers["headwear"])
    safe = load_makeup_safe_regions()[silhouette]
    for slot in MAKEUP_SLOTS:
        allowed = np.zeros(shape, dtype=bool)
        for x, y, width, height in safe.rects(slot):
            allowed[y : y + height, x : x + width] = True
        layers[slot], result.cropped_pixels[slot] = crop(layers[slot], ~allowed)
        write_png(makeup_root / makeup_paths[(CLASSIC_VARIANT, silhouette, slot)], layers[slot])
        write_png(makeup_root / makeup_paths[(LIGHT_VARIANT, silhouette, slot)], scale_alpha(layers[slot], LIGHT_ALPHA_FACTOR))
    write_png(outfit_assets / f"{GARMENT_ITEM}-{GARMENT_VARIANT}-{silhouette}-outerwear.png", layers["garment"])
    write_png(outfit_assets / f"{HAIR_ITEM}-{HAIR_VARIANT}-{silhouette}-front.png", layers["hair"])
    write_png(outfit_assets / f"{HAIR_ITEM}-{HAIR_VARIANT}-{silhouette}-back.png", np.zeros_like(layers["hair"]))
    write_png(outfit_assets / f"{HEADWEAR_ITEM}-{HEADWEAR_VARIANT}-{silhouette}-headwear.png", layers["headwear"])
    result.opaque_pixels = {key: int((layer[:, :, 3] > 0).sum()) for key, layer in layers.items()}
    result.registration_flags = registration_flags(source / "report.json")
    if (source / "base.png").is_file():
        result.probes = probes(read_rgba(source / "base.png"), layers, forbidden.makeup_excluded)
    return result


def outfit_manifest(results: dict[str, SilhouetteResult]) -> dict[str, object]:
    silhouettes = tuple(results)
    garment_poses = {
        silhouette: [asset_entry("outerwear", f"assets/{GARMENT_ITEM}-{GARMENT_VARIANT}-{silhouette}-outerwear.png", GARMENT_Z)]
        for silhouette in silhouettes
    }
    hair_poses = {
        silhouette: [
            asset_entry("back", f"assets/{HAIR_ITEM}-{HAIR_VARIANT}-{silhouette}-back.png", HAIR_BACK_Z),
            asset_entry("front", f"assets/{HAIR_ITEM}-{HAIR_VARIANT}-{silhouette}-front.png", HAIR_FRONT_Z),
        ]
        for silhouette in silhouettes
    }
    headwear_poses = {
        silhouette: [asset_entry("headwear", f"assets/{HEADWEAR_ITEM}-{HEADWEAR_VARIANT}-{silhouette}-headwear.png", HEADWEAR_Z)]
        for silhouette in silhouettes
    }
    visibility = {region: "visible" if region in VISIBLE_REGIONS else "covered" for region in BODY_REGIONS}
    return {
        "format": FORMAT,
        "version": VERSION,
        "id": OFFICIAL_OUTFIT_PACK_ID,
        "pack_version": PACK_VERSION,
        "app_range": APP_VERSION_RANGE,
        "display_names": names(PACK_NAMES),
        "compatible_body_profile": {"id": BODY_PROFILE_ID, "version": BODY_PROFILE_VERSION},
        "source": {"kind": "original", "author": AUTHOR, "license": ASSETS_LICENSE_NAME, "reference_included": False},
        "authoring": {"template": AUTHORING_TEMPLATE, "version": AUTHORING_VERSION},
        "looks": [{
            "id": GARMENT_ITEM,
            "display_names": names(GARMENT_NAMES),
            "variants": [{
                "id": GARMENT_VARIANT,
                "display_names": names(GARMENT_VARIANT_NAMES),
                "fabric_behavior": "draped",
                "body_visibility": {silhouette: dict(visibility) for silhouette in silhouettes},
                "poses": garment_poses,
            }],
        }],
        "hairstyles": [{
            "id": HAIR_ITEM,
            "display_names": names(HAIR_NAMES),
            "variants": [{
                "id": HAIR_VARIANT,
                "display_names": names(HAIR_VARIANT_NAMES),
                "poses": hair_poses,
                "face_occlusion_masks": {silhouette: results[silhouette].hair_face_mask for silhouette in silhouettes},
                "hand_occlusion": dict.fromkeys(silhouettes, "behind-hands"),
                "garment_occlusion": dict.fromkeys(silhouettes, "front-of-collar"),
            }],
        }],
        "headwear": [{
            "id": HEADWEAR_ITEM,
            "display_names": names(HEADWEAR_NAMES),
            "attachment_point": "crown",
            "safe_mask": "crown-safe",
            "variants": [{"id": HEADWEAR_VARIANT, "display_names": names(HEADWEAR_VARIANT_NAMES), "poses": headwear_poses}],
        }],
        "accessories": [],
        "ensembles": [{
            "id": OFFICIAL_OUTFIT_ENSEMBLE_ID,
            "display_names": names(PACK_NAMES),
            "selections": {
                "garment": {"item_id": GARMENT_ITEM, "variant_id": GARMENT_VARIANT},
                "hairstyle": {"item_id": HAIR_ITEM, "variant_id": HAIR_VARIANT},
                "headwear": {"item_id": HEADWEAR_ITEM, "variant_id": HEADWEAR_VARIANT},
                "weapon": None,
                "handheld": None,
                "jewelry": None,
                "foreground-effect": None,
            },
            "autonomous_profile": {
                "thermal_bands": ["hot", "warm", "mild", "cool", "cold"],
                "weather": ["clear", "cloudy", "rain", "storm", "snow", "windy", "indoor"],
                "moods": ["calm", "cheerful", "affectionate", "reserved", "upset", "focused"],
                "occasions": ["everyday", "work", "formal", "holiday"],
                "priority": 0,
            },
        }],
    }


def makeup_layer_paths(template: Path) -> dict[tuple[str, str, str], str]:
    """(variant, silhouette, slot) -> relative PNG path declared by the scaffolded template."""
    manifest = json.loads(template.read_text(encoding="utf-8"))
    paths = {}
    for item in manifest["makeup"]:
        for variant in item["variants"]:
            for silhouette, entries in variant["poses"].items():
                for entry in entries:
                    paths[(variant["id"], silhouette, entry["slot"])] = entry["path"]
    return paths


def seal(manifest_path: Path, asset_root: Path, output: Path, replace: bool) -> str:
    if output.exists():
        if not replace:
            raise SystemExit(f"{output} exists; pass --replace to rebuild it.")
        output.unlink()
    build_outfit_pack(manifest_path, asset_root, output)
    pack = inspect_outfit_pack(output)
    print(f"sealed {output} ({output.stat().st_size} bytes, id {pack.pack_id})")
    return hashlib.sha256(output.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--layers", type=Path, required=True, help="directory with one <silhouette>/ folder per required silhouette")
    parser.add_argument("--outfit-authoring", type=Path, required=True, help="where manifest.json + assets/ of the outfit pack are written")
    parser.add_argument("--makeup-authoring", type=Path, default=ROOT / "assets" / "makeup" / "builtin", help="scaffolded makeup template root")
    parser.add_argument("--official-root", type=Path, default=None, help="sealed archives go here (default: domain OFFICIAL_PACK_ROOT)")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--replace", action="store_true", help="rebuild sealed archives that already exist")
    arguments = parser.parse_args(argv)
    QGuiApplication.instance() or QGuiApplication([])
    template = official_pose_template()
    if not APP_RANGE.fullmatch(APP_VERSION_RANGE):
        raise SystemExit("Invalid app range.")
    makeup_paths = makeup_layer_paths(arguments.makeup_authoring / MANIFEST)
    results = {}
    for silhouette in template["required_silhouettes"]:
        source = arguments.layers / silhouette
        if not source.is_dir():
            raise SystemExit(f"Missing silhouette directory: {source}")
        results[silhouette] = process_silhouette(
            source, silhouette, arguments.outfit_authoring / "assets", arguments.makeup_authoring, makeup_paths
        )
        print(f"{silhouette}: cropped {results[silhouette].cropped_pixels} hair mask {results[silhouette].hair_face_mask}")
    manifest_path = arguments.outfit_authoring / MANIFEST
    manifest_path.write_text(json.dumps(outfit_manifest(results), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    official_root = OFFICIAL_PACK_ROOT if arguments.official_root is None else arguments.official_root
    outfit_name = f"{OFFICIAL_OUTFIT_PACK_ID}.mohan-outfit"
    outfit_sha = seal(manifest_path, arguments.outfit_authoring, official_root / outfit_name, arguments.replace)
    makeup_id = json.loads((arguments.makeup_authoring / MANIFEST).read_text(encoding="utf-8"))["id"]
    makeup_sha = seal(arguments.makeup_authoring / MANIFEST, arguments.makeup_authoring, official_root / f"{makeup_id}.mohan-outfit", arguments.replace)
    report = {
        "light_alpha_factor": LIGHT_ALPHA_FACTOR,
        "sealed": {outfit_name: outfit_sha, f"{makeup_id}.mohan-outfit": makeup_sha},
        "silhouettes": {silhouette: asdict(result) for silhouette, result in results.items()},
    }
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=list) + "\n", encoding="utf-8")
    print(arguments.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
