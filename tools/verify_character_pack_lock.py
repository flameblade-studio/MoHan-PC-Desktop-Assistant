"""Build the repository MoHan pack and verify its version lock."""

from __future__ import annotations

lazy import argparse
lazy import sys
lazy from collections.abc import Callable, Mapping, Sequence
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from huapu import character_pack_lock as _core
lazy from tools import build_character_pack as builder

LOCK_SCHEMA = _core.LOCK_SCHEMA
LOCK_SCHEMA_VERSION = _core.LOCK_SCHEMA_VERSION
DEFAULT_LOCK = _core.DEFAULT_LOCK
SOURCE_REPOSITORY = "flameblade-studio/mohan-character-pack"
RELEASE_TAG_PREFIX = "mohan-pack-v"

CharacterPackLockError = _core.CharacterPackLockError
CharacterPackLockSettings = _core.CharacterPackLockSettings
LockedArchive = _core.LockedArchive
LockedSource = _core.LockedSource
LockedEngineCompatibility = _core.LockedEngineCompatibility
LockedFile = _core.LockedFile
CharacterPackLock = _core.CharacterPackLock
CharacterPackLockResult = _core.CharacterPackLockResult

DEFAULT_LOCK_SETTINGS = CharacterPackLockSettings(
    schema=LOCK_SCHEMA,
    schema_version=LOCK_SCHEMA_VERSION,
    source_repository=SOURCE_REPOSITORY,
    release_tag_prefix=RELEASE_TAG_PREFIX,
    pack_source_path=builder.DEFAULT_SOURCE,
)


def load_character_pack_lock(path: str | Path) -> CharacterPackLock:
    """Load the MoHan lock through the product-neutral Huapu parser."""
    return _core.load_character_pack_lock(path, settings=DEFAULT_LOCK_SETTINGS)


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--update", action="store_true")
    parser.add_argument(
        "--archive-output",
        type=Path,
        help="Keep the exact release ZIP produced during --update; the path must not exist.",
    )
    parsed = parser.parse_args(arguments)
    if parsed.archive_output is not None and not parsed.update:
        parser.error("--archive-output requires --update")
    try:
        if parsed.update:
            result = update_character_pack_lock(
                parsed.lock,
                repo_root=parsed.repo_root,
                archive_output=parsed.archive_output,
            )
            print(
                "CHARACTER_PACK_LOCK_UPDATED="
                f"{_core._resolve_lock_path(parsed.repo_root.resolve(), parsed.lock)}"
            )
        else:
            result = verify_character_pack_lock(parsed.lock, repo_root=parsed.repo_root)
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
