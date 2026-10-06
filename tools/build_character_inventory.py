"""Inventory existing MoHan data and embedded content without importing runtime code.

This is an engineering index, not a pack builder or a distribution permission.
Reader anchors are verified against source on every run. Unreferenced files stay
outside the proposed payload; provenance paths do not become runtime dependencies.
"""

from __future__ import annotations

lazy import argparse
lazy import ast
lazy import hashlib
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

ROOT = Path(__file__).resolve().parents[1]
DIRECT = "純資料可直接搬"
EMBEDDED = "被程式寫死需先改"
SOURCE_ROOTS = ("domain", "application", "infrastructure", "integrations", "presentation")
IMAGE_SUFFIXES = frozenset({".png", ".ico", ".webp", ".gif", ".jpg", ".jpeg"})
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
    "ui_onboarding": "初次設定角色圖／首次设置角色图／Onboarding character image／初回設定のキャラクター画像",
}


@dataclass(frozen=True)
class Group:
    prefix: str
    category: str
    reader: str
    anchor: str


# Most-specific prefix wins. Each anchor names the real read or composition site.
GROUPS = (
    Group("assets/pose-atlas/v5-base/", "fullbody_master", "presentation/pose_atlas_assets.py", 'self._root / f"{view_id}.png"'),
    Group("assets/pose-atlas/v5-base-layered/", "fullbody_core_layer", "infrastructure/layered_full_body_assets.py", 'root / f"{view_id}_{layer}.png"'),
    Group("assets/pose-atlas/v5-garment-visibility/", "garment_visibility", "infrastructure/source_bound_garment_visibility.py", "MANIFEST ="),
    Group("assets/pose-atlas/v5-appearance-replacement-masks/", "appearance_replacement_mask", "infrastructure/active_outfit_overlay_layers.py", '"assets/pose-atlas/v5-appearance-replacement-masks"'),
    Group("assets/pose-atlas/v5-appearance-silhouettes/", "appearance_silhouette", "infrastructure/active_outfit_overlay_layers.py", '"assets/pose-atlas/v5-appearance-silhouettes"'),
    Group("assets/pose-atlas/v5-body-overlays/", "body_overlay", "infrastructure/active_outfit_overlay_layers.py", '"assets/pose-atlas/v5-body-overlays"'),
    Group("assets/pose-atlas/v5-hand-overlays/", "hand_overlay", "infrastructure/active_outfit_overlay_layers.py", '"assets/pose-atlas/v5-hand-overlays"'),
    Group("assets/expressions/complete-expressions/", "halfbody_complete_expression", "infrastructure/complete_halfbody_expressions.py", "data = path.read_bytes()"),
    Group("assets/expressions/reviewed-garments/", "native_garment_motion", "infrastructure/reviewed_garment_assets.py", "payload = path.read_bytes()"),
    Group("assets/expressions/source-bound-exasperated/", "source_bound_expression", "infrastructure/exasperated_candidate_assets.py", "records = receipt.get(\"installed_files_sha256\")"),
    Group("assets/expressions/layered/", "halfbody_layer", "infrastructure/layered_face_assets.py", 'root / f"{pose.value}_{layer}.png"'),
    Group("assets/expressions/", "halfbody_expression", "presentation/companion_visual_dynamics.py", 'resource_path(f"assets/expressions/{expression}.png")'),
    Group("assets/official-packs/", "appearance_pack", "application/service_container.py", 'official_pack_root = asset_root / "assets" / "official-packs"'),
    Group("assets/makeup-eye-apertures/", "makeup_eye_aperture", "domain/outfit_pack_makeup.py", "data = mask_path.read_bytes()"),
    Group("assets/makeup-foundation-safe-regions/", "makeup_foundation_mask", "domain/outfit_pack_makeup.py", "data = mask_path.read_bytes()"),
    Group("assets/makeup-safe-regions/", "makeup_safe_mask", "domain/outfit_pack_makeup.py", "data = mask_path.read_bytes()"),
    Group("assets/makeup/", "makeup_authoring_mirror", "application/service_container.py", 'official_pack_root = asset_root / "assets" / "official-packs"'),
    Group("assets/makeup-safe-regions.json", "makeup_region_rules", "domain/outfit_pack_makeup.py", 'SAFE_REGION_FILE = "makeup-safe-regions.json"'),
    Group("assets/mohan-halfbody.ico", "ui_character_icon", "infrastructure/app_resources.py", 'APP_ICON_PATH = "assets/mohan-halfbody.ico"'),
    Group("assets/onboarding/", "ui_onboarding", "presentation/first_run_wizard.py", '"assets/onboarding/first-run-ink-tech.png"'),
    Group("assets/ui/mohan-celestial-palace-v1.png", "ui_background", "presentation/dashboard_artwork.py", "ARTWORK_PATH ="),
    Group("assets/ui/mohan-strategist-lobby-v1.png", "ui_background", "presentation/lingxiao_shell.py", "_LOBBY_BACKDROP ="),
    Group("assets/ui/mohan-cloud.svg", "ui_brand_decoration", "presentation/flagship_theme.py", "_THEME_ASSET ="),
)

CODE_CATEGORIES = {
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
    result: dict[str, Any] = {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
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


def _code_records(root: Path) -> list[dict[str, Any]]:
    categories: dict[str, set[str]] = {}
    sources: dict[str, str] = {}
    for category, paths in CODE_CATEGORIES.items():
        for path in paths:
            categories.setdefault(path, set()).add(category)
    for directory in SOURCE_ROOTS:
        for path in sorted((root / directory).rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            sources[path.relative_to(root).as_posix()] = text
            if re.search(r"墨寒|主上|赤焰|MOHAN_EMOTION|coral|Yating", text):
                categories.setdefault(path.relative_to(root).as_posix(), set()).add("character_literal_sites")
    for path in sorted(root.glob("*.py")):
        sources[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    records = []
    for path, groups in sorted(categories.items()):
        text = (root / path).read_text(encoding="utf-8")
        lines = text.splitlines()
        # Index complete definition ranges as well as literal sites: English and
        # Japanese dialogue can span many lines and need their containing symbol.
        tree = ast.parse(re.sub(r"(?m)^(\s*)lazy (import |from )", r"\1\2", text))
        symbols = [{"name": node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else ast.unparse(node.targets[0] if isinstance(node, ast.Assign) else node.target), "line": node.lineno, "end_line": node.end_lineno} for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign))]
        evidence = [{"path": path, "line": number, "text": line.strip()} for number, line in enumerate(lines, 1) if re.search(r"墨寒|主上|赤焰|MoHan|MOHAN_|coral|Yating|DEFAULT_|PROMPT|EXPRESSION_|POSE_|VOICE|CANONICAL_YAWS|BODY_PROFILE|LAYER_Z_ORDER", line)]
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
        records.append({"path": path, "category": "embedded_character_content", "content_categories": sorted(groups), "scope": "embedded_code", "migration": EMBEDDED, "readers": consumers, "content_locations": evidence, "symbols": symbols, "note": "整個模組只作定位證據；通用邏輯留引擎，角色字串、預設值與規則需按 symbol 分流；readers 列靜態匯入者，事件內使用可查 symbol", **file_metadata(root / path)})
    return records


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
    records.extend(_code_records(root))
    records.sort(key=lambda row: row["path"])
    counts = Counter(row["category"] for row in records if row["scope"] == "runtime_data" and "!" not in row["path"])
    return {
        "schema": "mohan.character-inventory.v1", "schema_version": 1,
        "purpose": "existing_content_index_only",
        "owner_decisions": {"standalone_download_design": True, "pack_visibility": "private_repository", "character_asset_license": "owner_decision_pending", "dlc_relationship": "owner_decision_pending", "engine_license": "MIT", "art_tool_license": "MIT"},
        "scope_notes": ["runtime_data 包含正常與選配正式讀取；不是目前某一影格的追蹤", "embedded_code 是定位清冊，不可執行碼角色包內容", "readers 的 line 與 text 指向讀取或模板；manifest_references 點名精確宣告", "封存、製作鏡像、審閱原圖與來源 sidecar 均明確排除；既有核准 scope 沿用", "scratchpad、artifacts、.quality-tmp、docs/release-evidence、tests/golden 全樹不屬產品包輸入"],
        "non_product_roots": [dict(row) for row in NON_PRODUCT_ROOTS],
        "runtime_file_counts": dict(sorted(counts.items())),
        "appearance_catalog": appearance_catalog,
        "scope_counts": dict(sorted(Counter(row["scope"] for row in records).items())),
        "files": records,
    }


def render_inventory(inventory: dict[str, Any]) -> str:
    return json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_summary(inventory: dict[str, Any]) -> str:
    """Render parallel owner-facing summaries from the same measured counts."""
    counts = inventory["runtime_file_counts"]
    code_count = inventory["scope_counts"]["embedded_code"]
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
        ("繁體中文", "這份清冊逐檔點名既有內容，供後續拆分接線。現行素體 24 張、核心圖層 600 張；衍生圖 234 張＝眨眼 24、可見手部 8、完整表情影格 156、替換遮罩 13、口腔遮罩 33。", "類別", "檔案數", f"有 {code_count} 個程式檔包含角色內容或規則，需先按清冊的 symbol 與行號改成讀資料：名字、稱謂、人格與系統提示、提醒與節日台詞、聲音偏好、角度、表情、姿勢、嘴型與圖層順序。清冊也搜尋額外角色字串位置；整個模組不等於全部要搬。", "圖片、JSON 與兩個正式外觀封存包是純資料；髮型與髮飾在包內、核心圖層與正式原生衣裝中逐項列出。搬資料時仍需調整讀取路徑，這次只列清冊。", "v4 一代校準、artifacts 候選、.quality-tmp 暫存、docs/release-evidence 審閱證據、tests/golden 回歸證據、製作鏡像與未引用審閱原圖都不進產品包；完整機器分類見 non_product_roots。reviewed-garments 與 source-bound-exasperated 內被正式載入或驗證的資料保留。", "角色包自開始就支援獨立下載；墨寒角色包放在私有倉庫（擁有者 2026-10-05 裁定）；角色素材授權及 DLC 關係待擁有者決定。引擎與炎劍畫譜採 MIT。既有使用者設定與外觀核准保持原範圍。"),
        ("简体中文", "本清册逐文件列出现有内容，供后续拆分接线。现行素体 24 张、核心图层 600 张；衍生图 234 张＝眨眼 24、可见手部 8、完整表情帧 156、替换遮罩 13、口腔遮罩 33。", "类别", "文件数", f"有 {code_count} 个程序文件包含角色内容或规则，需要按清册的 symbol 和行号改为读取数据：名字、称谓、人格与系统提示、提醒与节日台词、声音偏好、角度、表情、姿势、嘴型与图层顺序。清册也搜索额外角色字符串位置；整个模块不等于全部要搬。", "图片、JSON 和两个正式外观封存包是纯数据；发型与发饰在包内、核心图层和正式原生衣装中逐项列出。搬数据时仍需调整读取路径，本次只列清册。", "v4 一代校准、artifacts 候选、.quality-tmp 暂存、docs/release-evidence 审阅证据、tests/golden 回归证据、制作镜像和未引用审阅原图均不进入产品包；完整机器分类见 non_product_roots。reviewed-garments 与 source-bound-exasperated 中正式加载或验证的数据予以保留。", "角色包从开始就支持独立下载；墨寒角色包放在私有仓库（所有者 2026-10-05 裁定）；角色素材授权及 DLC 关系待所有者决定。引擎与炎剑画谱采用 MIT。现有用户设置与外观批准保持原范围。"),
        ("English", "This measured index names existing content for subsequent extraction. There are 24 master views, 600 core layers and 234 derivatives: 24 blinks, 8 visible hands, 156 complete expression frames, 13 replacement masks and 33 oral masks.", "Category", "Files", f"{code_count} source files contain character content or rules. Use indexed symbols and lines to extract names, titles, persona and system prompts, reminders and occasion dialogue, voice preferences, angles, expressions, poses, mouth geometry and layer order. Additional character literals are searched; entire modules are not extraction payloads.", "Images, JSON and two official appearance archives are data. Hairstyles and headwear are indexed within archives, core layers and native garments. Moving data still requires changing reader paths; this step only inventories it.", "Generation-1 v4 calibration, artifacts candidates, .quality-tmp temporaries, docs/release-evidence reviews, tests/golden regression evidence, authoring mirrors and unreferenced review originals stay outside the product pack; non_product_roots records the machine-readable boundary. Formally loaded or verified reviewed-garments and source-bound-exasperated data remains included.", "Independent download is a design requirement from inception. The MoHan character pack lives in a private repository (owner decision, 2026-10-05); character asset licensing and DLC relationships await owner decisions. The engine and art tool use MIT. Existing user settings and appearance approvals retain their scope."),
        ("日本語", "この実測一覧は今後の分離に向け既存の内容を列挙します。主視点 24 枚、主要レイヤー 600 枚、派生画像 234 枚です。内訳は瞬き 24、可視の手 8、完全表情フレーム 156、置換マスク 13、口腔マスク 33 です。", "分類", "ファイル数", f"{code_count} 個のソースファイルにキャラクター内容や規則があります。symbol と行番号に従い、名前、呼称、人格とシステムプロンプト、通知と行事の台詞、声の好み、角度、表情、姿勢、口の形とレイヤー順をデータ化します。追加の文字列も検索し、モジュール全体を移行対象とは扱いません。", "画像、JSON、正式な外観アーカイブ 2 個はデータです。髪型と髪飾りはアーカイブ、主要レイヤー、正式な衣装内で列挙します。移動時には読込先の変更も必要で、この段階は一覧作成のみです。", "v4 の第一世代校正、artifacts の候補、.quality-tmp の一時出力、docs/release-evidence の審査証拠、tests/golden の回帰証拠、制作ミラー、未参照の審査原画は製品パックに含めません。機械可読の境界は non_product_roots に記録します。reviewed-garments と source-bound-exasperated の正式に読込または検証するデータは含めます。", "独立ダウンロードは当初からの設計要件です。墨寒キャラクターパックは非公開リポジトリに置きます（所有者決定、2026-10-05）。素材ライセンスと DLC との関係は所有者の決定待ちです。エンジンと素材管理ツールは MIT を採用します。既存の設定と外観承認の範囲を維持します。"),
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
    outputs = {"mohan-inventory.json": render_inventory(inventory), "mohan-inventory-summary.md": render_summary(inventory)}
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
