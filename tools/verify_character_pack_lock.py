"""Build repository character packs and verify their public release locks."""

from __future__ import annotations

lazy import argparse
lazy import sys
lazy from collections.abc import Callable, Mapping, Sequence
lazy from functools import partial
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from huapu import character_pack_lock as _core
lazy from tools import build_character_pack as builder
lazy from application.character_runtime_bootstrap import (
    activate_product_character_runtime,
)

LOCK_SCHEMA = _core.LOCK_SCHEMA
LOCK_SCHEMA_VERSION = _core.LOCK_SCHEMA_VERSION
DEFAULT_LOCK = _core.DEFAULT_LOCK
SOURCE_REPOSITORY = "flameblade-studio/MoHan-PC-Desktop-Assistant"
RELEASE_TAG_PREFIX = "mohan-pack-v"
LIN_KEYUN_LOCK = Path("docs/character-pack/lin-keyun-pack.lock.json")
LIN_KEYUN_RELEASE_TAG_PREFIX = "lin-keyun-pack-v"

CharacterPackLockError = _core.CharacterPackLockError
CharacterPackLockSettings = _core.CharacterPackLockSettings
LockedArchive = _core.LockedArchive
LockedSource = _core.LockedSource
LockedEngineCompatibility = _core.LockedEngineCompatibility
LockedFile = _core.LockedFile
CharacterPackLock = _core.CharacterPackLock
CharacterPackLockResult = _core.CharacterPackLockResult
CharacterPackReleaseProfile = _core.CharacterPackReleaseProfile


RELEASE_PROFILES = {
    "mohan": CharacterPackReleaseProfile(
        "flameblade.mohan",
        DEFAULT_LOCK,
        builder.DEFAULT_SOURCE,
        SOURCE_REPOSITORY,
        RELEASE_TAG_PREFIX,
    ),
    "lin-keyun": CharacterPackReleaseProfile(
        "flameblade.lin-keyun",
        LIN_KEYUN_LOCK,
        Path("assets/characters/lin-keyun/pack-source.json"),
        SOURCE_REPOSITORY,
        LIN_KEYUN_RELEASE_TAG_PREFIX,
    ),
}
RELEASE_SETTINGS_BY_PACK_ID = {
    profile.pack_id: profile.settings() for profile in RELEASE_PROFILES.values()
}
DEFAULT_LOCK_SETTINGS = RELEASE_PROFILES["mohan"].settings()


def load_character_pack_lock(path: str | Path) -> CharacterPackLock:
    """Load the MoHan lock through the product-neutral Huapu parser."""
    return _core.load_character_pack_lock(path, settings=DEFAULT_LOCK_SETTINGS)


def load_release_character_pack_lock(path: str | Path) -> CharacterPackLock:
    """Load a lock for one explicitly supported public character-pack series."""
    return _core.load_profiled_character_pack_lock(
        path,
        settings_by_pack_id=RELEASE_SETTINGS_BY_PACK_ID,
    )


def verify_character_pack_lock(
    lock_path: str | Path = DEFAULT_LOCK,
    *,
    repo_root: str | Path = ROOT,
    build: Callable[..., builder.CharacterPackBuildResult] = builder.build_character_pack,
) -> CharacterPackLockResult:
    """Rebuild the ZIP and compare every pinned identity without rewriting it."""
    return _core.verify_character_pack_lock(
        lock_path,
        repo_root=repo_root,
        build=build,
        settings=DEFAULT_LOCK_SETTINGS,
    )


def update_character_pack_lock(
    lock_path: str | Path = DEFAULT_LOCK,
    *,
    repo_root: str | Path = ROOT,
    archive_output: str | Path | None = None,
    build: Callable[..., builder.CharacterPackBuildResult] = builder.build_character_pack,
) -> CharacterPackLockResult:
    """Explicitly rebuild and atomically replace the measured MoHan lock."""
    return _core.update_character_pack_lock(
        lock_path,
        repo_root=repo_root,
        archive_output=archive_output,
        build=build,
        settings=DEFAULT_LOCK_SETTINGS,
    )


def compare_manifest_to_lock(
    manifest: Mapping[str, object],
    lock: CharacterPackLock,
) -> tuple[str, ...]:
    """Compare a validated downloaded manifest with all logical lock fields."""
    return _core.compare_manifest_to_lock(manifest, lock)


render_character_pack_lock = _core.render_character_pack_lock


def main(arguments: Sequence[str] | None = None) -> int:
    activate_product_character_runtime(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=tuple(RELEASE_PROFILES), default="mohan")
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--archive-output", type=Path, help="Keep the exact release ZIP during --update.")
    parsed = parser.parse_args(arguments)
    if parsed.archive_output is not None and not parsed.update:
        parser.error("--archive-output requires --update")
    profile = RELEASE_PROFILES[parsed.profile]
    lock_path = profile.lock_path if parsed.lock is None else parsed.lock
    settings = profile.settings()
    build = partial(builder.build_character_pack, source_path=profile.source_path)
    try:
        operation = (
            partial(_core.update_character_pack_lock, archive_output=parsed.archive_output)
            if parsed.update
            else _core.verify_character_pack_lock
        )
        result = operation(
            lock_path,
            repo_root=parsed.repo_root,
            build=build,
            settings=settings,
        )
        if parsed.update:
            print(
                "CHARACTER_PACK_LOCK_UPDATED="
                f"{_core._resolve_lock_path(parsed.repo_root.resolve(), lock_path)}"
            )
    except (CharacterPackLockError, builder.CharacterPackBuildError, OSError) as error:
        print(f"CHARACTER_PACK_LOCK_ERROR={error}", file=sys.stderr)
        return 1
    if not result.valid:
        print("CHARACTER_PACK_LOCK_MISMATCH", file=sys.stderr)
        for issue in result.issues:
            print(f"LOCK_DIFFERENCE={issue}", file=sys.stderr)
        return 1
    print(f"PACKAGE_HASH={result.package_hash}")
    print(f"ARCHIVE_SHA256={result.archive_sha256}")
    print(f"ARCHIVE_BYTES={result.archive_bytes}")
    print("CHARACTER_PACK_LOCK_VALID=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
