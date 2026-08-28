from __future__ import annotations

lazy import sqlite3

lazy from domain.time_utils import local_wall_time

__all__ = ("StudioDBAffectionMethods",)


class StudioDBAffectionMethods:
    """Persistence for the companion's exclusive-favor coefficients.

    The single-row ``companion_affection`` table keeps favor, trust, jealousy,
    satiety, and the derived devotion bonus together so the expression arbiter
    can read one consistent snapshot instead of several scattered settings keys.
    """

    def affection_row(self) -> sqlite3.Row | None:
        """Return the most recent companion-affection row, or None if unset.

        Ruling 2026-08-27: the historical write path INSERTed a new row per
        interaction while this read returned the OLDEST row, so persisted
        affection never took effect.  Reading the newest row also repairs
        databases that already accumulated one row per interaction.
        """
        return self.conn.execute(
            "SELECT * FROM companion_affection ORDER BY id DESC LIMIT 1"
        ).fetchone()

    def upsert_affection(
        self,
        *,
        favor_score: float,
        trust_level: float,
        jealousy_meter: float,
        satiety_level: float,
        devotion_bonus: int,
        last_interaction_ts: str | None,
    ) -> None:
        """Persist the companion's exclusive-favor coefficients atomically.

        A true upsert against the newest row: UPDATE it in place, INSERT only
        when the table is empty.  The historical INSERT-per-call grew the
        table without bound and (with the oldest-row read) froze the visible
        affection at its first-ever value.
        """
        updated_at = local_wall_time().isoformat(timespec="seconds")
        values = (
            float(favor_score),
            float(trust_level),
            float(jealousy_meter),
            float(satiety_level),
            int(devotion_bonus),
            last_interaction_ts,
            updated_at,
        )
        updated = self.conn.execute(
            "UPDATE companion_affection SET "
            "favor_score=?,trust_level=?,jealousy_meter=?,satiety_level=?,"
            "devotion_bonus=?,last_interaction_ts=?,updated_at=? "
            "WHERE id=(SELECT MAX(id) FROM companion_affection)",
            values,
        )
        if updated.rowcount == 0:
            self.conn.execute(
                "INSERT INTO companion_affection("
                "favor_score,trust_level,jealousy_meter,satiety_level,"
                "devotion_bonus,last_interaction_ts,updated_at"
                ") VALUES(?,?,?,?,?,?,?)",
                values,
            )
        self.conn.commit()
