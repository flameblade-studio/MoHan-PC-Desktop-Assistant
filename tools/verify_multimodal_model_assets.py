"""Verify the bundled multimodal model files and their SBOM records."""

from __future__ import annotations

lazy import hashlib
lazy import tomllib
lazy from dataclasses import dataclass
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class ExpectedModel:
    path: str
    size_bytes: int
    sha256: str
    source: str
    source_revision: str
    license_name: str


EXPECTED_MODELS = (
    ExpectedModel(
        path="assets/vision-models/face_landmark_468.tflite",
        size_bytes=1_242_398,
        sha256="1055cb9d4a9ca8b8c688902a3a5194311138ba256bcc94e336d8373a5f30c814",
        source="https://storage.googleapis.com/mediapipe-assets/face_landmark.tflite",
        source_revision="face_landmark.tflite",
        license_name="Apache-2.0",
    ),
    ExpectedModel(
        path="assets/vision-models/iris_landmark.tflite",
        size_bytes=2_640_568,
        sha256="d1744d2a09c25f501d39eba4faff47e53ecca8852c5ce19bce8eeac39357521f",
        source="https://storage.googleapis.com/mediapipe-assets/iris_landmark.tflite",
        source_revision="iris_landmark.tflite",
        license_name="Apache-2.0",
    ),
    ExpectedModel(
        path="assets/vision-models/silero_vad_v4.0.onnx",
        size_bytes=1_807_522,
        sha256="a35ebf52fd3ce5f1469b2a36158dba761bc47b973ea3382b3186ca15b1f5af28",
        source="https://github.com/snakers4/silero-vad/raw/v4.0/files/silero_vad.onnx",
        source_revision="v4.0",
        license_name="MIT",
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sbom_assets(root: Path) -> dict[str, dict[str, object]]:
    document = tomllib.loads(
        (root / "sbom" / "components.toml").read_text(encoding="utf-8")
    )
    records = document.get("asset", [])
    if not isinstance(records, list):
        raise ValueError("sbom/components.toml asset records must be a list")
    result: dict[str, dict[str, object]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("sbom/components.toml contains an invalid asset record")
        path = record.get("path")
        if isinstance(path, str):
            result[path] = record
    return result


def verify(root: Path = ROOT) -> None:
    assets = _sbom_assets(root)
    failures: list[str] = []

    for expected in EXPECTED_MODELS:
        path = root / expected.path
        record = assets.get(expected.path)
        if not path.is_file():
            failures.append(f"missing bundled model: {expected.path}")
            continue
        if record is None:
            failures.append(f"missing SBOM asset record: {expected.path}")
        else:
            checks = {
                "sha256": expected.sha256,
                "size_bytes": expected.size_bytes,
                "source": expected.source,
                "source_revision": expected.source_revision,
                "license": expected.license_name,
            }
            for key, value in checks.items():
                if record.get(key) != value:
                    failures.append(
                        f"SBOM mismatch for {expected.path}: {key}={record.get(key)!r}"
                    )

        actual_size = path.stat().st_size
        if actual_size != expected.size_bytes:
            failures.append(
                f"size mismatch for {expected.path}: {actual_size} != {expected.size_bytes}"
            )
        actual_sha = _sha256(path)
        if actual_sha != expected.sha256:
            failures.append(
                f"SHA-256 mismatch for {expected.path}: {actual_sha} != {expected.sha256}"
            )

    if failures:
        raise SystemExit("Multimodal model asset verification failed:\n" + "\n".join(failures))

    print(f"Verified {len(EXPECTED_MODELS)} bundled multimodal model assets.")


if __name__ == "__main__":
    verify()
