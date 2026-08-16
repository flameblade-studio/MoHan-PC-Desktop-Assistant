from __future__ import annotations

lazy import hashlib
lazy import sys
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from pathlib import Path


class VisionReadiness(StrEnum):
    READY = "ready"
    DISABLED = "disabled"
    CAMERA_UNAVAILABLE = "camera_unavailable"
    ENGINE_UNAVAILABLE = "engine_unavailable"
    MODEL_MISSING = "model_missing"
    MODEL_UNTRUSTED = "model_untrusted"
    RUNTIME_ERROR = "runtime_error"


@dataclass(frozen=True, slots=True)
class VisionModelSpec:
    filename: str
    sha256: str


OFFICIAL_MODEL_SPECS = (
    VisionModelSpec(
        "face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    VisionModelSpec(
        "face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
    VisionModelSpec(
        "object_detection_nanodet_2022nov.onnx",
        "4b82da9944b88577175ee23a459dce2e26e6e4be573def65b1055dc2d9720186",
    ),
)


@dataclass(frozen=True, slots=True)
class VisionHealth:
    readiness: VisionReadiness
    detail: str = ""

    @property
    def ready(self) -> bool:
        return self.readiness is VisionReadiness.READY


def _load_opencv() -> object:
    import cv2

    return cv2


class VisionEnvironmentProbe:
    """Fail-closed vision preflight that never affects non-vision features."""

    def __init__(
        self,
        model_directory: Path,
        *,
        engine_loader: Callable[[], object] = _load_opencv,
    ) -> None:
        self._model_directory = model_directory
        self._engine_loader = engine_loader

    def inspect(self, *, enabled: bool, camera_available: bool) -> VisionHealth:
        if not enabled:
            return VisionHealth(VisionReadiness.DISABLED)
        if not camera_available:
            return VisionHealth(VisionReadiness.CAMERA_UNAVAILABLE)
        engine_health = self._inspect_engine()
        if engine_health is not None:
            return engine_health
        model_health = self._inspect_models()
        return model_health or VisionHealth(VisionReadiness.READY)

    def _inspect_engine(self) -> VisionHealth | None:
        try:
            engine = self._engine_loader()
        except ImportError:
            return VisionHealth(VisionReadiness.ENGINE_UNAVAILABLE)
        if not all(
            hasattr(engine, name)
            for name in ("FaceDetectorYN", "FaceRecognizerSF")
        ):
            return VisionHealth(VisionReadiness.ENGINE_UNAVAILABLE)
        return None

    def _inspect_models(self) -> VisionHealth | None:
        for spec in OFFICIAL_MODEL_SPECS:
            model_path = self._model_directory / spec.filename
            if not model_path.is_file():
                return VisionHealth(VisionReadiness.MODEL_MISSING, spec.filename)
            if _sha256(model_path) != spec.sha256:
                return VisionHealth(VisionReadiness.MODEL_UNTRUSTED, spec.filename)
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bundled_model_directory() -> Path:
    packaged_root = getattr(sys, "_MEIPASS", None)
    root = (
        Path(packaged_root)
        if packaged_root is not None
        else Path(__file__).resolve().parents[1]
    )
    return root / "assets" / "vision-models"
