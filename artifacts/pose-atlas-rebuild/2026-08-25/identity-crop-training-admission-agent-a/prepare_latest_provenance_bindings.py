from __future__ import annotations

# SPDX-License-Identifier: MIT
# Copyright 2026 CHOU MING HUA / Flameblade Studio

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare hash-bound provenance inputs without promoting or training."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--qa", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    qa = json.loads(args.qa.read_text(encoding="utf-8"))
    entries = manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != 12:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "entries_not_exactly_12"}))
        return 4

    qa_status = str(qa.get("status", "UNKNOWN"))
    payload = {
        "schema": "mohan.latest_identity_provenance_bindings.v1",
        "promotion_status": "PENDING_FINAL_PROVENANCE_ADMISSION",
        "training_started": False,
        "manifest": {
            "path": str(args.manifest.resolve()),
            "sha256": sha256(args.manifest),
            "entries_sha256": canonical_sha256(entries),
            "entry_count": len(entries),
        },
        "qa": {
            "path": str(args.qa.resolve()),
            "sha256": sha256(args.qa),
            "status": qa_status,
            "is_visual_pass": qa_status == "PASS_MAIN_AGENT_VISUAL_REVIEW",
        },
    }
    if args.output is not None:
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["qa"]["is_visual_pass"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
