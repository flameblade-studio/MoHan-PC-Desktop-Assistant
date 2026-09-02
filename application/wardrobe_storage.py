from __future__ import annotations

lazy from dataclasses import dataclass
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path


@dataclass(frozen=True, slots=True)
class WardrobeStoragePolicy:
    max_installed_packages: int = 16
    max_quarantine_jobs: int = 5
    max_total_bytes: int = 6 * 1024 * 1024 * 1024
    minimum_generation_interval: timedelta = timedelta(days=7)

    def __post_init__(self) -> None:
        if self.max_installed_packages < 1:
            raise ValueError("Wardrobe package limit must be positive.")
        if self.max_quarantine_jobs < 1:
            raise ValueError("Wardrobe quarantine limit must be positive.")
        if self.max_total_bytes < 1024 * 1024:
            raise ValueError("Wardrobe storage limit is too small.")
        if self.minimum_generation_interval < timedelta(0):
            raise ValueError("Wardrobe generation interval cannot be negative.")


@dataclass(frozen=True, slots=True)
class WardrobeStorageStatus:
    allowed: bool
    reason: str
    installed_packages: int
    quarantine_jobs: int
    total_bytes: int


def _directory_bytes(root: Path) -> int | None:
    """回傳目錄總位元組；量不完整時回傳 None，而不是部分總量。

    原本任一 stat() 拋 OSError 就 return 目前累計值。quarantine 實際 6.4 GiB、
    掃到 800 MiB 時一個檔案因 ACL 變更或同步程式搬走而失敗，函式回傳 800 MiB，
    低於 6 GiB 上限，生成器繼續寫 draft——這是 fail-open，可能把磁碟寫滿。
    「量測失敗」與「量到很少」必須是兩個不同的回傳值。
    """
    if not root.is_dir():
        return 0
    total = 0
    for path in root.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                return None
    return total


class WardrobeStorageGuard:
    """Prevent unbounded generation without deleting user-owned outfits."""

    def __init__(
        self,
        outfit_store: Path,
        quarantine_root: Path,
        policy: WardrobeStoragePolicy | None = None,
    ) -> None:
        self.outfit_store = Path(outfit_store)
        self.quarantine_root = Path(quarantine_root)
        self.policy = policy or WardrobeStoragePolicy()

    def inspect(
        self,
        now: datetime,
        last_generated_at: datetime | None,
        *,
        special_occasion: bool,
    ) -> WardrobeStorageStatus:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Wardrobe storage time must include a timezone.")
        normalized = now.astimezone(UTC)
        packages = self.outfit_store / "packages"
        installed = (
            len(tuple(packages.glob("generated-*.mohan-outfit")))
            if packages.is_dir()
            else 0
        )
        jobs = (
            len(tuple(
                path
                for path in self.quarantine_root.iterdir()
                if path.is_dir()
                and (
                    (path / "quarantined.json").is_file()
                    or (path / "source").is_dir()
                )
            ))
            if self.quarantine_root.is_dir()
            else 0
        )
        generated_bytes = sum(
            path.stat().st_size
            for path in packages.glob("generated-*.mohan-outfit")
            if path.is_file()
        ) if packages.is_dir() else 0
        quarantine_bytes = _directory_bytes(self.quarantine_root)
        total = generated_bytes + (quarantine_bytes or 0)
        reason = "ready"
        if quarantine_bytes is None:
            # 量不準就不放行：上限檢查的前提是總量可信。
            reason = "storage-unmeasurable"
        elif installed >= self.policy.max_installed_packages:
            reason = "package-limit"
        elif jobs >= self.policy.max_quarantine_jobs:
            reason = "quarantine-limit"
        elif total >= self.policy.max_total_bytes:
            reason = "storage-limit"
        elif (
            not special_occasion
            and last_generated_at is not None
            and normalized - last_generated_at.astimezone(UTC)
            < self.policy.minimum_generation_interval
        ):
            reason = "generation-cooldown"
        return WardrobeStorageStatus(
            reason == "ready",
            reason,
            installed,
            jobs,
            total,
        )
