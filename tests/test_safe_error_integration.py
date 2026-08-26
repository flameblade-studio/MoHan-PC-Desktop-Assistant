from __future__ import annotations

lazy import io
lazy import os
lazy import sys
lazy import traceback
lazy from importlib import import_module
lazy from pathlib import Path
lazy from types import SimpleNamespace
lazy from unittest.mock import patch
lazy from urllib.error import HTTPError

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application import camera_presence
lazy from application.camera_presence import CameraPresenceController
lazy from domain.safe_error import SafeDiagnostic, SafeErrorType
lazy from domain.service_status_localization import ServiceStatus, service_status
lazy from domain.speech_configuration import AZURE_SECRET_POLICY
lazy from integrations import ai_client, speech
lazy from integrations.ai_client import ActionPlannerWorker, AIWorker, AIWorkerRequest
lazy from integrations.realtime_voice import RealtimeVoiceClient
lazy from presentation import (
    companion_speech_runtime,
    dashboard_settings_persistence,
    dashboard_voice_runtime,
)
lazy from presentation.companion_window import CompanionWindow
lazy from presentation.dashboard_window import Dashboard
lazy from presentation.flagship.oauth import OAuthWorker
lazy from presentation.flagship.workflows import FlagshipWorkflowMixin

_BAIT_MARKER = "NOT" + "-A-REAL-SECRET-42"
_PRIVATE_WINDOWS_PATH = "C:" + "\\Users\\private-user\\AppData\\secret.txt"
_PRIVATE_POSIX_PATH = "/home/" + "private-user/.config/secret.json"


def _bait_detail(*, http_status: int | None = None) -> str:
    status = f"HTTP {http_status}; " if http_status is not None else ""
    return (
        status
        + "api_key="
        + _BAIT_MARKER
        + "; token="
        + _BAIT_MARKER
        + "; password="
        + _BAIT_MARKER
        + "; Authorization: Bearer "
        + _BAIT_MARKER
        + "; maintainer"
        + "@example.test; "
        + _PRIVATE_WINDOWS_PATH
        + "; "
        + _PRIVATE_POSIX_PATH
    )


_FORBIDDEN_FRAGMENTS = (
    _BAIT_MARKER,
    "api_key=",
    "token=",
    "password=",
    "bearer",
    "maintainer@example.test",
    "private-user",
    "appdata",
    ".config/secret",
)


def _assert_sanitized(
    surface: object,
    *,
    error_type: SafeErrorType | None = None,
    diagnostic: SafeDiagnostic | None = None,
    http_status: int | None = None,
) -> str:
    if isinstance(surface, BaseException):
        assert surface.__cause__ is None
        assert surface.__context__ is None
        text = "\n".join(
            (
                str(surface),
                repr(surface),
                "".join(traceback.format_exception_only(type(surface), surface)),
            )
        )
    else:
        text = str(surface)
    lowered = text.casefold()
    for forbidden in _FORBIDDEN_FRAGMENTS:
        assert forbidden.casefold() not in lowered, (
            f"untrusted error detail escaped into the UI: {forbidden!r}"
        )
    if error_type is not None:
        assert error_type.value in lowered
    if diagnostic is not None:
        assert diagnostic.value in lowered
    if http_status is not None:
        assert str(http_status) in text
    return text


class _SignalRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def __call__(self, *values: object) -> None:
        self.calls.append(values)

    def single(self) -> tuple[object, ...]:
        assert len(self.calls) == 1
        return self.calls[0]


def _http_error(status: int) -> HTTPError:
    detail = _bait_detail(http_status=status)
    return HTTPError(
        "https://example.test/private?token=" + _BAIT_MARKER,
        status,
        detail,
        None,
        io.BytesIO(detail.encode("utf-8")),
    )


def _assert_openai_transcription_http_error() -> None:
    cases = (
        (418, SafeDiagnostic.INVALID_INPUT),
        (422, SafeDiagnostic.INVALID_INPUT),
        (599, SafeDiagnostic.REMOTE_SERVICE_FAILURE),
    )
    for status, diagnostic in cases:
        error = _http_error(status)
        reported: RuntimeError | None = None
        with patch.object(speech, "urlopen", side_effect=error):
            try:
                speech.transcribe_wav_bytes(
                    b"RIFF",
                    _BAIT_MARKER,
                    "gpt-4o-mini-transcribe",
                    speech.SpeechTranscriptionLocale(
                        provider_language="zh",
                        ui_language="en",
                    ),
                )
            except RuntimeError as exc:
                reported = exc
            else:
                raise AssertionError("the mocked HTTP failure must be reported")
        assert reported is not None
        surface = _assert_sanitized(
            reported,
            error_type=SafeErrorType.HTTP_ERROR,
            diagnostic=diagnostic,
            http_status=status,
        )
        assert "OpenAI" in surface


def _assert_realtime_error_boundaries() -> None:
    detail = _bait_detail(http_status=502)
    friendly = RealtimeVoiceClient._friendly_error(
        detail,
        "gpt-realtime-2.1-mini",
        "en",
    )
    _assert_sanitized(
        friendly,
        error_type=SafeErrorType.HTTP_ERROR,
        diagnostic=SafeDiagnostic.REMOTE_SERVICE_FAILURE,
        http_status=502,
    )

    audio = RealtimeVoiceClient._audio_error_message(
        RuntimeError("RawInputStream failed; " + detail),
        "en",
    )
    _assert_sanitized(
        audio,
        error_type=SafeErrorType.HTTP_ERROR,
        diagnostic=SafeDiagnostic.REMOTE_SERVICE_FAILURE,
        http_status=502,
    )


class _FailingOAuthFlow:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def authorize(self) -> dict[str, object]:
        raise RuntimeError(_bait_detail(http_status=401))


def _assert_oauth_worker_boundary() -> None:
    worker = OAuthWorker(
        "google",
        "client-id",
        "client-secret",
        ["openid"],
    )
    failed = _SignalRecorder()
    worker.signals.failed.connect(failed)
    with patch.object(OAuthWorker, "flow_factory", _FailingOAuthFlow):
        worker.run()
    provider_id, message = failed.single()
    assert provider_id == "google"
    _assert_sanitized(
        message,
        error_type=SafeErrorType.HTTP_ERROR,
        diagnostic=SafeDiagnostic.AUTHENTICATION_REQUIRED,
        http_status=401,
    )


class _FakeSignal:
    def __init__(self) -> None:
        self._callback = None

    def connect(self, callback) -> None:
        self._callback = callback

    def disconnect(self, callback) -> None:
        assert self._callback is None or self._callback == callback
        self._callback = None

    def emit(self, *values: object) -> None:
        assert self._callback is not None
        self._callback(*values)


class _FakeCamera:
    def deleteLater(self) -> None:
        return None

    def __init__(self, _device: object) -> None:
        self.errorOccurred = _FakeSignal()

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


class _FakeCaptureSession:
    def deleteLater(self) -> None:
        return None

    def setCamera(self, _camera: object) -> None:
        return None

    def setVideoSink(self, _sink: object) -> None:
        return None


class _FakeVideoSink:
    def deleteLater(self) -> None:
        return None

    def __init__(self) -> None:
        self.videoFrameChanged = _FakeSignal()


class _FakeDevice:
    def description(self) -> str:
        return "USB Camera"


class _FakeMediaDevices:
    @staticmethod
    def videoInputs() -> list[_FakeDevice]:
        return [_FakeDevice()]


def _assert_camera_error_boundary() -> None:
    with (
        patch.object(camera_presence, "QCamera", _FakeCamera),
        patch.object(
            camera_presence,
            "QMediaCaptureSession",
            _FakeCaptureSession,
        ),
        patch.object(camera_presence, "QVideoSink", _FakeVideoSink),
        patch.object(
            camera_presence,
            "QMediaDevices",
            _FakeMediaDevices,
        ),
    ):
        controller = CameraPresenceController(language="en")
        status = _SignalRecorder()
        controller.status_changed.connect(status)
        controller.start()
        controller.camera.errorOccurred.emit(0, _bait_detail())
        message = status.calls[-1][0]
    _assert_sanitized(
        message,
        error_type=SafeErrorType.UNKNOWN_ERROR,
        diagnostic=SafeDiagnostic.UNKNOWN_FAILURE,
    )


def _assert_ai_worker_boundaries() -> None:
    request = AIWorkerRequest(
        user_text="hello",
        mode="companion",
        api_key=_BAIT_MARKER,
        response_language="en",
    )
    worker = AIWorker(request)
    failed = _SignalRecorder()
    worker.signals.failed.connect(failed)
    with patch.object(ai_client, "urlopen", side_effect=_http_error(503)):
        worker.run()
    message, = failed.single()
    _assert_sanitized(
        message,
        error_type=SafeErrorType.HTTP_ERROR,
        diagnostic=SafeDiagnostic.REMOTE_SERVICE_FAILURE,
        http_status=503,
    )

    planner = ActionPlannerWorker(
        "open the dashboard",
        api_key=_BAIT_MARKER,
        model="gpt-test",
        available_targets="dashboard",
        language="en",
    )
    planner_failed = _SignalRecorder()
    planner.signals.failed.connect(planner_failed)
    with patch.object(ai_client, "urlopen", side_effect=_http_error(403)):
        planner.run()
    planner_message, = planner_failed.single()
    _assert_sanitized(
        planner_message,
        error_type=SafeErrorType.HTTP_ERROR,
        diagnostic=SafeDiagnostic.ACCESS_DENIED,
        http_status=403,
    )


class _FakeDashboard:
    def __init__(self) -> None:
        self.api_statuses: list[str] = []
        self.realtime_statuses: list[tuple[str, bool | None]] = []

    def set_api_status(self, status: str) -> None:
        self.api_statuses.append(status)

    def set_realtime_status(
        self,
        status: str,
        active: bool | None = None,
    ) -> None:
        self.realtime_statuses.append((status, active))


def _assert_dashboard_and_online_voice_boundaries() -> None:
    dashboard = _FakeDashboard()
    credentials = SimpleNamespace(
        azure_region="eastasia",
    )
    platform = SimpleNamespace(
        capabilities=SimpleNamespace(display_name="Windows")
    )
    fake = SimpleNamespace(
        dashboard=dashboard,
        db=SimpleNamespace(setting=lambda _key, default=None: default),
        platform_services=platform,
        speech_fallback_attempts=set(),
        speech_playing=False,
        active_speech_engine="",
        active_speech_text="",
        cloud_fallback_active=False,
        _speech_credentials=lambda: credentials,
        _configured_speech_providers=lambda _credentials: (),
        _speech_audio_finished=lambda: None,
    )
    CompanionWindow._online_voice_failed(
        fake,
        "openai-speech",
        "OpenAI voice",
        _bait_detail(http_status=429),
    )
    assert len(dashboard.api_statuses) == 1
    _assert_sanitized(
        dashboard.api_statuses[0],
        error_type=SafeErrorType.HTTP_ERROR,
        diagnostic=SafeDiagnostic.RATE_LIMITED,
        http_status=429,
    )

    realtime_fake = SimpleNamespace(
        dashboard=dashboard,
        db=SimpleNamespace(setting=lambda _key, default=None: default),
        realtime=SimpleNamespace(running=False),
        _stop_realtime_output=lambda: None,
    )
    warning = _SignalRecorder()
    with patch.object(
        companion_speech_runtime,
        "QMessageBox",
        SimpleNamespace(warning=warning),
    ):
        CompanionWindow._realtime_failed(
            realtime_fake,
            _bait_detail(http_status=504),
        )
    assert len(dashboard.realtime_statuses) == 1
    realtime_status, active = dashboard.realtime_statuses[0]
    assert active is False
    _assert_sanitized(
        realtime_status,
        error_type=SafeErrorType.HTTP_ERROR,
        diagnostic=SafeDiagnostic.REQUEST_TIMEOUT,
        http_status=504,
    )
    _parent, _title, warning_message = warning.single()
    _assert_sanitized(
        warning_message,
        error_type=SafeErrorType.HTTP_ERROR,
        diagnostic=SafeDiagnostic.REQUEST_TIMEOUT,
        http_status=504,
    )


def _assert_generic_service_status_boundary() -> None:
    camera = service_status(
        "en",
        ServiceStatus.CAMERA_ERROR,
        detail=_bait_detail(),
    )
    _assert_sanitized(
        camera,
        error_type=SafeErrorType.UNKNOWN_ERROR,
        diagnostic=SafeDiagnostic.UNKNOWN_FAILURE,
    )

    connection = service_status(
        "en",
        ServiceStatus.SPEECH_OPENAI_CONNECTION_ERROR,
        detail=_bait_detail(),
    )
    _assert_sanitized(
        connection,
        error_type=SafeErrorType.UNKNOWN_ERROR,
        diagnostic=SafeDiagnostic.UNKNOWN_FAILURE,
    )


def _assert_settings_error_boundaries() -> None:
    class FailingSecretStore:
        def save(self, _value: str) -> None:
            raise OSError(_bait_detail())

    key_input = SimpleNamespace(text=lambda: _BAIT_MARKER)
    fake = SimpleNamespace(
        ui_language="en",
        _t=lambda _key, fallback, **values: fallback.format(**values),
    )
    warning = _SignalRecorder()
    with patch.object(
        dashboard_voice_runtime,
        "QMessageBox",
        SimpleNamespace(warning=warning),
    ):
        saved = Dashboard._persist_secret_input(
            fake,
            key_input,
            FailingSecretStore(),
            AZURE_SECRET_POLICY,
            silent=False,
        )
    assert saved is False
    _parent, _title, message = warning.single()
    _assert_sanitized(
        message,
        error_type=SafeErrorType.OPERATING_SYSTEM_ERROR,
        diagnostic=SafeDiagnostic.LOCAL_IO_FAILURE,
    )


def _assert_workflow_validation_boundaries() -> None:
    warning = _SignalRecorder()
    center = SimpleNamespace(
        language="en",
        _t=lambda source, **_values: source,
    )
    invalid_workflow = SimpleNamespace(
        require_preview=False,
        to_plan=lambda: (_ for _ in ()).throw(
            ValueError(_bait_detail())
        ),
    )
    workflow_module = import_module("presentation.flagship.workflows")
    with patch.object(
        workflow_module,
        "QMessageBox",
        SimpleNamespace(warning=warning),
    ):
        FlagshipWorkflowMixin.run_workflow(
            center,
            invalid_workflow,
        )
    _parent, _title, message = warning.single()
    _assert_sanitized(
        message,
        error_type=SafeErrorType.VALIDATION_ERROR,
        diagnostic=SafeDiagnostic.INVALID_INPUT,
    )

    warning = _SignalRecorder()
    fake = SimpleNamespace(
        ui_language="en",
        autostart=SimpleNamespace(isChecked=lambda: True),
        platform_services=SimpleNamespace(
            capabilities=SimpleNamespace(desktop_autostart=True)
        ),
        db=SimpleNamespace(set_setting=lambda *_args: None),
        _settings_text=lambda _key, **values: values.get("reason", "title"),
    )
    def failing_autostart(*_args: object) -> None:
        raise OSError(_bait_detail())

    fake.autostart_configurator = failing_autostart
    with patch.object(
        dashboard_settings_persistence,
        "QMessageBox",
        SimpleNamespace(warning=warning),
    ):
        Dashboard._save_autostart_setting(fake)
    _parent, _title, message = warning.single()
    _assert_sanitized(
        message,
        error_type=SafeErrorType.OPERATING_SYSTEM_ERROR,
        diagnostic=SafeDiagnostic.LOCAL_IO_FAILURE,
    )


def run() -> None:
    _assert_openai_transcription_http_error()
    _assert_realtime_error_boundaries()
    _assert_oauth_worker_boundary()
    _assert_camera_error_boundary()
    _assert_ai_worker_boundaries()
    _assert_dashboard_and_online_voice_boundaries()
    _assert_generic_service_status_boundary()
    _assert_settings_error_boundaries()
    _assert_workflow_validation_boundaries()
    print("SAFE_ERROR_INTEGRATION_OK")


if __name__ == "__main__":
    run()
