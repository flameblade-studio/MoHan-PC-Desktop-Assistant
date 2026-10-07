"""Strict loader for character-owned expression-state data."""

from __future__ import annotations

lazy from functools import lru_cache
lazy from pathlib import Path

lazy from domain.character_data_types import (
    DEFAULT_EXPRESSION_CATALOG_PATH,
    EXPRESSION_SCHEMA,
    MAX_CHANNEL_VALUE,
    PAIR_LENGTH,
    SCHEMA_VERSION,
    BrowGuardSpec,
    ExpressionRuleSpec,
    ExpressionStateCatalog,
    FacePoseAssetSpec,
    SourceBoundExasperatedSpec,
    _array,
    _int_pair,
    _integer,
    _number,
    _object,
    _read_payload,
    _rect,
    _text,
    _text_mapping,
    _unique_texts,
)


def _rule(value: object, *, name: str) -> ExpressionRuleSpec:
    payload = _object(
        value,
        name=name,
        keys=frozenset({"priority", "minimum_ms", "maximum_ms", "cooldown_ms"}),
    )
    result = ExpressionRuleSpec(
        _integer(payload["priority"], name=f"{name}.priority"),
        _integer(payload["minimum_ms"], name=f"{name}.minimum_ms", minimum=0),
        _integer(payload["maximum_ms"], name=f"{name}.maximum_ms", minimum=0),
        _integer(payload["cooldown_ms"], name=f"{name}.cooldown_ms", minimum=0),
    )
    if result.minimum_ms > result.maximum_ms:
        raise ValueError(f"{name} minimum_ms cannot exceed maximum_ms.")
    return result


def _rect_mapping(value: object, *, name: str) -> frozendict[str, tuple[int, int, int, int]]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{name} must be a non-empty object.")
    return frozendict(
        {
            _text(key, name=f"{name} key"): _rect(item, name=f"{name}.{key}")
            for key, item in value.items()
        }
    )


def _offset_mapping(value: object, *, name: str) -> frozendict[str, tuple[int, int]]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{name} must be a non-empty object.")
    return frozendict(
        {
            _text(key, name=f"{name} key"): _int_pair(item, name=f"{name}.{key}")
            for key, item in value.items()
        }
    )


def _face_pose_assets(value: object) -> frozendict[str, FacePoseAssetSpec]:
    if not isinstance(value, dict) or not value:
        raise ValueError("face_pose_assets must be a non-empty object.")
    expected = frozenset(
        {
            "base",
            "blink",
            "open_mouth",
            "viseme_i",
            "viseme_u",
            "viseme_o",
            "face",
            "eyes",
            "mouth_rect",
            "eye_rects",
        }
    )
    result: dict[str, FacePoseAssetSpec] = {}
    for pose, raw_spec in value.items():
        name = f"face_pose_assets.{pose}"
        spec = _object(raw_spec, name=name, keys=expected)
        eye_rects = tuple(
            _rect(item, name=f"{name}.eye_rects[{index}]")
            for index, item in enumerate(
                _array(spec["eye_rects"], name=f"{name}.eye_rects")
            )
        )
        if len(eye_rects) != PAIR_LENGTH:
            raise ValueError(f"{name}.eye_rects must contain two eye regions.")
        result[_text(pose, name="face pose id")] = FacePoseAssetSpec(
            _text(spec["base"], name=f"{name}.base"),
            _text(spec["blink"], name=f"{name}.blink"),
            _text(spec["open_mouth"], name=f"{name}.open_mouth"),
            _text(spec["viseme_i"], name=f"{name}.viseme_i"),
            _text(spec["viseme_u"], name=f"{name}.viseme_u"),
            _text(spec["viseme_o"], name=f"{name}.viseme_o"),
            _text(spec["face"], name=f"{name}.face"),
            _text(spec["eyes"], name=f"{name}.eyes"),
            _rect(spec["mouth_rect"], name=f"{name}.mouth_rect"),
            eye_rects,
        )
    return frozendict(result)


def load_expression_catalog(  # ruff: ignore[too-many-branches, too-many-locals, too-many-statements]
    path: str | Path,
) -> ExpressionStateCatalog:
    """Read and validate one expression catalog; invalid data fails closed."""

    payload = _object(
        _read_payload(Path(path)),
        name="expression catalog",
        keys=frozenset(
            {
                "schema",
                "schema_version",
                "character_id",
                "state_to_pose",
                "emotion_to_expression",
                "new_expression_assets",
                "eyes_closed_expressions",
                "gesture_speech_expressions",
                "neutral_viseme_asset_stems",
                "speaking_blink_prefixes",
                "speech_frame_suffixes",
                "derived_viseme_suffixes",
                "blink_frames",
                "half_blink_frames",
                "blush_preserving_blink_expressions",
                "base_image_assets",
                "legacy_viseme_assets",
                "face_pose_assets",
                "mouth_rectangles",
                "closed_speech_expressions",
                "offsets",
                "blink_brow_guard",
                "source_bound_exasperated",
                "rules",
                "base_expressions",
                "ai_wait_expressions",
                "ai_wait_current_states",
            }
        ),
    )
    schema = _text(payload["schema"], name="schema")
    schema_version = _integer(
        payload["schema_version"],
        name="schema_version",
        minimum=1,
    )
    if schema != EXPRESSION_SCHEMA or schema_version != SCHEMA_VERSION:
        raise ValueError("Expression catalog schema is unsupported.")
    state_to_pose = _text_mapping(payload["state_to_pose"], name="state_to_pose")
    emotion_to_expression = _text_mapping(
        payload["emotion_to_expression"],
        name="emotion_to_expression",
    )
    state_names = frozenset(state_to_pose)
    base_expressions = frozenset(
        _unique_texts(payload["base_expressions"], name="base_expressions")
    )
    if not set(emotion_to_expression.values()) <= state_names | base_expressions:
        raise ValueError("Emotion mappings must target declared expression states.")
    prefix_pairs: list[tuple[str, str]] = []
    for index, raw_item in enumerate(
        _array(payload["speaking_blink_prefixes"], name="speaking_blink_prefixes")
    ):
        pair = _array(raw_item, name=f"speaking_blink_prefixes[{index}]")
        if len(pair) != PAIR_LENGTH:
            raise ValueError("Each speaking blink prefix requires two text values.")
        prefix_pairs.append(
            (
                _text(pair[0], name="speaking blink source"),
                _text(pair[1], name="speaking blink target"),
            )
        )
    if len(prefix_pairs) != len(set(prefix_pairs)):
        raise ValueError("speaking_blink_prefixes must be unique.")
    mouth_rectangles = _object(
        payload["mouth_rectangles"],
        name="mouth_rectangles",
        keys=frozenset({"by_pose", "overrides"}),
    )
    offsets = _object(
        payload["offsets"],
        name="offsets",
        keys=frozenset({"face", "eye", "mouth"}),
    )
    rules = _object(
        payload["rules"],
        name="rules",
        keys=frozenset({"default", "states"}),
    )
    state_rule_payload = rules["states"]
    if not isinstance(state_rule_payload, dict) or not state_rule_payload:
        raise ValueError("rules.states must be a non-empty object.")
    expression_rules = frozendict(
        {
            _text(state, name="rules state"): _rule(
                rule,
                name=f"rules.states.{state}",
            )
            for state, rule in state_rule_payload.items()
        }
    )
    if not set(expression_rules) <= state_names:
        raise ValueError("Expression rules must target declared states.")
    new_expression_assets = _unique_texts(
        payload["new_expression_assets"],
        name="new_expression_assets",
    )
    eyes_closed_expressions = frozenset(
        _unique_texts(
            payload["eyes_closed_expressions"],
            name="eyes_closed_expressions",
        )
    )
    gesture_speech_expressions = frozenset(
        _unique_texts(
            payload["gesture_speech_expressions"],
            name="gesture_speech_expressions",
        )
    )
    blush_preserving_expressions = frozenset(
        _unique_texts(
            payload["blush_preserving_blink_expressions"],
            name="blush_preserving_blink_expressions",
        )
    )
    ai_wait_expressions = frozenset(
        _unique_texts(payload["ai_wait_expressions"], name="ai_wait_expressions")
    )
    ai_wait_current_states = frozenset(
        _unique_texts(
            payload["ai_wait_current_states"],
            name="ai_wait_current_states",
        )
    )
    referenced_states = (
        set(new_expression_assets)
        | eyes_closed_expressions
        | gesture_speech_expressions
        | blush_preserving_expressions
        | ai_wait_expressions
    )
    if not referenced_states <= state_names:
        raise ValueError("Expression subsets must target declared states.")
    if not ai_wait_current_states <= state_names | base_expressions:
        raise ValueError("AI wait current states must target declared states.")
    blink_frames = _text_mapping(payload["blink_frames"], name="blink_frames")
    half_blink_frames = _text_mapping(
        payload["half_blink_frames"],
        name="half_blink_frames",
    )
    face_offsets = _offset_mapping(offsets["face"], name="offsets.face")
    eye_offsets = _offset_mapping(offsets["eye"], name="offsets.eye")
    mouth_offsets = _offset_mapping(offsets["mouth"], name="offsets.mouth")
    if set(face_offsets) != state_names or set(eye_offsets) != state_names or set(mouth_offsets) != state_names:
        raise ValueError("Every expression state requires face, eye, and mouth offsets.")
    face_pose_assets = _face_pose_assets(payload["face_pose_assets"])
    mouth_rect_by_pose = _rect_mapping(
        mouth_rectangles["by_pose"],
        name="mouth_rectangles.by_pose",
    )
    mouth_rect_overrides = _rect_mapping(
        mouth_rectangles["overrides"],
        name="mouth_rectangles.overrides",
    )
    if set(mouth_rect_by_pose) != set(face_pose_assets):
        raise ValueError("Mouth rectangles must cover every declared face pose.")
    if not set(state_to_pose.values()) <= set(face_pose_assets):
        raise ValueError("Expression states must target a declared face pose.")
    if not set(mouth_rect_overrides) <= state_names:
        raise ValueError("Mouth rectangle overrides must target declared states.")
    if not set(blink_frames) <= state_names:
        raise ValueError("Blink frames must target declared states.")
    brow_guard_payload = _object(
        payload["blink_brow_guard"],
        name="blink_brow_guard",
        keys=frozenset(
            {
                "regions",
                "dark_limit",
                "eureka_dark_limit",
                "eureka_guard_width",
                "native_guard_width",
                "guard_sigma",
                "expressions",
            }
        ),
    )
    brow_regions = tuple(
        _rect(region, name=f"blink_brow_guard.regions[{index}]")
        for index, region in enumerate(
            _array(brow_guard_payload["regions"], name="blink_brow_guard.regions")
        )
    )
    brow_expressions = frozenset(
        _unique_texts(
            brow_guard_payload["expressions"],
            name="blink_brow_guard.expressions",
        )
    )
    dark_limit = _integer(
        brow_guard_payload["dark_limit"],
        name="blink_brow_guard.dark_limit",
        minimum=0,
    )
    eureka_dark_limit = _integer(
        brow_guard_payload["eureka_dark_limit"],
        name="blink_brow_guard.eureka_dark_limit",
        minimum=0,
    )
    if (
        not brow_regions
        or not brow_expressions <= state_names
        or dark_limit > MAX_CHANNEL_VALUE
        or eureka_dark_limit > MAX_CHANNEL_VALUE
    ):
        raise ValueError("Blink brow guard declarations are incomplete or out of range.")
    brow_guard = BrowGuardSpec(
        brow_regions,
        dark_limit,
        eureka_dark_limit,
        _integer(
            brow_guard_payload["eureka_guard_width"],
            name="blink_brow_guard.eureka_guard_width",
            minimum=1,
        ),
        _integer(
            brow_guard_payload["native_guard_width"],
            name="blink_brow_guard.native_guard_width",
            minimum=1,
        ),
        _number(
            brow_guard_payload["guard_sigma"],
            name="blink_brow_guard.guard_sigma",
        ),
        brow_expressions,
    )
    if brow_guard.guard_sigma <= 0.0:
        raise ValueError("blink_brow_guard.guard_sigma must be positive.")
    source_bound_payload = _object(
        payload["source_bound_exasperated"],
        name="source_bound_exasperated",
        keys=frozenset({"mouth_bounds", "mouth_variants"}),
    )
    source_bound_exasperated = SourceBoundExasperatedSpec(
        _rect(
            source_bound_payload["mouth_bounds"],
            name="source_bound_exasperated.mouth_bounds",
        ),
        _text_mapping(
            source_bound_payload["mouth_variants"],
            name="source_bound_exasperated.mouth_variants",
        ),
    )
    return ExpressionStateCatalog(
        schema,
        schema_version,
        _text(payload["character_id"], name="character_id"),
        state_to_pose,
        emotion_to_expression,
        new_expression_assets,
        eyes_closed_expressions,
        gesture_speech_expressions,
        _text_mapping(
            payload["neutral_viseme_asset_stems"],
            name="neutral_viseme_asset_stems",
        ),
        tuple(prefix_pairs),
        _unique_texts(payload["speech_frame_suffixes"], name="speech_frame_suffixes"),
        _text_mapping(
            payload["derived_viseme_suffixes"],
            name="derived_viseme_suffixes",
        ),
        blink_frames,
        half_blink_frames,
        blush_preserving_expressions,
        _unique_texts(payload["base_image_assets"], name="base_image_assets"),
        _unique_texts(
            payload["legacy_viseme_assets"],
            name="legacy_viseme_assets",
        ),
        face_pose_assets,
        mouth_rect_by_pose,
        mouth_rect_overrides,
        _text_mapping(
            payload["closed_speech_expressions"],
            name="closed_speech_expressions",
        ),
        face_offsets,
        eye_offsets,
        mouth_offsets,
        brow_guard,
        source_bound_exasperated,
        _rule(rules["default"], name="rules.default"),
        expression_rules,
        base_expressions,
        ai_wait_expressions,
        ai_wait_current_states,
    )


@lru_cache(maxsize=1)
def default_expression_catalog() -> ExpressionStateCatalog:
    """Return the validated bundled catalog; disk is read at most once per process."""

    return load_expression_catalog(DEFAULT_EXPRESSION_CATALOG_PATH)
