from __future__ import annotations

lazy import contextlib
lazy import hashlib
lazy from importlib import import_module
lazy import sys
lazy from collections.abc import Callable, Iterator
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

lazy import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools.verify_multimodal_model_assets import ExpectedModel, verify


MODEL_FIXTURES = (
    (
        "assets/vision-models/face_landmark_468.tflite",
        b"face model fixture data",
        "https://example.test/face_landmark_468.tflite",
        "face-landmark-revision",
        "Apache-2.0",
    ),
    (
        "assets/vision-models/iris_landmark.tflite",
        b"iris model fixture data",
        "https://example.test/iris_landmark.tflite",
        "iris-landmark-revision",
        "Apache-2.0",
    ),
    (
        "assets/vision-models/silero_vad_v4.0.onnx",
        b"silero vad fixture data",
        "https://example.test/silero_vad_v4.0.onnx",
        "v4.0",
        "MIT",
    ),
)

ModelFixture = tuple[str, bytes, str, str, str]
ExpectedBundle = tuple[tuple[ExpectedModel, bytes], ...]


def _build_expected_bundle() -> ExpectedBundle:
    expected: list[tuple[ExpectedModel, bytes]] = []
    for path, payload, source, revision, license_name in MODEL_FIXTURES:
        digest = hashlib.sha256(payload).hexdigest()
        expected.append(
            (
                ExpectedModel(
                    path=path,
                    size_bytes=len(payload),
                    sha256=digest,
                    source=source,
                    source_revision=revision,
                    license_name=license_name,
                ),
                payload,
            )
        )
    return tuple(expected)


def _as_toml_string(records: tuple[dict[str, object], ...]) -> str:
    lines: list[str] = []
    for record in records:
        lines.append("[[asset]]")
        for key in ("path", "sha256", "size_bytes", "source", "source_revision", "license"):
            value = record[key]
            if isinstance(value, str):
                lines.append(f'{key} = "{value}"')
            else:
                lines.append(f"{key} = {value}")
        lines.append("")
    return "\n".join(lines)


def _write_sbom(root: Path, records: tuple[dict[str, object], ...]) -> None:
    components = root / "sbom"
    components.mkdir(parents=True, exist_ok=True)
    (components / "components.toml").write_text(
        _as_toml_string(records),
        encoding="utf-8",
    )


def _build_workspace(root: Path, bundle: ExpectedBundle) -> None:
    records: list[dict[str, object]] = []
    for model, payload in bundle:
        asset = root / model.path
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(payload)
        records.append(
            {
                "path": model.path,
                "sha256": model.sha256,
                "size_bytes": model.size_bytes,
                "source": model.source,
                "source_revision": model.source_revision,
                "license": model.license_name,
            }
        )
    _write_sbom(root, tuple(records))


@contextlib.contextmanager
def _patched_expected_models(bundle: tuple[ExpectedModel, ...]) -> Iterator[None]:
    multimodal_tool = import_module("tools.verify_multimodal_model_assets")
    original = multimodal_tool.EXPECTED_MODELS
    multimodal_tool.EXPECTED_MODELS = bundle
    try:
        yield
    finally:
        multimodal_tool.EXPECTED_MODELS = original


def _scenario_matching_models(root: Path) -> None:
    expected = _build_expected_bundle()
    _build_workspace(root, expected)
    with _patched_expected_models(tuple(model for model, _ in expected)):
        verify(root)


def _scenario_missing_model(root: Path) -> None:
    expected = _build_expected_bundle()
    _build_workspace(root, expected)
    missing = root / expected[1][0].path
    missing.unlink()
    with _patched_expected_models(tuple(model for model, _ in expected)):
        with pytest.raises(SystemExit) as failure:
            verify(root)
    assert expected[1][0].path in str(failure.value)


def _scenario_hash_mismatch(root: Path) -> None:
    expected = _build_expected_bundle()
    _build_workspace(root, expected)
    target = root / expected[0][0].path
    payload = bytearray(target.read_bytes())
    payload[0] ^= 0xFF
    target.write_bytes(payload)
    with _patched_expected_models(tuple(model for model, _ in expected)):
        with pytest.raises(SystemExit) as failure:
            verify(root)
    assert f"SHA-256 mismatch for {expected[0][0].path}:" in str(failure.value)


def _scenario_corrupt_manifest(root: Path) -> None:
    expected = _build_expected_bundle()
    _build_workspace(root, expected)
    (root / "sbom" / "components.toml").write_text(
        'asset = "this is not a list"',
        encoding="utf-8",
    )
    with _patched_expected_models(tuple(model for model, _ in expected)):
        with pytest.raises(ValueError, match="asset records must be a list"):
            verify(root)


def _run_with_temp_root(action: Callable[[Path], None], prefix: str) -> None:
    with TemporaryDirectory(prefix=prefix) as temporary:
        action(Path(temporary))


def test_verify_multimodal_model_assets_pass_when_inputs_match() -> None:
    _run_with_temp_root(_scenario_matching_models, "mohan-mmverify-multimodal-")


def test_verify_multimodal_model_assets_missing_model_is_reported() -> None:
    _run_with_temp_root(_scenario_missing_model, "mohan-mmverify-multimodal-")


def test_verify_multimodal_model_assets_hash_mismatch_is_reported() -> None:
    _run_with_temp_root(_scenario_hash_mismatch, "mohan-mmverify-multimodal-")


def test_verify_multimodal_model_assets_corrupt_sbom_is_reported() -> None:
    _run_with_temp_root(_scenario_corrupt_manifest, "mohan-mmverify-multimodal-")


def main() -> int:
    for action in (
        _scenario_matching_models,
        _scenario_missing_model,
        _scenario_hash_mismatch,
        _scenario_corrupt_manifest,
    ):
        _run_with_temp_root(action, "mohan-mmverify-multimodal-")
    print("MULTIMODAL_MODEL_ASSETS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
