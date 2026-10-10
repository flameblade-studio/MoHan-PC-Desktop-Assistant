"""Download a released character pack and load it the way the product does.

The lock check rebuilds a pack from source; this check closes the other half of
the release loop by fetching the published GitHub asset, installing it into an
isolated profile, and reading it with the product's official pack limits.
"""

from __future__ import annotations

lazy import argparse
lazy import sys
lazy import tempfile
lazy from collections.abc import Sequence
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from application.character_runtime_bootstrap import official_character_pack_limits
lazy from infrastructure.installed_character_packs import (
    installed_character_pack_path,
    load_installed_character_pack,
)
lazy from tools.fetch_character_pack import CharacterPackFetchError, fetch_character_pack
lazy from tools.verify_character_pack_lock import RELEASE_PROFILES


def verify_download(profile_name: str, data_root: Path) -> int:
    """Fetch, install, and load one released pack; return the loaded file count."""

    profile = RELEASE_PROFILES[profile_name]
    character_id = profile.pack_id.removeprefix("flameblade.")
    target = installed_character_pack_path(character_id, data_root=data_root)
    result = fetch_character_pack(target, lock_path=ROOT / profile.lock_path)
    reader = load_installed_character_pack(
        character_id,
        data_root=data_root,
        limits=official_character_pack_limits(),
    )
    if reader.character_id != character_id:
        raise ValueError(f"Loaded {reader.character_id!r}; expected {character_id!r}.")
    print(f"PACK_ID={result.pack_id}")
    print(f"PACK_VERSION={result.pack_version}")
    print(f"PACKAGE_HASH={result.package_hash}")
    print(f"LOADED_CHARACTER={reader.character_id}")
    return result.checked_files


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=tuple(RELEASE_PROFILES), required=True)
    parsed = parser.parse_args(arguments)
    with tempfile.TemporaryDirectory(prefix="mohan-pack-download-") as directory:
        try:
            checked = verify_download(parsed.profile, Path(directory))
        except (CharacterPackFetchError, ValueError, OSError) as error:
            print(f"CHARACTER_PACK_DOWNLOAD_ERROR={error}", file=sys.stderr)
            return 1
    print(f"CHECKED_FILES={checked}")
    print("CHARACTER_PACK_DOWNLOAD_VALID=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
