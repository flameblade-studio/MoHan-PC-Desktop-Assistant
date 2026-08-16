from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from theme_session import (
    ACTIVE_THEME_SETTING_KEY,
    BUILTIN_THEME_ID,
    ThemeResolution,
    ThemeSession,
    ThemeSessionError,
)


class Harness:
    def __init__(self) -> None:
        self.available = {
            BUILTIN_THEME_ID: "built-in-style",
            "moonlit-blue": "moonlit-style",
            "plum-blossom": "plum-style",
        }
        self.visual = "built-in-style"
        self.committed: list[str] = []
        self.fail_preview_for: set[str] = set()
        self.fail_commit = False

    def resolve(self, theme_id: str) -> ThemeResolution:
        if theme_id not in self.available:
            return ThemeResolution(
                requested_id=theme_id,
                resolved_id=BUILTIN_THEME_ID,
                payload=self.available[BUILTIN_THEME_ID],
                status="missing",
            )
        return ThemeResolution(
            requested_id=theme_id,
            resolved_id=theme_id,
            payload=self.available[theme_id],
            status="ready",
        )

    def preview(self, resolution: ThemeResolution) -> None:
        if resolution.resolved_id in self.fail_preview_for:
            raise RuntimeError("test-only preview failure")
        self.visual = str(resolution.payload)

    def commit(self, theme_id: str) -> None:
        if self.fail_commit:
            raise RuntimeError("test-only commit failure")
        self.committed.append(theme_id)


def _session(harness: Harness, persisted: str = BUILTIN_THEME_ID) -> ThemeSession:
    return ThemeSession(
        persisted,
        resolve=harness.resolve,
        preview=harness.preview,
        commit=harness.commit,
    )


def test_preview_cancel_and_save_are_explicit() -> None:
    assert ACTIVE_THEME_SETTING_KEY == "active_theme_id"
    assert ThemeSession.setting_key == ACTIVE_THEME_SETTING_KEY
    harness = Harness()
    session = _session(harness)

    result = session.preview("moonlit-blue")
    assert result.status == "ready"
    assert harness.visual == "moonlit-style"
    assert session.has_unsaved_preview
    assert harness.committed == []

    session.cancel()
    assert harness.visual == "built-in-style"
    assert not session.has_unsaved_preview

    session.preview("plum-blossom")
    commit = session.save()
    assert commit.previous_id == BUILTIN_THEME_ID
    assert commit.theme_id == "plum-blossom"
    assert harness.committed == ["plum-blossom"]
    assert not session.has_unsaved_preview


def test_missing_theme_falls_back_explicitly() -> None:
    harness = Harness()
    session = _session(harness, "removed-theme")
    assert session.persisted_theme_id == BUILTIN_THEME_ID
    assert session.last_resolution.status == "missing"
    assert session.last_resolution.requested_id == "removed-theme"


def test_failed_preview_restores_last_good_visual() -> None:
    harness = Harness()
    session = _session(harness)
    session.preview("moonlit-blue")
    harness.fail_preview_for.add("plum-blossom")

    try:
        session.preview("plum-blossom")
    except ThemeSessionError:
        pass
    else:
        raise AssertionError("a failed preview must be reported")
    assert harness.visual == "moonlit-style"
    assert session.preview_theme_id == "moonlit-blue"


def test_failed_save_does_not_change_persisted_state() -> None:
    harness = Harness()
    session = _session(harness)
    session.preview("moonlit-blue")
    harness.fail_commit = True
    try:
        session.save()
    except ThemeSessionError:
        pass
    else:
        raise AssertionError("a failed commit must be reported")
    assert session.persisted_theme_id == BUILTIN_THEME_ID
    assert session.preview_theme_id == "moonlit-blue"


def test_removal_guard_covers_builtin_active_and_preview() -> None:
    harness = Harness()
    session = _session(harness, "moonlit-blue")
    assert session.removal_block(BUILTIN_THEME_ID) == "builtin"
    assert session.removal_block("moonlit-blue") == "active"
    session.preview("plum-blossom")
    assert session.removal_block("plum-blossom") == "preview"
    assert session.removal_block("unused-theme") is None


if __name__ == "__main__":
    test_preview_cancel_and_save_are_explicit()
    test_missing_theme_falls_back_explicitly()
    test_failed_preview_restores_last_good_visual()
    test_failed_save_does_not_change_persisted_state()
    test_removal_guard_covers_builtin_active_and_preview()
    print("THEME_SESSION_OK")
