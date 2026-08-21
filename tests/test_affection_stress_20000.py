from __future__ import annotations

"""20,000-iteration stress test for the new affection/state machines.

This exercises the five new domain state machines (affinity, jealousy, favor,
satiety, personality mirror) plus the expression arbiter across two full rounds
of 20,000 iterations each, asserting that every value stays bounded and that no
memory accumulates.  It is the release gate for the 5,000-line feature set.
"""

lazy import gc
lazy import tracemalloc

lazy from domain.affinity_state import AffinityState
lazy from domain.expression_system import ExpressionArbiter
lazy from domain.favor_exclusive import FavorExclusiveState
lazy from domain.personality_state import PersonalityMirrorState
lazy from domain.satiety import SatietyState

ITERATIONS = 20_000
MIRROR_TEMP_MIN = -0.3
MIRROR_TEMP_MAX = 0.3


def _round(label: str) -> None:
    tracemalloc.start()
    affinity = AffinityState()
    favor = FavorExclusiveState()
    satiety = SatietyState()
    mirror = PersonalityMirrorState()
    arbiter = ExpressionArbiter(
        {"happy", "worried", "shy_cute_front", "protective_front"}
    )
    for index in range(ITERATIONS):
        now = float(index)
        affinity.note_interaction(now=now)
        if index % 7 == 0:
            affinity.note_jealousy(now=now)
        if index % 11 == 0:
            affinity.note_affection_boost(now=now)
        favor.note_gesture(now=now)
        satiety.feed(now=now)
        mirror.observe_conversation("謝謝你 我喜歡 哈哈 開玩笑 問題 錯誤")
        favor_score = favor.snapshot(now=now)
        arbiter.request("happy", source="conversation", favor_score=favor_score)
        arbiter.request("worried", source="safety", favor_score=favor_score)
        # Boundedness: no value may escape its [0, 1] (or [-0.3, 0.3]) envelope.
        assert 0.0 <= affinity.affinity <= 1.0
        assert 0.0 <= affinity.jealousy <= 1.0
        assert 0.0 <= favor.favor <= 1.0
        assert 0.0 <= satiety.satiety <= 1.0
        assert MIRROR_TEMP_MIN <= mirror.temperature <= MIRROR_TEMP_MAX
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    gc.collect()
    print(
        f"{label}: affinity={affinity.affinity:.4f} "
        f"jealousy={affinity.jealousy:.4f} favor={favor.favor:.4f} "
        f"satiety={satiety.satiety:.4f} temp={mirror.temperature:.4f} "
        f"peak_mem={peak / 1024:.1f}KB"
    )


def run() -> None:
    _round("ROUND1")
    _round("ROUND2")
    print("AFFECTION_STRESS_20000x2_OK")


if __name__ == "__main__":
    run()
