from __future__ import annotations

lazy import math
lazy import threading
lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from pathlib import Path
lazy from typing import Any, Protocol

_PALM_INPUT_SIZE = 192
_HAND_INPUT_SIZE = 224
_LANDMARK_COUNT = 21
_MAX_HANDS = 2
# Model loaders and injected inference backends can raise vendor-specific
# Exception subclasses. This boundary deliberately excludes BaseException.
_FAULT_BOUNDARY_ERRORS = (Exception,)


class HandLandmarkStatus(StrEnum):
    """Stable machine codes; localized user-facing text belongs to the UI."""

    OK = "ok"
    CANCELLED = "cancelled"
    STALE = "stale"
    INVALID_FRAME = "invalid_frame"
    MODEL_MISSING = "model_missing"
    MODEL_LOAD_FAILED = "model_load_failed"
    INFERENCE_FAILED = "inference_failed"


class Handedness(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    UNKNOWN = "unknown"


class MirrorMode(StrEnum):
    """NATIVE is camera space; SELFIE mirrors x and swaps handedness."""

    NATIVE = "native"
    SELFIE = "selfie"


@dataclass(frozen=True, slots=True)
class HandModelPaths:
    palm_detection: Path
    hand_pose: Path

    @property
    def missing(self) -> tuple[Path, ...]:
        return tuple(
            path
            for path in (self.palm_detection, self.hand_pose)
            if not path.is_file()
        )


@dataclass(frozen=True, slots=True)
class HandLandmark:
    """Frame-normalized point. x/y are clamped; z is frame-scale relative."""

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) for value in (self.x, self.y, self.z)):
            raise ValueError("hand_landmark_non_finite")
        if not 0.0 <= self.x <= 1.0 or not 0.0 <= self.y <= 1.0:
            raise ValueError("hand_landmark_out_of_bounds")


@dataclass(frozen=True, slots=True)
class HandObservation:
    handedness: Handedness
    confidence: float
    landmarks: tuple[HandLandmark, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.handedness, Handedness):
            raise TypeError("handedness_invalid")
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("hand_confidence_invalid")
        if len(self.landmarks) != _LANDMARK_COUNT:
            raise ValueError("hand_landmark_count_invalid")


@dataclass(frozen=True, slots=True)
class HandLandmarkResult:
    status: HandLandmarkStatus
    generation: int
    hands: tuple[HandObservation, ...] = ()

    def __post_init__(self) -> None:
        if self.generation < 0:
            raise ValueError("generation_invalid")
        if len(self.hands) > _MAX_HANDS:
            raise ValueError("hand_count_invalid")
        if self.status is not HandLandmarkStatus.OK and self.hands:
            raise ValueError("failed_result_contains_hands")


class HandInferenceRunnerPort(Protocol):
    def infer(
        self,
        rgb_frame: Any,
        palm_net: Any,
        hand_net: Any,
    ) -> tuple[HandObservation, ...]: ...


@dataclass(frozen=True, slots=True)
class _Palm:
    confidence: float
    box: tuple[float, float, float, float]
    keypoints: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class _Letterbox:
    scale: float
    left: int
    top: int


@dataclass(frozen=True, slots=True)
class _HandCrop:
    image: Any
    rotated_palm_box: Any
    angle_degrees: float
    rotation_matrix: Any
    pad_bias: Any


@dataclass(frozen=True, slots=True)
class _CropRegion:
    image: Any
    box: Any
    bias: Any


class OpenCVZooHandRunner:
    """Offline OpenCV Zoo MP-PalmDet + MP-HandPose FP32 ONNX pipeline."""

    def __init__(
        self,
        cv2_module: Any,
        numpy_module: Any,
        *,
        palm_threshold: float = 0.55,
        hand_threshold: float = 0.80,
    ) -> None:
        self._cv2 = cv2_module
        self._np = numpy_module
        self._palm_threshold = palm_threshold
        self._hand_threshold = hand_threshold
        self._anchors = _generate_palm_anchors(numpy_module)

    def infer(
        self,
        rgb_frame: Any,
        palm_net: Any,
        hand_net: Any,
    ) -> tuple[HandObservation, ...]:
        palms = self._detect_palms(rgb_frame, palm_net)
        hands = tuple(
            hand
            for palm in palms[:_MAX_HANDS]
            if (hand := self._estimate_hand(rgb_frame, palm, hand_net)) is not None
        )
        return tuple(sorted(hands, key=lambda hand: hand.confidence, reverse=True))

    def _detect_palms(self, frame: Any, net: Any) -> tuple[_Palm, ...]:
        height, width = frame.shape[:2]
        blob, letterbox = self._letterbox(frame, width, height)
        net.setInput(blob[self._np.newaxis, ...])
        outputs = net.forward(net.getUnconnectedOutLayersNames())
        if len(outputs) != 2:
            raise ValueError("palm_output_shape_invalid")
        regressions = self._np.asarray(outputs[0])[0]
        logits = self._np.asarray(outputs[1])[0, :, 0]
        if regressions.shape != (len(self._anchors), 18):
            raise ValueError("palm_output_shape_invalid")
        scores = 1.0 / (1.0 + self._np.exp(-self._np.clip(logits, -80.0, 80.0)))
        candidates = [
            candidate
            for index in self._np.flatnonzero(scores >= self._palm_threshold)
            if (
                candidate := _decode_palm_candidate(
                    regressions[index],
                    float(scores[index]),
                    self._anchors[index],
                    letterbox,
                )
            )
            is not None
        ]
        return _non_maximum_suppression(candidates, limit=_MAX_HANDS)

    def _letterbox(
        self,
        frame: Any,
        width: int,
        height: int,
    ) -> tuple[Any, _Letterbox]:
        scale = min(_PALM_INPUT_SIZE / width, _PALM_INPUT_SIZE / height)
        resized_width = max(1, round(width * scale))
        resized_height = max(1, round(height * scale))
        resized = self._cv2.resize(frame, (resized_width, resized_height))
        left = (_PALM_INPUT_SIZE - resized_width) // 2
        top = (_PALM_INPUT_SIZE - resized_height) // 2
        padded = self._cv2.copyMakeBorder(
            resized,
            top,
            _PALM_INPUT_SIZE - resized_height - top,
            left,
            _PALM_INPUT_SIZE - resized_width - left,
            self._cv2.BORDER_CONSTANT,
            None,
            (0, 0, 0),
        )
        return padded.astype(self._np.float32) / 255.0, _Letterbox(scale, left, top)

    def _estimate_hand(
        self,
        frame: Any,
        palm: _Palm,
        net: Any,
    ) -> HandObservation | None:
        height, width = frame.shape[:2]
        crop = self._hand_crop(frame, palm)
        if crop is None:
            return None
        net.setInput(crop.image[self._np.newaxis, ...])
        outputs = net.forward(net.getUnconnectedOutLayersNames())
        return self._decode_hand(outputs, crop, width, height)

    def _hand_crop(self, frame: Any, palm: _Palm) -> _HandCrop | None:
        palm_box = self._np.asarray(palm.box, dtype=self._np.float32).reshape(2, 2)
        pre_crop = self._crop_and_pad(
            frame,
            palm_box,
            shift=(0.0, 0.0),
            enlarge=4.0,
            diagonal_padding=True,
        )
        if pre_crop is None:
            return None
        palm_box = palm_box - pre_crop.bias
        palm_points = self._np.asarray(palm.keypoints, dtype=self._np.float32) - pre_crop.bias
        wrist = palm_points[0]
        middle_base = palm_points[2]
        radians = math.pi / 2.0 - math.atan2(
            -(middle_base[1] - wrist[1]),
            middle_base[0] - wrist[0],
        )
        radians -= 2.0 * math.pi * math.floor((radians + math.pi) / (2.0 * math.pi))
        angle = math.degrees(radians)
        palm_center = tuple(self._np.sum(palm_box, axis=0) / 2.0)
        rotation = self._cv2.getRotationMatrix2D(palm_center, angle, 1.0)
        rotated = self._cv2.warpAffine(
            pre_crop.image,
            rotation,
            (pre_crop.image.shape[1], pre_crop.image.shape[0]),
        )
        homogeneous = self._np.c_[palm_points, self._np.ones(len(palm_points))]
        rotated_points = self._np.asarray(
            (
                self._np.dot(homogeneous, rotation[0]),
                self._np.dot(homogeneous, rotation[1]),
            )
        )
        rotated_palm_box = self._np.asarray(
            (
                self._np.amin(rotated_points, axis=1),
                self._np.amax(rotated_points, axis=1),
            )
        )
        final_crop = self._crop_and_pad(
            rotated,
            rotated_palm_box,
            shift=(0.0, -0.4),
            enlarge=3.0,
            diagonal_padding=False,
        )
        if final_crop is None:
            return None
        image = self._cv2.resize(
            final_crop.image,
            (_HAND_INPUT_SIZE, _HAND_INPUT_SIZE),
            interpolation=self._cv2.INTER_AREA,
        )
        return _HandCrop(
            image.astype(self._np.float32) / 255.0,
            final_crop.box,
            angle,
            rotation,
            pre_crop.bias,
        )

    def _crop_and_pad(
        self,
        image: Any,
        box: Any,
        *,
        shift: tuple[float, float],
        enlarge: float,
        diagonal_padding: bool,
    ) -> _CropRegion | None:
        clipped = _expanded_clipped_box(self._np, image.shape, box, shift, enlarge)
        left, top = clipped[0]
        right, bottom = clipped[1]
        if right <= left or bottom <= top:
            return None
        cropped = image[top:bottom, left:right, :]
        side = (
            int(self._np.linalg.norm(cropped.shape[:2]))
            if diagonal_padding
            else max(cropped.shape[:2])
        )
        if side <= 0:
            return None
        pad_width = side - cropped.shape[1]
        pad_height = side - cropped.shape[0]
        pad_left = pad_width // 2
        pad_top = pad_height // 2
        padded = self._cv2.copyMakeBorder(
            cropped,
            pad_top,
            pad_height - pad_top,
            pad_left,
            pad_width - pad_left,
            self._cv2.BORDER_CONSTANT,
            None,
            (0, 0, 0),
        )
        bias = clipped[0] - self._np.asarray((pad_left, pad_top))
        return _CropRegion(padded, clipped, bias)

    def _decode_hand(
        self,
        outputs: Any,
        crop: _HandCrop,
        width: int,
        height: int,
    ) -> HandObservation | None:
        if len(outputs) != 4:
            raise ValueError("hand_output_shape_invalid")
        raw_landmarks = self._np.asarray(outputs[0])[0].reshape(-1, 3)
        world_landmarks = self._np.asarray(outputs[3])[0].reshape(-1, 3)
        if raw_landmarks.shape != (_LANDMARK_COUNT, 3):
            raise ValueError("hand_output_shape_invalid")
        if world_landmarks.shape != (_LANDMARK_COUNT, 3):
            raise ValueError("hand_world_output_shape_invalid")
        confidence = float(self._np.asarray(outputs[1]).reshape(-1)[0])
        handedness_score = float(self._np.asarray(outputs[2]).reshape(-1)[0])
        if not all(map(math.isfinite, (confidence, handedness_score))):
            raise ValueError("hand_output_non_finite")
        if confidence < self._hand_threshold:
            return None
        screen = self._project_screen_landmarks(raw_landmarks, crop)
        frame_scale = max(width, height)
        points = tuple(
            HandLandmark(
                _clamp(float(pixel_x) / width),
                _clamp(float(pixel_y) / height),
                float(pixel_z) / frame_scale,
            )
            for pixel_x, pixel_y, pixel_z in screen
        )
        handedness = Handedness.RIGHT if handedness_score >= 0.5 else Handedness.LEFT
        return HandObservation(handedness, _clamp(confidence), points)

    def _project_screen_landmarks(self, landmarks: Any, crop: _HandCrop) -> Any:
        scale = max(
            (crop.rotated_palm_box[1] - crop.rotated_palm_box[0])
            / self._np.asarray((_HAND_INPUT_SIZE, _HAND_INPUT_SIZE))
        )
        screen = landmarks.copy()
        screen[:, :2] = (screen[:, :2] - _HAND_INPUT_SIZE / 2.0) * scale
        screen[:, 2] *= scale
        coordinate_rotation = self._cv2.getRotationMatrix2D(
            (0.0, 0.0), crop.angle_degrees, 1.0
        )
        rotated_xy = self._np.dot(screen[:, :2], coordinate_rotation[:, :2])
        rotation_component = self._np.asarray(
            (
                (crop.rotation_matrix[0][0], crop.rotation_matrix[1][0]),
                (crop.rotation_matrix[0][1], crop.rotation_matrix[1][1]),
            )
        )
        translation = self._np.asarray(
            (crop.rotation_matrix[0][2], crop.rotation_matrix[1][2])
        )
        inverse_rotation = self._np.c_[
            rotation_component,
            (
                -self._np.dot(rotation_component[0], translation),
                -self._np.dot(rotation_component[1], translation),
            ),
        ]
        rotated_center = self._np.append(
            self._np.sum(crop.rotated_palm_box, axis=0) / 2.0,
            1.0,
        )
        original_center = self._np.asarray(
            (
                self._np.dot(rotated_center, inverse_rotation[0]),
                self._np.dot(rotated_center, inverse_rotation[1]),
            )
        )
        screen[:, :2] = rotated_xy + original_center + crop.pad_bias
        return screen


class HandLandmarkProvider:
    """Fault-isolated provider that never retains a source frame."""

    def __init__(
        self,
        models: HandModelPaths,
        *,
        cv2_module: Any | None = None,
        numpy_module: Any | None = None,
        runner: HandInferenceRunnerPort | None = None,
    ) -> None:
        self._state_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._generation = 0
        self._cancelled_through = -1
        self._failure: HandLandmarkStatus | None = None
        self._palm_net: Any | None = None
        self._hand_net: Any | None = None
        self._np: Any | None = numpy_module
        self._runner: HandInferenceRunnerPort | None = runner
        if models.missing:
            self._failure = HandLandmarkStatus.MODEL_MISSING
            return
        try:
            if cv2_module is None:
                import cv2 as cv2_module
            if numpy_module is None:
                import numpy as numpy_module
            self._np = numpy_module
            self._palm_net = cv2_module.dnn.readNet(str(models.palm_detection))
            self._hand_net = cv2_module.dnn.readNet(str(models.hand_pose))
            if self._runner is None:
                self._runner = OpenCVZooHandRunner(cv2_module, numpy_module)
        except _FAULT_BOUNDARY_ERRORS:
            self._palm_net = None
            self._hand_net = None
            self._runner = None
            self._failure = HandLandmarkStatus.MODEL_LOAD_FAILED

    def reserve_generation(self) -> int:
        with self._state_lock:
            self._generation += 1
            return self._generation

    def cancel(self) -> None:
        with self._state_lock:
            self._cancelled_through = self._generation
            self._generation += 1

    def analyze(
        self,
        rgb_bytes: bytes,
        width: int,
        height: int,
        *,
        generation: int | None = None,
        mirror: MirrorMode = MirrorMode.NATIVE,
    ) -> HandLandmarkResult:
        request_generation = self.reserve_generation() if generation is None else generation
        preflight = self._preflight(rgb_bytes, width, height, request_generation, mirror)
        if preflight is not None:
            return preflight
        try:
            with self._inference_lock:
                superseded = self._superseded_status(request_generation)
                if superseded is not None:
                    return HandLandmarkResult(superseded, request_generation)
                assert self._np is not None
                frame = self._np.frombuffer(rgb_bytes, dtype=self._np.uint8).reshape(
                    height, width, 3
                )
                assert self._runner is not None
                hands = self._runner.infer(frame, self._palm_net, self._hand_net)
            superseded = self._superseded_status(request_generation)
            if superseded is not None:
                return HandLandmarkResult(superseded, request_generation)
            if len(hands) > _MAX_HANDS:
                hands = hands[:_MAX_HANDS]
            if mirror is MirrorMode.SELFIE:
                hands = tuple(_mirror_hand(hand) for hand in hands)
            return HandLandmarkResult(HandLandmarkStatus.OK, request_generation, hands)
        except _FAULT_BOUNDARY_ERRORS:
            return HandLandmarkResult(HandLandmarkStatus.INFERENCE_FAILED, request_generation)

    def _preflight(
        self,
        rgb_bytes: bytes,
        width: int,
        height: int,
        generation: int,
        mirror: MirrorMode,
    ) -> HandLandmarkResult | None:
        status = self._superseded_status(generation) or self._failure
        if status is not None:
            return HandLandmarkResult(status, generation)
        if (
            width <= 0
            or height <= 0
            or len(rgb_bytes) != width * height * 3
            or not isinstance(mirror, MirrorMode)
        ):
            return HandLandmarkResult(HandLandmarkStatus.INVALID_FRAME, generation)
        return None

    def _superseded_status(self, generation: int) -> HandLandmarkStatus | None:
        with self._state_lock:
            if generation <= self._cancelled_through:
                return HandLandmarkStatus.CANCELLED
            if generation != self._generation:
                return HandLandmarkStatus.STALE
        return None


def _mirror_hand(hand: HandObservation) -> HandObservation:
    opposite = {
        Handedness.LEFT: Handedness.RIGHT,
        Handedness.RIGHT: Handedness.LEFT,
        Handedness.UNKNOWN: Handedness.UNKNOWN,
    }[hand.handedness]
    landmarks = tuple(HandLandmark(1.0 - point.x, point.y, point.z) for point in hand.landmarks)
    return HandObservation(opposite, hand.confidence, landmarks)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _decode_palm_candidate(
    row: Any,
    score: float,
    anchor: Any,
    letterbox: _Letterbox,
) -> _Palm | None:
    anchor_x, anchor_y = anchor
    center_x = (row[0] / _PALM_INPUT_SIZE + anchor_x) * _PALM_INPUT_SIZE
    center_y = (row[1] / _PALM_INPUT_SIZE + anchor_y) * _PALM_INPUT_SIZE
    box_width = float(row[2])
    box_height = float(row[3])
    box = (
        (center_x - box_width / 2.0 - letterbox.left) / letterbox.scale,
        (center_y - box_height / 2.0 - letterbox.top) / letterbox.scale,
        (center_x + box_width / 2.0 - letterbox.left) / letterbox.scale,
        (center_y + box_height / 2.0 - letterbox.top) / letterbox.scale,
    )
    keypoints = tuple(
        (
            ((row[4 + offset] / _PALM_INPUT_SIZE + anchor_x) * _PALM_INPUT_SIZE - letterbox.left)
            / letterbox.scale,
            ((row[5 + offset] / _PALM_INPUT_SIZE + anchor_y) * _PALM_INPUT_SIZE - letterbox.top)
            / letterbox.scale,
        )
        for offset in range(0, 14, 2)
    )
    values = (*box, *[*point for point in keypoints])
    if box_width <= 0.0 or box_height <= 0.0 or not all(map(math.isfinite, values)):
        return None
    return _Palm(score, box, keypoints)


def _expanded_clipped_box(
    np: Any,
    image_shape: tuple[int, ...],
    box: Any,
    shift: tuple[float, float],
    enlarge: float,
) -> Any:
    shifted = np.asarray(box, dtype=np.float32).copy()
    shifted += np.asarray(shift, dtype=np.float32) * (shifted[1] - shifted[0])
    center = np.sum(shifted, axis=0) / 2.0
    half_size = (shifted[1] - shifted[0]) * enlarge / 2.0
    clipped = np.asarray((center - half_size, center + half_size)).astype(np.int32)
    clipped[:, 0] = np.clip(clipped[:, 0], 0, image_shape[1])
    clipped[:, 1] = np.clip(clipped[:, 1], 0, image_shape[0])
    return clipped


def _non_maximum_suppression(
    palms: list[_Palm],
    *,
    limit: int,
    threshold: float = 0.30,
) -> tuple[_Palm, ...]:
    selected: list[_Palm] = []
    for candidate in sorted(palms, key=lambda palm: palm.confidence, reverse=True):
        if all(_intersection_over_union(candidate.box, item.box) <= threshold for item in selected):
            selected.append(candidate)
        if len(selected) == limit:
            break
    return tuple(selected)


def _intersection_over_union(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    first_area = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    second_area = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    union = first_area + second_area - intersection
    return 0.0 if union <= 0.0 else intersection / union


def _generate_palm_anchors(np: Any) -> Any:
    """Generate the 2,016 fixed-size MediaPipe palm SSD anchors."""

    anchors: list[tuple[float, float]] = []
    strides = (8, 16, 16, 16)
    layer = 0
    while layer < len(strides):
        same_stride_layers = 1
        while (
            layer + same_stride_layers < len(strides)
            and strides[layer + same_stride_layers] == strides[layer]
        ):
            same_stride_layers += 1
        anchors_per_cell = 2 * same_stride_layers
        grid = math.ceil(_PALM_INPUT_SIZE / strides[layer])
        anchors.extend(
            ((x + 0.5) / grid, (y + 0.5) / grid)
            for y in range(grid)
            for x in range(grid)
            for _ in range(anchors_per_cell)
        )
        layer += same_stride_layers
    result = np.asarray(anchors, dtype=np.float32)
    if result.shape != (2016, 2):
        raise RuntimeError("palm_anchor_generation_failed")
    return result
