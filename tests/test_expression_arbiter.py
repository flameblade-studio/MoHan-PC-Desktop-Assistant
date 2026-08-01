from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from expression_system import (
    AI_WAIT_TIMEOUT_MS,
    EMOTION_TO_EXPRESSION,
    ExpressionArbiter,
    plan_wait_expressions,
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
    greeting = plan_wait_expressions("早安，墨寒")
    assert len(greeting) == 1
    assert greeting[0].expression == "thinking_front"
    assert greeting[0].delay_ms == AI_WAIT_TIMEOUT_MS

    ordinary = plan_wait_expressions("天空為什麼是藍色？")
    assert len(ordinary) == 1
    assert ordinary[0].reason == "response_timeout"

    complex_prompt = plan_wait_expressions(
        "請分析兩個方案的利弊、風險與優先順序。"
    )
    assert [cue.expression for cue in complex_prompt] == [
        "thinking_front",
        "thinking_front",
    ]
    assert complex_prompt[0].delay_ms >= 1_000
    assert complex_prompt[0].delay_ms < AI_WAIT_TIMEOUT_MS

    narrative = plan_wait_expressions(
        "我今天把企劃重新整理了一遍，也補上角色設定，"
        "接下來想和妳慢慢說說目前的進度。"
    )
    assert narrative[0].expression == "attentive_front"
    assert narrative[-1].reason == "response_timeout"

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
        "ai_wait",
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
