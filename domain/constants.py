"""Centralized, cross-module constants for MoHan.

This single module is the project's "constant island": every shared,
domain-agnostic value lives here with a single source of truth. It contains
only pure literals (numbers, strings, booleans) and never imports any project
module, which physically prevents circular imports.

Every constant is declared with :data:`typing.Final` so any accidental
reassignment is rejected by the type checker.

Import style::

    from constants import HTTP_NOT_FOUND, SERVER_ERROR_BOUNDARY
    from constants import PNG_SIGNATURE, SHA256_HEX_LENGTH
    from constants import HOURS_PER_DAY, SECONDS_PER_DAY
"""

lazy from typing import Final

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
LAYER_OPACITY_EYE_LID: Final = 1.0
LAYER_OPACITY_EYELINER: Final = 1.0
LAYER_OPACITY_BLUSH: Final = 1.0
LAYER_OPACITY_IRIS: Final = 1.0

# Mouth articulation stretch/scale ratios.
MOUTH_STRETCH_RATIO: Final = 0.08
MOUTH_ROUNDING_RATIO: Final = 0.02
MOUTH_HEIGHT_RATIO: Final = 0.04
MOUTH_APERTURE_NORMALIZER: Final = 0.18

# Jaw / brow / corner translation factors (pixels per unit control).
JAW_TRANSLATION_FACTOR: Final = 3.0
BROW_LIFT_FACTOR: Final = 3.0
BROW_TENSION_FACTOR: Final = 1.5
CORNER_SMILE_FACTOR: Final = 2.0
CORNER_SMILE_LIFT_FACTOR: Final = 1.0

# Micro-expression chain weights (shyness cascade: blush → gaze → lips).
SHYNESS_BLUSH_WEIGHT: Final = 0.15
SHYNESS_GAZE_WEIGHT: Final = 0.10
SHYNESS_LIP_WEIGHT: Final = 0.05

# Sub-frame interpolation timing (50 Hz speech clock).
VISEME_FRAME_INTERVAL_MS: Final = 20
INTERPOLATION_EPSILON: Final = 1e-4

# Absolute tolerance for zero/boundary float comparisons.  Values produced by
# ``clamped()`` are exact, but computed values (gaze confidence, normalized
# vectors, cosine similarity) can drift by a few ULPs; this tolerance makes
# ``== 0.0`` / ``== 1.0`` checks robust without treating a near-zero value as
# exactly zero.
FLOAT_COMPARISON_EPSILON: Final = 1e-9

# ---------------------------------------------------------------------------
# Full-body 25-layer depth order (Z-order, bottom to top).
#
# The full-body parametric renderer composes 25 authored layers per view. This
# tuple is the single source of truth for paint order so that, when the
# character turns, back hair stays behind the body, front hair stays in front of
# the face, and sleeves stay in front of the torso — no clothing clipping.
# ---------------------------------------------------------------------------
FULL_BODY_LAYER_COUNT: Final = 25
FULL_BODY_LAYER_Z_ORDER: Final = (
    "body",            # torso + clothing base (face region left transparent)
    "hair_back",       # back hair, behind the face
    "base",            # face base
    "jaw",             # jaw influence region
    "oral_cavity",     # dark oral cavity (open mouth)
    "teeth_tongue",    # teeth / tongue (open mouth)
    "lip_lower",       # lower lip
    "lip_upper",       # upper lip
    "corner_left",     # left mouth corner
    "corner_right",    # right mouth corner
    "blush_left",      # left cheek blush
    "blush_right",     # right cheek blush
    "iris_left",       # left iris
    "iris_right",      # right iris
    "eyelid_left",     # left eyelid
    "eyelid_right",    # right eyelid
    "eyeliner_left",   # left eyeliner
    "eyeliner_right",  # right eyeliner
    "brow_left",       # left brow
    "brow_right",      # right brow
    "hair_left",       # front hair, left side (in front of face)
    "hair_right",      # front hair, right side (in front of face)
    "sleeve_left",     # left sleeve (in front of torso)
    "sleeve_right",    # right sleeve (in front of torso)
    "ornament",        # hair ornament / accessory (topmost)
)
