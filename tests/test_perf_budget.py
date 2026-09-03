"""Run the reduced offscreen composite benchmark as a CI performance gate."""

from __future__ import annotations

lazy import json
lazy import os
lazy import subprocess
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "tools" / "bench_composite.py"
BUDGET_PATH = ROOT / "tools" / "perf_budget.json"
CI_TIMEOUT_SECONDS = 180
EXPECTED_SCHEMA = "mohan.composite-performance-budget.v1"
BENCHMARK_SCHEMA = "mohan.composite-performance.v1"
EXPECTED_BASELINE_ITERATIONS = 5
EXPECTED_BASELINE_ROUNDS = 5
EXPECTED_METRICS = (
    "cold_full_body",
    "hot_full_body_view_switch",
    "hot_half_body_silhouette_switch",
)


def _budget() -> dict[str, object]:
    return json.loads(BUDGET_PATH.read_text(encoding="utf-8"))


def _number(record: dict[str, object], key: str) -> float:
    value = record[key]
    assert isinstance(value, (int, float)) and not isinstance(value, bool)
    return float(value)


def test_budget_records_the_measured_formula_and_over_target_truth() -> None:
    budget = _budget()
    assert budget["schema"] == EXPECTED_SCHEMA
    basis = budget["measurement_basis"]
    assert isinstance(basis, dict)
    assert basis["qt_qpa_platform"] == "offscreen"
    assert basis["rounds"] == EXPECTED_BASELINE_ROUNDS
    assert basis["iterations_per_round"] == EXPECTED_BASELINE_ITERATIONS

    targets = budget["owner_targets_ms"]
    records = budget["budgets"]
    assert isinstance(targets, dict)
    assert isinstance(records, dict)
    assert tuple(records) == EXPECTED_METRICS
    for metric in EXPECTED_METRICS:
        record = records[metric]
        assert isinstance(record, dict)
        assert _number(record, "budget_ms") >= _number(record, "measured_p95_ms")
        assert _number(record, "round_p95_max_ms") == _number(
            record,
            "measured_p95_ms",
        )
        assert "formula" in record and "reason" in record

    cold = records["cold_full_body"]
    assert isinstance(cold, dict)
    assert cold["over_target"] is True
    assert _number(cold, "measured_p95_ms") > _number(
        targets,
        "cold_full_body",
    )
    assert "do not multiply it by 1.5" in cold["reason"]


def test_reduced_offscreen_measurement_is_inside_the_budget() -> None:
    budget = _budget()
    gate = budget["ci_gate"]
    records = budget["budgets"]
    assert isinstance(gate, dict)
    assert isinstance(records, dict)
    command = [
        sys.executable,
        str(BENCHMARK),
        "--iterations",
        str(gate["reduced_iterations_per_round"]),
        "--rounds",
        str(gate["reduced_rounds"]),
    ]
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=CI_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, (
        f"benchmark failed with exit {completed.returncode}:\n"
        f"stdout={completed.stdout}\n"
        f"stderr={completed.stderr}"
    )
    result = json.loads(completed.stdout)
    assert result["schema"] == BENCHMARK_SCHEMA
    assert result["environment"]["qt_offscreen"] is True
    measurements = result["measurements"]
    assert isinstance(measurements, dict)
    for metric in EXPECTED_METRICS:
        observed = measurements[metric]["summary"]["p95_ms"]
        ceiling = records[metric]["budget_ms"]
        assert observed <= ceiling, (
            f"{metric} p95 {observed} ms exceeds budget {ceiling} ms"
        )

    conclusion = result["decode_audit"]["conclusion"]
    assert conclusion["new_decode_calls_on_hot_full_body_switch"] is False
    assert conclusion["new_decode_calls_on_hot_half_body_switch"] is False
