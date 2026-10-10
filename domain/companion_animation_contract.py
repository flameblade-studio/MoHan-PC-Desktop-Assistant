from __future__ import annotations

lazy import math
lazy from itertools import product

lazy from PySide6.QtCore import QRect

lazy from domain.character_runtime import character_rig_manifest
lazy from domain.character_source import active_expression_catalog
lazy from domain.lip_sync import VISEME_CLOSE_TRANSITION_SECONDS

_RIG_MANIFEST = character_rig_manifest()
_EXPRESSION_CATALOG = active_expression_catalog()
if _RIG_MANIFEST.character_id != _EXPRESSION_CATALOG.character_id:
    raise ValueError("Bundled expression catalog targets a different character.")

NEUTRAL_VISEME_ASSET_STEMS = _EXPRESSION_CATALOG.neutral_viseme_asset_stems
SPEAKING_BLINK_PREFIXES = _EXPRESSION_CATALOG.speaking_blink_prefixes
PHYSICS_POSE_SUFFIXES = _RIG_MANIFEST.physics.pose_suffixes
PHYSICS_SPEECH_FRAME_PREFIXES = _RIG_MANIFEST.physics.speech_frame_prefixes
EXPRESSION_POSES = _EXPRESSION_CATALOG.state_to_pose
NEW_EXPRESSION_ASSETS = _EXPRESSION_CATALOG.new_expression_assets
EYES_CLOSED_EXPRESSIONS = _EXPRESSION_CATALOG.eyes_closed_expressions
GESTURE_SPEECH_EXPRESSIONS = _EXPRESSION_CATALOG.gesture_speech_expressions
EXPRESSION_SPEECH_EXPRESSIONS = frozenset(EXPRESSION_POSES)
# Appearance-pack silhouette rendered under each half-body pose, and the four
# gesture silhouettes whose body differs from the neutral pose: the official
# pack ships garment/hair/headwear layers cut on those gesture portraits, so
# the runtime must both draw the gesture portrait and dress it with its own
# layers.  Speech (``_speech_*``) and blink (``_speech_blink``) frames of a
# gesture inherit its silhouette.
POSE_OUTFIT_SILHOUETTES = _RIG_MANIFEST.pose_silhouettes
GESTURE_OUTFIT_SILHOUETTES = _RIG_MANIFEST.gesture_silhouettes
SPEECH_FRAME_MARKER = "_speech_"


def gesture_portrait_expression(expression: str) -> str | None:
    """The gesture portrait an expression (or one of its speech/blink frames) is drawn on."""
    base = str(expression).split(SPEECH_FRAME_MARKER, 1)[0]
    return base if base in GESTURE_OUTFIT_SILHOUETTES else None


def outfit_silhouette(expression: str, pose: str) -> str:
    """Silhouette whose appearance layers dress ``expression`` shown in ``pose``."""
    gesture = gesture_portrait_expression(expression)
    if gesture is not None:
        return GESTURE_OUTFIT_SILHOUETTES[gesture]
    return POSE_OUTFIT_SILHOUETTES.get(str(pose), POSE_OUTFIT_SILHOUETTES["front"])


EXPRESSION_SPEECH_FRAMES = frozendict({
    expression: frozendict({
        frame: f"{expression}_speech_{frame}"
        for frame in _EXPRESSION_CATALOG.speech_frame_suffixes
    })
    for expression in EXPRESSION_SPEECH_EXPRESSIONS
})
GESTURE_SPEECH_FRAMES = frozendict({
    expression: EXPRESSION_SPEECH_FRAMES[expression]
    for expression in GESTURE_SPEECH_EXPRESSIONS
})
EXPRESSION_DERIVED_VISEME_FRAMES = frozendict({
    expression: frozendict({
        viseme: f"{expression}_speech_{suffix}"
        for viseme, suffix in _EXPRESSION_CATALOG.derived_viseme_suffixes.items()
    })
    for expression in EXPRESSION_SPEECH_EXPRESSIONS
})
HALF_BLINK_NEUTRAL_FRAME_PREFIXES = tuple(
    prefix for prefix in PHYSICS_SPEECH_FRAME_PREFIXES
    if not prefix.startswith("blink")
)
EXPRESSION_VISEME_FRAMES = frozendict({
    expression: frozendict({
        "A": EXPRESSION_SPEECH_FRAMES[expression]["open"],
        "I": EXPRESSION_DERIVED_VISEME_FRAMES[expression]["I"],
        "U": EXPRESSION_DERIVED_VISEME_FRAMES[expression]["U"],
        "E": EXPRESSION_SPEECH_FRAMES[expression]["mid"],
        "O": EXPRESSION_SPEECH_FRAMES[expression]["round"],
    })
    for expression in EXPRESSION_SPEECH_EXPRESSIONS
})
EXPRESSION_SPEECH_ASSETS = tuple(
    asset for frames in EXPRESSION_SPEECH_FRAMES.values() for asset in frames.values()
)
EXPRESSION_BLINK_FRAMES = _EXPRESSION_CATALOG.blink_frames
EXPRESSION_BLINK_ASSETS = tuple(EXPRESSION_BLINK_FRAMES.values())
EXPRESSION_HALF_BLINK_FRAMES = _EXPRESSION_CATALOG.half_blink_frames


def _half_blink_frame_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for prefix, (suffix, _pose) in product(
        HALF_BLINK_NEUTRAL_FRAME_PREFIXES, PHYSICS_POSE_SUFFIXES
    ):
        if f"idle{suffix}" in EXPRESSION_HALF_BLINK_FRAMES:
            sources[f"{prefix}{suffix}"] = EXPRESSION_HALF_BLINK_FRAMES[f"idle{suffix}"]
    for expression, source in EXPRESSION_HALF_BLINK_FRAMES.items():
        if expression not in EXPRESSION_SPEECH_FRAMES:
            continue
        for frame in (
            expression,
            *EXPRESSION_SPEECH_FRAMES[expression].values(),
            *EXPRESSION_DERIVED_VISEME_FRAMES[expression].values(),
        ):
            sources[frame] = source
    return sources


EXPRESSION_HALF_BLINK_FRAME_SOURCES = frozendict(_half_blink_frame_sources())
EXPRESSION_HALF_BLINK_ASSETS = tuple(EXPRESSION_HALF_BLINK_FRAMES.values())
EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES = frozendict({
    expression: source.removesuffix("_half") + "_closed"
    for expression, source in EXPRESSION_HALF_BLINK_FRAME_SOURCES.items()
})
EXPRESSION_NATIVE_CLOSED_BLINK_ASSETS = tuple(dict.fromkeys(
    EXPRESSION_NATIVE_CLOSED_BLINK_FRAME_SOURCES.values(),
))
BLUSH_PRESERVING_BLINK_EXPRESSIONS = (
    _EXPRESSION_CATALOG.blush_preserving_blink_expressions
)
EXPRESSION_IMAGE_ASSETS = (
    *_EXPRESSION_CATALOG.base_image_assets, *NEW_EXPRESSION_ASSETS,
    *EXPRESSION_SPEECH_ASSETS, *EXPRESSION_BLINK_ASSETS,
    *EXPRESSION_HALF_BLINK_ASSETS, *EXPRESSION_NATIVE_CLOSED_BLINK_ASSETS,
    *_EXPRESSION_CATALOG.legacy_viseme_assets,
)
GESTURE_SPEECH_ASSETS = tuple(
    asset
    for frames in GESTURE_SPEECH_FRAMES.values()
    for asset in frames.values()
)

EXPRESSION_SPEECH_MOUTH_RECTS = frozendict({
    expression: QRect(*_EXPRESSION_CATALOG.mouth_rect_by_pose[pose])
    for expression, pose in EXPRESSION_POSES.items()
} | {
    expression: QRect(*rect)
    for expression, rect in _EXPRESSION_CATALOG.mouth_rect_overrides.items()
})
GESTURE_SPEECH_MOUTH_RECTS = frozendict({
    expression: EXPRESSION_SPEECH_MOUTH_RECTS[expression]
    for expression in GESTURE_SPEECH_EXPRESSIONS
})
CHEEK_SPEECH_CLOSED_EXPRESSION = (
    _EXPRESSION_CATALOG.closed_speech_expressions["cheek"]
)
HAPPY_SPEECH_CLOSED_EXPRESSION = (
    _EXPRESSION_CATALOG.closed_speech_expressions["happy"]
)
EXPRESSION_FACE_OFFSETS = _EXPRESSION_CATALOG.face_offsets
EXPRESSION_EYE_OFFSETS = _EXPRESSION_CATALOG.eye_offsets
EXPRESSION_MOUTH_OFFSETS = _EXPRESSION_CATALOG.mouth_offsets
CHARACTER_CANVAS_WIDTH = _RIG_MANIFEST.viewport.canvas_width
CHARACTER_IMAGE_SIZE = _RIG_MANIFEST.viewport.image_size
CHARACTER_BASE_Y = _RIG_MANIFEST.viewport.base_y
CHARACTER_SCALE_MIN = _RIG_MANIFEST.viewport.scale_min
CHARACTER_SCALE_MAX = _RIG_MANIFEST.viewport.scale_max
CHARACTER_SCALE_DEFAULT = _RIG_MANIFEST.viewport.scale_default
MOUTH_CLOSE_DEADLINE_MS = max(
    110, math.ceil(VISEME_CLOSE_TRANSITION_SECONDS * 1000) + 32,
)
MOTION_FRAME_INTERVAL_MS = 16
SPEECH_MOTION_RELEASE_LIMIT = 12
# Attention (gaze/blink) and physics (breath/sleeve) timers run on their own
# cadence so pointer tracking and fabric motion share the 60 Hz
# motion clock.  These are named so a future cadence change stays in one place.
ATTENTION_FRAME_INTERVAL_MS = 40
PHYSICS_FRAME_INTERVAL_MS = 33
IDLE_FRAME_INTERVAL_MS = 90
