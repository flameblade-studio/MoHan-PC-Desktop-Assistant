from __future__ import annotations

lazy import hashlib
lazy import tomllib
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAND_MODELS = {
    "palm_detection_mediapipe_2023feb.onnx": {
        "sha256": "78ff51c38496b7fc8b8ebdb6cc8c1abb02fa6c38427c6848254cdaba57fcce7c",
        "size_bytes": 3_905_734,
        "revision": "8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5",
    },
    "handpose_estimation_mediapipe_2023feb.onnx": {
        "sha256": "db0898ae717b76b075d9bf563af315b29562e11f8df5027a1ef07b02bef6d81c",
        "size_bytes": 4_099_621,
        "revision": "56cef36ae45e5a6da7eba01a91631f6d7e955da1",
    },
}


def _registered_assets() -> dict[str, dict[str, object]]:
    manifest = tomllib.loads(
        (ROOT / "sbom" / "components.toml").read_text(encoding="utf-8")
    )
    return {Path(row["path"]).name: row for row in manifest["asset"]}


def test_hand_model_assets_match_the_packaging_manifest() -> None:
    assets = _registered_assets()
    assert set(HAND_MODELS).issubset(assets)
    for filename, expected in HAND_MODELS.items():
        registered = assets[filename]
        relative_path = f"assets/vision-models/{filename}"
        assert registered["path"] == relative_path
        assert registered["type"] == "machine-learning-model"
        assert registered["profiles"] == ["windows"]
        assert registered["license"] == "Apache-2.0"
        assert registered["source_revision"] == expected["revision"]
        assert expected["revision"] in registered["source"]
        assert registered["sha256"] == expected["sha256"]
        assert registered["size_bytes"] == expected["size_bytes"]

        model = ROOT / relative_path
        content = model.read_bytes()
        assert len(content) == expected["size_bytes"]
        assert hashlib.sha256(content).hexdigest() == expected["sha256"]


def test_windows_release_packages_the_complete_assets_tree() -> None:
    build_script = (ROOT / "build.ps1").read_text(encoding="utf-8")
    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    assert build_script.count('--add-data "assets;assets"') == 1
    assert release_workflow.count(r".\build.ps1") == 1
    for filename in HAND_MODELS:
        model = ROOT / "assets" / "vision-models" / filename
        assert model.is_file()
        assert model.is_relative_to(ROOT / "assets")
