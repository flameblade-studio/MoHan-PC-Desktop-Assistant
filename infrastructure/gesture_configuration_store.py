from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, replace
lazy from typing import Final, Self, TypeVar

# Keep these public re-exports concrete after the composition root loads them
# first; Python 3.15rc1 can otherwise expose nested lazy-import proxies.
from domain.gesture_configuration import (
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
    """fixed-detail storage boundary result that keeps backend content private."""


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
            raise GestureConfigurationStoreError("Gesture draft needs a supported value.")
        self.value = configuration
        return self

    def update_definition(self, definition: GestureDefinition) -> Self:
        self._assert_open()
        try:
            self.value = self.value.replace_definition(definition)
        except (KeyError, TypeError, ValueError):
            raise GestureConfigurationStoreError("Gesture draft edit needs a supported value.") from None
        return self

    def set_enabled(self, enabled: bool) -> Self:
        self._assert_open()
        if type(enabled) is not bool:
            raise GestureConfigurationStoreError("Gesture enabled state needs a supported value.")
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
        # 後端讀不到不是「從未保存」：回預設值會讓排程端把已送達的提醒再送一次，
        # 偏好編輯器也會拿預設值開啟、一存就覆蓋掉原有設定。寫入路徑早就拋
        # 型別化錯誤，讀取路徑比照。
            raise GestureConfigurationStoreError(
                "Gesture configuration could not be read."
            ) from None
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
            raise GestureConfigurationStoreError("Gesture configuration needs a supported value.")
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
        """Capture both storage layers while keeping protected content private."""

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
        """Restore an exact cross-layer snapshot or report rollback requiring attention."""

        if not isinstance(snapshot, GestureConfigurationStoreSnapshot):
            raise GestureConfigurationStoreError(
                "Gesture configuration snapshot needs a supported value."
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
                "Gesture configuration rollback requires attention."
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
                    "Gesture configuration save requires attention and rollback requires attention."
                ) from None
            raise GestureConfigurationStoreError(
                "Gesture configuration save requires attention; previous values were restored."
            ) from None
