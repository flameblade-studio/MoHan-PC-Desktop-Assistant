"""Command-line orchestration for configured character-pack release locks."""

from __future__ import annotations

lazy import argparse
lazy import sys
lazy from collections.abc import Callable, Mapping, Sequence
lazy from functools import partial
lazy from pathlib import Path

lazy from huapu import character_pack_lock as lock_core
lazy from huapu.character_pack_builder import (
    CharacterPackBuildError,
    CharacterPackBuildResult,
)

BuildForProfile = Callable[[str], Callable[..., CharacterPackBuildResult]]
ActivateRuntime = Callable[[Path], object]


def run_release_lock_cli(
    arguments: Sequence[str] | None,
    *,
    description: str | None,
    profiles: Mapping[str, lock_core.CharacterPackReleaseProfile],
    default_profile: str,
    build_for_profile: BuildForProfile,
    repository_root: Path,
    activate_runtime: ActivateRuntime,
) -> int:
    """Run the standard verify/update CLI with caller-owned release profiles."""
    activate_runtime(repository_root)
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--profile", choices=tuple(profiles), default=default_profile)
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--repo-root", type=Path, default=repository_root)
    parser.add_argument("--update", action="store_true")
    parser.add_argument(
        "--archive-output",
        type=Path,
        help="Keep the exact release ZIP during --update.",
    )
    parsed = parser.parse_args(arguments)
    if parsed.archive_output is not None and not parsed.update:
        parser.error("--archive-output requires --update")
    profile = profiles[parsed.profile]
    lock_path = profile.lock_path if parsed.lock is None else parsed.lock
    settings = profile.settings()
    build = build_for_profile(parsed.profile)
    try:
        operation = (
            partial(lock_core.update_character_pack_lock, archive_output=parsed.archive_output)
            if parsed.update
            else lock_core.verify_character_pack_lock
        )
        result = operation(
            lock_path,
            repo_root=parsed.repo_root,
            build=build,
            settings=settings,
        )
        if parsed.update:
            resolved_root = parsed.repo_root.resolve()
            resolved_lock = lock_core._resolve_lock_path(resolved_root, lock_path)
            print(f"CHARACTER_PACK_LOCK_UPDATED={resolved_lock}")
    except (lock_core.CharacterPackLockError, CharacterPackBuildError, OSError) as error:
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
