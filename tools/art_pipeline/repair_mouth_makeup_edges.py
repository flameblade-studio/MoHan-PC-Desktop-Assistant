"""Rebuild source-bound cosmetic aperture alpha while preserving native RGB.

Only mouth ROI mask alpha and packaged lip alpha are authored. Backups and
SHA-256 pins make repeated candidate creation and installation reproducible.
"""
from __future__ import annotations

lazy import argparse
lazy import io
lazy import json
lazy import sys
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np
lazy from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools.art_pipeline.front_crossed_rig import PACK, RigBuilder, digest, write_json

ROI = (548, 530, 686, 600)
SCALE = 8
MIDPOINT = 128
OPAQUE = 255
OFFSET_LIMIT = .5
MIN_CONTOUR_COLUMNS = 3
FAMILIES = ("small", "a", "o")


def pixels(data: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as image:
        return np.asarray(image.convert("RGBA")).copy()


def smooth_aperture(alpha: np.ndarray) -> tuple[np.ndarray, dict]:
    """Close fragmented openings and antialias their subpixel envelope.

    The outer upper/lower envelope is the registration authority: internal
    fragment edges are removed, rather than counted as lip contour positions.
    """
    left, top, right, bottom = ROI
    binary = (alpha[top:bottom, left:right] >= MIDPOINT).astype(np.uint8)
    columns = np.flatnonzero(binary.any(axis=0))
    if len(columns) < MIN_CONTOUR_COLUMNS:
        raise ValueError("The mouth aperture has no measurable contour")
    xs = np.arange(columns[0], columns[-1] + 1)
    upper = np.interp(xs, columns, [np.flatnonzero(binary[:, x])[0] - .5 for x in columns])
    lower = np.interp(xs, columns, [np.flatnonzero(binary[:, x])[-1] + .5 for x in columns])
    # Bounded closing joins the native dark fragments; the envelope also fills
    # tooth-shaped holes so a single aperture owns the cosmetic exclusion.
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3, 7), np.uint8))
    envelope = closed.copy()
    for i, x in enumerate(xs):
        envelope[int(np.ceil(upper[i])):int(np.floor(lower[i])) + 1, x] = 1
    contours, _ = cv2.findContours(envelope, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if len(contours) != 1:
        raise ValueError("Closing did not produce a single mouth opening")
    # Smooth the source envelope, preserving its native horizontal extent.
    kernel = np.array([1, 2, 3, 2, 1], dtype=float) / 9
    smooth_upper = np.convolve(np.pad(upper, 2, mode="edge"), kernel, "valid")
    smooth_lower = np.convolve(np.pad(lower, 2, mode="edge"), kernel, "valid")
    offset = float(np.mean(np.abs(np.concatenate((smooth_upper - upper, smooth_lower - lower)))))
    if offset > OFFSET_LIMIT:
        raise ValueError(f"Mean source-envelope contour offset {offset:.4f} exceeds {OFFSET_LIMIT}")
    coverage = rasterize_aperture(binary.shape, xs, smooth_upper, smooth_lower)
    result = alpha.copy()
    result[top:bottom, left:right] = coverage
    return result, {"mean_outer_envelope_offset_px": offset,
                    "original_components": cv2.connectedComponents(binary)[0] - 1,
                    "result_components": cv2.connectedComponents((coverage >= MIDPOINT).astype(np.uint8))[0] - 1,
                    "partial_alpha_pixels": int(np.count_nonzero((coverage > 0) & (coverage < OPAQUE)))}


def rasterize_aperture(shape: tuple[int, int], xs: np.ndarray,
                       upper: np.ndarray, lower: np.ndarray) -> np.ndarray:
    """Measure area coverage from eight samples per native pixel axis."""
    high_x = (np.arange(shape[1] * SCALE) + .5) / SCALE - .5
    high_y = (np.arange(shape[0] * SCALE) + .5) / SCALE - .5
    lo = np.interp(high_x, xs, upper)
    hi = np.interp(high_x, xs, lower)
    high = ((high_y[:, None] >= lo) & (high_y[:, None] <= hi)
            & (high_x[None, :] >= xs[0] - .5) & (high_x[None, :] <= xs[-1] + .5))
    return cv2.resize(high.astype(np.uint8) * OPAQUE, (shape[1], shape[0]), interpolation=cv2.INTER_AREA)


class MakeupEdgeRepair(RigBuilder):
    """Seal only cosmetic alpha assets, with complete frames pinned unchanged."""

    def repair(self) -> None:
        self.region = self.safe["silhouettes"]["front-crossed"]
        self.eyes_only = False
        self.metrics = []
        self.targets = [p for p in self.complete["poses"] if p.startswith("front-") and p.endswith("_front")] + ["front-crossed"]
        for pose in self.targets:
            record = self.complete["poses"][pose]
            for family in FAMILIES:
                descriptor = record["oral_masks"][family]
                relative = "assets/expressions/complete-expressions/" + descriptor["path"]
                original = pixels(self.original(relative))
                oral, metrics = smooth_aperture(original[..., 3])
                fixed = original.copy()
                fixed[..., 3] = oral
                descriptor["sha256"] = self.put(relative, fixed)["sha256"]
                if pose == "front-crossed":
                    rig_path = f"assets/front-makeup-rigs/front-crossed-{family}_oral_cavity.png"
                    rig = pixels(self.original(rig_path))
                    rig[..., 3] = oral
                    self.put(rig_path, rig)
                for frame in record["frames"][family].values():
                    path = "assets/expressions/complete-expressions/" + frame["path"]
                    if digest(self.original(path)) != frame["sha256"]:
                        raise ValueError(f"Complete-frame source pin changed: {path}")
                self.metrics.append({"pose": pose, "family": family, **metrics})
                self.lip_layers(pose, family, original[..., 3], oral)
        write_json(self.evidence / "contour-metrics.json", self.metrics)

    def lip_layers(self, pose: str, family: str, old_oral: np.ndarray, oral: np.ndarray) -> None:
        """Cut the smooth aperture and soften its finite exterior alpha band."""
        left, top, right, bottom = ROI
        for variant in self.pack["makeup"][0]["variants"]:
            for row in variant["mouth_states"][family][pose]:
                if row["slot"] != "lips":
                    continue
                path = self.staging / row["path"]
                data = path.read_bytes()
                if digest(data) != row["sha256"]:
                    raise ValueError(f"Cosmetic source pin changed: {row['path']}")
                original = pixels(data)
                fixed = original.copy()
                alpha = original[top:bottom, left:right, 3]
                # Transparent baked cutout pixels have zero RGB. Retain their
                # zero coverage and soften only the finite exterior edge band;
                # restoring their alpha would introduce black pigment.
                opening = oral[top:bottom, left:right]
                distance = cv2.distanceTransform((opening == 0).astype(np.uint8),
                                                cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
                exterior = np.clip((distance - .5) / 1.5, 0, 1)
                retention = np.minimum(1 - opening / OPAQUE, exterior)
                fixed[top:bottom, left:right, 3] = np.rint(alpha * retention).astype(np.uint8)
                self.pins[f"{PACK}!/{row['path']}"] = digest(data)
                backup = self.evidence / "lip-backups" / row["path"]
                backup.parent.mkdir(parents=True, exist_ok=True)
                backup.write_bytes(data)
                buffer = io.BytesIO()
                Image.fromarray(fixed).save(buffer, format="PNG")
                payload = buffer.getvalue()
                path.write_bytes(payload)
                row["sha256"] = digest(payload)


def install_candidate(evidence: Path) -> None:
    """Install the already sealed candidate after checking every recorded pin."""
    receipt_path = evidence / "receipt.json"
    receipt = json.loads(receipt_path.read_text("utf-8"))
    if receipt.get("installation_blocked"):
        raise ValueError("Candidate was rejected and cannot be installed")
    builder = MakeupEdgeRepair(ROOT, evidence, True)
    builder.eyes_only = False
    for relative, expected in receipt["inputs"].items():
        if "!/" in relative:
            continue
        payload = builder.original(relative)
        if digest(payload) != expected:
            raise ValueError(f"Candidate input backup changed: {relative}")
        if "/frames/" in relative and digest((ROOT / relative).read_bytes()) != expected:
            raise ValueError(f"Native complete frame changed: {relative}")
    for row in receipt["files"]:
        relative = row["path"]
        candidate = evidence / ("candidate.mohan-outfit" if relative == PACK else "candidate/" + relative)
        payload = candidate.read_bytes()
        if digest(payload) != row["after_sha256"]:
            raise ValueError(f"Sealed candidate changed: {relative}")
        builder.changes[relative] = payload
    builder.install()
    installed = json.loads(receipt_path.read_text("utf-8"))
    installed.update({key: value for key, value in receipt.items() if key not in {"files", "inputs", "applied"}})
    installed["applied"] = True
    write_json(receipt_path, installed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--install-candidate", action="store_true", help="Verify pins and install the sealed candidate without rebuilding")
    parser.add_argument("--evidence", type=Path, default=ROOT / ".quality-tmp/mouth-edge-1/round2/alpha-repair")
    args = parser.parse_args()
    if args.install_candidate:
        install_candidate(args.evidence.resolve())
        return
    from application.character_runtime_bootstrap import activate_product_character_runtime
    activate_product_character_runtime(ROOT)
    builder = MakeupEdgeRepair(ROOT, args.evidence.resolve(), args.apply)
    builder.prepare()
    builder.repair()
    builder.seal()
    builder.install()
    receipt_path = builder.evidence / "receipt.json"
    receipt = json.loads(receipt_path.read_text("utf-8"))
    receipt.update(method="8x continuous cosmetic aperture alpha; complete RGB unchanged",
                   target_poses=builder.targets, roi=ROI, complete_frames_modified=0)
    write_json(receipt_path, receipt)


if __name__ == "__main__":
    main()
