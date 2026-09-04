from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from types import SimpleNamespace
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application import service_container
lazy from presentation.flagship.overview import FlagshipOverviewMixin

RETRY_ATTEMPTS = 2


class _RetryingBackupManager:
    instances: list[_RetryingBackupManager] = []

    def __init__(self, _db: object, _backup_dir: Path) -> None:
        self.calls = 0
        self.automatic_backup_failed = False
        self.failure_count = 0
        type(self).instances.append(self)

    def automatic_if_due(self) -> None:
        self.calls += 1
        if self.calls == 1:
            raise OSError("simulated backup disk failure")

    def record_automatic_failure(self, _error: BaseException) -> None:
        self.automatic_backup_failed = True
        self.failure_count += 1


class _Summary:
    def __init__(self) -> None:
        self.value = ""

    def setText(self, value: str) -> None:
        self.value = value


class _HealthDB:
    def workflows(self, *, enabled_only: bool) -> list[object]:
        assert enabled_only
        return []

    def paired_devices(self) -> list[object]:
        return []

    def connector(self, _name: str) -> None:
        return None


def assert_startup_backup_failure_retains_manager_and_retries() -> None:
    _RetryingBackupManager.instances.clear()
    with TemporaryDirectory() as temporary, patch.object(
        service_container,
        "BackupManager",
        _RetryingBackupManager,
    ):
        initialize = getattr(service_container, "_initialize_backup_manager")
        manager = initialize(object(), Path(temporary))
        assert manager is _RetryingBackupManager.instances[0]
        assert manager.automatic_backup_failed is True
        assert manager.failure_count == 1
        manager.automatic_if_due()
        assert manager.calls == RETRY_ATTEMPTS


def assert_overview_exposes_automatic_backup_failure() -> None:
    summary = _Summary()
    probe = SimpleNamespace(
        db=_HealthDB(),
        remote_server=None,
        backup_manager=SimpleNamespace(automatic_backup_failed=True),
        health_summary=summary,
        _t=lambda source, **values: source.format(**values),
    )
    FlagshipOverviewMixin.refresh_health(probe)
    assert "自動備份失敗" in summary.value


def run() -> None:
    checks = (
        assert_startup_backup_failure_retains_manager_and_retries,
        assert_overview_exposes_automatic_backup_failure,
    )
    failures: list[str] = []
    for check in checks:
        try:
            check()
        except Exception as error:
            failures.append(f"{check.__name__}: {type(error).__name__}: {error}")
    if failures:
        raise AssertionError("\n".join(failures))
    print("D05_BACKUP_OK")


if __name__ == "__main__":
    run()
