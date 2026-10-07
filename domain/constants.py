"""Centralized, cross-module constants for MoHan.

Domain-agnostic values remain literals. Character-owned asset geometry is
adapted from the strict bundled rig manifest while the long-standing public
constant names stay compatible. Every constant is declared with
:data:`typing.Final` so the type checker accepts assignments that follow the
contract.

Import style::

    from domain.constants import HTTP_NOT_FOUND, SERVER_ERROR_BOUNDARY
    from domain.constants import PNG_SIGNATURE, SHA256_HEX_LENGTH
    from domain.constants import HOURS_PER_DAY, SECONDS_PER_DAY
"""

lazy from typing import Final

lazy from domain.character_runtime_data import default_rig_manifest

_RIG_MANIFEST = default_rig_manifest()

# ---------------------------------------------------------------------------
# HTTP status codes and classification boundaries (RFC 9110).
# ---------------------------------------------------------------------------
HTTP_MIN_STATUS: Final = 100
HTTP_MAX_STATUS: Final = 599
HTTP_CLIENT_ERROR_BOUNDARY: Final = 400
HTTP_SERVER_ERROR_BOUNDARY: Final = 500
HTTP_SERVER_ERROR_MAX: Final = 600

HTTP_OK: Final = 200
HTTP_UNAUTHORIZED: Final = 401
HTTP_FORBIDDEN: Final = 403
HTTP_NOT_FOUND: Final = 404
HTTP_TOO_MANY_REQUESTS: Final = 429
HTTP_BAD_GATEWAY: Final = 502
HTTP_SERVICE_UNAVAILABLE: Final = 503
HTTP_GATEWAY_TIMEOUT: Final = 504

# ---------------------------------------------------------------------------
# Cryptographic / hash lengths.
# ---------------------------------------------------------------------------
SHA256_HEX_LENGTH: Final = 64
SHA256_RAW_LENGTH: Final = 32

# ---------------------------------------------------------------------------
# Media / asset constants (PNG, RGBA, color channels).
# ---------------------------------------------------------------------------
PNG_SIGNATURE: Final = b"\x89PNG\r\n\x1a\n"
PNG_BIT_DEPTH: Final = 8
PNG_COLOR_TYPE_RGBA: Final = 6
PNG_MIN_HEADER_LENGTH: Final = 33

BYTES_PER_PIXEL: Final = 4
RGB_CHANNELS: Final = 3
BYTE_MAX: Final = 255
RGB_MAX: Final = 255

SYMLINK_FILE_TYPE: Final = 0o120000

# ---------------------------------------------------------------------------
# PCM16 audio constants.
# ---------------------------------------------------------------------------
PCM16_MIN_SAMPLE: Final = -32_768
PCM16_MAX_SAMPLE: Final = 32_767
PCM16_SAMPLE_WIDTH: Final = 2

# ---------------------------------------------------------------------------
# Time units.
# ---------------------------------------------------------------------------
SECONDS_PER_MINUTE: Final = 60
MINUTES_PER_HOUR: Final = 60
SECONDS_PER_HOUR: Final = 3_600
HOURS_PER_DAY: Final = 24
SECONDS_PER_DAY: Final = 86_400

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

# Absolute tolerance for zero/boundary float comparisons.  Values produced by
# ``clamped()`` are exact, but computed values (gaze confidence, normalized
# vectors, cosine similarity) can drift by a few ULPs; this tolerance makes
# ``== 0.0`` / ``== 1.0`` checks robust while a near-zero value keeps its
# exactly zero.
FLOAT_COMPARISON_EPSILON: Final = 1e-9

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
