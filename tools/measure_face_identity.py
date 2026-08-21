from __future__ import annotations

lazy import argparse
lazy import json
lazy import math
lazy from pathlib import Path

lazy from domain.constants import FLOAT_COMPARISON_EPSILON


def _embedding(
    image_path: Path,
    detector_model: Path,
    recognizer_model: Path,
) -> tuple[float, ...]:
    import cv2

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Cannot decode image: {image_path}")
    detector = cv2.FaceDetectorYN.create(
        str(detector_model),
        "",
        (image.shape[1], image.shape[0]),
        0.75,
        0.3,
        100,
    )
    recognizer = cv2.FaceRecognizerSF.create(str(recognizer_model), "")
    _status, faces = detector.detect(image)
    if faces is None or len(faces) != 1:
        raise ValueError(
            f"Expected exactly one detectable face in {image_path}; "
            f"found {0 if faces is None else len(faces)}."
        )
    aligned = recognizer.alignCrop(image, faces[0])
    return tuple(float(value) for value in recognizer.feature(aligned).flatten())


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Face embeddings must use the same non-zero dimension.")
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm < FLOAT_COMPARISON_EPSILON or right_norm < FLOAT_COMPARISON_EPSILON:
        raise ValueError("Face embedding norm must not be zero.")
    return dot / (left_norm * right_norm)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare locally rendered MoHan face assets with bundled YuNet/SFace; "
            "no embedding is persisted."
        )
    )
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidates", nargs="+", type=Path)
    parser.add_argument(
        "--models",
        type=Path,
        default=Path("assets/vision-models"),
    )
    args = parser.parse_args()
    detector = args.models / "face_detection_yunet_2023mar.onnx"
    recognizer = args.models / "face_recognition_sface_2021dec.onnx"
    reference = _embedding(args.reference, detector, recognizer)
    results = []
    for candidate in args.candidates:
        try:
            similarity = cosine_similarity(
                reference,
                _embedding(candidate, detector, recognizer),
            )
            results.append(
                {
                    "candidate": str(candidate),
                    "similarity": round(similarity, 6),
                    "measured": True,
                }
            )
        except ValueError as error:
            results.append(
                {
                    "candidate": str(candidate),
                    "measured": False,
                    "reason": str(error),
                }
            )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
