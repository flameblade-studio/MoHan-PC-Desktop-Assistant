"""Fail-closed package audit and rebuild manifest for the 24x25 PoseAtlas.

This command never edits artwork.  It inventories the registered full-canvas
RGBA layers, applies pixel-safety checks, consumes the semantic audit, and
emits an actionable A/B/C rebuild manifest.  Class A is mechanically repairable
from existing pixels/masks, B requires re-segmentation from an approved master
view, and C is an intentional neutral-state exception.
"""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import sys
lazy from collections import Counter
lazy from dataclasses import asdict, dataclass
lazy from pathlib import Path
lazy from typing import Any, Iterable

lazy import cv2
lazy import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from infrastructure.layered_full_body_assets import VIEW_IDS
lazy from tools.audit_layered_full_body_semantics import LAYER_NAMES


DEFAULT_ASSET_ROOT = ROOT / "assets" / "pose-atlas" / "v4-layered"
DEFAULT_AUTHORITY_ROOT = ROOT / "assets" / "pose-atlas" / "v4"
DEFAULT_SEMANTIC_REPORT = ROOT / "work" / "full_body_semantic_audit.json"
DEFAULT_AUDIT_OUTPUT = ROOT / "work" / "full_body_layer_pack_audit.json"
DEFAULT_MANIFEST_OUTPUT = ROOT / "work" / "full_body_layer_rebuild_manifest.json"
COLOR_IMAGE_NDIM = 3
RGBA_CHANNELS = 4
EXPECTED_WH = (1024, 1536)
ALPHA_VISIBLE = 16
SCHEMA = "mohan.full-body-layer-pack-audit.v1"
MANIFEST_SCHEMA = "mohan.full-body-layer-rebuild-manifest.v1"

# Neutral static authorities legitimately have no exposed teeth.  Teeth are
# synthesized only after aperture opens; inventing pixels here would be wrong.
EXPECTED_NEUTRAL_EMPTY = frozenset({"teeth_tongue"})
LIP_LAYERS = frozenset({"lip_upper", "lip_lower"})


@dataclass(frozen=True, slots=True)
class Finding:
    classification: str
    code: str
    view_id: str
    layer: str
    path: str
    metrics: dict[str, int | float | str]


def _read(path: Path) -> np.ndarray | None:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    return image


def _transparent_rgb_count(image: np.ndarray) -> int:
    alpha0 = image[..., 3] == 0
    return int(np.count_nonzero(alpha0 & np.any(image[..., :3] != 0, axis=2)))


def _lip_chroma_counts(image: np.ndarray) -> tuple[int, int]:
    """Count conspicuous green/cyan contaminants only inside visible pixels."""
    b, g, r, a = cv2.split(image)
    visible = a > ALPHA_VISIBLE
    # Integer widening prevents uint8 subtraction wraparound.
    bi, gi, ri = b.astype(np.int16), g.astype(np.int16), r.astype(np.int16)
    green = visible & (gi >= ri + 28) & (gi >= bi + 18)
    cyan = visible & (gi >= ri + 24) & (bi >= ri + 24)
    return int(np.count_nonzero(green)), int(np.count_nonzero(cyan))


def _edge_counts(image: np.ndarray) -> dict[str, int]:
    visible = image[..., 3] > ALPHA_VISIBLE
    return {
        "top": int(np.count_nonzero(visible[0, :])),
        "bottom": int(np.count_nonzero(visible[-1, :])),
        "left": int(np.count_nonzero(visible[:, 0])),
        "right": int(np.count_nonzero(visible[:, -1])),
    }


def _semantic_actions(report_path: Path) -> list[Finding]:
    if not report_path.is_file():
        return [Finding("B", "semantic_report_missing", "*", "*", str(report_path), {})]
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    actions: list[Finding] = []
    c_codes = {"teeth_tongue_all_views_empty"}
    for issue in payload.get("issues", []):
        code = str(issue.get("code", "unknown"))
        cls = "C" if code in c_codes else "B"
        actions.append(Finding(
            cls, code, str(issue.get("view_id", "*")), str(issue.get("layer", "*")),
            str(issue.get("path", "")), dict(issue.get("metrics", {})),
        ))
    return actions


def audit_pack(asset_root: Path, semantic_report: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    findings: list[Finding] = []
    checked = 0
    empty = 0
    edge_metrics: dict[str, dict[str, int]] = {}

    for view_id in VIEW_IDS:
        for layer in LAYER_NAMES:
            path = asset_root / f"{view_id}_{layer}.png"
            if not path.is_file():
                findings.append(Finding("B", "missing_file", view_id, layer, str(path), {}))
                continue
            image = _read(path)
            if image is None:
                findings.append(Finding("B", "unreadable_png", view_id, layer, str(path), {}))
                continue
            checked += 1
            if image.ndim != COLOR_IMAGE_NDIM or image.shape[2] != RGBA_CHANNELS:
                findings.append(Finding("B", "not_rgba", view_id, layer, str(path), {"shape": str(image.shape)}))
                continue
            height, width = image.shape[:2]
            if (width, height) != EXPECTED_WH:
                findings.append(Finding("B", "wrong_dimensions", view_id, layer, str(path), {
                    "width": width, "height": height,
                }))
                continue

            visible = int(np.count_nonzero(image[..., 3] > ALPHA_VISIBLE))
            if visible == 0:
                empty += 1
                if layer in EXPECTED_NEUTRAL_EMPTY:
                    findings.append(Finding("C", "neutral_teeth_empty", view_id, layer, str(path), {}))
                # Other empty layers can be valid at back views; semantic audit
                # owns that visibility decision and remains fail-closed.

            hidden = _transparent_rgb_count(image)
            if hidden:
                findings.append(Finding("A", "transparent_rgb_nonzero", view_id, layer, str(path), {
                    "pixel_count": hidden,
                    "repair": "set RGB=0 wherever alpha=0 without changing alpha",
                }))

            edges = _edge_counts(image)
            if any(edges.values()):
                edge_metrics[f"{view_id}_{layer}"] = edges
                # A touched canvas boundary cannot be reconstructed by padding;
                # it needs a master view with safe margin and re-segmentation.
                findings.append(Finding("B", "visible_pixels_touch_canvas_edge", view_id, layer, str(path), edges))

            if layer in LIP_LAYERS and visible:
                green, cyan = _lip_chroma_counts(image)
                if green or cyan:
                    findings.append(Finding("A", "lip_green_cyan_contamination", view_id, layer, str(path), {
                        "green_pixels": green, "cyan_pixels": cyan,
                        "repair": "replace only flagged visible pixels from approved master-view lip pixels",
                    }))

    findings.extend(_semantic_actions(semantic_report))

    # Deduplicate identical semantic file/code entries while preserving cases
    # where two independent rules intentionally name the same bad file.
    unique: dict[tuple[str, str, str, str], Finding] = {}
    for finding in findings:
        unique[(finding.classification, finding.code, finding.view_id, finding.layer)] = finding
    findings = sorted(unique.values(), key=lambda f: (f.classification, f.view_id, f.layer, f.code))
    counts = Counter(f.classification for f in findings)
    blockers = counts["A"] + counts["B"]

    audit = {
        "schema": SCHEMA,
        "passed": blockers == 0,
        "exit_code": 0 if blockers == 0 else 1,
        "asset_root": str(asset_root.resolve()),
        "expected_views": len(VIEW_IDS),
        "expected_layers_per_view": len(LAYER_NAMES),
        "expected_files": len(VIEW_IDS) * len(LAYER_NAMES),
        "files_checked": checked,
        "empty_files": empty,
        "classification_counts": dict(sorted(counts.items())),
        "findings": [asdict(f) for f in findings],
    }
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "fail_closed": True,
        "promotable": blockers == 0,
        "asset_root": str(asset_root.resolve()),
        "authority_contract": "Only user-approved 24 master views may source class-B re-segmentation.",
        "classes": {
            "A": {
                "meaning": "deterministic repair from existing approved pixels/masks",
                "actions": [asdict(f) for f in findings if f.classification == "A"],
            },
            "B": {
                "meaning": "must re-segment/repaint from an approved 24-view master; never mirror or hallucinate",
                "actions": [asdict(f) for f in findings if f.classification == "B"],
            },
            "C": {
                "meaning": "audit exception confirmed intentional; retain pixels unchanged",
                "actions": [asdict(f) for f in findings if f.classification == "C"],
            },
        },
        "promotion_gate": [
            "run tools/audit_layered_full_body_semantics.py and require exit 0 after C exceptions are applied",
            "run tools/audit_full_body_layer_pack.py and require exit 0",
            "do not promote generated layers while any class A or B action remains",
        ],
    }
    return audit, manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, default=DEFAULT_ASSET_ROOT)
    parser.add_argument("--semantic-report", type=Path, default=DEFAULT_SEMANTIC_REPORT)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT_OUTPUT)
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST_OUTPUT)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        audit, manifest = audit_pack(args.asset_root.resolve(), args.semantic_report.resolve())
        for path, payload in ((args.audit_output, audit), (args.manifest_output, manifest)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "passed": audit["passed"], "exit_code": audit["exit_code"],
            "files_checked": audit["files_checked"],
            "classification_counts": audit["classification_counts"],
            "audit_output": str(args.audit_output), "manifest_output": str(args.manifest_output),
        }, ensure_ascii=False))
        return int(audit["exit_code"])
    except Exception as exc:  # package gate must fail closed
        print(json.dumps({"passed": False, "exit_code": 2, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
