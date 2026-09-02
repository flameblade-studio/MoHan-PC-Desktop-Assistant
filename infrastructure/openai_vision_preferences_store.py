from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, replace
lazy from typing import Final, Self, TypeVar

lazy from domain.openai_vision_preferences import (
    SETTING_KEYS,
    OpenAIVisionPreferences,
    OpenAIVisionPreferencesError,
    UnsupportedOpenAIVisionPreferencesVersion,
    export_openai_vision_preferences,
    import_openai_vision_preferences,
    preferences_from_mapping,
    settings_payload,
)
lazy from domain.performance_preferences import SettingsPort

STORE_SCHEMA_KEY: Final = "openai_vision_preferences_schema_version"
STORE_SCHEMA_VERSION: Final = 1
PORTABLE_SETTING_KEYS: Final = (*SETTING_KEYS, STORE_SCHEMA_KEY)
_BOUNDARY_ERRORS: Final = (Exception,)

SnapshotT = TypeVar("SnapshotT")


class OpenAIVisionPreferencesStoreError(RuntimeError):
    """A fixed-detail persistence error without backend content."""


@dataclass(slots=True)
class OpenAIVisionPreferencesDraft[SnapshotT]:
    _store: OpenAIVisionPreferencesStore[SnapshotT]
    original: OpenAIVisionPreferences
    value: OpenAIVisionPreferences
    _closed: bool = False

    def update(self, **changes: object) -> Self:
        self._assert_open()
        try:
            self.value = replace(self.value, **changes)
        except (TypeError, ValueError):
            raise OpenAIVisionPreferencesStoreError(
                "OpenAI vision draft is invalid."
            ) from None
        return self

    def commit(self) -> OpenAIVisionPreferences:
        self._assert_open()
        self._store.save(self.value)
        self._closed = True
        return self.value

    def cancel(self) -> OpenAIVisionPreferences:
        self._assert_open()
        self._closed = True
        self.value = self.original
        return self.original

    def _assert_open(self) -> None:
        if self._closed:
            raise OpenAIVisionPreferencesStoreError(
                "OpenAI vision draft is already closed."
            )


class OpenAIVisionPreferencesStore[SnapshotT]:
    def __init__(self, settings: SettingsPort[SnapshotT]) -> None:
        self._settings = settings

    def load(self) -> OpenAIVisionPreferences:
        try:
            raw = self._settings.read(PORTABLE_SETTING_KEYS)
        except _BOUNDARY_ERRORS:
        # 後端讀不到不是「從未保存」：回預設值會讓排程端把已送達的提醒再送一次，
        # 偏好編輯器也會拿預設值開啟、一存就覆蓋掉原有設定。寫入路徑早就拋
        # 型別化錯誤，讀取路徑比照。
            raise OpenAIVisionPreferencesStoreError(
                "OpenAI vision preferences could not be read."
            ) from None
        if not isinstance(raw, Mapping):
            return OpenAIVisionPreferences()
        version = raw.get(STORE_SCHEMA_KEY)
        if version is not None and (
            type(version) is not int or version != STORE_SCHEMA_VERSION
        ):
            return OpenAIVisionPreferences()
        return preferences_from_mapping(
            {
                "enabled": raw.get(SETTING_KEYS[0]),
                "cloud_vision_enabled": raw.get(SETTING_KEYS[1]),
                "model_id": raw.get(SETTING_KEYS[2]),
                "detail": raw.get(SETTING_KEYS[3]),
                "trigger_policy": raw.get(SETTING_KEYS[4]),
                "daily_limit": raw.get(SETTING_KEYS[5]),
                "per_minute_limit": raw.get(SETTING_KEYS[6]),
                "object_semantics_enabled": raw.get(SETTING_KEYS[7]),
                "web_search_suggestions_enabled": raw.get(SETTING_KEYS[8]),
                "raw_image_storage_enabled": raw.get(SETTING_KEYS[9]),
            }
        )

    def begin_edit(self) -> OpenAIVisionPreferencesDraft[SnapshotT]:
        current = self.load()
        return OpenAIVisionPreferencesDraft(self, current, current)

    def save(self, preferences: OpenAIVisionPreferences) -> None:
        if not isinstance(preferences, OpenAIVisionPreferences):
            raise OpenAIVisionPreferencesStoreError(
                "OpenAI vision preferences are invalid."
            )
        values = settings_payload(preferences)
        values[STORE_SCHEMA_KEY] = STORE_SCHEMA_VERSION
        try:
            before = self._settings.snapshot(PORTABLE_SETTING_KEYS)
        except _BOUNDARY_ERRORS:
            raise OpenAIVisionPreferencesStoreError(
                "OpenAI vision preferences could not be snapshotted."
            ) from None
        try:
            self._settings.write(values)
        except _BOUNDARY_ERRORS:
            try:
                self._settings.restore(before)
            except _BOUNDARY_ERRORS:
                raise OpenAIVisionPreferencesStoreError(
                    "OpenAI vision save failed and rollback was incomplete."
                ) from None
            raise OpenAIVisionPreferencesStoreError(
                "OpenAI vision save failed; previous values were restored."
            ) from None

    def export_portable(self) -> dict[str, object]:
        return export_openai_vision_preferences(self.load())

    def import_portable(
        self, payload: Mapping[str, object]
    ) -> OpenAIVisionPreferences:
        try:
            preferences = import_openai_vision_preferences(payload)
        except UnsupportedOpenAIVisionPreferencesVersion:
            raise
        except OpenAIVisionPreferencesError:
            preferences = OpenAIVisionPreferences()
        self.save(preferences)
        return preferences
