from __future__ import annotations

lazy from collections import deque

lazy from domain.speech_configuration import QueuedSpeech
lazy from infrastructure.db_memory import MAX_MEMORIES, StudioDBMemoryMethods
lazy from infrastructure.memory_index import MAX_INDEXED_TEXT_CHARS, MemoryVectorIndex
lazy from presentation.companion_speech_queue import (
    MAX_PENDING_SPEECH,
    enqueue_bounded_speech,
)


def test_speech_queue_stays_bounded_and_rejects_proactive_flood() -> None:
    queue: deque[QueuedSpeech] = deque(
        QueuedSpeech(f"line-{index}", "idle")
        for index in range(MAX_PENDING_SPEECH)
    )
    proactive = QueuedSpeech(
        "proactive",
        "idle",
        source="proactive",
        delivery_token="token",
    )

    assert not enqueue_bounded_speech(queue, proactive)
    assert len(queue) == MAX_PENDING_SPEECH


def test_conversation_replaces_oldest_and_completes_evicted_proactive() -> None:
    results: list[bool] = []
    evicted = QueuedSpeech(
        "old proactive",
        "idle",
        source="proactive",
        delivery_token="old-token",
        completed=results.append,
    )
    queue: deque[QueuedSpeech] = deque([evicted])
    queue.extend(
        QueuedSpeech(f"line-{index}", "idle")
        for index in range(MAX_PENDING_SPEECH - 1)
    )
    completions = {"old-token": results.append}

    assert enqueue_bounded_speech(
        queue,
        QueuedSpeech("new conversation", "speaking"),
        proactive_completions=completions,
    )
    assert len(queue) == MAX_PENDING_SPEECH
    assert queue[-1].text == "new conversation"
    assert results == [False]
    assert "old-token" not in completions


def test_memory_retrieval_pool_is_bounded_without_deleting_user_data() -> None:
    class Harness:
        def __init__(self) -> None:
            self.limit = 0

        def list_memories(self, limit: int):
            self.limit = limit
            return []

    harness = Harness()
    assert StudioDBMemoryMethods.memory_context(harness) == ""
    assert harness.limit == MAX_MEMORIES


def test_memory_index_document_text_has_a_hard_transient_bound() -> None:
    text = MemoryVectorIndex._document_text({
        "category": "category",
        "title": "title",
        "content": "x" * (MAX_INDEXED_TEXT_CHARS * 10),
    })
    assert len(text) == MAX_INDEXED_TEXT_CHARS
