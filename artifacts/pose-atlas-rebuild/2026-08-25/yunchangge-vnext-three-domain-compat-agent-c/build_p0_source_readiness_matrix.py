"""Build a fail-closed inventory for the 73 P0 empty PoseAtlas layers.

This script reads existing evidence only.  It creates no image asset and never
edits the formal PoseAtlas manifest.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[4]
ARTIFACTS = PROJECT / "artifacts" / "pose-atlas-rebuild" / "2026-08-25"
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "p0-reusable-source-deterministic-matrix.json"
REPORT = HERE / "P0-REUSABLE-SOURCE-DETERMINISTIC-MATRIX.md"
WORKPACK = HERE / "p0-empty-layer-repair-workpack-index.json"

CONTROL_MANIFEST = ARTIFACTS / "candidate3-formal-controls-bundle-agent-a" / "formal-controls-manifest.json"
PART_MANIFEST = ARTIFACTS / "skin-weight-parts-agent-a" / "skin-weight-part-manifest.json"
RIGID_SOFT_MANIFEST = ARTIFACTS / "geometry-rigid-soft-masks-agent-a" / "geometry-rigid-soft-mask-manifest.json"
ANGLE_AUDIT = ARTIFACTS / "angle-pass-geometry-masters-agent-c" / "angle-geometry-master-audit.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def image_record(path: Path) -> dict[str, Any]:
    header = path.read_bytes()[:29]
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"not a PNG: {path}")
    width, height, bit_depth, colour_type = struct.unpack(">IIBB", header[16:26])
    modes = {0: "L", 2: "RGB", 3: "P", 4: "LA", 6: "RGBA"}
    mode = modes.get(colour_type, f"PNG_COLOR_TYPE_{colour_type}")
    size = [width, height]
    return {
        "path": path.relative_to(PROJECT).as_posix(),
        "sha256": sha256(path),
        "mode": mode,
        "size": size,
        "bit_depth": bit_depth,
    }


def candidate_map(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    items = audit["angle_pass_geometry_masters"] + audit["angle_fail_views_closest_bracket"]
    for item in items:
        result[item["view_id"]] = item
    return result


def resolve_candidate(relative: str) -> Path:
    return ARTIFACTS / relative


def main() -> int:
    workpack = load_json(WORKPACK)
    controls = load_json(CONTROL_MANIFEST)
    parts = load_json(PART_MANIFEST)
    rigid_soft = load_json(RIGID_SOFT_MANIFEST)
    angle = load_json(ANGLE_AUDIT)
    candidates = candidate_map(angle)

    packages: list[dict[str, Any]] = []
    for package in workpack["packages"]:
        view = package["view_id"]
        control_root = ARTIFACTS / "candidate3-formal-controls-bundle-agent-a" / "formal-controls"
        part_root = ARTIFACTS / "skin-weight-parts-agent-a" / "masks"
        rigid_root = ARTIFACTS / "geometry-rigid-soft-masks-agent-a" / "masks"
        candidate = candidates[view]
        candidate_path = resolve_candidate(candidate["selected_candidate"])
        if not candidate_path.is_file():
            raise FileNotFoundError(candidate_path)
        candidate_sha_matches = sha256(candidate_path) == candidate["sha256"]
        if not candidate_sha_matches:
            raise ValueError(f"candidate hash drift: {view}")

        is_angle_geometry_mother = candidate["angle_geometry_status"] == "PASS_GEOMETRY_MOTHER_ONLY"
        packages.append(
            {
                "workpack_id": package["workpack_id"],
                "view_id": view,
                "record_count": package["record_count"],
                "layer_ids": package["layer_ids"],
                "reusable_geometry_controls": {
                    "status": "REUSABLE_CONTROL_ONLY",
                    "source_status": controls["status"],
                    "depth": image_record(control_root / f"{view}_depth.png"),
                    "normal": image_record(control_root / f"{view}_normal.png"),
                    "silhouette": image_record(control_root / f"{view}_silhouette.png"),
                },
                "reusable_coarse_object_id": {
                    "status": "REUSABLE_COARSE_HEAD_BODY_CONTROL_ONLY",
                    "part_id": image_record(part_root / f"{view}_part-id.png"),
                    "sufficient_for_18_fine_face_layers": False,
                    "reason": "The admitted skin-weight part-ID has one coarse head region; eyes/teeth/tongue are unsupported and no per-lip/eyelid/brow/oral IDs exist.",
                },
                "reusable_geometry_rigid_soft": {
                    "status": "REUSABLE_DEFORMATION_CONTROL_ONLY",
                    "source_status": rigid_soft["status"],
                    "rigid": image_record(rigid_root / f"{view}_rigid.png"),
                    "soft": image_record(rigid_root / f"{view}_soft.png"),
                    "sufficient_for_fine_face_ownership": False,
                },
                "closest_existing_mother_candidate": {
                    "path": candidate_path.relative_to(PROJECT).as_posix(),
                    "sha256": candidate["sha256"],
                    "hash_verified": candidate_sha_matches,
                    "angle_geometry_status": candidate["angle_geometry_status"],
                    "full_art_pass": candidate["full_art_pass"],
                    "failed_items": candidate["failed_items"],
                    "unresolved_items": candidate["unresolved_items"],
                    "formal_pixel_authority": False,
                },
                "missing_formal_inputs": {
                    "accepted_same_view_mother_png": "MISSING",
                    "fine_face_object_id_or_verified_landmark_masks": "MISSING",
                    "dynamic_assets_by_layer": "MISSING",
                    "manual_art_acceptance": "MISSING",
                },
                "deterministic_readiness": (
                    "CONTROL_PREP_ONLY_NOT_PIXEL_REPAIR"
                    if is_angle_geometry_mother
                    else "BLOCKED_SOURCE_AND_ANGLE_OR_ART_GATE"
                ),
                "formal_repair_now": False,
                "promotion_allowed": False,
            }
        )

    matrix = {
        "schema": "mohan.pose-atlas.p0-reusable-source-deterministic-matrix.v1",
        "status": "BLOCKED_NO_ACCEPTED_SAME_VIEW_PIXEL_SOURCE_OR_FINE_FACE_MASKS",
        "promotion_allowed": False,
        "formal_manifest_modified": False,
        "png_assets_created": 0,
        "p0_record_count": workpack["expanded_record_count"],
        "immediately_repairable_formal_record_count": 0,
        "control_preparation_record_count": sum(
            p["record_count"] for p in packages if p["deterministic_readiness"] == "CONTROL_PREP_ONLY_NOT_PIXEL_REPAIR"
        ),
        "source_evidence": {
            "workpack": {"path": WORKPACK.relative_to(PROJECT).as_posix(), "sha256": sha256(WORKPACK)},
            "geometry_controls_manifest": {"path": CONTROL_MANIFEST.relative_to(PROJECT).as_posix(), "sha256": sha256(CONTROL_MANIFEST), "status": controls["status"], "formal_art_status": controls["formal_art_status"]},
            "part_id_manifest": {"path": PART_MANIFEST.relative_to(PROJECT).as_posix(), "sha256": sha256(PART_MANIFEST), "status": parts["status"], "unsupported": parts["unsupported"]},
            "rigid_soft_manifest": {"path": RIGID_SOFT_MANIFEST.relative_to(PROJECT).as_posix(), "sha256": sha256(RIGID_SOFT_MANIFEST), "status": rigid_soft["status"]},
            "candidate_angle_audit": {"path": ANGLE_AUDIT.relative_to(PROJECT).as_posix(), "sha256": sha256(ANGLE_AUDIT), "formal_acceptance": angle["formal_acceptance"]},
        },
        "packages": packages,
        "minimum_safe_advance_batch": {
            "workpack_id": "P0-yaw-105-face18",
            "record_count": 18,
            "scope": "CONTROL_PREPARATION_ONLY",
            "allowed_actions": [
                "derive or acquire verified fine-face masks from admitted same-view geometry",
                "obtain manual acceptance for a same-view mother pixel source",
                "bind required dynamic assets and hashes",
            ],
            "forbidden_actions": [
                "extract formal pixels from the unaccepted candidate",
                "promote coarse head part-ID as 18 fine facial masks",
                "create blank or placeholder PNGs",
                "mark any P0 record repaired or PASS",
            ],
            "why_first": "It is the only P0 view whose closest candidate is an angle geometry mother; it still fails full-art and alpha gates.",
        },
        "truth_boundary": "All five views have admitted geometry controls, but none has both an accepted same-view mother image and verified fine-face masks. Therefore zero of 73 P0 records is immediately repairable for formal promotion.",
    }
    # Some inherited artifact directories are read-only to subprocesses even
    # though the checked-in evidence is managed by the workspace patch tool.
    # In that case the inventory is still fully recomputed and emitted below;
    # the pinned JSON is verified separately by validate_p0_source_readiness.py.
    output_written = True
    try:
        OUTPUT.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except PermissionError:
        output_written = False

    lines = [
        "# P0 73 筆可重用來源確定性矩陣",
        "",
        "## 真實結論",
        "",
        "- 可立即進行正式像素修復：**0 / 73**。",
        f"- 可先做控制準備：**{matrix['control_preparation_record_count']} / 73**，僅 `yaw-105-pitch+00` 18 層；不得產出或升格正式 PNG。",
        "- 5 個相關視角都有 MHR/ufbx depth、normal、silhouette、粗粒度 part-ID 與 rigid/soft 幾何控制。",
        "- 粗粒度 part-ID 只有整體 head，不能冒充嘴唇、眼皮、眉毛、虹膜、口腔等 18 個細臉層遮罩。",
        "- 5 個視角都缺已通過美術驗收的同視角主圖；候選圖只能作控制或退件證據，不能抽正式像素。",
        "",
        "## 逐工作包",
        "",
        "| 工作包 | 筆數 | 幾何控制 | 最近主圖候選 | 正式修復 |",
        "|---|---:|---|---|---|",
    ]
    for package in packages:
        candidate = package["closest_existing_mother_candidate"]
        lines.append(
            f"| `{package['workpack_id']}` | {package['record_count']} | 可重用但僅控制 | {candidate['angle_geometry_status']}; full-art={str(candidate['full_art_pass']).lower()} | BLOCK |"
        )
    lines += [
        "",
        "## 最小先行批次",
        "",
        "`P0-yaw-105-face18` 僅可先補齊細臉遮罩、同視角主圖人工驗收與動態資產證據。完成前不可抽像素、不可建立空白層、不可改正式 manifest。",
    ]
    try:
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except PermissionError:
        output_written = False
    print(json.dumps({
        "computed_status": matrix["status"],
        "p0_record_count": matrix["p0_record_count"],
        "immediately_repairable_formal_record_count": matrix["immediately_repairable_formal_record_count"],
        "control_preparation_record_count": matrix["control_preparation_record_count"],
        "output_written_by_subprocess": output_written,
    }, ensure_ascii=False, indent=2))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
