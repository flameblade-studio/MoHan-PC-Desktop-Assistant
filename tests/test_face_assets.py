from __future__ import annotations

lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from domain.face_rig import FacePose
lazy from infrastructure.face_assets import FACE_ASSET_MANIFESTS, validate_face_assets

FACE_ASSET_COUNT = 24


def run() -> None:
    assert set(FACE_ASSET_MANIFESTS) == set(FacePose)
    checked = validate_face_assets(ROOT / "assets" / "expressions")
    assert len(checked) == FACE_ASSET_COUNT
    assert all(path.suffix == ".png" for path in checked)
    print("FACE_ASSETS_OK")


if __name__ == "__main__":
    run()
