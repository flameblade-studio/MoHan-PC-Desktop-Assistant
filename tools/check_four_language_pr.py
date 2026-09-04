from __future__ import annotations

lazy import json
lazy import os
lazy import sys
lazy from pathlib import Path

lazy from check_four_language_docs import audit_text

TITLE_SEPARATOR = "／"
LANGUAGE_COUNT = 4


def _title_errors(title: object) -> list[str]:
    if not isinstance(title, str):
        return ["pull-request title must be a string"]
    parts = tuple(part.strip() for part in title.split(TITLE_SEPARATOR))
    if len(parts) != LANGUAGE_COUNT or any(not part for part in parts):
        return [
            (
                "pull-request title must contain four non-empty translations "
                "separated by ／ in this order: Traditional Chinese, Simplified "
                "Chinese, English, Japanese"
            )
        ]
    return []


def _is_release_please_pull_request(pull_request: dict[str, object]) -> bool:
    head = pull_request.get("head")
    user = pull_request.get("user")
    head_ref = head.get("ref") if isinstance(head, dict) else None
    author = user.get("login") if isinstance(user, dict) else None
    return (
        isinstance(head_ref, str)
        and head_ref.startswith("release-please--branches--")
        and author == "github-actions[bot]"
    )


def _is_release_please_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    pull_request = payload.get("pull_request")
    return isinstance(pull_request, dict) and _is_release_please_pull_request(
        pull_request
    )


def audit_pull_request(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["GitHub event payload must be a JSON object"]
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return ["GitHub event payload is missing pull_request metadata"]

    errors = _title_errors(pull_request.get("title"))
    if _is_release_please_pull_request(pull_request):
        return errors
    body = pull_request.get("body")
    if not isinstance(body, str):
        errors.append("pull-request body must be a string")
        return errors
    errors.extend(f"pull-request body: {error}" for error in audit_text(body))
    return errors


def main() -> int:
    event_value = os.environ.get("GITHUB_EVENT_PATH")
    if not event_value:
        print("FAIL: GITHUB_EVENT_PATH is not set", file=sys.stderr)
        return 2

    event_path = Path(event_value)
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"FAIL: cannot read GitHub event payload: {error}", file=sys.stderr)
        return 2

    errors = audit_pull_request(payload)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if _is_release_please_payload(payload):
        print("RELEASE_PLEASE_BODY_EXEMPT")
    else:
        print("FOUR_LANGUAGE_PR_METADATA_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
