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


class _ProactiveDb:
    @staticmethod
    def setting(_key: str, default: object = None) -> object:
        return default


def _proactive_harness():
    from presentation.companion_proactive import CompanionProactiveMixin

    class Harness(CompanionProactiveMixin):
        def __init__(self) -> None:
            self._closing = False
            self.db = _ProactiveDb()
            self.speech_queue: deque[QueuedSpeech] = deque()
            self._proactive_speech_completions = {}
            self.started = 0

        def _start_next_speech(self) -> None:
            self.started += 1

    return Harness()


def test_proactive_enqueue_shares_completion_registry_with_bounded_queue() -> None:
    """The proactive mixin must hand its delivery-token registry to the
    bounded queue; otherwise a later eviction of a queued proactive line
    leaves its token behind and permanently blocks redelivery."""

    import presentation.companion_proactive as proactive_module

    harness = _proactive_harness()
    seen_registries: list[object] = []
    # Keep whatever binding (resolved function or still-lazy proxy) the
    # module currently holds so it can be restored verbatim afterwards.
    original_binding = proactive_module.enqueue_bounded_speech

    def recording_enqueue(queue, queued, *, proactive_completions=None):
        seen_registries.append(proactive_completions)
        return enqueue_bounded_speech(
            queue,
            queued,
            proactive_completions=proactive_completions,
        )

    proactive_module.enqueue_bounded_speech = recording_enqueue
    try:
        assert harness._enqueue_proactive_speech(
            "主上，久等了。",
            "idle",
            "token-1",
            lambda _ok: None,
        )
    finally:
        proactive_module.enqueue_bounded_speech = original_binding

    assert seen_registries == [harness._proactive_speech_completions]
    assert "token-1" in harness._proactive_speech_completions

    # With the shared registry, an eviction caused by a full queue must also
    # clear the token so the bridge may redeliver the message later.
    while len(harness.speech_queue) < MAX_PENDING_SPEECH:
        assert enqueue_bounded_speech(
            harness.speech_queue,
            QueuedSpeech("filler", "idle"),
            proactive_completions=harness._proactive_speech_completions,
        )
    assert enqueue_bounded_speech(
        harness.speech_queue,
        QueuedSpeech("conversation", "speaking"),
        proactive_completions=harness._proactive_speech_completions,
    )
    assert "token-1" not in harness._proactive_speech_completions
