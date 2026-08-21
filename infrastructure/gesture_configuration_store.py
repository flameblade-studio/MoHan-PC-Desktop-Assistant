from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, replace
lazy from typing import Final, Self, TypeVar

lazy from domain.gesture_configuration import (
    GestureConfiguration,
    GestureDefinition,
    export_gesture_configuration,
    import_gesture_configuration,
)
lazy from domain.performance_preferences import SettingsPort
lazy from infrastructure.gesture_template_store import (
    GestureTemplateStoreError,
    ProtectedGestureTemplateStore,
    merge_protected_templates,
)

GESTURE_CONFIGURATION_KEY: Final = "gesture_configuration_v1"
PORTABLE_GESTURE_SETTING_KEYS: Final = (GESTURE_CONFIGURATION_KEY,)
SnapshotT = TypeVar("SnapshotT")


class GestureConfigurationStoreError(RuntimeError):
    """Fixed-detail storage error that never exposes backend content."""


@dataclass(frozen=True, slots=True)
class GestureConfigurationStoreSnapshot[SnapshotT]:
    """One rollback point spanning ordinary settings and protected templates."""

    settings: SnapshotT
    protected_templates: str | None


@dataclass(slots=True)
class GestureConfigurationDraft[SnapshotT]:
    _store: GestureConfigurationStore[SnapshotT]
    original: GestureConfiguration
    value: GestureConfiguration
    _closed: bool = False

    def replace(self, configuration: GestureConfiguration) -> Self:
        self._assert_open()
        if not isinstance(configuration, GestureConfiguration):
            raise GestureConfigurationStoreError("Gesture draft is invalid.")
        self.value = configuration
        return self

    def update_definition(self, definition: GestureDefinition) -> Self:
        self._assert_open()
        try:
            self.value = self.value.replace_definition(definition)
        except (KeyError, TypeError, ValueError):
            raise GestureConfigurationStoreError("Gesture draft edit is invalid.") from None
        return self

    def set_enabled(self, enabled: bool) -> Self:
        self._assert_open()
        if type(enabled) is not bool:
            raise GestureConfigurationStoreError("Gesture enabled state is invalid.")
        self.value = replace(self.value, enabled=enabled)
        return self

    def commit(self) -> GestureConfiguration:
        self._assert_open()
        self._store.save(self.value)
        self._closed = True
        return self.value

    def cancel(self) -> GestureConfiguration:
        self._assert_open()
        self._closed = True
        self.value = self.original
        return self.original

    def _assert_open(self) -> None:
        if self._closed:
            raise GestureConfigurationStoreError("Gesture draft is already closed.")


class GestureConfigurationStore[SnapshotT]:
    def __init__(
        self,
        settings: SettingsPort[SnapshotT],
        template_store: ProtectedGestureTemplateStore | None = None,
    ) -> None:
        self._settings = settings
        self._template_store = template_store
        self._template_storage_error = False

    @property
    def template_storage_error(self) -> bool:
        return self._template_storage_error

    def load(self) -> GestureConfiguration:
        try:
            raw = self._settings.read(PORTABLE_GESTURE_SETTING_KEYS)
        except Exception:
            return GestureConfiguration()
        if not isinstance(raw, Mapping):
            return GestureConfiguration()
        configuration = import_gesture_configuration(
            raw.get(GESTURE_CONFIGURATION_KEY)
        )
        if self._template_store is None:
            return configuration
        try:
            templates = self._template_store.load()
        except GestureTemplateStoreError:
            self._template_storage_error = True
            return replace(configuration, enabled=False)
        self._template_storage_error = False
        return merge_protected_templates(configuration, templates)

    def begin_edit(self) -> GestureConfigurationDraft[SnapshotT]:
        current = self.load()
        return GestureConfigurationDraft(self, current, current)

    def save(self, configuration: GestureConfiguration) -> None:
        if not isinstance(configuration, GestureConfiguration):
            raise GestureConfigurationStoreError("Gesture configuration is invalid.")
        if self._template_store is None and any(
            definition.samples for definition in configuration.definitions
        ):
            raise GestureConfigurationStoreError(
                "Protected gesture-template storage is unavailable."
            )
        self._atomic_write(configuration)

    def export_portable(self) -> dict[str, object]:
        return export_gesture_configuration(self.load())

    def import_portable(self, payload: Mapping[str, object]) -> GestureConfiguration:
        try:
            configuration = import_gesture_configuration(payload)
        except (TypeError, ValueError):
            configuration = GestureConfiguration()
        self.save(configuration)
        return configuration

    def snapshot(self) -> GestureConfigurationStoreSnapshot[SnapshotT]:
        """Capture both storage layers without exposing protected content."""

        try:
            settings = self._settings.snapshot(PORTABLE_GESTURE_SETTING_KEYS)
        except Exception:
            raise GestureConfigurationStoreError(
                "Gesture configuration could not be snapshotted."
            ) from None
        protected_templates = None
        if self._template_store is not None:
            try:
                protected_templates = self._template_store.snapshot()
            except GestureTemplateStoreError:
                raise GestureConfigurationStoreError(
                    "Protected gesture templates could not be snapshotted."
                ) from None
        return GestureConfigurationStoreSnapshot(settings, protected_templates)

    def restore(
        self,
        snapshot: GestureConfigurationStoreSnapshot[SnapshotT],
    ) -> None:
        """Restore an exact cross-layer snapshot or report incomplete rollback."""

        if not isinstance(snapshot, GestureConfigurationStoreSnapshot):
            raise GestureConfigurationStoreError(
                "Gesture configuration snapshot is invalid."
            )
        restored = True
        try:
            self._settings.restore(snapshot.settings)
        except Exception:
            restored = False
        if self._template_store is not None:
            protected = snapshot.protected_templates
            if protected is None:
                restored = False
            else:
                try:
                    self._template_store.restore(protected)
                except GestureTemplateStoreError:
                    restored = False
        elif snapshot.protected_templates is not None:
            restored = False
        if not restored:
            raise GestureConfigurationStoreError(
                "Gesture configuration rollback was incomplete."
            )

    def _atomic_write(self, configuration: GestureConfiguration) -> None:
        values = {
            GESTURE_CONFIGURATION_KEY: export_gesture_configuration(configuration)
        }
        before = self.snapshot()
        try:
            self._settings.write(values)
            if self._template_store is not None:
                self._template_store.save(configuration)
        except Exception:
            try:
                self.restore(before)
            except GestureConfigurationStoreError:
                raise GestureConfigurationStoreError(
                    "Gesture configuration save failed and rollback was incomplete."
                ) from None
            raise GestureConfigurationStoreError(
                "Gesture configuration save failed; previous values were restored."
            ) from None
