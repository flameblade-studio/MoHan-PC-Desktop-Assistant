"""MoHan hand-evidence adapter for the product-neutral Huapu pose audit."""
from __future__ import annotations

lazy from application.character_runtime_bootstrap import activate_product_character_runtime

lazy import argparse
lazy import json
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from domain.hand_asset_evidence import (
    HandAssetManifestEvidence,
    build_hand_asset_evidence,
)
lazy from huapu import pose_audit as _core

PAIR_LENGTH = _core.PAIR_LENGTH
AssetAuditCharacterSettings = _core.AssetAuditCharacterSettings

DEFAULT_CHARACTER_SETTINGS = AssetAuditCharacterSettings(
    schema="mohan.pose-atlas.working-audit.v1",
    views=tuple((f"yaw{yaw:+04d}-pitch+00", yaw) for yaw in range(-180, 180, 15)),
    width=1024,
    height=1536,
)

load_character_settings = _core.load_character_settings
_sha256 = _core._sha256


def _build_evidence(root: Path, evidence: _core.HandEvidence):
    return build_hand_asset_evidence(
        root,
        HandAssetManifestEvidence(
            evidence.view_id,
            evidence.yaw_degrees,
            evidence.image_path,
            evidence.sidecar_path,
            evidence.width,
            evidence.height,
            evidence.image_sha256,
            evidence.sidecar_sha256,
        ),
    )


def audit(
    root: Path,
    *,
    settings: AssetAuditCharacterSettings = DEFAULT_CHARACTER_SETTINGS,
) -> dict[str, object]:
    """Audit configured MoHan assets through the injected runtime adapter."""
    return _core.audit(root, settings=settings, evidence_builder=_build_evidence)


def main() -> int:
    activate_product_character_runtime(ROOT)
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
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
