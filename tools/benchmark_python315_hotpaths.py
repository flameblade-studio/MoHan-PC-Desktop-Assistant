from __future__ import annotations

lazy import argparse
lazy import json
lazy import math
lazy import os
lazy import statistics
lazy import subprocess
lazy import sys
lazy import time
lazy from array import array
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from domain.expression_system import EXPRESSION_RULES, ExpressionArbiter
lazy from domain.lip_sync import (
    VISEME_CUES_PER_SECOND,
    VisemeDynamics,
    infer_vowel_pcm16,
)


def _audio_frames() -> tuple[bytes, ...]:
    sample_rate = 24_000
    samples_per_cue = sample_rate // VISEME_CUES_PER_SECOND
    frames: list[bytes] = []
    for first, second in ((800, 1200), (300, 2400), (350, 850), (500, 2000), (500, 950)):
        samples = array(
            "h",
            (
                round(
                    4_200 * math.sin(2 * math.pi * first * index / sample_rate)
                    + 2_400 * math.sin(2 * math.pi * second * index / sample_rate)
                )
                for index in range(samples_per_cue)
            ),
        )
        if sys.byteorder != "little":
            samples.byteswap()
        frames.append(samples.tobytes())
    return tuple(frames)


def _expression_workload(iterations: int) -> tuple[float, dict[str, object]]:
    expressions = tuple(EXPRESSION_RULES)
    sources = ("ambient", "ai_wait", "conversation", "user_direct", "reminder", "safety")
    arbiter = ExpressionArbiter(set(expressions), clock=lambda: 0.0)
    accepted = 0
    reason_counts: dict[str, int] = {}
    started = time.perf_counter()
    for index in range(iterations):
        decision = arbiter.request(
            expressions[index % len(expressions)],
            source=sources[index % len(sources)],
            intensity=(index % 101) / 100,
            force=index % 97 == 0,
            now_ms=index * 23,
        )
        accepted += int(decision.accepted)
        reason_counts[decision.reason] = reason_counts.get(decision.reason, 0) + 1
    elapsed = time.perf_counter() - started
    checksum = {
        "accepted": accepted,
        "generation": arbiter.generation,
        "active": arbiter.active,
        "reasons": reason_counts,
    }
    return elapsed, checksum


def _lipsync_workload(iterations: int) -> tuple[float, dict[str, object]]:
    frames = _audio_frames()
    inferred_counts: dict[str, int] = {}
    selected_counts: dict[str, int] = {}
    level_checksum = 0
    jaw_checksum = 0
    dynamics = VisemeDynamics()
    started = time.perf_counter()
    for index in range(iterations):
        # Four consecutive 20 ms cues exercise confirmation, hold and change
        # behavior instead of presenting an impossible new vowel every frame.
        frame = frames[(index // 4) % len(frames)]
        level, vowel = infer_vowel_pcm16(frame)
        viseme = dynamics.advance(level, vowel)
        inferred_counts[vowel] = inferred_counts.get(vowel, 0) + 1
        selected_counts[viseme.selected] = (
            selected_counts.get(viseme.selected, 0) + 1
        )
        level_checksum += round(level * 1_000_000)
        jaw_checksum += round(viseme.jaw_aperture * 1_000_000)
    elapsed = time.perf_counter() - started
    return elapsed, {
        "levels": level_checksum,
        "jaw": jaw_checksum,
        "inferred_visemes": inferred_counts,
        "selected_visemes": selected_counts,
        "cue_hz": VISEME_CUES_PER_SECOND,
    }


def worker(expression_iterations: int, lipsync_iterations: int, rounds: int) -> dict[str, object]:
    jit = getattr(sys, "_jit", None)
    if not jit or not jit.is_available():
        raise RuntimeError("This benchmark requires a CPython build with JIT support")
    expression_times: list[float] = []
    lipsync_times: list[float] = []
    expression_checksum: dict[str, object] | None = None
    lipsync_checksum: dict[str, object] | None = None
    for _ in range(rounds):
        elapsed, current = _expression_workload(expression_iterations)
        expression_times.append(elapsed)
        if expression_checksum is not None and current != expression_checksum:
            raise RuntimeError("Expression benchmark produced a non-deterministic result")
        expression_checksum = current
        elapsed, current = _lipsync_workload(lipsync_iterations)
        lipsync_times.append(elapsed)
        if lipsync_checksum is not None and current != lipsync_checksum:
            raise RuntimeError("Lip-sync benchmark produced a non-deterministic result")
        lipsync_checksum = current
    return {
        "jit_enabled": jit.is_enabled(),
        "expression": {
            "iterations": expression_iterations,
            "median_seconds": round(statistics.median(expression_times), 6),
            "checksum": expression_checksum,
        },
        "lipsync_50hz": {
            "iterations": lipsync_iterations,
            "median_seconds": round(statistics.median(lipsync_times), 6),
            "checksum": lipsync_checksum,
        },
    }


def _run_mode(mode: str, args: argparse.Namespace) -> dict[str, object]:
    environment = os.environ.copy()
    environment["PYTHON_JIT"] = mode
    environment.pop("MOHAN_DISABLE_JIT", None)
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            "--expected-jit",
            mode,
            "--expression-iterations",
            str(args.expression_iterations),
            "--lipsync-iterations",
            str(args.lipsync_iterations),
            "--rounds",
            str(args.rounds),
        ],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--expected-jit", choices=("0", "1"))
    parser.add_argument("--expression-iterations", type=int, default=120_000)
    parser.add_argument("--lipsync-iterations", type=int, default=2_000)
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    if args.worker:
        result = worker(args.expression_iterations, args.lipsync_iterations, args.rounds)
        expected = args.expected_jit == "1"
        if result["jit_enabled"] is not expected:
            raise RuntimeError(
                f"PYTHON_JIT={args.expected_jit} was not passed to the child runtime"
            )
        print(json.dumps(result, ensure_ascii=False))
        return 0

    off = _run_mode("0", args)
    on = _run_mode("1", args)
    for name in ("expression", "lipsync_50hz"):
        if off[name]["checksum"] != on[name]["checksum"]:
            raise RuntimeError(f"JIT changed the functional result of {name}")
    result = {
        "result": "PYTHON315_JIT_HOTPATH_COMPARISON_OK",
        "python": sys.version.split()[0],
        "jit_off": off,
        "jit_on": on,
        "relative": {
            name: round(
                off[name]["median_seconds"] / on[name]["median_seconds"],
                4,
            )
            for name in ("expression", "lipsync_50hz")
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
