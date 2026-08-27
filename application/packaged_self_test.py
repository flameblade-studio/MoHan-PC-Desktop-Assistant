from __future__ import annotations

lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy import sounddevice
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import QApplication, QPushButton

lazy from application.speech_performance import (
    SpeechPerformancePhase,
    SpeechPerformanceTimeline,
)
lazy from domain.constants import FLOAT_COMPARISON_EPSILON
lazy from domain.face_motion import FaceMotionController
lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from domain.text_normalizer import to_taiwan_traditional
lazy from domain.lip_sync import VisemeDynamics
lazy from infrastructure.app_resources import APP_ICON_PATH, resource_path
lazy from integrations.realtime_voice import (
    RealtimeSessionConfig,
    RealtimeVoiceClient,
)
lazy from integrations.speech import SpeechListener
lazy from presentation.pose_atlas_assets import PoseAtlasAssets

TAB_COUNT = 8
VIEW_COUNT = 24
LAYERED_HALF_BODY_LAYER_COUNT = 75
LAYERED_HALF_BODY_LAYERS_PER_POSE = 25
END_SILENCE_SECONDS = 0.85
MAX_RECORD_SECONDS = 10.0


def _visible_windows_voices(window) -> tuple[str, ...]:
    combo = window.dashboard.windows_voice
    return tuple(
        str(combo.itemData(index) or "")
        for index in range(combo.count())
    )


@dataclass(frozen=True, slots=True)
class _SelfTestCheck:
    name: str
    passed: bool


def _physics_checks(window) -> tuple[_SelfTestCheck, ...]:
    return tuple(
        _SelfTestCheck(name, passed)
        for pose in ("cheek", "lean", "front")
        for name, passed in (
            (f"visual.physics.{pose}.ornament", not window.physics_sources[pose].isNull()),
            (f"visual.physics.{pose}.face", not window.face_sources[pose].isNull()),
            (f"visual.physics.{pose}.eyes", not window.eye_sources[pose].isNull()),
            *(
                (
                    f"visual.physics.{pose}.hair.{side}",
                    not window.hair_sources[pose][side].isNull(),
                )
                for side in ("left", "right")
            ),
            *(
                (
                    f"visual.physics.{pose}.sleeve.{side}",
                    not window.sleeve_sources[pose][side].isNull(),
                )
                for side in ("left", "right")
            ),
        )
    )


def _flagship_checks(window) -> tuple[_SelfTestCheck, ...]:
    center = getattr(window.dashboard, "flagship_center", None)
    if center is None:
        return (_SelfTestCheck("flagship.center", False),)
    return (
        _SelfTestCheck("flagship.center", True),
        _SelfTestCheck("flagship.tab_count", center.tabs.count() == TAB_COUNT),
        _SelfTestCheck("flagship.remote_disabled", not center.remote_enabled.isChecked()),
        _SelfTestCheck(
            "flagship.camera_setting_boolean",
            isinstance(center.camera_enabled.isChecked(), bool),
        ),
        _SelfTestCheck("flagship.camera_closed", center.camera_presence.camera is None),
        _SelfTestCheck("flagship.remote_server_closed", center.remote_server is None),
        _SelfTestCheck("flagship.payment_handler_absent", "payment" not in center.executor.handlers),
        _SelfTestCheck("flagship.shell_handler_absent", "shell" not in center.executor.handlers),
    )


def _neutral_face_motion() -> FaceMotionFrame:
    """A neutral face frame used to exercise the layered full-body renderer."""
    return FaceMotionFrame(
        FacePose.FRONT,
        "idle",
        Viseme.CLOSED,
        MouthShape(),
        ExpressionShape(),
    )


def _pose_atlas_checks() -> tuple[_SelfTestCheck, ...]:
    root = resource_path("assets/pose-atlas/v4")
    try:
        assets = PoseAtlasAssets(root, image_size=465)
        view_ids = assets.view_ids
        # The parametric layered renderer is the sole full-body path; it needs a
        # neutral motion frame to compose each view.
        neutral = _neutral_face_motion()
        views = tuple(
            assets.resolve_static("release-self-test", view_id, neutral)
            for view_id in view_ids
        )
    except (OSError, TypeError, ValueError, KeyError):
        return (_SelfTestCheck("pose_atlas.load", False),)
    sidecars_complete = all(
        (root / f"{view_id}{suffix}").is_file()
        for view_id in view_ids
        for suffix in (".landmarks.json", ".hands.json")
    )
    return (
        _SelfTestCheck("pose_atlas.release_eligible", assets.release_eligible),
        _SelfTestCheck("pose_atlas.complete_ring", len(view_ids) == VIEW_COUNT),
        _SelfTestCheck("pose_atlas.sidecars", sidecars_complete),
        _SelfTestCheck("pose_atlas.all_views_load", all(view is not None for view in views)),
    )


def _layered_half_body_checks() -> tuple[_SelfTestCheck, ...]:
    """Verify the packaged three-pose, 25-layer portrait asset contract."""
    root = resource_path("assets/expressions/layered")
    layers = tuple(root.glob("*.png")) if root.is_dir() else ()
    return (
        _SelfTestCheck(
            "layered_half_body.layer_count",
            len(layers) == LAYERED_HALF_BODY_LAYER_COUNT,
        ),
        _SelfTestCheck(
            "layered_half_body.pose_count",
            all(
                sum(path.name.startswith(f"{pose}_") for path in layers)
                == LAYERED_HALF_BODY_LAYERS_PER_POSE
                for pose in ("front", "lean", "cheek")
            ),
        ),
    )
def _visual_checks(app: QApplication, window) -> tuple[_SelfTestCheck, ...]:
    checks = (
        _SelfTestCheck("visual.character_pixmap", window.character.pixmap() is not None),
        _SelfTestCheck(
            "visual.expression_pixmaps",
            all(not pixmap.isNull() for pixmap in window.expression_pixmaps.values()),
        ),
        *_physics_checks(window),
        *_layered_half_body_checks(),
        *_pose_atlas_checks(),
        *(
            _SelfTestCheck(f"visual.{key}", window._physics_enabled(key))
            for key in (
                "physics_sleeves",
                "physics_hair",
                "physics_ornament",
                "physics_eye_tracking",
                "physics_face_parallax",
            )
        ),
        _SelfTestCheck(
            "visual.character_opacity",
            abs(window.character_opacity.opacity() - 1.0) < FLOAT_COMPARISON_EPSILON,
        ),
        _SelfTestCheck("dashboard.tab_count", window.dashboard.tabs.count() == TAB_COUNT),
        _SelfTestCheck(
            "dashboard.no_default_buttons",
            all(
                not button.autoDefault() and not button.isDefault()
                for button in window.dashboard.findChildren(QPushButton)
            ),
        ),
        *_flagship_checks(window),
        _SelfTestCheck(
            "dashboard.not_always_on_top",
            not (window.dashboard.windowFlags() & Qt.WindowStaysOnTopHint),
        ),
        _SelfTestCheck("assets.voice_listener", resource_path("voice_listener.ps1").exists()),
        _SelfTestCheck("assets.application_icon", resource_path(APP_ICON_PATH).exists()),
        _SelfTestCheck("icons.application", not app.windowIcon().isNull()),
        _SelfTestCheck("icons.dashboard", not window.dashboard.windowIcon().isNull()),
        _SelfTestCheck("icons.tray", not window.tray.icon().isNull()),
    )
    return tuple(checks)


def _voice_checks(window, voices: tuple[str, ...]) -> tuple[_SelfTestCheck, ...]:
    dashboard = window.dashboard
    return (
        _SelfTestCheck("voice.windows_voices_present", bool(voices)),
        *_speech_runtime_checks(),
        _SelfTestCheck("voice.realtime_dependencies", RealtimeVoiceClient.dependencies_available()),
        _SelfTestCheck(
            "voice.windows_default",
            bool(voices) and str(dashboard.windows_voice.currentData() or "") == voices[0],
        ),
        _SelfTestCheck("voice.zira_excluded", all("zira" not in voice.casefold() for voice in voices)),
        _SelfTestCheck(
            "voice.transcription_model",
            dashboard.transcription_model.currentText() == SpeechListener.TRANSCRIPTION_MODEL,
        ),
        _SelfTestCheck(
            "voice.realtime_transcription_model",
            dashboard.realtime_transcription_model.currentText() == SpeechListener.TRANSCRIPTION_MODEL,
        ),
        _SelfTestCheck("voice.noise_reduction", dashboard.realtime_noise_reduction.currentData() == "near_field"),
        _SelfTestCheck(
            "voice.turn_detection",
            dashboard.realtime_turn_detection.currentData()
            in {"server_vad", "semantic_vad"},
        ),
        _SelfTestCheck("voice.hybrid_transcription", dashboard.realtime_hybrid_transcription.isChecked()),
        _SelfTestCheck("voice.windows_fallback", dashboard.windows_transcription_fallback.isChecked()),
        _SelfTestCheck("voice.end_silence", SpeechListener.END_SILENCE_SECONDS == END_SILENCE_SECONDS),
        _SelfTestCheck("voice.max_record", SpeechListener.MAX_RECORD_SECONDS == MAX_RECORD_SECONDS),
        _SelfTestCheck("voice.traditional_normalization", to_taiwan_traditional("打开软件") == "開啟軟體"),
    )


def _speech_runtime_checks() -> tuple[_SelfTestCheck, ...]:
    """Exercise packaged speech lifecycle and mouth controls without sound."""

    portaudio = Path(str(getattr(sounddevice, "_libname", "")))
    timeline = SpeechPerformanceTimeline()
    timeline.prepare("system-local")
    dynamics = VisemeDynamics()
    controller = FaceMotionController()
    maximum_aperture = 0.0
    speaking = False
    for _ in range(5):
        level = 0.65
        update = timeline.viseme(level, "A")
        speaking = speaking or (
            update is not None
            and timeline.snapshot.phase is SpeechPerformancePhase.SPEAKING
        )
        frame = controller.advance(
            dynamics.advance(level, "A"),
            pose="front",
            expression="idle_front",
        )
        maximum_aperture = max(maximum_aperture, frame.mouth.aperture)
    dynamics.reset()
    closed = controller.close(pose="front", expression="idle_front")
    return (
        _SelfTestCheck(
            "voice.portaudio_binary",
            bool(portaudio.name) and portaudio.is_file(),
        ),
        _SelfTestCheck("voice.phase_speaking", speaking),
        _SelfTestCheck("voice.mouth_parameter_nonzero", maximum_aperture > 0.0),
        _SelfTestCheck(
            "voice.mouth_parameter_returns_zero",
            closed.mouth.aperture == 0.0,
        ),
    )


def _realtime_checks() -> tuple[_SelfTestCheck, ...]:
    session = RealtimeVoiceClient._session_update_event(
        RealtimeSessionConfig(
            transcription_model=SpeechListener.TRANSCRIPTION_MODEL,
        ),
        "test",
    )["session"]
    return (
        _SelfTestCheck(
            "realtime.prompt_sanitized",
            "請使用" not in RealtimeVoiceClient._sanitize_realtime_transcription_prompt(
                SpeechListener.TRANSCRIPTION_PROMPT
            ),
        ),
        _SelfTestCheck(
            "realtime.instructions_composed",
            "好呀你說" in RealtimeVoiceClient._compose_instructions("人格", "記憶", "最近對話"),
        ),
        _SelfTestCheck(
            "realtime.response_creation_disabled",
            not session["audio"]["input"]["turn_detection"]["create_response"],
        ),
        _SelfTestCheck("realtime.transcription_disabled", session["audio"]["input"]["transcription"] is None),
    )


def _collect_checks(app: QApplication, window) -> tuple[_SelfTestCheck, ...]:
    voices = _visible_windows_voices(window)
    return (*_visual_checks(app, window), *_voice_checks(window, voices), *_realtime_checks())


def _report_failures(checks: tuple[_SelfTestCheck, ...]) -> None:
    failed = tuple(check.name for check in checks if not check.passed)
    if failed:
        sys.stderr.write("PACKAGED_SELFTEST_FAILED_CHECKS=" + ",".join(failed) + "\n")


def _write_result(path: str, passed: bool) -> None:
    if not path:
        return
    Path(path).write_text(
        "PACKAGED_SELFTEST_OK" if passed else "PACKAGED_SELFTEST_FAILED",
        encoding="utf-8",
    )


def run_packaged_self_test(
    app: QApplication,
    window,
    *,
    output_path: str = "",
) -> int:
    checks = _collect_checks(app, window)
    passed = all(check.passed for check in checks)
    _write_result(output_path, passed)
    _report_failures(checks)
    window.close()
    app.processEvents()
    return 0 if passed else 2


__all__ = ("run_packaged_self_test",)
