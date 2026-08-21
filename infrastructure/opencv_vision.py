from __future__ import annotations

lazy import importlib
lazy import math
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Any

lazy from domain.gesture_intent import LipRegion, NormalizedPoint
lazy from domain.scene_semantics import LocalSceneInterpreter
lazy from domain.vision_domain import (
    BoundingBox,
    IdentityObservation,
    IdentityState,
    ObjectDetection,
    SceneUnderstanding,
)
lazy from infrastructure.face_identity_store import FaceIdentityStore

COCO_LABELS = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
)

YUNET_POINT_COUNT = 5
YUNET_MIN_VALUES = 14
MAX_DETECTION_CANDIDATES = 1000
TWO_DIMENSIONAL = 2
THREE_DIMENSIONAL = 3


class OpenCVDependencyError(RuntimeError):
    """The installed OpenCV runtime cannot satisfy the vision adapter contract."""


@dataclass(frozen=True, slots=True)
class OpenCVRuntime:
    cv2: Any
    numpy: Any


def load_opencv_runtime(
    importer: Callable[[str], Any] | None = None,
) -> OpenCVRuntime:
    """Load and validate native dependencies at the OpenCV adapter boundary."""

    load = importer or importlib.import_module
    try:
        cv2 = load("cv2")
        np = load("numpy")
    except ImportError as exc:
        raise OpenCVDependencyError(
            "OpenCV vision is unavailable; install the pinned runtime dependencies."
        ) from exc

    missing = [
        name
        for name in (
            "FaceDetectorYN",
            "FaceRecognizerSF",
            "cvtColor",
            "resize",
            "COLOR_RGB2BGR",
        )
        if not hasattr(cv2, name)
    ]
    dnn = getattr(cv2, "dnn", None)
    missing.extend(
        f"dnn.{name}"
        for name in ("readNet", "NMSBoxes", "blobFromImage")
        if dnn is None or not hasattr(dnn, name)
    )
    if missing:
        raise OpenCVDependencyError(
            "OpenCV vision is incompatible; missing APIs: " + ", ".join(missing)
        )
    return OpenCVRuntime(cv2=cv2, numpy=np)


@dataclass(frozen=True, slots=True)
class VisionModelPaths:
    face_detector: Path
    face_recognizer: Path
    object_detector: Path

    @property
    def missing(self) -> tuple[Path, ...]:
        return tuple(
            path
            for path in (self.face_detector, self.face_recognizer, self.object_detector)
            if not path.is_file()
        )


@dataclass(frozen=True, slots=True)
class OpenCVFrameEvidence:
    """Typed local evidence from one frame; no camera or pipeline state."""

    scene: SceneUnderstanding
    face_box: BoundingBox | None
    sparse_face_landmarks: tuple[NormalizedPoint, ...] | None
    lip_region: LipRegion | None = None

    def __post_init__(self) -> None:
        if self.sparse_face_landmarks is not None and len(self.sparse_face_landmarks) != YUNET_POINT_COUNT:
            raise ValueError("YuNet sparse evidence must contain exactly five points.")
        if self.lip_region is not None and self.sparse_face_landmarks is None:
            raise ValueError("Lip evidence requires one detected face.")


class OpenCVVisionProvider:
    """Local OpenCV adapter. Import and model loading happen only when enabled."""

    def __init__(self, models: VisionModelPaths, identities: FaceIdentityStore) -> None:
        missing = models.missing
        if missing:
            raise FileNotFoundError(", ".join(str(path) for path in missing))
        runtime = load_opencv_runtime()
        cv2 = runtime.cv2
        np = runtime.numpy

        self._cv2 = cv2
        self._np = np
        self._face_detector = cv2.FaceDetectorYN.create(
            str(models.face_detector), "", (320, 320), 0.82, 0.3, 100
        )
        self._face_recognizer = cv2.FaceRecognizerSF.create(
            str(models.face_recognizer), ""
        )
        self._object_net = cv2.dnn.readNet(str(models.object_detector))
        self._nanodet = NanoDetDecoder(cv2, np)
        self._identities = identities
        self._semantics = LocalSceneInterpreter()

    def analyze(self, rgb_bytes: bytes, width: int, height: int) -> SceneUnderstanding:
        return self.analyze_frame(rgb_bytes, width, height).scene

    def analyze_frame(
        self,
        rgb_bytes: bytes,
        width: int,
        height: int,
    ) -> OpenCVFrameEvidence:
        image = self._np.frombuffer(rgb_bytes, dtype=self._np.uint8).reshape(height, width, 3)
        bgr = self._cv2.cvtColor(image, self._cv2.COLOR_RGB2BGR)
        faces = self._faces(bgr)
        identity = self._identify_from_faces(bgr, faces)
        detections = self._detect_objects(bgr)
        scene = self._semantics.interpret(identity, detections)
        if len(faces) != 1:
            return OpenCVFrameEvidence(scene, None, None)
        face_box, landmarks = yunet_single_face_geometry(faces[0], width, height)
        return OpenCVFrameEvidence(
            scene,
            face_box,
            landmarks,
            yunet_lip_region(face_box, landmarks, width, height),
        )

    def face_embedding(self, rgb_bytes: bytes, width: int, height: int) -> tuple[float, ...] | None:
        image = self._np.frombuffer(rgb_bytes, dtype=self._np.uint8).reshape(height, width, 3)
        bgr = self._cv2.cvtColor(image, self._cv2.COLOR_RGB2BGR)
        faces = self._faces(bgr)
        if len(faces) != 1:
            return None
        aligned = self._face_recognizer.alignCrop(bgr, faces[0])
        feature = self._face_recognizer.feature(aligned).flatten()
        return tuple(float(value) for value in feature)

    def _identify(self, image: Any) -> IdentityObservation:
        faces = self._faces(image)
        return self._identify_from_faces(image, faces)

    def _identify_from_faces(
        self,
        image: Any,
        faces: tuple[Any, ...],
    ) -> IdentityObservation:
        if not faces:
            return IdentityObservation(IdentityState.NO_FACE)
        if len(faces) != 1:
            return IdentityObservation(IdentityState.UNKNOWN)
        aligned = self._face_recognizer.alignCrop(image, faces[0])
        feature = self._face_recognizer.feature(aligned).flatten()
        return self._identities.identify(tuple(float(value) for value in feature))

    def _faces(self, image: Any) -> tuple[Any, ...]:
        height, width = image.shape[:2]
        self._face_detector.setInputSize((width, height))
        _, faces = self._face_detector.detect(image)
        return () if faces is None else tuple(faces)

    def _detect_objects(self, image: Any) -> tuple[ObjectDetection, ...]:
        resized = self._cv2.resize(image, (416, 416)).astype(self._np.float32)
        normalized = (resized - self._nanodet.mean) / self._nanodet.std
        blob = self._cv2.dnn.blobFromImage(normalized)
        self._object_net.setInput(blob)
        # NanoDet post-processing is intentionally isolated and validated separately;
        # an unknown output shape fails closed instead of inventing detections.
        outputs = self._object_net.forward(self._object_net.getUnconnectedOutLayersNames())
        return self._nanodet.decode(outputs, image.shape[1], image.shape[0])


def yunet_single_face_geometry(
    face: Any,
    width: int,
    height: int,
) -> tuple[BoundingBox, tuple[NormalizedPoint, ...]]:
    """Convert one YuNet row into pixel bounds and five normalized points."""

    if width <= 0 or height <= 0:
        raise ValueError("source dimensions must be positive")
    values = tuple(float(value) for value in face)
    if len(values) < YUNET_MIN_VALUES or not all(math.isfinite(value) for value in values):
        raise ValueError("invalid YuNet face evidence")
    left, top, box_width, box_height = values[:4]
    if box_width <= 0.0 or box_height <= 0.0:
        raise ValueError("invalid YuNet face bounds")
    box = BoundingBox(
        max(0.0, min(float(width), left)),
        max(0.0, min(float(height), top)),
        max(0.0, min(float(width), left + box_width)),
        max(0.0, min(float(height), top + box_height)),
    )
    landmarks = tuple(
        NormalizedPoint(
            max(0.0, min(1.0, values[index] / width)),
            max(0.0, min(1.0, values[index + 1] / height)),
        )
        for index in range(4, 14, 2)
    )
    return box, landmarks


def yunet_lip_region(
    face_box: BoundingBox,
    landmarks: tuple[NormalizedPoint, ...],
    width: int,
    height: int,
) -> LipRegion:
    """Derive a conservative touch target from YuNet's two mouth corners."""

    if len(landmarks) != YUNET_POINT_COUNT or width <= 0 or height <= 0:
        raise ValueError("invalid YuNet lip evidence")
    left, right = landmarks[3:5]
    mouth_width = left.distance_to(right)
    normalized_face_height = max(
        1.0 / height,
        (face_box.bottom - face_box.top) / height,
    )
    if mouth_width <= 0.0:
        raise ValueError("invalid YuNet mouth width")
    center = NormalizedPoint(
        (left.x + right.x) / 2.0,
        (left.y + right.y) / 2.0,
    )
    return LipRegion(
        center,
        min(1.0, max(mouth_width * 1.8, 2.0 / width)),
        min(1.0, max(normalized_face_height * 0.16, 2.0 / height)),
    )


class NanoDetDecoder:
    """Decode OpenCV Zoo NanoDet output without owning model or camera state."""

    def __init__(self, cv2: Any, np: Any) -> None:
        self._cv2 = cv2
        self._np = np
        self._strides = (8, 16, 32)
        self._reg_max = 7
        self._project = np.arange(self._reg_max + 1)
        self.mean = np.array([103.53, 116.28, 123.675], dtype=np.float32).reshape(1, 1, 3)
        self.std = np.array([57.375, 57.12, 58.395], dtype=np.float32).reshape(1, 1, 3)
        self._anchors = tuple(self._anchors_for(stride) for stride in self._strides)

    def decode(
        self,
        outputs: Any,
        source_width: int,
        source_height: int,
    ) -> tuple[ObjectDetection, ...]:
        if source_width <= 0 or source_height <= 0:
            raise ValueError("source dimensions must be positive")
        class_scores, box_predictions = self._split_outputs(outputs)
        boxes: list[Any] = []
        scores: list[Any] = []
        for stride, class_score, box_prediction, anchors in zip(
            self._strides,
            class_scores,
            box_predictions,
            self._anchors,
            strict=True,
        ):
            layer_boxes, layer_scores = self._decode_layer(
                stride,
                class_score,
                box_prediction,
                anchors,
            )
            boxes.append(layer_boxes)
            scores.append(layer_scores)
        return self._select_detections(boxes, scores, source_width, source_height)

    def _decode_layer(
        self,
        stride: int,
        class_score: Any,
        box_prediction: Any,
        anchors: Any,
    ) -> tuple[Any, Any]:
        class_score = self._squeeze(class_score)
        box_prediction = self._squeeze(box_prediction)
        if (
            class_score.ndim != TWO_DIMENSIONAL
            or box_prediction.ndim != TWO_DIMENSIONAL
            or class_score.shape[0] != anchors.shape[0]
            or box_prediction.shape != (anchors.shape[0], 4 * (self._reg_max + 1))
        ):
            raise ValueError("unsupported NanoDet output shape")
        if not (
            self._np.isfinite(class_score).all()
            and self._np.isfinite(box_prediction).all()
        ):
            raise ValueError("NanoDet output contains non-finite values")
        probabilities = self._softmax(box_prediction.reshape(-1, self._reg_max + 1))
        distances = (probabilities @ self._project).reshape(-1, 4) * stride
        if class_score.shape[0] > MAX_DETECTION_CANDIDATES:
            selected = class_score.max(axis=1).argsort()[::-1][:MAX_DETECTION_CANDIDATES]
            class_score = class_score[selected]
            distances = distances[selected]
            anchors = anchors[selected]
        coordinates = (
            self._np.clip(anchors[:, 0] - distances[:, 0], 0, 416),
            self._np.clip(anchors[:, 1] - distances[:, 1], 0, 416),
            self._np.clip(anchors[:, 0] + distances[:, 2], 0, 416),
            self._np.clip(anchors[:, 1] + distances[:, 3], 0, 416),
        )
        return self._np.column_stack(coordinates), class_score

    def _select_detections(
        self,
        boxes: list[Any],
        scores: list[Any],
        source_width: int,
        source_height: int,
    ) -> tuple[ObjectDetection, ...]:
        all_boxes = self._np.concatenate(boxes, axis=0)
        all_scores = self._np.concatenate(scores, axis=0)
        class_ids = self._np.argmax(all_scores, axis=1)
        confidences = self._np.max(all_scores, axis=1)
        boxes_xywh = all_boxes.copy()
        boxes_xywh[:, 2:4] -= boxes_xywh[:, 0:2]
        indices = self._cv2.dnn.NMSBoxes(
            boxes_xywh.tolist(), confidences.tolist(), 0.35, 0.6
        )
        scale_x = source_width / 416.0
        scale_y = source_height / 416.0
        return tuple(
            ObjectDetection(
                COCO_LABELS[int(class_ids[index])],
                float(confidences[index]),
                BoundingBox(
                    float(all_boxes[index][0] * scale_x),
                    float(all_boxes[index][1] * scale_y),
                    float(all_boxes[index][2] * scale_x),
                    float(all_boxes[index][3] * scale_y),
                ),
            )
            for index in self._flatten_indices(indices)
            if 0 <= int(class_ids[index]) < len(COCO_LABELS)
        )

    def _anchors_for(self, stride: int) -> Any:
        size = 416 // stride
        x_values, y_values = self._np.meshgrid(
            self._np.arange(size) * stride,
            self._np.arange(size) * stride,
        )
        offset = 0.5 * (stride - 1)
        return self._np.column_stack((x_values.flatten() + offset, y_values.flatten() + offset))

    @staticmethod
    def _squeeze(value: Any) -> Any:
        return value.squeeze(axis=0) if value.ndim == THREE_DIMENSIONAL else value

    def _softmax(self, value: Any) -> Any:
        shifted = value - value.max(axis=1, keepdims=True)
        exponential = self._np.exp(shifted)
        return exponential / exponential.sum(axis=1, keepdims=True)

    def _split_outputs(self, outputs: Any) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
        values = tuple(outputs)
        class_scores = tuple(
            value for value in values if value.shape[-1] == len(COCO_LABELS)
        )
        box_predictions = tuple(
            value
            for value in values
            if value.shape[-1] == 4 * (self._reg_max + 1)
        )
        expected_layers = len(self._strides)
        if (
            len(values) != expected_layers * 2
            or len(class_scores) != expected_layers
            or len(box_predictions) != expected_layers
        ):
            raise ValueError("unsupported NanoDet output layout")
        return (
            tuple(sorted(class_scores, key=lambda value: value.shape[-2], reverse=True)),
            tuple(sorted(box_predictions, key=lambda value: value.shape[-2], reverse=True)),
        )

    @staticmethod
    def _flatten_indices(indices: Any) -> tuple[int, ...]:
        return tuple(int(index) for index in indices)
