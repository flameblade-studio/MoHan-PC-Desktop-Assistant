from __future__ import annotations

lazy import copy
lazy import sys
lazy from collections.abc import Mapping
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from gesture_configuration import (
    BUILTIN_GESTURE_LABELS,
    GESTURE_ACTION_LABELS,
    GestureAction,
    GestureBinding,
    GestureConfiguration,
    GestureDefinition,
    GestureLandmark,
    GestureSample,
    GestureSource,
    export_gesture_configuration,
    import_gesture_configuration,
)
lazy from infrastructure.gesture_configuration_store import (
    GESTURE_CONFIGURATION_KEY,
    PORTABLE_GESTURE_SETTING_KEYS,
    GestureConfigurationStore,
    GestureConfigurationStoreError,
)

CUSTOM_GESTURE_SAMPLE_COUNT = 2


class MemorySettings:
    def __init__(
        self,
        values: Mapping[str, object] | None = None,
        *,
        fail_write: bool = False,
        fail_restore: bool = False,
    ) -> None:
        self.values = copy.deepcopy(dict(values or {}))
        self.fail_write = fail_write
        self.fail_restore = fail_restore

    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        return {key: self.values[key] for key in keys if key in self.values}

    def snapshot(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {key: copy.deepcopy(self.values[key]) for key in keys if key in self.values}

    def write(self, values: Mapping[str, object]) -> None:
        self.values.update(copy.deepcopy(values))
        if self.fail_write:
            raise RuntimeError("PRIVATE-GESTURE-WRITE")

    def restore(self, snapshot: dict[str, object]) -> None:
        if self.fail_restore:
            raise RuntimeError("PRIVATE-GESTURE-RESTORE")
        for key in PORTABLE_GESTURE_SETTING_KEYS:
            self.values.pop(key, None)
        self.values.update(copy.deepcopy(snapshot))


def sample(offset: float = 0.0) -> GestureSample:
    return GestureSample(tuple(
        GestureLandmark(index / 20 + offset, index / 40, 0.0)
        for index in range(21)
    ))


def assert_defaults_are_complete_safe_and_four_language() -> None:
    configuration = GestureConfiguration()
    assert configuration.enabled is False
    assert tuple(BUILTIN_GESTURE_LABELS) == tuple(
        definition.gesture_id for definition in configuration.definitions
    )
    assert configuration.definition("wave").binding.action is GestureAction.NONE
    assert configuration.definition("silence").binding.action is GestureAction.MUTE_AUDIO
    assert configuration.definition("closed-fist").binding.action is GestureAction.NONE
    labels = (*BUILTIN_GESTURE_LABELS.values(), *GESTURE_ACTION_LABELS.values())
    assert all(
        label.traditional_chinese.strip()
        and label.simplified_chinese.strip()
        and label.english.strip()
        and label.japanese.strip()
        for label in labels
    )


def assert_custom_gestures_can_be_added_edited_and_deleted() -> None:
    configuration = GestureConfiguration().add_custom(
        "我的手勢",
        (sample(), sample(0.01)),
        gesture_id="custom:my-gesture",
        binding=GestureBinding(GestureAction.CUSTOM_COMMAND, "切換陪伴模式"),
    )
    custom = configuration.definition("custom:my-gesture")
    assert custom.source is GestureSource.CUSTOM
    assert len(custom.samples) == CUSTOM_GESTURE_SAMPLE_COUNT
    updated = GestureDefinition(
        custom.gesture_id,
        "新的名稱",
        custom.source,
        False,
        GestureBinding(GestureAction.STOP_SPEECH),
        custom.samples,
    )
    configuration = configuration.replace_definition(updated)
    assert configuration.definition(custom.gesture_id) == updated
    assert all("image" not in field for field in export_gesture_configuration(configuration))
    configuration = configuration.remove_custom(custom.gesture_id)
    try:
        configuration.definition(custom.gesture_id)
    except KeyError:
        pass
    else:
        raise AssertionError("deleted custom gesture remains")
    try:
        configuration.remove_custom("wave")
    except ValueError:
        pass
    else:
        raise AssertionError("built-in gesture was deleted")


def assert_round_trip_restores_missing_builtins_and_rejects_corruption() -> None:
    configuration = GestureConfiguration(enabled=True).add_custom(
        "自訂",
        (sample(),),
        gesture_id="custom:portable",
    )
    ordinary_payload = export_gesture_configuration(configuration)
    ordinary_custom = next(
        item
        for item in ordinary_payload["definitions"]
        if item["gesture_id"] == "custom:portable"
    )
    assert "samples" not in ordinary_custom
    ordinary_import = import_gesture_configuration(ordinary_payload)
    assert ordinary_import.definition("custom:portable").samples == ()

    protected_payload = export_gesture_configuration(
        configuration,
        include_samples=True,
    )
    assert import_gesture_configuration(
        protected_payload,
        include_samples=True,
    ) == configuration

    ordinary_payload["definitions"] = [
        item
        for item in ordinary_payload["definitions"]
        if item["gesture_id"] != "wave"
    ]
    restored = import_gesture_configuration(ordinary_payload)
    assert restored.definition("wave").source is GestureSource.BUILTIN
    for corrupt in (
        {"format": "wrong", "version": 1},
        {"format": "mohan-gesture-configuration", "version": 1, "enabled": "yes"},
        {"format": "mohan-gesture-configuration", "version": 1, "definitions": "bad"},
    ):
        assert import_gesture_configuration(corrupt) == GestureConfiguration()


def assert_store_is_staged_atomic_and_portable() -> None:
    settings = MemorySettings({"unrelated": {"keep": True}})
    store = GestureConfigurationStore(settings)
    draft = store.begin_edit().set_enabled(True)
    assert store.load().enabled is False
    expected = draft.commit()
    assert store.load() == expected
    assert settings.values["unrelated"] == {"keep": True}
    assert GESTURE_CONFIGURATION_KEY in settings.values
    target = GestureConfigurationStore(MemorySettings())
    assert target.import_portable(store.export_portable()) == expected
    cancelled = store.begin_edit().set_enabled(False).cancel()
    assert cancelled == expected
    assert store.load() == expected


def assert_store_failure_rolls_back_without_private_details() -> None:
    original = {GESTURE_CONFIGURATION_KEY: export_gesture_configuration(GestureConfiguration())}
    settings = MemorySettings(original, fail_write=True)
    try:
        GestureConfigurationStore(settings).save(GestureConfiguration(enabled=True))
    except GestureConfigurationStoreError as error:
        assert "PRIVATE" not in str(error)
    else:
        raise AssertionError("failing gesture save unexpectedly succeeded")
    assert settings.values == original
    broken = MemorySettings(original, fail_write=True, fail_restore=True)
    try:
        GestureConfigurationStore(broken).save(GestureConfiguration(enabled=True))
    except GestureConfigurationStoreError as error:
        assert "rollback was incomplete" in str(error)
        assert "PRIVATE" not in str(error)
    else:
        raise AssertionError("failing gesture rollback unexpectedly succeeded")


def run() -> None:
    assert_defaults_are_complete_safe_and_four_language()
    assert_custom_gestures_can_be_added_edited_and_deleted()
    assert_round_trip_restores_missing_builtins_and_rejects_corruption()
    assert_store_is_staged_atomic_and_portable()
    assert_store_failure_rolls_back_without_private_details()
    print("GESTURE_CONFIGURATION_OK")


if __name__ == "__main__":
    run()
