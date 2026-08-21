from __future__ import annotations

lazy import random
lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from expression_system import (
    AI_WAIT_TIMEOUT_MS,
    EMOTION_TO_EXPRESSION,
    ExpressionArbiter,
    parse_internal_emotion,
    plan_wait_expressions,
)

MIN_COMPLEX_DELAY_MS = 1_000
EXPECTED_TAGGED_INTENSITY = 0.72
SPEAKING_FORCE_PROBABILITY = 0.06
IDLE_FORCE_PROBABILITY = 0.08
MIN_ACCEPTED_COUNT = 500
MIN_REJECTED_COUNT = 500
AUDIT_CAPACITY = 256


class VirtualClock:
    def __init__(self) -> None:
        self.seconds = 0.0

    def __call__(self) -> float:
        return self.seconds

    def advance_ms(self, milliseconds: int) -> None:
        self.seconds += milliseconds / 1000.0


def assert_wait_expression_plans() -> None:
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
    assert complex_prompt[0].delay_ms >= MIN_COMPLEX_DELAY_MS
    assert complex_prompt[0].delay_ms < AI_WAIT_TIMEOUT_MS

    narrative = plan_wait_expressions(
        "我今天把企劃重新整理了一遍，也補上角色設定，"
        "接下來想和妳慢慢說說目前的進度。"
    )
    assert narrative[0].expression == "attentive_front"
    assert narrative[-1].reason == "response_timeout"


def create_arbiter() -> tuple[set[str], VirtualClock, ExpressionArbiter]:
    allowed = set(EMOTION_TO_EXPRESSION.values())
    clock = VirtualClock()
    arbiter = ExpressionArbiter(allowed, clock=clock)
    return allowed, clock, arbiter


def assert_priority_and_cooldown(
    clock: VirtualClock,
    arbiter: ExpressionArbiter,
) -> None:
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


def assert_internal_emotion_parsing() -> None:
    tagged = parse_internal_emotion(
        "主上，妾已想明白。[[MOHAN_EMOTION:thinking:0.72]]"
    )
    assert tagged.text == "主上，妾已想明白。"
    assert tagged.expression == "thinking_front"
    assert tagged.intensity == EXPECTED_TAGGED_INTENSITY
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


def assert_eight_hour_arbitration_soak(
    allowed: set[str],
    clock: VirtualClock,
    arbiter: ExpressionArbiter,
) -> None:
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
        if random.random() < SPEAKING_FORCE_PROBABILITY:
            arbiter.request("speaking", force=True)
        if random.random() < IDLE_FORCE_PROBABILITY:
            arbiter.request("idle", force=True)
    assert accepted > MIN_ACCEPTED_COUNT
    assert rejected > MIN_REJECTED_COUNT
    assert len(arbiter.audit) == AUDIT_CAPACITY


def run() -> None:
    assert_wait_expression_plans()
    allowed, clock, arbiter = create_arbiter()
    assert_priority_and_cooldown(clock, arbiter)
    assert_internal_emotion_parsing()
    assert_eight_hour_arbitration_soak(allowed, clock, arbiter)
    print("EXPRESSION_ARBITER_AND_8H_SOAK_OK")


if __name__ == "__main__":
    run()
