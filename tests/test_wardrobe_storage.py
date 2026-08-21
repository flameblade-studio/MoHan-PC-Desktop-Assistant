from __future__ import annotations

lazy import sys
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.wardrobe_storage import (
    WardrobeStorageGuard,
    WardrobeStoragePolicy,
)


def run() -> None:
    now = datetime(2026, 8, 15, tzinfo=UTC)
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        policy = WardrobeStoragePolicy(
            max_installed_packages=2,
            max_quarantine_jobs=2,
            max_total_bytes=1024 * 1024,
            minimum_generation_interval=timedelta(days=7),
        )
        guard = WardrobeStorageGuard(root / "store", root / "drafts", policy)
        ready = guard.inspect(now, None, special_occasion=False)
        assert ready.allowed and ready.reason == "ready"
        cooling = guard.inspect(
            now,
            now - timedelta(days=1),
            special_occasion=False,
        )
        assert not cooling.allowed and cooling.reason == "generation-cooldown"
        special = guard.inspect(
            now,
            now - timedelta(days=1),
            special_occasion=True,
        )
        assert special.allowed
        packages = root / "store" / "packages"
        packages.mkdir(parents=True)
        (packages / "official.mohan-outfit").write_bytes(b"official")
        user_owned = guard.inspect(now, None, special_occasion=True)
        assert user_owned.allowed and user_owned.installed_packages == 0
        (packages / "generated-one.mohan-outfit").write_bytes(b"one")
        (packages / "generated-two.mohan-outfit").write_bytes(b"two")
        full = guard.inspect(now, None, special_occasion=True)
        assert not full.allowed and full.reason == "package-limit"
    print("WARDROBE_STORAGE_OK")


if __name__ == "__main__":
    run()
