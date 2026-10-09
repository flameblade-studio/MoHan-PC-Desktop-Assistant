"""Compatibility facade for MoHan-owned and character-neutral constants.

Domain-agnostic values are re-exported from :mod:`domain.core_constants`.
Character-owned asset geometry is adapted from the strict bundled rig
manifest while the long-standing public constant names stay compatible.

Import style::

    from domain.constants import HTTP_NOT_FOUND, SERVER_ERROR_BOUNDARY
    from domain.constants import PNG_SIGNATURE, SHA256_HEX_LENGTH
    from domain.constants import HOURS_PER_DAY, SECONDS_PER_DAY
"""

lazy import json
lazy from pathlib import Path, PurePosixPath
lazy from typing import Final

lazy from domain.character_runtime_data import default_rig_manifest
lazy from domain import core_constants as _core_constants

BYTES_PER_PIXEL = _core_constants.BYTES_PER_PIXEL
BYTE_MAX = _core_constants.BYTE_MAX
FLOAT_COMPARISON_EPSILON = _core_constants.FLOAT_COMPARISON_EPSILON
HOURS_PER_DAY = _core_constants.HOURS_PER_DAY
HTTP_BAD_GATEWAY = _core_constants.HTTP_BAD_GATEWAY
HTTP_CLIENT_ERROR_BOUNDARY = _core_constants.HTTP_CLIENT_ERROR_BOUNDARY
HTTP_FORBIDDEN = _core_constants.HTTP_FORBIDDEN
HTTP_GATEWAY_TIMEOUT = _core_constants.HTTP_GATEWAY_TIMEOUT
HTTP_MAX_STATUS = _core_constants.HTTP_MAX_STATUS
HTTP_MIN_STATUS = _core_constants.HTTP_MIN_STATUS
HTTP_NOT_FOUND = _core_constants.HTTP_NOT_FOUND
HTTP_OK = _core_constants.HTTP_OK
HTTP_SERVER_ERROR_BOUNDARY = _core_constants.HTTP_SERVER_ERROR_BOUNDARY
HTTP_SERVER_ERROR_MAX = _core_constants.HTTP_SERVER_ERROR_MAX
HTTP_SERVICE_UNAVAILABLE = _core_constants.HTTP_SERVICE_UNAVAILABLE
HTTP_TOO_MANY_REQUESTS = _core_constants.HTTP_TOO_MANY_REQUESTS
HTTP_UNAUTHORIZED = _core_constants.HTTP_UNAUTHORIZED
MINUTES_PER_HOUR = _core_constants.MINUTES_PER_HOUR
PCM16_MAX_SAMPLE = _core_constants.PCM16_MAX_SAMPLE
PCM16_MIN_SAMPLE = _core_constants.PCM16_MIN_SAMPLE
PCM16_SAMPLE_WIDTH = _core_constants.PCM16_SAMPLE_WIDTH
PNG_BIT_DEPTH = _core_constants.PNG_BIT_DEPTH
PNG_COLOR_TYPE_RGBA = _core_constants.PNG_COLOR_TYPE_RGBA
PNG_MIN_HEADER_LENGTH = _core_constants.PNG_MIN_HEADER_LENGTH
PNG_SIGNATURE = _core_constants.PNG_SIGNATURE
RGB_CHANNELS = _core_constants.RGB_CHANNELS
RGB_MAX = _core_constants.RGB_MAX
SECONDS_PER_DAY = _core_constants.SECONDS_PER_DAY
SECONDS_PER_HOUR = _core_constants.SECONDS_PER_HOUR
SECONDS_PER_MINUTE = _core_constants.SECONDS_PER_MINUTE
SHA256_HEX_LENGTH = _core_constants.SHA256_HEX_LENGTH
SHA256_RAW_LENGTH = _core_constants.SHA256_RAW_LENGTH
SYMLINK_FILE_TYPE = _core_constants.SYMLINK_FILE_TYPE

__all__ = (
    "BROW_LIFT_FACTOR",
    "BROW_TENSION_FACTOR",
    "BYTES_PER_PIXEL",
    "BYTE_MAX",
    "CHARACTER_ASSET_PATHS",
    "CHARACTER_EXPRESSION_ROLES",
    "CHARACTER_LAYER_ROLES",
    "CHARACTER_POSE_ROLES",
    "CORNER_SMILE_FACTOR",
    "CORNER_SMILE_LIFT_FACTOR",
    "DEFAULT_WEATHER_CONDITION",
    "DEFAULT_WEATHER_TEMPERATURE_C",
    "FLOAT_COMPARISON_EPSILON",
    "FULL_BODY_LAYER_COUNT",
    "FULL_BODY_LAYER_Z_ORDER",
    "HOURS_PER_DAY",
    "HTTP_BAD_GATEWAY",
    "HTTP_CLIENT_ERROR_BOUNDARY",
    "HTTP_FORBIDDEN",
    "HTTP_GATEWAY_TIMEOUT",
    "HTTP_MAX_STATUS",
    "HTTP_MIN_STATUS",
    "HTTP_NOT_FOUND",
    "HTTP_OK",
    "HTTP_SERVER_ERROR_BOUNDARY",
    "HTTP_SERVER_ERROR_MAX",
    "HTTP_SERVICE_UNAVAILABLE",
    "HTTP_TOO_MANY_REQUESTS",
    "HTTP_UNAUTHORIZED",
    "INTERPOLATION_EPSILON",
    "JAW_TRANSLATION_FACTOR",
    "LAYER_OPACITY_BLUSH",
    "LAYER_OPACITY_EYELINER",
    "LAYER_OPACITY_EYE_LID",
    "LAYER_OPACITY_IRIS",
    "MINUTES_PER_HOUR",
    "MOUTH_APERTURE_NORMALIZER",
    "MOUTH_HEIGHT_RATIO",
    "MOUTH_ROUNDING_RATIO",
    "MOUTH_STRETCH_RATIO",
    "PCM16_MAX_SAMPLE",
    "PCM16_MIN_SAMPLE",
    "PCM16_SAMPLE_WIDTH",
    "PNG_BIT_DEPTH",
    "PNG_COLOR_TYPE_RGBA",
    "PNG_MIN_HEADER_LENGTH",
    "PNG_SIGNATURE",
    "POSE_ATLAS_GENERATION",
    "POSE_ATLAS_LAYERED_RELATIVE_ROOT",
    "POSE_ATLAS_LAYERED_ROOT_NAME",
    "POSE_ATLAS_RELATIVE_ROOT",
    "POSE_ATLAS_ROOT_NAME",
    "RGB_CHANNELS",
    "RGB_MAX",
    "SECONDS_PER_DAY",
    "SECONDS_PER_HOUR",
    "SECONDS_PER_MINUTE",
    "SHA256_HEX_LENGTH",
    "SHA256_RAW_LENGTH",
    "SHYNESS_BLUSH_WEIGHT",
    "SHYNESS_GAZE_WEIGHT",
    "SHYNESS_LIP_WEIGHT",
    "SYMLINK_FILE_TYPE",
    "VISEME_FRAME_INTERVAL_MS",
    "Final",
    "Path",
    "PurePosixPath",
    "default_rig_manifest",
    "json",
)

_RIG_MANIFEST = default_rig_manifest()

_RUNTIME_BINDING_KEYS = frozenset(
    {"schema", "schema_version", "asset_paths", "pose_roles", "expression_roles", "layer_roles"}
)
_RUNTIME_BINDING_SECTIONS = (
    "asset_paths",
    "pose_roles",
    "expression_roles",
    "layer_roles",
)
_RUNTIME_BINDING_SECTION_KEYS = frozendict({
    "asset_paths": frozenset({
        "application_icon",
        "appearance_masks",
        "appearance_silhouettes",
        "body_overlays",
        "dashboard_artwork",
        "first_run_portrait",
        "garment_visibility",
        "halfbody_detachable",
        "halfbody_layers",
        "halfbody_root",
        "hand_overlays",
        "lobby_backdrop",
        "onboarding_artwork",
        "source_bound_expression",
        "theme_artwork",
    }),
    "pose_roles": frozenset({
        "front_idle", "left_cheek", "left_idle", "rear_full", "rear_left",
        "rear_right", "right_idle",
    }),
    "expression_roles": frozenset({
        "amusement", "attention", "bashful", "bashful_cute", "concern",
        "exasperation", "gentle", "gentle_scold", "happiness", "insight",
        "mock_strike", "noticed", "pride", "protection", "relief", "reminder",
        "resolve", "side_gaze", "surprise", "thought", "worry",
    }),
    "layer_roles": frozenset({
        "left_blush", "left_brow", "left_eyelid", "left_eyeliner", "left_iris",
        "left_mouth_corner", "left_side_hair", "left_sleeve", "lower_lip",
        "mouth_cavity", "rear_hair", "right_blush", "right_brow", "right_eyelid",
        "right_eyeliner", "right_iris", "right_mouth_corner", "right_side_hair",
        "right_sleeve", "teeth_and_tongue", "upper_lip",
    }),
})


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate runtime-binding field: {key}")
        result[key] = value
    return result


def _load_runtime_bindings() -> frozendict[str, frozendict[str, str]]:
    path = Path(__file__).resolve().parents[1].joinpath(
        "assets", "characters", "mohan", "rig", "runtime-bindings.json"
    )
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise RuntimeError("Bundled character runtime bindings must be valid UTF-8 JSON.") from error
    if (
        not isinstance(payload, dict)
        or set(payload) != _RUNTIME_BINDING_KEYS
        or payload.get("schema") != "flameblade.character-runtime-bindings.v1"
        or payload.get("schema_version") != 1
    ):
        raise RuntimeError("Bundled character runtime bindings use an unsupported schema.")
    sections: dict[str, frozendict[str, str]] = {}
    for section in _RUNTIME_BINDING_SECTIONS:
        values = payload[section]
        if (
            not isinstance(values, dict)
            or set(values) != _RUNTIME_BINDING_SECTION_KEYS[section]
            or any(
                not isinstance(key, str)
                or not key
                or not isinstance(value, str)
                or not value
                for key, value in values.items()
            )
        ):
            raise RuntimeError("Bundled character runtime bindings require non-empty text maps.")
        sections[section] = frozendict(values)
    for value in sections["asset_paths"].values():
        relative = PurePosixPath(value)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise RuntimeError("Bundled character asset paths must remain relative.")
    return frozendict(sections)


_RUNTIME_BINDINGS = _load_runtime_bindings()
CHARACTER_ASSET_PATHS: Final = _RUNTIME_BINDINGS["asset_paths"]
CHARACTER_POSE_ROLES: Final = _RUNTIME_BINDINGS["pose_roles"]
CHARACTER_EXPRESSION_ROLES: Final = _RUNTIME_BINDINGS["expression_roles"]
CHARACTER_LAYER_ROLES: Final = _RUNTIME_BINDINGS["layer_roles"]

# ---------------------------------------------------------------------------
# Parametric 2.5D face gradient parameters.
#
# These drive the layered face renderer's continuous deformation. Each value is
# a dimensionless ratio (0.0..1.0) or a pixel/scale factor that maps a single
# :class:`~domain.face_rig.FaceMotionFrame` control onto one authored layer.
# ---------------------------------------------------------------------------
# Layer opacity ceilings for independent facial features.
LAYER_OPACITY_EYE_LID: Final = _RIG_MANIFEST.face_calibration.layer_opacity_eye_lid
LAYER_OPACITY_EYELINER: Final = (
    _RIG_MANIFEST.face_calibration.layer_opacity_eyeliner
)
LAYER_OPACITY_BLUSH: Final = _RIG_MANIFEST.face_calibration.layer_opacity_blush
LAYER_OPACITY_IRIS: Final = _RIG_MANIFEST.face_calibration.layer_opacity_iris

# Mouth articulation stretch/scale ratios.
MOUTH_STRETCH_RATIO: Final = _RIG_MANIFEST.face_calibration.mouth_stretch_ratio
MOUTH_ROUNDING_RATIO: Final = _RIG_MANIFEST.face_calibration.mouth_rounding_ratio
MOUTH_HEIGHT_RATIO: Final = _RIG_MANIFEST.face_calibration.mouth_height_ratio
MOUTH_APERTURE_NORMALIZER: Final = (
    _RIG_MANIFEST.face_calibration.mouth_aperture_normalizer
)

# Jaw / brow / corner translation factors (pixels per unit control).
JAW_TRANSLATION_FACTOR: Final = _RIG_MANIFEST.face_calibration.jaw_translation_factor
BROW_LIFT_FACTOR: Final = _RIG_MANIFEST.face_calibration.brow_lift_factor
BROW_TENSION_FACTOR: Final = _RIG_MANIFEST.face_calibration.brow_tension_factor
CORNER_SMILE_FACTOR: Final = _RIG_MANIFEST.face_calibration.corner_smile_factor
CORNER_SMILE_LIFT_FACTOR: Final = (
    _RIG_MANIFEST.face_calibration.corner_smile_lift_factor
)

# Micro-expression chain weights (shyness cascade: blush → gaze → lips).
SHYNESS_BLUSH_WEIGHT: Final = _RIG_MANIFEST.face_calibration.shyness_blush_weight
SHYNESS_GAZE_WEIGHT: Final = _RIG_MANIFEST.face_calibration.shyness_gaze_weight
SHYNESS_LIP_WEIGHT: Final = _RIG_MANIFEST.face_calibration.shyness_lip_weight

# Sub-frame interpolation timing (50 Hz speech clock).
VISEME_FRAME_INTERVAL_MS: Final = 20
INTERPOLATION_EPSILON: Final = 1e-4

# ---------------------------------------------------------------------------
# Full-body 25-layer depth order (Z-order, bottom to top).
#
# The full-body parametric renderer composes 25 authored layers per view. This
# tuple is the single source of truth for paint order so that, when the
# character turns, back hair stays behind the body, front hair stays in front of
# the face, and sleeves stay in front of the torso — clothing clipping stays outside the visible result.
# ---------------------------------------------------------------------------
FULL_BODY_LAYER_Z_ORDER: Final = _RIG_MANIFEST.layer_z_order
FULL_BODY_LAYER_COUNT: Final = len(FULL_BODY_LAYER_Z_ORDER)

# ---------------------------------------------------------------------------
# Full-body PoseAtlas generation (runtime switch ratified 2026-09-02).
#
# The 24 static authority views (``{view}.png`` + landmarks/hands sidecars)
# and the 600 layered PNGs live under ``assets/pose-atlas/<root>``.  Every
# runtime consumer, the packaged self-test, the preview packager and the
# audit-tool defaults resolve the CURRENT generation through these names, so a
# generation switch is one edit here instead of twenty scattered literals.
# Generation 1 (``v4`` / ``v4-layered``) stays in the repository as an archive
# and as the calibration reference of the v4-specific golden/rebuild tools.
# ---------------------------------------------------------------------------
POSE_ATLAS_GENERATION: Final = 2
POSE_ATLAS_ROOT_NAME: Final = "v5-base"
POSE_ATLAS_LAYERED_ROOT_NAME: Final = "v5-base-layered"
POSE_ATLAS_RELATIVE_ROOT: Final = "assets/pose-atlas/v5-base"
POSE_ATLAS_LAYERED_RELATIVE_ROOT: Final = "assets/pose-atlas/v5-base-layered"

# ---------------------------------------------------------------------------
# Weather defaults (裁決 2026-08-28): before the wardrobe runtime has written
# ``weather_temperature_c``/``weather_condition``, every reader must assume the
# same comfortable indoor scene.  24 °C sits in the "warm" thermal band and
# "indoor" fits every outfit profile, so nothing complains or changes clothes
# based on observed weather data.
# ---------------------------------------------------------------------------
DEFAULT_WEATHER_TEMPERATURE_C: Final = 24.0
DEFAULT_WEATHER_CONDITION: Final = "indoor"
