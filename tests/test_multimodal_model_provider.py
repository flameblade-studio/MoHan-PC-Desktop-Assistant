from __future__ import annotations

lazy import hashlib
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from application.multimodal_fusion_hub import (
    MultimodalFusionHub,
    VoiceActivityResult,
    VoiceActivityState,
)
lazy from infrastructure.multimodal_model_provider import (
    MultimodalModelPaths,
    OpenCVMultiModalModelProvider,
)
lazy from presentation.companion_core import CompanionCoreMixin

MODEL_EXPECTATIONS = {
    "face_landmark_468.tflite": (
        1_242_398,
        "1055cb9d4a9ca8b8c688902a3a5194311138ba256bcc94e336d8373a5f30c814",
    ),
    "iris_landmark.tflite": (
        2_640_568,
        "d1744d2a09c25f501d39eba4faff47e53ecca8852c5ce19bce8eeac39357521f",
    ),
    "silero_vad_v4.0.onnx": (
        1_807_522,
        "a35ebf52fd3ce5f1469b2a36158dba761bc47b973ea3382b3186ca15b1f5af28",
    ),
}


def assert_bundled_model_files_are_intact() -> None:
    model_directory = ROOT / "assets" / "vision-models"
    for filename, (size, expected_hash) in MODEL_EXPECTATIONS.items():
        path = model_directory / filename
        assert path.is_file(), filename
        content = path.read_bytes()
        assert len(content) == size
        assert hashlib.sha256(content).hexdigest() == expected_hash
    assert not (model_directory / "silero_vad_v6.2.1.onnx").exists()


def assert_all_bundled_models_load_and_warm_up() -> None:
    provider = OpenCVMultiModalModelProvider(
        MultimodalModelPaths.from_directory(
            ROOT / "assets" / "vision-models"
        )
    )
    capabilities = provider.warmup()
    assert capabilities.face_mesh
    assert capabilities.iris
    assert capabilities.silero_vad
    assert capabilities.runtime == "opencv-dnn"


def assert_face_and_voice_paths_fail_safe() -> None:
    provider = OpenCVMultiModalModelProvider(
        MultimodalModelPaths.from_directory(
            ROOT / "assets" / "vision-models"
        )
    )
    blank = bytes(320 * 240 * 3)
    assert provider.analyze_face(blank, 320, 240) is None
    silent = provider.analyze_voice((0.0,) * 512)
    assert silent.state in {
        VoiceActivityState.SILENT,
        VoiceActivityState.ACTIVE,
    }
    assert 0.0 <= silent.confidence <= 1.0
    assert silent.rms == 0.0
    provider.reset_voice()


def assert_runtime_vad_fault_is_marked_and_notified_once() -> None:
    provider = OpenCVMultiModalModelProvider(
        MultimodalModelPaths.from_directory(
            ROOT / "assets" / "vision-models"
        )
    )
    samples = (0.10, -0.10) * 256

    healthy = provider.analyze_voice(samples)
    healthy_legacy_shape = VoiceActivityResult(
        healthy.state,
        healthy.rms,
        healthy.confidence,
    )
    assert healthy == healthy_legacy_shape
    assert healthy.degraded is False

    def fail_silero(_chunk) -> float:
        raise RuntimeError("simulated silero runtime fault")

    provider._silero_infer = fail_silero
    degraded = provider.analyze_voice(samples)
    assert degraded.degraded is True
    assert degraded.rms > 0.0
    assert degraded.state is VoiceActivityState.ACTIVE

    class StatusDashboard:
        def __init__(self) -> None:
            self.messages: list[str] = []

        def _t(self, _key: str, fallback: str) -> str:
            return fallback

        def set_voice_phase(self, message: str) -> None:
            self.messages.append(message)

    core = object.__new__(CompanionCoreMixin)
    dashboard = StatusDashboard()
    core.dashboard = dashboard
    degraded_result = VoiceActivityResult(
        VoiceActivityState.ACTIVE,
        degraded.rms,
        degraded.confidence,
        True,
    )
    core._notify_vad_degradation(degraded_result)
    core._notify_vad_degradation(degraded_result)
    assert dashboard.messages == ["語音偵測已降級，改用 RMS。"]
    core._notify_vad_degradation(
        VoiceActivityResult(
            VoiceActivityState.ACTIVE,
            healthy.rms,
            healthy.confidence,
        )
    )
    core._notify_vad_degradation(degraded_result)
    assert dashboard.messages == [
        "語音偵測已降級，改用 RMS。",
        "語音偵測已降級，改用 RMS。",
    ]


def assert_provider_can_drive_the_canonical_hub() -> None:
    provider = OpenCVMultiModalModelProvider(
        MultimodalModelPaths.from_directory(
            ROOT / "assets" / "vision-models"
        )
    )
    hub = MultimodalFusionHub(voice_activity_detector=provider)
    result = hub.process(
        1.0,
        audio_samples=(0.0,) * 512,
        user_speech_text="test",
        language="en-US",
    )
    assert result.voice.state in {
        VoiceActivityState.SILENT,
        VoiceActivityState.ACTIVE,
    }
    assert result.llm_ready_prompt is not None
    hub.reset()


def assert_missing_model_paths_are_rejected() -> None:
    missing = MultimodalModelPaths.from_directory(ROOT / "missing-models")
    try:
        OpenCVMultiModalModelProvider(missing)
    except FileNotFoundError as error:
        assert "face_landmark_468.tflite" in str(error)
    else:
        raise AssertionError("missing multimodal models must fail closed")


def run() -> None:
    assert_bundled_model_files_are_intact()
    assert_all_bundled_models_load_and_warm_up()
    assert_face_and_voice_paths_fail_safe()
    assert_runtime_vad_fault_is_marked_and_notified_once()
    assert_provider_can_drive_the_canonical_hub()
    assert_missing_model_paths_are_rejected()
    print("MULTIMODAL_MODEL_PROVIDER_OK")


if __name__ == "__main__":
    run()
