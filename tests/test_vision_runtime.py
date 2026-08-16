from __future__ import annotations

lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from shutil import copy2
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from vision_runtime import (
    OFFICIAL_MODEL_SPECS,
    VisionEnvironmentProbe,
    VisionReadiness,
    bundled_model_directory,
)

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class _CompleteOpenCVContract:
    FaceDetectorYN: object = sentinel("FaceDetectorYN")
    FaceRecognizerSF: object = sentinel("FaceRecognizerSF")


@dataclass(frozen=True, slots=True)
class _IncompleteOpenCVContract:
    FaceDetectorYN: object = sentinel("FaceDetectorYN")


def _missing_opencv() -> object:
    raise ModuleNotFoundError("No module named 'cv2'", name="cv2")


def assert_model_directory_resolves_source_and_packaged_assets() -> None:
    expected_source = ROOT / "assets" / "vision-models"
    assert bundled_model_directory() == expected_source
    assert all((expected_source / spec.filename).is_file() for spec in OFFICIAL_MODEL_SPECS)

    had_meipass = hasattr(sys, "_MEIPASS")
    previous_meipass = getattr(sys, "_MEIPASS", None)
    with TemporaryDirectory() as temporary:
        sys._MEIPASS = temporary
        try:
            assert bundled_model_directory() == Path(temporary) / "assets" / "vision-models"
        finally:
            if had_meipass:
                sys._MEIPASS = previous_meipass
            else:
                del sys._MEIPASS


def assert_engine_unavailability_fails_closed() -> None:
    with TemporaryDirectory() as temporary:
        missing = VisionEnvironmentProbe(
            Path(temporary),
            engine_loader=_missing_opencv,
        ).inspect(enabled=True, camera_available=True)
        assert missing.readiness is VisionReadiness.ENGINE_UNAVAILABLE

        incomplete = VisionEnvironmentProbe(
            Path(temporary),
            engine_loader=_IncompleteOpenCVContract,
        ).inspect(enabled=True, camera_available=True)
        assert incomplete.readiness is VisionReadiness.ENGINE_UNAVAILABLE


def run() -> None:
    assert_model_directory_resolves_source_and_packaged_assets()
    assert_engine_unavailability_fails_closed()
    with TemporaryDirectory() as temporary:
        probe = VisionEnvironmentProbe(
            Path(temporary),
            engine_loader=_CompleteOpenCVContract,
        )
        assert probe.inspect(enabled=False, camera_available=False).readiness is VisionReadiness.DISABLED
        assert probe.inspect(enabled=True, camera_available=False).readiness is VisionReadiness.CAMERA_UNAVAILABLE
        missing = probe.inspect(enabled=True, camera_available=True)
        assert missing.readiness is VisionReadiness.MODEL_MISSING
    with TemporaryDirectory() as temporary:
        model_directory = Path(temporary)
        source_directory = bundled_model_directory()
        for spec in OFFICIAL_MODEL_SPECS:
            copy2(source_directory / spec.filename, model_directory / spec.filename)
        probe = VisionEnvironmentProbe(
            model_directory,
            engine_loader=_CompleteOpenCVContract,
        )
        ready = probe.inspect(enabled=True, camera_available=True)
        assert ready.readiness is VisionReadiness.READY
        tampered_path = model_directory / OFFICIAL_MODEL_SPECS[-1].filename
        with tampered_path.open("ab") as stream:
            stream.write(b"tampered")
        untrusted = probe.inspect(enabled=True, camera_available=True)
        assert untrusted.readiness is VisionReadiness.MODEL_UNTRUSTED
        assert untrusted.detail == tampered_path.name


if __name__ == "__main__":
    run()
    print("VISION_RUNTIME_OK")
