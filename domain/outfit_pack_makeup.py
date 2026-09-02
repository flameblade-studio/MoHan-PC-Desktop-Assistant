"""Makeup slot contracts: safe regions, the pixel gate, intensity state and the built-in item.

Makeup is the one appearance category that legitimately paints the face.  Every
layer is a full-canvas RGBA PNG registered to its silhouette; its opaque pixels
must stay inside the slot's safe region, which this module derives from the
layered rig (eyelid/eyeliner/brow, blush and lip cut-out bounding boxes dilated
by a per-slot margin) and stores once in ``assets/makeup-safe-regions.json``.
The runtime additionally clips the visible iris and the open oral cavity.
"""

from __future__ import annotations

lazy import json
lazy import os
lazy import zipfile
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import NamedTemporaryFile

lazy from PySide6.QtGui import QImage

lazy from domain import outfit_pack
lazy from domain.outfit_pack import (
    BUILTIN_MAKEUP_ITEM_ID,
    BUILTIN_MAKEUP_PACK_ID,
    BUILTIN_MAKEUP_VARIANTS,
    MAKEUP_SLOTS,
    REQUIRED_SILHOUETTES,
    OutfitPackError,
    inspect_outfit_pack,
)

SAFE_REGION_SCHEMA = "mohan.makeup-safe-regions.v1"
SAFE_REGION_FILE = "makeup-safe-regions.json"
SAFE_REGION_PATH = Path(__file__).resolve().parents[1] / "assets" / SAFE_REGION_FILE
MAKEUP_STATE_FILE = "makeup.json"
ACTIVE_STATE_FILE = "active.json"
DEFAULT_MAKEUP_INTENSITY = 1.0
INTENSITY_DECIMALS = 2
RECT_FIELDS = 4
CANVAS_FIELDS = 2
# Rig cut-outs whose alpha bounding boxes define each slot, grouped per side so a
# profile view with one visible eye keeps one tight rectangle instead of a band.
SLOT_RIG_LAYERS = frozendict({
    "eyes": (
        ("eyelid_left", "eyeliner_left", "brow_left"),
        ("eyelid_right", "eyeliner_right", "brow_right"),
    ),
    "cheeks": (("blush_left",), ("blush_right",)),
    "lips": (("lip_upper", "lip_lower", "corner_left", "corner_right"),),
})
# Dilation applied to each slot's rig bounding boxes (pixels on the authored canvas).
SLOT_MARGINS_PX = frozendict({"eyes": 24, "cheeks": 48, "lips": 20})
# (painted layers, covering layers): the runtime clip excludes the painted mask
# minus the covering mask, so a liner authored over the lid survives while the
# visible iris and the open oral cavity never receive makeup.
EXCLUSION_RIG_LAYERS = (
    (("iris_left", "iris_right"), ("eyelid_left", "eyelid_right")),
    (("oral_cavity", "teeth_tongue"), ("lip_upper", "lip_lower")),
)
# Half-body silhouettes share the three authored expression rigs; the four
# gesture silhouettes are front-pose performances of the same head.
HALF_BODY_RIGS = frozendict({
    "cheek-rest": "cheek",
    "left-neutral": "lean",
    "front-crossed": "front",
    "front-mock-scold": "front",
    "front-mock-hit": "front",
    "front-eureka": "front",
    "front-exasperated": "front",
})
HALF_BODY_RIG_ROOT = "assets/expressions/layered"
FULL_BODY_RIG_ROOT = "assets/pose-atlas"

Rect = tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class MakeupSafeRegion:
    silhouette: str
    canvas: tuple[int, int]
    rig: str
    slots: frozendict[str, tuple[Rect, ...]]

    def rects(self, slot: str) -> tuple[Rect, ...]:
        return self.slots.get(slot, ())


def _rect(value: object) -> Rect:
    if (
        not isinstance(value, list)
        or len(value) != RECT_FIELDS
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value)
        or value[2] <= 0
        or value[3] <= 0
    ):
        raise OutfitPackError("Invalid makeup safe-region rectangle.")
    return (value[0], value[1], value[2], value[3])


def parse_makeup_safe_regions(payload: object) -> frozendict[str, MakeupSafeRegion]:
    """Validate the safe-region document; every required silhouette must be present."""
    if not isinstance(payload, dict) or payload.get("schema") != SAFE_REGION_SCHEMA:
        raise OutfitPackError("Unsupported makeup safe-region document.")
    silhouettes = payload.get("silhouettes")
    if not isinstance(silhouettes, dict) or set(silhouettes) != set(REQUIRED_SILHOUETTES):
        raise OutfitPackError("Makeup safe regions must cover every required silhouette.")
    parsed = {}
    for silhouette, entry in silhouettes.items():
        canvas = entry.get("canvas") if isinstance(entry, dict) else None
        slots = entry.get("slots") if isinstance(entry, dict) else None
        rig = entry.get("rig") if isinstance(entry, dict) else None
        if (
            not isinstance(canvas, list) or len(canvas) != CANVAS_FIELDS
            or any(not isinstance(v, int) or v <= 0 for v in canvas)
            or not isinstance(slots, dict) or set(slots) != MAKEUP_SLOTS or not isinstance(rig, str)
        ):
            raise OutfitPackError(f"Invalid makeup safe region for {silhouette!r}.")
        parsed[silhouette] = MakeupSafeRegion(
            silhouette,
            (canvas[0], canvas[1]),
            rig,
            frozendict({slot: tuple(_rect(rect) for rect in rects) for slot, rects in slots.items()}),
        )
    return frozendict(parsed)


def load_makeup_safe_regions(path: Path | None = None) -> frozendict[str, MakeupSafeRegion]:
    source = SAFE_REGION_PATH if path is None else Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise OutfitPackError("The makeup safe-region document is unavailable.") from None
    return parse_makeup_safe_regions(payload)


def alpha_plane(png: bytes) -> tuple[bytes, int, int]:
    """Decode one PNG into a tightly packed 8-bit alpha plane (row-major, no padding)."""
    image = QImage.fromData(png, "PNG")
    if image.isNull():
        raise OutfitPackError("Makeup layer is not a decodable PNG.")
    if not image.hasAlphaChannel():
        raise OutfitPackError("Makeup layers must carry an alpha channel.")
    alpha = image.convertToFormat(QImage.Format_Alpha8)
    width, height, stride = alpha.width(), alpha.height(), alpha.bytesPerLine()
    raw = bytes(alpha.constBits())
    if stride == width:
        return raw[: width * height], width, height
    return b"".join(raw[row * stride : row * stride + width] for row in range(height)), width, height


def alpha_outside_rects(plane: bytes, width: int, height: int, rects: tuple[Rect, ...]) -> bool:
    """True when any non-transparent pixel lies outside every allowed rectangle."""
    if len(plane) != width * height:
        raise OutfitPackError("Alpha plane does not match its declared canvas.")
    remaining = bytearray(plane)
    for x, y, w, h in rects:
        left, top = max(0, x), max(0, y)
        right, bottom = min(width, x + w), min(height, y + h)
        if right <= left or bottom <= top:
            continue
        blank = bytes(right - left)
        for row in range(top, bottom):
            start = row * width + left
            remaining[start : start + right - left] = blank
    return remaining.count(b"\x00") != len(remaining)


def makeup_layer_escapes(png: bytes, region: MakeupSafeRegion, slot: str) -> bool:
    """Whether one makeup layer paints outside its slot's safe region (canvas mismatch counts)."""
    plane, width, height = alpha_plane(png)
    if (width, height) != region.canvas:
        return True
    return alpha_outside_rects(plane, width, height, region.rects(slot))


def verify_makeup_layers(archive_path: Path, regions: frozendict[str, MakeupSafeRegion] | None = None) -> None:
    """Import-time pixel gate: every makeup layer of the pack stays inside its safe region."""
    pack = inspect_outfit_pack(archive_path)
    makeup_items = [item for item in pack.items if item.category == "makeup"]
    if not makeup_items:
        return
    table = load_makeup_safe_regions() if regions is None else regions
    with zipfile.ZipFile(archive_path) as archive:
        for item in makeup_items:
            for variant in item.variants:
                for silhouette, assets in variant.poses.items():
                    region = table[silhouette]
                    for asset in assets:
                        if makeup_layer_escapes(archive.read(asset.path), region, asset.slot):
                            raise OutfitPackError(
                                f"Makeup layer {asset.path} ({item.item_id}/{variant.variant_id}) paints outside "
                                f"the {asset.slot} safe region of {silhouette}."
                            )


def clamp_makeup_intensity(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return DEFAULT_MAKEUP_INTENSITY
    if number != number:  # NaN never becomes an alpha multiplier.
        return DEFAULT_MAKEUP_INTENSITY
    return round(min(1.0, max(0.0, number)), INTENSITY_DECIMALS)


def read_makeup_intensity(store: Path) -> float:
    """The user's makeup intensity (0 = bare face, 1 = authored layer); defaults to 1."""
    path = Path(store) / MAKEUP_STATE_FILE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return DEFAULT_MAKEUP_INTENSITY
    if not isinstance(payload, dict) or isinstance(payload.get("intensity"), bool):
        return DEFAULT_MAKEUP_INTENSITY
    return clamp_makeup_intensity(payload.get("intensity", DEFAULT_MAKEUP_INTENSITY))


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(payload, temporary, ensure_ascii=False, sort_keys=True)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_makeup_intensity(store: Path, value: object) -> float:
    """Persist the intensity atomically next to active.json; returns the clamped value."""
    intensity = clamp_makeup_intensity(value)
    _atomic_json(Path(store) / MAKEUP_STATE_FILE, {"intensity": intensity})
    return intensity


def select_builtin_makeup(store: Path, variant_id: str) -> None:
    """Choose one built-in makeup variant; ``classic`` is what a fresh profile resolves to anyway."""
    if variant_id not in BUILTIN_MAKEUP_VARIANTS:
        raise OutfitPackError("Unknown built-in makeup variant.")
    active_path = Path(store) / ACTIVE_STATE_FILE
    try:
        active = json.loads(active_path.read_text(encoding="utf-8")) if active_path.is_file() else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise OutfitPackError("Invalid saved appearance state.") from None
    if not isinstance(active, dict):
        raise OutfitPackError("Invalid saved appearance state.")
    active.pop("_ensemble", None)
    active["makeup"] = {"pack_id": "builtin", "item_id": "builtin", "variant_id": variant_id}
    _atomic_json(active_path, active)


def builtin_makeup_pack_path() -> Path:
    """The official built-in makeup pack (two variants: ``classic`` and ``light``)."""
    return outfit_pack.OFFICIAL_PACK_ROOT / f"{BUILTIN_MAKEUP_PACK_ID}.mohan-outfit"


def builtin_makeup_identity(variant_id: str) -> tuple[str, str, str]:
    if variant_id not in BUILTIN_MAKEUP_VARIANTS:
        raise OutfitPackError("Unknown built-in makeup variant.")
    return (BUILTIN_MAKEUP_PACK_ID, BUILTIN_MAKEUP_ITEM_ID, variant_id)
