from __future__ import annotations

"""Measure MoHan's offline first-paint and deferred-startup latency."""

lazy import argparse
lazy import json
lazy import os
lazy import platform
lazy import socket
lazy import statistics
lazy import subprocess
lazy import sys
lazy import tempfile
lazy import time
lazy from pathlib import Path
lazy from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULT_PREFIX = "MOHAN_STARTUP_RESULT="
MINIMUM_RUNS = 7
MINIMUM_SUMMARY_SAMPLES = 2
IMPORT_TIME_FIELD_COUNT = 3
DEFAULT_TIMEOUT_SECONDS = 120.0


def _quartiles(values: list[float]) -> tuple[float, float]:
    """Return Tukey hinges so small samples have an unsurprising IQR."""

    ordered = sorted(values)
    midpoint = len(ordered) // 2
    lower = ordered[:midpoint]
    upper = ordered[-midpoint:]
    return statistics.median(lower), statistics.median(upper)


def summarize(values: list[float]) -> dict[str, float]:
    if len(values) < MINIMUM_SUMMARY_SAMPLES:
        raise ValueError("At least two measurements are required.")
    q1, q3 = _quartiles(values)
    return {
        "median_ms": round(statistics.median(values), 3),
        "q1_ms": round(q1, 3),
        "q3_ms": round(q3, 3),
        "iqr_ms": round(q3 - q1, 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


def _block_network() -> None:
    def blocked_connect(*_args: object, **_kwargs: object) -> None:
        raise OSError("Startup measurement forbids network connections.")

    socket.socket.connect = blocked_connect
    socket.socket.connect_ex = blocked_connect


def _worker() -> int:
    _block_network()
    start_ns = int(os.environ["MOHAN_STARTUP_T0_NS"])

    from PySide6.QtCore import QEvent, QObject

    from application.application_bootstrap import _create_application
    from integrations.openai_fashion_trend_scout import (
        create_openai_fashion_trend_scout,
    )
    from presentation.companion_window import CompanionWindow

    class FirstPaintProbe(QObject):
        def __init__(self) -> None:
            super().__init__()
            self.first_paint_ns: int | None = None

        def eventFilter(self, watched: QObject, event: QEvent) -> bool:
            del watched
            if self.first_paint_ns is None and event.type() == QEvent.Paint:
                self.first_paint_ns = time.perf_counter_ns()
            return False

    app = _create_application()
    window = CompanionWindow(
        startup_speech=False,
        defer_visual_startup=True,
        fashion_trend_scout_factory=create_openai_fashion_trend_scout,
    )
    probe = FirstPaintProbe()
    window.installEventFilter(probe)
    window.show()
    deadline = time.perf_counter() + DEFAULT_TIMEOUT_SECONDS
    while probe.first_paint_ns is None and time.perf_counter() < deadline:
        app.processEvents()
        time.sleep(0.001)
    if probe.first_paint_ns is None:
        raise TimeoutError("The main window did not paint before the timeout.")

    window.complete_deferred_startup()
    app.processEvents()
    deferred_ns = time.perf_counter_ns()
    if not window._visual_startup_complete:
        raise RuntimeError("Deferred startup returned without completing.")

    payload = {
        "first_paint_ms": (probe.first_paint_ns - start_ns) / 1_000_000,
        "deferred_complete_ms": (deferred_ns - probe.first_paint_ns) / 1_000_000,
        "total_ms": (deferred_ns - start_ns) / 1_000_000,
    }
    window.close()
    app.processEvents()
    print(RESULT_PREFIX + json.dumps(payload, sort_keys=True), flush=True)
    return 0


def _worker_environment(temp_root: Path, start_ns: int) -> dict[str, str]:
    environment = os.environ.copy()
    existing_python_path = environment.get("PYTHONPATH", "")
    python_path = str(ROOT)
    if existing_python_path:
        python_path += os.pathsep + existing_python_path
    environment.update(
        {
            "ALL_PROXY": "",
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "LOCALAPPDATA": str(temp_root),
            "MOHAN_DATA_DIR": str(temp_root / "profile"),
            "MOHAN_STARTUP_T0_NS": str(start_ns),
            "NO_PROXY": "*",
            "PYTHONPATH": python_path,
            "QT_QPA_PLATFORM": "offscreen",
        }
    )
    return environment


def _invoke_worker(*, import_time: bool = False) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(
        prefix="mohan-startup-",
        ignore_cleanup_errors=True,
    ) as temp:
        command = [sys.executable]
        if import_time:
            command.extend(("-X", "importtime"))
        command.extend((str(Path(__file__).resolve()), "--_worker"))
        start_ns = time.perf_counter_ns()
        return subprocess.run(
            command,
            cwd=ROOT,
            env=_worker_environment(Path(temp), start_ns),
            capture_output=True,
            check=False,
            text=True,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )


def _parse_worker_result(completed: subprocess.CompletedProcess[str]) -> dict[str, float]:
    if completed.returncode != 0:
        raise RuntimeError(
            "Startup worker failed with exit code "
            f"{completed.returncode}:\n{completed.stdout}\n{completed.stderr}"
        )
    result_line = next(
        (
            line
            for line in reversed(completed.stdout.splitlines())
            if line.startswith(RESULT_PREFIX)
        ),
        "",
    )
    if not result_line:
        raise RuntimeError("Startup worker did not emit a measurement result.")
    return json.loads(result_line.removeprefix(RESULT_PREFIX))


def _import_time_sources(stderr: str) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for line in stderr.splitlines():
        if not line.startswith("import time:") or "cumulative" in line:
            continue
        fields = line.removeprefix("import time:").split("|", 2)
        if len(fields) != IMPORT_TIME_FIELD_COUNT:
            continue
        try:
            self_us = int(fields[0].strip())
            cumulative_us = int(fields[1].strip())
        except ValueError:
            continue
        sources.append(
            {
                "module": fields[2].strip(),
                "self_ms": round(self_us / 1_000, 3),
                "cumulative_ms": round(cumulative_us / 1_000, 3),
            }
        )
    return sorted(
        sources,
        key=lambda item: (item["cumulative_ms"], item["self_ms"]),
        reverse=True,
    )[:15]


def _git_value(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def measure(runs: int) -> dict[str, Any]:
    if runs < MINIMUM_RUNS:
        raise ValueError(f"--runs must be at least {MINIMUM_RUNS}.")
    samples = [_parse_worker_result(_invoke_worker()) for _ in range(runs)]
    profiled = _invoke_worker(import_time=True)
    _parse_worker_result(profiled)
    metrics = {
        name: summarize([sample[name] for sample in samples])
        for name in ("first_paint_ms", "deferred_complete_ms", "total_ms")
    }
    return {
        "schema": "mohan.startup-measurement.v1",
        "measurement": {
            "runs": runs,
            "clock": "time.perf_counter_ns",
            "quartiles": "Tukey hinges",
            "qt_qpa_platform": "offscreen",
            "network": "socket connect and proxy paths disabled",
            "profile_storage": "fresh temporary LOCALAPPDATA and MOHAN_DATA_DIR per run",
            "startup_speech": False,
        },
        "repository": {
            "branch": _git_value("branch", "--show-current"),
            "head": _git_value("rev-parse", "HEAD"),
        },
        "runtime": {
            "python": sys.version.split()[0],
            "executable": sys.executable,
            "platform": platform.platform(),
        },
        "samples_ms": samples,
        "summary": metrics,
        "import_time_top_15": _import_time_sources(profiled.stderr),
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "MoHan startup measurement",
        f"runs: {report['measurement']['runs']}",
        f"head: {report['repository']['head']}",
    ]
    labels = {
        "first_paint_ms": "process start -> first paint",
        "deferred_complete_ms": "first paint -> deferred startup complete",
        "total_ms": "process start -> deferred startup complete",
    }
    for name, label in labels.items():
        summary = report["summary"][name]
        lines.append(
            f"{label}: median {summary['median_ms']:.3f} ms, "
            f"IQR {summary['iqr_ms']:.3f} ms "
            f"(Q1 {summary['q1_ms']:.3f}, Q3 {summary['q3_ms']:.3f})"
        )
    lines.append("top import-time sources (cumulative ms):")
    lines.extend(
        f"  {item['cumulative_ms']:10.3f}  {item['module']}"
        for item in report["import_time_top_15"]
    )
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=MINIMUM_RUNS)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--text-output", type=Path)
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments._worker:
        return _worker()
    report = measure(arguments.runs)
    json_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    text_report = render_text(report)
    if arguments.json_output:
        arguments.json_output.write_text(json_text, encoding="utf-8")
    else:
        print(json_text, end="")
    if arguments.text_output:
        arguments.text_output.write_text(text_report, encoding="utf-8")
    else:
        print(text_report, file=sys.stderr, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
