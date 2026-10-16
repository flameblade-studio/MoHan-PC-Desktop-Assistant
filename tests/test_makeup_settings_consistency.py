"""Regression coverage for concurrent and recoverable makeup settings state."""

from __future__ import annotations

lazy import json
lazy import threading
lazy from pathlib import Path

lazy import pytest

lazy from domain import outfit_pack_makeup as makeup


HUGE_INTEGER = 10**1000
FOUNDATION_VALUE = 0.4
FOUNDATION = "foundation"


def test_global_huge_integer_keeps_last_valid_value_and_notifies(tmp_path: Path) -> None:
    store = tmp_path / "global"
    makeup.write_makeup_intensity(store, 0.3)
    (store / makeup.MAKEUP_STATE_FILE).write_text(
        json.dumps({"intensity": HUGE_INTEGER}), encoding="utf-8"
    )

    messages: list[str] = []
    assert makeup.read_makeup_intensity(store, messages.append) == pytest.approx(0.3)
    assert messages == [makeup.MAKEUP_READ_FAILURE_MESSAGE]


def test_slot_huge_integer_keeps_last_valid_value_and_notifies(tmp_path: Path) -> None:
    store = tmp_path / "slot"
    makeup.write_makeup_slot_intensity(store, "lips", 0.3)
    (store / makeup.MAKEUP_STATE_FILE).write_text(
        json.dumps(
            {"intensity": 1.0, "slot_intensities": {"lips": HUGE_INTEGER}}
        ),
        encoding="utf-8",
    )

    messages: list[str] = []
    values = makeup.read_makeup_slot_intensities(store, messages.append)
    assert values["lips"] == pytest.approx(0.3)
    assert messages == [makeup.MAKEUP_READ_FAILURE_MESSAGE]


def test_legacy_pose_read_and_write_preserve_shared_foundation(tmp_path: Path) -> None:
    """A three-slot pose edits shared state while preserving foundation."""
    store = tmp_path / "crosspose"
    makeup.write_makeup_slot_intensity(
        store, FOUNDATION, FOUNDATION_VALUE, slots=makeup.MAKEUP_SLOTS_V2,
    )
    makeup.write_makeup_slot_intensity(
        store, "eyes", 0.25, slots=makeup.MAKEUP_SLOTS_V2,
    )
    makeup.write_makeup_slot_intensity(
        store, "lips", 0.6, slots=makeup.MAKEUP_SLOTS_V2,
    )

    legacy_values = makeup.read_makeup_slot_intensities(
        store, slots=makeup.MAKEUP_SLOTS,
    )
    assert legacy_values == {"eyes": 0.25, "cheeks": 1.0, "lips": 0.6}
    assert FOUNDATION not in legacy_values

    makeup.write_makeup_slot_intensity(
        store, "cheeks", 0.35, slots=makeup.MAKEUP_SLOTS,
    )
    assert makeup.read_makeup_slot_intensities(
        store, slots=makeup.MAKEUP_SLOTS_V2,
    ) == {
        "eyes": 0.25,
        "cheeks": 0.35,
        "lips": 0.6,
        FOUNDATION: FOUNDATION_VALUE,
    }
    persisted = json.loads((store / makeup.MAKEUP_STATE_FILE).read_text(encoding="utf-8"))
    assert persisted["slot_intensities"][FOUNDATION] == FOUNDATION_VALUE


@pytest.mark.parametrize(
    "persisted_slots",
    ({FOUNDATION: "broken"}, {"unknown": 0.2}),
)
def test_legacy_read_rejects_invalid_or_unknown_v2_entries(
    tmp_path: Path, persisted_slots: dict[str, object],
) -> None:
    """Legacy results retain full-map validation before foundation filtering."""
    store = tmp_path / "crosspose-invalid"
    makeup.write_makeup_slot_intensity(
        store, "eyes", 0.3, slots=makeup.MAKEUP_SLOTS_V2,
    )
    payload = {"intensity": 1.0, "slot_intensities": persisted_slots}
    (store / makeup.MAKEUP_STATE_FILE).write_text(
        json.dumps(payload), encoding="utf-8",
    )
    messages: list[str] = []
    values = makeup.read_makeup_slot_intensities(
        store, messages.append, slots=makeup.MAKEUP_SLOTS,
    )
    assert values["eyes"] == pytest.approx(0.3)
    assert values["cheeks"] == 1.0
    assert values["lips"] == 1.0
    assert messages == [makeup.MAKEUP_READ_FAILURE_MESSAGE]


def test_read_without_callback_does_not_consume_later_warning(tmp_path: Path) -> None:
    store = tmp_path / "warning"
    store.mkdir()
    (store / makeup.MAKEUP_STATE_FILE).write_text(
        json.dumps({"intensity": "broken"}), encoding="utf-8"
    )

    assert makeup.read_makeup_intensity(store) == 1.0
    messages: list[str] = []
    assert makeup.read_makeup_intensity(store, messages.append) == 1.0
    assert messages == [makeup.MAKEUP_READ_FAILURE_MESSAGE]
    assert makeup.read_makeup_intensity(store, messages.append) == 1.0
    assert messages == [makeup.MAKEUP_READ_FAILURE_MESSAGE]


def test_parallel_slot_writes_preserve_independent_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "race"
    original_read = makeup.read_makeup_slot_intensities
    first_read_started = threading.Event()
    second_read_started = threading.Event()
    release_first_read = threading.Event()
    read_count = 0
    read_count_lock = threading.Lock()

    def delayed_read(store_path: Path, notify=None, *, slots=None):
        nonlocal read_count
        result = original_read(store_path, notify, slots=slots)
        with read_count_lock:
            index = read_count
            read_count += 1
        if index == 0:
            first_read_started.set()
            if not release_first_read.wait(timeout=5):
                raise TimeoutError("first makeup read was not released")
        elif index == 1:
            second_read_started.set()
        return result

    monkeypatch.setattr(makeup, "read_makeup_slot_intensities", delayed_read)
    errors: list[BaseException] = []

    def write_slot(slot: str, value: float) -> None:
        try:
            makeup.write_makeup_slot_intensity(store, slot, value)
        except BaseException as exc:  # pragma: no cover - exception is asserted below
            errors.append(exc)

    first = threading.Thread(target=write_slot, args=("eyes", 0.2))
    second = threading.Thread(target=write_slot, args=("lips", 0.3))
    blocked_before_release = False
    first_started = False
    second_started = False
    try:
        first.start()
        first_started = True
        assert first_read_started.wait(timeout=5)
        second.start()
        second_started = True
        blocked_before_release = not second_read_started.wait(timeout=0.5)
    finally:
        release_first_read.set()
        if first_started:
            first.join(timeout=5)
        if second_started:
            second.join(timeout=5)

    assert blocked_before_release
    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert original_read(store) == {
        "eyes": 0.2,
        "cheeks": 1.0,
        "lips": 0.3,
    }
