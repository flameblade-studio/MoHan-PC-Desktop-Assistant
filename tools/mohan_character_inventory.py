"""Inventory existing MoHan data and embedded content without importing runtime code.

This is an engineering index, not a pack builder or a distribution permission.
Reader anchors are verified against source on every run. Unreferenced files stay
outside the proposed payload; provenance paths do not become runtime dependencies.
"""

from __future__ import annotations

lazy import argparse
lazy import ast
lazy import io
lazy import json
lazy import re
lazy import zipfile
lazy from xml.etree import ElementTree as ET
lazy from collections import Counter
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Any

lazy from PIL import Image

lazy from huapu.hashing import sha256_bytes

ROOT = Path(__file__).resolve().parents[1]
DIRECT = "純資料可直接搬"
EMBEDDED = "被程式寫死需先改"
SOURCE_ROOTS = ("domain", "application", "infrastructure", "integrations", "presentation")
IMAGE_SUFFIXES = frozenset({".png", ".ico", ".webp", ".gif", ".jpg", ".jpeg"})
MEDIUM_EVIDENCE_THRESHOLD = 3
HIGH_EVIDENCE_THRESHOLD = 10
NON_PRODUCT_ROOTS = (
    {"path": ".quality-tmp/", "classification": "temporary_or_candidate_output"},
    {"path": "artifacts/", "classification": "candidate_or_generated_output"},
    {"path": "assets/pose-atlas/v4/", "classification": "generation_1_calibration_reference"},
    {"path": "assets/pose-atlas/v4-layered/", "classification": "generation_1_calibration_archive"},
    {"path": "assets/pose-atlas/v4-source/", "classification": "generation_1_review_sources"},
    {"path": "assets/pose-atlas/v4-working/", "classification": "generation_1_calibration_archive"},
    {"path": "docs/media/", "classification": "documentation_and_marketing_media"},
    {"path": "docs/release-evidence/", "classification": "review_and_release_evidence"},
    {"path": "tests/golden/", "classification": "regression_evidence"},
)
CATEGORY_LABELS = {
    "character_appearance_defaults": "角色外觀預設資料／角色外观默认数据／Character appearance defaults／キャラクター外観の既定値",
    "appearance_pack": "正式外觀包／正式外观包／Official appearance archives／正式外観パック",
    "appearance_replacement_mask": "外觀替換遮罩／外观替换遮罩／Appearance replacement masks／外観置換マスク",
    "appearance_silhouette": "服裝輪廓／服装轮廓／Garment silhouettes／衣装の輪郭",
    "body_overlay": "身體覆蓋圖／身体覆盖图／Body overlays／身体の重ね画像",
    "fullbody_blink": "全身眨眼圖／全身眨眼图／Full-body blinks／全身の瞬き",
    "fullbody_complete_frames": "全身完整表情影格／全身完整表情帧／Complete full-body frames／全身の完全表情フレーム",
    "fullbody_complete_masks": "全身完整表情替換遮罩／全身完整表情替换遮罩／Full-body replacement masks／全身の置換マスク",
    "fullbody_complete_oral": "全身口腔遮罩／全身口腔遮罩／Full-body oral masks／全身の口腔マスク",
    "fullbody_core_layer": "全身核心圖層／全身核心图层／Core full-body layers／全身の主要レイヤー",
    "fullbody_expression_rules": "全身表情與嘴部清單／全身表情与嘴部清单／Full-body expression manifests／全身表情と口部の定義",
    "fullbody_master": "全身主視角／全身主视角／Full-body master views／全身の主視点",
    "fullbody_sidecar": "全身中繼資料與綁定／全身元数据与绑定／Full-body metadata and bindings／全身メタデータと紐付け",
    "fullbody_visible_hand": "全身可見手部／全身可见手部／Full-body visible hands／全身の可視の手",
    "garment_visibility": "服裝可見區與手部／服装可见区与手部／Garment visibility and hands／衣装の可視領域と手",
    "halfbody_complete_expression": "半身完整表情與遮罩／半身完整表情与遮罩／Complete half-body expressions and masks／半身の完全表情とマスク",
    "halfbody_expression": "半身表情與原生來源／半身表情与原生来源／Half-body expressions and native sources／半身表情と元画像",
    "halfbody_layer": "半身分層／半身分层／Half-body layers／半身レイヤー",
    "hand_overlay": "手部覆蓋圖／手部覆盖图／Hand overlays／手の重ね画像",
    "makeup_eye_aperture": "妝容眼睛開口遮罩／妆容眼睛开口遮罩／Makeup eye aperture masks／メイクの眼開口マスク",
    "makeup_foundation_mask": "粉底安全區／粉底安全区／Foundation safe regions／ファンデーションの安全領域",
    "makeup_region_rules": "妝容區域規則／妆容区域规则／Makeup region rules／メイク領域の規則",
    "makeup_safe_mask": "妝容安全遮罩／妆容安全遮罩／Makeup safe masks／メイク安全マスク",
    "native_garment_motion": "原生衣裝與動作資料／原生衣装与动作数据／Native garment and motion data／元の衣装と動作データ",
    "source_bound_expression": "來源綁定表情與妝容／来源绑定表情与妆容／Source-bound expressions and makeup／出典に紐付いた表情とメイク",
    "ui_background": "介面角色背景／界面角色背景／Character UI backgrounds／キャラクター背景",
    "ui_brand_decoration": "介面品牌裝飾／界面品牌装饰／UI brand decoration／ブランド装飾",
    "ui_character_icon": "角色圖示／角色图标／Character icon／キャラクターアイコン",
    "character_runtime_binding_data": "角色執行期素材綁定資料／角色运行期素材绑定数据／Character runtime binding data／キャラクターの実行時素材バインドデータ",
    "character_runtime_dialogue_data": "角色執行期台詞資料／角色运行期台词数据／Character runtime dialogue data／キャラクターの実行時台詞データ",
    "character_ui_identifier_data": "角色介面識別資料／角色界面标识数据／Character UI identifier data／キャラクターの UI 識別データ",
    "character_persona_data": "角色身分與人格資料／角色身份与人格数据／Character identity and persona data／キャラクターの身元と人格データ",
    "character_dialogue_data": "角色台詞與事件資料／角色台词与事件数据／Character dialogue and event data／キャラクターの台詞とイベントデータ",
    "character_voice_data": "角色聲音偏好資料／角色声音偏好数据／Character voice preference data／キャラクターの音声設定データ",
    "character_rig_data": "角色外觀骨架資料／角色外观骨架数据／Character rig data／キャラクターのリグデータ",
    "character_expression_catalog": "角色表情狀態目錄／角色表情状态目录／Character expression state catalog／キャラクターの表情状態目録",
    "ui_onboarding": "初次設定角色圖／首次设置角色图／Onboarding character image／初回設定のキャラクター画像",
}


@dataclass(frozen=True)
class Group:
    prefix: str
    category: str
    reader: str
    anchor: str


@dataclass(frozen=True)
class ContentRule:
    """One reproducible rule for content that still lives in Python source."""

    name: str
    content_kind: str
    pattern: re.Pattern[str]
    suggested_data_target: str
    description: str


# Most-specific prefix wins. Each anchor names the real read or composition site.
GROUPS = (
    Group("assets/pose-atlas/v5-base/", "fullbody_master", "presentation/pose_atlas_assets.py", 'self._root / f"{view_id}.png"'),
    Group("assets/pose-atlas/v5-base-layered/", "fullbody_core_layer", "infrastructure/layered_full_body_assets.py", 'root / f"{view_id}_{layer}.png"'),
    Group("assets/pose-atlas/v5-garment-visibility/", "garment_visibility", "infrastructure/source_bound_garment_visibility.py", "MANIFEST ="),
    Group("assets/pose-atlas/v5-appearance-replacement-masks/", "appearance_replacement_mask", "infrastructure/active_outfit_overlay_layers.py", 'CHARACTER_ASSET_PATHS["appearance_masks"]'),
    Group("assets/pose-atlas/v5-appearance-silhouettes/", "appearance_silhouette", "infrastructure/active_outfit_overlay_layers.py", 'CHARACTER_ASSET_PATHS["appearance_silhouettes"]'),
    Group("assets/pose-atlas/v5-body-overlays/", "body_overlay", "infrastructure/active_outfit_overlay_layers.py", 'CHARACTER_ASSET_PATHS["body_overlays"]'),
    Group("assets/pose-atlas/v5-hand-overlays/", "hand_overlay", "infrastructure/active_outfit_overlay_layers.py", 'CHARACTER_ASSET_PATHS["hand_overlays"]'),
    Group("assets/expressions/complete-expressions/", "halfbody_complete_expression", "infrastructure/complete_halfbody_expressions.py", "data = path.read_bytes()"),
    Group("assets/expressions/reviewed-garments/", "native_garment_motion", "infrastructure/reviewed_garment_assets.py", "payload = path.read_bytes()"),
    Group("assets/expressions/source-bound-exasperated/", "source_bound_expression", "infrastructure/exasperated_candidate_assets.py", "records = receipt.get(\"installed_files_sha256\")"),
    Group("assets/expressions/layered/", "halfbody_layer", "infrastructure/layered_face_assets.py", 'root / f"{pose.value}_{layer}.png"'),
    Group("assets/expressions/", "halfbody_expression", "presentation/companion_visual_dynamics.py", "CHARACTER_ASSET_PATHS['halfbody_root']"),
    Group("assets/characters/mohan/appearance/", "character_appearance_defaults", "domain/character_pack/appearance_data.py", 'Path(path).read_text(encoding="utf-8")'),
    Group("assets/characters/mohan/persona/ui-identifiers.json", "character_ui_identifier_data", "domain/service_status_localization.py", '_UI_IDENTIFIERS_PATH = MOHAN_CHARACTER_DATA_ROOT / "persona/ui-identifiers.json"'),
    Group("assets/characters/mohan/persona/", "character_persona_data", "domain/character_pack/character_data.py", 'root / "persona"'),
    Group("assets/characters/mohan/dialogue/runtime.json", "character_runtime_dialogue_data", "domain/sensory_synesthesia.py", '_RUNTIME_DIALOGUE_PATH = MOHAN_CHARACTER_DATA_ROOT / "dialogue" / "runtime.json"'),
    Group("assets/characters/mohan/dialogue/", "character_dialogue_data", "domain/character_pack/character_data.py", 'root / "dialogue"'),
    Group("assets/characters/mohan/voice/", "character_voice_data", "domain/character_pack/character_data.py", 'root / "voice" / "profile.json"'),
    Group("assets/characters/mohan/rig/runtime-bindings.json", "character_runtime_binding_data", "domain/constants.py", '"assets", "characters", "mohan", "rig", "runtime-bindings.json"'),
    Group("assets/characters/mohan/rig/", "character_rig_data", "domain/character_data_types.py", '"rig-manifest.json"'),
    Group("assets/characters/mohan/expressions/", "character_expression_catalog", "domain/character_data_types.py", '"state-catalog.json"'),
    Group("assets/official-packs/", "appearance_pack", "application/service_container.py", 'official_pack_root = asset_root / "assets" / "official-packs"'),
    Group("assets/makeup-eye-apertures/", "makeup_eye_aperture", "domain/outfit_pack_makeup.py", "data = mask_path.read_bytes()"),
    Group("assets/makeup-foundation-safe-regions/", "makeup_foundation_mask", "domain/outfit_pack_makeup.py", "data = mask_path.read_bytes()"),
    Group("assets/makeup-safe-regions/", "makeup_safe_mask", "domain/outfit_pack_makeup.py", "data = mask_path.read_bytes()"),
    Group("assets/makeup/", "makeup_authoring_mirror", "application/service_container.py", 'official_pack_root = asset_root / "assets" / "official-packs"'),
    Group("assets/makeup-safe-regions.json", "makeup_region_rules", "domain/outfit_pack_makeup.py", 'SAFE_REGION_FILE = "makeup-safe-regions.json"'),
    Group("assets/mohan-halfbody.ico", "ui_character_icon", "infrastructure/app_resources.py", 'APP_ICON_PATH = "assets/mohan-halfbody.ico"'),
    Group("assets/onboarding/", "ui_onboarding", "presentation/first_run_wizard.py", 'CHARACTER_ASSET_PATHS["onboarding_artwork"]'),
    Group("assets/ui/mohan-celestial-palace-v1.png", "ui_background", "presentation/dashboard_artwork.py", "ARTWORK_PATH ="),
    Group("assets/ui/mohan-strategist-lobby-v1.png", "ui_background", "presentation/lingxiao_shell.py", "_LOBBY_BACKDROP ="),
    Group("assets/ui/mohan-cloud.svg", "ui_brand_decoration", "presentation/flagship_theme.py", "_THEME_ASSET ="),
)

MANUAL_REVIEW_HINTS = {
    "identity_persona_dialogue": (
        "domain/persona_defaults.py", "domain/app_profile.py", "domain/language_support.py",
        "infrastructure/db.py", "integrations/ai_client.py", "application/companion_phrasebook.py",
        "application/special_occasion.py", "application/proactive_companion_runtime.py",
        "application/wellbeing_reminder.py", "application/wellbeing_runtime.py",
        "presentation/companion_visual_dynamics.py", "presentation/companion_face_animation.py",
        "presentation/ui_localization.py", "presentation/ui_localization_en.py",
        "presentation/ui_localization_ja.py", "presentation/auxiliary_ui_localization.py",
        "presentation/flagship/localization_cloud_home.py",
        "presentation/flagship/localization_interaction.py",
        "presentation/flagship/localization_remote_vision.py",
        "presentation/flagship/localization_security_audit.py",
        "presentation/flagship/localization_themes.py",
        "presentation/flagship/localization_workflows.py",
        "presentation/flagship_ui_localization.py",
        "domain/somniloquy.py", "domain/wardrobe_intuition.py", "domain/affective_state.py",
        "domain/shyness.py", "domain/shy_gaze.py", "domain/affinity_state.py",
        "domain/personality_state.py", "domain/emotional_resonance.py", "domain/sword_soul_resonance.py",
    ),
    "voice_preferences": (
        "domain/speech_configuration.py", "application/presentation_ports.py",
        "presentation/dashboard_voice.py", "integrations/speech_voice_catalog.py",
        "integrations/azure_voice_catalog.py",
        "integrations/realtime_voice.py", "presentation/companion_speech_emotion.py",
    ),
    "rig_angle_expression_pose_rules": (
        "domain/character_body_profile.py", "domain/outfit_pack_archive.py", "domain/constants.py",
        "domain/character_pose.py", "domain/pose_pack.py", "domain/face_rig.py", "domain/companion_animation_contract.py",
        "domain/character_full_body_rig.py", "domain/character_framing.py",
        "domain/framing_context_policy.py", "application/framing_orchestrator.py",
        "domain/expression_system.py", "domain/outfit_pack_makeup.py", "domain/makeup_eye_states.py",
        "domain/makeup_mouth_states.py", "application/behavior_director.py",
        "application/service_container.py", "infrastructure/layered_full_body_assets.py",
        "infrastructure/layered_full_body_renderer.py", "infrastructure/layered_face_assets.py",
        "infrastructure/layered_face_renderer.py", "infrastructure/face_assets.py",
        "infrastructure/active_outfit_overlay_layers.py", "infrastructure/core_hand_regions.py",
        "infrastructure/complete_halfbody_expressions.py", "infrastructure/reviewed_pose_motion.py",
        "infrastructure/exasperated_candidate_assets.py", "presentation/companion_wait_expression.py",
        "presentation/companion_face_animation.py", "presentation/companion_face_assets.py",
        "presentation/companion_visual_physics.py", "integrations/openai_outfit_generator.py",
    ),
}

# These hints preserve the analysis coverage that predated data extraction. A
# hint never creates an embedded-code record; only CONTENT_RULES or the exact
# rig-canvas detector below can do that.
CONTENT_RULES = (
    ContentRule(
        "character_name_literal",
        "identity",
        re.compile(r"墨寒|(?<![A-Za-z])MoHan(?![A-Za-z])|(?<![A-Za-z])Mohan(?![A-Za-z])"),
        "assets/characters/mohan/persona/profile.json",
        "角色名字仍是原始碼字串；引擎或介面應由角色身分資料代入。",
    ),
    ContentRule(
        "character_title_or_dialogue_literal",
        "persona_dialogue",
        re.compile(r"主上|赤焰[劍剑]|劍魂|剑魂|汴京|妾"),
        "assets/characters/mohan/dialogue/<locale>.json",
        "角色稱謂、故事設定或台詞仍寫在原始碼。",
    ),
    ContentRule(
        "character_voice_preference_literal",
        "voice",
        re.compile(r"(?<![A-Za-z])coral(?![A-Za-z])|Yating"),
        "assets/characters/mohan/voice/profile.json",
        "墨寒偏好的聲音識別碼仍寫在原始碼。",
    ),
    ContentRule(
        "character_body_profile_literal",
        "rig",
        re.compile(r"mohan-body-v2|flameblade\.mohan"),
        "assets/characters/mohan/rig/rig-manifest.json",
        "角色身形或角色識別碼仍寫在原始碼。",
    ),
    ContentRule(
        "character_appearance_pack_identifier",
        "appearance",
        re.compile(
            r"(?<![A-Za-z0-9])mohan\.(?:makeup|official|default|sponsor)\.[a-z0-9][a-z0-9.-]*"
            r"|(?<![A-Za-z0-9-])mohan-signature(?![A-Za-z0-9-])"
        ),
        "assets/characters/mohan/appearance/defaults.json",
        "墨寒專屬外觀包或外觀項目識別碼仍寫在原始碼。",
    ),
    ContentRule(
        "character_protocol_label_literal",
        "expression",
        re.compile(r"MOHAN_EMOTION"),
        "assets/characters/mohan/expressions/state-catalog.json",
        "角色命名的情緒協定標籤仍寫在引擎原始碼。",
    ),
    ContentRule(
        "character_asset_path_literal",
        "rig_assets",
        re.compile(
            r"assets/(?:characters/mohan|expressions(?:/|$)|pose-atlas/v5|"
            r"mohan-|ui/mohan|onboarding/first-run)"
        ),
        "assets/characters/mohan/rig/rig-manifest.json",
        "墨寒專屬素材路徑仍由程式直接指定。",
    ),
    ContentRule(
        "character_canvas_size_literal",
        "rig",
        re.compile(r"1024\s*[x×]\s*1536|1254\s*[x×]\s*1254"),
        "assets/characters/mohan/rig/rig-manifest.json",
        "墨寒現行畫布尺寸仍寫在程式流程。",
    ),
    ContentRule(
        "character_expression_state_literal",
        "expression",
        re.compile(
            r"(?<![A-Za-z0-9_])(?:(?:thinking|attentive|determined|gentle_smile|proud|relieved|"
            r"worried|surprised|shy|shy_cute|restrained_amused|exasperated|"
            r"mock_hit|eureka|protective)_front|mock_scold|caught|glance)"
            r"(?![A-Za-z0-9_])"
        ),
        "assets/characters/mohan/expressions/state-catalog.json",
        "角色專屬表情或狀態名稱仍寫在程式流程。",
    ),
    ContentRule(
        "character_pose_name_literal",
        "rig",
        re.compile(
            r"front-crossed|left-cheek-rest|left-neutral|right-neutral|"
            r"back-two-thirds-(?:left|right)|back-full|cheek-rest|"
            r"front-(?:mock-scold|mock-hit|eureka|exasperated)"
        ),
        "assets/characters/mohan/rig/rig-manifest.json",
        "墨寒專屬姿勢或輪廓名稱仍寫在程式流程。",
    ),
    ContentRule(
        "character_layer_name_literal",
        "rig",
        re.compile(
            r"hair_back|oral_cavity|teeth_tongue|lip_(?:lower|upper)|"
            r"corner_(?:left|right)|blush_(?:left|right)|iris_(?:left|right)|"
            r"eyelid_(?:left|right)|eyeliner_(?:left|right)|brow_(?:left|right)|"
            r"hair_(?:left|right)|sleeve_(?:left|right)"
        ),
        "assets/characters/mohan/rig/rig-manifest.json",
        "墨寒現行圖層名稱仍寫在程式流程。",
    ),
)

PRODUCT_SHELL_ALLOWLIST = {
    "application/application_bootstrap.py": "墨寒最外層組裝入口保留產品程序名稱。",
    "application/runtime_bootstrap.py": "墨寒產品執行期入口保留程序與執行緒識別字。",
    "domain/constants.py": "現行 PoseAtlas 世代目錄名依專案契約只在此定義一次（AGENTS.md：換代只改這裡），屬墨寒產品殼。",
    "domain/version_info.py": "原墨寒專案的版本、儲存庫與更新網址屬產品殼。",
    "infrastructure/app_resources.py": "產品名、Windows AppUserModelID、圖示與 studio 識別屬墨寒產品殼。",
    "infrastructure/backup_manager.py": "墨寒使用者備份檔名與產品資料位置屬產品殼相容契約。",
    "infrastructure/profile_transfer.py": "墨寒攜帶檔名稱與既有使用者匯入格式屬產品殼相容契約。",
    "infrastructure/updater.py": "墨寒更新端點、User-Agent 與發行資產名稱屬產品殼。",
    "presentation/auxiliary_ui_localization.py": "更新、備份與攜帶檔中的墨寒產品名稱屬產品殼文案。",
    "presentation/preview_app.py": "墨寒預覽封裝入口的視窗名與內建產品素材屬產品殼。",
}

# Exact product-identity literals: the MoHan product name, About heading, the
# network User-Agent, and secure-storage labels. They identify the MoHan product
# shell, not the character, so they never count as extraction work. Any other
# character literal in the same file is still reported.
PRODUCT_IDENTITY_LITERAL = re.compile(
    r"墨寒桌面助理|墨寒桌面助手|MoHan Desktop Assistant|墨寒デスクトップアシスタント"
    r"|關於墨寒|关于墨寒|About MoHan|墨寒について"
    r"|MoHan-Desktop-Assistant/"
    r"|MoHan (?:\{provider_id\} OAuth token|Home Assistant token|OpenAI API key"
    r"|local face identity templates|local gesture skeleton templates)"
)
PRODUCT_IDENTITY_RULE = ContentRule(
    "product_identity_literal",
    "product_identity",
    PRODUCT_IDENTITY_LITERAL,
    "infrastructure/app_resources.py",
    "墨寒產品殼識別字串（產品名、關於、User-Agent、安全儲存標籤），依產品契約保留。",
)
PERSISTED_IDENTIFIER_RULE = ContentRule(
    "persisted_identifier",
    "product_shell",
    re.compile(r"mohan\.default\.blue-silver"),
    "application/wardrobe_service.py",
    "自 v2 起寫入 active_outfit_id 的不透明產品殼識別碼；必須保持位元相同以相容既有使用者設定。",
)
PERSISTED_IDENTIFIER_PATHS = frozenset(
    {
        "application/wardrobe_service.py",
        "domain/outfit_pack_official.py",
    }
)
PRODUCT_IDENTITY_REASON = "命中內容只有墨寒產品名、「關於」標題、連網 User-Agent 或安全儲存標籤，屬墨寒產品殼識別。"

UI_TEXT_REFERENCE_PATHS = frozenset(
    {
        "domain/safe_error_localization.py",
        "domain/service_status_localization.py",
        "integrations/cloud_connectors.py",
        "integrations/realtime_contracts.py",
        "integrations/remote_control.py",
        "presentation/_dashboard_wardrobe_tab.py",
        "presentation/dashboard_conversation.py",
        "presentation/dashboard_settings.py",
        "presentation/dashboard_settings_persistence.py",
        "presentation/dashboard_shell.py",
        "presentation/dashboard_today_memory.py",
        "presentation/dashboard_voice.py",
        "presentation/dashboard_wardrobe_preferences.py",
        "presentation/dashboard_wardrobe_preview.py",
        "presentation/dashboard_wardrobe_status.py",
        "presentation/desktop_companion_status.py",
        "presentation/flagship/audit.py",
        "presentation/flagship/cloud.py",
        "presentation/flagship/companion.py",
        "presentation/flagship/gesture_editor.py",
        "presentation/flagship/localization_cloud_home.py",
        "presentation/flagship/localization_interaction.py",
        "presentation/flagship/localization_remote_vision.py",
        "presentation/flagship/localization_security_audit.py",
        "presentation/flagship/localization_themes.py",
        "presentation/flagship/localization_workflows.py",
        "presentation/flagship/overview.py",
        "presentation/flagship/remote.py",
        "presentation/flagship/runtime.py",
        "presentation/flagship/settings_security.py",
        "presentation/flagship/vision.py",
        "presentation/flagship_ui_localization.py",
        "presentation/ui_localization.py",
        "presentation/ui_localization_en.py",
        "presentation/ui_localization_ja.py",
    }
)

CLASSIFICATION_REASONS = {
    "engine_extract": "此檔屬未來炎劍鑄魂引擎；偵測到的角色內容須改由角色資料提供。",
    "persisted_identifier": "命中內容只有既有使用者設定所保存的不透明識別碼；它屬產品殼持久化契約，不是角色外觀資料。",
    "product_shell_allowed": "此檔位於逐檔白名單；命中內容是墨寒產品殼識別，可依既有產品契約保留。",
    "ui_text_reference": "此檔的介面文字直接提到角色；應由角色身分資料以佔位符代入。",
}

WORK_PACKAGE_DEFINITIONS = (
    {
        "id": "engine-identity-parameterization",
        "titles": ("引擎身分參數化", "引擎身份参数化", "Engine identity parameterization", "エンジン身元のパラメータ化"),
        "objective": "把引擎、平台與儲存邊界中的墨寒名稱改由產品或角色身分設定注入。",
        "exclusions": "不改產品殼白名單，不處理圖像路徑、姿勢與圖層。",
    },
    {
        "id": "persona-dialogue-voice-extraction",
        "titles": ("人格、台詞與聲音抽離", "人格、台词与声音抽离", "Persona, dialogue and voice extraction", "人格・台詞・音声の抽出"),
        "objective": "把剩餘稱謂、故事台詞、提示詞與聲音偏好接到現有角色資料。",
        "exclusions": "不改介面純名稱文字，不處理 rig 或正式素材 bytes。",
    },
    {
        "id": "rig-and-asset-parameterization",
        "titles": ("Rig 與素材路徑參數化", "Rig 与素材路径参数化", "Rig and asset parameterization", "Rig と素材パスのパラメータ化"),
        "objective": "把角色專屬畫布、姿勢、表情、圖層與素材路徑接到 rig 或表情資料。",
        "exclusions": "不移動或修改正式素材，不改產品殼品牌與更新設定。",
    },
    {
        "id": "ui-name-parameterization",
        "titles": ("介面角色名稱參數化", "界面角色名称参数化", "UI character-name parameterization", "UI キャラクター名のパラメータ化"),
        "objective": "把介面中的墨寒名稱與使用者稱謂改成角色資料佔位符。",
        "exclusions": "保留 About、更新、攜帶檔等已列入產品殼白名單的產品名稱。",
    },
)


def source_evidence(root: Path, path: str, anchor: str, *, after: str | None = None) -> dict[str, Any]:
    """Bind a reader claim to an actual line, failing when the anchor drifts."""
    lines = (root / path).read_text(encoding="utf-8").splitlines()
    active = after is None
    for number, line in enumerate(lines, 1):
        if after is not None and after in line:
            active = True
        if active and anchor in line:
            return {"path": path, "line": number, "text": line.strip()}
    raise ValueError(f"Reader anchor missing: {path}: {anchor}")


def file_metadata(path: Path, data: bytes | None = None) -> dict[str, Any]:
    payload = path.read_bytes() if data is None else data
    result: dict[str, Any] = {"sha256": sha256_bytes(payload), "bytes": len(payload)}
    if path.suffix.lower() in IMAGE_SUFFIXES:
        with Image.open(io.BytesIO(payload)) as image:
            result["image"] = {"width": image.width, "height": image.height, "mode": image.mode}
    elif path.suffix.lower() == ".svg":
        attributes = ET.fromstring(payload).attrib
        result["image"] = {
            "width": int(attributes["width"]), "height": int(attributes["height"]),
            "mode": "SVG", "view_box": attributes.get("viewBox"),
        }
    return result


def manifest_references(root: Path, manifest: Path) -> dict[str, list[dict[str, str]]]:
    """Index local records, excluding authoring lineage and review references."""
    excluded_keys = {"source_lineage", "base", "eye_patch", "source", "provenance", "approval", "owner_approval", "review_page", "approved_installation"}
    found: dict[str, list[dict[str, str]]] = {}

    def walk(value: Any, pointer: str) -> None:
        if isinstance(value, dict):
            path = value.get("path")
            if isinstance(path, str):
                candidates = (manifest.parent / path, root / path)
                for candidate in candidates:
                    if candidate.is_file() and candidate.resolve().is_relative_to(root.resolve()):
                        name = candidate.relative_to(root).as_posix()
                        found.setdefault(name, []).append({"path": manifest.relative_to(root).as_posix(), "pointer": pointer + "/path"})
                        break
            for key, child in value.items():
                if key not in excluded_keys:
                    walk(child, pointer + "/" + key.replace("~", "~0").replace("/", "~1"))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, pointer + f"/{index}")

    walk(json.loads(manifest.read_text(encoding="utf-8")), "")
    return found


def _reference_index(root: Path) -> dict[str, list[dict[str, str]]]:
    manifests = [
        "assets/expressions/complete-expressions/manifest.json",
        "assets/expressions/reviewed-garments/manifest.json",
        "assets/expressions/reviewed-garments/cheek-rest/motion/manifest.json",
        "assets/makeup-safe-regions.json",
        "assets/pose-atlas/v5-base-layered/complete_expression_manifest.json",
        "assets/pose-atlas/v5-garment-visibility/manifest.json",
    ]
    result: dict[str, list[dict[str, str]]] = {}
    for name in manifests:
        for path, evidence in manifest_references(root, root / name).items():
            result.setdefault(path, []).extend(evidence)
    # The native authority is read from the expression directory, not the garment directory.
    name = manifests[1]
    poses = json.loads((root / name).read_text(encoding="utf-8"))["poses"]
    for pose, record in poses.items():
        path = "assets/expressions/" + record["native_source_file"]
        result.setdefault(path, []).append({"path": name, "pointer": f"/poses/{pose}/native_source_file"})
    return result


def _excluded_scope(path: str) -> tuple[str, str]:
    if path == "assets/mohan-taskbar-icon.png":
        return "excluded_product_build_output", "Windows 圖示建置產物；執行期讀取 mohan-halfbody.ico"
    if path.startswith("assets/pose-atlas/v4"):
        return "excluded_calibration_archive", "一代封存與校準參考"
    if path.startswith("docs/media/"):
        return "excluded_marketing", "文件與行銷媒體"
    return "excluded_support", "來源、審閱或非角色依賴；未列入執行期讀取範圍"


def _asset_scope(path: str, group: Group | None, references: dict[str, Any]) -> tuple[str, str]:
    if group is None:
        return _excluded_scope(path)
    category = group.category
    if category == "makeup_authoring_mirror":
        return "excluded_authoring_mirror", "正式讀取 official-packs 封存包；此目錄是製作鏡像"
    if category in {"halfbody_complete_expression", "native_garment_motion", "makeup_eye_aperture", "makeup_foundation_mask", "makeup_safe_mask"}:
        if path in references or path.endswith("manifest.json"):
            return "runtime_data", "執行期 manifest 引用"
        return "excluded_review_source", "執行期 manifest 未引用的審閱原圖或舊候選"
    if category == "fullbody_master" and path.endswith((".landmarks.json", ".hands.json")):
        return "product_validation_data", "packaged self-test 驗證必備；一般動畫不讀取"
    if category == "fullbody_master" and not path.endswith((".png", "BUILD-METADATA.json", "DISPLAY-PLACEMENT.json", ".blink-binding.json")):
        return "excluded_provenance", "保存來源與核准鏈；未作執行期影像載入"
    if category == "halfbody_layer" and not path.endswith(".png"):
        return "excluded_provenance", "分層建置來源與證據"
    return "runtime_data", "正式載入資料；純資料搬移仍須後續調整路徑接線"


def _fullbody_category(path: str) -> str:
    if "/complete-expressions/" in path:
        return "fullbody_complete_" + path.split("/complete-expressions/", maxsplit=1)[1].split("/", maxsplit=1)[0]
    if "_blink_" in path:
        return "fullbody_blink"
    if "_visible_hand_" in path:
        return "fullbody_visible_hand"
    if path.endswith(".json"):
        return "fullbody_expression_rules"
    return "fullbody_core_layer"


def _readers(root: Path, group: Group, category: str, path: str) -> list[dict[str, Any]]:
    reader, anchor = group.reader, group.anchor
    if category == "fullbody_blink":
        anchor = 'root / f"{view_id}_blink_{state.value}.png"'
    elif category == "fullbody_visible_hand" or "visible_hand" in path:
        reader = "infrastructure/core_hand_regions.py"
        anchor = 'directory / f"{view_id}_visible_hand_{side}.png"' if category == "fullbody_visible_hand" else 'directory / f"{prefix}_visible_hand_{side}.png"'
    elif category.startswith("fullbody_complete_"):
        return [source_evidence(root, reader, "data = path.read_bytes()", after="def _resolve_complete_expression_asset(")]
    elif category == "native_garment_motion" and "/motion/" in path:
        reader, anchor = "infrastructure/reviewed_pose_motion.py", "payload = path.read_bytes()"
    if category == "source_bound_expression":
        anchor = 'hashlib.sha256(path.read_bytes()).hexdigest() != digest'
        if path.endswith("/receipt.json"):
            anchor = 'receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))'
        elif path.endswith("/appearance/manifest.json"):
            anchor = 'appearance = json.loads((root / "appearance" / "manifest.json").read_text(encoding="utf-8"))'
        elif path.endswith("/manifest.json"):
            anchor = 'manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))'
    manifest_readers = {
        "assets/expressions/complete-expressions/manifest.json": ("infrastructure/complete_halfbody_expressions.py", 'data = json.loads(path.read_text(encoding="utf-8"))'),
        "assets/expressions/reviewed-garments/manifest.json": ("infrastructure/reviewed_garment_assets.py", 'manifest = json.loads(manifest_path.read_text(encoding="utf-8"))'),
        "assets/expressions/reviewed-garments/cheek-rest/motion/manifest.json": ("infrastructure/reviewed_pose_motion.py", 'value = json.loads(manifest_path.read_text(encoding="utf-8"))'),
        "assets/pose-atlas/v5-garment-visibility/manifest.json": ("infrastructure/source_bound_garment_visibility.py", 'manifest = json.loads(manifest_path.read_text(encoding="utf-8"))'),
        "assets/makeup-safe-regions.json": ("domain/outfit_pack_makeup.py", 'payload = json.loads(source.read_text(encoding="utf-8"))'),
    }
    if path in manifest_readers:
        reader, anchor = manifest_readers[path]
    elif category == "garment_visibility":
        anchor = "payload = target.read_bytes()"
    suffix_readers = (
        ("mouth_authority_manifest.json", group.reader, 'path = root / "mouth_authority_manifest.json"'),
        ("complete_expression_manifest.json", group.reader, "path = root / COMPLETE_EXPRESSION_MANIFEST_NAME"),
        ("BUILD-METADATA.json", group.reader, 'path = self._root / "BUILD-METADATA.json"'),
        ("DISPLAY-PLACEMENT.json", "infrastructure/full_body_display_placement.py", 'manifest = json.loads((root / FILENAME).read_text(encoding="utf-8"))'),
        (".blink-binding.json", "infrastructure/full_body_blink_binding.py", 'receipt_path = authority_root / f"{view_id}.blink-binding.json"'),
        ((".landmarks.json", ".hands.json"), "application/packaged_self_test.py", 'for suffix in (".landmarks.json", ".hands.json")'),
    )
    for suffix, source, site in suffix_readers:
        if path.endswith(suffix):
            reader, anchor = source, site
            break
    return [source_evidence(root, reader, anchor)]


def _pack_members(root: Path, path: Path) -> list[dict[str, Any]]:
    reader = source_evidence(root, "infrastructure/active_outfit_overlay.py", "encoded = archive.read(declaration.path)")
    records = []
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        for name in sorted(archive.namelist()):
            if name.endswith("/"):
                continue
            categories = [key for key in ("looks", "hairstyles", "headwear", "makeup", "accessories", "ensembles") if name in json.dumps(manifest.get(key, []), ensure_ascii=False)]
            member_reader = source_evidence(root, "domain/outfit_pack_archive.py", 'manifest = json.loads(archive.read(MANIFEST).decode("utf-8"))') if name == "manifest.json" else reader
            records.append({"path": path.relative_to(root).as_posix() + "!" + name, "category": "appearance_pack_member", "appearance_categories": categories, "scope": "runtime_data", "migration": DIRECT, "readers": [member_reader], **file_metadata(Path(name), archive.read(name))})
    return records


def _python_sources(root: Path) -> dict[str, str]:
    sources: dict[str, str] = {}
    for directory in SOURCE_ROOTS:
        for path in sorted((root / directory).rglob("*.py")):
            relative = path.relative_to(root).as_posix()
            sources[relative] = path.read_text(encoding="utf-8")
    for path in sorted(root.glob("*.py")):
        relative = path.relative_to(root).as_posix()
        sources[relative] = path.read_text(encoding="utf-8")
    return sources


def _parsed_python(text: str) -> ast.Module:
    return ast.parse(re.sub(r"(?m)^(\s*)lazy (import |from )", r"\1\2", text))


def _docstring_nodes(tree: ast.Module) -> set[int]:
    result: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            result.add(id(node.value))
    return result


def _match_line(lines: list[str], node: ast.Constant, matched: str) -> int:
    """Return the first source line of a possibly multi-line literal that shows the match."""
    last = node.end_lineno or node.lineno
    return next(
        (number for number in range(node.lineno, last + 1) if matched in lines[number - 1]),
        node.lineno,
    )


def _fstring_templates(tree: ast.Module) -> dict[int, tuple[str, int]]:
    """Map each f-string constant piece to its template text and offset within it."""
    templates: dict[int, tuple[str, int]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr):
            continue
        pieces = [
            (part, part.value if isinstance(part, ast.Constant) else "{" + ast.unparse(part.value) + "}")
            for part in node.values
        ]
        template = "".join(text for _, text in pieces)
        offset = 0
        for part, text in pieces:
            if isinstance(part, ast.Constant):
                templates[id(part)] = (template, offset)
            offset += len(text)
    return templates


def _product_identity_spans(text: str) -> list[tuple[int, int]]:
    return [match.span() for match in PRODUCT_IDENTITY_LITERAL.finditer(text)]


def _content_evidence(path: str, text: str) -> list[dict[str, Any]]:
    """Return literal evidence only; identifiers, comments and hints do not count."""
    lines = text.splitlines()
    tree = _parsed_python(text)
    docstrings = _docstring_nodes(tree)
    # f-string pieces are separate constants; judge product identity on the whole template.
    templates = _fstring_templates(tree)
    found: dict[tuple[int, str, str], dict[str, Any]] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            template, offset = templates.get(id(node), (node.value, 0))
            identity_spans = _product_identity_spans(template)
            for content_rule in CONTENT_RULES:
                for match in content_rule.pattern.finditer(node.value):
                    start, end = match.start() + offset, match.end() + offset
                    rule = (
                        PRODUCT_IDENTITY_RULE
                        if content_rule.name == "character_name_literal"
                        and any(left <= start and end <= right for left, right in identity_spans)
                        else PERSISTED_IDENTIFIER_RULE
                        if content_rule.name == "character_appearance_pack_identifier"
                        and path in PERSISTED_IDENTIFIER_PATHS
                        and match.group(0) == "mohan.default.blue-silver"
                        else content_rule
                    )
                    line = _match_line(lines, node, match.group(0))
                    key = (line, rule.name, match.group(0))
                    found[key] = {
                        "path": path,
                        "line": line,
                        "text": lines[line - 1].strip(),
                        "matched": match.group(0),
                        "rule": rule.name,
                        "content_kind": rule.content_kind,
                        "description": rule.description,
                        "suggested_data_target": rule.suggested_data_target,
                    }
        if isinstance(node, (ast.Tuple, ast.List)):
            values = []
            for item in node.elts:
                if not isinstance(item, ast.Constant) or not isinstance(item.value, int):
                    values = []
                    break
                values.append(item.value)
            if tuple(values) not in {(1024, 1536), (1254, 1254)}:
                continue
            matched = "x".join(str(value) for value in values)
            key = (node.lineno, "character_canvas_size_literal", matched)
            found[key] = {
                "path": path,
                "line": node.lineno,
                "text": lines[node.lineno - 1].strip(),
                "matched": matched,
                "rule": "character_canvas_size_literal",
                "content_kind": "rig",
                "description": "墨寒現行畫布尺寸仍寫在程式流程。",
                "suggested_data_target": "assets/characters/mohan/rig/rig-manifest.json",
            }
    return [found[key] for key in sorted(found)]


def _top_level_symbols(tree: ast.Module) -> list[dict[str, Any]]:
    symbols = []
    supported = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.Assign,
        ast.AnnAssign,
    )
    for node in tree.body:
        if not isinstance(node, supported):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
        elif isinstance(node, ast.Assign):
            name = ast.unparse(node.targets[0])
        else:
            name = ast.unparse(node.target)
        symbols.append({"name": name, "line": node.lineno, "end_line": node.end_lineno})
    return symbols


def _source_classification(path: str, evidence: list[dict[str, Any]]) -> str:
    rules = {row["rule"] for row in evidence} - {PRODUCT_IDENTITY_RULE.name}
    if not rules:
        return "product_shell_allowed"
    if rules == {PERSISTED_IDENTIFIER_RULE.name}:
        return "persisted_identifier"
    shell_rules = {"character_name_literal", "character_asset_path_literal"}
    if path in PRODUCT_SHELL_ALLOWLIST and rules <= shell_rules:
        return "product_shell_allowed"
    ui_rules = {"character_name_literal", "character_title_or_dialogue_literal"}
    if path in UI_TEXT_REFERENCE_PATHS and rules <= ui_rules:
        return "ui_text_reference"
    return "engine_extract"


def _source_difficulty(evidence: list[dict[str, Any]]) -> str:
    rules = {row["rule"] for row in evidence}
    rig_rules = {
        "character_asset_path_literal",
        "character_body_profile_literal",
        "character_canvas_size_literal",
        "character_expression_state_literal",
        "character_layer_name_literal",
        "character_pose_name_literal",
    }
    if rules & rig_rules or len(evidence) >= HIGH_EVIDENCE_THRESHOLD:
        return "high"
    if (
        len(evidence) >= MEDIUM_EVIDENCE_THRESHOLD
        or "character_title_or_dialogue_literal" in rules
    ):
        return "medium"
    return "low"


def _work_package(classification: str, evidence: list[dict[str, Any]]) -> str | None:
    if classification in {"persisted_identifier", "product_shell_allowed"}:
        return None
    if classification == "ui_text_reference":
        return "ui-name-parameterization"
    rules = {row["rule"] for row in evidence}
    if rules & {
        "character_title_or_dialogue_literal",
        "character_voice_preference_literal",
    }:
        return "persona-dialogue-voice-extraction"
    rig_rules = {
        "character_asset_path_literal",
        "character_body_profile_literal",
        "character_canvas_size_literal",
        "character_expression_state_literal",
        "character_layer_name_literal",
        "character_pose_name_literal",
    }
    if rules & rig_rules:
        return "rig-and-asset-parameterization"
    return "engine-identity-parameterization"


def _code_records(root: Path) -> list[dict[str, Any]]:
    sources = _python_sources(root)
    evidence_by_path = {}
    for path, text in sources.items():
        evidence = _content_evidence(path, text)
        if evidence:
            evidence_by_path[path] = evidence
    records = []
    for path, evidence in sorted(evidence_by_path.items()):
        text = sources[path]
        tree = _parsed_python(text)
        classification = _source_classification(path, evidence)
        module = path.removesuffix(".py").replace("/", ".")
        consumer_pattern = re.compile(rf"\b(?:from|import) {re.escape(module)}\b")
        consumers = []
        for source_path, source in sorted(sources.items()):
            consumers.extend(
                {"path": source_path, "line": number, "text": line.strip()}
                for number, line in enumerate(source.splitlines(), 1)
                if consumer_pattern.search(line)
            )
        if path == "presentation/preview_app.py":
            consumers.append(source_evidence(root, "tools/build_preview_package.py", 'command.append(str(ROOT / "presentation" / "preview_app.py"))'))
        targets = sorted({row["suggested_data_target"] for row in evidence})
        records.append(
            {
                "path": path,
                "category": "embedded_character_content",
                "content_categories": sorted({row["content_kind"] for row in evidence}),
                "scope": "embedded_code",
                "migration": EMBEDDED,
                "classification": classification,
                "classification_reason": (
                    PRODUCT_SHELL_ALLOWLIST.get(path, PRODUCT_IDENTITY_REASON)
                    if classification == "product_shell_allowed"
                    else CLASSIFICATION_REASONS[classification]
                ),
                "suggested_data_targets": targets,
                "estimated_difficulty": _source_difficulty(evidence),
                "work_package": _work_package(classification, evidence),
                "readers": consumers,
                "content_locations": evidence,
                "symbols": _top_level_symbols(tree),
                "note": "只有 content_locations 的具名規則證據構成計數；人工提示、識別碼、註解與 docstring 均不單獨計入。",
                **file_metadata(root / path),
            }
        )
    return records


def _manual_review_hints(code_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    detected = {row["path"]: row for row in code_records}
    categories: dict[str, set[str]] = {}
    for category, paths in MANUAL_REVIEW_HINTS.items():
        for path in paths:
            categories.setdefault(path, set()).add(category)
    hints = []
    for path, suggested_categories in sorted(categories.items()):
        record = detected.get(path)
        hints.append(
            {
                "path": path,
                "suggested_categories": sorted(suggested_categories),
                "status": "confirmed_by_content_rules" if record else "review_hint_only",
                "evidence_rules": sorted(
                    {row["rule"] for row in record["content_locations"]}
                ) if record else [],
            }
        )
    return hints


def build_inventory(root: Path = ROOT) -> dict[str, Any]:
    """Return a stable repository-relative, physically measured inventory."""
    root = root.resolve()
    references = _reference_index(root)
    records = []
    appearance_catalog = []
    paths = []
    for directory in ("assets", "docs/media"):
        paths.extend(path for path in (root / directory).rglob("*") if path.is_file())
    paths.sort(key=lambda path: path.relative_to(root).as_posix())
    for path in paths:
        relative = path.relative_to(root).as_posix()
        group = next((g for g in GROUPS if relative.startswith(g.prefix)), None)
        category = group.category if group else "archive_or_support"
        if relative == "assets/mohan-taskbar-icon.png":
            category = "ui_character_icon_build_output"
        if category == "fullbody_core_layer":
            category = _fullbody_category(relative)
        scope, reason = _asset_scope(relative, group, references)
        readers = _readers(root, group, category, relative) if group and scope in {"runtime_data", "product_validation_data"} else []
        if category == "fullbody_master" and path.suffix != ".png":
            category = "fullbody_sidecar"
        if category == "halfbody_expression" and relative not in references and path.stem.startswith(("cheek-native", "cheek_native")):
            scope, reason, readers = "excluded_review_source", "正式原生來源已由 manifest 替換；舊審閱原圖", []
        if relative in references and relative.startswith("assets/expressions/") and "/" not in relative.removeprefix("assets/expressions/"):
            readers = [source_evidence(root, "infrastructure/reviewed_garment_assets.py", "root.parent, {\"path\": name, \"sha256\": native_sha}")]
        record = {"path": relative, "category": category, "scope": scope, "migration": DIRECT, "reason": reason, "readers": readers, "manifest_references": references.get(relative, []), **file_metadata(path)}
        records.append(record)
        if path.suffix == ".mohan-outfit":
            records.extend(_pack_members(root, path))
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            for component in ("looks", "hairstyles", "headwear", "makeup", "accessories", "ensembles"):
                appearance_catalog.extend(
                    {
                        "archive": relative,
                        "category": component,
                        "id": item["id"],
                        "display_names": item["display_names"],
                        "variants": sorted(variant["id"] for variant in item.get("variants", [])),
                    }
                    for item in manifest.get(component, [])
                )
    code_records = _code_records(root)
    records.extend(code_records)
    records.sort(key=lambda row: row["path"])
    counts = Counter(row["category"] for row in records if row["scope"] == "runtime_data" and "!" not in row["path"])
    classification_counts = Counter(row["classification"] for row in code_records)
    return {
        "schema": "mohan.character-inventory.v1", "schema_version": 1,
        "purpose": "existing_content_index_only",
        "owner_decisions": {"standalone_download_design": True, "pack_visibility": "private_repository", "character_asset_license": "owner_decision_pending", "dlc_relationship": "owner_decision_pending", "engine_license": "MIT", "art_tool_license": "MIT"},
        "scope_notes": ["runtime_data 包含正常與選配正式讀取；不是目前某一影格的追蹤", "embedded_code 只由實際字串或角色專屬數值規則產生；人工提示、註解與 docstring 不計數", "content_locations 的 line、text、matched 與 rule 是可重現判定證據", "readers 的 line 與 text 指向讀取或模板；manifest_references 點名精確宣告", "封存、製作鏡像、審閱原圖與來源 sidecar 均明確排除；既有核准 scope 沿用", "scratchpad、artifacts、.quality-tmp、docs/release-evidence、tests/golden 全樹不屬產品包輸入"],
        "non_product_roots": [dict(row) for row in NON_PRODUCT_ROOTS],
        "runtime_file_counts": dict(sorted(counts.items())),
        "appearance_catalog": appearance_catalog,
        "embedded_code_classification_counts": dict(sorted(classification_counts.items())),
        "manual_review_hints": _manual_review_hints(code_records),
        "product_shell_allowlist": [
            {"path": path, "reason": reason}
            for path, reason in sorted(PRODUCT_SHELL_ALLOWLIST.items())
        ],
        "scope_counts": dict(sorted(Counter(row["scope"] for row in records).items())),
        "files": records,
    }


def render_inventory(inventory: dict[str, Any]) -> str:
    return json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _worklist_item(row: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    for evidence in row["content_locations"]:
        rule = evidence["rule"]
        if rule not in grouped:
            grouped[rule] = {
                "rule": rule,
                "content_kind": evidence["content_kind"],
                "description": evidence["description"],
                "suggested_data_target": evidence["suggested_data_target"],
                "locations": [],
            }
        grouped[rule]["locations"].append(
            {
                "line": evidence["line"],
                "text": evidence["text"],
                "matched": evidence["matched"],
            }
        )
    return {
        "path": row["path"],
        "classification": row["classification"],
        "reason": row["classification_reason"],
        "estimated_difficulty": row["estimated_difficulty"],
        "suggested_data_targets": row["suggested_data_targets"],
        "work_package": row["work_package"],
        "content": [grouped[key] for key in sorted(grouped)],
    }


def build_extraction_worklist(inventory: dict[str, Any]) -> dict[str, Any]:
    """Build non-overlapping extraction packages from measured source evidence."""
    code_rows = [row for row in inventory["files"] if row["scope"] == "embedded_code"]
    pending_rows = [
        row for row in code_rows
        if row["classification"] not in {"persisted_identifier", "product_shell_allowed"}
    ]
    allowed_rows = [
        row for row in code_rows
        if row["classification"] in {"persisted_identifier", "product_shell_allowed"}
    ]
    packages = []
    assigned_paths = []
    for definition in WORK_PACKAGE_DEFINITIONS:
        files = sorted(
            row["path"]
            for row in pending_rows
            if row["work_package"] == definition["id"]
        )
        if not files:
            continue
        assigned_paths.extend(files)
        packages.append(
            {
                "id": definition["id"],
                "titles": list(definition["titles"]),
                "objective": definition["objective"],
                "exclusions": definition["exclusions"],
                "file_count": len(files),
                "exclusive_files": files,
            }
        )
    expected_paths = sorted(row["path"] for row in pending_rows)
    if sorted(assigned_paths) != expected_paths or len(assigned_paths) != len(set(assigned_paths)):
        raise ValueError("Extraction work packages must cover each pending file exactly once.")
    by_path = {row["path"]: row for row in code_rows}
    declared_allowlist = []
    for entry in inventory["product_shell_allowlist"]:
        row = by_path.get(entry["path"])
        if row is None:
            status = "no_current_content_evidence"
        elif row["classification"] == "product_shell_allowed":
            status = "allowed_content_present"
        else:
            status = "contains_extraction_content"
        declared_allowlist.append({**entry, "status": status})
    hint_only_count = sum(
        row["status"] == "review_hint_only"
        for row in inventory["manual_review_hints"]
    )
    classification_counts = Counter(row["classification"] for row in code_rows)
    return {
        "schema": "mohan.character-extraction-worklist.v1",
        "schema_version": 1,
        "source_inventory": "docs/character-pack/mohan-inventory.json",
        "purpose": "measured_parallel_extraction_assignment",
        "counts": {
            "actual_embedded_code_files": len(code_rows),
            "true_extraction_files": len(pending_rows),
            "engine_extract_files": classification_counts["engine_extract"],
            "ui_text_reference_files": classification_counts["ui_text_reference"],
            "product_shell_allowed_files": len(allowed_rows),
            "persisted_identifier_files": classification_counts["persisted_identifier"],
            "manual_review_hint_only_files": hint_only_count,
            "work_packages": len(packages),
        },
        "classification_definitions": dict(CLASSIFICATION_REASONS),
        "extraction_items": [_worklist_item(row) for row in pending_rows],
        "product_shell_allowed": [_worklist_item(row) for row in allowed_rows],
        "declared_product_shell_allowlist": declared_allowlist,
        "work_packages": packages,
        "owner_decisions": dict(inventory["owner_decisions"]),
    }


def render_extraction_worklist(worklist: dict[str, Any]) -> str:
    return json.dumps(worklist, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_extraction_summary(worklist: dict[str, Any]) -> str:
    counts = worklist["counts"]
    package_rows = worklist["work_packages"]
    allowed_paths = [row["path"] for row in worklist["product_shell_allowed"]]
    sections = (
        (
            "繁體中文",
            f"實測後，真正仍需搬離引擎或改由角色資料代入的程式檔有 {counts['true_extraction_files']} 個：引擎抽離 {counts['engine_extract_files']} 個、介面名稱參照 {counts['ui_text_reference_files']} 個。另有 {counts['product_shell_allowed_files']} 個檔案屬墨寒產品殼，可按逐檔理由保留品牌內容。",
            f"舊名單另有 {counts['manual_review_hint_only_files']} 個檔案只剩人工複核提示，沒有實際內容規則證據，因此不計入待搬數。每個待搬檔只出現在下列一個獨占工作包。",
            "工作包", "獨占檔案數",
            "產品殼允許保留",
            "角色素材授權與 DLC 關係仍待擁有者決定；本清單不改變私有倉庫與獨立下載設計裁定。",
            "詳細證據與逐檔理由見 `extraction-worklist.json`。",
        ),
        (
            "简体中文",
            f"实测后，真正仍需从引擎移出或改为由角色数据代入的程序文件有 {counts['true_extraction_files']} 个：引擎抽离 {counts['engine_extract_files']} 个、界面名称引用 {counts['ui_text_reference_files']} 个。另有 {counts['product_shell_allowed_files']} 个文件属于墨寒产品壳，可按逐文件理由保留品牌内容。",
            f"旧名单另有 {counts['manual_review_hint_only_files']} 个文件只剩人工复核提示，没有实际内容规则证据，因此不计入待迁移数。每个待迁移文件只出现在下列一个独占工作包。",
            "工作包", "独占文件数",
            "产品壳允许保留",
            "角色素材授权与 DLC 关系仍待所有者决定；本清单不改变私有仓库和独立下载设计裁定。",
            "详细证据与逐文件理由见 `extraction-worklist.json`。",
        ),
        (
            "English",
            f"Measurement finds {counts['true_extraction_files']} source files that still need engine extraction or character-data substitution: {counts['engine_extract_files']} engine-extraction files and {counts['ui_text_reference_files']} UI-name references. Another {counts['product_shell_allowed_files']} files belong to the MoHan product shell and may retain branded content for their recorded per-file reasons.",
            f"The old list leaves {counts['manual_review_hint_only_files']} manual-review-only hints with no content-rule evidence; they are not counted as extraction work. Every pending file belongs to exactly one exclusive package below.",
            "Work package", "Exclusive files",
            "Allowed product-shell files",
            "Character-asset licensing and the DLC relationship still require the owner's decision; this list does not change the private-repository or independent-download decisions.",
            "See `extraction-worklist.json` for detailed evidence and per-file reasons.",
        ),
        (
            "日本語",
            f"実測の結果、エンジンからの抽出またはキャラクターデータによる差し替えが必要なソースは {counts['true_extraction_files']} ファイルです。内訳はエンジン抽出 {counts['engine_extract_files']}、UI の名前参照 {counts['ui_text_reference_files']} です。別に {counts['product_shell_allowed_files']} ファイルは墨寒製品シェルに属し、ファイルごとの理由に従ってブランド内容を保持できます。",
            f"旧一覧には実内容の規則証拠がない人工確認専用の候補が {counts['manual_review_hint_only_files']} ファイル残りますが、抽出数には含めません。各対象ファイルは以下の独占作業パッケージ一つだけに属します。",
            "作業パッケージ", "独占ファイル数",
            "製品シェルで保持可能",
            "キャラクター素材のライセンスと DLC の関係は所有者の決定待ちです。本一覧は非公開リポジトリと独立ダウンロード設計の決定を変更しません。",
            "詳細な証拠とファイルごとの理由は `extraction-worklist.json` を参照してください。",
        ),
    )
    parts = ["# 角色內容抽離待辦摘要／角色内容抽离待办摘要／Character Extraction Worklist Summary／キャラクター内容抽出一覧\n"]
    for locale, section in enumerate(sections):
        (
            language,
            result,
            hints,
            package_header,
            count_header,
            allowed_header,
            decisions,
            details,
        ) = section
        rows = [
                f"| {package['titles'][locale]} (`{package['id']}`) | {package['file_count']} |"
            for package in package_rows
        ]
        allowed = "、".join(f"`{path}`" for path in allowed_paths)
        parts.append(
            f"## {language}\n\n{result}\n\n{hints}\n\n"
            f"| {package_header} | {count_header} |\n|---|---:|\n"
            + "\n".join(rows)
            + f"\n\n### {allowed_header}\n\n{allowed}\n\n{decisions}\n\n"
            + details
            + "\n"
        )
    return "\n".join(parts)


def render_summary(inventory: dict[str, Any]) -> str:
    """Render parallel owner-facing summaries from the same measured counts."""
    counts = inventory["runtime_file_counts"]
    code_count = inventory["scope_counts"]["embedded_code"]
    classifications = inventory["embedded_code_classification_counts"]
    extraction_count = (
        classifications.get("engine_extract", 0)
        + classifications.get("ui_text_reference", 0)
    )
    allowed_count = (
        classifications.get("persisted_identifier", 0)
        + classifications.get("product_shell_allowed", 0)
    )
    hint_only_count = sum(
        row["status"] == "review_hint_only"
        for row in inventory["manual_review_hints"]
    )
    runtime_physical = sum(row["scope"] == "runtime_data" and "!" not in row["path"] for row in inventory["files"])
    archive_members = sum(row["scope"] == "runtime_data" and "!" in row["path"] for row in inventory["files"])
    validation_count = inventory["scope_counts"]["product_validation_data"]
    excluded_count = sum(count for scope, count in inventory["scope_counts"].items() if scope.startswith("excluded_"))
    scope_details = (
        f"產品資料合計 {runtime_physical + validation_count} 個實體檔案：執行期 {runtime_physical} 個，產品自測必需 {validation_count} 個（landmarks 與 hands 中繼資料）。兩個外觀包的 {archive_members} 個內部成員另列細項，已包含在封存包內，不重複計算實體檔案。另有 {excluded_count} 個排除檔案與 {code_count} 個程式定位檔。下表只計執行期實體檔案。",
        f"产品数据合计 {runtime_physical + validation_count} 个实体文件：运行时 {runtime_physical} 个，产品自测必需 {validation_count} 个（landmarks 与 hands 元数据）。两个外观包的 {archive_members} 个内部成员另列细项，已包含在归档包内，不重复计算实体文件。另有 {excluded_count} 个排除文件和 {code_count} 个程序定位文件。下表只计运行时实体文件。",
        f"Product data totals {runtime_physical + validation_count} physical files: {runtime_physical} runtime files and {validation_count} required self-test sidecars (landmarks and hands). The {archive_members} members inside two appearance archives are indexed separately and already included in those archives. There are also {excluded_count} excluded files and {code_count} source-location files. The table counts runtime physical files only.",
        f"製品データは実ファイル {runtime_physical + validation_count} 個です。実行時に {runtime_physical} 個、製品自己テストに landmarks と hands のメタデータ {validation_count} 個が必要です。外観アーカイブ 2 個に含まれる {archive_members} メンバーは別途列挙し、実ファイル数には重複計上しません。除外ファイル {excluded_count} 個とコード位置ファイル {code_count} 個も記録します。下表は実行時の実ファイルのみを数えます。",
    )
    appearance_counts = Counter(item["category"] for item in inventory["appearance_catalog"])
    look, hair, headwear, makeup = (appearance_counts[key] for key in ("looks", "hairstyles", "headwear", "makeup"))
    appearance_details = (
        f"正式包內點名：服裝項目 {look}、髮型項目 {hair}、髮飾項目 {headwear}、妝容項目 {makeup}。變體與四語名稱見清冊 appearance_catalog。",
        f"正式包内列明：服装项目 {look}、发型项目 {hair}、发饰项目 {headwear}、妆容项目 {makeup}。变体与四语名称见清册 appearance_catalog。",
        f"Official archives declare {look} garment, {hair} hairstyle, {headwear} headwear and {makeup} makeup item. Variants and names are indexed in appearance_catalog.",
        f"正式パック内には衣装 {look}、髪型 {hair}、髪飾り {headwear}、メイク {makeup} 項目があります。差分と四言語の名称は appearance_catalog に記録します。",
    )
    sections = (
        ("繁體中文", "這份清冊逐檔點名既有內容，供後續拆分接線。現行素體 24 張、核心圖層 600 張；衍生圖 234 張＝眨眼 24、可見手部 8、完整表情影格 156、替換遮罩 13、口腔遮罩 33。", "類別", "檔案數", f"實際內容規則找到 {code_count} 個程式檔；其中真正待搬或參數化 {extraction_count} 個，產品殼允許保留 {allowed_count} 個。舊名單另有 {hint_only_count} 個檔案只有人工提示、沒有實際內容證據，不計入進度。每筆證據都保存行號、內容與規則名。", "圖片、JSON 與兩個正式外觀封存包是純資料；髮型與髮飾在包內、核心圖層與正式原生衣裝中逐項列出。搬資料時仍需調整讀取路徑，這次只列清冊。", "v4 一代校準、artifacts 候選、.quality-tmp 暫存、docs/release-evidence 審閱證據、tests/golden 回歸證據、製作鏡像與未引用審閱原圖都不進產品包；完整機器分類見 non_product_roots。reviewed-garments 與 source-bound-exasperated 內被正式載入或驗證的資料保留。", "角色包自開始就支援獨立下載；墨寒角色包放在私有倉庫（擁有者 2026-10-05 裁定）；角色素材授權及 DLC 關係待擁有者決定。引擎與炎劍畫譜採 MIT。既有使用者設定與外觀核准保持原範圍。"),
        ("简体中文", "本清册逐文件列出现有内容，供后续拆分接线。现行素体 24 张、核心图层 600 张；衍生图 234 张＝眨眼 24、可见手部 8、完整表情帧 156、替换遮罩 13、口腔遮罩 33。", "类别", "文件数", f"实际内容规则找到 {code_count} 个程序文件；其中真正待迁移或参数化 {extraction_count} 个，产品壳允许保留 {allowed_count} 个。旧名单另有 {hint_only_count} 个文件只有人工提示、没有实际内容证据，不计入进度。每条证据都保存行号、内容与规则名。", "图片、JSON 和两个正式外观封存包是纯数据；发型与发饰在包内、核心图层和正式原生衣装中逐项列出。搬数据时仍需调整读取路径，本次只列清册。", "v4 一代校准、artifacts 候选、.quality-tmp 暂存、docs/release-evidence 审阅证据、tests/golden 回归证据、制作镜像和未引用审阅原图均不进入产品包；完整机器分类见 non_product_roots。reviewed-garments 与 source-bound-exasperated 中正式加载或验证的数据予以保留。", "角色包从开始就支持独立下载；墨寒角色包放在私有仓库（所有者 2026-10-05 裁定）；角色素材授权及 DLC 关系待所有者决定。引擎与炎剑画谱采用 MIT。现有用户设置与外观批准保持原范围。"),
        ("English", "This measured index names existing content for subsequent extraction. There are 24 master views, 600 core layers and 234 derivatives: 24 blinks, 8 visible hands, 156 complete expression frames, 13 replacement masks and 33 oral masks.", "Category", "Files", f"Actual-content rules find {code_count} source files: {extraction_count} require extraction or parameterization and {allowed_count} are allowed product-shell files. Another {hint_only_count} files appear only as manual hints with no actual-content evidence and do not count toward progress. Every evidence item records a line, content and rule name.", "Images, JSON and two official appearance archives are data. Hairstyles and headwear are indexed within archives, core layers and native garments. Moving data still requires changing reader paths; this step only inventories it.", "Generation-1 v4 calibration, artifacts candidates, .quality-tmp temporaries, docs/release-evidence reviews, tests/golden regression evidence, authoring mirrors and unreferenced review originals stay outside the product pack; non_product_roots records the machine-readable boundary. Formally loaded or verified reviewed-garments and source-bound-exasperated data remains included.", "Independent download is a design requirement from inception. The MoHan character pack lives in a private repository (owner decision, 2026-10-05); character asset licensing and DLC relationships await owner decisions. The engine and art tool use MIT. Existing user settings and appearance approvals retain their scope."),
        ("日本語", "この実測一覧は今後の分離に向け既存の内容を列挙します。主視点 24 枚、主要レイヤー 600 枚、派生画像 234 枚です。内訳は瞬き 24、可視の手 8、完全表情フレーム 156、置換マスク 13、口腔マスク 33 です。", "分類", "ファイル数", f"実内容の規則により {code_count} ソースファイルを検出しました。抽出またはパラメータ化が必要なのは {extraction_count}、製品シェルで保持可能なのは {allowed_count} ファイルです。旧一覧のうち {hint_only_count} ファイルは実内容の証拠がない人工確認専用の候補であり、進捗には数えません。各証拠に行番号、内容、規則名を保存します。", "画像、JSON、正式な外観アーカイブ 2 個はデータです。髪型と髪飾りはアーカイブ、主要レイヤー、正式な衣装内で列挙します。移動時には読込先の変更も必要で、この段階は一覧作成のみです。", "v4 の第一世代校正、artifacts の候補、.quality-tmp の一時出力、docs/release-evidence の審査証拠、tests/golden の回帰証拠、制作ミラー、未参照の審査原画は製品パックに含めません。機械可読の境界は non_product_roots に記録します。reviewed-garments と source-bound-exasperated の正式に読込または検証するデータは含めます。", "独立ダウンロードは当初からの設計要件です。墨寒キャラクターパックは非公開リポジトリに置きます（所有者決定、2026-10-05）。素材ライセンスと DLC との関係は所有者の決定待ちです。エンジンと素材管理ツールは MIT を採用します。既存の設定と外観承認の範囲を維持します。"),
    )
    parts = ["# 墨寒角色內容清冊摘要／墨寒角色内容清册摘要／MoHan Character Inventory Summary／墨寒キャラクター内容一覧\n"]
    for locale, (language, intro, category, files, code, data, exclusions, decisions) in enumerate(sections):
        rows = "\n".join(f"| {CATEGORY_LABELS[key].split('／')[locale]} (`{key}`) | {count} |" for key, count in counts.items())
        parts.append(f"## {language}\n\n{intro}\n\n{scope_details[locale]}\n\n| {category} | {files} |\n|---|---:|\n{rows}\n\n{appearance_details[locale]}\n\n{code}\n\n{data}\n\n{exclusions}\n\n{decisions}\n\n`mohan-inventory.json` · `python tools/build_character_inventory.py --check`\n")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/character-pack")
    args = parser.parse_args(argv)
    inventory = build_inventory()
    worklist = build_extraction_worklist(inventory)
    outputs = {
        "mohan-inventory.json": render_inventory(inventory),
        "mohan-inventory-summary.md": render_summary(inventory),
        "extraction-worklist.json": render_extraction_worklist(worklist),
        "extraction-worklist.md": render_extraction_summary(worklist),
    }
    if args.check:
        for name, expected in outputs.items():
            path = args.output_dir / name
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                print(f"CHARACTER_INVENTORY_STALE={name}")
                return 1
        print("CHARACTER_INVENTORY_MATCH")
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, text in outputs.items():
        (args.output_dir / name).write_text(text, encoding="utf-8", newline="\n")
    print("CHARACTER_INVENTORY_WRITTEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
