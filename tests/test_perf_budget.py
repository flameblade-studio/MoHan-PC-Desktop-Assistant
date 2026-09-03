"""Run the reduced offscreen composite benchmark as a CI performance gate."""

from __future__ import annotations

lazy import json
lazy import math
lazy import os
lazy import pytest
lazy import subprocess
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "tools" / "bench_composite.py"
BUDGET_PATH = ROOT / "tools" / "perf_budget.json"
CI_TIMEOUT_SECONDS = 180
EXPECTED_SCHEMA = "mohan.composite-performance-budget.v1"
BENCHMARK_SCHEMA = "mohan.composite-performance.v1"
DEVELOPER_PROFILE = "developer_known_hardware"
CI_PROFILE = "ci_runner"
EXPECTED_PROFILES = (DEVELOPER_PROFILE, CI_PROFILE)
CI_RECORDED_COLD_P95_MS = 1722.333
EXPECTED_BASELINE_ITERATIONS = 5
EXPECTED_BASELINE_ROUNDS = 5
EXPECTED_CALIBRATION_ROUNDS = 5
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
    result = float(value)
    assert math.isfinite(result)
    return result


def _enabled(value: object) -> bool:
    return isinstance(value, str) and value.strip().casefold() in {
        "1",
        "true",
        "yes",
    }


def _profile_for_result(
    result_environment: dict[str, object],
    process_environment: dict[str, str],
    profiles: dict[str, object],
) -> str:
    ci_markers = ("GITHUB_ACTIONS", "CI")
    if any(_enabled(process_environment.get(marker)) for marker in ci_markers):
        return CI_PROFILE

    developer = profiles.get(DEVELOPER_PROFILE)
    assert isinstance(developer, dict)
    environment = developer.get("environment")
    assert isinstance(environment, dict)
    match = environment.get("match")
    assert isinstance(match, dict)
    mismatches = {
        key: {
            "expected": expected,
            "observed": result_environment.get(key),
        }
        for key, expected in match.items()
        if result_environment.get(key) != expected
    }
    if not mismatches:
        return DEVELOPER_PROFILE

    raise AssertionError(
        "PERF_BUDGET_ENVIRONMENT_UNIDENTIFIED: no CI marker and runtime "
        f"does not match {DEVELOPER_PROFILE}; mismatches={mismatches}; "
        f"runtime_environment={result_environment}"
    )


def _summary(measurement: object, label: str) -> dict[str, object]:
    assert isinstance(measurement, dict), f"{label} measurement is not an object"
    summary = measurement.get("summary")
    assert isinstance(summary, dict), f"{label} summary is not an object"
    return summary


def _require_sample_count(summary: dict[str, object], minimum: int, label: str) -> int:
    value = summary.get("count")
    assert isinstance(value, int) and not isinstance(value, bool), (
        f"PERF_BUDGET_SAMPLE_COUNT_INVALID: {label} count={value!r}; "
        f"minimum={minimum}"
    )
    assert value >= minimum, (
        f"PERF_BUDGET_SAMPLE_COUNT_INSUFFICIENT: {label} count={value}; "
        f"minimum={minimum}; fail-closed"
    )
    return value


def _assert_profile_shape(profile_name: str, profile: dict[str, object]) -> None:
    environment = profile["environment"]
    assert isinstance(environment, dict)
    assert environment["kind"] == profile_name
    measurement = profile["measurement"]
    assert isinstance(measurement, dict)
    assert _number(measurement, "iterations_per_round") > 0
    assert _number(measurement, "rounds") > 0
    assert _number(measurement, "calibration_rounds") >= EXPECTED_CALIBRATION_ROUNDS
    assert _number(measurement, "independent_runs") > 0
    assert isinstance(profile["margin_policy"], str)

    calibration = profile["calibration"]
    assert isinstance(calibration, dict)
    assert calibration["metric"] == "calibration.summary.p95_ms"
    assert isinstance(calibration["payload_sha256"], str)
    assert isinstance(calibration["method"], str)
    if profile_name == DEVELOPER_PROFILE:
        assert _number(calibration, "gate_floor_p95_ms") > 0

    records = profile["measurements"]
    assert isinstance(records, dict)
    assert tuple(records) == EXPECTED_METRICS
    for metric in EXPECTED_METRICS:
        record = records[metric]
        assert isinstance(record, dict)
        assert _number(record, "owner_target_ms") > 0
        assert _number(record, "ratio_budget") > 0
        assert isinstance(record["margin"], str)
        assert isinstance(record["formula"], str)
        assert isinstance(record["reason"], str)


def _assert_developer_profile_truth(profile: dict[str, object]) -> None:
    assert profile["measurement"]["rounds"] == EXPECTED_BASELINE_ROUNDS
    calibration = profile["calibration"]
    assert isinstance(calibration, dict)
    calibration_floor = _number(calibration, "gate_floor_p95_ms")
    calibration_round_floor = _number(calibration, "round_p95_min_ms")
    assert calibration_floor <= calibration_round_floor
    records = profile["measurements"]
    assert isinstance(records, dict)
    cold = records["cold_full_body"]
    assert isinstance(cold, dict)
    assert cold["over_target"] is True
    assert _number(cold, "measured_p95_ms") > _number(cold, "owner_target_ms")
    assert _number(cold, "absolute_budget_ms") >= _number(cold, "measured_p95_ms")
    expected_ratio_budget = _number(cold, "absolute_budget_ms") / calibration_floor
    assert math.isclose(
        _number(cold, "ratio_budget"),
        expected_ratio_budget,
        rel_tol=0.0,
        abs_tol=1e-6,
    )


def _assert_ci_profile_truth(profile: dict[str, object], budget: dict[str, object]) -> None:
    records = profile["measurements"]
    assert isinstance(records, dict)
    cold = records["cold_full_body"]
    assert isinstance(cold, dict)
    assert _number(cold, "observed_p95_ms") == CI_RECORDED_COLD_P95_MS
    assert profile["measurement"]["independent_runs"] == 1
    absolute_gate = profile["absolute_gate"]
    assert isinstance(absolute_gate, dict)
    assert absolute_gate["mode"] == "record_only"
    assert absolute_gate["active"] is False
    gate = budget["ci_gate"]
    assert isinstance(gate, dict)
    assert gate["ratio_active"] is True
    assert gate["ratio_threshold_profile"] == DEVELOPER_PROFILE
    profiles = budget["profiles"]
    assert isinstance(profiles, dict)
    developer = profiles[DEVELOPER_PROFILE]
    assert isinstance(developer, dict)
    developer_records = developer["measurements"]
    assert isinstance(developer_records, dict)
    developer_cold = developer_records["cold_full_body"]
    assert isinstance(developer_cold, dict)
    assert _number(cold, "ratio_budget") == _number(
        developer_cold,
        "ratio_budget",
    )


def test_perf_budget_fails_closed_for_unknown_environment() -> None:
    budget = _budget()
    profiles = budget["profiles"]
    assert isinstance(profiles, dict)
    with pytest.raises(
        AssertionError,
        match="PERF_BUDGET_ENVIRONMENT_UNIDENTIFIED",
    ):
        _profile_for_result(
            {"python": "unrecognized"},
            {},
            profiles,
        )


def test_perf_budget_fails_closed_for_insufficient_samples() -> None:
    with pytest.raises(
        AssertionError,
        match="PERF_BUDGET_SAMPLE_COUNT_INSUFFICIENT",
    ):
        _require_sample_count(
            {"count": 4},
            5,
            "calibration",
        )


def _run_reduced_benchmark(gate: dict[str, object]) -> dict[str, object]:
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
    return result


def _calibration_values(
    result: dict[str, object],
    gate: dict[str, object],
) -> tuple[float, int]:
    configuration = result.get("configuration")
    assert isinstance(configuration, dict)
    assert configuration.get("calibration_rounds") == EXPECTED_CALIBRATION_ROUNDS, (
        "PERF_BUDGET_CALIBRATION_ROUNDS_INVALID: "
        f"observed={configuration.get('calibration_rounds')!r}; "
        f"required={EXPECTED_CALIBRATION_ROUNDS}; fail-closed"
    )
    calibration = _summary(result["calibration"], "calibration")
    minimum_samples = int(gate["minimum_runtime_samples"])
    sample_count = _require_sample_count(calibration, minimum_samples, "calibration")
    p95 = _number(calibration, "p95_ms")
    assert p95 > 0, (
        "PERF_BUDGET_CALIBRATION_INVALID: calibration p95 must be positive; "
        f"observed_p95_ms={p95}; samples={sample_count}; fail-closed"
    )
    return p95, sample_count


def _assert_metric_gate(
    metric: str,
    measurement: object,
    record: dict[str, object],
    threshold_record: dict[str, object],
    *,
    context: dict[str, object],
) -> None:
    profile_name = context["profile_name"]
    calibration_p95 = context["calibration_p95"]
    calibration_count = context["calibration_count"]
    minimum_samples = context["minimum_samples"]
    assert isinstance(profile_name, str)
    assert isinstance(calibration_p95, float)
    assert isinstance(calibration_count, int)
    assert isinstance(minimum_samples, int)
    summary = _summary(measurement, metric)
    sample_count = _require_sample_count(summary, minimum_samples, metric)
    observed_p95 = _number(summary, "p95_ms")
    ratio_threshold = _number(threshold_record, "ratio_budget")
    observed_ratio = observed_p95 / calibration_p95
    absolute_budget = record.get("absolute_budget_ms")
    absolute_trend = record.get("observed_p95_ms")
    assert (
        profile_name == CI_PROFILE or isinstance(absolute_budget, (int, float))
    ), (
        "PERF_BUDGET_ABSOLUTE_THRESHOLD_MISSING: "
        f"environment={profile_name}; metric={metric}; fail-closed"
    )
    assert observed_ratio <= ratio_threshold, (
        "PERF_BUDGET_RATIO_GATE_FAILED: "
        f"environment={profile_name}; metric={metric}; "
        f"composition_p95_ms={observed_p95:.3f}; "
        f"calibration_p95_ms={calibration_p95:.3f}; "
        f"ratio={observed_ratio:.6f}; "
        f"ratio_threshold={ratio_threshold:.6f}; "
        f"absolute_trend_p95_ms={absolute_trend}; "
        f"absolute_budget_ms={absolute_budget}; "
        f"composition_samples={sample_count}; "
        f"calibration_samples={calibration_count}"
    )
    if profile_name == DEVELOPER_PROFILE:
        assert observed_p95 <= float(absolute_budget), (
            "PERF_BUDGET_DEVELOPER_ABSOLUTE_GATE_FAILED: "
            f"metric={metric}; observed_p95_ms={observed_p95:.3f}; "
            f"absolute_budget_ms={absolute_budget}; "
            f"ratio={observed_ratio:.6f}; "
            f"ratio_threshold={ratio_threshold:.6f}"
        )


def test_budget_records_environment_scoped_formula_and_truth() -> None:
    budget = _budget()
    assert budget["schema"] == EXPECTED_SCHEMA

    basis = budget["measurement_basis"]
    assert isinstance(basis, dict)
    assert basis["qt_qpa_platform"] == "offscreen"
    assert basis["iterations_per_round"] == EXPECTED_BASELINE_ITERATIONS
    assert basis["rounds"] == EXPECTED_BASELINE_ROUNDS
    assert basis["calibration_rounds"] == EXPECTED_CALIBRATION_ROUNDS

    profiles = budget["profiles"]
    assert isinstance(profiles, dict)
    assert tuple(profiles) == EXPECTED_PROFILES
    for profile_name in EXPECTED_PROFILES:
        profile = profiles[profile_name]
        assert isinstance(profile, dict)
        _assert_profile_shape(profile_name, profile)

    developer = profiles[DEVELOPER_PROFILE]
    assert isinstance(developer, dict)
    _assert_developer_profile_truth(developer)

    ci = profiles[CI_PROFILE]
    assert isinstance(ci, dict)
    _assert_ci_profile_truth(ci, budget)


def test_reduced_offscreen_measurement_is_inside_the_budget() -> None:
    budget = _budget()
    gate = budget["ci_gate"]
    profiles = budget["profiles"]
    assert isinstance(gate, dict)
    assert isinstance(profiles, dict)

    process_environment = os.environ.copy()
    result = _run_reduced_benchmark(gate)
    result_environment = result["environment"]
    assert isinstance(result_environment, dict)
    assert result_environment["qt_offscreen"] is True

    profile_name = _profile_for_result(
        result_environment,
        process_environment,
        profiles,
    )
    profile = profiles.get(profile_name)
    assert isinstance(profile, dict)
    minimum_samples = int(gate["minimum_runtime_samples"])
    calibration_p95, calibration_count = _calibration_values(result, gate)

    threshold_profile_name = gate["ratio_threshold_profile"]
    threshold_profile = profiles.get(threshold_profile_name)
    assert isinstance(threshold_profile, dict), (
        "PERF_BUDGET_RATIO_THRESHOLD_MISSING: "
        f"profile={threshold_profile_name!r}; fail-closed"
    )
    threshold_records = threshold_profile.get("measurements")
    assert isinstance(threshold_records, dict)
    records = profile.get("measurements")
    assert isinstance(records, dict)
    measurements = result["measurements"]
    assert isinstance(measurements, dict)
    context = {
        "profile_name": profile_name,
        "calibration_p95": calibration_p95,
        "calibration_count": calibration_count,
        "minimum_samples": minimum_samples,
    }

    for metric in EXPECTED_METRICS:
        threshold_record = threshold_records.get(metric)
        assert isinstance(threshold_record, dict)
        record = records.get(metric)
        assert isinstance(record, dict)
        _assert_metric_gate(
            metric,
            measurements.get(metric),
            record,
            threshold_record,
            context=context,
        )

    conclusion = result["decode_audit"]["conclusion"]
    assert conclusion["new_decode_calls_on_hot_full_body_switch"] is False
    assert conclusion["new_decode_calls_on_hot_half_body_switch"] is False
