from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy from pathlib import Path

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from domain.hand_asset_evidence import (
    HandAssetManifestEvidence,
    build_hand_asset_evidence,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root: Path) -> dict[str, object]:
    resolved = root.resolve()
    views = []
    for yaw in CANONICAL_YAWS:
        view_id = canonical_view_id(yaw)
        png = resolved / f"{view_id}.png"
        sidecar = resolved / f"{view_id}.hands.json"
        if not png.is_file() or not sidecar.is_file():
            views.append(
                {
                    "view_id": view_id,
                    "passed": False,
                    "issues": ["asset_missing"],
                }
            )
            continue
        result = build_hand_asset_evidence(
            resolved,
            HandAssetManifestEvidence(
                view_id,
                yaw,
                png.name,
                sidecar.name,
                1024,
                1536,
                _sha256(png),
                _sha256(sidecar),
            ),
        )
        views.append(
            {
                "view_id": view_id,
                "passed": result.passed,
                "issues": list(result.problems),
                "issue_details": [
                    {
                        "code": issue.code,
                        "side": issue.side,
                        "finger": issue.finger,
                        "landmark_index": issue.landmark_index,
                    }
                    for issue in result.issues
                ],
                "visible_sides": sorted(result.visible_sides),
                "occluded_sides": sorted(result.occluded_sides),
            }
        )
    failed = [item for item in views if not item["passed"]]
    return {
        "schema": "mohan.pose-atlas.working-audit.v1",
        "passed": not failed,
        "view_count": len(views),
        "passed_view_count": len(views) - len(failed),
        "failed_view_count": len(failed),
        "views": views,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.root)
    payload = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
