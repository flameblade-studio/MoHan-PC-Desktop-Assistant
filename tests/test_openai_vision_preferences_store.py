from __future__ import annotations

lazy import copy
lazy import sys
lazy from collections.abc import Mapping
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.openai_vision_preferences_store import (
    PORTABLE_SETTING_KEYS,
    OpenAIVisionPreferencesStore,
    OpenAIVisionPreferencesStoreError,
)
lazy from domain.openai_vision_preferences import OpenAIVisionPreferences


class MemorySettings:
    def __init__(self, *, fail_write: bool = False) -> None:
        self.values: dict[str, object] = {"unrelated": "keep"}
        self.fail_write = fail_write
        self.write_calls = 0

    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def snapshot(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {
            key: copy.deepcopy(self.values[key])
            for key in keys
            if key in self.values
        }

    def write(self, values: Mapping[str, object]) -> None:
        self.write_calls += 1
        self.values.update(copy.deepcopy(values))
        if self.fail_write:
            raise RuntimeError("SECRET-BACKEND-CONTENT")

    def restore(self, snapshot: dict[str, object]) -> None:
        for key in PORTABLE_SETTING_KEYS:
            self.values.pop(key, None)
        self.values.update(copy.deepcopy(snapshot))


def assert_staging_round_trip_and_rollback() -> None:
    settings = MemorySettings()
    store = OpenAIVisionPreferencesStore(settings)
    assert store.load() == OpenAIVisionPreferences()
    assert store.begin_edit().update(enabled=True).cancel() == (
        OpenAIVisionPreferences()
    )
    assert settings.write_calls == 0

    expected = store.begin_edit().update(
        enabled=True,
        cloud_vision_enabled=True,
        object_semantics_enabled=True,
    ).commit()
    assert store.load() == expected
    target = OpenAIVisionPreferencesStore(MemorySettings())
    assert target.import_portable(store.export_portable()) == expected

    failing_settings = MemorySettings(fail_write=True)
    before = copy.deepcopy(failing_settings.values)
    try:
        OpenAIVisionPreferencesStore(failing_settings).save(expected)
    except OpenAIVisionPreferencesStoreError as exc:
        assert "SECRET" not in str(exc)
    else:
        raise AssertionError("failing write unexpectedly succeeded")
    assert failing_settings.values == before


def run() -> None:
    assert_staging_round_trip_and_rollback()
    print("OPENAI_VISION_PREFERENCES_STORE_OK")


if __name__ == "__main__":
    run()
