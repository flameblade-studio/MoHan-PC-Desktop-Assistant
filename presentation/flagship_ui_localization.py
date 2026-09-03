"""Strict four-language localization boundary for the flagship control center."""

from __future__ import annotations

lazy import re
lazy from dataclasses import dataclass
lazy from typing import Any

lazy from domain.language_support import canonical_ui_language
lazy from presentation.flagship.localization_catalog import (
    merge_translation_catalogs,
)
lazy from presentation.flagship.localization_cloud_home import (
    CLOUD_HOME_TRANSLATIONS,
)
lazy from presentation.flagship.localization_interaction import (
    INTERACTION_TRANSLATIONS,
)
lazy from presentation.flagship.localization_remote_vision import (
    REMOTE_VISION_TRANSLATIONS,
)
lazy from presentation.flagship.localization_security_audit import (
    SECURITY_AUDIT_TRANSLATIONS,
)
lazy from presentation.flagship.localization_themes import THEME_TRANSLATIONS
lazy from presentation.flagship.localization_workflows import (
    WORKFLOW_TRANSLATIONS,
)

_TRANSLATION_INDEX = frozendict({"zh-CN": 0, "en": 1, "ja-JP": 2})

# Traditional Chinese remains the canonical source and public default. Keeping
# one ordered merged catalog preserves the legacy API while each responsibility
# has an independently maintainable owner.
FLAGSHIP_TRANSLATIONS = merge_translation_catalogs(
    INTERACTION_TRANSLATIONS,
    WORKFLOW_TRANSLATIONS,
    CLOUD_HOME_TRANSLATIONS,
    REMOTE_VISION_TRANSLATIONS,
    SECURITY_AUDIT_TRANSLATIONS,
    THEME_TRANSLATIONS,
)

_SYSTEM_PATTERNS = (
    (r"^安全政策已阻擋：(?P<reason>.*)$", "安全政策已阻擋：{reason}"),
    (r"^工具執行失敗：(?P<detail>.*)$", "工具執行失敗：{detail}"),
    (r"^已開啟資料夾：(?P<value>.*)$", "已開啟資料夾：{value}"),
    (r"^已啟動：(?P<value>.*)$", "已啟動：{value}"),
    (r"^已建立檔案：(?P<value>.*)$", "已建立檔案：{value}"),
    (r"^找到 (?P<count>\d+) 個符合項目$", "找到 {count} 個符合項目"),
    (r"^已移動至：(?P<value>.*)$", "已移動至：{value}"),
    (r"^目前有 (?P<count>\d+) 個可見視窗$", "目前有 {count} 個可見視窗"),
    (r"^已切換至：(?P<value>.*)$", "已切換至：{value}"),
    (r"^已執行 (?P<value>.*)$", "已執行 {value}"),
)

_VISION_AUTHORIZATION_SUMMARY = (
    "公開版預設關閉。明確啟用並全域保存後即持續授權，直到你主動關閉；"
    "系統不會逐幀詢問，狀態始終可見，並可設定配額與成本上限或立即撤銷。"
    "本機 OpenCV 不受此設定影響。"
)
_VISION_AUTHORIZATION_DETAILS = (
    "明確啟用並全域保存後，雲端視覺會依所選事件與用量限制持續運作，直到你主動關閉；"
    "系統不會逐幀詢問，狀態始終可見，並可設定配額與成本上限或立即撤銷。"
    "原始影像不保存，也不會自動上網。"
)


def _current_source(source: str) -> str:
    """Map retired UI copy to the current catalog without changing behavior."""

    if source.startswith("公開版預設關閉。") and source.endswith(
        "本機 OpenCV 不受此設定影響。"
    ):
        return _VISION_AUTHORIZATION_SUMMARY
    if source.startswith("啟用並保存後會依所選事件與用量限制持續運作"):
        return _VISION_AUTHORIZATION_DETAILS
    return source


@dataclass(frozen=True, slots=True)
class FlagshipTranslator:
    """Translate flagship UI text while preserving runtime-provided values."""

    language: str = "zh-TW"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "language",
            canonical_ui_language(self.language),
        )

    def text(self, source: str, /, **values: Any) -> str:
        current_source = _current_source(source)
        template = current_source
        if self.language != "zh-TW":
            try:
                template = FLAGSHIP_TRANSLATIONS[current_source][
                    _TRANSLATION_INDEX[self.language]
                ]
            except KeyError as exc:
                raise KeyError(
                    f"Missing flagship translation for {current_source!r} in {self.language}"
                ) from exc
        return template.format_map(values) if values else template

    def system_message(self, message: str) -> str:
        """Translate known system prose while preserving data and error detail."""

        value = str(message)
        if self.language == "zh-TW":
            return value
        if value in FLAGSHIP_TRANSLATIONS:
            return self.text(value)
        for pattern, source in _SYSTEM_PATTERNS:
            match = re.fullmatch(pattern, value)
            if match is None:
                continue
            fields = match.groupdict()
            if "reason" in fields:
                fields["reason"] = self.system_message(fields["reason"])
            return self.text(source, **fields)
        return value

    def home_issue(self, message: str) -> str:
        """Translate Home Assistant status prose without touching entity data."""

        value = str(message)
        if self.language == "zh-TW":
            return value
        if " 電量只剩 " in value:
            name, remaining = value.rsplit(" 電量只剩 ", 1)
            return self.text(
                "{name} 電量只剩 {value}",
                name=name,
                value=remaining,
            )
        if " 目前" in value:
            name, state = value.rsplit(" 目前", 1)
            return self.text("{name} 目前{state}", name=name, state=state)
        return value


def validate_flagship_translations() -> None:
    """Fail fast when any catalog row is incomplete or blank."""

    for source, translations in FLAGSHIP_TRANSLATIONS.items():
        if not source or len(translations) != len(_TRANSLATION_INDEX):
            raise ValueError(f"Invalid flagship translation row: {source!r}")
        if any(not value.strip() for value in translations):
            raise ValueError(f"Blank flagship translation: {source!r}")


validate_flagship_translations()

__all__ = (
    "FLAGSHIP_TRANSLATIONS",
    "FlagshipTranslator",
    "validate_flagship_translations",
)
