from __future__ import annotations

lazy import re
lazy from dataclasses import dataclass
lazy from datetime import UTC, datetime, timedelta
lazy from typing import Final, Literal, Protocol

type SafeIntentCapability = Literal[
    "email_read",
    "calendar_read",
    "cloud_file_read",
]
type SafeIntentArgument = str | int

_READ_INTENT_MARKERS: Final = (
    "讀取",
    "查看",
    "搜尋",
    "查詢",
    "查找",
    "尋找",
    "找出",
    "列出",
    "整理",
    "顯示",
    "檢查",
    "測試",
    "瀏覽",
    "取得",
)
_ASSIST_INTENT_MARKERS: Final = ("幫我", "請", "替我", "執行")
_GMAIL_MARKERS: Final = ("gmail", "郵件", "電子郵件", "信件", "信箱")
_GMAIL_SEND_MARKERS: Final = ("寄信", "寄出", "發信", "傳送郵件")
_GMAIL_SEND_NEGATIONS: Final = ("不要寄", "不用寄", "不寄出", "不要傳送")
_CALENDAR_MARKERS: Final = (
    "google calendar",
    "googlecalendar",
    "calendar",
    "日曆",
    "行事曆",
    "行程",
)
_CALENDAR_WRITE_MARKERS: Final = ("建立", "新增", "加入", "取消", "刪除")
_DRIVE_MARKERS: Final = (
    "google drive",
    "googledrive",
    "雲端硬碟",
    "雲端檔案",
)
_DRIVE_WRITE_MARKERS: Final = ("上傳", "寫入", "修改", "刪除", "移動")
_CHINESE_DAY_COUNTS: Final = frozendict({
    "一天": 1,
    "一日": 1,
    "三天": 3,
    "三日": 3,
    "七天": 7,
    "七日": 7,
    "一週": 7,
    "一周": 7,
    "兩週": 14,
    "兩周": 14,
    "一個月": 30,
})
_CHINESE_MAIL_COUNTS: Final = frozendict({
    "一封": 1,
    "兩封": 2,
    "三封": 3,
    "五封": 5,
    "十封": 10,
})
_SAFE_CAPABILITIES: Final = frozenset({
    "email_read",
    "calendar_read",
    "cloud_file_read",
})


class SafeIntentTranslator(Protocol):
    """Translate one canonical source string without owning localization data."""

    def __call__(self, source: str, /, **values: object) -> str: ...


class LocalAwareClock(Protocol):
    """Return the current local time with an explicit UTC offset."""

    def __call__(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class SafeIntentStep:
    """One immutable, read-only action in a deterministic local plan."""

    capability: SafeIntentCapability
    description: str
    arguments: frozendict[str, SafeIntentArgument]

    def __post_init__(self) -> None:
        if self.capability not in _SAFE_CAPABILITIES:
            raise ValueError("Safe intent capability must be read-only.")
        if not self.description.strip():
            raise ValueError("Safe intent description must not be empty.")
        if not isinstance(self.arguments, frozendict):
            raise TypeError("Safe intent arguments must be immutable.")

    def to_payload(self) -> dict[str, object]:
        """Return a fresh legacy-compatible payload for the presentation adapter."""

        return {
            "capability": self.capability,
            "description": self.description,
            "arguments": dict(self.arguments),
        }


@dataclass(frozen=True, slots=True)
class SafeIntentPlan:
    """An immutable plan accepted by the established flagship planner flow."""

    title: str
    steps: tuple[SafeIntentStep, ...]

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Safe intent title must not be empty.")
        if len(self.steps) != 1:
            raise ValueError("A known safe intent must contain exactly one step.")

    def to_payload(self) -> dict[str, object]:
        """Return a fresh payload with the exact established dictionary shape."""

        return {
            "title": self.title,
            "steps": [step.to_payload() for step in self.steps],
        }


def _source_text(source: str, /, **values: object) -> str:
    return source.format_map(values) if values else source


def _local_aware_time() -> datetime:
    return datetime.now(UTC).astimezone()


@dataclass(frozen=True, slots=True)
class FlagshipSafeIntentService:
    """Build deterministic read-only Google plans without UI or I/O dependencies."""

    translate: SafeIntentTranslator = _source_text
    clock: LocalAwareClock = _local_aware_time

    def __post_init__(self) -> None:
        if not callable(self.translate):
            raise TypeError("Safe intent translator must be callable.")
        if not callable(self.clock):
            raise TypeError("Safe intent clock must be callable.")

    @staticmethod
    def contains_any(text: str, markers: tuple[str, ...]) -> bool:
        return any(marker in text for marker in markers)

    @staticmethod
    def gmail_days(instruction: str) -> int:
        days = next(
            (
                value
                for marker, value in _CHINESE_DAY_COUNTS.items()
                if marker in instruction
            ),
            7,
        )
        numeric = re.search(
            r"最近\s*(\d{1,3})\s*(?:天|日)",
            instruction,
        )
        if numeric:
            return max(1, min(365, int(numeric.group(1))))
        return days

    @staticmethod
    def gmail_limit(instruction: str) -> int:
        limit = next(
            (
                value
                for marker, value in _CHINESE_MAIL_COUNTS.items()
                if marker in instruction
            ),
            3,
        )
        numeric = re.search(
            r"(?:最多|前|最近)?\s*(\d{1,3})\s*封",
            instruction,
        )
        if numeric:
            return max(1, min(100, int(numeric.group(1))))
        return limit

    def gmail_plan(
        self,
        normalized: str,
        folded: str,
        read_requested: bool,
    ) -> SafeIntentPlan | None:
        mentions_mail = self.contains_any(folded, _GMAIL_MARKERS)
        send_requested = self.contains_any(
            normalized,
            _GMAIL_SEND_MARKERS,
        ) and not self.contains_any(
            normalized,
            _GMAIL_SEND_NEGATIONS,
        )
        assisted = self.contains_any(normalized, _ASSIST_INTENT_MARKERS)
        if not mentions_mail or send_requested or not (read_requested or assisted):
            return None
        days = self.gmail_days(normalized)
        limit = self.gmail_limit(normalized)
        return SafeIntentPlan(
            title=self.translate("讀取 Gmail 郵件"),
            steps=(
                SafeIntentStep(
                    capability="email_read",
                    description=self.translate(
                        "讀取最近 {days} 天內最多 {limit} 封 Gmail 郵件",
                        days=days,
                        limit=limit,
                    ),
                    arguments=frozendict({
                        "provider": "google",
                        "query": f"newer_than:{days}d",
                        "limit": limit,
                    }),
                ),
            ),
        )

    def calendar_plan(
        self,
        normalized: str,
        folded: str,
        read_requested: bool,
    ) -> SafeIntentPlan | None:
        assisted = self.contains_any(normalized, _ASSIST_INTENT_MARKERS)
        if (
            not self.contains_any(folded, _CALENDAR_MARKERS)
            or not (read_requested or assisted)
            or self.contains_any(normalized, _CALENDAR_WRITE_MARKERS)
        ):
            return None
        start = self.clock().replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        days = 7
        if "明天" in normalized:
            start += timedelta(days=1)
            days = 1
        elif "今天" in normalized or "今日" in normalized:
            days = 1
        end = start + timedelta(days=days)
        return SafeIntentPlan(
            title=self.translate("讀取 Google Calendar"),
            steps=(
                SafeIntentStep(
                    capability="calendar_read",
                    description=self.translate(
                        "讀取 Google Calendar 未來 {days} 天行程",
                        days=days,
                    ),
                    arguments=frozendict({
                        "provider": "google",
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                    }),
                ),
            ),
        )

    def drive_plan(
        self,
        normalized: str,
        folded: str,
        read_requested: bool,
    ) -> SafeIntentPlan | None:
        assisted = self.contains_any(normalized, _ASSIST_INTENT_MARKERS)
        if (
            not self.contains_any(folded, _DRIVE_MARKERS)
            or not (read_requested or assisted)
            or self.contains_any(normalized, _DRIVE_WRITE_MARKERS)
        ):
            return None
        quoted = re.search(
            r'[「『"]([^」』"]+)[」』"]',
            normalized,
        )
        name = quoted.group(1).strip() if quoted else ""
        description = (
            self.translate("搜尋 Google Drive 檔案：{name}", name=name)
            if name
            else self.translate("列出 Google Drive 最近修改的檔案")
        )
        return SafeIntentPlan(
            title=self.translate("讀取 Google Drive"),
            steps=(
                SafeIntentStep(
                    capability="cloud_file_read",
                    description=description,
                    arguments=frozendict({
                        "provider": "google",
                        "name": name,
                        "limit": 20,
                    }),
                ),
            ),
        )

    def known_safe_plan(self, instruction: str) -> SafeIntentPlan | None:
        """Return a deterministic plan for an established read-only request."""

        normalized = str(instruction).strip()
        folded = normalized.casefold()
        read_requested = self.contains_any(normalized, _READ_INTENT_MARKERS)
        return (
            self.gmail_plan(normalized, folded, read_requested)
            or self.calendar_plan(normalized, folded, read_requested)
            or self.drive_plan(normalized, folded, read_requested)
        )
