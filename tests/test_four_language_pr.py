from __future__ import annotations

lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

lazy from check_four_language_pr import audit_pull_request

BODY = """## 繁體中文

說明。

- `python tests/run_all.py`

## 简体中文
说明。

- `python tests/run_all.py`

## English

Description.

- `python tests/run_all.py`

## 日本語
説明。

- `python tests/run_all.py`
"""


def test_valid_pull_request_metadata() -> None:
    payload = {
        "pull_request": {
            "title": "修正／修复／Fix／修正",
            "body": BODY,
        }
    }
    assert audit_pull_request(payload) == []


def test_title_requires_exactly_four_nonempty_segments() -> None:
    payload = {"pull_request": {"title": "修正 / Fix", "body": BODY}}
    errors = audit_pull_request(payload)
    assert any("title must contain four" in error for error in errors)


def test_body_requires_fixed_order_and_structural_parity() -> None:
    wrong_order = BODY.replace("## 繁體中文", "## TEMP", 1).replace(
        "## 简体中文", "## 繁體中文", 1
    ).replace("## TEMP", "## 简体中文", 1)
    payload = {
        "pull_request": {
            "title": "修正／修复／Fix／修正",
            "body": wrong_order,
        }
    }
    errors = audit_pull_request(payload)
    assert any("language sections must appear exactly once" in error for error in errors)

    unequal = BODY.replace("- `python tests/run_all.py`", "", 1)
    payload["pull_request"]["body"] = unequal
    errors = audit_pull_request(payload)
    assert any("differs across language sections" in error for error in errors)


def main() -> None:
    test_valid_pull_request_metadata()
    test_title_requires_exactly_four_nonempty_segments()
    test_body_requires_fixed_order_and_structural_parity()
    print("FOUR_LANGUAGE_PR_TESTS_OK")


if __name__ == "__main__":
    main()
