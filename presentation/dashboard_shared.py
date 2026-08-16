from __future__ import annotations

lazy from presentation.ui_localization import (
    MEMORY_CATEGORY_LABELS,
    SIMPLIFIED_MEMORY_CATEGORY_LABELS,
    display_label,
)
lazy from presentation.ui_localization_ja import JAPANESE_MEMORY_CATEGORY_LABELS

__all__ = ("MEMORY_CATEGORIES", "TODO_CATEGORIES", "memory_category_label")

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
