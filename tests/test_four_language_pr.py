from __future__ import annotations

lazy import json
lazy import os
lazy import sys
lazy import tempfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

lazy from check_four_language_pr import audit_pull_request
lazy from check_four_language_pr import main as check_pr_main

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


def _run_main_with_payload(payload: dict) -> int:
    with tempfile.TemporaryDirectory(prefix="mohan-four-language-pr-") as raw:
        event_path = Path(raw) / "event.json"
        event_path.write_text(json.dumps(payload), encoding="utf-8")
        previous = os.environ.get("GITHUB_EVENT_PATH")
        os.environ["GITHUB_EVENT_PATH"] = str(event_path)
        try:
            return check_pr_main()
        finally:
            if previous is None:
                os.environ.pop("GITHUB_EVENT_PATH", None)
            else:
                os.environ["GITHUB_EVENT_PATH"] = previous


def test_release_please_body_exemption_requires_bot_author_and_four_language_title() -> None:
    payload = {
        "pull_request": {
            "title": "single-language title",
            "body": "single-language body",
            "head": {"ref": "release-please--branches--main"},
            "user": {"login": "impostor"},
        }
    }
    # A human-authored PR must not bypass governance via the branch name.
    assert _run_main_with_payload(payload) == 1

    payload["pull_request"]["user"]["login"] = "github-actions[bot]"
    # The release bot may skip the machine-generated body, but its title still
    # has to satisfy the four-language contract.
    assert _run_main_with_payload(payload) == 1

    payload["pull_request"]["title"] = "發版 4.5.1／发版 4.5.1／Release 4.5.1／リリース 4.5.1"
    assert _run_main_with_payload(payload) == 0

    payload["pull_request"]["head"]["ref"] = "feature/normal-branch"
    assert _run_main_with_payload(payload) == 1


def main() -> None:
    test_valid_pull_request_metadata()
    test_title_requires_exactly_four_nonempty_segments()
    test_body_requires_fixed_order_and_structural_parity()
    test_release_please_body_exemption_requires_bot_author_and_four_language_title()
    print("FOUR_LANGUAGE_PR_TESTS_OK")


if __name__ == "__main__":
    main()
