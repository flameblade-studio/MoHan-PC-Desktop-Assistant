from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from expression_system import (
    EMOTION_TO_EXPRESSION,
    ExpressionArbiter,
    classify_wait_expression,
    parse_internal_emotion,
)


class VirtualClock:
    def __init__(self) -> None:
        self.seconds = 0.0

    def __call__(self) -> float:
        return self.seconds

    def advance_ms(self, milliseconds: int) -> None:
        self.seconds += milliseconds / 1000.0


def run() -> None:
    # Waiting for the network is not itself a thinking emotion.  Casual and
    # ordinary factual questions must keep the current natural pose.
    assert classify_wait_expression("早安，墨寒") is None
    assert classify_wait_expression("妳今天心情好嗎？") is None
    assert classify_wait_expression("天空為什麼是藍色？") is None

    analytical = classify_wait_expression(
        "請分析這兩個方案的利弊、風險與優先順序。"
    )
    assert analytical is not None
    assert analytical.expression == "thinking_front"
    assert analytical.delay_ms >= 800

    attentive = classify_wait_expression(
        "我今天把企劃重新整理了一遍，還補上角色設定，接下來想和妳說說目前的進度。"
    )
    assert attentive is not None
    assert attentive.expression == "attentive_front"

    allowed = set(EMOTION_TO_EXPRESSION.values())
    clock = VirtualClock()
    arbiter = ExpressionArbiter(allowed, clock=clock)

    first = arbiter.request(
        "shy_cute_front",
        source="ai_tag",
        intensity=0.6,
    )
    assert first.accepted
    assert not arbiter.request(
        "shy_cute_front",
        source="ai_tag",
    ).accepted
    assert not arbiter.request(
        "attentive_front",
        source="fallback",
    ).accepted
    urgent = arbiter.request(
        "protective_front",
        source="safety",
        intensity=0.9,
    )
    assert urgent.accepted
    assert urgent.priority > first.priority
    arbiter.request("idle", force=True)

    clock.advance_ms(15_000)
    assert arbiter.request(
        "shy_cute_front",
        source="user_direct",
    ).accepted
    arbiter.request("idle", force=True)
    clock.advance_ms(100)
    cooldown = arbiter.request(
        "shy_cute_front",
        source="fallback",
    )
    assert not cooldown.accepted
    assert cooldown.reason == "cooldown"

    tagged = parse_internal_emotion(
        "主上，妾已想明白。[[MOHAN_EMOTION:thinking:0.72]]"
    )
    assert tagged.text == "主上，妾已想明白。"
    assert tagged.expression == "thinking_front"
    assert tagged.intensity == 0.72
    assert tagged.valid_tag

    multiple = parse_internal_emotion(
        "[[MOHAN_EMOTION:worried:0.9]]正文"
        "[[MOHAN_EMOTION:relieved:0.4]]"
    )
    assert multiple.text == "正文"
    assert multiple.expression == "relieved_front"
    invalid = parse_internal_emotion(
        "保留正文[[MOHAN_EMOTION:unknown:9.9]]"
    )
    assert invalid.text == "保留正文"
    assert not invalid.valid_tag

    # Accelerated eight-hour arbitration soak: random ordering, duplicate
    # requests, priority pre-emption and clock jumps must remain deterministic.
    random.seed(20260730)
    expressions = tuple(allowed)
    sources = (
        "ambient",
        "fallback",
        "ai_tag",
        "conversation",
        "user_direct",
        "reminder",
        "safety",
    )
    accepted = 0
    rejected = 0
    target_ms = 8 * 60 * 60 * 1000
    elapsed_ms = 0
    while elapsed_ms < target_ms:
        step = random.randint(20, 1_200)
        clock.advance_ms(step)
        elapsed_ms += step
        decision = arbiter.request(
            random.choice(expressions),
            source=random.choice(sources),
            intensity=random.random(),
        )
        accepted += int(decision.accepted)
        rejected += int(not decision.accepted)
        assert decision.generation == arbiter.generation
        assert decision.hold_ms > 0
        assert arbiter.active in arbiter.allowed
        if random.random() < 0.06:
            arbiter.request("speaking", force=True)
        if random.random() < 0.08:
            arbiter.request("idle", force=True)
    assert accepted > 500
    assert rejected > 500
    assert len(arbiter.audit) == 256
    print("EXPRESSION_ARBITER_AND_8H_SOAK_OK")


if __name__ == "__main__":
    run()
