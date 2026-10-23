from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import secrets
lazy import sqlite3
lazy import stat
lazy from datetime import timedelta
lazy from pathlib import Path
lazy import tempfile

lazy from domain.time_utils import local_wall_time, local_wall_time_from_timestamp

WINDOWS_REPARSE_POINT = 0x0400


def _is_reparse_point(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError:
        return True
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & WINDOWS_REPARSE_POINT
    )


class BackupManager:
    def __init__(self, db, backup_dir: Path):
        self.db = db
        self.backup_dir = backup_dir
        self.automatic_backup_failed = False
        self.automatic_backup_failure_count = 0
        self.automatic_backup_last_error: str | None = None

    def record_automatic_failure(self, error: BaseException) -> None:
        """Keep a non-sensitive attention event marker for the next visible health refresh."""

        self.automatic_backup_failed = True
        self.automatic_backup_failure_count += 1
        self.automatic_backup_last_error = type(error).__name__

    def _record_automatic_success(self) -> None:
        self.automatic_backup_failed = False
        self.automatic_backup_last_error = None

    def create(self, reason: str = "manual") -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        if _is_reparse_point(self.backup_dir):
            raise OSError("備份目錄包含不受信任的 reparse point")
        stamp = local_wall_time().strftime("%Y%m%d-%H%M%S-%f")
        target = self.backup_dir / f"mohan-{stamp}-{secrets.token_hex(16)}.db"
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".mohan-backup-",
            suffix=".db",
            dir=self.backup_dir,
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        destination = sqlite3.connect(temporary)
        try:
            self.db.conn.backup(destination)
            result = destination.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise RuntimeError("備份資料庫完整性檢查失敗")
        finally:
            destination.close()
        try:
            os.replace(temporary, target)
            with target.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
            manifest = {
                "file": target.name,
                "sha256": digest,
                "reason": reason,
                "created_at": local_wall_time().isoformat(timespec="seconds"),
                "source": str(self.db.path),
            }
            descriptor, manifest_name = tempfile.mkstemp(
                prefix=".mohan-manifest-",
                suffix=".json",
                dir=self.backup_dir,
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as manifest_file:
                json.dump(manifest, manifest_file, ensure_ascii=False, indent=2)
                manifest_file.flush()
                os.fsync(manifest_file.fileno())
            os.replace(manifest_name, target.with_suffix(".json"))
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def verify(self, target: Path) -> bool:
        manifest_path = target.with_suffix(".json")
        if (
            _is_reparse_point(target)
            or _is_reparse_point(manifest_path)
            or not target.is_file()
            or not manifest_path.is_file()
        ):
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(manifest, dict):
            return False
        if hashlib.sha256(target.read_bytes()).hexdigest() != manifest.get("sha256"):
            return False
        connection = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()
            return bool(result and result[0] == "ok")
        finally:
            connection.close()

    def _verified_backups(self) -> list[Path]:
        """Backups that pass verify(), newest first.

        A .db earns backup status with its manifest, matching hash, and passing integrity_check; the recent-backup check and prune order use those verified records.
        Such files are left alone rather than deleted.
        """
        return sorted(
            (
                path
                for path in self.backup_dir.glob("mohan-*.db")
                if self.verify(path)
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

    def automatic_if_due(self, hours: int = 24) -> Path | None:
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            newest = next(iter(self._verified_backups()), None)
            if newest is not None:
                age = local_wall_time() - local_wall_time_from_timestamp(
                    newest.stat().st_mtime
                )
                if age < timedelta(hours=max(1, hours)):
                    return None
            created = self.create("automatic")
            self.prune()
        except (OSError, RuntimeError, sqlite3.Error) as error:
            self.record_automatic_failure(error)
            raise
        self._record_automatic_success()
        return created

    def prune(self, keep_daily: int = 14, keep_monthly: int = 6) -> None:
        backups = self._verified_backups()
        keep: set[Path] = set(backups[: max(1, keep_daily)])
        months: set[str] = set()
        for backup in backups:
            month = local_wall_time_from_timestamp(
                backup.stat().st_mtime
            ).strftime("%Y-%m")
            if month not in months and len(months) < max(0, keep_monthly):
                months.add(month)
                keep.add(backup)
        for backup in backups:
            if backup in keep:
                continue
            manifest = backup.with_suffix(".json")
            backup.unlink(missing_ok=True)
            manifest.unlink(missing_ok=True)
