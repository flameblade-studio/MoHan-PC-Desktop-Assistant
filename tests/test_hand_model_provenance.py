from __future__ import annotations

lazy import hashlib
lazy import json
lazy import re
lazy import tomllib
lazy from pathlib import Path

lazy import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "HAND-MODEL-PROVENANCE.md"
EVIDENCE = ROOT / "docs" / "HAND-MODEL-PROVENANCE.json"
ASSET_ROOT = ROOT / "assets" / "vision-models"
EXPECTED = {
    "palm_detection_mediapipe_2023feb.onnx": {
        "commit": "8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5",
        "sha256": "78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c",
        "size_bytes": 3_905_734,
    },
    "handpose_estimation_mediapipe_2023feb.onnx": {
        "commit": "56cef36ae45e5a6da7eba01a91631f6d7e955da1",
        "sha256": "db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c",
        "size_bytes": 4_099_621,
    },
}


def _document() -> str:
    return DOCUMENT.read_text(encoding="utf-8")


def _evidence() -> dict[str, object]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_provenance_contract_is_complete_immutable_and_four_language() -> None:
    document = _document()
    headings = ("## 繁體中文", "## 简体中文", "## English", "## 日本語")
    assert tuple(document.index(heading) for heading in headings) == tuple(
        sorted(document.index(heading) for heading in headings)
    )
    evidence = _evidence()
    assert evidence["schema"] == "mohan-hand-model-provenance-v1"
    assert evidence["repository"] == "https://github.com/opencv/opencv_zoo"
    assert evidence["license"] == "Apache-2.0"
    models = {item["filename"]: item for item in evidence["models"]}
    assert set(models) == set(EXPECTED)
    for filename, expected in EXPECTED.items():
        model = models[filename]
        assert model["commit"] == expected["commit"]
        assert model["sha256"] == expected["sha256"]
        assert model["lfs_oid_sha256"] == expected["sha256"]
        assert model["size_bytes"] == expected["size_bytes"]
        assert re.fullmatch(r"[0-9a-f]{40}", model["commit"])
        assert re.fullmatch(r"[0-9a-f]{64}", model["sha256"])
        for key in ("pointer_url", "readme_url", "license_url"):
            assert model["commit"] in model[key]
            assert "/main/" not in model[key]
        assert filename in document
        assert expected["commit"] in document
        assert expected["sha256"] in document
    starts = tuple(document.index(heading) + len(heading) for heading in headings)
    ends = (
        *tuple(document.index(headings[index + 1]) for index in range(3)),
        len(document),
    )
    sections = tuple(document[start:end] for start, end in zip(starts, ends, strict=True))
    for section in sections:
        assert "Apache-2.0" in section or "Apache License 2.0" in section
        assert "assets/vision-models/" in section
        for filename, expected in EXPECTED.items():
            assert filename in section
            assert expected["commit"] in section
            assert expected["sha256"] in section
            assert f"{expected['size_bytes']:,}" in section


@pytest.mark.parametrize("filename", tuple(EXPECTED))
def test_actual_hand_model_asset_gate(filename: str) -> None:
    """A skipped asset gate is explicitly incomplete, never a provenance pass."""

    path = ASSET_ROOT / filename
    if not path.is_file():
        pytest.skip(f"ACTUAL_ASSET_MISSING: {filename}")
    expected = EXPECTED[filename]
    content = path.read_bytes()
    assert not content.startswith(b"version https://git-lfs.github.com/spec/v1")
    assert len(content) == expected["size_bytes"]
    assert hashlib.sha256(content).hexdigest() == expected["sha256"]


def test_hand_models_are_registered_for_windows_packaging() -> None:
    registry = tomllib.loads((ROOT / "sbom" / "components.toml").read_text(encoding="utf-8"))
    assets = {Path(item["path"]).name: item for item in registry["asset"]}
    for filename, expected in EXPECTED.items():
        asset = assets[filename]
        assert asset["path"] == f"assets/vision-models/{filename}"
        assert asset["sha256"] == expected["sha256"]
        assert asset["size_bytes"] == expected["size_bytes"]
        assert asset["source_revision"] == expected["commit"]
        assert expected["commit"] in asset["source"]
        assert asset["license"] == "Apache-2.0"
        assert asset["profiles"] == ["windows"]
    build_script = (ROOT / "build.ps1").read_text(encoding="utf-8")
    assert '--add-data "assets;assets"' in build_script
