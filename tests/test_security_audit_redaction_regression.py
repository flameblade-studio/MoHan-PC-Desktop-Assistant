from __future__ import annotations

lazy import json

lazy from application.flagship_action_runtime import redact_audit_payload


def test_audit_redaction_never_keeps_sensitive_text_previews() -> None:
    password = "p@ssw0rd"
    clipboard_text = "private note"
    nested_secret = "do-not-audit-this"
    payload = {
        "request": {
            "arguments": {
                "password": password,
                "token": {"nested": nested_secret},
                "text": clipboard_text,
            }
        },
        "result": {"data": {"text": [clipboard_text, {"message": nested_secret}]}},
    }

    redacted = redact_audit_payload(payload)
    serialized = json.dumps(redacted, ensure_ascii=False)

    assert password not in serialized
    assert clipboard_text not in serialized
    assert nested_secret not in serialized
    assert redacted["request"]["arguments"]["password"] == "<redacted str (8)>"
    assert redacted["request"]["arguments"]["token"] == "<redacted dict (1)>"
    assert redacted["request"]["arguments"]["text"] == "<redacted str (12)>"
    assert redacted["result"]["data"]["text"] == "<redacted list (2)>"
