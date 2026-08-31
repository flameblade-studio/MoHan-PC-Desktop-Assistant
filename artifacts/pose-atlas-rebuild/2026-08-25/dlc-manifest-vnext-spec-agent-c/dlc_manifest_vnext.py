from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path


VIEWS = tuple(
    [f"yaw-{degree:03d}-pitch+00" for degree in range(180, 0, -15)]
    + ["yaw+000-pitch+00"]
    + [f"yaw+{degree:03d}-pitch+00" for degree in range(15, 180, 15)]
)
CORE_25 = (
    "base", "jaw", "oral_cavity", "teeth_tongue", "lip_lower", "lip_upper",
    "corner_left", "corner_right", "blush_left", "blush_right", "iris_left",
    "iris_right", "eyelid_left", "eyelid_right", "eyeliner_left",
    "eyeliner_right", "brow_left", "brow_right", "body", "hair_back",
    "hair_left", "hair_right", "sleeve_left", "sleeve_right", "ornament",
)
GARMENT_SLOTS = (
    "outfit_inner", "outfit_outer", "skirt", "sleeve_left", "sleeve_right",
    "shoe_left", "shoe_right",
)
HASH = re.compile(r"[0-9A-F]{64}\Z")


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest().upper()


def asset(label: str, owner: str, z: int) -> dict:
    return {
        "path": f"fixture://{label}.png", "sha256": digest(label),
        "alpha_mask_sha256": digest(f"{label}:alpha"), "width": 1024,
        "height": 1536, "mode": "RGBA", "anchor": [0, 0], "z_order": z,
        "owner": owner, "source_provenance": "FIXTURE_ONLY",
        "license_provenance": "FIXTURE_ONLY_NOT_DISTRIBUTABLE",
    }


def build_example() -> dict:
    views = []
    for view in VIEWS:
        garments = {slot: asset(f"{view}:{slot}", "replaceable_garment", 30 + index) for index, slot in enumerate(GARMENT_SLOTS)}
        views.append({
            "view_id": view,
            "core": {
                "core_skin": asset(f"{view}:core_skin", "immutable_core", 0),
                "hand_left": asset(f"{view}:hand_left", "immutable_core", 50),
                "hand_right": asset(f"{view}:hand_right", "immutable_core", 50),
                "body_geometry": {
                    "path": f"fixture://{view}:body_geometry.mask", "sha256": digest(f"{view}:body_geometry"),
                    "format": "L16", "owner": "immutable_geometry_control",
                },
                "fixed_ornament": asset(f"{view}:fixed_hairpin", "immutable_core", 70),
            },
            "garments": garments,
            "replaceable_ornaments": {
                "headwear": asset(f"{view}:headwear", "replaceable_ornament", 71),
                "jewelry": asset(f"{view}:jewelry", "replaceable_ornament", 72),
            },
            "ownership_masks": {
                "protected_core_mask_sha256": digest(f"{view}:protected_core"),
                "garment_occlusion_mask_sha256": digest(f"{view}:garment_occlusion"),
                "exclusive_ownership_index_sha256": digest(f"{view}:ownership_index"),
            },
            "physical_side": {"fixed_hairpin": "character_right", "mirroring_allowed": False},
            "qa_status": "SPEC_FIXTURE_ONLY",
        })
    return {
        "schema": "mohan.dlc-manifest.vnext.v1",
        "status": "SPEC_FIXTURE_NON_PRODUCTION",
        "promotion_allowed": False,
        "canvas": {"width": 1024, "height": 1536, "mode": "RGBA", "anchor": [0, 0]},
        "core_pose_atlas": {
            "view_count": 24, "layer_count_per_view": 25, "file_count": 600,
            "layer_ids": list(CORE_25),
            "compatibility_semantics": {
                "body": "core_skin_excluding_hands_no_garment",
                "sleeve_left": "compatibility_alias_for_hand_left_no_fabric",
                "sleeve_right": "compatibility_alias_for_hand_right_no_fabric",
                "ornament": "fixed_physical_side_hairpin_only",
            },
            "manifest_sha256": digest("future-formal-core-pose-atlas-manifest"),
        },
        "ownership_policy": {
            "core_skin_excludes": list(GARMENT_SLOTS) + ["headwear", "jewelry"],
            "hands_are_core": True, "sleeves_exclude_hands": True,
            "shoes_are_replaceable": True, "one_authoritative_owner_per_pixel": True,
            "occlusion_does_not_transfer_ownership": True,
        },
        "views": views,
    }


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)
    require(data.get("schema") == "mohan.dlc-manifest.vnext.v1", "schema")
    require(data.get("status") == "SPEC_FIXTURE_NON_PRODUCTION", "fixture status")
    require(data.get("promotion_allowed") is False, "fixture cannot promote")
    canvas = data.get("canvas", {})
    require(canvas == {"width": 1024, "height": 1536, "mode": "RGBA", "anchor": [0, 0]}, "canvas")
    atlas = data.get("core_pose_atlas", {})
    require(atlas.get("view_count") == 24 and atlas.get("layer_count_per_view") == 25 and atlas.get("file_count") == 600, "24x25 core atlas")
    require(tuple(atlas.get("layer_ids", ())) == CORE_25, "core 25 IDs")
    semantics = atlas.get("compatibility_semantics", {})
    require(semantics.get("body") == "core_skin_excluding_hands_no_garment", "body core semantics")
    require(semantics.get("sleeve_left") == "compatibility_alias_for_hand_left_no_fabric", "left compatibility semantics")
    require(semantics.get("sleeve_right") == "compatibility_alias_for_hand_right_no_fabric", "right compatibility semantics")
    policy = data.get("ownership_policy", {})
    require(policy.get("hands_are_core") is True, "hands core")
    require(policy.get("sleeves_exclude_hands") is True, "sleeves exclude hands")
    require(policy.get("shoes_are_replaceable") is True, "shoes replaceable")
    require(policy.get("one_authoritative_owner_per_pixel") is True, "exclusive owner")
    require(set(policy.get("core_skin_excludes", ())).issuperset(GARMENT_SLOTS), "core excludes garments")
    views = data.get("views", [])
    require(isinstance(views, list) and tuple(item.get("view_id") for item in views) == VIEWS, "24 exact ordered views")
    for item in views if isinstance(views, list) else []:
        view = item.get("view_id", "UNKNOWN")
        core = item.get("core", {})
        garments = item.get("garments", {})
        require(set(garments) == set(GARMENT_SLOTS), f"{view}: garment slots")
        for name in ("core_skin", "hand_left", "hand_right", "fixed_ornament"):
            require(core.get(name, {}).get("owner") == "immutable_core", f"{view}: {name} owner")
        require(core.get("body_geometry", {}).get("owner") == "immutable_geometry_control", f"{view}: geometry owner")
        for slot in GARMENT_SLOTS:
            require(garments.get(slot, {}).get("owner") == "replaceable_garment", f"{view}: {slot} owner")
        all_assets = [core.get(name, {}) for name in ("core_skin", "hand_left", "hand_right", "fixed_ornament")]
        all_assets += [garments.get(slot, {}) for slot in GARMENT_SLOTS]
        all_assets += list(item.get("replaceable_ornaments", {}).values())
        paths = []
        for entry in all_assets:
            require(entry.get("width") == 1024 and entry.get("height") == 1536 and entry.get("mode") == "RGBA", f"{view}: full canvas RGBA")
            require(entry.get("anchor") == [0, 0], f"{view}: anchor")
            require(bool(HASH.fullmatch(str(entry.get("sha256", "")))), f"{view}: asset hash")
            require(bool(HASH.fullmatch(str(entry.get("alpha_mask_sha256", "")))), f"{view}: alpha mask hash")
            paths.append(entry.get("path"))
        require(len(paths) == len(set(paths)), f"{view}: duplicate pixel ownership")
        masks = item.get("ownership_masks", {})
        require(set(masks) == {"protected_core_mask_sha256", "garment_occlusion_mask_sha256", "exclusive_ownership_index_sha256"}, f"{view}: ownership masks")
        require(all(HASH.fullmatch(str(value)) for value in masks.values()), f"{view}: ownership mask hashes")
        require(item.get("physical_side") == {"fixed_hairpin": "character_right", "mirroring_allowed": False}, f"{view}: physical side")
    return errors


def negative_fixtures(example: dict) -> dict[str, dict]:
    cases = {}
    cases["missing_view"] = copy.deepcopy(example); cases["missing_view"]["views"].pop()
    cases["missing_shoe"] = copy.deepcopy(example); del cases["missing_shoe"]["views"][0]["garments"]["shoe_left"]
    cases["sleeve_owns_hand"] = copy.deepcopy(example); cases["sleeve_owns_hand"]["views"][0]["garments"]["sleeve_left"]["owner"] = "immutable_core"
    cases["body_allows_garment"] = copy.deepcopy(example); cases["body_allows_garment"]["ownership_policy"]["core_skin_excludes"] = []
    cases["duplicate_pixel_owner"] = copy.deepcopy(example); cases["duplicate_pixel_owner"]["views"][0]["garments"]["outfit_outer"]["path"] = cases["duplicate_pixel_owner"]["views"][0]["core"]["core_skin"]["path"]
    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(); args.output_dir.mkdir(parents=True, exist_ok=True)
    example = build_example()
    (args.output_dir / "manifest-vnext-example.json").write_text(json.dumps(example, ensure_ascii=False, indent=2), encoding="utf-8")
    results = {"positive": {"errors": validate(example)}}
    for name, fixture in negative_fixtures(example).items():
        path = args.output_dir / f"negative-{name}.json"
        path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
        results[name] = {"errors": validate(fixture)}
    positive_ok = not results["positive"]["errors"]
    negatives_ok = all(results[name]["errors"] for name in results if name != "positive")
    summary = {"schema": "mohan.dlc-vnext-validator-results.v1", "positive_exit": 0 if positive_ok else 4, "negative_exits": {name: 4 if value["errors"] else 0 for name, value in results.items() if name != "positive"}, "results": results, "all_tests_pass": positive_ok and negatives_ok}
    (args.output_dir / "validator-results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"positive_exit": summary["positive_exit"], "negative_exits": summary["negative_exits"], "all_tests_pass": summary["all_tests_pass"]}))
    return 0 if summary["all_tests_pass"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
