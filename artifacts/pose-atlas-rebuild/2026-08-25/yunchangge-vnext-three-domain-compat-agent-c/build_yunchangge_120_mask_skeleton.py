"""Build the 24 x 5 unresolved index. It never creates image assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

VIEWS = [
    *(f"yaw-{value:03d}-pitch+00" for value in range(180, 0, -15)),
    *(f"yaw+{value:03d}-pitch+00" for value in range(0, 180, 15)),
]
SLOTS = ["outerwear", "innerwear", "skirt", "shoe_left", "shoe_right"]
REQUIRED_EVIDENCE = [
    "clean_source_path", "source_sha256", "source_ownership",
    "mask_method", "license_id", "license_evidence_sha256",
    "human_core_overlap_pixels", "manual_qa_status",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Optional output path; stdout is the safe default.")
    args = parser.parse_args()
    entries = []
    for view in VIEWS:
        for slot in SLOTS:
            entries.append({
                "view_id": view,
                "slot": slot,
                "status": "MISSING",
                "asset": None,
                "mask": None,
                "source_evidence": {
                    "required_fields": REQUIRED_EVIDENCE,
                    "provided": {
                        "clean_source_path": None,
                        "source_sha256": None,
                        "source_ownership": None,
                        "mask_method": None,
                        "license_id": None,
                        "license_evidence_sha256": None,
                        "human_core_overlap_pixels": None,
                        "manual_qa_status": None,
                    },
                },
                "blocking_reason": "No admitted clean per-view source/mask evidence exists; mixed v4 body cannot be split by assumption.",
            })
    payload = {
        "schema": "mohan.yunchangge.five-slot-mask-skeleton-index.v1",
        "status": "STRUCTURALLY_COMPLETE_AS_MISSING",
        "asset_readiness": "BLOCKED_UNRESOLVED",
        "runtime_wired": False,
        "promotion_allowed": False,
        "expected_entry_count": 120,
        "views": VIEWS,
        "slots": SLOTS,
        "entries": entries,
        "generated_image_count": 0,
        "truth_boundary": "This is a missing-item index. No blank or transparent PNG is created or accepted as an asset.",
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
