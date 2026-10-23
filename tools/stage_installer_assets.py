"""Stage canonical installer assets without the body-pack source root."""

from __future__ import annotations

lazy import argparse
lazy import os
lazy import shutil
lazy import stat
lazy import sys
lazy import tempfile
lazy from collections.abc import Sequence
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BODY_PACKS_DIRECTORY = "body-packs"


class InstallerAssetStageError(RuntimeError):
    """The canonical installer asset tree could not be staged safely."""


def stage_installer_assets(source_root: str | Path, destination: str | Path) -> Path:
    """Create an isolated asset tree, omitting only ``assets/body-packs``."""

    source = Path(source_root)
    try:
        source = source.resolve(strict=True)
    except OSError as error:
        raise InstallerAssetStageError("The canonical assets directory is unavailable.") from error
    if source.name != "assets" or source.is_symlink() or source.is_junction() or not source.is_dir():
        raise InstallerAssetStageError("The source must be the canonical regular assets directory.")

    requested_destination = Path(destination).absolute()
    try:
        requested_destination.parent.mkdir(parents=True, exist_ok=True)
        parent = requested_destination.parent.resolve(strict=True)
    except OSError as error:
        raise InstallerAssetStageError("The installer asset staging parent is unavailable.") from error
    target = parent / requested_destination.name
    if target.exists() or target.is_symlink() or target.is_junction():
        raise InstallerAssetStageError(f"Installer asset staging destination already exists: {target}")
    if target == source or target.is_relative_to(source) or source.is_relative_to(target):
        raise InstallerAssetStageError("Installer asset staging must stay outside the source tree.")

    try:
        with tempfile.TemporaryDirectory(prefix=f".{target.name}-stage-", dir=parent) as temporary:
            staged_assets = Path(temporary) / "assets"
            staged_assets.mkdir()
            _copy_asset_directory(source, staged_assets, canonical_root=source)
            if (staged_assets / BODY_PACKS_DIRECTORY).exists():
                raise InstallerAssetStageError("The body-pack source root entered installer staging.")
            staged_assets.rename(target)
    except InstallerAssetStageError:
        raise
    except OSError as error:
        raise InstallerAssetStageError("The canonical installer asset tree could not be staged.") from error
    return target


def cleanup_installer_assets(destination: str | Path) -> None:
    """Remove only a staging directory directly below this repository's build root."""

    build_root = ROOT / "build"
    try:
        resolved_build = build_root.resolve(strict=True)
        requested = Path(destination).absolute()
        parent = requested.parent.resolve(strict=True)
    except OSError as error:
        raise InstallerAssetStageError("The installer staging cleanup path is unavailable.") from error
    target = parent / requested.name
    if (
        parent != resolved_build
        or not requested.name.startswith("installer-assets-")
        or target.is_symlink()
        or target.is_junction()
        or not target.is_dir()
    ):
        raise InstallerAssetStageError("Refusing cleanup outside a canonical installer staging directory.")
    for directory, children, files in os.walk(target, followlinks=False):
        parent = Path(directory)
        for name in (*children, *files):
            entry = parent / name
            if entry.is_symlink() or entry.is_junction():
                raise InstallerAssetStageError("Refusing cleanup through a linked staging entry.")
    shutil.rmtree(target)


def _copy_asset_directory(source: Path, destination: Path, *, canonical_root: Path) -> None:
    for entry in sorted(source.iterdir(), key=lambda item: item.name):
        if source == canonical_root and entry.name == BODY_PACKS_DIRECTORY:
            continue
        metadata = entry.lstat()
        if entry.is_symlink() or entry.is_junction():
            raise InstallerAssetStageError(f"Installer assets cannot contain links: {entry}")
        target = destination / entry.name
        if stat.S_ISDIR(metadata.st_mode):
            target.mkdir()
            _copy_asset_directory(entry, target, canonical_root=canonical_root)
        elif stat.S_ISREG(metadata.st_mode):
            _copy_asset(entry, target)
        else:
            raise InstallerAssetStageError(f"Installer assets must contain only regular files: {entry}")


def _copy_asset(source: Path, destination: Path) -> None:
    # Installer staging is an independent build tree.  Hard links would let a
    # later packaging step mutate the canonical asset tree through the stage.
    shutil.copy2(source, destination)


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--cleanup", action="store_true")
    parsed = parser.parse_args(arguments)
    try:
        if parsed.cleanup:
            cleanup_installer_assets(parsed.destination)
            print("INSTALLER_ASSETS_CLEANED=1")
            return 0
        if parsed.source is None:
            parser.error("--source is required unless --cleanup is selected")
        staged = stage_installer_assets(parsed.source, parsed.destination)
    except (InstallerAssetStageError, OSError, ValueError) as error:
        print(f"INSTALLER_ASSET_STAGE_ERROR={error}", file=sys.stderr)
        return 1
    print(f"INSTALLER_ASSETS_STAGED={staged}")
    print("EXCLUDED_ASSET_ROOT=body-packs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
