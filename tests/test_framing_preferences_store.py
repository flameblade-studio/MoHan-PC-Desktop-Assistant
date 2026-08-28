from __future__ import annotations

lazy import copy
lazy import sys
lazy from collections.abc import Mapping
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.framing_preferences import (
    ADAPTIVE_FRAMING_KEY,
    PREFERRED_FRAMING_KEY,
    SETTING_KEYS,
    FramingPreferences,
    PreferredFraming,
)
lazy from infrastructure.framing_preferences_store import (
    STORE_SCHEMA_KEY,
    FramingPreferencesStore,
    FramingPreferencesStoreError,
)


class MemorySettings:
    def __init__(
        self,
        values: Mapping[str, object] | None = None,
        *,
        fail_write_after: int | None = None,
    ) -> None:
        self.values = dict(values or {})
        self.write_calls = 0
        self.restore_calls = 0
        self.fail_write_after = fail_write_after

    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def snapshot(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {key: copy.deepcopy(self.values[key]) for key in keys if key in self.values}

    def write(self, values: Mapping[str, object]) -> None:
        self.write_calls += 1
        for index, (key, value) in enumerate(values.items()):
            self.values[key] = copy.deepcopy(value)
            if self.fail_write_after is not None and index >= self.fail_write_after:
                raise RuntimeError("PRIVATE-WRITE-DETAIL")

    def restore(self, snapshot: dict[str, object]) -> None:
        self.restore_calls += 1
        for key in (*SETTING_KEYS, STORE_SCHEMA_KEY):
            self.values.pop(key, None)
        self.values.update(copy.deepcopy(snapshot))


def assert_staged_save_and_cancel() -> None:
    settings = MemorySettings()
    store = FramingPreferencesStore(settings)
    draft = store.begin_edit().update(
        adaptive_enabled=False,
        preferred_framing=PreferredFraming.HALF,
    )
    draft.cancel()
    assert settings.write_calls == 0
    committed = store.begin_edit().update(
        allow_close=False,
        preferred_framing=PreferredFraming.THREE_QUARTER,
    ).commit()
    assert settings.write_calls == 1
    assert store.load() == committed


def assert_atomic_rollback_and_legacy_migration() -> None:
    original = {ADAPTIVE_FRAMING_KEY: True, "unrelated": "keep"}
    settings = MemorySettings(original, fail_write_after=2)
    store = FramingPreferencesStore(settings)
    try:
        store.save(FramingPreferences(adaptive_enabled=False))
    except FramingPreferencesStoreError as exc:
        assert "PRIVATE" not in str(exc)
    else:
        raise AssertionError("partial save must fail")
    assert settings.values == original

    legacy = MemorySettings(
        {
            "adaptive_framing_enabled": False,
            "allow_close_framing": False,
            "preferred_framing": "full_body",
            "unrelated": "keep",
        }
    )
    migrated = FramingPreferencesStore(legacy).migrate()
    assert migrated.adaptive_enabled is False
    assert migrated.allow_close is False
    assert migrated.preferred_framing is PreferredFraming.FULL_BODY
    assert legacy.values[PREFERRED_FRAMING_KEY] == "full_body"
    assert legacy.values["unrelated"] == "keep"


def assert_unknown_private_fields_are_not_persisted() -> None:
    settings = MemorySettings({"api_key": "local-secret"})
    store = FramingPreferencesStore(settings)
    payload = store.export_portable()
    payload["secret"] = "must-not-persist"
    payload["preferences"]["face_embedding"] = [0.1]
    payload["preferences"]["camera_frame"] = "frame"
    payload["preferences"]["private_phrasebook"] = "private"
    store.import_portable(payload)
    assert settings.values["api_key"] == "local-secret"
    forbidden = {"secret", "face_embedding", "camera_frame", "private_phrasebook"}
    assert forbidden.isdisjoint(settings.values)


def run() -> None:
    assert_staged_save_and_cancel()
    assert_atomic_rollback_and_legacy_migration()
    assert_unknown_private_fields_are_not_persisted()
    print("FRAMING_PREFERENCES_STORE_OK")


if __name__ == "__main__":
    run()
