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
        """Return the single companion-affection row, or None if unset."""
        return self.conn.execute(
            "SELECT * FROM companion_affection ORDER BY id LIMIT 1"
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
        """Persist the companion's exclusive-favor coefficients atomically."""
        updated_at = local_wall_time().isoformat(timespec="seconds")
        self.conn.execute(
            "INSERT INTO companion_affection("
            "favor_score,trust_level,jealousy_meter,satiety_level,"
            "devotion_bonus,last_interaction_ts,updated_at"
            ") VALUES(?,?,?,?,?,?,?)",
            (
                float(favor_score),
                float(trust_level),
                float(jealousy_meter),
                float(satiety_level),
                int(devotion_bonus),
                last_interaction_ts,
                updated_at,
            ),
        )
        self.conn.commit()
