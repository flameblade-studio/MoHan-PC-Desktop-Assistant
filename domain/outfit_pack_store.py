"""Archive discovery and atomic saved-state primitives for outfit packs."""
from __future__ import annotations

lazy import json
lazy import os
lazy from contextlib import nullcontext
lazy from pathlib import Path
lazy from tempfile import NamedTemporaryFile
lazy from collections.abc import Callable
lazy from domain._outfit_pack_models import OutfitPack
lazy from domain.outfit_pack_assets import (
    IncompatibleBodyProfileError,
    OutfitPackError,
    deferred_png_content_validation,
)


def _installed_pack_paths(
    store: Path,
    *,
    official_pack_root: Path,
    official_pack_ids: frozenset[str] | None = None,
) -> tuple[Path, ...]:
    """User-installed packs first, then the official packs shipped with the app (always restorable)."""
    paths = []
    installed_root = Path(store) / "packages"
    if installed_root.is_dir():
        paths.extend(sorted(installed_root.glob("*.mohan-outfit")))
    official_root = Path(official_pack_root)
    if official_root.is_dir():
        official_paths = sorted(official_root.glob("*.mohan-outfit"))
        installed_ids = {path.stem for path in paths}
        duplicate = next(
            (path for path in official_paths if path.stem in installed_ids),
            None,
        )
        if duplicate is not None:
            raise OutfitPackError(
                "Appearance pack identifiers must be unique.",
                reason="duplicate_pack_id",
                pack_id=duplicate.stem,
                asset_path=duplicate.name,
            )
        paths.extend(
            official_paths
            if official_pack_ids is None
            else (path for path in official_paths if path.stem in official_pack_ids)
        )
    pack_ids: dict[str, Path] = {}
    for path in paths:
        previous = pack_ids.setdefault(path.stem, path)
        if previous != path:
            raise OutfitPackError(
                "Appearance pack identifiers must be unique.",
                reason="duplicate_pack_id",
                pack_id=path.stem,
                asset_path=path.name,
            )
    return tuple(paths)


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(payload, temporary, ensure_ascii=False, sort_keys=True)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _state_references_pack(path: Path, pack_id: str) -> bool:
    if not path.is_file():
        return False
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise OutfitPackError("Provide a supported saved appearance state.") from None
    if not isinstance(state, dict):
        raise OutfitPackError("Provide a supported saved appearance state.")
    for value in state.values():
        if isinstance(value, dict) and value.get("pack_id") == pack_id:
            return True
    return False


def inspect_cached_pack(
    path: Path, inspect: Callable[[Path], OutfitPack],
    cache: dict[Path, tuple[tuple[int, int], OutfitPack | None]],
    *, defer_png_content_validation: bool = False,
) -> OutfitPack | None:
    """Parse an installed archive once per canonical (mtime, size) token."""
    path = Path(path).resolve()
    try:
        stat = path.stat()
    except OSError:
        raise OutfitPackError("Archive size needs a supported value.") from None
    token = (stat.st_mtime_ns, stat.st_size)
    cached = cache.get(path)
    if cached is None or cached[0] != token:
        try:
            validation = (
                deferred_png_content_validation()
                if defer_png_content_validation else nullcontext()
            )
            with validation:
                inspected = inspect(path)
            cached = (token, inspected)
        except IncompatibleBodyProfileError:
            cached = (token, None)
        except OutfitPackError as error:
            if error.pack_id is None:
                error.pack_id = path.stem
            raise
        cache[path] = cached
    return cached[1]


def copy_pack_archive(source: Path, store: Path, pack_id: str) -> None:
    packages = Path(store) / "packages"
    packages.mkdir(parents=True, exist_ok=True)
    destination = packages / f"{pack_id}.mohan-outfit"
    with NamedTemporaryFile("wb", dir=packages, delete=False) as temporary:
        temporary.write(Path(source).read_bytes())
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
