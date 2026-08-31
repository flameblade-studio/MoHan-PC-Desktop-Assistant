from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
CURRENT = ROOT / "assets/pose-atlas/v4-layered/layer_manifest.json"
OWNERSHIP_QA = ROOT / "artifacts/pose-atlas-rebuild/2026-08-25/v4-600-ownership-color-qa-agent-c/yaw000-ownership-color-qa.json"

VIEWS = tuple(
    [f"yaw{yaw:+04d}-pitch+00" for yaw in range(-180, 0, 15)]
    + [f"yaw{yaw:+04d}-pitch+00" for yaw in range(0, 180, 15)]
)
CORE = ("core_skin", "body_geometry", "hand_left", "hand_right", "foot_left", "foot_right", "core_hair_back", "core_hair_left", "core_hair_right", "core_fixed_ornament")
GARMENT = ("outerwear", "innerwear", "bodice", "skirt", "trousers", "sleeve_left", "sleeve_right", "shoe_left", "shoe_right", "garment_occluder_back", "garment_occluder_front")
ACCESSORY = ("headwear", "jewelry", "weapon", "handheld", "foreground_effect")
ALL_SLOTS = CORE + GARMENT + ACCESSORY
DOMAIN = {**dict.fromkeys(CORE, "core-body"), **dict.fromkeys(GARMENT, "garment-dlc"), **dict.fromkeys(ACCESSORY, "accessory")}
ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-ND-4.0"}
SHA = "A" * 64


def provenance() -> dict[str, object]:
    return {
        "origin_type": "first-party-fixture", "creator": "Flameblade Studio fixture",
        "rightsholder": "CHOU MING HUA", "source_url": "artifact://fixture",
        "source_revision": "fixture-v1", "source_sha256": SHA, "license_spdx": "MIT",
        "license_evidence_sha256": SHA, "commercial_use_allowed": True,
        "derivatives_allowed": True, "redistribution_allowed": True,
        "training_use_allowed": True, "modified": False,
        "notices_reference": "artifact://fixture/NOTICE",
    }


def asset(slot: str, resolved: bool) -> dict[str, object]:
    return {
        "slot": slot, "owner_domain": DOMAIN[slot],
        "status": "RESOLVED_FIXTURE" if resolved else "UNRESOLVED",
        "path": f"fixtures/{slot}.png" if resolved else None,
        "sha256": SHA if resolved else None,
        "mask": ({"path": f"fixtures/{slot}.mask.png", "sha256": SHA, "mode": "L", "owner_domain": DOMAIN[slot], "exclusive_primary": True, "allowed_overlap_with": [], "soft_edge_policy": "bounded-alpha"} if resolved else None),
        "offset": [0, 0], "provenance": provenance() if resolved else None,
        "qa_status": "FIXTURE_PASS" if resolved else "UNRESOLVED",
    }


def manifest(resolved: bool, status: str) -> dict[str, object]:
    return {
        "schema_version": "mohan.pose-atlas.vnext.garment-separable.v1-draft",
        "status": status, "canvas": {"width": 1024, "height": 1536, "mode": "RGBA"},
        "body_center": [512, 1292],
        "offset_policy": {"kind": "full-canvas-registered", "offset_x": 0, "offset_y": 0},
        "slot_contract": {"core-body": list(CORE), "garment-dlc": list(GARMENT), "accessory": list(ACCESSORY)},
        "ownership_contract": {"primary_owner_required": True, "undeclared_overlap_forbidden": True, "garment_over_core_identity_forbidden": True, "mask_registration": "full-canvas-[0,0]"},
        "license_policy": {"allowed": sorted(ALLOWED_LICENSES), "nc_forbidden": True, "unknown_forbidden": True, "rights_fields_required": True},
        "views": [{"view_id": view, "assets": [asset(slot, resolved) for slot in ALL_SLOTS], "recomposition": {"approved_master_sha256": SHA if resolved else None, "diff_policy": "exact" if resolved else "UNRESOLVED", "qa_status": "FIXTURE_PASS" if resolved else "UNRESOLVED"}} for view in VIEWS],
        "qa": {"promotion_allowed": False, "formal_assets_modified": False, "fixture_only": status == "FIXTURE_VALID"},
    }


def write_artifacts() -> None:
    draft = manifest(False, "DRAFT_ONLY")
    positive = manifest(True, "FIXTURE_VALID")
    missing_shoe = json.loads(json.dumps(positive))
    missing_shoe["views"][0]["assets"] = [item for item in missing_shoe["views"][0]["assets"] if item["slot"] != "shoe_left"]
    wrong_owner = json.loads(json.dumps(positive))
    next(item for item in wrong_owner["views"][0]["assets"] if item["slot"] == "core_skin")["owner_domain"] = "garment-dlc"
    missing_mask = json.loads(json.dumps(positive))
    next(item for item in missing_mask["views"][0]["assets"] if item["slot"] == "outerwear")["mask"] = None
    forbidden_license = json.loads(json.dumps(positive))
    next(item for item in forbidden_license["views"][0]["assets"] if item["slot"] == "outerwear")["provenance"]["license_spdx"] = "CC-BY-NC-4.0"
    nonzero_offset = json.loads(json.dumps(positive))
    next(item for item in nonzero_offset["views"][0]["assets"] if item["slot"] == "skirt")["offset"] = [1, 0]
    for name, payload in {
        "poseatlas-vnext-garment-separable.draft.json": draft,
        "fixtures-vnext-positive.json": positive,
        "fixtures-vnext-missing-shoe.json": missing_shoe,
        "fixtures-vnext-wrong-owner.json": wrong_owner,
        "fixtures-vnext-missing-mask.json": missing_mask,
        "fixtures-vnext-forbidden-license.json": forbidden_license,
        "fixtures-vnext-nonzero-offset.json": nonzero_offset,
    }.items():
        (HERE / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate(data: dict[str, object], *, allow_unresolved: bool = False) -> list[str]:
    issues: list[str] = []
    if data.get("schema_version") != "mohan.pose-atlas.vnext.garment-separable.v1-draft": issues.append("schema_version")
    if data.get("canvas") != {"width": 1024, "height": 1536, "mode": "RGBA"}: issues.append("canvas")
    if data.get("body_center") != [512, 1292]: issues.append("body_center")
    if data.get("offset_policy") != {"kind": "full-canvas-registered", "offset_x": 0, "offset_y": 0}: issues.append("offset_policy")
    views = data.get("views")
    if not isinstance(views, list) or [item.get("view_id") for item in views if isinstance(item, dict)] != list(VIEWS): return issues + ["exact_24_view_order"]
    for view in views:
        view_id = view["view_id"]
        assets = view.get("assets")
        if not isinstance(assets, list) or [item.get("slot") for item in assets if isinstance(item, dict)] != list(ALL_SLOTS): issues.append(f"{view_id}:exact_slots"); continue
        for item in assets:
            slot = item["slot"]
            if item.get("owner_domain") != DOMAIN[slot]: issues.append(f"{view_id}:{slot}:owner")
            if item.get("offset") != [0, 0]: issues.append(f"{view_id}:{slot}:offset")
            if item.get("status") == "UNRESOLVED":
                if not allow_unresolved: issues.append(f"{view_id}:{slot}:unresolved")
                continue
            if not item.get("path") or not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64: issues.append(f"{view_id}:{slot}:asset_integrity")
            mask = item.get("mask")
            if not isinstance(mask, dict) or mask.get("owner_domain") != DOMAIN[slot] or mask.get("exclusive_primary") is not True: issues.append(f"{view_id}:{slot}:mask")
            prov = item.get("provenance")
            if not isinstance(prov, dict) or prov.get("license_spdx") not in ALLOWED_LICENSES or prov.get("commercial_use_allowed") is not True: issues.append(f"{view_id}:{slot}:provenance")
            if isinstance(prov, dict) and prov.get("license_spdx") == "CC-BY-ND-4.0" and prov.get("modified") is True: issues.append(f"{view_id}:{slot}:nd_modified")
    return issues


def current_migration() -> tuple[dict[str, object], list[str]]:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    qa = json.loads(OWNERSHIP_QA.read_text(encoding="utf-8"))
    layers = qa["results"][0]["layers"]
    issues = [
        "legacy_body_contains_garment_pixels", "legacy_body_contains_shoe_pixels",
        "legacy_body_contains_arms_hands", "legacy_ornament_contains_identity_pixels",
        "missing_core_skin", "missing_body_geometry", "missing_hand_left", "missing_hand_right",
        "missing_foot_left", "missing_foot_right", "missing_outerwear", "missing_innerwear",
        "missing_bodice", "missing_skirt", "missing_shoe_left", "missing_shoe_right",
        "missing_ownership_masks", "missing_asset_provenance", "runtime_does_not_consume_manifest",
    ]
    evidence = {
        "current_manifest_sha256": hashlib.sha256(CURRENT.read_bytes()).hexdigest().upper(),
        "current_views": len(current.get("views", [])),
        "current_records": sum(len(view.get("layers", [])) for view in current.get("views", [])),
        "body_counts": layers["body"]["counts"], "ornament_counts": layers["ornament"]["counts"],
        "migration_status": "BLOCKED", "promotion_allowed": False, "issues": issues,
    }
    return evidence, issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", action="store_true")
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--allow-unresolved", action="store_true")
    parser.add_argument("--current", action="store_true")
    args = parser.parse_args()
    if args.emit:
        write_artifacts(); print("EMIT_OK"); return 0
    if args.current:
        evidence, issues = current_migration()
        (HERE / "current-600-to-vnext-migration-result.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif args.fixture:
        issues = validate(json.loads(args.fixture.read_text(encoding="utf-8")), allow_unresolved=args.allow_unresolved)
    else:
        parser.error("choose --emit, --fixture, or --current")
    print(json.dumps({"status": "PASS" if not issues else "BLOCK", "issues": issues}, ensure_ascii=False))
    return 0 if not issues else 4


if __name__ == "__main__":
    raise SystemExit(main())
