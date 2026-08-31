from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    build_lines = [line.strip() for line in cv2.getBuildInformation().splitlines()]
    build_features = {
        "png": next((line for line in build_lines if line.startswith("PNG:")), None),
        "ffmpeg": next((line for line in build_lines if line.startswith("FFMPEG:")), None),
        "zlib": next((line for line in build_lines if line.startswith("ZLib:")), None),
    }
    rgba = np.zeros((24, 32, 4), dtype=np.uint8)
    rgba[..., 0] = np.arange(32, dtype=np.uint8)[None, :]
    rgba[..., 1] = np.arange(24, dtype=np.uint8)[:, None]
    rgba[..., 2] = 173
    rgba[4:20, 6:26, 3] = 255
    rgba[8:16, 10:22, 3] = 127

    png_path = ROOT / "cv2-rgba-roundtrip.png"
    if not cv2.imwrite(str(png_path), rgba):
        raise RuntimeError("cv2.imwrite returned false")
    decoded = cv2.imread(str(png_path), cv2.IMREAD_UNCHANGED)
    if decoded is None:
        raise RuntimeError("cv2.imread returned None")
    if decoded.shape != rgba.shape or decoded.dtype != rgba.dtype:
        raise AssertionError((decoded.shape, decoded.dtype))
    if not np.array_equal(decoded, rgba):
        raise AssertionError("RGBA bytes changed during PNG round trip")

    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[8:56, 12:52] = 255
    distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    if distance.shape != mask.shape or distance.dtype != np.float32:
        raise AssertionError((distance.shape, distance.dtype))
    if not float(distance[32, 32]) > float(distance[8, 12]):
        raise AssertionError("distance transform did not increase toward center")
    preview = np.rint(distance / distance.max() * 255).astype(np.uint8)
    distance_path = ROOT / "cv2-distance-transform.png"
    if not cv2.imwrite(str(distance_path), preview):
        raise RuntimeError("distance preview write failed")

    result = {
        "schema": "mohan.cv2-functional-smoke.v1",
        "functional_only_not_license_admission": True,
        "cv2_version": cv2.__version__,
        "numpy_version": np.__version__,
        "cv2_build_features": build_features,
        "rgba_roundtrip": {
            "shape": list(decoded.shape),
            "dtype": str(decoded.dtype),
            "exact_equal": True,
            "sha256": sha256(png_path),
        },
        "distance_transform": {
            "shape": list(distance.shape),
            "dtype": str(distance.dtype),
            "minimum": float(distance.min()),
            "maximum": float(distance.max()),
            "center": float(distance[32, 32]),
            "preview_sha256": sha256(distance_path),
        },
    }
    result_path = ROOT / "cv2-functional-smoke.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
