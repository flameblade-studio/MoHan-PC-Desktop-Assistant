from __future__ import annotations

lazy import sys
lazy from pathlib import Path

lazy from PySide6.QtWidgets import QFrame

lazy from presentation.ui_localization import (
    MEMORY_CATEGORY_LABELS,
    SIMPLIFIED_MEMORY_CATEGORY_LABELS,
    display_label,
)
lazy from presentation.ui_localization_ja import JAPANESE_MEMORY_CATEGORY_LABELS

__all__ = (
    "MEMORY_CATEGORIES",
    "TODO_CATEGORIES",
    "mark_flagship_card",
    "memory_category_label",
    "resource_path",
)

RESOURCE_BASE = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])
)

MEMORY_CATEGORIES = (
    "人物",
    "偏好",
    "目標",
    "工作流程",
    "重要日期",
    "其他",
)

TODO_CATEGORIES = (
    ("漫畫", "todo_category_comic"),
    ("文章", "todo_category_article"),
    ("音樂", "todo_category_music"),
    ("貼圖", "todo_category_stickers"),
    ("出版", "todo_category_publishing"),
    ("行政", "todo_category_administration"),
    ("其他", "todo_category_other"),
)


def memory_category_label(language: str, value: str) -> str:
    return display_label(
        language,
        value,
        MEMORY_CATEGORY_LABELS,
        SIMPLIFIED_MEMORY_CATEGORY_LABELS,
        JAPANESE_MEMORY_CATEGORY_LABELS,
    )


def mark_flagship_card(frame: QFrame) -> None:
    """Opt a semantic section frame into the product theme's card styling."""

    frame.setProperty("mohanRole", "card")
    frame.style().unpolish(frame)
    frame.style().polish(frame)


def resource_path(relative: str) -> Path:
    """Resolve one packaged resource without selecting product-owned content."""

    return RESOURCE_BASE / relative
