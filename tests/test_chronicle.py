from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.chronicle import Chronicle, MilestoneKind


def test_chronicle_starts_empty() -> None:
    chronicle = Chronicle()
    assert chronicle.milestones == ()
    assert chronicle.recollection("zh-TW", 0) == ""


def test_record_deduplicates_by_kind() -> None:
    chronicle = Chronicle()
    first = chronicle.record(MilestoneKind.FIRST_TESTS_PASSED, 1)
    second = first.record(MilestoneKind.FIRST_TESTS_PASSED, 5)
    assert len(second.milestones) == 1
    assert second.milestones[0].day == 1


def test_recollection_is_four_language() -> None:
    chronicle = Chronicle().record(MilestoneKind.FIRST_TESTS_PASSED, 1)
    assert "綠燈" in chronicle.recollection("zh-TW", 30)
    assert chronicle.recollection("en", 30)
    assert chronicle.recollection("ja-JP", 30)


def test_recollection_uses_latest_milestone() -> None:
    chronicle = (
        Chronicle()
        .record(MilestoneKind.FIRST_TESTS_PASSED, 1)
        .record(MilestoneKind.FIRST_PR_MERGED, 10)
    )
    assert "PR" in chronicle.recollection("zh-TW", 30)


def run() -> None:
    test_chronicle_starts_empty()
    test_record_deduplicates_by_kind()
    test_recollection_is_four_language()
    test_recollection_uses_latest_milestone()
    print("CHRONICLE_OK")


if __name__ == "__main__":
    run()
