from __future__ import annotations

lazy import ast
lazy import sys
lazy from dataclasses import FrozenInstanceError, dataclass
lazy from datetime import datetime, timedelta, timezone
lazy from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

lazy import pytest

lazy from domain.flagship_safe_intent import FlagshipSafeIntentService

_MODULE_PATH = _ROOT / "domain" / "flagship_safe_intent.py"
_FIXED_NOW = datetime(
    2026,
    8,
    14,
    15,
    30,
    45,
    tzinfo=timezone(timedelta(hours=8)),
)
_TRANSLATIONS = frozendict({
    "zh-TW": frozendict({}),
    "zh-CN": frozendict({
        "讀取 Gmail 郵件": "读取 Gmail 邮件",
        "讀取最近 {days} 天內最多 {limit} 封 Gmail 郵件": (
            "读取最近 {days} 天内最多 {limit} 封 Gmail 邮件"
        ),
        "讀取 Google Calendar": "读取 Google Calendar",
        "讀取 Google Calendar 未來 {days} 天行程": (
            "读取 Google Calendar 未来 {days} 天的日程"
        ),
        "讀取 Google Drive": "读取 Google Drive",
        "搜尋 Google Drive 檔案：{name}": "搜索 Google Drive 文件：{name}",
        "列出 Google Drive 最近修改的檔案": "列出 Google Drive 最近修改的文件",
    }),
    "en": frozendict({
        "讀取 Gmail 郵件": "Read Gmail messages",
        "讀取最近 {days} 天內最多 {limit} 封 Gmail 郵件": (
            "Read up to {limit} Gmail messages from the last {days} days"
        ),
        "讀取 Google Calendar": "Read Google Calendar",
        "讀取 Google Calendar 未來 {days} 天行程": (
            "Read Google Calendar events for the next {days} days"
        ),
        "讀取 Google Drive": "Read Google Drive",
        "搜尋 Google Drive 檔案：{name}": "Search Google Drive files: {name}",
        "列出 Google Drive 最近修改的檔案": (
            "List recently modified Google Drive files"
        ),
    }),
    "ja-JP": frozendict({
        "讀取 Gmail 郵件": "Gmail メールを読み取る",
        "讀取最近 {days} 天內最多 {limit} 封 Gmail 郵件": (
            "過去 {days} 日間の Gmail メールを最大 {limit} 件読み取る"
        ),
        "讀取 Google Calendar": "Google Calendar を読み取る",
        "讀取 Google Calendar 未來 {days} 天行程": (
            "Google Calendar の今後 {days} 日間の予定を読み取る"
        ),
        "讀取 Google Drive": "Google Drive を読み取る",
        "搜尋 Google Drive 檔案：{name}": (
            "Google Drive のファイルを検索：{name}"
        ),
        "列出 Google Drive 最近修改的檔案": (
            "Google Drive で最近変更されたファイルを一覧表示"
        ),
    }),
})


@dataclass(frozen=True, slots=True)
class _Translator:
    language: str

    def __call__(self, source: str, /, **values: object) -> str:
        template = _TRANSLATIONS[self.language].get(source, source)
        return template.format_map(values) if values else template


def _clock() -> datetime:
    return _FIXED_NOW


def _service(language: str = "zh-TW") -> FlagshipSafeIntentService:
    return FlagshipSafeIntentService(
        translate=_Translator(language),
        clock=_clock,
    )


def test_module_uses_python315_lazy_standard_library_imports_only() -> None:
    tree = ast.parse(
        _MODULE_PATH.read_text(encoding="utf-8"),
        filename=str(_MODULE_PATH),
    )
    imports = tuple(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    )
    imported_roots = {
        *(alias.name.partition(".")[0] for alias in node.names)
        for node in imports
        if isinstance(node, ast.Import)
    }
    imported_roots.update(
        node.module.partition(".")[0]
        for node in imports
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported_roots <= {
        "__future__",
        "dataclasses",
        "datetime",
        "re",
        "typing",
    }
    assert all(
        node.module == "__future__" or getattr(node, "is_lazy", False)
        for node in imports
        if isinstance(node, ast.ImportFrom)
    )
    assert all(
        getattr(node, "is_lazy", False)
        for node in imports
        if isinstance(node, ast.Import)
    )


def test_service_and_plans_are_typed_immutable_legacy_compatible() -> None:
    service = _service()
    plan = service.known_safe_plan(
        "請幫我讀取最近七天最多三封 Gmail 郵件"
    )
    assert plan is not None
    assert plan.to_payload() == {
        "title": "讀取 Gmail 郵件",
        "steps": [
            {
                "capability": "email_read",
                "description": "讀取最近 7 天內最多 3 封 Gmail 郵件",
                "arguments": {
                    "provider": "google",
                    "query": "newer_than:7d",
                    "limit": 3,
                },
            }
        ],
    }
    with pytest.raises(FrozenInstanceError):
        plan.title = "mutated"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        service.clock = datetime.now  # type: ignore[misc]
    with pytest.raises(TypeError):
        plan.steps[0].arguments["limit"] = 99  # type: ignore[index]
    payload = plan.to_payload()
    payload["title"] = "mutated copy"
    assert plan.title == "讀取 Gmail 郵件"


@pytest.mark.parametrize(
    ("instruction", "expected"),
    (
        ("沒有日期", 7),
        ("最近一天", 1),
        ("最近三日", 3),
        ("最近兩週", 14),
        ("最近一個月", 30),
        ("最近 42 天", 42),
        ("最近 0 日", 1),
        ("最近 999 天", 365),
    ),
)
def test_gmail_day_parsing_matches_existing_rules(
    instruction: str,
    expected: int,
) -> None:
    assert FlagshipSafeIntentService.gmail_days(instruction) == expected


@pytest.mark.parametrize(
    ("instruction", "expected"),
    (
        ("沒有數量", 3),
        ("一封", 1),
        ("兩封", 2),
        ("十封", 10),
        ("最近 27 封", 27),
        ("前 0 封", 1),
        ("最近 999 封", 100),
    ),
)
def test_gmail_limit_parsing_matches_existing_rules(
    instruction: str,
    expected: int,
) -> None:
    assert FlagshipSafeIntentService.gmail_limit(instruction) == expected


def test_gmail_read_only_plan_and_write_rejection() -> None:
    service = _service()
    plan = service.known_safe_plan("請幫我讀取最近 12 天最多 5 封 GMAIL 郵件")
    assert plan is not None
    assert plan.steps[0].capability == "email_read"
    assert plan.steps[0].arguments == {
        "provider": "google",
        "query": "newer_than:12d",
        "limit": 5,
    }
    for instruction in (
        "請幫我寄信到 Gmail",
        "請幫我寄出 Gmail 郵件",
        "請幫我發信到 Gmail",
        "請幫我傳送郵件到 Gmail",
    ):
        assert service.known_safe_plan(instruction) is None


@pytest.mark.parametrize(
    ("instruction", "expected_start", "expected_end"),
    (
        (
            "請查詢 Google Calendar",
            "2026-08-14T00:00:00+08:00",
            "2026-08-21T00:00:00+08:00",
        ),
        (
            "請幫我查看今天 Google Calendar",
            "2026-08-14T00:00:00+08:00",
            "2026-08-15T00:00:00+08:00",
        ),
        (
            "請幫我查看明天 Google Calendar",
            "2026-08-15T00:00:00+08:00",
            "2026-08-16T00:00:00+08:00",
        ),
    ),
)
def test_calendar_read_only_date_ranges(
    instruction: str,
    expected_start: str,
    expected_end: str,
) -> None:
    plan = _service().known_safe_plan(instruction)
    assert plan is not None
    step = plan.steps[0]
    assert step.capability == "calendar_read"
    assert step.arguments == {
        "provider": "google",
        "start": expected_start,
        "end": expected_end,
    }


@pytest.mark.parametrize("write_marker", ("建立", "新增", "加入", "取消", "刪除"))
def test_calendar_write_requests_are_rejected(write_marker: str) -> None:
    instruction = f"請把{write_marker} Google Calendar 行程"
    assert _service().known_safe_plan(instruction) is None


@pytest.mark.parametrize(
    ("instruction", "expected_name"),
    (
        ("請讀取 Google Drive", ""),
        ("幫我搜尋 Google Drive「會議記錄」", "會議記錄"),
        ("請幫我找 Google Drive『報告草稿』", "報告草稿"),
        ('請幫我找 Google Drive "notes.md"', "notes.md"),
    ),
)
def test_drive_read_only_and_quoted_name_parsing(
    instruction: str,
    expected_name: str,
) -> None:
    plan = _service().known_safe_plan(instruction)
    assert plan is not None
    step = plan.steps[0]
    assert step.capability == "cloud_file_read"
    assert step.arguments == {
        "provider": "google",
        "name": expected_name,
        "limit": 20,
    }


@pytest.mark.parametrize("write_marker", ("上傳", "寫入", "修改", "刪除", "移動"))
def test_drive_write_requests_are_rejected(write_marker: str) -> None:
    instruction = f"請把{write_marker} Google Drive 檔案"
    assert _service().known_safe_plan(instruction) is None


@pytest.mark.parametrize(
    ("language", "expected"),
    (
        (
            "zh-TW",
            (
                "讀取 Gmail 郵件",
                "讀取最近 7 天內最多 3 封 Gmail 郵件",
                "讀取 Google Calendar",
                "讀取 Google Calendar 未來 1 天行程",
                "讀取 Google Drive",
                "搜尋 Google Drive 檔案：會議記錄",
                "列出 Google Drive 最近修改的檔案",
            ),
        ),
        (
            "zh-CN",
            (
                "读取 Gmail 邮件",
                "读取最近 7 天内最多 3 封 Gmail 邮件",
                "读取 Google Calendar",
                "读取 Google Calendar 未来 1 天的日程",
                "读取 Google Drive",
                "搜索 Google Drive 文件：會議記錄",
                "列出 Google Drive 最近修改的文件",
            ),
        ),
        (
            "en",
            (
                "Read Gmail messages",
                "Read up to 3 Gmail messages from the last 7 days",
                "Read Google Calendar",
                "Read Google Calendar events for the next 1 days",
                "Read Google Drive",
                "Search Google Drive files: 會議記錄",
                "List recently modified Google Drive files",
            ),
        ),
        (
            "ja-JP",
            (
                "Gmail メールを読み取る",
                "過去 7 日間の Gmail メールを最大 3 件読み取る",
                "Google Calendar を読み取る",
                "Google Calendar の今後 1 日間の予定を読み取る",
                "Google Drive を読み取る",
                "Google Drive のファイルを検索：會議記錄",
                "Google Drive で最近変更されたファイルを一覧表示",
            ),
        ),
    ),
)
def test_four_language_plan_output(
    language: str,
    expected: tuple[str, str, str, str, str, str, str],
) -> None:
    service = _service(language)
    gmail = service.known_safe_plan("請讀取最近 7 天內最多 3 封 Gmail 郵件")
    calendar = service.known_safe_plan("請讀取今天 Google Calendar")
    drive = service.known_safe_plan("請幫我找 Google Drive「會議記錄」")
    drive_list = service.known_safe_plan("請列出 Google Drive")
    assert gmail is not None
    assert calendar is not None
    assert drive is not None
    assert drive_list is not None
    assert (
        gmail.title,
        gmail.steps[0].description,
        calendar.title,
        calendar.steps[0].description,
        drive.title,
        drive.steps[0].description,
        drive_list.steps[0].description,
    ) == expected


def test_known_safe_priority_and_non_requests_match_existing_behavior() -> None:
    service = _service()
    assert service.contains_any("請幫我查詢 Gmail", ("查看", "查詢"))
    assert not service.contains_any("請幫我查詢 Gmail", ("建立", "刪除"))
    assert service.known_safe_plan("Gmail") is None
    mixed = service.known_safe_plan(
        "請查詢 Gmail、Google Calendar 與 Google Drive"
    )
    assert mixed is not None
    assert mixed.steps[0].capability == "email_read"
