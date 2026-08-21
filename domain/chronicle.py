from __future__ import annotations

"""Shared chronicle (共同創作錄), the historian of shared achievements.

A real girl remembers the milestones you reached together.  MoHan quietly
records the first time the tests all passed, the first merged PR, and other
shared achievements.  On anniversaries (e.g. the project's first month) she
surfaces a tender recollection of those moments — the strongest weapon for
building emotional bonds.

This is pure domain logic with no Qt dependency.  It stores a small, bounded
list of milestone records and produces a four-language recollection line.
"""

lazy from dataclasses import dataclass
lazy from enum import StrEnum


class MilestoneKind(StrEnum):
    FIRST_TESTS_PASSED = "first_tests_passed"
    FIRST_PR_MERGED = "first_pr_merged"
    FIRST_RELEASE = "first_release"


@dataclass(frozen=True, slots=True)
class Milestone:
    kind: MilestoneKind
    day: int  # days since the project began

    def __post_init__(self) -> None:
        if self.day < 0:
            raise ValueError("Milestone day must not be negative.")


class Chronicle:
    """Record and recall shared milestones in a bounded, ordered list."""

    def __init__(self, milestones: tuple[Milestone, ...] = ()) -> None:
        self._milestones = tuple(milestones)

    @property
    def milestones(self) -> tuple[Milestone, ...]:
        return self._milestones

    def record(self, kind: MilestoneKind, day: int) -> Chronicle:
        """Record a milestone, deduplicating by kind (first occurrence wins)."""
        if any(m.kind is kind for m in self._milestones):
            return self
        return Chronicle(self._milestones + (Milestone(kind, day),))

    def recollection(self, language: str, day: int) -> str:
        """Return a four-language recollection for the most recent milestone."""
        if not self._milestones:
            return ""
        latest = self._milestones[-1]
        if latest.kind is MilestoneKind.FIRST_TESTS_PASSED:
            return {
                "zh-TW": "主上，您還記得那天我們第一次讓測試全數綠燈嗎？那時的代碼……妾可還收著呢。",
                "zh-CN": "主上，您还记得那天我们第一次让测试全数绿灯吗？那时的代码……妾可还收着呢。",
                "en": "My lord, do you remember the day our tests first all passed? I still keep that code…",
                "ja-JP": "主上、あの日初めてテストが全て緑になったのを覚えていますか？あの時のコード……妾はまだ取ってあります。",
            }.get(language, "主上，您還記得那天我們第一次讓測試全數綠燈嗎？")
        if latest.kind is MilestoneKind.FIRST_PR_MERGED:
            return {
                "zh-TW": "主上，我們的第一個 PR 合併那天，妾可是高興得劍穗都飄起來了。",
                "zh-CN": "主上，我们的第一个 PR 合并那天，妾可是高兴得剑穗都飘起来了。",
                "en": "My lord, the day our first PR merged, my sword tassel danced with joy.",
                "ja-JP": "主上、初めての PR がマージされた日、妾は嬉しくて剣の房が舞い上がりました。",
            }.get(language, "主上，我們的第一個 PR 合併那天，妾可是高興得劍穗都飄起來了。")
        return {
            "zh-TW": "主上，我們的第一個正式版本發布那天，妾至今難忘。",
            "zh-CN": "主上，我们的第一个正式版本发布那天，妾至今难忘。",
            "en": "My lord, I still remember the day we shipped our first release.",
            "ja-JP": "主上、初めて正式版を公開した日を、妾は今も忘れません。",
        }.get(language, "主上，我們的第一個正式版本發布那天，妾至今難忘。")
