from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import re
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIR_LENGTH = 2
sys.path.insert(0, str(ROOT))

lazy from domain.hand_asset_evidence import (
    HandAssetManifestEvidence,
    build_hand_asset_evidence,
)


@dataclass(frozen=True, slots=True)
class AssetAuditCharacterSettings:
    """Explicit view IDs, angles and canvas for the hand-evidence adapter."""

    schema: str
    views: tuple[tuple[str, int], ...]
    width: int
    height: int

    def __post_init__(self) -> None:
        if not isinstance(self.schema, str) or not self.schema:
            raise ValueError("Asset audit schema must be a nonempty string.")
        if any(type(value) is not int or value <= 0 for value in (self.width, self.height)):
            raise ValueError("Asset audit dimensions must be positive integers.")
        ids = []
        for view_id, yaw in self.views:
            if not isinstance(view_id, str) or re.fullmatch(r"[A-Za-z0-9_+.-]+", view_id) is None or view_id in {".", ".."}:
                raise ValueError("Asset audit view IDs must be safe filename identifiers.")
            if type(yaw) is not int:
                raise ValueError("Asset audit angles must be integers.")
            ids.append(view_id)
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("Asset audit views must be nonempty and unique.")


DEFAULT_CHARACTER_SETTINGS = AssetAuditCharacterSettings(
    schema="mohan.pose-atlas.working-audit.v1",
    views=tuple((f"yaw{yaw:+04d}-pitch+00", yaw) for yaw in range(-180, 180, 15)),
    width=1024,
    height=1536,
)


def load_character_settings(path: Path) -> AssetAuditCharacterSettings:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"schema", "views", "width", "height"}:
        raise ValueError("Asset audit settings require schema, views, width and height.")
    if not isinstance(payload["views"], list) or any(
        not isinstance(pair, list) or len(pair) != PAIR_LENGTH for pair in payload["views"]
    ):
        raise ValueError("Asset audit views must be pairs of view ID and yaw.")
    return AssetAuditCharacterSettings(
        payload["schema"], tuple(tuple(pair) for pair in payload["views"]),
        payload["width"], payload["height"],
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(
    root: Path, *, settings: AssetAuditCharacterSettings = DEFAULT_CHARACTER_SETTINGS,
) -> dict[str, object]:
    resolved = root.resolve()
    views = []
    for view_id, yaw in settings.views:
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
                settings.width,
                settings.height,
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
                "skipped_checks": list(result.skipped_checks),
            }
        )
    failed = [item for item in views if not item["passed"]]
    return {
        "schema": settings.schema,
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
    parser.add_argument("--character-settings", type=Path)
    args = parser.parse_args()
    settings = load_character_settings(args.character_settings) if args.character_settings else DEFAULT_CHARACTER_SETTINGS
    report = audit(args.root, settings=settings)
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
