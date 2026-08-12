from __future__ import annotations

lazy import io
lazy import json
lazy import os
lazy import re
lazy import sys
lazy import tempfile
lazy from pathlib import Path
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import camera_presence
lazy from ai_client import ActionPlannerWorker
lazy from camera_presence import CameraPresenceController
lazy from service_status_localization import (
    SUPPORTED_SERVICE_LANGUAGES,
    ServiceStatus,
    service_status,
)
lazy from speech import SpeechListener, SpeechListenerProviders

HAN_TEXT = re.compile(r"[\u3400-\u9fff]")
FORMAT_VALUES = {
    "detail": "Driver 42",
    "device": "USB Camera",
    "model": "gpt-test",
    "status": 503,
    "voice": "Zira",
}


class _CapturedThread:
    def __init__(self, target, args, daemon):
        assert daemon
        self.target = target
        self.args = args

    def start(self) -> None:
        return None


class _FakeSignal:
    def __init__(self) -> None:
        self.callback = None

    def connect(self, callback) -> None:
        self.callback = callback

    def emit(self, *args) -> None:
        assert self.callback is not None
        self.callback(*args)


class _FakeDevice:
    def description(self) -> str:
        return "USB Camera"


class _FakeCamera:
    def __init__(self, _device) -> None:
        self.errorOccurred = _FakeSignal()
        self.started = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False


class _FakeCaptureSession:
    def setCamera(self, _camera) -> None:
        return None

    def setVideoSink(self, _sink) -> None:
        return None


class _FakeVideoSink:
    def __init__(self) -> None:
        self.videoFrameChanged = _FakeSignal()


class _FakeMediaDevices:
    @staticmethod
    def videoInputs() -> list[_FakeDevice]:
        return [_FakeDevice()]


def _assert_catalog_contract() -> None:
    for language in SUPPORTED_SERVICE_LANGUAGES:
        for key in ServiceStatus:
            rendered = service_status(
                language,
                key,
                **FORMAT_VALUES,
            )
            assert rendered.strip(), (language, key)
            if language == "en":
                assert not HAN_TEXT.search(rendered), (key, rendered)

    assert service_status(
        "en-US",
        ServiceStatus.CAMERA_CLOSED,
    ) == service_status("en", ServiceStatus.CAMERA_CLOSED)
    assert service_status(
        "unknown",
        ServiceStatus.CAMERA_CLOSED,
    ) == "攝影機已關閉"
    camera_error = service_status(
        "en",
        ServiceStatus.CAMERA_ERROR,
        detail="供應器原始錯誤 42",
    )
    assert camera_error.startswith("Camera error: type=unknown_error")
    assert "diagnostic=unknown_failure" in camera_error
    assert "供應器原始錯誤 42" not in camera_error


def _assert_speech_states() -> None:
    statuses: list[str] = []
    diagnostics: list[str] = []
    failures: list[str] = []
    recognized: list[str] = []
    listener = SpeechListener(
        Path("voice_listener.ps1"),
        SpeechListenerProviders(
            api_key=lambda: "sk-test",
            recognition_mode=lambda: "OpenAI",
            windows_fallback=lambda: False,
        ),
        language="en",
    )
    listener.status_changed.connect(statuses.append)
    listener.diagnostic_changed.connect(diagnostics.append)
    listener.failed.connect(failures.append)
    listener.recognized.connect(recognized.append)

    with patch("speech.threading.Thread", _CapturedThread):
        listener.listen_once()
    assert statuses[-1].startswith("Listening")

    listener._busy.clear()
    listener._recording_active.clear()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as stream:
        audio_path = Path(stream.name)
        stream.write(b"RIFF-test")
    with (
        patch.object(listener, "_record_wav", return_value=audio_path),
        patch.object(listener, "_transcribe", return_value="Provider result"),
    ):
        listener._busy.set()
        listener._listen_with_openai(
            "sk-test",
            "gpt-test",
            "en",
            "prompt",
            False,
        )
    assert recognized[-1] == "Provider result"
    assert statuses[-1] == "Recognizing…"
    assert diagnostics[-1] == "OpenAI transcription succeeded: gpt-test"

    no_key = SpeechListener(
        Path("voice_listener.ps1"),
        SpeechListenerProviders(
            api_key=lambda: "",
            recognition_mode=lambda: "OpenAI",
            windows_fallback=lambda: False,
        ),
        language="en",
    )
    no_key.failed.connect(failures.append)
    no_key.listen_once()
    assert failures[-1] == (
        "The OpenAI API key has not been configured."
        " Windows fallback recognition is currently disabled."
    )
    assert not HAN_TEXT.search(failures[-1])

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as stream:
        failed_audio = Path(stream.name)
        stream.write(b"RIFF-test")
    with (
        patch.object(listener, "_record_wav", return_value=failed_audio),
        patch.object(
            listener,
            "_transcribe",
            side_effect=RuntimeError("Provider 503"),
        ),
    ):
        listener._busy.set()
        listener._listen_with_openai(
            "sk-test",
            "gpt-test",
            "en",
            "prompt",
            False,
        )
    assert failures[-1].endswith(
        "Windows fallback recognition is currently disabled."
    )


def _assert_camera_states() -> None:
    statuses: list[str] = []
    with (
        patch.object(camera_presence, "QCamera", _FakeCamera),
        patch.object(
            camera_presence,
            "QMediaCaptureSession",
            _FakeCaptureSession,
        ),
        patch.object(camera_presence, "QVideoSink", _FakeVideoSink),
        patch.object(camera_presence, "QMediaDevices", _FakeMediaDevices),
    ):
        controller = CameraPresenceController(language="en")
        controller.status_changed.connect(statuses.append)
        controller.start()
        assert statuses[:2] == [
            "Starting camera…",
            "Camera active: USB Camera (local presence detection only)",
        ]
        controller.camera.errorOccurred.emit(0, "Driver 42")
        assert statuses[-1].startswith("Camera error: type=unknown_error")
        assert "diagnostic=unknown_failure" in statuses[-1]
        assert "Driver 42" not in statuses[-1]
        controller.stop()
        assert statuses[-1] == "Camera closed"

    with patch.object(camera_presence, "QCamera", None):
        unavailable = CameraPresenceController(language="en")
        try:
            unavailable.start()
        except RuntimeError as exc:
            assert str(exc).startswith("This package does not include")
            assert not HAN_TEXT.search(str(exc))
        else:
            raise AssertionError("missing camera component must fail closed")


def _planner_response() -> io.BytesIO:
    return io.BytesIO(
        json.dumps(
            {
                "output": [
                    {
                        "type": "function_call",
                        "name": "propose_action_plan",
                        "arguments": json.dumps(
                            {
                                "title": "Open project",
                                "steps": [],
                            }
                        ),
                    }
                ]
            }
        ).encode("utf-8")
    )


def _assert_ai_states() -> None:
    completed: list[object] = []
    worker = ActionPlannerWorker(
        "Open the project",
        api_key="sk-test",
        model="gpt-test",
        available_targets="project",
        language="en",
    )
    assert worker.waiting_status == "Planning…"
    worker.signals.done.connect(completed.append)
    with patch("ai_client.urlopen", return_value=_planner_response()):
        worker.run()
    assert completed == [{"title": "Open project", "steps": []}]

    failures: list[str] = []
    missing_key = ActionPlannerWorker(
        "Open the project",
        api_key="",
        model="gpt-test",
        available_targets="project",
        language="en",
    )
    missing_key.signals.failed.connect(failures.append)
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        missing_key.run()
    assert failures[-1].startswith("The OpenAI API key is not configured")
    assert not HAN_TEXT.search(failures[-1])


def run() -> None:
    _assert_catalog_contract()
    _assert_speech_states()
    _assert_camera_states()
    _assert_ai_states()
    print("SERVICE_STATUS_LOCALIZATION_OK")


if __name__ == "__main__":
    run()
