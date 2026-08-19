from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.affinity_state import AffinityState


class _FakeDB:
    """Minimal settings store mirroring the db.setting / db.set_setting contract."""

    def __init__(self) -> None:
        self._values: dict[str, object] = {}

    def setting(self, key: str, default: object = None) -> object:
        return self._values.get(key, default)

    def set_setting(self, key: str, value: object) -> None:
        self._values[key] = value


def _load_affinity(db: _FakeDB) -> AffinityState:
    """Mirror companion_core._initialize_companion_state's load path."""
    return AffinityState(
        affinity=float(db.setting("affinity_value", 0.0)),
        jealousy=float(db.setting("jealousy_value", 0.0)),
        interaction_count=int(db.setting("affinity_interaction_count", 0)),
    )


def _save_affinity(db: _FakeDB, state: AffinityState) -> None:
    """Mirror companion_proactive._note_human_interaction's save path."""
    snapshot = state.note_interaction()
    db.set_setting("affinity_value", snapshot.affinity)
    db.set_setting("jealousy_value", snapshot.jealousy)
    db.set_setting("affinity_interaction_count", snapshot.interaction_count)


def test_affinity_survives_restart() -> None:
    db = _FakeDB()
    state = _load_affinity(db)
    assert state.affinity == 0.0
    assert state.interaction_count == 0

    # Simulate a session of interactions, persisting after each.
    for _ in range(10):
        _save_affinity(db, state)

    # A "restart" rebuilds the state purely from the db.
    rebuilt = _load_affinity(db)
    assert rebuilt.affinity > 0.0
    assert rebuilt.interaction_count == 10
    assert rebuilt.affinity == state.affinity


def test_affinity_loads_existing_value() -> None:
    db = _FakeDB()
    db.set_setting("affinity_value", 0.6)
    db.set_setting("affinity_interaction_count", 42)
    state = _load_affinity(db)
    assert state.affinity == 0.6
    assert state.interaction_count == 42
    assert state.snapshot(now=0.0).stage == "close"


def test_affinity_persistence_round_trip() -> None:
    db = _FakeDB()
    state = _load_affinity(db)
    for _ in range(5):
        _save_affinity(db, state)
    assert float(db.setting("affinity_value", 0.0)) == state.affinity
    assert int(db.setting("affinity_interaction_count", 0)) == state.interaction_count


def test_jealousy_survives_restart() -> None:
    db = _FakeDB()
    state = _load_affinity(db)
    state.note_jealousy(now=0.0)
    db.set_setting("jealousy_value", state.jealousy)
    # A "restart" rebuilds the state purely from the db.
    rebuilt = _load_affinity(db)
    assert rebuilt.jealousy == state.jealousy
    assert rebuilt.jealousy > 0.5


def run() -> None:
    test_affinity_survives_restart()
    test_affinity_loads_existing_value()
    test_affinity_persistence_round_trip()
    test_jealousy_survives_restart()
    print("AFFINITY_PERSISTENCE_OK")


if __name__ == "__main__":
    run()
