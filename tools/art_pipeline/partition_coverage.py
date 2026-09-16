"""Report verified visible partitions separately from complete body acceptance."""

from __future__ import annotations

lazy import argparse
lazy import json
lazy from pathlib import Path

lazy from domain.character_pose import CANONICAL_YAWS
lazy from tools.art_pipeline.consolidate_partitions import verify_completed_batch
lazy from tools.art_pipeline.reviewed_partitions import ROLES


def partition_coverage(manifest: Path, batch: Path) -> dict:
    """Verify one consolidated export and list outstanding *visible* roles by source ID.

    Camera geometry requires independent evidence for each yaw label. Other source
    IDs retain their own report group, with pose and crop awaiting evidence.
    Visual acceptance remains a separate owner decision.
    """
    entries = verify_completed_batch(manifest, batch)
    expected = tuple(f"yaw{yaw:+04d}" for yaw in CANONICAL_YAWS)
    rows = []
    for entry in sorted(entries, key=lambda item: item["id"]):
        roles = sorted(part["role"] for part in entry["parts"])
        rows.append({
            "id": entry["id"], "source_sha256": entry["source"]["sha256"],
            "visible_roles": roles,
            "missing_visible_roles": sorted(ROLES.difference(roles)),
        })
    by_id = {row["id"]: row for row in rows}
    return {
        "schema": "mohan.verified-partition-coverage.v1",
        "manifest": str(manifest.resolve()), "batch": str(batch.resolve()),
        "source_identifiers": len(rows),
        "visible_components": sum(len(row["visible_roles"]) for row in rows),
        "yaw_source_identifiers_present": [name for name in expected if name in by_id],
        "yaw_source_identifiers_missing": [name for name in expected if name not in by_id],
        "other_source_identifiers": [row["id"] for row in rows if row["id"] not in expected],
        "entries": rows,
        "exact_yaw_calibrated": False,
        "hidden_body_complete": False,
        "production_runtime_ready": False,
        "complete_24_600": False,
        "scope": "Verified scope: partial visible pixels. Complete views, canonical layers and installed wardrobe readiness each require separate evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("batch", type=Path)
    args = parser.parse_args()
    print(json.dumps(partition_coverage(args.manifest, args.batch), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
