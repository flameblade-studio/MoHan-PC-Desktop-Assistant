from __future__ import annotations

lazy import sqlite3
lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.db_affection import StudioDBAffectionMethods

UPSERT_ROUNDS = 5
LEGACY_ROWS = 3
FLOAT_TOLERANCE = 1e-9
REWRITTEN_FAVOR = 0.9


class _AffectionStore(StudioDBAffectionMethods):
    """The affection mixin over an in-memory copy of the production schema."""

    def __init__(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE companion_affection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                favor_score REAL NOT NULL DEFAULT 0.0,
                trust_level REAL NOT NULL DEFAULT 0.0,
                jealousy_meter REAL NOT NULL DEFAULT 0.0,
                satiety_level REAL NOT NULL DEFAULT 1.0,
                devotion_bonus INTEGER NOT NULL DEFAULT 0,
                last_interaction_ts TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )

    def row_count(self) -> int:
        return int(
            self.conn.execute(
                "SELECT COUNT(*) FROM companion_affection"
            ).fetchone()[0]
        )

    def write(self, favor: float) -> None:
        self.upsert_affection(
            favor_score=favor,
            trust_level=favor / 2.0,
            jealousy_meter=0.0,
            satiety_level=1.0,
            devotion_bonus=0,
            last_interaction_ts=None,
        )


def test_upsert_updates_in_place_and_read_returns_latest() -> None:
    """Ruling 2026-08-27: persisted affection must actually take effect.

    The historical write INSERTed one row per interaction while the read
    returned the OLDEST row, so the visible affection froze at its first
    value and the table grew without bound.
    """
    store = _AffectionStore()
    assert store.affection_row() is None
    for round_index in range(1, UPSERT_ROUNDS + 1):
        store.write(favor=float(round_index) / 10.0)
    assert store.row_count() == 1
    row = store.affection_row()
    assert row is not None
    assert abs(float(row["favor_score"]) - UPSERT_ROUNDS / 10.0) < FLOAT_TOLERANCE


def test_read_repairs_databases_with_legacy_row_pileup() -> None:
    store = _AffectionStore()
    for round_index in range(1, LEGACY_ROWS + 1):
        store.conn.execute(
            "INSERT INTO companion_affection("
            "favor_score,trust_level,jealousy_meter,satiety_level,"
            "devotion_bonus,last_interaction_ts,updated_at"
            ") VALUES(?,0,0,1,0,NULL,'legacy')",
            (float(round_index) / 10.0,),
        )
    row = store.affection_row()
    assert row is not None
    assert abs(float(row["favor_score"]) - LEGACY_ROWS / 10.0) < FLOAT_TOLERANCE
    store.write(favor=REWRITTEN_FAVOR)
    assert store.row_count() == LEGACY_ROWS
    latest = store.affection_row()
    assert latest is not None
    assert abs(float(latest["favor_score"]) - REWRITTEN_FAVOR) < FLOAT_TOLERANCE


def run() -> None:
    test_upsert_updates_in_place_and_read_returns_latest()
    test_read_repairs_databases_with_legacy_row_pileup()
    print("AFFECTION_UPSERT_OK")


if __name__ == "__main__":
    run()
