from __future__ import annotations

lazy import hashlib
lazy import json
lazy import sqlite3
lazy from datetime import timedelta
lazy from pathlib import Path

lazy from domain.time_utils import local_wall_time, local_wall_time_from_timestamp


class BackupManager:
    def __init__(self, db, backup_dir: Path):
        self.db = db
        self.backup_dir = backup_dir

    def create(self, reason: str = "manual") -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = local_wall_time().strftime("%Y%m%d-%H%M%S-%f")
        target = self.backup_dir / f"mohan-{stamp}.db"
        destination = sqlite3.connect(target)
        try:
            self.db.conn.backup(destination)
            result = destination.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise RuntimeError("備份資料庫完整性檢查失敗")
        finally:
            destination.close()
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        manifest = {
            "file": target.name,
            "sha256": digest,
            "reason": reason,
            "created_at": local_wall_time().isoformat(timespec="seconds"),
            "source": str(self.db.path),
        }
        target.with_suffix(".json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    def verify(self, target: Path) -> bool:
        manifest_path = target.with_suffix(".json")
        if not target.is_file() or not manifest_path.is_file():
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
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

        A .db without its manifest (power loss between the two writes), with a
        mismatched hash or failing integrity_check is not a backup: it must not
        satisfy "recent backup exists" and must not outrank a real one in prune.
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
