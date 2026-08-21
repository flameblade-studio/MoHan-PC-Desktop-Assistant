from __future__ import annotations

# These fixtures intentionally model MoHan's offset-free local wall clock.
lazy import sys
lazy import time
lazy from datetime import datetime
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from background_agents import (
    AgentObservation,
    DiagnosticReportWorker,
    ManagerWorkerScheduler,
    VisibleAppWorker,
    is_quiet_time,
)

PAIR_LENGTH = 2


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class RepeatingWorker:
    worker_id = "repeating"
    interval_seconds = 1.0

    def poll(self):
        return [AgentObservation("repeating", "same", "安全觀察")]


def _wait_for_drain(
    scheduler: ManagerWorkerScheduler,
    timeout: float = 1.0,
):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rows = scheduler.drain(now=datetime(2026, 8, 4, 12, 0))
        if rows:
            return rows
        time.sleep(0.005)
    return []


def run() -> None:
    sequence = [
        [],
        [{"title": "MoHan — Visual Studio Code"}],
        [{"title": "MoHan — Visual Studio Code"}],
    ]

    def windows():
        return sequence.pop(0)

    visible = VisibleAppWorker(
        windows,
        {"Visual Studio Code": ("Visual Studio Code",)},
        interval_seconds=1,
    )
    assert list(visible.poll()) == []
    launched = list(visible.poll())
    assert len(launched) == 1
    assert launched[0].expression == "attentive_front"
    assert launched[0].metadata["status"] == "launched"
    assert list(visible.poll()) == []

    with TemporaryDirectory() as temp_dir:
        report = Path(temp_dir) / "diagnostics.log"
        report.write_text(
            "warning: first issue\nnormal line\n錯誤: second issue\n",
            encoding="utf-8",
        )
        diagnostic = DiagnosticReportWorker(lambda: report)
        observations = list(diagnostic.poll())
        assert len(observations) == 1
        assert observations[0].metadata["issue_lines"] == PAIR_LENGTH
        assert observations[0].metadata["read_only"] is True
        assert list(diagnostic.poll()) == []
        assert report.read_text(encoding="utf-8").startswith("warning")

    assert is_quiet_time(datetime(2026, 8, 4, 23, 0))
    assert is_quiet_time(datetime(2026, 8, 4, 7, 59))
    assert not is_quiet_time(datetime(2026, 8, 4, 12, 0))

    clock = FakeClock()
    scheduler = ManagerWorkerScheduler(
        [RepeatingWorker()],
        event_cooldown_seconds=10,
        global_cooldown_seconds=2,
        clock=clock,
    )
    try:
        scheduler.tick()
        first = _wait_for_drain(scheduler)
        assert [row.message for row in first] == ["安全觀察"]

        clock.value = 1.0
        scheduler.tick()
        time.sleep(0.02)
        assert scheduler.drain(now=datetime(2026, 8, 4, 12, 0)) == []

        clock.value = 11.0
        scheduler.tick()
        assert _wait_for_drain(scheduler)

        clock.value = 22.0
        scheduler.tick()
        time.sleep(0.02)
        assert scheduler.drain(quiet=True) == []
        assert _wait_for_drain(scheduler)
    finally:
        scheduler.close()

    print("BACKGROUND_MANAGER_WORKERS_OK")


if __name__ == "__main__":
    run()
