"""PoseAtlas runtime must honor hashes declared by its metadata."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import shutil
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import cv2
lazy import pytest

lazy from infrastructure.layered_full_body_assets import (
    COLOR_IMAGE_DIMENSIONS,
    FULL_BODY_DIMENSION_HEIGHT,
    FULL_BODY_DIMENSION_WIDTH,
    RGBA_CHANNELS,
)
lazy from presentation import pose_atlas_assets
lazy from presentation.pose_atlas_assets import PoseAtlasAssets

ROOT = Path(__file__).resolve().parents[1]
CURRENT_ROOT = ROOT / "assets" / "pose-atlas" / "v5-base"
VIEW_ID = "yaw-180-pitch+00"


@pytest.fixture
def isolated_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Copy the reviewed authority into a disposable canonical-looking root."""

    authority = tmp_path / "v5-base"
    authority.mkdir()
    for source in CURRENT_ROOT.glob("*.png"):
        shutil.copy2(source, authority / source.name)
    shutil.copy2(
        CURRENT_ROOT / "BUILD-METADATA.json",
        authority / "BUILD-METADATA.json",
    )
    monkeypatch.setattr(pose_atlas_assets, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        pose_atlas_assets,
        "FULL_BODY_AUTHORITY_DIR",
        Path("v5-base"),
    )
    return authority


def _replace_with_same_shape_rgba_png(path: Path) -> tuple[str, str]:
    """Change one pixel while preserving a valid same-size four-channel PNG."""

    before = hashlib.sha256(path.read_bytes()).hexdigest()
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    assert image is not None
    assert image.ndim == COLOR_IMAGE_DIMENSIONS
    assert image.shape[2] == RGBA_CHANNELS
    height, width, _ = image.shape
    assert (width, height) == (
        FULL_BODY_DIMENSION_WIDTH,
        FULL_BODY_DIMENSION_HEIGHT,
    )
    altered = image.copy()
    altered[0, 0, 0] = int(altered[0, 0, 0]) ^ 1
    assert cv2.imwrite(str(path), altered)
    roundtrip = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    assert roundtrip is not None
    assert roundtrip.shape == image.shape
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    assert after != before
    return before, after


def _metadata_payload(root: Path) -> dict[str, object]:
    return json.loads(
        (root / "BUILD-METADATA.json").read_text(encoding="utf-8")
    )


def _write_metadata(root: Path, payload: dict[str, object]) -> None:
    (root / "BUILD-METADATA.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_declared_normalized_digest_mismatch_fails_closed(
    isolated_authority: Path,
) -> None:
    """A same-filename replacement still requires verified provenance."""

    target = isolated_authority / f"{VIEW_ID}.png"
    _replace_with_same_shape_rgba_png(target)

    metadata = json.loads(
        (isolated_authority / "BUILD-METADATA.json").read_text(encoding="utf-8")
    )
    record = next(item for item in metadata["views"] if item["view_id"] == VIEW_ID)
    assert record["normalized_sha256"] != hashlib.sha256(target.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="(hash|digest|provenance|source)"):
        PoseAtlasAssets(isolated_authority, image_size=1)


def test_declared_normalized_digest_match_still_constructs(
    isolated_authority: Path,
) -> None:
    """The unchanged schema and reviewed PNG set remain loadable."""

    PoseAtlasAssets(isolated_authority, image_size=1)


def test_undeclared_normalized_digest_keeps_legacy_metadata_compatible(
    isolated_authority: Path,
) -> None:
    """Older metadata remains loadable when it omits the optional normalized digest."""

    metadata = _metadata_payload(isolated_authority)
    views = metadata["views"]
    assert isinstance(views, list)
    for view in views:
        assert isinstance(view, dict)
        view.pop("normalized_sha256", None)
    _write_metadata(isolated_authority, metadata)

    PoseAtlasAssets(isolated_authority, image_size=1)


@pytest.mark.parametrize(
    "declared_digest",
    ("", "not-a-sha256", None, 123, "g" * 64),
)
def test_declared_normalized_digest_must_be_nonempty_sha256(
    isolated_authority: Path,
    declared_digest: object,
) -> None:
    """An explicitly supplied digest must use the declared SHA-256 format."""

    metadata = _metadata_payload(isolated_authority)
    views = metadata["views"]
    assert isinstance(views, list)
    record = next(view for view in views if view["view_id"] == VIEW_ID)
    record["normalized_sha256"] = declared_digest
    _write_metadata(isolated_authority, metadata)

    with pytest.raises(ValueError, match="(hash|digest|sha256|provenance)"):
        PoseAtlasAssets(isolated_authority, image_size=1)


def test_declared_normalized_digest_missing_png_fails_closed(
    isolated_authority: Path,
) -> None:
    """A declared source requires its corresponding PNG to pass verification."""

    (isolated_authority / f"{VIEW_ID}.png").unlink()

    with pytest.raises(ValueError, match="(read|source|hash|digest)"):
        PoseAtlasAssets(isolated_authority, image_size=1)
