"""Strict immutable loaders for character-owned rig and expression data."""

from __future__ import annotations

lazy import json
lazy import math
lazy from dataclasses import dataclass
lazy from pathlib import Path

RIG_SCHEMA = "flameblade.character-rig.v1"
EXPRESSION_SCHEMA = "flameblade.expression-state-catalog.v1"
SCHEMA_VERSION = 1
PAIR_LENGTH = 2
TRIPLE_LENGTH = 3
RECT_LENGTH = 4
HAND_LANDMARK_COUNT = 21
FULL_BODY_LAYER_COUNT = 25
FULL_VIEW_COUNT = 24
MIN_PITCH_DEGREES = -45
MAX_PITCH_DEGREES = 45
MAX_YAW_DEGREES = 180
MAX_CHANNEL_VALUE = 255

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CHARACTER_ROOT = _PROJECT_ROOT / "assets" / "characters" / "mohan"
DEFAULT_RIG_MANIFEST_PATH = _DEFAULT_CHARACTER_ROOT / "rig" / "rig-manifest.json"
DEFAULT_EXPRESSION_CATALOG_PATH = (
    _DEFAULT_CHARACTER_ROOT / "expressions" / "state-catalog.json"
)


@dataclass(frozen=True, slots=True)
class CanvasSpec:
    width: int
    height: int
    mode: str


@dataclass(frozen=True, slots=True)
class ViewportSpec:
    canvas_width: int
    image_size: int
    base_y: int
    scale_min: int
    scale_max: int
    scale_default: int


@dataclass(frozen=True, slots=True)
class ViewRingSpec:
    yaw_step_degrees: int
    pitch_degrees: tuple[int, ...]
    yaws: tuple[int, ...]
    legacy_aliases: frozendict[str, int]
    mirror_views: frozendict[str, str]


@dataclass(frozen=True, slots=True)
class ArmSpec:
    shoulder: tuple[float, float]
    upper_arm_length: float
    forearm_length: float
    hand_length: float
    shoulder_degrees: float
    elbow_degrees: float
    wrist_degrees: float


@dataclass(frozen=True, slots=True)
class PoseSpec:
    pose_id: str
    yaw_degrees: int
    legacy_face_pose: str
    silhouette: str
    left_arm: ArmSpec
    right_arm: ArmSpec
    required_corrections: frozenset[str]
    speech_safe: bool
    tags: frozenset[str]


@dataclass(frozen=True, slots=True)
class PhysicsSpec:
    pose_suffixes: tuple[tuple[str, str], ...]
    speech_frame_prefixes: tuple[str, ...]
    ornament_anchors: frozendict[str, tuple[int, int]]
    hair_anchors: frozendict[str, frozendict[str, tuple[int, int]]]
    sleeve_anchors: frozendict[str, frozendict[str, tuple[int, int]]]
    pose_switch_probability: float
    breath_lift_scale: float
    max_sleeve_lift: float
    max_gesture_sway: float
    gesture_energy_threshold: float


@dataclass(frozen=True, slots=True)
class FaceCalibrationSpec:
    layer_opacity_eye_lid: float
    layer_opacity_eyeliner: float
    layer_opacity_blush: float
    layer_opacity_iris: float
    mouth_stretch_ratio: float
    mouth_rounding_ratio: float
    mouth_height_ratio: float
    mouth_aperture_normalizer: float
    jaw_translation_factor: float
    brow_lift_factor: float
    brow_tension_factor: float
    corner_smile_factor: float
    corner_smile_lift_factor: float
    shyness_blush_weight: float
    shyness_gaze_weight: float
    shyness_lip_weight: float
    viseme_u_inward_lerp: float


@dataclass(frozen=True, slots=True)
class BodyProportionsSpec:
    root_to_pelvis: float
    pelvis_to_spine: float
    spine_to_chest: float
    chest_to_neck: float
    neck_to_head: float
    hip_half_width: float
    thigh_length: float
    shin_length: float
    foot_length: float
    toe_length: float


@dataclass(frozen=True, slots=True)
class BodyMeasurementsSpec:
    height_cm: int
    weight_kg: int
    bust_cm: int
    underbust_cm: int
    waist_cm: int
    hips_cm: int


@dataclass(frozen=True, slots=True)
class FullBodyCalibrationSpec:
    proportions: BodyProportionsSpec
    root: tuple[float, float]
    minimum_perspective: float
    left_leg_degrees: tuple[float, float, float]
    right_leg_degrees: tuple[float, float, float]
    heel_center_offset: float
    sole_half_width: float
    direction_vectors: frozendict[str, tuple[float, float]]


@dataclass(frozen=True, slots=True)
class CharacterRigManifest:
    schema: str
    schema_version: int
    character_id: str
    body_profile_id: str
    body_profile_version: int
    body_measurements: BodyMeasurementsSpec
    body_art_direction: str
    full_body_canvas: CanvasSpec
    half_body_asset_canvas: CanvasSpec
    viewport: ViewportSpec
    view_ring: ViewRingSpec
    layer_z_order: tuple[str, ...]
    required_full_body_layers: frozenset[str]
    registered_composite_layers: tuple[str, ...]
    face_authority_layers: tuple[str, ...]
    side_view_yaw_limit: int
    mouth_authority_manifest: str
    pose_silhouettes: frozendict[str, str]
    gesture_silhouettes: frozendict[str, str]
    behavior_pose_views: frozendict[str, str]
    back_depth: frozendict[str, int]
    poses: tuple[PoseSpec, ...]
    legacy_pose_ids: tuple[str, ...]
    relaxed_hand_facing: str
    relaxed_hand_points: tuple[tuple[float, float], ...]
    physics: PhysicsSpec
    face_calibration: FaceCalibrationSpec
    full_body_calibration: FullBodyCalibrationSpec
    gesture_actions: frozendict[str, str]


@dataclass(frozen=True, slots=True)
class ExpressionRuleSpec:
    priority: int
    minimum_ms: int
    maximum_ms: int
    cooldown_ms: int


@dataclass(frozen=True, slots=True)
class FacePoseAssetSpec:
    base: str
    blink: str
    open_mouth: str
    viseme_i: str
    viseme_u: str
    viseme_o: str
    face: str
    eyes: str
    mouth_rect: tuple[int, int, int, int]
    eye_rects: tuple[tuple[int, int, int, int], ...]


@dataclass(frozen=True, slots=True)
class BrowGuardSpec:
    regions: tuple[tuple[int, int, int, int], ...]
    dark_limit: int
    eureka_dark_limit: int
    eureka_guard_width: int
    native_guard_width: int
    guard_sigma: float
    expressions: frozenset[str]


@dataclass(frozen=True, slots=True)
class SourceBoundExasperatedSpec:
    mouth_bounds: tuple[int, int, int, int]
    mouth_variants: frozendict[str, str]


@dataclass(frozen=True, slots=True)
class ExpressionStateCatalog:
    schema: str
    schema_version: int
    character_id: str
    state_to_pose: frozendict[str, str]
    emotion_to_expression: frozendict[str, str]
    new_expression_assets: tuple[str, ...]
    eyes_closed_expressions: frozenset[str]
    gesture_speech_expressions: frozenset[str]
    neutral_viseme_asset_stems: frozendict[str, str]
    speaking_blink_prefixes: tuple[tuple[str, str], ...]
    speech_frame_suffixes: tuple[str, ...]
    derived_viseme_suffixes: frozendict[str, str]
    blink_frames: frozendict[str, str]
    half_blink_frames: frozendict[str, str]
    blush_preserving_blink_expressions: frozenset[str]
    base_image_assets: tuple[str, ...]
    legacy_viseme_assets: tuple[str, ...]
    face_pose_assets: frozendict[str, FacePoseAssetSpec]
    mouth_rect_by_pose: frozendict[str, tuple[int, int, int, int]]
    mouth_rect_overrides: frozendict[str, tuple[int, int, int, int]]
    closed_speech_expressions: frozendict[str, str]
    face_offsets: frozendict[str, tuple[int, int]]
    eye_offsets: frozendict[str, tuple[int, int]]
    mouth_offsets: frozendict[str, tuple[int, int]]
    brow_guard: BrowGuardSpec
    source_bound_exasperated: SourceBoundExasperatedSpec
    default_rule: ExpressionRuleSpec
    expression_rules: frozendict[str, ExpressionRuleSpec]
    base_expressions: frozenset[str]
    ai_wait_expressions: frozenset[str]
    ai_wait_current_states: frozenset[str]


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Character data contains a duplicate key: {key!r}.")
        result[key] = value
    return result


def _reject_non_finite_number(value: str) -> None:
    raise ValueError(f"Character data contains a non-finite number: {value}.")


def _read_payload(path: Path) -> dict[str, object]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Cannot read character data: {path.name}.") from error
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_non_finite_number,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"Character data is not valid strict JSON: {path.name}.") from error
    if not isinstance(payload, dict):
        raise ValueError("Character data root must be an object.")
    return payload


def _object(
    value: object,
    *,
    name: str,
    keys: frozenset[str],
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{name} must contain exactly: {', '.join(sorted(keys))}.")
    return value


def _array(value: object, *, name: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array.")
    return value


def _text(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty trimmed text.")
    return value


def _integer(value: object, *, name: str, minimum: int | None = None) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise ValueError(f"{name} must be a supported integer.")
    return value


def _number(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number.")
    return result


def _boolean(value: object, *, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be boolean.")
    return value


def _unique_texts(value: object, *, name: str) -> tuple[str, ...]:
    result = tuple(
        _text(item, name=f"{name} item")
        for item in _array(value, name=name)
    )
    if not result or len(result) != len(set(result)):
        raise ValueError(f"{name} must contain unique text values.")
    return result


def _int_pair(value: object, *, name: str) -> tuple[int, int]:
    items = _array(value, name=name)
    if len(items) != PAIR_LENGTH:
        raise ValueError(f"{name} must contain two integers.")
    return (
        _integer(items[0], name=f"{name}[0]"),
        _integer(items[1], name=f"{name}[1]"),
    )


def _float_pair(value: object, *, name: str) -> tuple[float, float]:
    items = _array(value, name=name)
    if len(items) != PAIR_LENGTH:
        raise ValueError(f"{name} must contain two numbers.")
    return (
        _number(items[0], name=f"{name}[0]"),
        _number(items[1], name=f"{name}[1]"),
    )


def _float_triple(value: object, *, name: str) -> tuple[float, float, float]:
    items = _array(value, name=name)
    if len(items) != TRIPLE_LENGTH:
        raise ValueError(f"{name} must contain three numbers.")
    return (
        _number(items[0], name=f"{name}[0]"),
        _number(items[1], name=f"{name}[1]"),
        _number(items[2], name=f"{name}[2]"),
    )


def _rect(value: object, *, name: str) -> tuple[int, int, int, int]:
    items = _array(value, name=name)
    if len(items) != RECT_LENGTH:
        raise ValueError(f"{name} must contain x, y, width, and height.")
    result = (
        _integer(items[0], name=f"{name}[0]"),
        _integer(items[1], name=f"{name}[1]"),
        _integer(items[2], name=f"{name}[2]"),
        _integer(items[3], name=f"{name}[3]"),
    )
    if result[2] <= 0 or result[3] <= 0:
        raise ValueError(f"{name} width and height must be positive.")
    return result


def _text_mapping(value: object, *, name: str) -> frozendict[str, str]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{name} must be a non-empty object.")
    return frozendict(
        {
            _text(key, name=f"{name} key"): _text(item, name=f"{name}.{key}")
            for key, item in value.items()
        }
    )


def _canvas(value: object, *, name: str) -> CanvasSpec:
    payload = _object(
        value,
        name=name,
        keys=frozenset({"width", "height", "mode"}),
    )
    result = CanvasSpec(
        _integer(payload["width"], name=f"{name}.width", minimum=1),
        _integer(payload["height"], name=f"{name}.height", minimum=1),
        _text(payload["mode"], name=f"{name}.mode"),
    )
    if result.mode != "RGBA":
        raise ValueError(f"{name}.mode must be RGBA.")
    return result
