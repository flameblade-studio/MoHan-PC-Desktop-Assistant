"""Makeup slot contracts: safe regions, the pixel gate, intensity state and the built-in item.

Makeup is the one appearance category that legitimately paints the face.  Every
layer is a full-canvas RGBA PNG registered to its silhouette; its opaque pixels
must stay inside the slot's safe region, which this module derives from the
layered rig (eyelid/eyeliner/brow, blush and lip cut-out bounding boxes dilated
by a per-slot margin) and stores once in ``assets/makeup-safe-regions.json``.
The runtime additionally clips the visible iris and the open oral cavity.
"""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import re
lazy import zipfile
lazy from dataclasses import dataclass
lazy from collections.abc import Callable
lazy from math import isfinite
lazy from pathlib import Path
lazy from tempfile import NamedTemporaryFile
lazy from threading import RLock

lazy from PySide6.QtGui import QImage

lazy from domain import outfit_pack
lazy from domain.outfit_pack import (
    BUILTIN_MAKEUP_ITEM_ID,
    BUILTIN_MAKEUP_ALWAYS_VISIBLE_VARIANTS,
    BUILTIN_MAKEUP_PACK_ID,
    FOUNDATION_SLOT,
    BUILTIN_MAKEUP_VARIANTS,
    MAKEUP_SLOTS,
    MAKEUP_SLOTS_V2,
    REQUIRED_SILHOUETTES,
    OutfitPackError,
    inspect_outfit_pack,
)

SAFE_REGION_SCHEMA = "mohan.makeup-safe-regions.v1"
SAFE_REGION_SCHEMA_V2 = "mohan.makeup-safe-regions.v2"
SAFE_REGION_FILE = "makeup-safe-regions.json"
SAFE_REGION_PATH = Path(__file__).resolve().parents[1] / "assets" / SAFE_REGION_FILE
MAKEUP_STATE_FILE = "makeup.json"
ACTIVE_STATE_FILE = "active.json"
DEFAULT_MAKEUP_INTENSITY = 1.0
MAKEUP_READ_FAILURE_MESSAGE = "妝容設定無法讀取，已保留上一個有效值。"
INTENSITY_DECIMALS = 2
RECT_FIELDS = 4
CANVAS_FIELDS = 2
FOUNDATION_STATES = frozenset({"rest", "half", "closed"})
FOUNDATION_MASK_FIELDS = frozenset({"path", "sha256", "width", "height", "anchor"})
EYE_APERTURE_MASK_FIELDS = FOUNDATION_MASK_FIELDS
FOUNDATION_MASK_PATH = re.compile(r"assets/[A-Za-z0-9][A-Za-z0-9_./+\-]{0,254}\.png\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
NATIVE_VISIBILITY_FIELDS = frozenset({"foundation_coverage", "eye_aperture"})
NATIVE_VISIBILITY_RECORD_FIELDS = frozenset({"nonvisible", "evidence"})
VISIBILITY_EVIDENCE_MARKERS = ("manifest.json", "receipt.json", "stage.json")
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
# Rig cut-outs that form the feature core: the only face pixels hair may never
# cover.  Hair naturally falls over the brow, temples and cheeks, so hairstyle
# layers are clipped out of this core (dilated by HAIRSTYLE_FEATURE_CORE_DILATION_PX,
# faded over HAIRSTYLE_FEATURE_CORE_FEATHER_PX) instead of the whole protected
# face; garments, headwear and accessories keep the full protected-face rule.
FEATURE_CORE_LAYERS = (
    "iris_left", "iris_right", "eyelid_left", "eyelid_right",
    "oral_cavity", "lip_upper", "lip_lower",
)
HAIRSTYLE_FEATURE_CORE_DILATION_PX = 8
HAIRSTYLE_FEATURE_CORE_FEATHER_PX = 6
FULL_BODY_RIG_ROOT = "assets/pose-atlas"

Rect = tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class FoundationSafeMask:
    """A validated, state-specific alpha mask used by a makeup clip."""

    path: str
    sha256: str
    canvas: tuple[int, int]
    anchor: tuple[int, int]
    alpha: bytes = b""


@dataclass(frozen=True, slots=True)
class MakeupSafeRegion:
    silhouette: str
    canvas: tuple[int, int]
    rig: str
    slots: frozendict[str, tuple[Rect, ...]]
    foundation_masks: frozendict[str, FoundationSafeMask] = frozendict()
    eye_aperture_masks: frozendict[str, FoundationSafeMask] = frozendict()

    def rects(self, slot: str) -> tuple[Rect, ...]:
        return self.slots.get(slot, ())

    def foundation_mask(self, state: str = "rest") -> FoundationSafeMask | None:
        return self.foundation_masks.get(state)

    def eye_aperture_mask(self, state: str = "rest") -> FoundationSafeMask | None:
        return self.eye_aperture_masks.get(state)


def _rect(value: object) -> Rect:
    if (
        not isinstance(value, list)
        or len(value) != RECT_FIELDS
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value)
        or value[2] <= 0
        or value[3] <= 0
    ):
        raise OutfitPackError("Provide a supported makeup safe-region rectangle.")
    return (value[0], value[1], value[2], value[3])


def _foundation_mask_descriptor(
    value: object,
    canvas: tuple[int, int],
    *,
    asset_root: Path | None,
    allow_empty: bool = False,
    nonvisible: bool | None = None,
) -> FoundationSafeMask:
    if not isinstance(value, dict) or set(value) != FOUNDATION_MASK_FIELDS:
        raise OutfitPackError("Provide a supported foundation safe-mask declaration.")
    path = value["path"]
    digest = value["sha256"]
    width, height = value["width"], value["height"]
    anchor = value["anchor"]
    if (
        not isinstance(path, str)
        or not FOUNDATION_MASK_PATH.fullmatch(path)
        or ".." in Path(path).parts
        or not isinstance(digest, str)
        or not SHA256.fullmatch(digest)
        or any(not isinstance(number, int) or isinstance(number, bool) for number in (width, height))
        or (width, height) != canvas
        or not isinstance(anchor, list)
        or anchor != [0, 0]
    ):
        raise OutfitPackError("Provide a supported foundation safe-mask geometry or hash.")
    if asset_root is None:
        return FoundationSafeMask(path, digest, canvas, (0, 0))
    root = asset_root.resolve()
    mask_path = (root / Path(*path.split("/"))).resolve()
    try:
        mask_path.relative_to(root)
        data = mask_path.read_bytes()
    except (OSError, ValueError):
        raise OutfitPackError("Foundation safe-mask asset is unavailable.") from None
    if hashlib.sha256(data).hexdigest() != digest:
        raise OutfitPackError("Foundation safe-mask hash mismatch.")
    image = QImage.fromData(data, "PNG")
    if image.isNull() or not image.hasAlphaChannel() or image.size().toTuple() != canvas:
        raise OutfitPackError("Provide a supported foundation safe-mask PNG.")
    alpha = image.convertToFormat(QImage.Format_Alpha8)
    stride = alpha.bytesPerLine()
    raw = bytes(alpha.constBits())
    plane = raw if stride == width else b"".join(
        raw[row * stride : row * stride + width] for row in range(height)
    )
    has_visible_geometry = bool(plane) and any(plane)
    if nonvisible is True and has_visible_geometry:
        raise OutfitPackError("Foundation safe-mask is marked nonvisible but contains visible content.")
    if nonvisible is False and not has_visible_geometry:
        raise OutfitPackError("Foundation safe-mask requires visible content.")
    if nonvisible is None and not has_visible_geometry and not allow_empty:
        raise OutfitPackError("Foundation safe-mask requires visible content.")
    return FoundationSafeMask(path, digest, canvas, (0, 0), plane)


def _native_visibility(
    value: object,
    silhouette: str,
) -> dict[str, dict[str, dict[str, object]]] | None:
    if not isinstance(value, dict) or set(value) != set(FOUNDATION_STATES):
        raise OutfitPackError(f"Invalid native visibility for {silhouette!r}.")
    result: dict[str, dict[str, dict[str, object]]] = {}
    for state in sorted(FOUNDATION_STATES):
        state_value = value[state]
        if not isinstance(state_value, dict) or set(state_value) != NATIVE_VISIBILITY_FIELDS:
            raise OutfitPackError(f"Invalid native visibility for {silhouette!r} {state!r}.")
        masks: dict[str, dict[str, object]] = {}
        for mask_kind in sorted(NATIVE_VISIBILITY_FIELDS):
            record = state_value[mask_kind]
            if not isinstance(record, dict) or set(record) != NATIVE_VISIBILITY_RECORD_FIELDS:
                raise OutfitPackError(
                    f"Invalid native visibility for {silhouette!r} {state!r} {mask_kind!r}."
                )
            nonvisible = record["nonvisible"]
            evidence = record["evidence"]
            if (
                not isinstance(nonvisible, bool)
                or not isinstance(evidence, str)
                or not evidence.strip()
                or "#" not in evidence
                or not any(marker in evidence for marker in VISIBILITY_EVIDENCE_MARKERS)
            ):
                raise OutfitPackError(
                    f"Native visibility evidence is invalid for {silhouette!r} {state!r} {mask_kind!r}."
                )
            masks[mask_kind] = {"nonvisible": nonvisible, "evidence": evidence.strip()}
        result[state] = masks
    return result


def _visibility_flag(
    visibility: dict[str, dict[str, dict[str, object]]] | None,
    state: str,
    mask_kind: str,
) -> bool | None:
    if visibility is None:
        return None
    return bool(visibility[state][mask_kind]["nonvisible"])


def parse_makeup_safe_regions(
    payload: object,
    *,
    asset_root: Path | None = None,
) -> frozendict[str, MakeupSafeRegion]:
    """Validate the safe-region document; every required silhouette must be present."""
    if not isinstance(payload, dict) or payload.get("schema") not in {SAFE_REGION_SCHEMA, SAFE_REGION_SCHEMA_V2}:
        raise OutfitPackError("Provide a supported makeup safe-region document.")
    schema = payload["schema"]
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
        foundation_masks = {}
        eye_aperture_masks = {}
        if schema == SAFE_REGION_SCHEMA_V2:
            raw_masks = entry.get("foundation_masks") if isinstance(entry, dict) else None
            raw_apertures = entry.get("eye_aperture_masks") if isinstance(entry, dict) else None
            # A silhouette retains legacy makeup only when both maps explicitly
            # use the legacy makeup path. Foundation-bearing variants are
            # separately required to have all canonical masks at import time.
            legacy_only = raw_masks == {} and raw_apertures == {}
            required_states = frozenset() if legacy_only else FOUNDATION_STATES
            if not isinstance(raw_masks, dict) or set(raw_masks) != required_states:
                raise OutfitPackError(f"Invalid foundation safe masks for {silhouette!r}.")
            visibility = (
                None
                if "native_visibility" not in entry
                else _native_visibility(entry["native_visibility"], silhouette)
            )
            foundation_masks = {
                state: _foundation_mask_descriptor(
                    raw_masks[state],
                    (canvas[0], canvas[1]),
                    asset_root=asset_root,
                    nonvisible=_visibility_flag(visibility, state, "foundation_coverage"),
                )
                for state in sorted(raw_masks)
            }
            if not isinstance(raw_apertures, dict) or set(raw_apertures) != required_states:
                raise OutfitPackError(f"Invalid eye aperture masks for {silhouette!r}.")
            eye_aperture_masks = {
                state: _foundation_mask_descriptor(
                    raw_apertures[state],
                    (canvas[0], canvas[1]),
                    asset_root=asset_root,
                    allow_empty=visibility is None and state == "closed",
                    nonvisible=_visibility_flag(visibility, state, "eye_aperture"),
                )
                for state in sorted(raw_apertures)
            }
        parsed[silhouette] = MakeupSafeRegion(
            silhouette,
            (canvas[0], canvas[1]),
            rig,
            frozendict({slot: tuple(_rect(rect) for rect in rects) for slot, rects in slots.items()}),
            frozendict(foundation_masks),
            frozendict(eye_aperture_masks),
        )
    return frozendict(parsed)


def load_makeup_safe_regions(path: Path | None = None) -> frozendict[str, MakeupSafeRegion]:
    source = SAFE_REGION_PATH if path is None else Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise OutfitPackError("The makeup safe-region document is unavailable.") from None
    return parse_makeup_safe_regions(payload, asset_root=source.parent.parent)


def alpha_plane(png: bytes) -> tuple[bytes, int, int]:
    """Decode one PNG into a tightly packed 8-bit alpha plane (row-major with contiguous rows)."""
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


def makeup_layer_escapes(
    png: bytes,
    region: MakeupSafeRegion,
    slot: str,
    *,
    state: str = "rest",
) -> bool:
    """Whether one makeup layer paints outside its slot's safe region."""
    plane, width, height = alpha_plane(png)
    if (width, height) != region.canvas:
        return True
    if slot == FOUNDATION_SLOT:
        mask = region.foundation_mask(state)
        if mask is None or mask.canvas != region.canvas or len(mask.alpha) != width * height:
            return True
        return any(pixel and not allowed for pixel, allowed in zip(plane, mask.alpha, strict=True))
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
                    if silhouette in variant.foundation_silhouettes and (
                        not region.foundation_masks or not region.eye_aperture_masks
                    ):
                        raise OutfitPackError(
                            f"Foundation makeup for {silhouette!r} has no canonical state masks."
                        )
                    for asset in assets:
                        if makeup_layer_escapes(archive.read(asset.path), region, asset.slot):
                            raise OutfitPackError(
                                f"Makeup layer {asset.path} ({item.item_id}/{variant.variant_id}) paints outside "
                                f"the {asset.slot} safe region of {silhouette}."
                            )
                for state, poses in variant.eye_states.items():
                    for silhouette, assets in poses.items():
                        region = table[silhouette]
                        for asset in assets:
                            if makeup_layer_escapes(
                                archive.read(asset.path), region, asset.slot, state=state,
                            ):
                                raise OutfitPackError(
                                    f"Makeup layer {asset.path} ({item.item_id}/{variant.variant_id}) paints outside "
                                    f"the {asset.slot} {state} safe region of {silhouette}."
                                )


def clamp_makeup_intensity(value: object) -> float:
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError):
        return DEFAULT_MAKEUP_INTENSITY
    if number != number:  # NaN remains outside the alpha multiplier.
        return DEFAULT_MAKEUP_INTENSITY
    return round(min(1.0, max(0.0, number)), INTENSITY_DECIMALS)


_LAST_VALID_MAKEUP_INTENSITIES: dict[Path, float] = {}
_MAKEUP_READ_WARNED: set[Path] = set()
_LAST_VALID_SLOT_INTENSITIES: dict[Path, frozendict[str, float]] = {}
_SLOT_READ_WARNED: set[Path] = set()
DEFAULT_SLOT_INTENSITIES = frozendict({slot: 1.0 for slot in MAKEUP_SLOTS})
DEFAULT_SLOT_INTENSITIES_V2 = frozendict({slot: 1.0 for slot in MAKEUP_SLOTS_V2})
# This process-local lock protects the read-modify-write pair; atomic replacement protects one write.
_MAKEUP_STATE_LOCK = RLock()


def _makeup_store_key(store: Path) -> Path:
    return Path(store)


def _notify_makeup_read_failure(
    store: Path,
    notify: Callable[[str], None] | None,
) -> None:
    if notify is None:
        return
    with _MAKEUP_STATE_LOCK:
        if store in _MAKEUP_READ_WARNED:
            return
        _MAKEUP_READ_WARNED.add(store)
    notify(MAKEUP_READ_FAILURE_MESSAGE)


def _last_valid_makeup_intensity(store: Path) -> float:
    with _MAKEUP_STATE_LOCK:
        return _LAST_VALID_MAKEUP_INTENSITIES.get(store, DEFAULT_MAKEUP_INTENSITY)


def read_makeup_intensity(
    store: Path,
    notify: Callable[[str], None] | None = None,
) -> float:
    """The user's makeup intensity (0 = bare face, 1 = authored layer); defaults to 1."""
    store = _makeup_store_key(store)
    path = store / MAKEUP_STATE_FILE
    try:
        if not path.exists():
            intensity = _last_valid_makeup_intensity(store)
            with _MAKEUP_STATE_LOCK:
                _LAST_VALID_MAKEUP_INTENSITIES[store] = intensity
            return intensity
    except OSError:
        _notify_makeup_read_failure(store, notify)
        return _last_valid_makeup_intensity(store)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        _notify_makeup_read_failure(store, notify)
        return _last_valid_makeup_intensity(store)
    if not isinstance(payload, dict) or "intensity" not in payload:
        _notify_makeup_read_failure(store, notify)
        return _last_valid_makeup_intensity(store)
    value = payload["intensity"]
    if isinstance(value, bool):
        _notify_makeup_read_failure(store, notify)
        return _last_valid_makeup_intensity(store)
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError):
        _notify_makeup_read_failure(store, notify)
        return _last_valid_makeup_intensity(store)
    if not isfinite(number):
        _notify_makeup_read_failure(store, notify)
        return _last_valid_makeup_intensity(store)
    intensity = clamp_makeup_intensity(value)
    with _MAKEUP_STATE_LOCK:
        _LAST_VALID_MAKEUP_INTENSITIES[store] = intensity
        _MAKEUP_READ_WARNED.discard(store)
    return intensity


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


def _slot_defaults(slots: frozenset[str]) -> frozendict[str, float]:
    if not slots or not slots.issubset(MAKEUP_SLOTS_V2):
        raise ValueError("Provide a supported makeup slots")
    return DEFAULT_SLOT_INTENSITIES_V2 if slots == MAKEUP_SLOTS_V2 else frozendict(
        {slot: 1.0 for slot in slots}
    )


def _cached_slot_intensities(store: Path, slots: frozenset[str]) -> frozendict[str, float]:
    defaults = _slot_defaults(slots)
    previous = _LAST_VALID_SLOT_INTENSITIES.get(store, DEFAULT_SLOT_INTENSITIES_V2)
    if previous is None:
        previous = defaults
    return frozendict({slot: previous.get(slot, 1.0) for slot in slots})


def read_makeup_slot_intensities(
    store: Path,
    notify: Callable[[str], None] | None = None,
    *,
    slots: frozenset[str] | None = None,
) -> frozendict[str, float]:
    """Read optional per-slot multipliers while preserving the legacy default shape."""
    store = _makeup_store_key(store)
    requested = frozenset(slots) if slots is not None else MAKEUP_SLOTS
    with _MAKEUP_STATE_LOCK:
        previous = _cached_slot_intensities(store, requested)
    try:
        path = store / MAKEUP_STATE_FILE
        if not path.exists():
            return previous
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Makeup state must be an object")
        persisted_slots = payload.get("slot_intensities", {})
        if not isinstance(persisted_slots, dict):
            raise ValueError("Provide a supported makeup slots")
        if not set(persisted_slots).issubset(MAKEUP_SLOTS_V2):
            raise ValueError("Provide a supported makeup slots")
        values = dict(DEFAULT_SLOT_INTENSITIES_V2)
        for slot, value in persisted_slots.items():
            if isinstance(value, bool) or not isfinite(float(value)):
                raise ValueError("Provide a supported makeup slot intensity")
            values[slot] = clamp_makeup_intensity(value)
    except (OSError, UnicodeError, OverflowError, ValueError, TypeError):
        if notify is not None:
            with _MAKEUP_STATE_LOCK:
                should_notify = store not in _SLOT_READ_WARNED
                if should_notify:
                    _SLOT_READ_WARNED.add(store)
            if should_notify:
                notify(MAKEUP_READ_FAILURE_MESSAGE)
        return previous
    result = frozendict({slot: values[slot] for slot in requested})
    with _MAKEUP_STATE_LOCK:
        _LAST_VALID_SLOT_INTENSITIES[store] = frozendict(values)
        _SLOT_READ_WARNED.discard(store)
    return result


def _makeup_state_payload(
    intensity: float,
    slots: frozendict[str, float],
    *,
    allowed_slots: frozenset[str] = MAKEUP_SLOTS,
) -> dict:
    payload = {"intensity": intensity}
    if slots != _slot_defaults(allowed_slots):
        defaults = _slot_defaults(allowed_slots)
        payload["slot_intensities"] = {
            slot: value for slot, value in slots.items()
            if value != defaults[slot]
        }
    return payload


def write_makeup_slot_intensity(
    store: Path,
    slot: str,
    value: object,
    *,
    slots: frozenset[str] | None = None,
) -> float:
    """Change one detail while preserving global intensity or another slot."""
    # Writes use the v2 state shape so a foundation value survives a later
    # legacy-slot edit.  Reading still accepts an old three-slot JSON and
    # supplies the foundation multiplier's neutral default.
    requested = frozenset(slots or MAKEUP_SLOTS_V2)
    if slot not in requested or not requested.issubset(MAKEUP_SLOTS_V2):
        raise ValueError(f"Unknown makeup slot: {slot}")
    store = _makeup_store_key(store)
    with _MAKEUP_STATE_LOCK:
        values = dict(read_makeup_slot_intensities(store, slots=MAKEUP_SLOTS_V2))
        values[slot] = clamp_makeup_intensity(value)
        selected = frozendict(values)
        _atomic_json(
            store / MAKEUP_STATE_FILE,
            _makeup_state_payload(
                read_makeup_intensity(store), selected, allowed_slots=MAKEUP_SLOTS_V2,
            ),
        )
        _LAST_VALID_SLOT_INTENSITIES[store] = selected
        _SLOT_READ_WARNED.discard(store)
        return selected[slot]


def write_makeup_intensity(store: Path, value: object) -> float:
    """Persist the intensity atomically next to active.json; returns the clamped value."""
    intensity = clamp_makeup_intensity(value)
    store = _makeup_store_key(store)
    with _MAKEUP_STATE_LOCK:
        slots = read_makeup_slot_intensities(store, slots=MAKEUP_SLOTS_V2)
        _atomic_json(
            store / MAKEUP_STATE_FILE,
            _makeup_state_payload(intensity, slots, allowed_slots=MAKEUP_SLOTS_V2),
        )
        _LAST_VALID_MAKEUP_INTENSITIES[store] = intensity
        _MAKEUP_READ_WARNED.discard(store)
        return intensity


def select_builtin_makeup(store: Path, variant_id: str) -> None:
    """Choose a built-in variant, requiring optional material before persisting it."""
    if variant_id not in BUILTIN_MAKEUP_VARIANTS:
        raise OutfitPackError("Use a recognized built-in makeup variant.")
    if variant_id not in BUILTIN_MAKEUP_ALWAYS_VISIBLE_VARIANTS:
        installed = outfit_pack.list_installed_selections(Path(store), "makeup")
        if not any(
            selection.pack_id == BUILTIN_MAKEUP_PACK_ID
            and selection.item_id == BUILTIN_MAKEUP_ITEM_ID
            and selection.variant_id == variant_id
            for selection in installed
        ):
            raise OutfitPackError("The selected built-in makeup variant is not installed.")
    active_path = Path(store) / ACTIVE_STATE_FILE
    try:
        active = json.loads(active_path.read_text(encoding="utf-8")) if active_path.is_file() else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise OutfitPackError("Provide a supported saved appearance state.") from None
    if not isinstance(active, dict):
        raise OutfitPackError("Provide a supported saved appearance state.")
    active.pop("_ensemble", None)
    active["makeup"] = {"pack_id": "builtin", "item_id": "builtin", "variant_id": variant_id}
    _atomic_json(active_path, active)


def builtin_makeup_pack_path() -> Path:
    """The official built-in makeup pack and its classic, light, and glamorous variants."""
    return outfit_pack.OFFICIAL_PACK_ROOT / f"{BUILTIN_MAKEUP_PACK_ID}.mohan-outfit"


def builtin_makeup_identity(variant_id: str) -> tuple[str, str, str]:
    if variant_id not in BUILTIN_MAKEUP_VARIANTS:
        raise OutfitPackError("Use a recognized built-in makeup variant.")
    return (BUILTIN_MAKEUP_PACK_ID, BUILTIN_MAKEUP_ITEM_ID, variant_id)
