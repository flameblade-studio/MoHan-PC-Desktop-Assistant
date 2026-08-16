from __future__ import annotations

lazy import math

lazy from PySide6.QtCore import QRect

lazy from domain.lip_sync import VISEME_CLOSE_TRANSITION_SECONDS

NEUTRAL_VISEME_ASSET_STEMS = frozendict({
    "A": "mouth_wide",
    "I": "mouth_i",
    "U": "mouth_round",
    "E": "mouth_mid",
    "O": "mouth_o",
})
SPEAKING_BLINK_PREFIXES = (
    ("mouth_mid", "blink_mid"),
    ("mouth_wide", "blink_wide"),
    ("mouth_round", "blink_round"),
    ("mouth_i", "blink_i"),
    ("mouth_o", "blink_o"),
    ("speaking", "blink_open"),
)
PHYSICS_POSE_SUFFIXES = (
    ("", "cheek"),
    ("_lean", "lean"),
    ("_front", "front"),
)
PHYSICS_SPEECH_FRAME_PREFIXES = (
    "idle", "speaking", "blink", "mouth_mid", "mouth_wide",
    "mouth_round", "mouth_i", "mouth_o", "blink_mid", "blink_open",
    "blink_wide", "blink_round", "blink_i", "blink_o",
)
EXPRESSION_POSES = frozendict({
    "glance": "cheek", "caught": "cheek", "happy": "cheek",
    "worried": "cheek", "reminder": "cheek", "thinking_front": "front",
    "gentle_smile_front": "front", "worried_front": "front",
    "shy_front": "front", "mock_scold": "front",
    "surprised_front": "front", "relieved_front": "front",
    "tired_front": "front", "proud_front": "front",
    "shy_cute_front": "front", "mock_hit_front": "front",
    "attentive_front": "front", "determined_front": "front",
    "restrained_amused_front": "front", "exasperated_front": "front",
    "eureka_front": "front", "protective_front": "front",
})
NEW_EXPRESSION_ASSETS = (
    "shy_cute_front", "mock_hit_front", "attentive_front",
    "determined_front", "restrained_amused_front", "exasperated_front",
    "eureka_front", "protective_front",
)
EYES_CLOSED_EXPRESSIONS = frozenset({"exasperated_front"})
GESTURE_SPEECH_EXPRESSIONS = frozenset(
    {
        "mock_scold",
        "mock_hit_front",
        "exasperated_front",
        "eureka_front",
    }
)
EXPRESSION_SPEECH_EXPRESSIONS = frozenset(EXPRESSION_POSES)
EXPRESSION_SPEECH_FRAMES = frozendict({
    expression: frozendict({
        frame: f"{expression}_speech_{frame}"
        for frame in ("mid", "open", "round")
    })
    for expression in EXPRESSION_SPEECH_EXPRESSIONS
})
GESTURE_SPEECH_FRAMES = frozendict({
    expression: EXPRESSION_SPEECH_FRAMES[expression]
    for expression in GESTURE_SPEECH_EXPRESSIONS
})
EXPRESSION_DERIVED_VISEME_FRAMES = frozendict({
    expression: frozendict({
        "I": f"{expression}_speech_i", "U": f"{expression}_speech_u",
    })
    for expression in EXPRESSION_SPEECH_EXPRESSIONS
})
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
EXPRESSION_BLINK_FRAMES = frozendict({
    "thinking_front": "thinking_front_speech_blink",
    "glance": "glance_speech_blink", "happy": "happy_speech_blink",
    "worried": "worried_speech_blink", "reminder": "reminder_speech_blink",
})
EXPRESSION_BLINK_ASSETS = tuple(EXPRESSION_BLINK_FRAMES.values())
BLUSH_PRESERVING_BLINK_EXPRESSIONS = frozenset({"shy_front", "shy_cute_front"})
EXPRESSION_IMAGE_ASSETS = (
    "idle", "idle_lean", "idle_front", "blink", "blink_lean", "blink_front",
    "glance", "caught", "speaking", "speaking_lean", "speaking_front",
    "happy", "worried", "reminder", "thinking_front", "gentle_smile_front",
    "worried_front", "shy_front", "mock_scold", "surprised_front",
    "relieved_front", "tired_front", "proud_front", *NEW_EXPRESSION_ASSETS,
    *EXPRESSION_SPEECH_ASSETS, *EXPRESSION_BLINK_ASSETS, "viseme_mid_front",
    "viseme_wide_front", "viseme_round", "viseme_round_lean",
    "viseme_round_front", "viseme_i", "viseme_i_lean", "viseme_i_front",
    "viseme_o", "viseme_o_lean", "viseme_o_front",
)
GESTURE_SPEECH_ASSETS = tuple(
    asset
    for frames in GESTURE_SPEECH_FRAMES.values()
    for asset in frames.values()
)
EXPRESSION_SPEECH_MOUTH_RECTS = frozendict({
    expression: (
        QRect(170, 194, 60, 42) if pose == "cheek"
        else QRect(158, 194, 62, 42) if pose == "lean"
        else QRect(202, 195, 62, 43)
    )
    for expression, pose in EXPRESSION_POSES.items()
} | {
    "mock_scold": QRect(202, 196, 53, 44),
    "mock_hit_front": QRect(201, 190, 56, 50),
    "exasperated_front": QRect(199, 201, 58, 47),
    "eureka_front": QRect(197, 190, 58, 48),
})
GESTURE_SPEECH_MOUTH_RECTS = frozendict({
    expression: EXPRESSION_SPEECH_MOUTH_RECTS[expression]
    for expression in GESTURE_SPEECH_EXPRESSIONS
})
CHEEK_SPEECH_CLOSED_EXPRESSION = "idle_speech_neutral"
HAPPY_SPEECH_CLOSED_EXPRESSION = "happy_speech_neutral"
EXPRESSION_FACE_OFFSETS = frozendict({
    "glance": (0, 0), "caught": (0, 1), "happy": (0, 0),
    "worried": (0, 0), "reminder": (0, 0), "thinking_front": (3, 0),
    "gentle_smile_front": (0, 0), "worried_front": (0, 0),
    "shy_front": (1, 0), "mock_scold": (5, 3), "surprised_front": (0, 0),
    "relieved_front": (0, 0), "tired_front": (0, 0), "proud_front": (0, -1),
    "shy_cute_front": (0, 0), "mock_hit_front": (1, -1),
    "attentive_front": (1, 3), "determined_front": (0, 0),
    "restrained_amused_front": (0, 0), "exasperated_front": (-1, 6),
    "eureka_front": (-1, -1), "protective_front": (0, -4),
})
EXPRESSION_EYE_OFFSETS = frozendict({
    **EXPRESSION_FACE_OFFSETS, "caught": (0, 3), "reminder": (0, 1),
    "thinking_front": (4, -3), "surprised_front": (0, -1),
    "attentive_front": (1, 2), "determined_front": (0, 1),
    "restrained_amused_front": (0, 1), "protective_front": (0, -3),
})
EXPRESSION_MOUTH_OFFSETS = frozendict({
    **EXPRESSION_FACE_OFFSETS, "caught": (0, 0), "mock_scold": (4, 4),
    "proud_front": (0, 0), "mock_hit_front": (1, -2),
    "eureka_front": (0, 0), "protective_front": (0, -3),
})
CHARACTER_CANVAS_WIDTH = 470
CHARACTER_IMAGE_SIZE = 465
CHARACTER_BASE_Y = 215
CHARACTER_SCALE_MIN = 75
CHARACTER_SCALE_MAX = 180
CHARACTER_SCALE_DEFAULT = 100
MOUTH_CLOSE_DEADLINE_MS = max(
    110, math.ceil(VISEME_CLOSE_TRANSITION_SECONDS * 1000) + 32,
)
MOTION_FRAME_INTERVAL_MS = 16
SPEECH_MOTION_RELEASE_LIMIT = 12
