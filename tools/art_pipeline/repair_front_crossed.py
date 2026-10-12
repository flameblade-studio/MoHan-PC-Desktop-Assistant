"""Transplant approved attentive-front mouths with a pinned similarity transform.

Round-four authorisation accepts <=2 px geometry residual, 6 px expansion and
8 px finite feather. Eye rigs and all pixels outside this support are retained.
Candidate creation is isolated; --apply installs the same verified candidate.
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
    PACK, SIZE, STATES, RigBuilder, digest, mask_rgba, write_json,
)

# Five-point all-landmark fit, 17x17 patches, round3/geometry.json.
TARGET_TO_DONOR = ((.9998496701740691, .004209057234445812, -2.126534933241573),
                   (-.004209057234445812, .9998496701740691, 1.6295989696702167))
GEOMETRY_PINS = {
    "front-crossed": "01d7ab6c3a0b82a7b9a33e09b005c9f5bfac8340625bea43868597d73cab43ab",
    "front-attentive_front": "494eb61dff8e6d1cf44ad6e9e57699e00036f69de967903a5c34b9b60e11bcf8",
}
RESIDUAL_LIMIT_PX = 2
MAX_RESIDUAL_PX = 1.8045809005447888
MOUTH_ROI = (558, 538, 664, 588)
EXPANSION_PX = 6
FEATHER_PX = 8
MOUTH_FAMILIES = ("a", "o", "small")


def pixels(payload: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(payload)) as image:
        return np.asarray(image.convert("RGBA")).copy()


def support_weight() -> np.ndarray:
    """Full donor ownership across lips, finite cosine feather in nearby skin."""
    left, top, right, bottom = MOUTH_ROI
    yy, xx = np.mgrid[:SIZE[1], :SIZE[0]]
    dx = np.maximum(np.maximum(left - EXPANSION_PX - xx, xx - (right + EXPANSION_PX)), 0)
    dy = np.maximum(np.maximum(top - EXPANSION_PX - yy, yy - (bottom + EXPANSION_PX)), 0)
    distance = np.hypot(dx, dy)
    return np.where(distance < FEATHER_PX,
                    .5 * (1 + np.cos(np.pi * np.minimum(distance, FEATHER_PX) / FEATHER_PX)), 0)


def aligned(layer: np.ndarray, *, premultiplied: bool) -> np.ndarray:
    """Apply the one similarity registration with cubic subpixel resampling."""
    source = layer.astype(np.float32)
    if premultiplied:
        source[..., :3] *= source[..., 3:4] / 255
    transform = cv2.invertAffineTransform(np.asarray(TARGET_TO_DONOR, dtype=np.float64))
    result = cv2.warpAffine(source, transform, SIZE, flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_CONSTANT)
    result[..., 3] = np.clip(result[..., 3], 0, 255)
    if premultiplied:
        result[..., :3] = np.divide(result[..., :3] * 255, result[..., 3:4],
                                    out=np.zeros_like(result[..., :3]), where=result[..., 3:4] > 0)
    return np.clip(np.rint(result), 0, 255).astype(np.uint8)


class MouthTransplant(RigBuilder):
    """Use V5 pack sealing and pinned backups while preserving accepted eyes."""

    def transplant(self) -> None:
        if MAX_RESIDUAL_PX > RESIDUAL_LIMIT_PX:
            raise ValueError("Geometry exceeds the owner's round-four threshold")
        for pose, expected in GEOMETRY_PINS.items():
            relative = f"assets/expressions/complete-expressions/frames/{pose}-neutral-rest.rgba.png"
            if digest(self.original(relative)) != expected:
                raise ValueError(f"Measured geometry source changed: {pose}")
        self.region = self.safe["silhouettes"]["front-crossed"]
        weight = support_weight()
        self.put("assets/front-makeup-rigs/front-crossed-mouth-transplant-support.png",
                 mask_rgba(np.rint(weight * 255).astype(np.uint8)))
        self.frame_diffs = []
        donor_pose = self.complete["poses"]["front-attentive_front"]
        target_pose = self.complete["poses"]["front-crossed"]
        for family in MOUTH_FAMILIES:
            for state in STATES:
                relative = f"assets/expressions/complete-expressions/frames/front-crossed-{family}-{state}.rgba.png"
                donor_path = f"assets/expressions/complete-expressions/frames/front-attentive_front-{family}-{state}.rgba.png"
                base = pixels(self.original(relative))
                donor_bytes = self.original(donor_path)
                donor_record = donor_pose["frames"][family][state]
                if digest(donor_bytes) != donor_record["sha256"]:
                    raise ValueError(f"Donor frame pin changed: {donor_path}")
                donor = aligned(pixels(donor_bytes), premultiplied=False)
                result = base.copy()
                result[..., :3] = np.rint(base[..., :3] * (1 - weight[..., None]) +
                                          donor[..., :3] * weight[..., None]).astype(np.uint8)
                changed = np.any(result != base, axis=2)
                outside = int(np.count_nonzero(changed & (weight == 0)))
                if outside:
                    raise ValueError(f"Transplant escapes support: {relative}")
                descriptor = self.put(relative, result)
                target_pose["frames"][family][state]["sha256"] = descriptor["sha256"]
                target_pose["frames"][family][state]["repair"] = {
                    "tool": "tools/art_pipeline/repair_front_crossed.py",
                    "original_sha256": self.pins[relative], "donor": donor_path,
                    "donor_sha256": digest(donor_bytes), "target_to_donor": TARGET_TO_DONOR,
                    "mouth_roi": MOUTH_ROI, "expansion_px": EXPANSION_PX,
                    "feather_px": FEATHER_PX, "affine_micro_adjustment": None,
                }
                self.frame_diffs.append({"path": relative, "changed_pixels": int(changed.sum()),
                                         "outside_support_pixels": outside})
            record = donor_pose["oral_masks"][family]
            donor_path = "assets/expressions/complete-expressions/" + record["path"]
            payload = self.original(donor_path)
            if digest(payload) != record["sha256"]:
                raise ValueError(f"Oral donor pin changed: {donor_path}")
            oral = aligned(pixels(payload), premultiplied=True)
            oral[weight == 0] = 0
            descriptor = self.put(f"assets/expressions/complete-expressions/masks/front-crossed-transplant-oral-{family}.png", oral)
            target_pose["oral_masks"][family] = {"path": "masks/" + Path(descriptor["path"]).name,
                                               "sha256": descriptor["sha256"]}
            self.put(f"assets/front-makeup-rigs/front-crossed-{family}_oral_cavity.png", oral)
            for role in ("lip_upper", "lip_lower", "teeth_tongue"):
                # V5's lip/teeth exclusion layers are intentionally empty;
                # native lip/teeth texture remains owned by the complete frame.
                path = f"assets/front-makeup-rigs/front-attentive_front_{role}.png"
                layer = aligned(pixels(self.original(path)), premultiplied=True)
                layer[weight == 0] = 0
                self.put(f"assets/front-makeup-rigs/front-crossed-{family}_{role}.png", layer)
            self.makeup_family(family, weight)
        write_json(self.evidence / "transplant.json", {
            "target_to_donor": TARGET_TO_DONOR, "max_residual_px": MAX_RESIDUAL_PX,
            "mouth_roi": MOUTH_ROI, "expansion_px": EXPANSION_PX,
            "feather_px": FEATHER_PX, "affine_micro_adjustment": None,
            "resampling": "bicubic; premultiplied RGBA for detachable rigs",
            "frame_differences": self.frame_diffs, "inputs": self.pins,
        })

    def makeup_family(self, family: str, weight: np.ndarray) -> None:
        """Register detachable lip pigment with the frame transform."""
        for variant in self.pack["makeup"][0]["variants"]:
            source = next(row for row in variant["mouth_states"][family]["front-attentive_front"] if row["slot"] == "lips")
            data = (self.staging / source["path"]).read_bytes()
            if digest(data) != source["sha256"]:
                raise ValueError(f"Lip donor pin changed: {source['path']}")
            self.pins[f"{PACK}!/{source['path']}"] = digest(data)
            layer = aligned(pixels(data), premultiplied=True)
            layer[weight == 0] = 0
            # Retain the V5 declared safe-region contract.
            allowed = np.zeros(SIZE[::-1], dtype=bool)
            for x, y, width, height in self.region["slots"]["lips"]:
                allowed[y:y + height, x:x + width] = True
            layer[~allowed] = 0
            relative = f"assets/front-transplant-{variant['id']}-{family}-lips.png"
            buffer = io.BytesIO()
            Image.fromarray(layer).save(buffer, format="PNG")
            data = buffer.getvalue()
            (self.staging / relative).write_bytes(data)
            variant["mouth_states"][family]["front-crossed"] = [
                {**source, "path": relative, "sha256": digest(data)}]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--evidence", type=Path, default=ROOT / ".quality-tmp/front-fix/round4/repair")
    args = parser.parse_args()
    from application.character_runtime_bootstrap import activate_product_character_runtime
    activate_product_character_runtime(ROOT)
    builder = MouthTransplant(ROOT, args.evidence.resolve(), args.apply)
    builder.prepare()
    builder.transplant()
    builder.eyes_only = False
    builder.seal()
    builder.install()
    receipt_path = builder.evidence / "receipt.json"
    receipt = json.loads(receipt_path.read_text("utf-8"))
    receipt.update(method="attentive_front mouth ROI similarity transplant",
                   mouth_stage="round4_similarity_candidate", eyes_preserved=True)
    write_json(receipt_path, receipt)


if __name__ == "__main__":
    main()
