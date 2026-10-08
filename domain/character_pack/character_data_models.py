"""Immutable contracts returned by the strict built-in character-data loader."""

from __future__ import annotations

lazy from collections.abc import Mapping
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

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CHARACTER_ROOT = _PROJECT_ROOT / "assets" / "characters" / "mohan"
DEFAULT_RIG_MANIFEST_PATH = _DEFAULT_CHARACTER_ROOT / "rig" / "rig-manifest.json"
DEFAULT_EXPRESSION_CATALOG_PATH = (
    _DEFAULT_CHARACTER_ROOT / "expressions" / "state-catalog.json"
)


class CharacterDataError(ValueError):
    """Built-in character data violates its versioned schema."""


def canonical_character_locale(language: str) -> str:
    normalized = str(language or "").strip()
    if normalized in {"en", "en-US", "en-GB"}:
        return "en"
    if normalized in {"zh-CN", "zh-SG", "zh-Hans"}:
        return "zh-CN"
    if normalized in {"ja", "ja-JP"}:
        return "ja-JP"
    return "zh-TW"


@dataclass(frozen=True, slots=True)
class PersonaIdentity:
    display_name: str
    assistant_alias: str
    default_user_title: str
    default_wake_word: str


@dataclass(frozen=True, slots=True)
class AppearanceItemSelection:
    item_id: str
    variant_id: str


@dataclass(frozen=True, slots=True)
class CharacterAppearanceDefaults:
    makeup_pack_id: str
    makeup_item_id: str
    makeup_variants: tuple[str, ...]
    makeup_menu_variants: tuple[str, ...]
    makeup_always_visible_variants: tuple[str, ...]
    outfit_pack_id: str
    outfit_ensemble_id: str
    native_hair: AppearanceItemSelection
    native_headwear: AppearanceItemSelection | None


@dataclass(frozen=True, slots=True)
class PersonaLocale:
    locale: str
    identity: PersonaIdentity
    system_prompt: str
    response_language_instruction: str
    transcription_prompt_base: str


@dataclass(frozen=True, slots=True)
class TextReplacement:
    source: str
    target: str


@dataclass(frozen=True, slots=True)
class IdentityProfile:
    default_locale: str
    defaults: Mapping[str, str]
    legacy_defaults: Mapping[str, str]
    assistant_tokens: tuple[str, ...]
    user_title_tokens: tuple[str, ...]
    organization_token: str
    organization_neutralizations: tuple[TextReplacement, ...]
    organization_context_templates: Mapping[str, str]
    legacy_author_organization: str
    legacy_transcription_prompt: str
    start_work_phrases: tuple[str, ...]
    stop_work_phrases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OfflineDialogue:
    notice: str
    work_mode_value: str
    triggers: Mapping[str, tuple[str, ...]]
    replies: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class DialogueLocale:
    locale: str
    reminder_lines: Mapping[str, str]
    offline: OfflineDialogue
    phrasebook: Mapping[str, tuple[str, ...]]
    line_sets: Mapping[str, tuple[str, ...]]
    templates: Mapping[str, str]
    labels: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class OccasionData:
    kind: str
    month: int
    day: int
    hint_hour: int
    grumble_hour: int
    minimum_grumble_delay_seconds: float


@dataclass(frozen=True, slots=True)
class EventsProfile:
    zodiac: str
    fixed_occasions: tuple[OccasionData, ...]
    qixi_hint_hour: int
    qixi_grumble_hour: int
    qixi_minimum_grumble_delay_seconds: float


@dataclass(frozen=True, slots=True)
class OpenAIVoicePreferences:
    voice_order: tuple[str, ...]
    realtime_unsupported: frozenset[str]


@dataclass(frozen=True, slots=True)
class AzureVoicePreferences:
    voices: Mapping[str, tuple[str, ...]]
    hd_voices: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class SystemLocalVoicePreferences:
    onecore_prefix: str
    preferred_voice_ids: Mapping[str, str]
    preferred_name_markers: Mapping[str, tuple[str, ...]]
    female_compatibility_markers: tuple[str, ...]
    male_markers: tuple[str, ...]
    excluded_name_markers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VoiceProfile:
    default_provider: str
    default_rate: int
    default_volume_percent: int
    default_tts_voice: str
    default_cloud_voice: str
    default_realtime_voice: str
    instructions: Mapping[str, str]
    preview_text: Mapping[str, str]
    openai: OpenAIVoicePreferences
    azure: AzureVoicePreferences
    system_local: SystemLocalVoicePreferences
    fallback_provider_order: Mapping[str, tuple[str, ...]]
    user_selection_wins: bool


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


@dataclass(frozen=True, slots=True)
class MohanCharacterData:
    appearance_defaults: CharacterAppearanceDefaults
    identity: IdentityProfile
    personas: Mapping[str, PersonaLocale]
    dialogues: Mapping[str, DialogueLocale]
    events: EventsProfile
    voice: VoiceProfile


__all__ = (
    "DEFAULT_EXPRESSION_CATALOG_PATH",
    "DEFAULT_RIG_MANIFEST_PATH",
    "EXPRESSION_SCHEMA",
    "FULL_BODY_LAYER_COUNT",
    "FULL_VIEW_COUNT",
    "HAND_LANDMARK_COUNT",
    "MAX_CHANNEL_VALUE",
    "MAX_PITCH_DEGREES",
    "MAX_YAW_DEGREES",
    "MIN_PITCH_DEGREES",
    "PAIR_LENGTH",
    "RECT_LENGTH",
    "RIG_SCHEMA",
    "SCHEMA_VERSION",
    "TRIPLE_LENGTH",
    "AppearanceItemSelection",
    "ArmSpec",
    "AzureVoicePreferences",
    "BodyMeasurementsSpec",
    "BodyProportionsSpec",
    "BrowGuardSpec",
    "CanvasSpec",
    "CharacterAppearanceDefaults",
    "CharacterDataError",
    "CharacterRigManifest",
    "DialogueLocale",
    "EventsProfile",
    "ExpressionRuleSpec",
    "ExpressionStateCatalog",
    "FaceCalibrationSpec",
    "FacePoseAssetSpec",
    "FullBodyCalibrationSpec",
    "IdentityProfile",
    "MohanCharacterData",
    "OccasionData",
    "OfflineDialogue",
    "OpenAIVoicePreferences",
    "PersonaIdentity",
    "PersonaLocale",
    "PhysicsSpec",
    "PoseSpec",
    "SourceBoundExasperatedSpec",
    "SystemLocalVoicePreferences",
    "TextReplacement",
    "ViewRingSpec",
    "ViewportSpec",
    "VoiceProfile",
    "canonical_character_locale",
)
