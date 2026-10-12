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
MIN_CONTOUR_COLUMNS = 3
FAMILIES = ("small", "a", "o")
TEETH_RED_GREEN_GAP = 35
TEETH_RED_BLUE_GAP = 45
TEETH_GREEN_MIN = 65
TEETH_RED_MAX = 210
CAVITY_RED_MAX = 115
CAVITY_GREEN_MAX = 75
NATIVE_MOUTH_BOUNDS = (566, 550, 656, 580)
MIN_COMPONENT_COUNT = 2


def pixels(data: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(data)) as image:
        return np.asarray(image.convert("RGBA")).copy()


def classify_native_opening(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return the connected native opening and its low-chroma tooth pixels."""
    left, top, right, bottom = ROI
    red, green, blue = frame[top:bottom, left:right, :3].astype(float).transpose(2, 0, 1)
    yy, xx = np.mgrid[top:bottom, left:right]
    teeth = ((red - green < TEETH_RED_GREEN_GAP)
             & (red - blue < TEETH_RED_BLUE_GAP)
             & (green > TEETH_GREEN_MIN) & (red < TEETH_RED_MAX))
    cavity = (red < CAVITY_RED_MAX) & (green < CAVITY_GREEN_MAX)
    bounds = NATIVE_MOUTH_BOUNDS
    mouth = (xx > bounds[0]) & (xx < bounds[2]) & (yy > bounds[1]) & (yy < bounds[3])
    binary = ((teeth | cavity) & mouth).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
    if count < MIN_COMPONENT_COUNT:
        raise ValueError("The native frame has no measurable mouth opening")
    binary = (labels == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    return binary, teeth & (binary > 0)


def native_aperture(frame: np.ndarray) -> tuple[np.ndarray, dict]:
    """Measure teeth and dark cavity directly from the bare native frame.

    The mouth-local colour classifier separates low-chroma teeth and dark
    cavity from red lips. The largest connected component owns one continuous
    upper/lower envelope; the old cosmetic mask supplies no contour positions.
    """
    binary, teeth = classify_native_opening(frame)
    columns = np.flatnonzero(binary.any(axis=0))
    if len(columns) < MIN_CONTOUR_COLUMNS:
        raise ValueError("The native mouth opening has too few columns")
    xs = np.arange(columns[0], columns[-1] + 1)
    upper = np.interp(xs, columns, [np.flatnonzero(binary[:, x])[0] - .5 for x in columns])
    lower = np.interp(xs, columns, [np.flatnonzero(binary[:, x])[-1] + .5 for x in columns])
    kernel = np.array([1, 2, 3, 2, 1], dtype=float) / 9
    smooth_upper = np.convolve(np.pad(upper, 2, mode="edge"), kernel, "valid")
    smooth_lower = np.convolve(np.pad(lower, 2, mode="edge"), kernel, "valid")
    # Cover the native colour-transition pixels as well as the tooth cores.
    # Rounding never moves inward across a classified native boundary.
    smooth_upper = np.minimum(smooth_upper, upper) - .5
    smooth_lower = np.maximum(smooth_lower, lower) + .5
    coverage = rasterize_aperture(binary.shape, xs, smooth_upper, smooth_lower)
    result = np.zeros(frame.shape[:2], dtype=np.uint8)
    result[ROI[1]:ROI[3], ROI[0]:ROI[2]] = coverage
    return result, {"native_classified_pixels": int(binary.sum()),
                    "native_teeth_pixels": int(np.count_nonzero(teeth & (binary > 0))),
                    "maximum_inset_px": 0,
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


def extend_retracted_hole(patch: np.ndarray, old_opening: np.ndarray,
                          opening: np.ndarray) -> np.ndarray:
    """Extend nearest authored pigment into a former hard hole, where needed."""
    result = patch.copy()
    missing = (patch[..., 3] == 0) & (old_opening >= MIDPOINT) & (opening < OPAQUE)
    if not missing.any():
        return result
    transparent = (patch[..., 3] == 0).astype(np.uint8)
    _, labels = cv2.distanceTransformWithLabels(transparent, cv2.DIST_L2, 5,
                                               labelType=cv2.DIST_LABEL_PIXEL)
    lookup = np.zeros((int(labels.max()) + 1, 4), dtype=np.uint8)
    painted = patch[..., 3] > 0
    lookup[labels[painted]] = patch[painted]
    result[missing] = lookup[labels[missing]]
    return result


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
                native_frames = []
                for frame in record["frames"][family].values():
                    path = "assets/expressions/complete-expressions/" + frame["path"]
                    data = self.original(path)
                    if digest(data) != frame["sha256"]:
                        raise ValueError(f"Complete-frame source pin changed: {path}")
                    native_frames.append(pixels(data))
                # Blink states use one mouth mask: verify the source mouth agrees.
                left, top, right, bottom = ROI
                native = native_frames[0]
                if any(not np.array_equal(native[top:bottom, left:right],
                                          image[top:bottom, left:right]) for image in native_frames[1:]):
                    raise ValueError(f"Native mouth differs across eye states: {pose} {family}")
                oral, metrics = native_aperture(native)
                self.aperture_overlay(pose, family, native, oral)
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

    def aperture_overlay(self, pose: str, family: str, native: np.ndarray,
                         oral: np.ndarray) -> None:
        """Publish a three-times native/opening overlay for owner review."""
        left, top, right, bottom = ROI
        rgb = native[top:bottom, left:right, :3].astype(float)
        weight = oral[top:bottom, left:right, None] / OPAQUE * .45
        overlay = np.rint(rgb * (1 - weight) + np.array([0, 255, 0]) * weight).astype(np.uint8)
        image = Image.fromarray(overlay).resize(((right - left) * 3, (bottom - top) * 3), Image.Resampling.NEAREST)
        destination = self.evidence / "opening-overlays" / f"{pose}-{family}.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination)

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
                opening = oral[top:bottom, left:right]
                patch = extend_retracted_hole(original[top:bottom, left:right],
                                              old_oral[top:bottom, left:right], opening)
                fixed[top:bottom, left:right] = patch
                alpha = patch[..., 3]
                # Preserve the accepted exterior feather and authored RGB.
                # A larger native opening only subtracts extra pigment.
                retention = 1 - opening / OPAQUE
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
    parser.add_argument("--evidence", type=Path, default=ROOT / ".quality-tmp/mouth-edge-3/repair")
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
    receipt.update(method="native teeth/cavity colour segmentation; 8x aperture alpha; complete RGB unchanged",
                   target_poses=builder.targets, roi=ROI, complete_frames_modified=0)
    write_json(receipt_path, receipt)


if __name__ == "__main__":
    main()
