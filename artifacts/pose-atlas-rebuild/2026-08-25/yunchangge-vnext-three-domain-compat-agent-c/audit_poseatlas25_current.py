from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
MANIFEST = ROOT / "assets/pose-atlas/v4-layered/layer_manifest.json"
QA = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/v4-600-ownership-color-qa-agent-c/yaw000-ownership-color-qa.json"

LAYERS = (
    "base", "jaw", "oral_cavity", "teeth_tongue", "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
    "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left",
    "eyeliner_right", "brow_left", "brow_right", "body", "hair_back",
    "hair_left", "hair_right", "sleeve_left", "sleeve_right", "ornament",
)

SOURCES = {
    "outfit_pack": ("domain/outfit_pack.py", [[16, 31], [46, 70], [97, 109], [117, 168], [374, 451], [670, 680]]),
    "overlay": ("infrastructure/active_outfit_overlay.py", [[32, 74], [106, 230], [288, 308]]),
    "builder": ("application/outfit_pack_builder.py", [[43, 118]]),
    "wardrobe": ("application/self_generating_wardrobe.py", [[23, 35], [183, 216], [240, 265], [310, 375]]),
    "generator": ("integrations/openai_outfit_generator.py", [[317, 318], [398, 460], [517, 525], [575, 614], [658, 755]]),
    "atlas_loader": ("infrastructure/layered_full_body_assets.py", [[1, 12], [29, 51], [84, 112]]),
    "atlas_renderer": ("infrastructure/layered_full_body_renderer.py", [[40, 43], [52, 67], [111, 155]]),
    "constants": ("domain/constants.py", [[125, 151]]),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    qa = json.loads(QA.read_text(encoding="utf-8"))
    views = manifest.get("views", [])
    layer_lists = [[record.get("layer") for record in view.get("layers", [])] for view in views]
    records = sum(map(len, layer_lists))
    yaw000 = qa["results"][0]["layers"]

    source_evidence = []
    for source_id, (relative, ranges) in SOURCES.items():
        path = ROOT / relative
        source_evidence.append({
            "id": source_id,
            "path": relative,
            "sha256": digest(path),
            "line_ranges": ranges,
        })
    source_evidence.extend([
        {"id": "pose_atlas_manifest", "path": MANIFEST.relative_to(ROOT).as_posix(), "sha256": digest(MANIFEST), "line_ranges": [[2, 43], [392, 608], [19046, 19046]]},
        {"id": "yaw000_ownership_qa", "path": QA.relative_to(ROOT).as_posix(), "sha256": digest(QA), "truth_boundary": "color evidence only; not semantic segmentation"},
    ])

    compatibility = [
        {"poseatlas": "body", "target": "core_skin + body_geometry + hands + feet", "status": "BLOCKED_WELDED", "evidence": "domain/constants.py:127 calls it torso + clothing base; renderer lines 40-43 says arms/hands are included; yaw+000 has garment/shoe color evidence"},
        {"poseatlas": "base/jaw/facial layers", "target": "protected_identity", "status": "PARTIAL", "evidence": "overlay lines 288-308 uses base alpha as protected face, but it is not a versioned ownership mask"},
        {"poseatlas": "hair_back/hair_left/hair_right", "target": "core_hair + hair_occlusion", "status": "PARTIAL", "evidence": "hair pack supports face/hand/garment occlusion, but atlas has no ownership fields"},
        {"poseatlas": "sleeve_left/sleeve_right", "target": "sleeve-left/sleeve-right", "status": "ADAPTER_REQUIRED", "evidence": "semantic match; underscore/hyphen differs; hands remain baked into body"},
        {"poseatlas": "ornament", "target": "core_fixed_ornament", "status": "BLOCKED_MIXED_OWNER", "evidence": "yaw+000 QA detects face/skin and existing manual review confirms a complete face is included"},
        {"poseatlas": "missing torso/lower garment layers", "target": "outerwear/innerwear/bodice/skirt/trousers/garment occluders", "status": "BLOCKED_MISSING_LAYERS", "evidence": "25 layers contain only sleeves; torso/lower clothing remains in body"},
        {"poseatlas": "missing shoes", "target": "shoe-left/shoe-right", "status": "BLOCKED_MISSING_SLOTS", "evidence": "outfit pack v2 GARMENT_SLOTS has no shoe slots"},
    ]

    required_slots = {
        "core": ["core_skin", "body_geometry", "hand_left", "hand_right", "foot_left", "foot_right", "core_hair_back", "core_hair_left", "core_hair_right", "core_fixed_ornament"],
        "garment": ["outerwear", "innerwear", "bodice", "skirt", "trousers", "sleeve_left", "sleeve_right", "shoe_left", "shoe_right", "garment_occluder_back", "garment_occluder_front"],
        "replaceable_accessory": ["headwear", "jewelry", "weapon", "handheld", "foreground_effect"],
    }
    required_masks = [
        "protected_identity", "core_skin", "body_geometry", "hand_left", "hand_right",
        "foot_left", "foot_right", "outerwear", "innerwear", "skirt", "sleeve_left",
        "sleeve_right", "shoe_left", "shoe_right", "hair_occlusion",
        "core_fixed_ornament", "replaceable_headwear", "replaceable_jewelry",
        "garment_occluder_back", "garment_occluder_front",
    ]
    rights = [
        "origin_type", "creator", "rightsholder", "source_url", "source_revision",
        "source_asset_sha256", "derived_asset_sha256", "code_license_spdx",
        "model_weight_license_or_service_output_terms", "asset_license_spdx",
        "license_evidence_path_sha256", "commercial_use_allowed", "derivatives_allowed",
        "redistribution_allowed", "training_use_allowed", "modified",
        "modification_description", "notices_reference", "qa_status",
        "manual_approval_evidence",
    ]
    missing_top_level = sorted({
        "ownership_domains", "outfit_slots", "ownership_masks", "asset_provenance",
        "license_policy", "qa_status_by_asset",
    } - set(manifest))

    report = {
        "schema": "mohan.yunchangge.poseatlas25.compatibility-audit.v1",
        "status": "BLOCKED_NOT_WIRED",
        "exit_code": 4,
        "formal_code_modified": False,
        "formal_assets_modified": False,
        "promotion_allowed": False,
        "atlas": {
            "views": len(views), "records": records,
            "declared_records": manifest.get("layer_record_count"),
            "exact_25_layers_each": all(tuple(item) == LAYERS for item in layer_lists),
            "layers": list(LAYERS), "missing_vnext_top_level_fields": missing_top_level,
        },
        "runtime": {
            "loads_layer_manifest_json": False,
            "applies_outfit_after_base_composition": True,
            "can_remove_baked_clothing": False,
            "pack_license_gate": "syntax-only string validation, not evidence/allowlist validation",
        },
        "yaw000_pixel_evidence": {
            "body": {"sha256": yaw000["body"]["sha256"], "blue": yaw000["body"]["counts"]["blue_pixels"], "white": yaw000["body"]["counts"]["white_pixels"], "lower_white_shoe_proxy": yaw000["body"]["counts"]["lower_white_pixels"], "gate": yaw000["body"]["gate"]},
            "sleeve_left": {"sha256": yaw000["sleeve_left"]["sha256"], "fabric_proxy": yaw000["sleeve_left"]["counts"]["blue_pixels"] + yaw000["sleeve_left"]["counts"]["white_pixels"], "gate": yaw000["sleeve_left"]["gate"]},
            "sleeve_right": {"sha256": yaw000["sleeve_right"]["sha256"], "fabric_proxy": yaw000["sleeve_right"]["counts"]["blue_pixels"] + yaw000["sleeve_right"]["counts"]["white_pixels"], "gate": yaw000["sleeve_right"]["gate"]},
            "ornament": {"sha256": yaw000["ornament"]["sha256"], "skin_face_proxy": yaw000["ornament"]["counts"]["skin_like_pixels"], "gate": yaw000["ornament"]["gate"]},
        },
        "compatibility": compatibility,
        "required_vnext_slots": required_slots,
        "required_full_canvas_ownership_masks": required_masks,
        "ownership_mask_required_fields": ["path", "sha256", "mode", "view_id", "owner_domain", "offset", "alpha_policy", "soft_edge_policy", "allowed_overlap_with", "source_evidence_sha256", "qa_status"],
        "ownership_mask_gates": ["1024x1536 full-canvas registered at [0,0]", "one primary owner per pixel", "all overlaps declared and z-ordered", "garment never paints protected identity/core skin", "approved-master recomposition exact or explicitly bounded"],
        "required_rights_provenance_fields": rights,
        "minimum_migration": ["create clean core skin/body/hands/feet", "split torso/lower garments and shoes", "separate fixed ornament from replaceable headwear/jewelry", "add ownership/occlusion masks and rights evidence", "make runtime consume versioned manifest", "gate DLC swap and master recomposition before promotion"],
        "source_evidence": source_evidence,
    }

    output_json = HERE / "yunchangge-poseatlas25-current-compatibility.json"
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = f"""# 雲裳閣 ↔ 25 層 PoseAtlas 現況相容性（唯讀）

## 結論

`BLOCKED_NOT_WIRED`，退出碼 `4`。雲裳閣 pack 已有 31 視角、SHA/尺寸/anchor/z-order、隔離稽核與 runtime 疊圖；但它是在現有 25 層畫面合成後才疊新衣（`infrastructure/active_outfit_overlay.py:51-74`、`infrastructure/layered_full_body_renderer.py:111-155`），無法移除 `body` 已焊入的藍白衣與鞋。沒有修改正式程式、素材或 active selection。

## 實讀證據

- manifest：{len(views)} views、{records} records；每 view 25 層順序一致=`{all(tuple(item) == LAYERS for item in layer_lists)}`。
- loader 不讀 manifest，只按檔名找圖；且僅強制 body/hair/sleeves/ornament 七層（`infrastructure/layered_full_body_assets.py:29-51,84-112`）。
- `body` 的正式定義就是 torso + clothing base（`domain/constants.py:125-151`），renderer 又明寫 body 含 arms/hands（`infrastructure/layered_full_body_renderer.py:40-43`）。
- yaw+000 body：藍 {yaw000['body']['counts']['blue_pixels']:,}、白 {yaw000['body']['counts']['white_pixels']:,}、下緣白鞋 proxy {yaw000['body']['counts']['lower_white_pixels']:,}，故不能作 core skin。
- yaw+000 左/右 sleeve 布料 proxy 分別 {yaw000['sleeve_left']['counts']['blue_pixels'] + yaw000['sleeve_left']['counts']['white_pixels']:,}/{yaw000['sleeve_right']['counts']['blue_pixels'] + yaw000['sleeve_right']['counts']['white_pixels']:,}；它們是衣裝，不是手或人體核心。
- yaw+000 ornament 膚色/臉 proxy {yaw000['ornament']['counts']['skin_like_pixels']:,}，既有人工實開亦確認包含完整臉，不能作純髮飾 authority。

## 相容性與缺口

| 現況 | vNext/雲裳閣目標 | 判定 |
|---|---|---|
| body（人體＋衣＋鞋＋手） | core_skin/body_geometry/hands/feet | BLOCKED_WELDED |
| base/jaw/顏面層 | protected_identity | PARTIAL；需正式 ownership mask |
| hair_* | core_hair + occlusion | PARTIAL；缺 ownership/occlusion |
| sleeve_left/right | sleeve-left/right | 可映射但需命名 adapter；手須獨立 |
| ornament | core_fixed_ornament | BLOCKED_MIXED_OWNER |
| 無 torso/lower garment 層 | outer/inner/bodice/skirt/trousers | BLOCKED_MISSING_LAYERS |
| 無 shoe 層/pack slot | shoe-left/right | BLOCKED_MISSING_SLOTS |

## 可直接復用

- pack v2 強制 7 legacy + 24 yaw（`domain/outfit_pack.py:16-31,398-416`）。
- 現有 garment slots 已有 bodice/outerwear/sleeves/skirt/trousers/legwear/garment-occluder（`domain/outfit_pack.py:46-49`）。
- 每資產已有 path/SHA/尺寸/anchor/z-order；builder 封裝並驗證後原子替換（`domain/outfit_pack.py:117-125,374-395`; `application/outfit_pack_builder.py:43-118`）。
- 官方、使用者、雲端自創 pack 共用同一閘門（`infrastructure/active_outfit_overlay.py:32-38`），自創素材先隔離、稽核再安裝（`application/self_generating_wardrobe.py:183-216,310-368`）。

## 必須新增

1. core slots：skin/body geometry/左右手/左右腳/核心髮/固定髮簪。
2. garment slots：outer/inner/bodice/skirt/trousers/左右袖/左右鞋/front-back occluder。
3. 每 view 1024x1536、offset [0,0] 的 ownership masks，驗單一主 owner、宣告重疊、身份禁畫、重組差異。
4. 固定髮簪歸 core；可換 headwear/jewelry 另域。
5. 權利欄位需分開：程式授權、權重/服務輸出條款、素材授權、來源與衍生 SHA、商用/衍生/散布/訓練權限、修改、notices、QA、人工核准。現行 source 僅 kind/author/license/reference_included，而且 license 只做字串格式檢查（`domain/outfit_pack.py:670-680`）。
6. runtime 改讀 versioned manifest；目前 filename discovery 無法保證 ownership/provenance。

完整欄位、逐檔 SHA256 與行號範圍見 `yunchangge-poseatlas25-current-compatibility.json`。
"""
    (HERE / "YUNCHANGGE-POSEATLAS25-CURRENT-COMPATIBILITY.md").write_text(md, encoding="utf-8")
    print(json.dumps({"status": report["status"], "exit_code": 4, "report": str(output_json)}, ensure_ascii=False))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
