from __future__ import annotations

lazy import threading
lazy from pathlib import Path
lazy from typing import Any

lazy import numpy as np

lazy from infrastructure.hand_landmark_provider import (
    Handedness,
    HandLandmark,
    HandLandmarkProvider,
    HandLandmarkStatus,
    HandModelPaths,
    HandObservation,
    MirrorMode,
    OpenCVZooHandRunner,
    _HandCrop,
    _Palm,
)


class FakeNet:
    def __init__(self, outputs: tuple[Any, ...] = ()) -> None:
        self.outputs = outputs
        self.inputs: list[Any] = []

    def setInput(self, value: Any) -> None:
        self.inputs.append(value)

    def getUnconnectedOutLayersNames(self) -> tuple[str, ...]:
        return ("output",)

    def forward(self, _names: Any) -> tuple[Any, ...]:
        return self.outputs


class FakeDnn:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.paths: list[str] = []

    def readNet(self, path: str) -> FakeNet:
        self.paths.append(path)
        if self.fail:
            raise ValueError("corrupt model details must stay internal")
        return FakeNet()


class FakeCV2:
    def __init__(self, *, fail: bool = False) -> None:
        self.dnn = FakeDnn(fail=fail)


class MathCV2:
    BORDER_CONSTANT = 0
    INTER_AREA = 1

    def __init__(self) -> None:
        self.resize_calls: list[tuple[int, int]] = []
        self.border_calls: list[tuple[int, int, int, int]] = []

    def resize(
        self,
        image: Any,
        size: tuple[int, int],
        interpolation: int | None = None,
    ) -> Any:
        del interpolation
        self.resize_calls.append(size)
        y_indices = np.linspace(0, image.shape[0] - 1, size[1]).astype(int)
        x_indices = np.linspace(0, image.shape[1] - 1, size[0]).astype(int)
        return image[y_indices][:, x_indices]

    def copyMakeBorder(self, image: Any, *args: Any) -> Any:
        top, bottom, left, right, _border, _destination, value = args
        self.border_calls.append((top, bottom, left, right))
        return np.pad(
            image,
            ((top, bottom), (left, right), (0, 0)),
            mode="constant",
            constant_values=value[0],
        )

    def getRotationMatrix2D(
        self,
        center: tuple[float, float],
        angle: float,
        scale: float,
    ) -> Any:
        radians = np.deg2rad(angle)
        alpha = scale * np.cos(radians)
        beta = scale * np.sin(radians)
        center_x, center_y = center
        return np.asarray(
            (
                (alpha, beta, (1.0 - alpha) * center_x - beta * center_y),
                (-beta, alpha, beta * center_x + (1.0 - alpha) * center_y),
            ),
            dtype=np.float32,
        )

    def warpAffine(self, image: Any, _matrix: Any, size: tuple[int, int]) -> Any:
        return self.resize(image, size)


class FixedPalmRunner(OpenCVZooHandRunner):
    def __init__(self, cv2_module: Any, palms: tuple[_Palm, ...]) -> None:
        super().__init__(cv2_module, np)
        self._palms = palms

    def _detect_palms(self, _frame: Any, _net: Any) -> tuple[_Palm, ...]:
        return self._palms


class FakeRunner:
    def __init__(self, hands: tuple[HandObservation, ...] = ()) -> None:
        self.hands = hands
        self.frames: list[Any] = []

    def infer(self, frame: Any, palm_net: Any, hand_net: Any) -> tuple[HandObservation, ...]:
        assert isinstance(palm_net, FakeNet)
        assert isinstance(hand_net, FakeNet)
        self.frames.append(frame)
        return self.hands


class RaisingRunner:
    def infer(self, _frame: Any, _palm_net: Any, _hand_net: Any) -> tuple[HandObservation, ...]:
        raise RuntimeError("sensitive inference internals")


class BlockingRunner:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def infer(self, _frame: Any, _palm_net: Any, _hand_net: Any) -> tuple[HandObservation, ...]:
        self.started.set()
        assert self.release.wait(timeout=2.0)
        return (_hand(Handedness.LEFT),)


def _models(tmp_path: Path) -> HandModelPaths:
    palm = tmp_path / "palm_detection_mediapipe_2023feb.onnx"
    pose = tmp_path / "handpose_estimation_mediapipe_2023feb.onnx"
    palm.write_bytes(b"fake")
    pose.write_bytes(b"fake")
    return HandModelPaths(palm, pose)


def _frame(width: int = 4, height: int = 3) -> bytes:
    return bytes(width * height * 3)


def _hand(side: Handedness = Handedness.LEFT, *, x: float = 0.2) -> HandObservation:
    points = tuple(HandLandmark(x, index / 20.0, 0.01 * index) for index in range(21))
    return HandObservation(side, 0.91, points)


def test_returns_two_typed_hands_without_retaining_source_frame(tmp_path: Path) -> None:
    runner = FakeRunner((_hand(Handedness.LEFT), _hand(Handedness.RIGHT), _hand()))
    provider = HandLandmarkProvider(
        _models(tmp_path), cv2_module=FakeCV2(), numpy_module=np, runner=runner
    )

    result = provider.analyze(_frame(), 4, 3)

    assert result.status is HandLandmarkStatus.OK
    assert len(result.hands) == 2
    assert all(len(hand.landmarks) == 21 for hand in result.hands)
    assert not hasattr(provider, "_frame")
    assert len(runner.frames) == 1


def test_selfie_mode_mirrors_x_and_swaps_handedness(tmp_path: Path) -> None:
    provider = HandLandmarkProvider(
        _models(tmp_path),
        cv2_module=FakeCV2(),
        numpy_module=np,
        runner=FakeRunner((_hand(Handedness.LEFT, x=0.2),)),
    )

    result = provider.analyze(_frame(), 4, 3, mirror=MirrorMode.SELFIE)

    assert result.hands[0].handedness is Handedness.RIGHT
    assert result.hands[0].landmarks[0].x == 0.8


def test_missing_and_corrupt_models_fail_closed(tmp_path: Path) -> None:
    missing = HandLandmarkProvider(
        HandModelPaths(tmp_path / "missing-palm.onnx", tmp_path / "missing-hand.onnx"),
        cv2_module=FakeCV2(),
        numpy_module=np,
    )
    corrupt = HandLandmarkProvider(
        _models(tmp_path), cv2_module=FakeCV2(fail=True), numpy_module=np
    )

    assert missing.analyze(_frame(), 4, 3).status is HandLandmarkStatus.MODEL_MISSING
    assert corrupt.analyze(_frame(), 4, 3).status is HandLandmarkStatus.MODEL_LOAD_FAILED


def test_invalid_frame_and_inference_exception_do_not_escape(tmp_path: Path) -> None:
    provider = HandLandmarkProvider(
        _models(tmp_path), cv2_module=FakeCV2(), numpy_module=np, runner=RaisingRunner()
    )

    invalid = provider.analyze(b"short", 4, 3)
    failed = provider.analyze(_frame(), 4, 3)

    assert invalid.status is HandLandmarkStatus.INVALID_FRAME
    assert failed.status is HandLandmarkStatus.INFERENCE_FAILED
    assert failed.hands == ()
    assert "sensitive" not in repr(failed)


def test_cancel_during_inference_discards_result(tmp_path: Path) -> None:
    runner = BlockingRunner()
    provider = HandLandmarkProvider(
        _models(tmp_path), cv2_module=FakeCV2(), numpy_module=np, runner=runner
    )
    generation = provider.reserve_generation()
    captured: list[Any] = []
    worker = threading.Thread(
        target=lambda: captured.append(
            provider.analyze(_frame(), 4, 3, generation=generation)
        )
    )

    worker.start()
    assert runner.started.wait(timeout=2.0)
    provider.cancel()
    runner.release.set()
    worker.join(timeout=2.0)

    assert captured[0].status is HandLandmarkStatus.CANCELLED
    assert captured[0].hands == ()


def test_new_generation_makes_older_request_stale(tmp_path: Path) -> None:
    provider = HandLandmarkProvider(
        _models(tmp_path), cv2_module=FakeCV2(), numpy_module=np, runner=FakeRunner()
    )
    old_generation = provider.reserve_generation()
    current_generation = provider.reserve_generation()

    old = provider.analyze(_frame(), 4, 3, generation=old_generation)
    current = provider.analyze(_frame(), 4, 3, generation=current_generation)

    assert old.status is HandLandmarkStatus.STALE
    assert current.status is HandLandmarkStatus.OK


def test_palm_input_is_nhwc_rgb_without_channel_swap() -> None:
    cv2 = MathCV2()
    runner = OpenCVZooHandRunner(cv2, np)
    frame = np.zeros((192, 192, 3), dtype=np.uint8)
    frame[0, 0] = (11, 22, 33)
    regressions = np.zeros((1, 2016, 18), dtype=np.float32)
    logits = np.full((1, 2016, 1), -100.0, dtype=np.float32)
    net = FakeNet((regressions, logits))

    assert runner._detect_palms(frame, net) == ()
    assert net.inputs[0].shape == (1, 192, 192, 3)
    assert tuple(net.inputs[0][0, 0, 0] * 255.0) == (11.0, 22.0, 33.0)


def test_official_two_stage_crop_uses_four_then_three_times_palm_geometry() -> None:
    cv2 = MathCV2()
    runner = OpenCVZooHandRunner(cv2, np)
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    palm = _Palm(
        0.9,
        (80.0, 80.0, 120.0, 120.0),
        (
            (100.0, 120.0),
            (90.0, 100.0),
            (100.0, 80.0),
            (110.0, 90.0),
            (115.0, 100.0),
            (90.0, 115.0),
            (110.0, 115.0),
        ),
    )

    crop = runner._hand_crop(frame, palm)

    assert crop is not None
    # Official pre-crop: 40px palm bbox enlarged 4x, then diagonal square padding.
    assert cv2.border_calls[0] == (33, 33, 33, 33)
    # Official second crop derives from rotated palm landmarks, shifts -0.4y,
    # enlarges 3x, and is finally resized to NHWC 224x224 RGB.
    assert crop.image.shape == (224, 224, 3)
    assert np.all(crop.rotated_palm_box[1] > crop.rotated_palm_box[0])


def test_four_output_order_and_screen_back_projection_preserve_negative_z() -> None:
    cv2 = MathCV2()
    runner = OpenCVZooHandRunner(cv2, np)
    raw = np.tile(np.asarray((112.0, 112.0, -22.4), dtype=np.float32), (21, 1))
    world = np.zeros((21, 3), dtype=np.float32)
    crop = _HandCrop(
        np.zeros((224, 224, 3), dtype=np.float32),
        np.asarray(((10.0, 20.0), (234.0, 244.0)), dtype=np.float32),
        0.0,
        np.asarray(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)), dtype=np.float32),
        np.asarray((5.0, 7.0), dtype=np.float32),
    )

    hand = runner._decode_hand(
        (
            raw.reshape(1, 63),
            np.asarray(((0.95,),), dtype=np.float32),
            np.asarray(((0.75,),), dtype=np.float32),
            world.reshape(1, 63),
        ),
        crop,
        400,
        300,
    )

    assert hand is not None
    assert hand.handedness is Handedness.RIGHT
    assert hand.landmarks[0].x == 127.0 / 400.0
    assert hand.landmarks[0].y == 139.0 / 300.0
    assert hand.landmarks[0].z == np.float32(-22.4) / 400.0


def test_wrong_four_output_order_fails_closed() -> None:
    runner = OpenCVZooHandRunner(MathCV2(), np)
    crop = _HandCrop(
        np.zeros((224, 224, 3), dtype=np.float32),
        np.asarray(((0.0, 0.0), (224.0, 224.0)), dtype=np.float32),
        0.0,
        np.asarray(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)), dtype=np.float32),
        np.zeros(2, dtype=np.float32),
    )

    with np.testing.assert_raises(ValueError):
        runner._decode_hand(
            (
                np.zeros((1, 63), dtype=np.float32),
                np.zeros((1, 63), dtype=np.float32),  # world output in confidence slot
                np.asarray(((0.8,),), dtype=np.float32),
                np.asarray(((0.9,),), dtype=np.float32),
            ),
            crop,
            100,
            100,
        )


def test_empty_crop_skips_only_that_palm() -> None:
    cv2 = MathCV2()
    invalid = _Palm(0.9, (20.0, 20.0, 20.0, 20.0), ((20.0, 20.0),) * 7)
    runner = FixedPalmRunner(cv2, (invalid,))
    hand_net = FakeNet(())

    hands = runner.infer(np.zeros((40, 40, 3), dtype=np.uint8), FakeNet(), hand_net)

    assert hands == ()
    assert hand_net.inputs == []
