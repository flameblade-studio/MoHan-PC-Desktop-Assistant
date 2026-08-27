from __future__ import annotations

lazy import argparse
lazy import math
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np

RGBA_CHANNELS = 4
MAX_COMPRESSION = 0.08


def _detect(image: np.ndarray, model: Path) -> np.ndarray:
    detector = cv2.FaceDetectorYN.create(
        str(model),
        "",
        (image.shape[1], image.shape[0]),
        0.75,
        0.3,
        100,
    )
    _status, faces = detector.detect(image[:, :, :3])
    if faces is None or len(faces) != 1:
        count = 0 if faces is None else len(faces)
        raise ValueError(f"expected one face, detected {count}")
    return faces[0]


def _forehead_remap_grids(
    image_shape: tuple[int, ...],
    band: tuple[int, int],
    span: tuple[int, int],
    anchor: float,
    compression: float,
) -> tuple[np.ndarray, np.ndarray]:
    band_top, band_bottom = band
    left, right = span
    map_x, map_y = np.meshgrid(
        np.arange(image_shape[1], dtype=np.float32),
        np.arange(image_shape[0], dtype=np.float32),
    )
    for row in range(band_top, band_bottom):
        progress = (row - band_top) / max(1, band_bottom - band_top - 1)
        envelope = math.sin(math.pi * progress) ** 2
        scale = 1.0 - compression * envelope
        # Inverse mapping: sampling farther from the fixed hair-side anchor
        # moves only the outward forehead silhouette inward.
        map_x[row, left:right] = anchor + (
            map_x[row, left:right] - anchor
        ) / scale
    return map_x, map_y


def smooth_forehead(
    source_path: Path,
    output_path: Path,
    detector_model: Path,
    *,
    compression: float = 0.04,
) -> None:
    image = cv2.imread(str(source_path), cv2.IMREAD_UNCHANGED)
    if image is None or image.shape[2] != RGBA_CHANNELS:
        raise ValueError("source must be a decodable RGBA PNG")
    face = _detect(image, detector_model)
    x, y, width, height = (float(value) for value in face[:4])
    landmarks = face[4:14].reshape(5, 2)
    nose_x = float(landmarks[2, 0])
    facing_right = nose_x > x + width * 0.5

    # Limit the deformation to the upper forehead. The eyes, nose, mouth and
    # jaw are below this band and therefore remain byte-for-byte unchanged.
    band_top = max(0, int(math.floor(y + height * 0.04)))
    band_bottom = min(image.shape[0], int(math.ceil(y + height * 0.38)))
    pad = int(math.ceil(width * 0.12))
    left = max(0, int(math.floor(x)) - pad)
    right = min(image.shape[1], int(math.ceil(x + width)) + pad)
    anchor = float(left if facing_right else right - 1)

    map_x, map_y = _forehead_remap_grids(
        image.shape,
        (band_top, band_bottom),
        (left, right),
        anchor,
        compression,
    )

    candidate = cv2.remap(
        image,
        map_x,
        map_y,
        interpolation=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    # Outside the deformation band, preserve the source exactly.
    candidate[:band_top] = image[:band_top]
    candidate[band_bottom:] = image[band_bottom:]
    candidate[:, :left] = image[:, :left]
    candidate[:, right:] = image[:, right:]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), candidate):
        raise OSError(f"could not write {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a local, non-destructive profile-forehead candidate."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--detector-model",
        type=Path,
        default=Path("assets/vision-models/face_detection_yunet_2023mar.onnx"),
    )
    parser.add_argument("--compression", type=float, default=0.04)
    args = parser.parse_args()
    if not 0.0 < args.compression <= MAX_COMPRESSION:
        raise ValueError(f"compression must be in (0, {MAX_COMPRESSION}]")
    smooth_forehead(
        args.source,
        args.output,
        args.detector_model,
        compression=args.compression,
    )


if __name__ == "__main__":
    main()
