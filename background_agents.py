from __future__ import annotations

import re
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, time as clock_time
from pathlib import Path
from typing import Callable, Iterable, Protocol


@dataclass(frozen=True)
class AgentObservation:
    worker_id: str
    event_key: str
    message: str
    expression: str = "attentive_front"
    priority: int = 10
    metadata: dict[str, object] = field(default_factory=dict)


class BackgroundWorker(Protocol):
    worker_id: str
    interval_seconds: float

    def poll(self) -> Iterable[AgentObservation]: ...


def is_quiet_time(
    moment: datetime,
    start: clock_time = clock_time(22, 0),
    end: clock_time = clock_time(8, 0),
) -> bool:
    current = moment.time()
    if start == end:
        return False
    if start < end:
        return start <= current < end
    return current >= start or current < end


class ManagerWorkerScheduler:
    """Run bounded read-only workers and arbitrate their observations.

    Workers never touch the UI, expression system, or action executor.  The
    main thread drains observations and remains the only authority that may
    display a message or request an expression through the existing arbiter.
    """

    def __init__(
        self,
        workers: Iterable[BackgroundWorker],
        *,
        max_workers: int = 2,
        event_cooldown_seconds: float = 900.0,
        global_cooldown_seconds: float = 300.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._workers = {worker.worker_id: worker for worker in workers}
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, min(4, int(max_workers))),
            thread_name_prefix="mohan-background",
        )
        self._futures: dict[str, Future[list[AgentObservation]]] = {}
        self._next_due = {worker_id: 0.0 for worker_id in self._workers}
        self._last_event: dict[str, float] = {}
        self._last_delivery = float("-inf")
        self._event_cooldown = max(0.0, event_cooldown_seconds)
        self._global_cooldown = max(0.0, global_cooldown_seconds)
        self._clock = clock
        self._closed = False
        self._lock = threading.RLock()

    @staticmethod
    def _poll(worker: BackgroundWorker) -> list[AgentObservation]:
        return list(worker.poll())

    def tick(self) -> None:
        now = self._clock()
        with self._lock:
            if self._closed:
                return
            for worker_id, worker in self._workers.items():
                future = self._futures.get(worker_id)
                if future is not None and not future.done():
                    continue
                if now < self._next_due[worker_id]:
                    continue
                self._futures[worker_id] = self._executor.submit(
                    self._poll,
                    worker,
                )
                self._next_due[worker_id] = (
                    now + max(1.0, float(worker.interval_seconds))
                )

    def drain(
        self,
        *,
        now: datetime | None = None,
        quiet: bool = False,
    ) -> list[AgentObservation]:
        if quiet or (now is not None and is_quiet_time(now)):
            return []
        current = self._clock()
        candidates: list[AgentObservation] = []
        with self._lock:
            for worker_id, future in list(self._futures.items()):
                if not future.done():
                    continue
                self._futures.pop(worker_id, None)
                try:
                    candidates.extend(future.result())
                except (OSError, RuntimeError, ValueError):
                    continue
            candidates.sort(key=lambda item: (-item.priority, item.event_key))
            delivered: list[AgentObservation] = []
            for observation in candidates:
                dedupe_key = f"{observation.worker_id}:{observation.event_key}"
                if (
                    current - self._last_event.get(dedupe_key, float("-inf"))
                    < self._event_cooldown
                ):
                    continue
                if current - self._last_delivery < self._global_cooldown:
                    continue
                self._last_event[dedupe_key] = current
                self._last_delivery = current
                delivered.append(observation)
                break
            return delivered

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            for future in self._futures.values():
                future.cancel()
            self._futures.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)


class VisibleAppWorker:
    worker_id = "visible-apps"

    def __init__(
        self,
        window_provider: Callable[[], list[dict]],
        watched_apps: dict[str, tuple[str, ...]],
        interval_seconds: float = 8.0,
    ) -> None:
        self.window_provider = window_provider
        self.watched_apps = watched_apps
        self.interval_seconds = interval_seconds
        self._previous: set[str] | None = None

    def poll(self) -> Iterable[AgentObservation]:
        titles = [str(row.get("title") or "").casefold() for row in self.window_provider()]
        present = {
            display_name
            for display_name, fragments in self.watched_apps.items()
            if any(
                fragment.casefold() in title
                for fragment in fragments
                for title in titles
            )
        }
        previous = self._previous
        self._previous = present
        if previous is None:
            return ()
        launched = sorted(present - previous)
        return tuple(
            AgentObservation(
                worker_id=self.worker_id,
                event_key=f"launched:{name.casefold()}",
                message=f"主上已開啟 {name}。妾會在旁留意，不打擾您工作。",
                expression="attentive_front",
                priority=10,
                metadata={"application": name, "status": "launched"},
            )
            for name in launched
        )


class DiagnosticReportWorker:
    worker_id = "ide-diagnostics"
    _ISSUE = re.compile(r"\b(error|warning)\b|錯誤|警告", re.IGNORECASE)

    def __init__(
        self,
        report_path_provider: Callable[[], Path | None],
        interval_seconds: float = 12.0,
        max_bytes: int = 256 * 1024,
    ) -> None:
        self.report_path_provider = report_path_provider
        self.interval_seconds = interval_seconds
        self.max_bytes = max(4096, int(max_bytes))
        self._last_signature: tuple[str, int, int] | None = None

    def poll(self) -> Iterable[AgentObservation]:
        path = self.report_path_provider()
        if path is None or not path.is_file():
            return ()
        resolved = path.resolve()
        stat = resolved.stat()
        signature = (str(resolved), stat.st_mtime_ns, stat.st_size)
        if signature == self._last_signature:
            return ()
        self._last_signature = signature
        with resolved.open("rb") as handle:
            if stat.st_size > self.max_bytes:
                handle.seek(-self.max_bytes, 2)
            raw = handle.read(self.max_bytes)
        text = raw.decode("utf-8", errors="replace")
        issues = sum(bool(self._ISSUE.search(line)) for line in text.splitlines())
        if issues <= 0:
            return ()
        return (
            AgentObservation(
                worker_id=self.worker_id,
                event_key=f"changed:{resolved}",
                message=(
                    f"妾在您指定的診斷報告 {resolved.name} 中看見 "
                    f"{issues} 行錯誤或警告；只做了唯讀檢查，尚未修改任何檔案。"
                ),
                expression="attentive_front",
                priority=20,
                metadata={
                    "path": str(resolved),
                    "issue_lines": issues,
                    "read_only": True,
                },
            ),
        )
