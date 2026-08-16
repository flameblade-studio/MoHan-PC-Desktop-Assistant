from __future__ import annotations

lazy import re


def _normalize_command(text: str) -> str:
    return re.sub(r"[\s，,。.!！?？、：:「」『』]+", "", text)


def is_start_work_command(text: str) -> bool:
    return _normalize_command(text) in {
        "我開始工作",
        "我開始工作了",
        "開始工作",
        "開始計時",
        "現在開始工作",
        "幫我開始工作",
        "墨寒我開始工作",
        "墨寒開始工作",
    }


def is_stop_work_command(text: str) -> bool:
    return _normalize_command(text) in {
        "我下班",
        "我下班了",
        "我收工",
        "我收工了",
        "結束工作",
        "結束計時",
        "墨寒我下班",
        "墨寒我收工",
    }
