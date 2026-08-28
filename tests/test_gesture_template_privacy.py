from __future__ import annotations

lazy import copy
lazy from collections.abc import Mapping

lazy import pytest

lazy from domain.gesture_configuration import (
    GestureConfiguration,
    GestureLandmark,
    GestureSample,
    export_gesture_configuration,
)
lazy from infrastructure.gesture_configuration_store import (
    GESTURE_CONFIGURATION_KEY,
    GestureConfigurationStore,
    GestureConfigurationStoreError,
)
lazy from infrastructure.gesture_template_store import (
    MAX_GESTURE_TEMPLATES_BYTES,
    GestureTemplateStoreError,
    ProtectedGestureTemplateStore,
)

SAMPLE_COUNT = 2
LANDMARK_COUNT = 21


class MemorySecretStore:
    def __init__(
        self,
        value: str = "",
        *,
        fail_load: bool = False,
        fail_save: bool = False,
        mutate_before_save_failure: bool = False,
        fail_clear: bool = False,
    ) -> None:
        self.value = value
        self.fail_load = fail_load
        self.fail_save = fail_save
        self.mutate_before_save_failure = mutate_before_save_failure
        self.fail_clear = fail_clear

    def load(self) -> str:
        if self.fail_load:
            raise RuntimeError("SYNTHETIC-PRIVATE-LOAD")
        return self.value

    def save(self, value: str) -> None:
        if self.fail_save:
            if self.mutate_before_save_failure:
                self.value = value
            raise RuntimeError("SYNTHETIC-PRIVATE-SAVE")
        self.value = value

    def clear(self) -> None:
        if self.fail_clear:
            raise RuntimeError("SYNTHETIC-PRIVATE-CLEAR")
        self.value = ""


class MemorySettings:
    def __init__(self, values: Mapping[str, object] | None = None) -> None:
        self.values = copy.deepcopy(dict(values or {}))
        self.fail_write = False
        self.fail_restore = False

    def read(self, keys: tuple[str, ...]) -> Mapping[str, object]:
        return {key: copy.deepcopy(self.values[key]) for key in keys if key in self.values}

    def snapshot(self, keys: tuple[str, ...]) -> dict[str, object]:
        return {key: copy.deepcopy(self.values[key]) for key in keys if key in self.values}

    def write(self, values: Mapping[str, object]) -> None:
        self.values.update(copy.deepcopy(values))
        if self.fail_write:
            raise RuntimeError("SYNTHETIC-PRIVATE-WRITE")

    def restore(self, snapshot: dict[str, object]) -> None:
        if self.fail_restore:
            raise RuntimeError("SYNTHETIC-PRIVATE-RESTORE")
        self.values.pop(GESTURE_CONFIGURATION_KEY, None)
        self.values.update(copy.deepcopy(snapshot))


def _sample(offset: float = 0.0) -> GestureSample:
    return GestureSample(
        tuple(
            GestureLandmark(index / 20.0 + offset, index / 40.0, -index / 80.0)
            for index in range(21)
        )
    )


def _configuration() -> GestureConfiguration:
    return GestureConfiguration(enabled=True).add_custom(
        "Synthetic gesture",
        (_sample(), _sample(0.01)),
        gesture_id="custom:synthetic-private",
    )


def _assert_safe(error: Exception) -> None:
    assert "SYNTHETIC-PRIVATE" not in str(error)
    assert error.__cause__ is None


def test_public_export_excludes_samples_and_protected_export_is_opt_in() -> None:
    configuration = _configuration()

    public_payload = export_gesture_configuration(configuration)
    protected_payload = export_gesture_configuration(configuration, include_samples=True)

    assert all("samples" not in definition for definition in public_payload["definitions"])
    custom = next(
        definition
        for definition in protected_payload["definitions"]
        if definition["gesture_id"] == "custom:synthetic-private"
    )
    assert len(custom["samples"]) == SAMPLE_COUNT
    assert len(custom["samples"][0]) == LANDMARK_COUNT


def test_protected_store_saves_loads_and_deletes_templates() -> None:
    secret = MemorySecretStore()
    store = ProtectedGestureTemplateStore(secret)

    store.save(_configuration())
    loaded = store.load()

    assert tuple(loaded) == ("custom:synthetic-private",)
    assert loaded["custom:synthetic-private"] == (_sample(), _sample(0.01))
    store.save(GestureConfiguration())
    assert secret.value == ""
    assert store.load() == {}


@pytest.mark.parametrize(
    "value",
    (
        "not-json",
        '{"format":"wrong","version":1,"templates":{}}',
        '{"format":"mohan-protected-gesture-templates","version":1,"templates":[],"extra":1}',
        '{"format":"mohan-protected-gesture-templates","version":1,"templates":{"bad":[]}}',
    ),
)
def test_protected_store_rejects_corrupt_json_and_schema(value: str) -> None:
    with pytest.raises(GestureTemplateStoreError) as captured:
        ProtectedGestureTemplateStore(MemorySecretStore(value)).load()
    _assert_safe(captured.value)


def test_protected_store_enforces_size_and_fault_boundaries() -> None:
    with pytest.raises(GestureTemplateStoreError) as oversized:
        ProtectedGestureTemplateStore(MemorySecretStore()).restore(
            "x" * (MAX_GESTURE_TEMPLATES_BYTES + 1)
        )
    _assert_safe(oversized.value)

    operations = (
        lambda: ProtectedGestureTemplateStore(
            MemorySecretStore(fail_load=True)
        ).load(),
        lambda: ProtectedGestureTemplateStore(
            MemorySecretStore(fail_save=True)
        ).save(_configuration()),
        lambda: ProtectedGestureTemplateStore(
            MemorySecretStore(fail_clear=True)
        ).save(GestureConfiguration()),
    )
    for operation in operations:
        with pytest.raises(GestureTemplateStoreError) as captured:
            operation()
        _assert_safe(captured.value)


def test_configuration_store_keeps_samples_out_of_general_settings_and_merges_on_load() -> None:
    settings = MemorySettings()
    protected = ProtectedGestureTemplateStore(MemorySecretStore())
    store = GestureConfigurationStore(settings, protected)

    store.save(_configuration())

    definitions = settings.values[GESTURE_CONFIGURATION_KEY]["definitions"]
    assert all("samples" not in definition for definition in definitions)
    loaded = store.load()
    assert loaded.definition("custom:synthetic-private").samples == (
        _sample(),
        _sample(0.01),
    )


def test_configuration_store_rolls_back_both_sides_when_template_save_fails() -> None:
    settings = MemorySettings()
    initial_secret = MemorySecretStore()
    initial_store = GestureConfigurationStore(
        settings,
        ProtectedGestureTemplateStore(initial_secret),
    )
    initial_store.save(GestureConfiguration(enabled=False))
    before_settings = copy.deepcopy(settings.values)
    before_secret = initial_secret.value
    initial_secret.fail_save = True
    initial_secret.mutate_before_save_failure = True

    with pytest.raises(GestureConfigurationStoreError) as captured:
        initial_store.save(_configuration())

    _assert_safe(captured.value)
    assert settings.values == before_settings
    assert initial_secret.value == before_secret


def test_configuration_store_rolls_back_when_general_settings_save_fails() -> None:
    settings = MemorySettings()
    secret = MemorySecretStore()
    store = GestureConfigurationStore(settings, ProtectedGestureTemplateStore(secret))
    store.save(GestureConfiguration(enabled=False))
    before_settings = copy.deepcopy(settings.values)
    before_secret = secret.value
    settings.fail_write = True

    with pytest.raises(GestureConfigurationStoreError) as captured:
        store.save(_configuration())

    _assert_safe(captured.value)
    assert settings.values == before_settings
    assert secret.value == before_secret


def test_samples_are_rejected_without_protected_store() -> None:
    settings = MemorySettings()

    with pytest.raises(GestureConfigurationStoreError) as captured:
        GestureConfigurationStore(settings).save(_configuration())

    _assert_safe(captured.value)
    assert GESTURE_CONFIGURATION_KEY not in settings.values


def test_public_snapshot_restores_both_storage_layers() -> None:
    settings = MemorySettings()
    secret = MemorySecretStore()
    store = GestureConfigurationStore(settings, ProtectedGestureTemplateStore(secret))
    store.save(_configuration())
    before = store.snapshot()

    store.save(GestureConfiguration(enabled=False))
    assert secret.value == ""
    store.restore(before)

    assert store.load() == _configuration()


def test_public_snapshot_reports_incomplete_cross_layer_rollback() -> None:
    settings = MemorySettings()
    secret = MemorySecretStore()
    store = GestureConfigurationStore(settings, ProtectedGestureTemplateStore(secret))
    store.save(_configuration())
    before = store.snapshot()
    settings.fail_restore = True

    with pytest.raises(GestureConfigurationStoreError) as captured:
        store.restore(before)

    _assert_safe(captured.value)
