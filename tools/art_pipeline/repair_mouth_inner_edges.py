"""Diagnose rejected source-bound mouth contours inside a fixed ROI.

Pinned backups are the reproducible input. Native RGB is resampled only across
1.5 px contour bands; small-mouth teeth reuse the same pose's A endpoint.
The character canvas alpha and all non-mouth pixels remain byte-identical.
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

lazy from tools.art_pipeline.front_crossed_rig import (
    PACK, STATES, RigBuilder, digest, mask_rgba, write_json,
)

ROI = (548, 530, 686, 600)
SCALE = 8
EDGE_HALF_WIDTH = 1.5
FAMILIES = ("small", "a", "o")
ALPHA_MIDPOINT = 128
OPAQUE = 255
MIN_COLUMN_PIXELS = 2
MIN_CONTOUR_COLUMNS = 3
TOOTH_CHROMA_MAX = 50
TOOTH_CHANNEL_MIN = 70
TOOTH_BOUNDS = (589, 558, 625, 561)


def pixels(data: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as image:
        return np.asarray(image.convert("RGBA")).copy()


def aperture(alpha: np.ndarray) -> np.ndarray:
    """Fill threshold holes and interpolate continuous subpixel inner curves."""
    left, top, right, bottom = ROI
    binary = alpha[top:bottom, left:right] >= ALPHA_MIDPOINT
    counts = binary.sum(axis=0)
    valid = np.flatnonzero(counts >= MIN_COLUMN_PIXELS)
    if len(valid) < MIN_CONTOUR_COLUMNS:
        raise ValueError("The source aperture has no measurable inner contour")
    upper = np.array([np.flatnonzero(binary[:, x])[0] - .5 for x in valid])
    lower = np.array([np.flatnonzero(binary[:, x])[-1] + .5 for x in valid])
    xs = np.arange(valid[0], valid[-1] + 1)
    kernel = np.array([1, 2, 3, 2, 1], dtype=float) / 9
    upper = np.convolve(np.pad(np.interp(xs, valid, upper), 2, mode="edge"), kernel, "valid")
    lower = np.convolve(np.pad(np.interp(xs, valid, lower), 2, mode="edge"), kernel, "valid")
    points = np.concatenate((np.column_stack((xs, upper)), np.column_stack((xs[::-1], lower[::-1]))))
    high = np.zeros((binary.shape[0] * SCALE, binary.shape[1] * SCALE), dtype=np.uint8)
    cv2.fillPoly(high, [np.rint((points + .5) * SCALE).astype(np.int32)], 255)
    coverage = cv2.resize(high, (binary.shape[1], binary.shape[0]), interpolation=cv2.INTER_AREA)
    result = np.zeros_like(alpha)
    result[top:bottom, left:right] = coverage
    return result


def signed_distance(binary: np.ndarray) -> np.ndarray:
    source = binary.astype(np.uint8)
    return (cv2.distanceTransform(source, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
            - cv2.distanceTransform(1 - source, cv2.DIST_L2, cv2.DIST_MASK_PRECISE))


def contour_rgb(rgb: np.ndarray, coverage: np.ndarray) -> np.ndarray:
    """Resample opposite sides only in the finite contour band, keeping texture."""
    binary = coverage >= ALPHA_MIDPOINT
    distance = signed_distance(binary)
    weight = np.clip(.5 + distance / (2 * EDGE_HALF_WIDTH), 0, 1)
    # Use authored subpixel coverage on the immediate contour itself.
    fractional = (coverage > 0) & (coverage < OPAQUE)
    weight[fractional] = coverage[fractional] / 255
    sides = []
    for side in (binary, ~binary):
        support = cv2.boxFilter(side.astype(np.float32), -1, (5, 5), normalize=False)
        colors = cv2.boxFilter(rgb.astype(np.float32) * side[..., None], -1, (5, 5), normalize=False)
        sides.append(np.divide(colors, support[..., None], out=rgb.astype(np.float32).copy(), where=support[..., None] > 0))
    band = (np.abs(distance) <= EDGE_HALF_WIDTH) | fractional
    rebuilt = sides[0] * weight[..., None] + sides[1] * (1 - weight[..., None])
    result = rgb.copy()
    result[band] = np.clip(np.rint(rebuilt[band]), 0, 255).astype(np.uint8)
    return result


def repair_frame(frame: np.ndarray, oral: np.ndarray, donor: np.ndarray | None) -> np.ndarray:
    left, top, right, bottom = ROI
    result = frame.copy()
    rgb = frame[top:bottom, left:right, :3].copy()
    if donor is not None:
        # Measured common x positions; A's upper incisors occupy y=558..561.
        # Small's upper incisors share the same coordinates and midline.
        yy, xx = np.mgrid[top:bottom, left:right].astype(np.float32)
        mapped_y = yy
        tooth_color = cv2.remap(donor[..., :3], xx, mapped_y, cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_REFLECT_101)
        chroma = rgb.max(axis=2).astype(int) - rgb.min(axis=2)
        teeth = (chroma < TOOTH_CHROMA_MAX) & (rgb.min(axis=2) > TOOTH_CHANNEL_MIN)
        tooth_left, tooth_top, tooth_right, tooth_bottom = TOOTH_BOUNDS
        teeth &= (xx >= tooth_left) & (xx <= tooth_right) & (yy >= tooth_top) & (yy <= tooth_bottom)
        teeth = cv2.morphologyEx(teeth.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
        teeth &= (xx >= tooth_left) & (xx <= tooth_right) & (yy >= tooth_top) & (yy <= tooth_bottom)
        if not np.any(teeth):
            raise ValueError("No native incisors found for the same-pose donor")
        weight = np.clip(.5 + signed_distance(teeth) / (2 * EDGE_HALF_WIDTH), 0, 1)
        rgb = np.clip(np.rint(rgb * (1 - weight[..., None]) + tooth_color * weight[..., None]), 0, 255).astype(np.uint8)
    rgb = contour_rgb(rgb, oral[top:bottom, left:right])
    result[top:bottom, left:right, :3] = rgb
    return result


class MouthEdgeRepair(RigBuilder):
    """Reuse the sealed official pack workflow and keep one backup authority."""

    def repair(self) -> None:
        self.region = self.safe["silhouettes"]["front-crossed"]
        self.eyes_only = False
        self.metrics = []
        self.targets = [p for p in self.complete["poses"] if p.startswith("front-") and p.endswith("_front")] + ["front-crossed"]
        for pose in self.targets:
            record = self.complete["poses"][pose]
            for family in FAMILIES:
                oral_record = record["oral_masks"][family]
                relative = "assets/expressions/complete-expressions/" + oral_record["path"]
                original = pixels(self.original(relative))
                oral = aperture(original[..., 3])
                descriptor = self.put(relative, mask_rgba(oral))
                oral_record["sha256"] = descriptor["sha256"]
                if pose == "front-crossed":
                    self.put(f"assets/front-makeup-rigs/front-crossed-{family}_oral_cavity.png", mask_rgba(oral))
                for eye in STATES:
                    frame_record = record["frames"][family][eye]
                    path = "assets/expressions/complete-expressions/" + frame_record["path"]
                    original_frame = pixels(self.original(path))
                    donor_path = "assets/expressions/complete-expressions/" + record["frames"]["a"][eye]["path"]
                    donor = pixels(self.original(donor_path)) if family == "small" else None
                    fixed = repair_frame(original_frame, oral, donor)
                    changed = np.any(fixed != original_frame, axis=2)
                    left, top, right, bottom = ROI
                    outside = changed.copy()
                    outside[top:bottom, left:right] = False
                    alpha_changed = int(np.count_nonzero(fixed[..., 3] != original_frame[..., 3]))
                    if outside.any() or alpha_changed:
                        raise ValueError(f"Repair escaped the mouth RGB contract: {path}")
                    frame_record["sha256"] = self.put(path, fixed)["sha256"]
                    frame_record["inner_edge_repair"] = {
                        "tool": "tools/art_pipeline/repair_mouth_inner_edges.py",
                        "original_sha256": self.pins[path], "roi": ROI,
                        "supersampling": SCALE, "edge_half_width_px": EDGE_HALF_WIDTH,
                        "teeth_donor": donor_path if donor is not None else None,
                        "teeth_donor_sha256": self.pins[donor_path] if donor is not None else None,
                        "teeth_registration": {"x": "identity", "y": "identity"} if donor is not None else None,
                    }
                    self.metrics.append({"path": path, "changed_pixels": int(changed.sum()), "outside_roi_pixels": int(outside.sum()), "alpha_changed_pixels": alpha_changed})
                self.lip_layers(pose, family, oral)
        write_json(self.evidence / "pixel-contract.json", self.metrics)

    def lip_layers(self, pose: str, family: str, oral: np.ndarray) -> None:
        """Retreat cosmetic alpha smoothly before Qt's hard ownership clip."""
        left, top, right, bottom = ROI
        # Zero all subpixel aperture support. The hard runtime region can no
        # longer introduce a new edge; alpha ramps over the next 1.5 px.
        distance = cv2.distanceTransform((oral[top:bottom, left:right] == 0).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        retention = np.clip((distance - .5) / EDGE_HALF_WIDTH, 0, 1)
        for variant in self.pack["makeup"][0]["variants"]:
            for row in variant["mouth_states"][family][pose]:
                if row["slot"] != "lips":
                    continue
                path = self.staging / row["path"]
                data = path.read_bytes()
                layer = pixels(data)
                original_alpha = layer[top:bottom, left:right, 3].copy()
                layer[top:bottom, left:right, 3] = np.rint(original_alpha * retention).astype(np.uint8)
                buffer = io.BytesIO()
                Image.fromarray(layer).save(buffer, format="PNG")
                payload = buffer.getvalue()
                self.pins[f"{PACK}!/{row['path']}"] = digest(data)
                path.write_bytes(payload)
                row["sha256"] = digest(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--evidence", type=Path, default=ROOT / ".quality-tmp/mouth-edge-1/repair")
    args = parser.parse_args()
    if args.apply:
        raise ValueError("MOUTH-EDGE-1 failed its second incisor-texture review; candidates cannot be installed")
    from application.character_runtime_bootstrap import activate_product_character_runtime
    activate_product_character_runtime(ROOT)
    builder = MouthEdgeRepair(ROOT, args.evidence.resolve(), args.apply)
    builder.prepare()
    builder.repair()
    builder.seal()
    builder.install()
    receipt_path = builder.evidence / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt.update(method="8x source-bound aperture contours and finite 1.5 px RGB/alpha edges",
                   mouth_stage="rejected_second_incisor_review", visual_acceptance=False,
                   installation_blocked=True, target_poses=builder.targets, roi=ROI)
    write_json(receipt_path, receipt)


if __name__ == "__main__":
    main()
