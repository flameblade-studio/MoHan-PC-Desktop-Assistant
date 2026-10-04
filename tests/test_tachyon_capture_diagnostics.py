from __future__ import annotations

lazy import json
lazy import argparse
lazy import subprocess
lazy import sys
lazy import tempfile
lazy from pathlib import Path
lazy from contextlib import redirect_stdout
lazy from io import StringIO
lazy from unittest.mock import patch
lazy from profiling.sampling.binary_collector import BinaryCollector
lazy from profiling.sampling.sample import SampleProfiler
lazy from tools import tachyon_capture
lazy from tools.profile_mohan_tachyon import (
    CaptureAttempt, _artifact_paths, _capture_once, _capture_with_retries,
    _host_evidence,
)

EXPECTED_RETRY_ATTEMPTS = 2


def test_counted_errors_preserve_exceptions_and_sampling_operations() -> None:
    original = BinaryCollector.collect_failed_sample
    collector = object.__new__(BinaryCollector)
    profiler = object.__new__(SampleProfiler)
    profiler.blocking = True
    calls: list[str] = []

    class Unwinder:
        failing = ""

        def pause_threads(self) -> None:
            calls.append("pause_threads")
            if self.failing == "pause_threads":
                raise OSError("SuspendThread: Windows error 5")

        def get_stack_trace(self) -> list[object]:
            calls.append("read_stack")
            if self.failing == "read_stack":
                raise RuntimeError("Failed to parse initial frame in chain")
            return []

        def resume_threads(self) -> None:
            calls.append("resume_threads")
            if self.failing == "resume_threads":
                raise OSError("ResumeThread: Windows error 6")

    unwinder = Unwinder()
    profiler.unwinder = unwinder

    def sample(*_args: object, **_kwargs: object) -> None:
        for operation in ("pause_threads", "read_stack", "resume_threads"):
            unwinder.failing = operation
            try:
                profiler._get_stack_trace()
            except (RuntimeError, OSError) as error:
                collector.collect_failed_sample()
                # The observer leaves the active exception unchanged.
                assert sys.exception() is error
            else:
                raise AssertionError("The sampling failure must propagate.")
        unwinder.failing = ""
        assert profiler._get_stack_trace() == []

    stdout = StringIO()
    with patch.object(tachyon_capture.runpy, "run_module", side_effect=sample), redirect_stdout(stdout):
        tachyon_capture.main()
    assert BinaryCollector.collect_failed_sample is original
    rows = json.loads(stdout.getvalue().removeprefix(tachyon_capture.DIAGNOSTICS_PREFIX))
    assert [row["operation"] for row in rows] == ["pause_threads", "read_stack", "resume_threads"]
    assert [row["count"] for row in rows] == [1, 1, 1]
    assert [row["windows_error"] for row in rows] == [5, None, 6]
    assert all(row["source"].startswith("sample.py:") for row in rows)
    assert calls == [
        "pause_threads",
        "pause_threads", "read_stack", "resume_threads",
        "pause_threads", "read_stack", "resume_threads",
        "pause_threads", "read_stack", "resume_threads",
    ]


def test_attempts_retain_each_error_category_and_missing_observer_is_explicit() -> None:
    rows = [{"operation": "read_stack", "exception_type": "RuntimeError", "count": 12}]
    attempt = CaptureAttempt(1, 33.0, True, output=tachyon_capture.DIAGNOSTICS_PREFIX + json.dumps(rows))
    assert attempt.as_json()["sample_read_errors"] == rows
    assert CaptureAttempt(2, 0.0, True).as_json()["sample_read_errors"] is None
    host = _host_evidence()
    assert host["python_build"]
    assert "processor_name" in host


def test_observer_restores_collector_and_does_not_count_process_exit() -> None:
    original = BinaryCollector.collect_failed_sample
    stdout = StringIO()
    error = ProcessLookupError("process terminated")
    with patch.object(tachyon_capture.runpy, "run_module", side_effect=error), redirect_stdout(stdout):
        try:
            tachyon_capture.main()
        except ProcessLookupError as raised:
            assert raised is error
        else:
            raise AssertionError("The original exit exception must propagate.")
    assert BinaryCollector.collect_failed_sample is original
    assert stdout.getvalue().strip() == tachyon_capture.DIAGNOSTICS_PREFIX + "[]"


def test_retry_and_aborted_capture_keep_attempt_diagnostics() -> None:
    rows = [{"operation": "read_stack", "exception_type": "RuntimeError", "count": 33}]
    output = "Error rate: 33.00\n" + tachyon_capture.DIAGNOSTICS_PREFIX + json.dumps(rows)
    args = argparse.Namespace(
        mode="wall", rate="1khz", duration=40, full_session=False,
        max_sample_read_error_percent=15.0,
    )
    with tempfile.TemporaryDirectory() as raw:
        directory = Path(raw)
        artifacts = _artifact_paths("expression", directory, None)
        artifacts.summary.parent.mkdir(parents=True)
        artifacts.runtime.write_text("{}", encoding="utf-8")
        results = [
            (subprocess.CompletedProcess([], 0, output, ""), 36.0),
            (subprocess.CompletedProcess([], 0, "Error rate: 0.00\n" + tachyon_capture.DIAGNOSTICS_PREFIX + "[]", ""), 36.0),
            (subprocess.CompletedProcess([], 1, output, ""), 1.0),
        ]

        def capture(number: int) -> CaptureAttempt:
            return _capture_once(args, "expression", number, artifacts, directory / "runner.py", {})

        with patch("tools.profile_mohan_tachyon._run_capture", side_effect=results):
            attempts = _capture_with_retries(args, "expression", capture)
            assert len(attempts) == EXPECTED_RETRY_ATTEMPTS
            try:
                capture(3)
            except RuntimeError as error:
                assert "exit code 1" in str(error)
            else:
                raise AssertionError("An aborted capture must remain a failure.")
        diagnostics = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(artifacts.summary.parent.glob("*.diagnostics.json"))
        ]
        assert [record["attempt"] for record in diagnostics] == [1, 2, 3]
        assert diagnostics[0]["sample_read_errors"] == rows
        assert diagnostics[1]["sample_read_errors"] == []
        assert diagnostics[2]["profiler_exit_code"] == 1


def main() -> None:
    test_counted_errors_preserve_exceptions_and_sampling_operations()
    test_attempts_retain_each_error_category_and_missing_observer_is_explicit()
    test_observer_restores_collector_and_does_not_count_process_exit()
    test_retry_and_aborted_capture_keep_attempt_diagnostics()


if __name__ == "__main__":
    main()
