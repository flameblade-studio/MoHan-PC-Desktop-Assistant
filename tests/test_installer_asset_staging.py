from __future__ import annotations

lazy import hashlib
lazy from pathlib import Path

lazy import pytest

lazy from tools.stage_installer_assets import stage_installer_assets


def test_installer_staging_excludes_only_the_canonical_body_pack_root(
    tmp_path: Path,
) -> None:
    assets = tmp_path / "assets"
    (assets / "body-packs" / "mohan-body-v2" / "source").mkdir(parents=True)
    (assets / "pose-atlas" / "v5-base").mkdir(parents=True)
    (assets / "characters" / "lin-keyun" / "body-packs").mkdir(parents=True)
    (assets / "mohan-halfbody.ico").write_bytes(b"icon")
    (assets / "body-packs" / "mohan-body-v2" / "source" / "body.png").write_bytes(b"source body")
    (assets / "pose-atlas" / "v5-base" / "front.png").write_bytes(b"MoHan payload")
    (assets / "characters" / "lin-keyun" / "body-packs" / "metadata.json").write_bytes(b"character data")
    destination = tmp_path / "build" / "installer-assets-test"

    staged = stage_installer_assets(assets, destination)

    assert staged == destination.resolve()
    assert not (staged / "body-packs").exists()
    assert (staged / "mohan-halfbody.ico").read_bytes() == b"icon"
    assert (staged / "pose-atlas" / "v5-base" / "front.png").read_bytes() == b"MoHan payload"
    assert (
        staged / "characters" / "lin-keyun" / "body-packs" / "metadata.json"
    ).read_bytes() == b"character data"


def test_installer_staging_never_links_canonical_files(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    canonical = assets / "pose-atlas" / "v5-base" / "front.png"
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(b"canonical payload")
    before = hashlib.sha256(canonical.read_bytes()).hexdigest()

    staged = stage_installer_assets(assets, tmp_path / "stage")
    staged_file = staged / "pose-atlas" / "v5-base" / "front.png"
    staged_file.write_bytes(b"staged mutation")

    assert hashlib.sha256(canonical.read_bytes()).hexdigest() == before
    assert canonical.read_bytes() == b"canonical payload"


def test_installer_staging_rejects_reused_destination(
    tmp_path: Path,
) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    destination = tmp_path / "stage"
    destination.mkdir()

    with pytest.raises(RuntimeError, match="already exists"):
        stage_installer_assets(assets, destination)


def test_release_build_uses_filtered_asset_staging() -> None:
    root = Path(__file__).resolve().parents[1]
    build_script = (root / "build.ps1").read_text(encoding="utf-8")

    assert "tools/stage_installer_assets.py" in build_script
    assert '--add-data "$AssetStage;assets"' in build_script
    assert '--add-data "assets;assets"' not in build_script
