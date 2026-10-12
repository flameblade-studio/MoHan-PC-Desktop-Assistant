"""Verify a generated body pack through the installed runtime renderer."""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import os
lazy import sys
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, field
lazy from io import BytesIO
lazy from math import ceil
lazy from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import numpy as np
lazy from PIL import Image, ImageDraw, ImageFilter
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPixmap

lazy from application.character_runtime_bootstrap import activate_product_character_runtime
lazy from domain.body_pack import parse_body_pack_reference
lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from domain.character_layer_plan import (
    CharacterLayerAsset,
    CharacterLayerMask,
    CharacterLayerPlan,
    parse_character_layer_views,
)
lazy from domain.face_rig import ExpressionShape, FaceMotionFrame, FacePose, MouthShape, Viseme
lazy from domain.qt_image_io import load_pixmap_png
lazy from infrastructure.body_pack_reader import BodyPackReader
lazy from infrastructure.body_pack_renderer import BodyPackRenderer


BODY_PACK_ID = "mohan-body-v2"
BODY_PACK_DIRECTORY = "mohan-body-v2"
LAYER_PACK_DIRECTORY = "lin-keyun-layers"
LAYER_MANIFEST_NAME = "manifest.json"
GESTURE_VIEWS = ("front-eureka", "front-mock-scold", "front-mock-hit")
HALF_BODY_VIEWS = ("front-crossed", "left-neutral", "cheek-rest", "exasperated", *GESTURE_VIEWS)
EXPRESSION_ALIASES = ("proud_front", "worried_front")
YAW_ZERO_SAMPLE_STATES = ("a-rest", "a-closed", "o-half", "small-closed")
HALF_FRONT_SAMPLE_STATES = ("a-rest", "a-closed", "o-half", "small-closed")
HALF_ALIAS_SAMPLE_STATES = ("neutral-rest", "neutral-closed")
SEAM_RING_RADIUS = 3
MAX_OUTSIDE_CORE_DELTA = 1
OPAQUE_ALPHA = 255
FACE_CROP_SCALE = 3
FACE_CROP_MARGIN_PX = 20
REPORT_SCHEMA = "mohan.body-pack-build-verification.v1"
DEFAULT_BUILD_ROOT = ROOT / ".quality-tmp" / "body-pack-build"
DEFAULT_LAYERS_ROOT = Path(
    "D:/FlamebladeStudio/CodexProjects/2026-09-29/mohan-lk-native/.quality-tmp"
)
DEFAULT_OUTPUT = ROOT / ".quality-tmp" / "body-install-1" / "render"
RGBA_CHANNELS = 4
RGB_CHANNELS = 3
_GUI_APPLICATION: QGuiApplication | None = None


@dataclass(frozen=True, slots=True)
class CoreEvidence:
    mask: np.ndarray
    mask_path: Path
    mask_origin: str


@dataclass(frozen=True, slots=True)
class ComparisonRequest:
    label: str
    view: str
    reference_path: Path
    reference: Image.Image
    rendered: Image.Image
    core: CoreEvidence
    group: str
    face_crop: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StateRequest:
    label: str
    reference_view: str
    render_view: str
    motion: object
    halfbody: bool
    api: str
    blink_after_render: str | None = None
    requested_state: str = ""


@dataclass(slots=True)
class VerificationContext:
    build_root: Path
    body_root: Path
    layer_root: Path
    layers_root: Path
    output: Path
    reader: BodyPackReader
    layer_views: Mapping[str, CharacterLayerPlan]
    renderer: BodyPackRenderer
    comparisons: list[dict[str, object]] = field(default_factory=list)
    errors: list[dict[str, object]] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)


def _gui_application() -> QGuiApplication:
    global _GUI_APPLICATION
    existing = QGuiApplication.instance()
    if existing is not None:
        return existing
    _GUI_APPLICATION = QGuiApplication([])
    return _GUI_APPLICATION


def _read_json_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _contained_root(path: Path, label: str) -> Path:
    if path.is_symlink() or path.is_junction():
        raise ValueError(f"{label} cannot be a symbolic link or junction: {path}")
    resolved = path.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError(f"{label} must be a directory: {path}")
    return resolved


def _load_body_reader(body_root: Path) -> BodyPackReader:
    manifest = _read_json_object(body_root / LAYER_MANIFEST_NAME)
    reference = parse_body_pack_reference(
        {key: manifest.get(key) for key in ("id", "version", "fingerprint")}
    )
    if reference.id != BODY_PACK_ID:
        raise ValueError(f"Expected body pack {BODY_PACK_ID!r}, found {reference.id!r}.")
    return BodyPackReader(body_root, reference)


def _load_layer_views(layer_root: Path, reference: object) -> Mapping[str, CharacterLayerPlan]:
    payload = _read_json_object(layer_root / LAYER_MANIFEST_NAME)
    if set(payload) != {"body_pack", "layer_views"}:
        raise ValueError(
            "lin-keyun-layers/manifest.json must contain exactly body_pack and layer_views."
        )
    if parse_body_pack_reference(payload["body_pack"]) != reference:
        raise ValueError("The character layers reference a different body pack.")
    return parse_character_layer_views(payload["layer_views"])


def _context_from_args(args: argparse.Namespace) -> VerificationContext:
    build_root = _contained_root(args.build_root, "Build output root")
    body_root = _contained_root(build_root / BODY_PACK_DIRECTORY, "Body-pack root")
    layer_root = _contained_root(build_root / LAYER_PACK_DIRECTORY, "Character-layer pack root")
    layers_root = _contained_root(args.layers_root, "Original layer source root")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    _gui_application()
    reader = _load_body_reader(body_root)
    layer_views = _load_layer_views(layer_root, reader.reference)
    renderer = BodyPackRenderer(reader, layer_views, _layer_loader(layer_root))
    return VerificationContext(
        build_root,
        body_root,
        layer_root,
        layers_root,
        output,
        reader,
        layer_views,
        renderer,
    )


def _safe_layer_path(root: Path, record: CharacterLayerAsset | CharacterLayerMask) -> Path:
    relative = PurePosixPath(record.path)
    if (
        not record.path
        or relative.is_absolute()
        or "\\" in record.path
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError(f"Unsafe character-layer path: {record.path!r}")
    candidate = root.joinpath(*relative.parts)
    if candidate.is_symlink() or candidate.is_junction():
        raise ValueError(f"Character-layer assets cannot be links: {record.path}")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError(f"Character-layer path escapes its pack: {record.path}")
    for ancestor in candidate.parents:
        if ancestor == root:
            break
        if ancestor.is_symlink() or ancestor.is_junction():
            raise ValueError(f"Character-layer ancestors cannot be links: {record.path}")
    if not resolved.is_file():
        raise ValueError(f"Character-layer path is not a regular file: {record.path}")
    return resolved


def _layer_loader(layer_root: Path):
    def load(record: CharacterLayerAsset | CharacterLayerMask) -> bytes:
        return _safe_layer_path(layer_root, record).read_bytes()

    return load


def _source_candidates(layers_root: Path, partition: str, view: str) -> tuple[Path, ...]:
    view_root = layers_root / partition / "round9" / view
    round_root = layers_root / partition / "round9"
    return (
        view_root / "A-birefnet.png",
        view_root / "approved-matted-aligned.png",
        view_root / "composite.png",
        round_root / f"{view}.png",
        view_root / "neutral.png",
        view_root / "render.png",
    )


def _source_partitions(halfbody: bool) -> tuple[str, ...]:
    if halfbody:
        return ("lk-hair-H",)
    return ("lk-hair-F1", "lk-hair-F2")


def _find_source(
    layers_root: Path,
    view: str,
    *,
    halfbody: bool,
    optional: bool = False,
) -> Path | None:
    if view in GESTURE_VIEWS:
        source = layers_root / "gestures3" / view / "A.png"
        if source.is_file():
            return source.resolve(strict=True)
    for partition in _source_partitions(halfbody):
        candidates = _source_candidates(layers_root, partition, view)
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve(strict=True)
    if optional:
        return None
    raise FileNotFoundError(f"No neutral composite found for {view!r}.")


def _rgba_image(payload: bytes, label: str) -> Image.Image:
    with Image.open(BytesIO(payload)) as opened:
        if opened.format != "PNG":
            raise ValueError(f"Expected PNG image: {label}")
        return opened.convert("RGBA").copy()


def _read_source(path: Path) -> Image.Image:
    return _rgba_image(path.read_bytes(), str(path))


def _pixmap_image(pixmap: QPixmap) -> Image.Image:
    if pixmap.isNull():
        raise ValueError("The body renderer returned a null QPixmap.")
    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    payload = bytes(image.constBits()[: image.sizeInBytes()])
    return Image.frombytes("RGBA", (image.width(), image.height()), payload)


def _installed_mask(reader: BodyPackReader, view: str) -> np.ndarray:
    payload = reader.load_face_core(view)
    if payload is None:
        raise ValueError(f"The body pack has no face-core mask for {view!r}.")
    image = _rgba_image(payload, f"body-pack face-core mask {view}")
    return np.asarray(image, dtype=np.uint8)[..., 3] > 0


def _core_evidence(
    reader: BodyPackReader,
    body_root: Path,
    rendered_view: str,
) -> CoreEvidence:
    records = dict(reader.manifest.face_core_masks)
    record = records.get(rendered_view)
    if record is None:
        raise ValueError(f"The body pack has no declared face-core mask for {rendered_view!r}.")
    mask = _installed_mask(reader, rendered_view)
    mask_path = body_root.joinpath(*PurePosixPath(record.path).parts)
    return CoreEvidence(mask, mask_path, "built-body-pack-alpha-greater-than-zero")


def _qt_reference(path: Path) -> Image.Image:
    pixmap = QPixmap()
    if not load_pixmap_png(pixmap, path.read_bytes()):
        raise ValueError(f"Qt could not decode the source PNG: {path}")
    return _pixmap_image(pixmap)


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    source = Image.fromarray(mask.astype(np.uint8) * 255)
    expanded = source.filter(ImageFilter.MaxFilter(size=radius * 2 + 1))
    return np.asarray(expanded, dtype=np.uint8) > 0


def _mask_bbox(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def _authored_face_mask(
    layers_root: Path,
    reference_path: Path,
    reference_view: str,
) -> tuple[np.ndarray, Path]:
    partition = reference_path.relative_to(layers_root).parts[0]
    mask_path = (layers_root / "gestures3" / reference_view / "face-core-mask.png"
                 if reference_view in GESTURE_VIEWS else
                 layers_root / partition / "round9" / reference_view / "face-core-mask.png")
    if not mask_path.is_file():
        raise FileNotFoundError(f"Missing authored round9 face-core mask: {mask_path}")
    with Image.open(mask_path) as opened:
        if opened.format != "PNG":
            raise ValueError(f"Expected PNG authored face-core mask: {mask_path}")
        if "A" in opened.getbands() or "transparency" in opened.info:
            channel = opened.convert("RGBA").getchannel("A")
        else:
            channel = opened.convert("L")
        mask = np.asarray(channel, dtype=np.uint8) > 0
    return mask, mask_path.resolve(strict=True)


def _delta_metrics(left: np.ndarray, right: np.ndarray, region: np.ndarray) -> dict[str, object]:
    compared = int(np.count_nonzero(region))
    if compared == 0:
        return {
            "compared_pixels": 0,
            "max_abs_channel_delta": 0,
            "changed_pixel_count": 0,
            "pixels_over_1": 0,
            "mean_abs_channel_delta": 0.0,
        }
    delta = np.abs(left.astype(np.int16) - right.astype(np.int16))
    local = delta[region]
    pixel_max = np.max(local, axis=1)
    return {
        "compared_pixels": compared,
        "max_abs_channel_delta": int(np.max(local)),
        "changed_pixel_count": int(np.count_nonzero(pixel_max > 0)),
        "pixels_over_1": int(np.count_nonzero(pixel_max > MAX_OUTSIDE_CORE_DELTA)),
        "mean_abs_channel_delta": round(float(np.mean(local)), 6),
    }


def _composite_over(rgba: np.ndarray, background: int) -> np.ndarray:
    alpha = rgba[..., 3:4].astype(np.uint16)
    color = rgba[..., :RGB_CHANNELS].astype(np.uint16)
    background_pixels = np.full_like(color, background, dtype=np.uint16)
    return ((color * alpha + background_pixels * (255 - alpha) + 127) // 255).astype(
        np.uint8
    )


def _region_metrics(
    reference: np.ndarray,
    rendered: np.ndarray,
    region: np.ndarray,
) -> dict[str, object]:
    return {
        "rgba": _delta_metrics(reference, rendered, region),
        "visible_on_black": _delta_metrics(
            _composite_over(reference, 0), _composite_over(rendered, 0), region
        ),
        "visible_on_white": _delta_metrics(
            _composite_over(reference, 255), _composite_over(rendered, 255), region
        ),
    }


def _measure_pair(
    reference: Image.Image,
    rendered: Image.Image,
    core_mask: np.ndarray,
) -> dict[str, object]:
    if reference.size != rendered.size:
        raise ValueError(f"Canvas mismatch: source {reference.size}, rendered {rendered.size}.")
    if core_mask.shape != (reference.height, reference.width):
        raise ValueError("The source face-core mask does not match the comparison canvas.")
    reference_pixels = np.asarray(reference, dtype=np.uint8)
    rendered_pixels = np.asarray(rendered, dtype=np.uint8)
    outside = ~core_mask
    seam = _dilate(core_mask, SEAM_RING_RADIUS) & outside
    return {
        "canvas": [reference.width, reference.height],
        "core_mask_pixels": int(np.count_nonzero(core_mask)),
        "core_mask_bbox_xyxy": _mask_bbox(core_mask),
        "outside_core": _region_metrics(reference_pixels, rendered_pixels, outside),
        "face_core": _region_metrics(reference_pixels, rendered_pixels, core_mask),
        "outside_core_seam_ring": {
            "thickness_px": SEAM_RING_RADIUS,
            **_region_metrics(reference_pixels, rendered_pixels, seam),
        },
        "all_pixels": _region_metrics(
            reference_pixels,
            rendered_pixels,
            np.ones(core_mask.shape, dtype=bool),
        ),
    }


def _premultiplied_rgb(pixels: np.ndarray) -> np.ndarray:
    alpha = pixels[..., 3:4].astype(np.uint16)
    rgb = pixels[..., :RGB_CHANNELS].astype(np.uint16)
    return ((rgb * alpha + 127) // 255).astype(np.uint8)


def _qt_region_metrics(
    reference: np.ndarray,
    rendered: np.ndarray,
    region: np.ndarray,
) -> dict[str, object]:
    return {
        "premultiplied_rgb": _delta_metrics(
            _premultiplied_rgb(reference), _premultiplied_rgb(rendered), region
        ),
        "alpha": _delta_metrics(reference[..., 3:4], rendered[..., 3:4], region),
    }


def _measure_qt_visible_pair(
    reference: Image.Image,
    rendered: Image.Image,
    core_mask: np.ndarray,
) -> dict[str, object]:
    if reference.size != rendered.size:
        raise ValueError(f"Canvas mismatch: Qt reference {reference.size}, renderer {rendered.size}.")
    if core_mask.shape != (reference.height, reference.width):
        raise ValueError("The built face-core mask does not match the comparison canvas.")
    reference_pixels = np.asarray(reference, dtype=np.uint8)
    rendered_pixels = np.asarray(rendered, dtype=np.uint8)
    outside = ~core_mask
    seam = _dilate(core_mask, SEAM_RING_RADIUS) & outside
    return {
        "canvas": [reference.width, reference.height],
        "core_mask_pixels": int(np.count_nonzero(core_mask)),
        "core_mask_bbox_xyxy": _mask_bbox(core_mask),
        "outside_core": _qt_region_metrics(reference_pixels, rendered_pixels, outside),
        "face_core": _qt_region_metrics(reference_pixels, rendered_pixels, core_mask),
        "outside_core_seam_ring": {
            "thickness_px": SEAM_RING_RADIUS,
            **_qt_region_metrics(reference_pixels, rendered_pixels, seam),
        },
        "all_pixels": _qt_region_metrics(
            reference_pixels, rendered_pixels, np.ones(core_mask.shape, dtype=bool)
        ),
    }


def _heatmap(
    reference: Image.Image,
    rendered: Image.Image,
    core_mask: np.ndarray,
    *,
    outside_only: bool,
) -> Image.Image:
    left = np.asarray(reference, dtype=np.uint8)
    right = np.asarray(rendered, dtype=np.uint8)
    delta = np.abs(left.astype(np.int16) - right.astype(np.int16))
    strength = np.max(delta, axis=2)
    changed = strength > 0
    if outside_only:
        changed &= ~core_mask
    pixels = np.zeros((*strength.shape, RGBA_CHANNELS), dtype=np.uint8)
    one_level = changed & (strength <= MAX_OUTSIDE_CORE_DELTA)
    larger = changed & ~one_level
    pixels[one_level] = (255, 190, 0, 230)
    pixels[larger] = (255, 38, 48, 245)
    return Image.fromarray(pixels)


def _save_face_crop(
    path: Path,
    reference: Image.Image,
    rendered: Image.Image,
    crop_mask: np.ndarray,
    difference_mask: np.ndarray,
) -> list[int]:
    if crop_mask.shape != (reference.height, reference.width):
        raise ValueError("The authored face-core mask does not match the crop canvas.")
    bbox = _mask_bbox(crop_mask)
    if bbox is None:
        raise ValueError("Cannot create a face crop from an empty authored face-core mask.")
    left, top, right, bottom = bbox
    width = right - left
    height = bottom - top
    margin_x = max(FACE_CROP_MARGIN_PX, round(width * 0.12))
    margin_y = max(FACE_CROP_MARGIN_PX, round(height * 0.12))
    crop = (
        max(0, left - margin_x),
        max(0, top - margin_y),
        min(reference.width, right + margin_x),
        min(reference.height, bottom + margin_y),
    )
    crop_width = (crop[2] - crop[0]) * FACE_CROP_SCALE
    crop_height = (crop[3] - crop[1]) * FACE_CROP_SCALE
    label_height = 48
    canvas = Image.new("RGB", (crop_width * RGB_CHANNELS, crop_height + label_height), "#17202b")
    draw = ImageDraw.Draw(canvas)
    panels = (
        ("neutral source", reference),
        ("renderer output", rendered),
        (
            "pixel difference",
            _heatmap(reference, rendered, difference_mask, outside_only=False),
        ),
    )
    for index, (label, image) in enumerate(panels):
        draw.text((index * crop_width + 8, 8), label, fill="#eff6ff")
        panel = image.crop(crop).convert("RGBA")
        background = Image.new("RGBA", panel.size, "#f4f5f6")
        background.alpha_composite(panel)
        enlarged = background.resize(
            (crop_width, crop_height), resample=Image.Resampling.NEAREST
        )
        canvas.paste(enlarged.convert("RGB"), (index * crop_width, label_height))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, format="PNG", compress_level=9)
    return [crop[0], crop[1], crop[2], crop[3]]


def _premultiplied_pixels(pixmap: QPixmap) -> np.ndarray:
    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888_Premultiplied)
    return np.frombuffer(image.constBits(), dtype=np.uint8).reshape(
        image.height(), image.bytesPerLine()
    )[:, :image.width() * RGBA_CHANNELS].reshape(
        image.height(), image.width(), RGBA_CHANNELS
    ).copy()


def _formula_endpoints(
    context: VerificationContext, case: ComparisonRequest,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Independently build unweighted Qt endpoints; never call the compositor."""
    halfbody = bool(case.metadata.get("halfbody", case.group == "half"))
    state = str(case.metadata.get("requested_state") or ("neutral-rest" if halfbody else "rest"))
    if context.reader.frame_keys(case.view, halfbody=halfbody) == ("rest",):
        state = "rest"
    body = QPixmap()
    if not load_pixmap_png(body, context.reader.load_frame(case.view, state, halfbody=halfbody)):
        raise ValueError(f"Cannot decode body endpoint: {case.label}")
    plan = context.layer_views[case.view]
    cleared = QPixmap(body)
    if plan.base_hide is not None:
        pixels = np.asarray(_read_source(_safe_layer_path(context.layer_root, plan.base_hide)))
        binary = np.zeros_like(pixels)
        binary[..., 3] = np.where(pixels[..., 3] > 0, 255, 0)
        mask = QImage(binary.data, body.width(), body.height(), body.width() * 4,
                      QImage.Format_RGBA8888).copy()
        painter = QPainter(cleared)
        try:
            painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
            painter.drawImage(0, 0, mask)
        finally:
            painter.end()
    character = QPixmap(body.size())
    character.fill(Qt.transparent)
    protected = QPixmap(body)
    character_painter = QPainter(character)
    body_painter = QPainter(protected)
    try:
        body_painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
        for stage in plan.order:
            if stage == "base":
                character_painter.drawPixmap(0, 0, cleared)
                continue
            painter = body_painter if stage == "makeup" else character_painter
            for record in plan.layers:
                if record.kind == stage:
                    image = QPixmap()
                    if not load_pixmap_png(image, _safe_layer_path(context.layer_root, record).read_bytes()):
                        raise ValueError(f"Cannot decode formula layer: {record.path}")
                    painter.drawPixmap(0, 0, image)
    finally:
        character_painter.end()
        body_painter.end()
    return _premultiplied_pixels(protected), _premultiplied_pixels(character), state


def _formula_acceptance(
    context: VerificationContext, case: ComparisonRequest,
) -> tuple[dict[str, object], dict[str, object]]:
    protected, character, state = _formula_endpoints(context, case)
    alpha = np.asarray(_read_source(case.core.mask_path), dtype=np.uint8)[..., 3]
    weight = alpha[..., None].astype(np.uint32)
    expected = ((protected.astype(np.uint32) * weight
                 + character.astype(np.uint32) * (255 - weight) + 127) // 255).astype(np.uint8)
    rendered = np.asarray(case.rendered, dtype=np.uint8)
    actual = np.concatenate((_premultiplied_rgb(rendered), rendered[..., 3:4]), axis=2)

    def acceptance(reference: np.ndarray, region: np.ndarray, label: str) -> dict[str, object]:
        metrics = {
            "premultiplied_rgb": _delta_metrics(reference[..., :3], actual[..., :3], region),
            "alpha": _delta_metrics(reference[..., 3:4], actual[..., 3:4], region),
        }
        return {
            "reference": label, "state": state, "metrics": metrics,
            "max_allowed_delta": MAX_OUTSIDE_CORE_DELTA,
            "passed": all(metric["max_abs_channel_delta"] <= MAX_OUTSIDE_CORE_DELTA
                          for metric in metrics.values()),
        }

    feather = acceptance(expected, (alpha > 0) & (alpha < OPAQUE_ALPHA),
                         "numpy-premultiplied-linear-formula-Bprime-F-plus-X-complement")
    feather["requires_visual_review"] = bool(np.any((alpha > 0) & (alpha < OPAQUE_ALPHA)))
    opaque = acceptance(protected, alpha == OPAQUE_ALPHA, "selected-body-plus-SourceAtop-makeup")
    return feather, opaque


def _record_comparison(
    context: VerificationContext,
    case: ComparisonRequest,
) -> dict[str, object]:
    raw_metrics = _measure_pair(case.reference, case.rendered, case.core.mask)
    qt_reference = _qt_reference(case.reference_path)
    qt_metrics = _measure_pair(qt_reference, case.rendered, case.core.mask)
    qt_visible_metrics = _measure_qt_visible_pair(
        qt_reference, case.rendered, case.core.mask
    )
    feather, opaque_core = _formula_acceptance(context, case)
    raw_outside = raw_metrics["outside_core"]["rgba"]
    premultiplied_rgb_delta = qt_visible_metrics["outside_core"]["premultiplied_rgb"][
        "max_abs_channel_delta"
    ]
    alpha_delta = qt_visible_metrics["outside_core"]["alpha"]["max_abs_channel_delta"]
    passed = (
        qt_visible_metrics["outside_core"]["premultiplied_rgb"]["compared_pixels"] > 0
        and premultiplied_rgb_delta <= MAX_OUTSIDE_CORE_DELTA
        and alpha_delta <= MAX_OUTSIDE_CORE_DELTA
        and opaque_core["passed"]
        and feather["passed"]
    )
    safe_label = case.label.replace("/", "_").replace("\\", "_")
    render_path = context.output / "renders" / case.group / f"{safe_label}.png"
    render_path.parent.mkdir(parents=True, exist_ok=True)
    case.rendered.save(render_path, format="PNG", compress_level=9)
    raw_diff_path = context.output / "diffs" / case.group / f"{safe_label}.png"
    raw_diff_path.parent.mkdir(parents=True, exist_ok=True)
    _heatmap(case.reference, case.rendered, case.core.mask, outside_only=case.group != "evidence").save(
        raw_diff_path, format="PNG", compress_level=9
    )
    qt_diff_path = raw_diff_path.with_name(f"{raw_diff_path.stem}-qt.png")
    _heatmap(qt_reference, case.rendered, case.core.mask, outside_only=case.group != "evidence").save(
        qt_diff_path, format="PNG", compress_level=9
    )
    row: dict[str, object] = {
        "label": case.label,
        "group": case.group,
        "view_id": case.view,
        "reference": str(case.reference_path),
        "render_path": str(render_path),
        "diff_path": str(raw_diff_path),
        "qt_normalized_diff_path": str(qt_diff_path),
        "metrics": {
            "raw_source_png_rgba": raw_metrics,
            "source_decoded_through_qt_rgba": qt_metrics,
            "qt_renderer_vs_reference_premultiplied_alpha": qt_visible_metrics,
        },
        "core_mask": {
            "path": str(case.core.mask_path),
            "origin": case.core.mask_origin,
            "nonzero_pixels": int(np.count_nonzero(case.core.mask)),
            "dynamic_built_mask": True,
        },
        "outside_core_max_abs_channel_delta": raw_outside["max_abs_channel_delta"],
        "qt_normalized_outside_core_max_abs_channel_delta": qt_metrics["outside_core"]["rgba"]["max_abs_channel_delta"],
        "qt_renderer_outside_core_premultiplied_rgb_max_abs_delta": premultiplied_rgb_delta,
        "qt_renderer_outside_core_alpha_max_abs_delta": alpha_delta,
        "raw_rgba_failed_qt_visible_passed": (
            raw_outside["max_abs_channel_delta"] > MAX_OUTSIDE_CORE_DELTA and passed
        ),
        "feather_band": feather,
        "opaque_core": opaque_core,
        "passed": passed,
    }
    if case.face_crop:
        crop_path = context.output / "evidence" / "face-crops" / f"{safe_label}.png"
        reference_view = str(case.metadata.get("reference_view", case.view))
        crop_mask, crop_mask_path = _authored_face_mask(
            context.layers_root, case.reference_path, reference_view
        )
        crop_bbox = _save_face_crop(
            crop_path,
            case.reference,
            case.rendered,
            crop_mask,
            case.core.mask,
        )
        row["face_crop_path"] = str(crop_path)
        row["face_crop_mask_path"] = str(crop_mask_path)
        row["face_crop_bbox_xyxy"] = crop_bbox
        row["face_crop_scale"] = FACE_CROP_SCALE
        row["face_crop_resampling"] = "nearest"
    if case.metadata:
        row["render_request"] = dict(case.metadata)
    context.comparisons.append(row)
    return row


def _motion(
    expression: str,
    *,
    viseme: Viseme | None = None,
    blink: float = 0.0,
) -> FaceMotionFrame:
    selected_viseme = Viseme.CLOSED if viseme is None else viseme
    aperture = {
        Viseme.CLOSED: 0.0,
        Viseme.CONSONANT: 0.5,
        Viseme.A: 1.0,
        Viseme.I: 0.5,
        Viseme.U: 0.5,
        Viseme.E: 0.5,
        Viseme.O: 0.5,
    }[selected_viseme]
    return FaceMotionFrame(
        pose=FacePose.FRONT,
        expression=expression,
        viseme=selected_viseme,
        mouth=MouthShape(aperture=aperture),
        expression_shape=ExpressionShape(blink=blink),
    )


def _record_case_error(context: VerificationContext, label: str, error: Exception) -> None:
    context.errors.append(
        {"case": label, "error_type": type(error).__name__, "message": str(error)}
    )


def _record_skipped(context: VerificationContext, label: str, reason: str) -> None:
    context.skipped.append({"case": label, "reason": reason})


def _primary_comparison(
    context: VerificationContext,
    view: str,
    halfbody: bool,
) -> None:
    label = f"{'half' if halfbody else 'full'}/{view}"
    try:
        reference_path = _find_source(context.layers_root, view, halfbody=halfbody)
        if reference_path is None:
            raise FileNotFoundError(f"Missing neutral composite for {view}.")
        reference = _read_source(reference_path)
        core = _core_evidence(context.reader, context.body_root, view)
        motion = _motion(view)
        rendered_pixmap = (
            context.renderer.render(QPixmap(), motion, None)
            if halfbody
            else context.renderer.render_view(view, motion)
        )
        rendered = _pixmap_image(rendered_pixmap)
        _record_comparison(
            context,
            ComparisonRequest(
                view,
                view,
                reference_path,
                reference,
                rendered,
                core,
                "half" if halfbody else "full",
                metadata={
                    "api": "render" if halfbody else "render_view",
                    "state": "neutral-rest" if halfbody else "rest",
                    "halfbody": halfbody,
                    "frame_keys": list(context.reader.frame_keys(view, halfbody=halfbody)),
                },
            ),
        )
    except Exception as error:
        _record_case_error(context, label, error)


def _state_evidence(context: VerificationContext, request: StateRequest) -> None:
    try:
        reference_path = _find_source(
            context.layers_root,
            request.reference_view,
            halfbody=request.halfbody,
            optional=True,
        )
        reference_view = request.reference_view
        if reference_path is None and request.halfbody and reference_view != "front-crossed":
            reference_view = "front-crossed"
            reference_path = _find_source(
                context.layers_root, reference_view, halfbody=True, optional=True
            )
        if reference_path is None:
            reference_path = _find_source(
                context.layers_root,
                reference_view,
                halfbody=request.halfbody,
            )
        reference = _read_source(reference_path)
        core = _core_evidence(context.reader, context.body_root, request.render_view)
        if request.api == "render_view":
            pixmap = context.renderer.render_view(request.render_view, request.motion)
        else:
            pixmap = context.renderer.render(QPixmap(), request.motion, None)
            if request.blink_after_render is not None:
                pixmap = context.renderer.render_complete_blink(
                    pixmap, request.blink_after_render
                )
        _record_comparison(
            context,
            ComparisonRequest(
                request.label,
                request.render_view,
                reference_path,
                reference,
                _pixmap_image(pixmap),
                core,
                "evidence",
                face_crop=True,
                metadata={
                    "api": request.api,
                    "halfbody": request.halfbody,
                    "reference_view": reference_view,
                    "requested_expression": request.motion.expression,
                    "requested_viseme": request.motion.viseme.value,
                    "requested_blink": request.motion.expression_shape.blink,
                    "blink_api": (
                        "render_complete_blink"
                        if request.blink_after_render is not None
                        else None
                    ),
                    "requested_state": request.requested_state,
                    "frame_keys": list(
                        context.reader.frame_keys(request.render_view, halfbody=request.halfbody)
                    ),
                },
            ),
        )
    except Exception as error:
        _record_case_error(context, request.label, error)


def _required_view_exists(context: VerificationContext, view: str, halfbody: bool) -> bool:
    manifest_views = context.reader.manifest.half_body if halfbody else context.reader.manifest.full_body
    available = {item.view_id for item in manifest_views}
    if view not in available:
        _record_case_error(context, f"missing:{view}", ValueError("Required body view is absent."))
        return False
    if view not in context.layer_views:
        _record_case_error(
            context,
            f"layer-view:{view}",
            ValueError("The character-layer manifest has no plan for this view."),
        )
        return False
    return True


def _verify_primary_views(context: VerificationContext, full_views: tuple[str, ...]) -> None:
    for view in full_views:
        if _required_view_exists(context, view, halfbody=False):
            _primary_comparison(context, view, halfbody=False)
    for view in HALF_BODY_VIEWS:
        if _required_view_exists(context, view, halfbody=True):
            _primary_comparison(context, view, halfbody=True)


def _sample_state_parameters(state: str) -> tuple[Viseme, float, str | None]:
    return {
        "a-rest": (Viseme.A, 0.0, None),
        "a-closed": (Viseme.A, 1.0, "closed"),
        "o-half": (Viseme.O, 0.5, "half"),
        "small-closed": (Viseme.CONSONANT, 1.0, "closed"),
    }[state]


def _verify_yaw_zero_states(context: VerificationContext, yaw_zero: str) -> None:
    if not _required_view_exists(context, yaw_zero, halfbody=False):
        return
    frame_keys = set(context.reader.frame_keys(yaw_zero))
    for state in YAW_ZERO_SAMPLE_STATES:
        label = f"full/{yaw_zero}/{state}"
        if state not in frame_keys:
            _record_case_error(
                context, label, ValueError(f"Body pack does not declare required state {state}.")
            )
            continue
        viseme, blink, _ = _sample_state_parameters(state)
        _state_evidence(
            context,
            StateRequest(
                label,
                yaw_zero,
                yaw_zero,
                _motion(yaw_zero, viseme=viseme, blink=blink),
                False,
                "render_view",
                requested_state=state,
            ),
        )


def _verify_half_front_states(context: VerificationContext, view: str = "front-crossed") -> None:
    if not _required_view_exists(context, view, halfbody=True):
        return
    frame_keys = set(context.reader.frame_keys(view, halfbody=True))
    for state in HALF_FRONT_SAMPLE_STATES:
        label = f"half/{view}/{state}"
        if state not in frame_keys:
            _record_case_error(
                context, label, ValueError(f"Body pack does not declare required state {state}.")
            )
            continue
        viseme, blink, blink_after = _sample_state_parameters(state)
        _state_evidence(
            context,
            StateRequest(
                label,
                view,
                view,
                _motion(view, viseme=viseme, blink=blink),
                True,
                "render",
                blink_after,
                state,
            ),
        )


def _verify_half_aliases(context: VerificationContext) -> str:
    for alias in EXPRESSION_ALIASES:
        if not _required_view_exists(context, alias, halfbody=True):
            continue
        frame_keys = set(context.reader.frame_keys(alias, halfbody=True))
        for state, blink_after in (("neutral-rest", None), ("neutral-closed", "closed")):
            label = f"half/{alias}/{state}"
            if state not in frame_keys:
                _record_case_error(
                    context, label, ValueError(f"Body pack does not declare required state {state}.")
                )
                continue
            _state_evidence(
                context,
                StateRequest(
                    label,
                    alias,
                    alias,
                    _motion(alias),
                    True,
                    "render",
                    blink_after,
                    state,
                ),
            )
    return "proud_front/worried_front"


def _build_overview(rows: list[dict[str, object]], output: Path) -> Path:
    columns = 6
    tile_width = 260
    tile_height = 240
    label_height = 52
    row_count = max(1, ceil(len(rows) / columns))
    sheet = Image.new(
        "RGB",
        (columns * tile_width, row_count * (tile_height + label_height)),
        "#101720",
    )
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(rows):
        x = (index % columns) * tile_width
        y = (index // columns) * (tile_height + label_height)
        diff_path = Path(str(row["diff_path"]))
        if diff_path.is_file():
            diff = Image.open(diff_path).convert("RGBA")
            diff.thumbnail((tile_width - 20, tile_height - 8), Image.Resampling.LANCZOS)
            background = Image.new("RGBA", diff.size, "#34404c")
            background.alpha_composite(diff)
            image_x = x + (tile_width - diff.width) // 2
            image_y = y + 4 + (tile_height - diff.height) // 2
            sheet.paste(background.convert("RGB"), (image_x, image_y))
        outside_max = row.get("outside_core_max_abs_channel_delta", "n/a")
        color = "#78e08f" if row.get("passed") else "#ff746c"
        draw.text((x + 8, y + tile_height + 5), str(row.get("label", "")), fill="#f0f4f8")
        draw.text((x + 8, y + tile_height + 25), f"outside max Δ {outside_max}", fill=color)
    overview = output / "overview" / "diff-overview.png"
    overview.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(overview, format="PNG", compress_level=9)
    return overview


def _build_rendered_overview(rows: list[dict[str, object]], output: Path) -> Path:
    primary_rows = rows
    columns = 6
    tile_width = 260
    tile_height = 240
    label_height = 32
    row_count = max(1, ceil(len(primary_rows) / columns))
    sheet = Image.new(
        "RGB",
        (columns * tile_width, row_count * (tile_height + label_height)),
        "#101720",
    )
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(primary_rows):
        x = (index % columns) * tile_width
        y = (index // columns) * (tile_height + label_height)
        image_path = Path(str(row["render_path"]))
        if image_path.is_file():
            with Image.open(image_path) as opened:
                rendered = opened.convert("RGBA")
            rendered.thumbnail((tile_width - 20, tile_height - 8), Image.Resampling.LANCZOS)
            tile = Image.new("RGBA", rendered.size, "#808080")
            tile.alpha_composite(rendered)
            image_x = x + (tile_width - rendered.width) // 2
            image_y = y + (tile_height - rendered.height) // 2
            sheet.paste(tile.convert("RGB"), (image_x, image_y))
        draw.text((x + 8, y + tile_height + 6), str(row["label"]), fill="#f0f4f8")
    overview = output / "overview" / "rendered-overview.png"
    overview.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(overview, format="PNG", compress_level=9)
    return overview


def _acceptance_breakdown(
    comparisons: list[dict[str, object]],
    skipped: list[dict[str, str]],
    expected_full: tuple[str, ...],
) -> dict[str, object]:
    neutral_rows = [row for row in comparisons if row["group"] in {"full", "half"}]
    state_rows = [row for row in comparisons if row["group"] == "evidence"]
    full_samples = [row for row in state_rows if str(row["label"]).startswith("full/")]
    half_front = [
        row for row in state_rows if str(row["label"]).startswith("half/front-crossed/")
    ]
    half_aliases = [
        row for row in state_rows
        if str(row["label"]).startswith("half/")
        and not str(row["label"]).startswith("half/front-crossed/")
        and not any(str(row["label"]).startswith(f"half/{gesture}/") for gesture in GESTURE_VIEWS)
    ]
    full_skips = [row for row in skipped if str(row["case"]).startswith("full/")]
    half_skips = [row for row in skipped if str(row["case"]).startswith("half/")]
    front_skips = sum(
        str(row["case"]).startswith("half/front-crossed/") for row in half_skips
    )
    return {
        "neutral_views": {
            "expected": len(expected_full) + len(HALF_BODY_VIEWS),
            "rendered": len(neutral_rows),
            "renderer_acceptance_failures": sum(not row["passed"] for row in neutral_rows),
        },
        "state_evidence": {
            "expected": len(YAW_ZERO_SAMPLE_STATES)
            + len(HALF_FRONT_SAMPLE_STATES) * (1 + len(GESTURE_VIEWS))
            + len(EXPRESSION_ALIASES) * len(HALF_ALIAS_SAMPLE_STATES),
            "rendered": len(state_rows),
            "full_yaw_zero": {
                "expected": len(YAW_ZERO_SAMPLE_STATES),
                "rendered": len(full_samples),
                "skipped": len(full_skips),
            },
            "half_front_crossed": {
                "expected": len(HALF_FRONT_SAMPLE_STATES),
                "rendered": len(half_front),
                "skipped": front_skips,
            },
            "gesture_states": {
                "expected": len(GESTURE_VIEWS) * len(HALF_FRONT_SAMPLE_STATES),
                "rendered": sum(any(str(row["label"]).startswith(f"half/{gesture}/")
                                    for gesture in GESTURE_VIEWS) for row in state_rows),
            },
            "half_expression_aliases": {
                "expected": len(EXPRESSION_ALIASES) * len(HALF_ALIAS_SAMPLE_STATES),
                "rendered": len(half_aliases),
                "skipped": len(half_skips) - front_skips,
            },
        },
    }


def _summary(
    context: VerificationContext,
    expected_full: tuple[str, ...],
    alias_route: str,
    overview: Path,
    rendered_overview: Path,
) -> dict[str, object]:
    failed_rows = [row for row in context.comparisons if not row["passed"]]
    return {
        "schema": REPORT_SCHEMA,
        "passed": not context.errors and not failed_rows,
        "numeric_passed": not context.errors and not failed_rows,
        "visual_review_required": True,
        "overall_passed": False,
        "threshold": {
            "qt_renderer_outside_dynamic_core_premultiplied_rgb_max_abs_delta": (
                MAX_OUTSIDE_CORE_DELTA
            ),
            "qt_renderer_outside_dynamic_core_alpha_max_abs_delta": MAX_OUTSIDE_CORE_DELTA,
            "qt_acceptance": (
                "Qt-decoded round9 reference vs actual Qt renderer output; compare premultiplied "
                "RGB and alpha independently, with transparent RGB ignored"
            ),
            "qt_renderer_opaque_core_vs_body_premultiplied_rgb_and_alpha_max_abs_delta": 1,
            "feather_acceptance": "numpy premultiplied linear formula delta <=1 plus 3x visual review",
            "face_core_exclusion": "built body-pack dynamic face-core mask: alpha > 0",
            "source_png_rgba_and_qt_rgba_metrics": "diagnostic only",
            "source_mask_consistency_gate": False,
            "seam_ring_radius_px": SEAM_RING_RADIUS,
        },
        "body_pack": {
            "id": context.reader.reference.id,
            "version": context.reader.reference.version,
            "fingerprint": context.reader.reference.fingerprint,
            "build_root": str(context.build_root),
            "body_pack_root": str(context.body_root),
            "full_body_canvas": list(context.reader.fullbody_canvas),
            "half_body_canvas": list(context.reader.halfbody_canvas),
        },
        "layers": {
            "package_root": str(context.layer_root),
            "original_source_root": str(context.layers_root),
            "views_declared": len(context.layer_views),
        },
        "expected_full_views": list(expected_full),
        "expected_half_views": list(HALF_BODY_VIEWS),
        "expression_evidence_route": alias_route,
        "comparisons": context.comparisons,
        "comparison_count": len(context.comparisons),
        "failed_comparison_count": len(failed_rows),
        "acceptance_breakdown": _acceptance_breakdown(
            context.comparisons,
            context.skipped,
            expected_full,
        ),
        "skipped": context.skipped,
        "errors": context.errors,
        "overview": str(overview),
        "rendered_overview": str(rendered_overview),
        "output_root": str(context.output),
    }


def _verify(args: argparse.Namespace) -> tuple[dict[str, object], int]:
    activate_product_character_runtime(ROOT)
    context = _context_from_args(args)
    expected_full = tuple(canonical_view_id(yaw, 0) for yaw in CANONICAL_YAWS)
    _verify_primary_views(context, expected_full)
    _verify_yaw_zero_states(context, canonical_view_id(0, 0))
    _verify_half_front_states(context)
    for gesture in GESTURE_VIEWS:
        _verify_half_front_states(context, gesture)
    alias_route = _verify_half_aliases(context)
    overview = _build_overview(context.comparisons, context.output)
    rendered_overview = _build_rendered_overview(context.comparisons, context.output)
    report = _summary(context, expected_full, alias_route, overview, rendered_overview)
    _write_json(context.output / "summary.json", report)
    return report, 0 if report["passed"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--layers-root", type=Path, default=DEFAULT_LAYERS_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    try:
        summary, exit_code = _verify(args)
    except Exception as error:
        report = {
            "schema": REPORT_SCHEMA,
            "passed": False,
            "errors": [
                {"case": "preflight", "error_type": type(error).__name__, "message": str(error)}
            ],
            "output_root": str(output),
        }
        try:
            _write_json(output / "summary.json", report)
        except OSError as summary_error:
            print(
                f"Could not write failure summary {output / 'summary.json'}: "
                f"{type(summary_error).__name__}: {summary_error}",
                file=sys.stderr,
            )
        print(
            f"Body-pack build verification failed: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1
    print(json.dumps({
        "passed": summary["passed"],
        "comparison_count": summary["comparison_count"],
        "failed_comparison_count": summary["failed_comparison_count"],
        "skipped_count": len(summary["skipped"]),
        "error_count": len(summary["errors"]),
        "summary": str(output / "summary.json"),
        "overview": summary["overview"],
    }, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
