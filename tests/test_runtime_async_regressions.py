from __future__ import annotations

lazy import ctypes
lazy import sys
lazy import threading
lazy import time
lazy from datetime import datetime
lazy from pathlib import Path
lazy from types import SimpleNamespace
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QCoreApplication, QProcess
lazy from PySide6.QtGui import QColor, QImage

lazy from application import camera_presence, desktop_presence
lazy from application.background_agents import (
    AgentObservation,
    DiagnosticReportWorker,
    ManagerWorkerScheduler,
)
lazy from application.vision_controller import VisionController
lazy from domain.gesture_intent import NormalizedPoint
lazy from domain.vision_domain import (
    BoundingBox,
    IdentityObservation,
    IdentityState,
    SceneUnderstanding,
)
lazy from infrastructure.opencv_vision import OpenCVFrameEvidence
lazy from integrations import speech
lazy from integrations.speech import SpeechListener, SpeechListenerProviders

EXPECTED_IDLE_SECONDS = 0.075
IDLE_SECONDS_TOLERANCE = 1e-9
UNSIGNED_TICK_SIZE_BYTES = 8
EXPECTED_START_ATTEMPTS = 2
EXPECTED_START_FAILURES = 2
EXPECTED_CLEANUP_UNLINK_CALLS = 2


def _application() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


def test_cancelled_face_enrollment_drops_old_generation() -> None:
    _application()

    class MemoryIdentities:
        def __init__(self) -> None:
            self.enrollments: list[tuple[str, tuple[tuple[float, ...], ...]]] = []

        def enroll(self, name: str, samples: tuple[tuple[float, ...], ...]):
            self.enrollments.append((name, samples))
            return SimpleNamespace(succeeded=True, error_name="")

    identities = MemoryIdentities()
    controller = VisionController(identities)  # type: ignore[arg-type]
    controller._enabled = True
    try:
        controller.begin_enrollment("A")
        old_generation = controller._generation
        controller.cancel_enrollment()
        controller.begin_enrollment("B")
        controller._embedding_completed((0.0, 1.0), old_generation)
        for _ in range(5):
            controller._embedding_completed((1.0, 0.0), controller._generation)

        assert identities.enrollments == [
            ("B", ((1.0, 0.0),) * 5),
        ]
    finally:
        controller.close()


def test_camera_rgb_stride_padding_is_removed() -> None:
    image = QImage(9, 16, QImage.Format_RGB888)
    image.fill(QColor("#8090a0"))

    raw, width, height = camera_presence._transient_rgb_frame(image)

    assert (width, height) == (270, 480)
    assert len(raw) == width * height * 3


def test_get_tick_count64_is_unsigned_and_idle_delta_handles_wrap() -> None:
    tick_value = (1 << 32) + 50

    class NativeTickFunction:
        restype = None

        def __call__(self) -> int:
            if self.restype is None:
                return ctypes.c_int32(tick_value & 0xFFFFFFFF).value
            return tick_value

    tick_function = NativeTickFunction()

    class User32:
        @staticmethod
        def GetLastInputInfo(pointer) -> int:
            info = ctypes.cast(
                pointer,
                ctypes.POINTER(desktop_presence._LastInputInfo),
            ).contents
            info.dwTime = (1 << 32) - 25
            return 1

    native = SimpleNamespace(
        user32=User32(),
        kernel32=SimpleNamespace(GetTickCount64=tick_function),
    )
    with (
        patch.object(
            desktop_presence,
            "sys",
            SimpleNamespace(platform="win32"),
        ),
        patch.object(desktop_presence.ctypes, "windll", native, create=True),
    ):
        idle_seconds = desktop_presence.seconds_since_local_input()

    assert abs(idle_seconds - EXPECTED_IDLE_SECONDS) < IDLE_SECONDS_TOLERANCE
    assert tick_function.restype is not None
    assert ctypes.sizeof(tick_function.restype) == UNSIGNED_TICK_SIZE_BYTES


def test_scheduler_keeps_completed_result_until_drain() -> None:
    started = threading.Event()
    release = threading.Event()

    class Clock:
        value = 0.0

        def __call__(self) -> float:
            return self.value

    class ControlledWorker:
        worker_id = "controlled"
        interval_seconds = 1.0

        def __init__(self) -> None:
            self.calls = 0

        def poll(self):
            self.calls += 1
            if self.calls == 1:
                started.set()
                assert release.wait(1.0)
                return [AgentObservation(self.worker_id, "first", "first result")]
            return []

    clock = Clock()
    worker = ControlledWorker()
    scheduler = ManagerWorkerScheduler(
        [worker],
        event_cooldown_seconds=0,
        global_cooldown_seconds=0,
        clock=clock,
    )
    try:
        scheduler.tick()
        assert started.wait(1.0)
        release.set()
        future = scheduler._futures[worker.worker_id]
        deadline = time.monotonic() + 1.0
        while not future.done() and time.monotonic() < deadline:
            time.sleep(0.001)
        assert future.done()

        clock.value = 1.0
        scheduler.tick()
        observations = scheduler.drain(now=datetime(2026, 10, 4, 12, 0))

        assert [item.message for item in observations] == ["first result"]
    finally:
        release.set()
        scheduler.close()


def test_diagnostic_report_read_failure_retries_same_signature(tmp_path) -> None:
    report = tmp_path / "diagnostics.log"
    report.write_text("warning: retry after temporary lock\n", encoding="utf-8")
    worker = DiagnosticReportWorker(lambda: report)
    original_open = Path.open
    calls = 0

    def fail_first_open(self, *args, **kwargs):
        nonlocal calls
        if self == report and calls == 0:
            calls += 1
            raise PermissionError("temporary lock")
        return original_open(self, *args, **kwargs)

    with patch.object(Path, "open", fail_first_open):
        try:
            worker.poll()
        except PermissionError:
            pass
        observations = list(worker.poll())

    assert calls == 1
    assert len(observations) == 1
    assert observations[0].metadata["issue_lines"] == 1


class _FakeSignal:
    def __init__(self) -> None:
        self._slots = []

    def connect(self, callback) -> None:
        self._slots.append(callback)

    def emit(self, *args) -> None:
        for callback in tuple(self._slots):
            callback(*args)


class _FailedProcess:
    FailedToStart = 1
    NotRunning = 0
    starts = 0

    def __init__(self, _parent) -> None:
        self.finished = _FakeSignal()
        self.errorOccurred = _FakeSignal()

    def state(self) -> int:
        return self.NotRunning

    def start(self, _program: str, _arguments: list[str]) -> None:
        type(self).starts += 1
        self.errorOccurred.emit(self.FailedToStart)

    def deleteLater(self) -> None:
        pass

    def readAllStandardError(self) -> bytes:
        return b""


def test_failed_speech_process_start_cleans_up_and_can_retry() -> None:
    _application()
    _FailedProcess.starts = 0
    listener = SpeechListener(
        Path("voice_listener.ps1"),
        SpeechListenerProviders(
            recognition_mode=lambda: "Windows recognition",
            windows_fallback=lambda: False,
        ),
    )
    failures: list[str] = []
    listener.failed.connect(failures.append)

    with patch.object(speech, "QProcess", _FailedProcess):
        listener.listen_once()
        assert not listener.is_busy
        assert listener.process is None
        assert listener.output_path is None
        listener.listen_once()

    assert _FailedProcess.starts == EXPECTED_START_ATTEMPTS
    assert len(failures) == EXPECTED_START_FAILURES
    assert not listener.is_busy
    assert listener.process is None
    assert listener.output_path is None


def test_failed_speech_start_emits_failure_even_if_cleanup_raises() -> None:
    _application()
    listener = SpeechListener(
        Path("voice_listener.ps1"),
        SpeechListenerProviders(
            recognition_mode=lambda: "Windows recognition",
            windows_fallback=lambda: False,
        ),
    )
    failures: list[str] = []
    listener.failed.connect(failures.append)
    original_unlink = Path.unlink
    calls = 0

    def fail_during_cleanup(self, *args, **kwargs):
        nonlocal calls
        if self.name.startswith("mohan-voice-"):
            calls += 1
            if calls == EXPECTED_CLEANUP_UNLINK_CALLS:
                raise PermissionError("deterministic cleanup failure")
        return original_unlink(self, *args, **kwargs)

    with (
        patch.object(speech, "QProcess", _FailedProcess),
        patch.object(Path, "unlink", fail_during_cleanup),
    ):
        try:
            listener.listen_once()
        except PermissionError:
            pass
        else:
            raise AssertionError("cleanup failure must remain visible")

    assert calls == EXPECTED_CLEANUP_UNLINK_CALLS
    assert len(failures) == 1
    assert not listener.is_busy
    assert listener.process is None
    assert listener.output_path is None


def test_real_qprocess_failed_start_can_retry(tmp_path) -> None:
    application = _application()
    missing_executable = tmp_path / "definitely-missing-powershell.exe"

    class MissingExecutableProcess(QProcess):
        starts = 0

        def start(self, _program: str, arguments: list[str]) -> None:
            type(self).starts += 1
            super().start(str(missing_executable), arguments)

    listener = SpeechListener(
        Path("voice_listener.ps1"),
        SpeechListenerProviders(
            recognition_mode=lambda: "Windows recognition",
            windows_fallback=lambda: False,
        ),
    )
    failures: list[str] = []
    listener.failed.connect(failures.append)
    MissingExecutableProcess.starts = 0

    with patch.object(speech, "QProcess", MissingExecutableProcess):
        for expected_failures in (1, 2):
            listener.listen_once()
            deadline = time.monotonic() + 2.0
            while len(failures) < expected_failures and time.monotonic() < deadline:
                application.processEvents()
                time.sleep(0.005)
            application.processEvents()
            assert len(failures) == expected_failures
            assert not listener.is_busy
            assert listener.process is None
            assert listener.output_path is None

    assert not missing_executable.exists()
    assert MissingExecutableProcess.starts == EXPECTED_START_ATTEMPTS


def test_finished_speech_output_read_failure_still_releases_resources(
    tmp_path,
) -> None:
    _application()
    output_path = tmp_path / "speech-output.txt"
    output_path.write_text("recognized", encoding="utf-8")
    listener = SpeechListener(Path("voice_listener.ps1"))

    class FinishedProcess:
        deleted = False

        def readAllStandardError(self) -> bytes:
            return b""

        def deleteLater(self) -> None:
            self.deleted = True

    process = FinishedProcess()
    listener.process = process  # type: ignore[assignment]
    listener.output_path = output_path
    listener._busy.set()
    original_read_text = Path.read_text

    def fail_output_read(self, *args, **kwargs):
        if self == output_path:
            raise PermissionError("deterministic output read failure")
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", fail_output_read):
        try:
            listener._finished()
        except PermissionError:
            pass
        else:
            raise AssertionError("output read failure must remain visible")

    assert not listener.is_busy
    assert listener.process is None
    assert listener.output_path is None
    assert process.deleted
    assert not output_path.exists()


def test_local_vision_failures_accumulate_until_health_is_disabled() -> None:
    _application()
    identity = IdentityObservation(IdentityState.RECOGNIZED, "owner", "Owner", 0.9)
    scene = SceneUnderstanding(identity, (), (), ())
    evidence = OpenCVFrameEvidence(
        scene,
        BoundingBox(20.0, 10.0, 80.0, 90.0),
        (
            NormalizedPoint(0.35, 0.35),
            NormalizedPoint(0.65, 0.35),
            NormalizedPoint(0.50, 0.50),
            NormalizedPoint(0.40, 0.68),
            NormalizedPoint(0.60, 0.68),
        ),
    )
    controller = VisionController(SimpleNamespace())  # type: ignore[arg-type]
    controller._enabled = True
    health_events = []
    controller.health_changed.connect(health_events.append)

    def fail_local_analysis(_frame) -> None:
        raise ValueError("deterministic local pipeline failure")

    controller._local_pipeline.analyze = fail_local_analysis
    generation = controller._generation
    try:
        for expected_count in (1, 2, 3):
            controller._analysis_completed(evidence, generation)
            assert controller._consecutive_analysis_failures == expected_count

        assert not controller._enabled
        assert len(health_events) == 1
    finally:
        controller.close()
