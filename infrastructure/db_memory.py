from __future__ import annotations

lazy import json
lazy import re
lazy import sqlite3
lazy from datetime import datetime

lazy from domain.text_normalizer import to_taiwan_traditional
lazy from domain.time_utils import local_wall_time
lazy from infrastructure.memory_index import cosine_similarity, hashed_text_vector

__all__ = ("StudioDBMemoryMethods",)

MAX_TITLE_LENGTH = 36
MAX_MEMORIES = 500
LOW_IMPORTANCE_THRESHOLD = 2
MEMORY_AGE_DAYS = 90


class StudioDBMemoryMethods:
    def add_memory(
        self,
        content: str,
        category: str = "偏好",
        source: str = "manual",
        importance: int = 3,
        title: str = "",
    ) -> int:
        text = content.strip()
        if not text:
            return 0
        title_was_supplied = bool(title.strip())
        memory_title = title.strip()
        if not memory_title:
            memory_title = " ".join(text.split())
            if len(memory_title) > MAX_TITLE_LENGTH:
                memory_title = memory_title[:MAX_TITLE_LENGTH].rstrip() + "…"
        now = local_wall_time().isoformat(timespec="seconds")
        conflict_title = (
            "title=excluded.title," if title_was_supplied else "title=memories.title,"
        )
        statement = (
            "INSERT INTO memories(category,title,content,source,importance,"
            "created_at,updated_at) VALUES(?,?,?,?,?,?,?) "
            "ON CONFLICT(content) DO UPDATE SET "
            f"category=excluded.category,{conflict_title}"
            "source=excluded.source,"
            "importance=MAX(memories.importance,excluded.importance),"
            "updated_at=excluded.updated_at"
        )
        self.conn.execute(
            statement,
            (
                to_taiwan_traditional(category.strip()) or "其他",
                memory_title or "未命名記憶",
                text,
                source,
                max(1, min(5, importance)),
                now,
                now,
            ),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM memories WHERE content=?", (text,)
        ).fetchone()
        memory_id = int(row["id"])
        self._memory_index.clear()
        total = self.conn.execute("SELECT COUNT(*) AS total FROM memories").fetchone()[
            "total"
        ]
        if int(total) > MAX_MEMORIES:
            self.optimize_memories()
        return memory_id

    def list_memories(
        self,
        limit: int = 100,
        category: str | None = None,
    ) -> list[sqlite3.Row]:
        now = local_wall_time().isoformat(timespec="seconds")
        where = "WHERE (expires_at IS NULL OR expires_at > ?)"
        parameters: list[object] = [now]
        if category:
            where += " AND category=?"
            parameters.append(category)
        parameters.append(limit)
        return list(
            self.conn.execute(
                f"SELECT * FROM memories {where} "
                "ORDER BY importance DESC,updated_at DESC LIMIT ?",
                parameters,
            )
        )

    def memory(self, memory_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM memories WHERE id=?", (memory_id,)
        ).fetchone()

    def update_memory(
        self,
        memory_id: int,
        title: str,
        content: str,
        category: str,
        importance: int,
    ) -> bool:
        title = title.strip()
        content = content.strip()
        normalized_category = to_taiwan_traditional(category.strip()) or "?嗡?"
        if not title or not content:
            return False
        try:
            cursor = self.conn.execute(
                "UPDATE memories SET title=?,content=?,category=?,"
                "importance=?,updated_at=? WHERE id=?",
                (
                    title,
                    content,
                    normalized_category,
                    max(1, min(5, int(importance))),
                    local_wall_time().isoformat(timespec="seconds"),
                    memory_id,
                ),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return False
        self._memory_index.clear()
        return cursor.rowcount > 0

    def delete_memory(self, memory_id: int) -> None:
        self.conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        self.conn.commit()
        self._memory_index.clear()

    def delete_memories(self, memory_ids: list[int]) -> int:
        ids = sorted({int(memory_id) for memory_id in memory_ids})
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        cursor = self.conn.execute(
            f"DELETE FROM memories WHERE id IN ({placeholders})",
            ids,
        )
        self.conn.commit()
        self._memory_index.clear()
        return max(0, int(cursor.rowcount))

    def clear_memories(self) -> None:
        self.conn.execute("DELETE FROM memories")
        self.conn.commit()
        self._memory_index.clear()

    def memory_context(self, limit: int = 24, query: str = "") -> str:
        pool = self.list_memories(5000)
        if query.strip():
            row_by_id = {int(row["id"]): row for row in pool}
            rows = [
                row_by_id[item.memory_id]
                for item in self._memory_index.rank(
                    query,
                    [dict(row) for row in pool],
                    limit,
                )
            ]
        else:
            rows = pool[:limit]
        if rows:
            now = local_wall_time().isoformat(timespec="seconds")
            with self.conn:
                self.conn.executemany(
                    "UPDATE memories SET last_used_at=? WHERE id=?",
                    [(now, int(row["id"])) for row in rows],
                )
        return "\n".join(f"- [{row['category']}] {row['content']}" for row in rows)

    def _archive_memory_ids(self, memory_ids: list[int], reason: str) -> int:
        ids = sorted({int(memory_id) for memory_id in memory_ids})
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        rows = self.conn.execute(
            f"SELECT * FROM memories WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
        archived_at = local_wall_time().isoformat(timespec="seconds")
        with self.conn:
            self.conn.executemany(
                "INSERT INTO memory_archive(original_id,snapshot,reason,archived_at) "
                "VALUES(?,?,?,?)",
                [
                    (
                        int(row["id"]),
                        json.dumps(dict(row), ensure_ascii=False),
                        reason,
                        archived_at,
                    )
                    for row in rows
                ],
            )
            self.conn.execute(
                f"DELETE FROM memories WHERE id IN ({placeholders})",
                ids,
            )
        self._memory_index.clear()
        return len(rows)

    def list_archived_memories(self, limit: int = 200) -> list[dict]:
        rows = list(
            self.conn.execute(
                "SELECT * FROM memory_archive WHERE restored_at IS NULL "
                "ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            )
        )
        archived: list[dict] = []
        for row in rows:
            try:
                snapshot = json.loads(str(row["snapshot"]))
            except TypeError, ValueError, json.JSONDecodeError:
                snapshot = {}
            archived.append({
                "id": int(row["id"]),
                "original_id": int(row["original_id"]),
                "reason": str(row["reason"]),
                "archived_at": str(row["archived_at"]),
                "category": str(snapshot.get("category") or "其他"),
                "title": str(snapshot.get("title") or "未命名記憶"),
                "content": str(snapshot.get("content") or ""),
                "source": str(snapshot.get("source") or "conversation"),
                "importance": int(snapshot.get("importance") or 1),
            })
        return archived

    def restore_archived_memory(self, archive_id: int) -> int:
        row = self.conn.execute(
            "SELECT * FROM memory_archive WHERE id=? AND restored_at IS NULL",
            (int(archive_id),),
        ).fetchone()
        if row is None:
            return 0
        snapshot = json.loads(str(row["snapshot"]))
        restored_at = local_wall_time().isoformat(timespec="seconds")
        with self.conn:
            self.conn.execute(
                "INSERT INTO memories(category,title,content,source,importance,"
                "created_at,updated_at,scope,expires_at,last_used_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(content) DO UPDATE SET "
                "importance=MAX(memories.importance,excluded.importance),"
                "updated_at=excluded.updated_at",
                (
                    snapshot["category"],
                    snapshot["title"],
                    snapshot["content"],
                    snapshot["source"],
                    snapshot["importance"],
                    snapshot["created_at"],
                    snapshot["updated_at"],
                    snapshot.get("scope", "personal"),
                    snapshot.get("expires_at"),
                    snapshot.get("last_used_at"),
                ),
            )
            self.conn.execute(
                "UPDATE memory_archive SET restored_at=? WHERE id=?",
                (restored_at, int(archive_id)),
            )
        restored = self.conn.execute(
            "SELECT id FROM memories WHERE content=?",
            (snapshot["content"],),
        ).fetchone()
        self._memory_index.clear()
        return int(restored["id"]) if restored else 0

    @staticmethod
    def _memory_age_days(row: sqlite3.Row, now: datetime) -> float:
        raw = str(row["last_used_at"] or row["updated_at"] or row["created_at"])
        try:
            return max(0.0, (now - datetime.fromisoformat(raw)).total_seconds() / 86400)
        except ValueError:
            return 3650.0

    def _consolidate_auto_duplicates(
        self,
        rows: list[sqlite3.Row],
        threshold: float = 0.90,
    ) -> int:
        candidates = [
            row
            for row in rows
            if str(row["source"]) == "conversation" and int(row["importance"]) <= LOW_IMPORTANCE_THRESHOLD
        ]
        vectors = {
            int(row["id"]): hashed_text_vector(str(row["content"]))
            for row in candidates
        }
        archived = 0
        consumed: set[int] = set()
        for index, keeper in enumerate(candidates):
            keeper_id = int(keeper["id"])
            if keeper_id in consumed:
                continue
            duplicate_ids: list[int] = []
            contents = [str(keeper["content"])]
            for other in candidates[index + 1 :]:
                other_id = int(other["id"])
                if other_id in consumed or other["category"] != keeper["category"]:
                    continue
                if (
                    cosine_similarity(vectors[keeper_id], vectors[other_id])
                    >= threshold
                ):
                    duplicate_ids.append(other_id)
                    contents.append(str(other["content"]))
                    consumed.add(other_id)
            if not duplicate_ids:
                continue
            summary = self._merge_memory_contents(contents)
            archived += self._archive_memory_ids(
                duplicate_ids,
                "semantic-deduplication",
            )
            with self.conn:
                self.conn.execute(
                    "UPDATE memories SET content=?,updated_at=? WHERE id=?",
                    (
                        summary,
                        local_wall_time().isoformat(timespec="seconds"),
                        keeper_id,
                    ),
                )
        return archived

    @staticmethod
    def _merge_memory_contents(contents: list[str], limit: int = 500) -> str:
        """Merge near-duplicate facts without inventing or discarding details."""
        fragments: list[str] = []
        seen: set[str] = set()
        for content in contents:
            for fragment in re.split(r"(?<=[。！？.!?])\s*|[；;]\s*", content):
                cleaned = " ".join(fragment.split()).strip()
                key = re.sub(r"\W+", "", cleaned).casefold()
                if not cleaned or not key or key in seen:
                    continue
                seen.add(key)
                fragments.append(cleaned)
        merged = " ".join(fragments) or max(contents, key=len, default="")
        if len(merged) > limit:
            merged = merged[: max(1, limit - 1)].rstrip() + "…"
        return merged

    def optimize_memories(
        self,
        max_active: int = 500,
        target_active: int = 400,
        now: datetime | None = None,
    ) -> dict[str, int]:
        if target_active <= 0 or max_active < target_active:
            raise ValueError("memory limits are invalid")
        reference = now or local_wall_time()
        rows = self.list_memories(10000)
        deduplicated = self._consolidate_auto_duplicates(rows)
        rows = self.list_memories(10000)
        excess = max(0, len(rows) - target_active) if len(rows) > max_active else 0
        eligible = sorted(
            (
                row
                for row in rows
                if str(row["source"]) == "conversation"
                and int(row["importance"]) <= LOW_IMPORTANCE_THRESHOLD
                and self._memory_age_days(row, reference) >= MEMORY_AGE_DAYS
            ),
            key=lambda row: (
                int(row["importance"]),
                str(row["last_used_at"] or row["updated_at"] or row["created_at"]),
                int(row["id"]),
            ),
        )
        pruned = self._archive_memory_ids(
            [int(row["id"]) for row in eligible[:excess]],
            "capacity-pruning",
        )
        return {
            "deduplicated": deduplicated,
            "pruned": pruned,
            "active": len(self.list_memories(10000)),
            "archived": len(self.list_archived_memories(10000)),
        }

    def optimize_database(self) -> dict[str, int]:
        """Reclaim space and prune stale rows without blocking the UI.

        SQLite WAL files grow over time; a periodic VACUUM plus a bounded
        cleanup of old completed todos and audit rows keeps the profile
        database small and responsive.  This is safe to call from a background
        worker because it only touches rows that are safe to remove.
        """
        now = local_wall_time().isoformat(timespec="seconds")
        pruned_todos = 0
        pruned_audit = 0
        try:
            cursor = self.conn.execute(
                "DELETE FROM todos WHERE status='完成' AND completed_at IS NOT NULL "
                "AND completed_at < ?",
                (now,),
            )
            pruned_todos = max(0, int(cursor.rowcount))
            cursor = self.conn.execute(
                "DELETE FROM action_audit WHERE created_at < ?",
                (now,),
            )
            pruned_audit = max(0, int(cursor.rowcount))
            self.conn.commit()
            self.conn.execute("VACUUM")
        except sqlite3.Error:
            return {"pruned_todos": 0, "pruned_audit": 0, "vacuumed": False}
        return {
            "pruned_todos": pruned_todos,
            "pruned_audit": pruned_audit,
            "vacuumed": True,
        }

    def recent_chat_context(
        self,
        limit: int = 16,
        max_chars: int = 4000,
    ) -> list[sqlite3.Row]:
        """Return recent chat bounded by both count and total characters."""
        rows = list(
            self.conn.execute(
                "SELECT * FROM chat_log ORDER BY id DESC LIMIT ?", (limit,)
            )
        )
        rows.reverse()
        selected: list[sqlite3.Row] = []
        total = 0
        for row in rows:
            content = str(row["content"] or "")
            total += len(content)
            if total > max_chars and selected:
                break
            selected.append(row)
        return selected

    def update_memory_policy(
        self,
        memory_id: int,
        *,
        scope: str = "personal",
        expires_at: str | None = None,
    ) -> None:
        if scope not in {"session", "personal", "work", "shared"}:
            raise ValueError("不支援的記憶範圍")
        if expires_at:
            datetime.fromisoformat(expires_at)
        with self.conn:
            self.conn.execute(
                "UPDATE memories SET scope=?,expires_at=?,updated_at=? WHERE id=?",
                (
                    scope,
                    expires_at,
                    local_wall_time().isoformat(timespec="seconds"),
                    int(memory_id),
                ),
            )

    def purge_expired_memories(self) -> int:
        now = local_wall_time().isoformat(timespec="seconds")
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now,),
            )
        return max(0, int(cursor.rowcount))

    def export_memories(self) -> list[dict]:
        return [
            {
                key: row[key]
                for key in (
                    "id",
                    "category",
                    "content",
                    "source",
                    "importance",
                    "scope",
                    "expires_at",
                    "created_at",
                    "updated_at",
                )
            }
            for row in self.list_memories(10000)
        ]
