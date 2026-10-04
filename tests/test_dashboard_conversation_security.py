from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from presentation import dashboard_conversation
lazy from presentation.dashboard_conversation import DashboardConversationMixin


def test_chat_speaker_is_rendered_as_plain_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ScrollBar:
        def maximum(self) -> int:
            return 10

        def setValue(self, _value: int) -> None:
            pass

    class _Chat:
        def __init__(self) -> None:
            self.html = ""
            self.scroll_bar = _ScrollBar()

        def append(self, value: str) -> None:
            self.html = value

        def verticalScrollBar(self) -> _ScrollBar:
            return self.scroll_bar

    speaker = '<a href="https://example.invalid/">Alice</a>'
    chat = _Chat()
    conversation = object.__new__(DashboardConversationMixin)
    conversation.assistant_name = "墨寒"
    conversation.db = object()
    conversation.chat = chat
    monkeypatch.setattr(
        dashboard_conversation,
        "personalize_text",
        lambda _db, text: text,
    )

    conversation.append_chat(speaker, "hello")

    assert "<a href=\"https://example.invalid/\">" not in chat.html
    assert "&lt;a href=&quot;https://example.invalid/&quot;&gt;Alice&lt;/a&gt;" in chat.html
