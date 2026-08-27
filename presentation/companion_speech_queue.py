from __future__ import annotations

lazy from collections import deque
lazy from collections.abc import Callable, MutableMapping

lazy from domain.speech_configuration import QueuedSpeech

MAX_PENDING_SPEECH = 32


def enqueue_bounded_speech(
    queue: deque[QueuedSpeech],
    queued: QueuedSpeech,
    *,
    proactive_completions: MutableMapping[str, Callable[[bool], None]] | None = None,
) -> bool:
    """Add speech without allowing a stalled provider to grow memory forever."""

    if len(queue) < MAX_PENDING_SPEECH:
        queue.append(queued)
        return True
    if queued.delivery_token:
        return False
    evicted = queue.popleft()
    if evicted.delivery_token:
        if proactive_completions is not None:
            proactive_completions.pop(evicted.delivery_token, None)
        if evicted.completed is not None:
            evicted.completed(False)
    queue.append(queued)
    return True
