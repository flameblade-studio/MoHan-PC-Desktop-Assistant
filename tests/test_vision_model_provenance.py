from __future__ import annotations

lazy import hashlib
lazy import json
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "docs" / "VISION-MODEL-PROVENANCE.json"


def run() -> None:
    payload = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    assert payload["schema"] == "mohan-vision-model-provenance-v1"
    assert payload["repository"] == "https://github.com/opencv/opencv_zoo"
    models = payload["models"]
    assert len(models) == 3
    for model in models:
        commit = model["commit"]
        sha256 = model["sha256"]
        assert len(commit) == 40
        assert len(sha256) == 64
        assert model["lfs_oid_sha256"] == sha256
        for field in ("pointer_url", "download_url", "readme_url", "license_url"):
            assert commit in model[field]
            assert "opencv/opencv_zoo" in model[field]
        local = ROOT / "assets" / "vision-models" / model["filename"]
        assert local.stat().st_size == model["size_bytes"]
        assert hashlib.sha256(local.read_bytes()).hexdigest() == sha256
        assert model["license"] in {"MIT", "Apache-2.0"}
    print("VISION_MODEL_PROVENANCE_OK")


if __name__ == "__main__":
    run()
