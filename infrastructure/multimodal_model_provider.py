from __future__ import annotations

lazy import math
lazy from collections.abc import Sequence
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Any

lazy from application.multimodal_fusion_hub import (
    FaceMeshFrame,
    FaceMeshPoint,
    MultimodalFusionHub,
    VoiceActivityResult,
    VoiceActivityState,
)
lazy from infrastructure.opencv_vision import (
    OpenCVDependencyError,
    load_opencv_runtime,
)


FACE_MESH_MODEL_SIZE = 192
IRIS_MODEL_SIZE = 64
SILERO_SAMPLE_RATE = 16_000
SILERO_CHUNK_SIZE = 512
SILERO_STATE_SHAPE = (2, 1, 64)


@dataclass(frozen=True, slots=True)
class MultimodalModelPaths:
    """Canonical paths for the bundled local multimodal model set."""

    face_detector: Path
    face_mesh: Path
    iris: Path
    silero_vad: Path

    @classmethod
    def from_directory(cls, directory: Path) -> "MultimodalModelPaths":
        root = Path(directory)
        return cls(
            root / "face_detection_yunet_2023mar.onnx",
            root / "face_landmark_468.tflite",
            root / "iris_landmark.tflite",
            root / "silero_vad_v4.0.onnx",
        )

    @property
    def missing(self) -> tuple[Path, ...]:
        return tuple(
            path
            for path in (
                self.face_detector,
                self.face_mesh,
                self.iris,
                self.silero_vad,
            )
            if not path.is_file()
        )


@dataclass(frozen=True, slots=True)
class MultimodalModelCapabilities:
    face_mesh: bool
    iris: bool
    silero_vad: bool
    runtime: str = "opencv-dnn"


@dataclass(frozen=True, slots=True)
class FaceMeshInference:
    frame: FaceMeshFrame
    detector_confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.detector_confidence <= 1.0:
            raise ValueError("face detector confidence must be normalized")


class OpenCVMultiModalModelProvider:
    """Run the bundled Face Mesh, iris and Silero models through OpenCV.

    The provider accepts only transient RGB bytes and audio samples. It owns no
    camera, UI, network, persistence or action-dispatch responsibility. If the
    optional Silero inference fails at runtime, the existing RMS VAD remains the
    deliberate compatibility fallback.
    """

    def __init__(
        self,
        models: MultimodalModelPaths,
        *,
        face_confidence: float = 0.82,
        vad_threshold: float = 0.50,
    ) -> None:
        if not isinstance(models, MultimodalModelPaths):
            raise TypeError("multimodal model paths must be canonical")
        missing = models.missing
        if missing:
            raise FileNotFoundError(", ".join(str(path) for path in missing))
        if not 0.0 < face_confidence <= 1.0:
            raise ValueError("face confidence must be normalized")
        if not 0.0 < vad_threshold <= 1.0:
            raise ValueError("Silero threshold must be normalized")

        runtime = load_opencv_runtime()
        cv2 = runtime.cv2
        if not hasattr(cv2.dnn, "readNetFromTFLite"):
            raise OpenCVDependencyError(
                "OpenCV vision is missing readNetFromTFLite for bundled models."
            )

        self._cv2 = cv2
        self._np = runtime.numpy
        self._face_detector = cv2.FaceDetectorYN.create(
            str(models.face_detector),
            "",
            (320, 320),
            face_confidence,
            0.3,
            100,
        )
        self._face_mesh = cv2.dnn.readNetFromTFLite(str(models.face_mesh))
        self._iris = cv2.dnn.readNetFromTFLite(str(models.iris))
        self._silero = cv2.dnn.readNet(str(models.silero_vad))
        self._vad_threshold = vad_threshold
        self._vad_h = self._np.zeros(SILERO_STATE_SHAPE, dtype=self._np.float32)
        self._vad_c = self._np.zeros(SILERO_STATE_SHAPE, dtype=self._np.float32)
        self._fallback = _RmsFallback()

    @property
    def capabilities(self) -> MultimodalModelCapabilities:
        return MultimodalModelCapabilities(True, True, True)

    def warmup(self) -> MultimodalModelCapabilities:
        """Execute one local inference through every bundled model."""

        blank = self._np.zeros((256, 256, 3), dtype=self._np.uint8)
        blob = self._cv2.dnn.blobFromImage(
            blank,
            scalefactor=1.0 / 255.0,
            size=(FACE_MESH_MODEL_SIZE, FACE_MESH_MODEL_SIZE),
            swapRB=True,
        )
        self._face_mesh.setInput(blob)
        face_output = self._face_mesh.forward().reshape(-1)
        if face_output.size != 468 * 3:
            raise RuntimeError("bundled Face Mesh output shape is unsupported")
        iris_blob = self._cv2.dnn.blobFromImage(
            blank[:64, :64],
            scalefactor=1.0 / 255.0,
            size=(IRIS_MODEL_SIZE, IRIS_MODEL_SIZE),
            swapRB=True,
        )
        self._iris.setInput(iris_blob)
        iris_output = self._iris.forward().reshape(-1)
        if iris_output.size != 15:
            raise RuntimeError("bundled iris output shape is unsupported")
        self._silero_infer(self._np.zeros(SILERO_CHUNK_SIZE, dtype=self._np.float32))
        self.reset_voice()
        return self.capabilities

    def analyze_face(
        self,
        rgb_bytes: bytes,
        width: int,
        height: int,
    ) -> FaceMeshInference | None:
        image = self._rgb_image(rgb_bytes, width, height)
        bgr = self._cv2.cvtColor(image, self._cv2.COLOR_RGB2BGR)
        faces = self._detect_faces(bgr)
        if len(faces) != 1:
            return None
        face = faces[0]
        confidence = _clamp(float(face[14]))
        crop, left, top, side = _square_crop_from_box(
            bgr,
            float(face[0]),
            float(face[1]),
            float(face[2]),
            float(face[3]),
            margin=0.25,
        )
        landmarks = self._infer_face_mesh(crop, left, top, side, width, height)
        if landmarks is None:
            return None
        iris_landmarks = self._infer_iris_landmarks(
            bgr,
            landmarks,
            width,
            height,
        )
        complete = landmarks if iris_landmarks is None else landmarks + iris_landmarks
        return FaceMeshInference(
            FaceMeshFrame(tuple(complete)),
            confidence,
        )

    def analyze_voice(
        self,
        samples: Sequence[float] | None,
        *,
        sample_rate: int = SILERO_SAMPLE_RATE,
    ) -> VoiceActivityResult:
        if samples is None or len(samples) == 0:
            return VoiceActivityResult(VoiceActivityState.UNKNOWN, 0.0, 0.0)
        if sample_rate != SILERO_SAMPLE_RATE:
            return self._fallback.analyze(samples)
        try:
            values = tuple(float(value) for value in samples)
        except (TypeError, ValueError):
            return self._fallback.analyze(samples)
        if not values or not all(math.isfinite(value) for value in values):
            return VoiceActivityResult(VoiceActivityState.UNKNOWN, 0.0, 0.0)
        array = self._np.asarray(values, dtype=self._np.float32)
        try:
            probabilities: list[float] = []
            for offset in range(0, len(array), SILERO_CHUNK_SIZE):
                chunk = array[offset : offset + SILERO_CHUNK_SIZE]
                if len(chunk) < SILERO_CHUNK_SIZE:
                    chunk = self._np.pad(
                        chunk,
                        (0, SILERO_CHUNK_SIZE - len(chunk)),
                        mode="constant",
                    )
                probabilities.append(self._silero_infer(chunk))
        except Exception:
            self.reset_voice()
            return self._fallback.analyze(values)
        confidence = max(probabilities, default=0.0)
        state = (
            VoiceActivityState.ACTIVE
            if confidence >= self._vad_threshold
            else VoiceActivityState.SILENT
        )
        rms = math.sqrt(sum(value * value for value in values) / len(values))
        return VoiceActivityResult(state, rms, confidence)

    def reset_voice(self) -> None:
        self._vad_h[...] = 0.0
        self._vad_c[...] = 0.0

    def _detect_faces(self, image: Any) -> tuple[Any, ...]:
        height, width = image.shape[:2]
        self._face_detector.setInputSize((width, height))
        _, faces = self._face_detector.detect(image)
        if faces is None:
            return ()
        return tuple(row for row in faces if len(row) >= 15)

    def _infer_face_mesh(
        self,
        crop: Any,
        left: int,
        top: int,
        side: int,
        width: int,
        height: int,
    ) -> tuple[FaceMeshPoint, ...] | None:
        blob = self._cv2.dnn.blobFromImage(
            crop,
            scalefactor=1.0 / 255.0,
            size=(FACE_MESH_MODEL_SIZE, FACE_MESH_MODEL_SIZE),
            swapRB=True,
        )
        self._face_mesh.setInput(blob)
        output = self._face_mesh.forward().reshape(-1)
        if output.size != 468 * 3 or not self._np.isfinite(output).all():
            return None
        points: list[FaceMeshPoint] = []
        for index in range(0, output.size, 3):
            x = left + float(output[index]) * side / FACE_MESH_MODEL_SIZE
            y = top + float(output[index + 1]) * side / FACE_MESH_MODEL_SIZE
            z = float(output[index + 2]) / FACE_MESH_MODEL_SIZE
            points.append(
                FaceMeshPoint(
                    _normalized_pixel(x, width),
                    _normalized_pixel(y, height),
                    z,
                )
            )
        return tuple(points)

    def _infer_iris_landmarks(
        self,
        image: Any,
        face_landmarks: tuple[FaceMeshPoint, ...],
        width: int,
        height: int,
    ) -> tuple[FaceMeshPoint, ...] | None:
        if len(face_landmarks) != 468:
            return None
        all_iris: list[FaceMeshPoint] = []
        for eye_indices in ((33, 133, 159, 145), (263, 362, 386, 374)):
            eye_points = tuple(face_landmarks[index] for index in eye_indices)
            crop, left, top, side = _square_crop_from_points(
                image,
                eye_points,
                width,
                height,
                margin=0.55,
            )
            if crop is None:
                return None
            blob = self._cv2.dnn.blobFromImage(
                crop,
                scalefactor=1.0 / 255.0,
                size=(IRIS_MODEL_SIZE, IRIS_MODEL_SIZE),
                swapRB=True,
            )
            self._iris.setInput(blob)
            output = self._iris.forward().reshape(-1)
            if output.size != 15 or not self._np.isfinite(output).all():
                return None
            for index in range(0, output.size, 3):
                x = left + float(output[index]) * side / IRIS_MODEL_SIZE
                y = top + float(output[index + 1]) * side / IRIS_MODEL_SIZE
                z = float(output[index + 2]) / IRIS_MODEL_SIZE
                all_iris.append(
                    FaceMeshPoint(
                        _normalized_pixel(x, width),
                        _normalized_pixel(y, height),
                        z,
                    )
                )
        return tuple(all_iris)

    def _silero_infer(self, chunk: Any) -> float:
        self._silero.setInput(chunk.reshape(1, SILERO_CHUNK_SIZE), "input")
        self._silero.setInput(self._vad_h, "h")
        self._silero.setInput(self._vad_c, "c")
        self._silero.setInput(
            self._np.asarray([SILERO_SAMPLE_RATE], dtype=self._np.int64),
            "sr",
        )
        names = tuple(self._silero.getUnconnectedOutLayersNames())
        outputs = self._silero.forward(names)
        by_name = dict(zip(names, outputs, strict=False))
        probability = float(by_name["output"].reshape(-1)[0])
        self._vad_h = by_name["hn"].astype(self._np.float32, copy=True)
        self._vad_c = by_name["cn"].astype(self._np.float32, copy=True)
        return _clamp(probability)

    def _rgb_image(self, rgb_bytes: bytes, width: int, height: int) -> Any:
        if not isinstance(rgb_bytes, bytes):
            raise TypeError("multimodal frame must be RGB bytes")
        if width <= 0 or height <= 0:
            raise ValueError("multimodal frame dimensions must be positive")
        expected = width * height * 3
        if len(rgb_bytes) != expected:
            raise ValueError("multimodal frame byte length does not match dimensions")
        return self._np.frombuffer(rgb_bytes, dtype=self._np.uint8).reshape(
            height,
            width,
            3,
        )


def create_bundled_multimodal_hub(
    model_directory: Path,
    *,
    air_interactions_enabled: bool = True,
    face_mesh_enabled: bool = True,
    smoothing: float = 0.30,
) -> tuple[MultimodalFusionHub, OpenCVMultiModalModelProvider]:
    """Create the opt-in bundled provider and the canonical fusion hub together."""

    provider = OpenCVMultiModalModelProvider(
        MultimodalModelPaths.from_directory(model_directory)
    )
    hub = MultimodalFusionHub(
        air_interactions_enabled=air_interactions_enabled,
        face_mesh_enabled=face_mesh_enabled,
        smoothing=smoothing,
        voice_activity_detector=provider,
    )
    return hub, provider


class _RmsFallback:
    def analyze(self, samples: Sequence[float]) -> VoiceActivityResult:
        values = tuple(float(value) for value in samples)
        if not values or not all(math.isfinite(value) for value in values):
            return VoiceActivityResult(VoiceActivityState.UNKNOWN, 0.0, 0.0)
        rms = math.sqrt(sum(value * value for value in values) / len(values))
        threshold = 0.018
        if rms < threshold:
            return VoiceActivityResult(
                VoiceActivityState.SILENT,
                rms,
                min(1.0, rms / threshold),
            )
        return VoiceActivityResult(
            VoiceActivityState.ACTIVE,
            rms,
            min(1.0, rms / (threshold * 4.0)),
        )


def _square_crop_from_box(
    image: Any,
    left: float,
    top: float,
    box_width: float,
    box_height: float,
    *,
    margin: float,
) -> tuple[Any, int, int, int]:
    side = max(box_width, box_height) * (1.0 + margin * 2.0)
    center_x = left + box_width / 2.0
    center_y = top + box_height / 2.0
    return _square_crop(image, center_x, center_y, side)


def _square_crop_from_points(
    image: Any,
    points: tuple[FaceMeshPoint, ...],
    width: int,
    height: int,
    *,
    margin: float,
) -> tuple[Any | None, int, int, int]:
    xs = tuple(point.x * width for point in points)
    ys = tuple(point.y * height for point in points)
    side = max(max(xs) - min(xs), max(ys) - min(ys)) * (1.0 + margin * 2.0)
    if side < 2.0:
        return None, 0, 0, 0
    crop, left, top, side = _square_crop(
        image,
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        side,
    )
    if crop.size == 0:
        return None, left, top, side
    return crop, left, top, side


def _square_crop(
    image: Any,
    center_x: float,
    center_y: float,
    side: float,
) -> tuple[Any, int, int, int]:
    height, width = image.shape[:2]
    integer_side = max(2, min(int(round(side)), width, height))
    left = max(0, min(width - integer_side, int(round(center_x - integer_side / 2.0))))
    top = max(0, min(height - integer_side, int(round(center_y - integer_side / 2.0))))
    crop = image[top : top + integer_side, left : left + integer_side]
    return crop, left, top, integer_side


def _normalized_pixel(value: float, size: int) -> float:
    if size <= 0:
        raise ValueError("pixel normalization size must be positive")
    return max(0.0, min(1.0, value / size))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
