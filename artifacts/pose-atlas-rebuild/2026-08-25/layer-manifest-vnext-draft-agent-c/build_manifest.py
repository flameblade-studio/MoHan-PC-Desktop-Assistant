from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
VIEWS = [
    "yaw-180-pitch+00", "yaw-165-pitch+00", "yaw-150-pitch+00", "yaw-135-pitch+00",
    "yaw-120-pitch+00", "yaw-105-pitch+00", "yaw-090-pitch+00", "yaw-075-pitch+00",
    "yaw-060-pitch+00", "yaw-045-pitch+00", "yaw-030-pitch+00", "yaw-015-pitch+00",
    "yaw+000-pitch+00", "yaw+015-pitch+00", "yaw+030-pitch+00", "yaw+045-pitch+00",
    "yaw+060-pitch+00", "yaw+075-pitch+00", "yaw+090-pitch+00", "yaw+105-pitch+00",
    "yaw+120-pitch+00", "yaw+135-pitch+00", "yaw+150-pitch+00", "yaw+165-pitch+00",
]
CHARACTER_Z = {
    "body": 0, "hair_back": 10, "base": 30, "jaw": 31, "oral_cavity": 32,
    "teeth_tongue": 33, "lip_lower": 34, "lip_upper": 35, "corner_left": 36,
    "corner_right": 37, "blush_left": 38, "blush_right": 39, "iris_left": 40,
    "iris_right": 41, "eyelid_left": 42, "eyelid_right": 43, "eyeliner_left": 44,
    "eyeliner_right": 45, "brow_left": 46, "brow_right": 47, "hair_left": 50,
    "hair_right": 51, "sleeve_left": 60, "sleeve_right": 61, "ornament": 70,
}
OUTFIT_Z = {
    "innerwear": 20, "skirt": 21, "outerwear": 22, "sleeve-left": 23,
    "sleeve-right": 24, "shoe-left": 25, "shoe-right": 26,
}
FACE_LAYERS = {
    "base", "jaw", "oral_cavity", "teeth_tongue", "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
    "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left", "eyeliner_right",
    "brow_left", "brow_right",
}


def unresolved_asset(view_id: str, layer_id: str, z_order: int, owner: str, semantics: str) -> dict[str, object]:
    return {
        "view_id": view_id,
        "layer_id": layer_id,
        "owner": owner,
        "semantics": semantics,
        "path": None,
        "asset_sha256": None,
        "alpha_mask_sha256": None,
        "width": 1024,
        "height": 1536,
        "mode": "RGBA",
        "offset_x": 0,
        "offset_y": 0,
        "z_order": z_order,
        "source_provenance": {"status": "UNRESOLVED", "source_id": None, "source_sha256": None},
        "license_provenance": {"status": "UNRESOLVED", "license": None, "evidence_path": None, "evidence_sha256": None},
        "qa": {"status": "UNRESOLVED", "alpha_gate": "NOT_RUN", "manual_art_gate": "NOT_RUN"},
    }


def character_semantics(layer: str) -> tuple[str, str]:
    if layer in FACE_LAYERS:
        return "immutable_identity", "identity_face"
    if layer == "body":
        return "immutable_core", "core_skin_only_no_garment_no_shoes_no_hands"
    if layer in {"sleeve_left", "sleeve_right"}:
        return "immutable_core", "hand_left_no_fabric" if layer.endswith("left") else "hand_right_no_fabric"
    if layer.startswith("hair_"):
        return "immutable_core", "canonical_hair"
    return "immutable_core", "fixed_hairpin_character_right_no_mirroring"


def main() -> int:
    mapping_path = HERE.parent / "poseatlas-yunchangge-vnext-mapping-agent-c" / "mapping.json"
    mapping_sha = hashlib.sha256(mapping_path.read_bytes()).hexdigest().upper()
    records = []
    for view in VIEWS:
        character = []
        for layer, z_order in CHARACTER_Z.items():
            owner, semantics = character_semantics(layer)
            character.append(unresolved_asset(view, layer, z_order, owner, semantics))
        outfits = []
        for slot, z_order in OUTFIT_Z.items():
            asset = unresolved_asset(view, slot, z_order, "replaceable_garment", "garment_only_no_identity_or_hand_skin")
            asset["hand_occlusion_rule"] = "behind-hands" if slot.startswith("sleeve-") else "not-applicable"
            outfits.append(asset)
        records.append({
            "view_id": view,
            "body_center": [512, 1292],
            "character_layers": character,
            "outfit_slots": outfits,
            "ownership_masks": {
                "protected_core_mask": {"path": None, "sha256": None, "status": "UNRESOLVED"},
                "garment_occlusion_mask": {"path": None, "sha256": None, "status": "UNRESOLVED"},
                "exclusive_ownership_index": {"path": None, "sha256": None, "status": "UNRESOLVED"},
            },
            "view_qa": {"status": "UNRESOLVED", "recomposition_sha256": None},
        })
    manifest = {
        "schema": "mohan.pose-atlas.layer-manifest.vnext.draft.v1",
        "status": "DRAFT_UNRESOLVED",
        "promotion_allowed": False,
        "canvas": {"width": 1024, "height": 1536, "mode": "RGBA", "registration": "full-canvas"},
        "body_center_constant": [512, 1292],
        "transition": {"tick_hz": 50, "tick_ms": 20, "yaw_step_degrees": 15, "wrap": ["yaw-180-pitch+00", "yaw+165-pitch+00"]},
        "counts": {"views": 24, "character_layers_per_view": 25, "character_records": 600, "outfit_slots_per_view": 7, "outfit_records": 168},
        "character_layer_ids": list(CHARACTER_Z),
        "character_z_order": CHARACTER_Z,
        "outfit_slot_ids": list(OUTFIT_Z),
        "outfit_z_order": OUTFIT_Z,
        "yunchangge": {
            "pack_format": "mohan-outfit-pack/v2",
            "required_view_count": 31,
            "pose_atlas_view_count": 24,
            "mapping_path": str(mapping_path),
            "mapping_sha256": mapping_sha,
            "pack_level_required": ["id", "pack_version", "source", "compatible_body_profile", "authoring", "looks", "ensembles"],
            "per_asset_required": ["path", "sha256", "width", "height", "anchor", "z_order", "source_provenance", "license_provenance", "qa_status"],
        },
        "ownership_policy": {
            "body_may_contain_garment": False,
            "body_may_contain_shoes": False,
            "hands_may_contain_fabric": False,
            "garments_may_contain_identity_or_hand_skin": False,
            "fixed_hairpin_side": "character_right",
            "mirroring_allowed": False,
            "one_authoritative_owner_per_pixel": True,
        },
        "views": records,
        "production_readiness": {"status": "UNRESOLVED", "missing_file_count": 768, "missing_ownership_mask_count": 72, "accepted_view_count": 0},
    }
    (HERE / "layer_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("BUILT views=24 character_records=600 outfit_records=168 status=DRAFT_UNRESOLVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
