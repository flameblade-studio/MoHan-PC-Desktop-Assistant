"""Character-neutral strict loader for rig data."""

from __future__ import annotations

lazy from itertools import product
lazy from pathlib import Path

lazy from domain.character_pack.character_data_models import (
    FULL_BODY_LAYER_COUNT,
    FULL_VIEW_COUNT,
    HAND_LANDMARK_COUNT,
    MAX_PITCH_DEGREES,
    MAX_YAW_DEGREES,
    MIN_PITCH_DEGREES,
    RIG_SCHEMA,
    SCHEMA_VERSION,
    ArmSpec,
    BodyMeasurementsSpec,
    BodyProportionsSpec,
    CharacterDataError,
    CharacterRigManifest,
    FaceCalibrationSpec,
    FullBodyCalibrationSpec,
    PhysicsSpec,
    PoseSpec,
    ViewportSpec,
    ViewRingSpec,
)
lazy from domain.character_pack.character_data_validation import (
    _array,
    _boolean,
    _canvas,
    _float_pair,
    _float_triple,
    _int_pair,
    _integer,
    _number,
    _object,
    _read_payload,
    _text,
    _text_mapping,
    _unique_texts,
)


def _arm(value: object, *, name: str) -> ArmSpec:
    payload = _object(
        value,
        name=name,
        keys=frozenset(
            {
                "shoulder",
                "upper_arm_length",
                "forearm_length",
                "hand_length",
                "shoulder_degrees",
                "elbow_degrees",
                "wrist_degrees",
            }
        ),
    )
    result = ArmSpec(
        _float_pair(payload["shoulder"], name=f"{name}.shoulder"),
        _number(payload["upper_arm_length"], name=f"{name}.upper_arm_length"),
        _number(payload["forearm_length"], name=f"{name}.forearm_length"),
        _number(payload["hand_length"], name=f"{name}.hand_length"),
        _number(payload["shoulder_degrees"], name=f"{name}.shoulder_degrees"),
        _number(payload["elbow_degrees"], name=f"{name}.elbow_degrees"),
        _number(payload["wrist_degrees"], name=f"{name}.wrist_degrees"),
    )
    if (
        not 0.0 <= result.shoulder[0] <= 1.0
        or not 0.0 <= result.shoulder[1] <= 1.0
        or result.upper_arm_length <= 0.0
        or result.forearm_length <= 0.0
        or result.hand_length <= 0.0
    ):
        raise CharacterDataError(f"{name} must use normalized anchors and positive lengths.")
    return result


def _pose(value: object, *, name: str, yaws: frozenset[int]) -> PoseSpec:
    payload = _object(
        value,
        name=name,
        keys=frozenset(
            {
                "id",
                "yaw_degrees",
                "legacy_face_pose",
                "silhouette",
                "left_arm",
                "right_arm",
                "required_corrections",
                "speech_safe",
                "tags",
            }
        ),
    )
    yaw = _integer(payload["yaw_degrees"], name=f"{name}.yaw_degrees")
    if yaw not in yaws:
        raise CharacterDataError(f"{name}.yaw_degrees must use the declared view ring.")
    return PoseSpec(
        _text(payload["id"], name=f"{name}.id"),
        yaw,
        _text(payload["legacy_face_pose"], name=f"{name}.legacy_face_pose"),
        _text(payload["silhouette"], name=f"{name}.silhouette"),
        _arm(payload["left_arm"], name=f"{name}.left_arm"),
        _arm(payload["right_arm"], name=f"{name}.right_arm"),
        frozenset(
            _unique_texts(
                payload["required_corrections"],
                name=f"{name}.required_corrections",
            )
        ),
        _boolean(payload["speech_safe"], name=f"{name}.speech_safe"),
        frozenset(_unique_texts(payload["tags"], name=f"{name}.tags")),
    )


def _side_anchors(
    value: object,
    *,
    name: str,
) -> frozendict[str, frozendict[str, tuple[int, int]]]:
    if not isinstance(value, dict) or not value:
        raise CharacterDataError(f"{name} must be a non-empty object.")
    return frozendict(
        {
            _text(pose, name=f"{name} pose"): _side_anchor_pair(raw, name=f"{name}.{pose}")
            for pose, raw in value.items()
        }
    )


def _side_anchor_pair(value: object, *, name: str) -> frozendict[str, tuple[int, int]]:
    payload = _object(value, name=name, keys=frozenset({"left", "right"}))
    return frozendict(
        {side: _int_pair(payload[side], name=f"{name}.{side}") for side in ("left", "right")}
    )


def _physics(value: object) -> PhysicsSpec:
    payload = _object(
        value,
        name="physics",
        keys=frozenset(
            {
                "pose_suffixes",
                "speech_frame_prefixes",
                "anchors",
                "pose_switch_probability",
                "breath_lift_scale",
                "max_sleeve_lift",
                "max_gesture_sway",
                "gesture_energy_threshold",
            }
        ),
    )
    suffixes: list[tuple[str, str]] = []
    for index, raw_item in enumerate(
        _array(payload["pose_suffixes"], name="physics.pose_suffixes")
    ):
        item = _object(
            raw_item,
            name=f"physics.pose_suffixes[{index}]",
            keys=frozenset({"suffix", "pose"}),
        )
        suffix = item["suffix"]
        if not isinstance(suffix, str):
            raise CharacterDataError("physics pose suffix must be text.")
        suffixes.append((suffix, _text(item["pose"], name="physics pose")))
    if not suffixes or len(suffixes) != len(set(suffixes)):
        raise CharacterDataError("physics.pose_suffixes must be unique and non-empty.")
    anchors = _object(
        payload["anchors"],
        name="physics.anchors",
        keys=frozenset({"ornament", "hair", "sleeve"}),
    )
    ornament_payload = anchors["ornament"]
    if not isinstance(ornament_payload, dict) or not ornament_payload:
        raise CharacterDataError("physics.anchors.ornament must be a non-empty object.")
    probability = _number(
        payload["pose_switch_probability"],
        name="physics.pose_switch_probability",
    )
    if not 0.0 <= probability <= 1.0:
        raise CharacterDataError("physics.pose_switch_probability must be within 0..1.")
    result = PhysicsSpec(
        tuple(suffixes),
        _unique_texts(
            payload["speech_frame_prefixes"],
            name="physics.speech_frame_prefixes",
        ),
        frozendict(
            {
                _text(pose, name="ornament pose"): _int_pair(
                    anchor,
                    name=f"physics.anchors.ornament.{pose}",
                )
                for pose, anchor in ornament_payload.items()
            }
        ),
        _side_anchors(anchors["hair"], name="physics.anchors.hair"),
        _side_anchors(anchors["sleeve"], name="physics.anchors.sleeve"),
        probability,
        _number(payload["breath_lift_scale"], name="physics.breath_lift_scale"),
        _number(payload["max_sleeve_lift"], name="physics.max_sleeve_lift"),
        _number(payload["max_gesture_sway"], name="physics.max_gesture_sway"),
        _number(
            payload["gesture_energy_threshold"],
            name="physics.gesture_energy_threshold",
        ),
    )
    if (
        result.breath_lift_scale < 0.0
        or result.max_sleeve_lift < 0.0
        or result.max_gesture_sway < 0.0
        or not 0.0 <= result.gesture_energy_threshold <= 1.0
    ):
        raise CharacterDataError("Physics calibrations must use supported non-negative ranges.")
    pose_names = {pose for _suffix, pose in result.pose_suffixes}
    if (
        set(result.ornament_anchors) != pose_names
        or set(result.hair_anchors) != pose_names
        or set(result.sleeve_anchors) != pose_names
    ):
        raise CharacterDataError("Physics anchors must cover every declared physics pose.")
    return result


def _face_calibration(value: object) -> FaceCalibrationSpec:
    keys = (
        "layer_opacity_eye_lid",
        "layer_opacity_eyeliner",
        "layer_opacity_blush",
        "layer_opacity_iris",
        "mouth_stretch_ratio",
        "mouth_rounding_ratio",
        "mouth_height_ratio",
        "mouth_aperture_normalizer",
        "jaw_translation_factor",
        "brow_lift_factor",
        "brow_tension_factor",
        "corner_smile_factor",
        "corner_smile_lift_factor",
        "shyness_blush_weight",
        "shyness_gaze_weight",
        "shyness_lip_weight",
        "viseme_u_inward_lerp",
    )
    payload = _object(
        value,
        name="face_calibration",
        keys=frozenset(keys),
    )
    values = tuple(
        _number(payload[key], name=f"face_calibration.{key}")
        for key in keys
    )
    if any(value < 0.0 for value in values):
        raise CharacterDataError("face_calibration values must be non-negative.")
    if any(value > 1.0 for value in (*values[:4], *values[13:])):
        raise CharacterDataError("Face opacity, shyness, and viseme weights must be within 0..1.")
    return FaceCalibrationSpec(*values)


def _full_body_calibration(value: object) -> FullBodyCalibrationSpec:
    payload = _object(
        value,
        name="full_body_calibration",
        keys=frozenset(
            {
                "proportions",
                "root",
                "minimum_perspective",
                "left_leg_degrees",
                "right_leg_degrees",
                "heel_center_offset",
                "sole_half_width",
                "direction_vectors",
            }
        ),
    )
    proportion_keys = (
        "root_to_pelvis",
        "pelvis_to_spine",
        "spine_to_chest",
        "chest_to_neck",
        "neck_to_head",
        "hip_half_width",
        "thigh_length",
        "shin_length",
        "foot_length",
        "toe_length",
    )
    raw_proportions = _object(
        payload["proportions"],
        name="full_body_calibration.proportions",
        keys=frozenset(proportion_keys),
    )
    proportion_values = tuple(
        _number(
            raw_proportions[key],
            name=f"full_body_calibration.proportions.{key}",
        )
        for key in proportion_keys
    )
    if any(value <= 0.0 for value in proportion_values):
        raise CharacterDataError("Full-body proportions must be positive.")
    directions = payload["direction_vectors"]
    if not isinstance(directions, dict) or set(directions) != {
        "forward",
        "back",
        "left",
        "right",
    }:
        raise CharacterDataError("Full-body direction vectors must cover four directions.")
    result = FullBodyCalibrationSpec(
        BodyProportionsSpec(*proportion_values),
        _float_pair(payload["root"], name="full_body_calibration.root"),
        _number(
            payload["minimum_perspective"],
            name="full_body_calibration.minimum_perspective",
        ),
        _float_triple(
            payload["left_leg_degrees"],
            name="full_body_calibration.left_leg_degrees",
        ),
        _float_triple(
            payload["right_leg_degrees"],
            name="full_body_calibration.right_leg_degrees",
        ),
        _number(
            payload["heel_center_offset"],
            name="full_body_calibration.heel_center_offset",
        ),
        _number(
            payload["sole_half_width"],
            name="full_body_calibration.sole_half_width",
        ),
        frozendict(
            {
                direction: _float_pair(
                    vector,
                    name=f"full_body_calibration.direction_vectors.{direction}",
                )
                for direction, vector in directions.items()
            }
        ),
    )
    if (
        not 0.0 <= result.root[0] <= 1.0
        or not 0.0 <= result.root[1] <= 1.0
        or not 0.0 < result.minimum_perspective <= 1.0
        or result.heel_center_offset <= 0.0
        or result.sole_half_width <= 0.0
        or any(vector == (0.0, 0.0) for vector in result.direction_vectors.values())
    ):
        raise CharacterDataError("Full-body calibration values are outside supported ranges.")
    return result


def load_rig_manifest(  # ruff: ignore[too-many-branches, too-many-locals, too-many-statements]
    path: str | Path,
) -> CharacterRigManifest:
    """Read and validate one character rig manifest; invalid data fails closed."""

    payload = _object(
        _read_payload(Path(path)),
        name="rig manifest",
        keys=frozenset(
            {
                "schema",
                "schema_version",
                "character_id",
                "body_profile",
                "full_body",
                "half_body",
                "poses",
                "physics",
                "face_calibration",
                "full_body_calibration",
                "gesture_actions",
            }
        ),
    )
    schema = _text(payload["schema"], name="schema")
    schema_version = _integer(
        payload["schema_version"],
        name="schema_version",
        minimum=1,
    )
    if schema != RIG_SCHEMA or schema_version != SCHEMA_VERSION:
        raise CharacterDataError("Rig manifest schema is unsupported.")
    body_profile = _object(
        payload["body_profile"],
        name="body_profile",
        keys=frozenset({"id", "version", "measurements", "art_direction"}),
    )
    measurement_keys = (
        "height_cm",
        "weight_kg",
        "bust_cm",
        "underbust_cm",
        "waist_cm",
        "hips_cm",
    )
    measurements = _object(
        body_profile["measurements"],
        name="body_profile.measurements",
        keys=frozenset(measurement_keys),
    )
    full_body = _object(
        payload["full_body"],
        name="full_body",
        keys=frozenset(
            {
                "canvas",
                "view_ring",
                "layer_z_order",
                "required_layers",
                "registered_composite_layers",
                "face_authority_layers",
                "side_view_yaw_limit",
                "mouth_authority_manifest",
            }
        ),
    )
    view_ring = _object(
        full_body["view_ring"],
        name="full_body.view_ring",
        keys=frozenset(
            {
                "yaw_step_degrees",
                "pitch_degrees",
                "yaws",
                "legacy_aliases",
                "mirror_views",
            }
        ),
    )
    yaws = tuple(
        _integer(item, name="full_body.view_ring.yaws item")
        for item in _array(view_ring["yaws"], name="full_body.view_ring.yaws")
    )
    step = _integer(
        view_ring["yaw_step_degrees"],
        name="full_body.view_ring.yaw_step_degrees",
        minimum=1,
    )
    if yaws != tuple(range(-180, 180, step)):
        raise CharacterDataError("Rig view ring must declare one ordered complete 360-degree ring.")
    legacy_alias_payload = view_ring["legacy_aliases"]
    if not isinstance(legacy_alias_payload, dict) or not legacy_alias_payload:
        raise CharacterDataError("full_body.view_ring.legacy_aliases must be a non-empty object.")
    legacy_aliases = frozendict(
        {
            _text(alias, name="legacy view alias"): _integer(
                yaw,
                name=f"legacy view alias {alias}",
            )
            for alias, yaw in legacy_alias_payload.items()
        }
    )
    if not set(legacy_aliases.values()) <= set(yaws):
        raise CharacterDataError("Legacy view aliases must target declared yaws.")
    half_body = _object(
        payload["half_body"],
        name="half_body",
        keys=frozenset({"asset_canvas", "viewport"}),
    )
    viewport = _object(
        half_body["viewport"],
        name="half_body.viewport",
        keys=frozenset(
            {
                "canvas_width",
                "image_size",
                "base_y",
                "scale_min",
                "scale_max",
                "scale_default",
            }
        ),
    )
    pose_payload = _object(
        payload["poses"],
        name="poses",
        keys=frozenset(
            {
                "silhouettes",
                "gesture_silhouettes",
                "behavior_views",
                "back_depth",
                "registry",
                "legacy_pose_ids",
                "relaxed_hand",
            }
        ),
    )
    poses = tuple(
        _pose(item, name=f"poses.registry[{index}]", yaws=frozenset(yaws))
        for index, item in enumerate(
            _array(pose_payload["registry"], name="poses.registry")
        )
    )
    pose_ids = tuple(item.pose_id for item in poses)
    if not poses or len(pose_ids) != len(set(pose_ids)):
        raise CharacterDataError("poses.registry must contain unique pose identifiers.")
    relaxed_hand = _object(
        pose_payload["relaxed_hand"],
        name="poses.relaxed_hand",
        keys=frozenset({"facing", "points"}),
    )
    hand_points = tuple(
        _float_pair(item, name=f"poses.relaxed_hand.points[{index}]")
        for index, item in enumerate(
            _array(relaxed_hand["points"], name="poses.relaxed_hand.points")
        )
    )
    if len(hand_points) != HAND_LANDMARK_COUNT:
        raise CharacterDataError("poses.relaxed_hand requires exactly 21 points.")
    layer_z_order = _unique_texts(
        full_body["layer_z_order"],
        name="full_body.layer_z_order",
    )
    if len(layer_z_order) != FULL_BODY_LAYER_COUNT:
        raise CharacterDataError("full_body.layer_z_order requires exactly 25 layers.")
    required_layers = frozenset(
        _unique_texts(full_body["required_layers"], name="full_body.required_layers")
    )
    if not required_layers <= set(layer_z_order):
        raise CharacterDataError("full_body.required_layers must reference declared layers.")
    registered_composite_layers = _unique_texts(
        full_body["registered_composite_layers"],
        name="full_body.registered_composite_layers",
    )
    face_authority_layers = _unique_texts(
        full_body["face_authority_layers"],
        name="full_body.face_authority_layers",
    )
    if (
        not set(registered_composite_layers) <= set(layer_z_order)
        or not set(face_authority_layers) <= set(layer_z_order)
    ):
        raise CharacterDataError("Full-body composition lists must reference declared layers.")
    mirror_views = _text_mapping(
        view_ring["mirror_views"],
        name="full_body.view_ring.mirror_views",
    )
    pitch_degrees = tuple(
        _integer(item, name="view_ring.pitch_degrees item")
        for item in _array(
            view_ring["pitch_degrees"],
            name="view_ring.pitch_degrees",
        )
    )
    if (
        not pitch_degrees
        or len(pitch_degrees) != len(set(pitch_degrees))
        or any(
            pitch < MIN_PITCH_DEGREES or pitch > MAX_PITCH_DEGREES
            for pitch in pitch_degrees
        )
    ):
        raise CharacterDataError("view_ring.pitch_degrees must be unique values within -45..45.")
    if len(yaws) != FULL_VIEW_COUNT or pitch_degrees != (0,):
        raise CharacterDataError("Bundled full-body rig requires one 24-yaw zero-pitch ring.")
    declared_views = {
        f"yaw{yaw:+04d}-pitch{pitch:+03d}" for pitch, yaw in product(pitch_degrees, yaws)
    }
    if set(mirror_views) != declared_views or set(mirror_views.values()) != declared_views:
        raise CharacterDataError("mirror_views must cover every declared view exactly once.")
    if any(mirror_views[mirror_views[view]] != view for view in declared_views):
        raise CharacterDataError("mirror_views must be a symmetric mapping.")
    viewport_spec = ViewportSpec(
        _integer(viewport["canvas_width"], name="viewport.canvas_width", minimum=1),
        _integer(viewport["image_size"], name="viewport.image_size", minimum=1),
        _integer(viewport["base_y"], name="viewport.base_y", minimum=0),
        _integer(viewport["scale_min"], name="viewport.scale_min", minimum=1),
        _integer(viewport["scale_max"], name="viewport.scale_max", minimum=1),
        _integer(
            viewport["scale_default"],
            name="viewport.scale_default",
            minimum=1,
        ),
    )
    if not viewport_spec.scale_min <= viewport_spec.scale_default <= viewport_spec.scale_max:
        raise CharacterDataError("viewport.scale_default must stay within the declared range.")
    legacy_pose_ids = _unique_texts(
        pose_payload["legacy_pose_ids"],
        name="poses.legacy_pose_ids",
    )
    if not set(legacy_pose_ids) <= set(pose_ids):
        raise CharacterDataError("poses.legacy_pose_ids must target declared poses.")
    behavior_pose_views = _text_mapping(
        pose_payload["behavior_views"],
        name="poses.behavior_views",
    )
    if set(behavior_pose_views) != set(pose_ids):
        raise CharacterDataError("poses.behavior_views must cover every declared pose.")
    side_view_yaw_limit = _integer(
        full_body["side_view_yaw_limit"],
        name="full_body.side_view_yaw_limit",
        minimum=0,
    )
    if side_view_yaw_limit > MAX_YAW_DEGREES:
        raise CharacterDataError("full_body.side_view_yaw_limit cannot exceed 180 degrees.")
    return CharacterRigManifest(
        schema,
        schema_version,
        _text(payload["character_id"], name="character_id"),
        _text(body_profile["id"], name="body_profile.id"),
        _integer(body_profile["version"], name="body_profile.version", minimum=1),
        BodyMeasurementsSpec(
            *(
                _integer(
                    measurements[key],
                    name=f"body_profile.measurements.{key}",
                    minimum=1,
                )
                for key in measurement_keys
            )
        ),
        _text(body_profile["art_direction"], name="body_profile.art_direction"),
        _canvas(full_body["canvas"], name="full_body.canvas"),
        _canvas(half_body["asset_canvas"], name="half_body.asset_canvas"),
        viewport_spec,
        ViewRingSpec(
            step,
            pitch_degrees,
            yaws,
            legacy_aliases,
            mirror_views,
        ),
        layer_z_order,
        required_layers,
        registered_composite_layers,
        face_authority_layers,
        side_view_yaw_limit,
        _text(
            full_body["mouth_authority_manifest"],
            name="full_body.mouth_authority_manifest",
        ),
        _text_mapping(pose_payload["silhouettes"], name="poses.silhouettes"),
        _text_mapping(
            pose_payload["gesture_silhouettes"],
            name="poses.gesture_silhouettes",
        ),
        behavior_pose_views,
        frozendict(
            {
                _text(pose, name="poses.back_depth key"): _integer(
                    depth,
                    name=f"poses.back_depth.{pose}",
                    minimum=0,
                )
                for pose, depth in _object(
                    pose_payload["back_depth"],
                    name="poses.back_depth",
                    keys=frozenset(pose_ids),
                ).items()
            }
        ),
        poses,
        legacy_pose_ids,
        _text(relaxed_hand["facing"], name="poses.relaxed_hand.facing"),
        hand_points,
        _physics(payload["physics"]),
        _face_calibration(payload["face_calibration"]),
        _full_body_calibration(payload["full_body_calibration"]),
        _text_mapping(payload["gesture_actions"], name="gesture_actions"),
    )
