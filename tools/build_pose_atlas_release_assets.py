from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import math
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path

lazy import cv2
lazy import numpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from domain.character_pose import CANONICAL_YAWS, canonical_view_id
lazy from infrastructure.hand_landmark_provider import (
    Handedness,
    HandLandmark,
    HandObservation,
    OpenCVZooHandRunner,
)

CANVAS_WIDTH = 1024
CANVAS_HEIGHT = 1536
ALPHA_THRESHOLD = 8
SAFE_MARGIN = 8
HAND_PALM_THRESHOLD = 0.45
HAND_CONFIDENCE_THRESHOLD = 0.65
HAND_ROI_MARGIN = 8
HAND_CLUSTER_DISTANCE = 72.0
PROVENANCE_SCHEMA = "mohan.pose-atlas.working-build.v1"
RGBA_CHANNEL_COUNT = 4
BGR_CHANNEL_COUNT = 3
MAX_FOOT_RUN_WIDTH = 190
FRONT_HALF_YAW = 90
MIN_FOOT_RUN_WIDTH = 4
TWO_HANDS = 2
ONE_HAND = 1
SKIN_COVERAGE_THRESHOLD = 0.35
MIN_OPAQUE_ALPHA = 96
MIN_SKIN_RED = 80
MIN_SKIN_CHANNEL_SPREAD = 10


@dataclass(frozen=True, slots=True)
class _SourceImage:
    view_id: str
    yaw: int
    source_path: Path
    source_sha256: str
    rgba: object
    top: int
    bottom: int
    left: int
    right: int

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1


@dataclass(frozen=True, slots=True)
class _FootRun:
    left: int
    right: int
    y: int

    @property
    def center(self) -> float:
        return (self.left + self.right) / 2.0


@dataclass(frozen=True, slots=True)
class _MappedHand:
    observation: HandObservation
    augmentation: str
    original_model_handedness: str


@dataclass(frozen=True, slots=True)
class _Augmentation:
    name: str
    rgb: object
    mirrored: bool
    mode: str


class BuildError(RuntimeError):
    pass


def build(source_root: Path, output_root: Path) -> dict[str, object]:
    source = source_root.resolve()
    output = output_root.resolve()
    if source == output:
        raise BuildError("source_and_output_must_differ")
    sources = _load_sources(source)
    target_height = _median_height(tuple(item.height for item in sources))
    target_bottom = min(
        max(item.bottom for item in sources),
        CANVAS_HEIGHT - SAFE_MARGIN - 1,
    )
    normalized = _prepare_output(output)
    for item in sources:
        _write_normalized_image(item, normalized, target_height, target_bottom)

    palm_path = ROOT / "assets" / "vision-models" / "palm_detection_mediapipe_2023feb.onnx"
    hand_path = ROOT / "assets" / "vision-models" / "handpose_estimation_mediapipe_2023feb.onnx"
    if not palm_path.is_file() or not hand_path.is_file():
        raise BuildError("hand_models_missing")
    palm_net = cv2.dnn.readNet(str(palm_path))
    hand_net = cv2.dnn.readNet(str(hand_path))
    runner = OpenCVZooHandRunner(
        cv2,
        numpy,
        palm_threshold=HAND_PALM_THRESHOLD,
        hand_threshold=HAND_CONFIDENCE_THRESHOLD,
    )

    view_records = []
    for item in sources:
        output_png = normalized / f"{item.view_id}.png"
        rgba = _read_rgba(output_png)
        body = _body_sidecar(item, rgba, target_height, item.source_sha256)
        (normalized / f"{item.view_id}.landmarks.json").write_text(
            json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        rgb = _rgba_to_rgb(rgba)
        hands, inference = _hand_sidecar(
            item,
            rgba,
            rgb,
            runner,
            palm_net,
            hand_net,
        )
        (normalized / f"{item.view_id}.hands.json").write_text(
            json.dumps(hands, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        view_records.append(
            {
                "view_id": item.view_id,
                "yaw_degrees": item.yaw,
                "source_sha256": item.source_sha256,
                "normalized_sha256": _sha256(output_png),
                "hand_inference": inference,
            }
        )

    provenance = _working_provenance(source, target_height, target_bottom, view_records)
    (normalized / "BUILD-METADATA.json").write_text(
        json.dumps(provenance, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_working_readme(normalized, provenance)
    return provenance


def _load_sources(source_root: Path) -> tuple[_SourceImage, ...]:
    result = []
    for yaw in CANONICAL_YAWS:
        view_id = canonical_view_id(yaw)
        path = source_root / f"{view_id}.png"
        if not path.is_file():
            raise BuildError(f"source_view_missing:{view_id}")
        rgba = _read_rgba(path)
        left, top, right, bottom = _alpha_bounds(rgba)
        if min(left, top, CANVAS_WIDTH - 1 - right, CANVAS_HEIGHT - 1 - bottom) < SAFE_MARGIN:
            raise BuildError(f"source_view_margin_invalid:{view_id}")
        result.append(
            _SourceImage(
                view_id,
                yaw,
                path,
                _sha256(path),
                rgba,
                top,
                bottom,
                left,
                right,
            )
        )
    return tuple(result)


def _prepare_output(output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    for path in output_root.glob("yaw*.png"):
        path.unlink()
    for path in output_root.glob("yaw*.json"):
        path.unlink()
    for name in ("BUILD-METADATA.json", "README.md"):
        path = output_root / name
        if path.exists():
            path.unlink()
    return output_root


def _write_normalized_image(
    source: _SourceImage,
    output_root: Path,
    target_height: int,
    target_bottom: int,
) -> None:
    crop = source.rgba[source.top : source.bottom + 1, source.left : source.right + 1]
    scale = target_height / source.height
    target_width = max(1, round(crop.shape[1] * scale))
    resized = cv2.resize(
        crop,
        (target_width, target_height),
        interpolation=cv2.INTER_LANCZOS4,
    )
    left = (CANVAS_WIDTH - target_width) // 2
    top = target_bottom - target_height + 1
    if left < SAFE_MARGIN or left + target_width > CANVAS_WIDTH - SAFE_MARGIN:
        raise BuildError(f"normalized_view_width_invalid:{source.view_id}")
    if top < SAFE_MARGIN or top + target_height > CANVAS_HEIGHT - SAFE_MARGIN + 1:
        raise BuildError(f"normalized_view_height_invalid:{source.view_id}")
    canvas = numpy.zeros((CANVAS_HEIGHT, CANVAS_WIDTH, 4), dtype=numpy.uint8)
    canvas[top : top + target_height, left : left + target_width] = resized
    encoded, data = cv2.imencode(".png", canvas)
    if not encoded:
        raise BuildError(f"normalized_png_encode_failed:{source.view_id}")
    (output_root / f"{source.view_id}.png").write_bytes(data.tobytes())


def _body_sidecar(
    source: _SourceImage,
    rgba: object,
    target_height: int,
    source_sha256: str,
) -> dict[str, object]:
    left, top, right, bottom = _alpha_bounds(rgba)
    mask = rgba[:, :, 3] > ALPHA_THRESHOLD
    crown_y = top
    crown_xs = numpy.flatnonzero(mask[crown_y])
    if len(crown_xs) == 0:
        raise BuildError(f"crown_missing:{source.view_id}")
    crown_index = len(crown_xs) // 2
    landmarks: dict[str, list[int]] = {
        "crown": [int(crown_xs[crown_index]), crown_y],
    }
    runs = _foot_runs(mask, bottom)
    if not runs:
        raise BuildError(f"foot_registration_missing:{source.view_id}")
    body_center = (left + right) / 2.0
    body_width = right - left + 1
    visible_sides = _foot_side_map(runs, body_center, source.yaw)
    occluded_landmarks = []
    for side in ("left", "right"):
        run = visible_sides.get(side)
        if run is None:
            occluded_landmarks.extend(
                {
                    "name": f"{side}_{part}",
                    "reason": "The lower robe and sleeve occlude this side in the authored view.",
                    "occluder_id": "lower-robe-and-sleeve",
                }
                for part in ("hip", "knee", "ankle", "heel", "toe", "sole")
            )
            continue
        hip_y = round(top + (bottom - top) * 0.56)
        knee_y = round(top + (bottom - top) * 0.78)
        ankle_y = max(top + 1, bottom - max(90, round(target_height * 0.06)))
        hip_offset = body_width * 0.22
        hip_target = body_center - hip_offset if side == "right" else body_center + hip_offset
        knee_target = (hip_target + run.center) / 2.0
        landmarks[f"{side}_hip"] = _alpha_point(mask, hip_target, hip_y, left, top, right, bottom)
        landmarks[f"{side}_knee"] = _alpha_point(mask, knee_target, knee_y, left, top, right, bottom)
        landmarks[f"{side}_ankle"] = _alpha_point(mask, run.center, ankle_y, left, top, right, bottom)
        landmarks[f"{side}_heel"] = _alpha_point(
            mask,
            run.left + (run.right - run.left) * 0.25,
            max(top + 1, run.y - 6),
            left,
            top,
            right,
            bottom,
        )
        landmarks[f"{side}_toe"] = _alpha_point(
            mask,
            run.right - (run.right - run.left) * 0.25,
            max(top + 1, run.y - 6),
            left,
            top,
            right,
            bottom,
        )
        landmarks[f"{side}_sole"] = _alpha_point(
            mask,
            run.center,
            run.y,
            left,
            top,
            right,
            bottom,
        )
    return {
        "schema_version": 2,
        "view_id": source.view_id,
        "yaw_degrees": source.yaw,
        "width": CANVAS_WIDTH,
        "height": CANVAS_HEIGHT,
        "landmarks": landmarks,
        "occluded_landmarks": occluded_landmarks,
        "measurement": {
            "method": "normalized-alpha-silhouette-registration",
            "source_sha256": source_sha256,
            "target_subject_height": target_height,
            "occlusion_policy": "no_coordinates_are invented for an occluded side",
        },
    }


def _foot_runs(mask: object, bottom: int) -> tuple[_FootRun, ...]:
    start = max(0, bottom - 72)
    for y in range(bottom, start - 1, -1):
        runs = tuple(
            (left, right)
            for left, right in _row_runs(mask[y])
            if MIN_FOOT_RUN_WIDTH <= right - left + 1 <= MAX_FOOT_RUN_WIDTH
        )
        if runs:
            # The lowest alpha-supported run is the only defensible sole
            # reference.  Choosing a higher row solely because ornamentation
            # creates more fragments can fabricate a false baseline.
            return tuple(_FootRun(left, right, y) for left, right in runs)
    return ()


def _foot_side_map(
    runs: tuple[_FootRun, ...],
    center: float,
    yaw: int,
) -> dict[str, _FootRun]:
    ordered = tuple(sorted(runs, key=lambda item: item.center))
    if len(ordered) >= TWO_HANDS:
        return {"right": ordered[0], "left": ordered[-1]}
    run = ordered[0]
    screen_left = run.center < center
    front_half = abs(yaw) < FRONT_HALF_YAW
    if front_half:
        side = "right" if screen_left else "left"
    else:
        side = "left" if screen_left else "right"
    return {side: run}


def _alpha_point(
    mask: object,
    target_x: float,
    target_y: float,
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> list[int]:
    target_x = min(max(target_x, left + 1), right)
    target_y = min(max(target_y, top + 1), bottom)
    for radius in range(48):
        x0 = max(left + 1, round(target_x) - radius)
        x1 = min(right, round(target_x) + radius)
        y0 = max(top + 1, round(target_y) - radius)
        y1 = min(bottom, round(target_y) + radius)
        ys, xs = numpy.nonzero(mask[y0 : y1 + 1, x0 : x1 + 1])
        if len(xs):
            distances = (xs + x0 - target_x) ** 2 + (ys + y0 - target_y) ** 2
            index = int(numpy.argmin(distances))
            return [int(xs[index] + x0), int(ys[index] + y0)]
    raise BuildError("alpha_registration_point_missing")


def _hand_sidecar(
    source: _SourceImage,
    rgba: object,
    rgb: object,
    runner: OpenCVZooHandRunner,
    palm_net: object,
    hand_net: object,
) -> tuple[dict[str, object], dict[str, object]]:
    mapped = []
    for augmentation in _augmentations(rgb):
        observations = runner.infer(augmentation.rgb, palm_net, hand_net)
        mapped.extend(_map_hand(
                    observation,
                    augmentation,
                    rgba.shape[1],
                    rgba.shape[0],
                ) for observation in observations)
    selected = _deduplicate_hands(
        mapped,
        rgba,
        enforce_screen_thumb_side=source.yaw == 0,
    )
    hands = []
    occluders = []
    for hand in selected:
        model_points = tuple(
            (
                round(point.x * rgba.shape[1]),
                round(point.y * rgba.shape[0]),
            )
            for point in hand.observation.landmarks
        )
        points = _refine_landmarks_to_skin(model_points, rgba)
        roi = _hand_roi(points, rgba.shape[1], rgba.shape[0])
        occlusions, detected_occluders = _thumb_base_garment_occlusions(
            hand.observation.handedness,
            points,
            rgba,
        )
        occluders.extend(detected_occluders)
        hands.append(
            {
                "side": hand.observation.handedness.value,
                "roi": list(roi),
                "landmarks": [list(point) for point in points],
                "occlusions": occlusions,
                "thumb_side_check": source.yaw == 0,
                "model_evidence": {
                    "augmentation": hand.augmentation,
                    "confidence": round(hand.observation.confidence, 6),
                    "model_handedness": hand.original_model_handedness,
                    "pixel_refinement": "nearest-skin-within-8px",
                },
            }
        )
    sides = {str(item["side"]) for item in hands}
    occluded = [{
                    "side": side,
                    "status": "occluded",
                    "reason": "No reliable 21-point hand observation was visible after the approved fixed augmentations.",
                    "occluder_id": "robe-or-view-occlusion",
                    "region": [0, source.top, rgba.shape[1], max(1, source.bottom - source.top + 1)],
                } for side in ("left", "right") if side not in sides]
    body_left = max(0, rgba.shape[1] // 2 - 100)
    body_top = min(rgba.shape[0] - 1, source.top + 260)
    body_height = min(220, rgba.shape[0] - body_top - 1)
    protected = [
        {
            "label": "face",
            "rect": [
                max(0, rgba.shape[1] // 2 - 100),
                min(rgba.shape[0] - 1, source.top + 80),
                200,
                220,
            ],
        },
        {"label": "body", "rect": [body_left, body_top, 200, max(1, body_height)]},
    ]
    payload = {
        "schema_version": 1,
        "view_id": source.view_id,
        "yaw_degrees": source.yaw,
        "width": int(rgba.shape[1]),
        "height": int(rgba.shape[0]),
        "hands": sorted(hands, key=lambda item: str(item["side"])),
        "occluded_hands": occluded,
        "protected_regions": protected,
        "occluders": occluders,
        "inference": {
            "pipeline": "OpenCV Zoo MediaPipe PalmDet + HandPose FP32 ONNX",
            "palm_threshold": HAND_PALM_THRESHOLD,
            "hand_confidence_threshold": HAND_CONFIDENCE_THRESHOLD,
            "augmentations": ["native", "flip-horizontal", "rotate-clockwise", "rotate-counterclockwise"],
            "source_sha256": source.source_sha256,
        },
    }
    report = {
        "observation_count": len(hands),
        "visible_sides": sorted(sides),
        "occluded_sides": sorted({str(item["side"]) for item in occluded}),
        "augmentations_used": sorted({item.augmentation for item in selected}),
        "confidences": sorted(
            round(item.observation.confidence, 6) for item in selected
        ),
    }
    return payload, report


def _thumb_base_garment_occlusions(
    side: Handedness,
    points: tuple[tuple[int, int], ...],
    rgba: object,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Record only a physically sampled sleeve covering a thumb root.

    The remaining three thumb landmarks must still be visible; the hand audit
    rejects any other base joint and every fingertip occlusion.
    """

    x, y = points[1]
    skin = _skin_mask(rgba)
    if _local_skin_coverage(skin, x, y) >= SKIN_COVERAGE_THRESHOLD:
        return [], []
    b, g, r, alpha = (int(value) for value in rgba[y, x])
    if alpha < MIN_OPAQUE_ALPHA or not (b > r + 20 and b > g + 10):
        return [], []
    identifier = f"sampled-blue-garment-{side.value}-thumb-root"
    return (
        [{"landmark_index": 1, "occluder_id": identifier}],
        [{"id": identifier, "rgb": [r, g, b], "tolerance": 24}],
    )


def _augmentations(rgb: object) -> tuple[_Augmentation, ...]:
    return (
        _Augmentation("native", rgb, False, "native"),
        _Augmentation("flip-horizontal", cv2.flip(rgb, 1), True, "flip"),
        _Augmentation("rotate-clockwise", cv2.rotate(rgb, cv2.ROTATE_90_CLOCKWISE), False, "rotate-clockwise"),
        _Augmentation("rotate-counterclockwise", cv2.rotate(rgb, cv2.ROTATE_90_COUNTERCLOCKWISE), False, "rotate-counterclockwise"),
    )


def _map_hand(
    observation: HandObservation,
    augmentation: _Augmentation,
    width: int,
    height: int,
) -> _MappedHand:
    transformed_width, transformed_height = (
        (height, width)
        if augmentation.mode.startswith("rotate")
        else (width, height)
    )
    points = []
    for point in observation.landmarks:
        x = point.x * transformed_width
        y = point.y * transformed_height
        if augmentation.mode == "flip":
            x, y = width - 1 - x, y
        elif augmentation.mode == "rotate-clockwise":
            x, y = y, height - 1 - x
        elif augmentation.mode == "rotate-counterclockwise":
            x, y = width - 1 - y, x
        points.append(
            HandLandmark(
                min(1.0, max(0.0, x / width)),
                min(1.0, max(0.0, y / height)),
                point.z,
            )
        )
    mapped_handedness = observation.handedness
    if augmentation.mirrored:
        mapped_handedness = _opposite_handedness(mapped_handedness)
    mapped = HandObservation(mapped_handedness, observation.confidence, tuple(points))
    return _MappedHand(mapped, augmentation.name, observation.handedness.value)


def _opposite_handedness(value: Handedness) -> Handedness:
    return {
        Handedness.LEFT: Handedness.RIGHT,
        Handedness.RIGHT: Handedness.LEFT,
        Handedness.UNKNOWN: Handedness.UNKNOWN,
    }[value]


def _deduplicate_hands(
    candidates: list[_MappedHand],
    rgba: object,
    *,
    enforce_screen_thumb_side: bool,
) -> tuple[_MappedHand, ...]:
    selected: list[_MappedHand] = []
    ordered = sorted(
        candidates,
        key=lambda item: _hand_quality(
            item,
            rgba,
            enforce_screen_thumb_side=enforce_screen_thumb_side,
        ),
        reverse=True,
    )
    for candidate in ordered:
        if len(selected) == TWO_HANDS:
            break
        center = _hand_center(candidate.observation)
        if any(
            _distance(center, _hand_center(item.observation)) < HAND_CLUSTER_DISTANCE
            for item in selected
        ):
            continue
        selected.append(candidate)
    return _assign_screen_sides(tuple(selected), rgba.shape[1])


def _assign_screen_sides(
    selected: tuple[_MappedHand, ...],
    width: int,
) -> tuple[_MappedHand, ...]:
    ordered = tuple(sorted(selected, key=lambda item: _hand_center(item.observation)[0]))
    if len(ordered) == TWO_HANDS:
        sides = (Handedness.LEFT, Handedness.RIGHT)
    elif len(ordered) == ONE_HAND:
        sides = (
            Handedness.LEFT
            if _hand_center(ordered[0].observation)[0] < width / 2
            else Handedness.RIGHT,
        )
    else:
        return ()
    assigned = []
    for item, side in zip(ordered, sides, strict=False):
        observation = HandObservation(
            side,
            item.observation.confidence,
            item.observation.landmarks,
        )
        assigned.append(
            _MappedHand(
                observation,
                item.augmentation,
                item.original_model_handedness,
            )
        )
    return tuple(assigned)


def _hand_quality(
    candidate: _MappedHand,
    rgba: object,
    *,
    enforce_screen_thumb_side: bool,
) -> tuple[float, float, float]:
    width = rgba.shape[1]
    height = rgba.shape[0]
    model_points = tuple(
        (round(point.x * width), round(point.y * height))
        for point in candidate.observation.landmarks
    )
    refined = _refine_landmarks_to_skin(model_points, rgba)
    skin = _skin_mask(rgba)
    coverage = sum(
        _local_skin_coverage(skin, x, y) for x, y in refined
    ) / len(refined)
    topology_penalty = _hand_topology_penalty(refined)
    thumb_penalty = 0.0
    if enforce_screen_thumb_side:
        center_x = sum(x for x, _y in refined) / len(refined)
        is_left_side = center_x < width / 2
        thumb_x = refined[4][0]
        pinky_x = refined[20][0]
        thumb_is_outer = thumb_x < pinky_x if is_left_side else thumb_x > pinky_x
        thumb_penalty = 0.0 if thumb_is_outer else 1.0
    return (
        -(topology_penalty + thumb_penalty),
        coverage,
        candidate.observation.confidence,
    )


def _hand_topology_penalty(points: tuple[tuple[int, int], ...]) -> float:
    wrist = points[0]
    penalty = 0.0
    for mcp, pip, dip, tip in ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)):
        distances = tuple(_pixel_distance(wrist, points[index]) for index in (mcp, pip, dip, tip))
        penalty += sum(
            1.0 for inner, outer in zip(distances, distances[1:], strict=False) if outer + 2.0 < inner
        )
    palm_width = max(1.0, _pixel_distance(points[5], points[17]))
    finger_lengths = tuple(
        _pixel_distance(points[mcp], points[tip]) / palm_width
        for mcp, tip in ((5, 8), (9, 12), (13, 16), (17, 20))
    )
    if finger_lengths[1] + 0.08 < finger_lengths[0]:
        penalty += 0.5
    if finger_lengths[3] > finger_lengths[2] + 0.15:
        penalty += 0.5
    return penalty


def _pixel_distance(first: tuple[int, int], second: tuple[int, int]) -> float:
    return math.hypot(first[0] - second[0], first[1] - second[1])


def _refine_landmarks_to_skin(
    points: tuple[tuple[int, int], ...],
    rgba: object,
    *,
    radius: int = 8,
) -> tuple[tuple[int, int], ...]:
    skin = _skin_mask(rgba)
    height, width = skin.shape
    refined = []
    for x, y in points:
        x = min(width - 1, max(0, x))
        y = min(height - 1, max(0, y))
        x0 = max(0, x - radius)
        x1 = min(width - 1, x + radius)
        y0 = max(0, y - radius)
        y1 = min(height - 1, y + radius)
        ys, xs = numpy.nonzero(skin[y0 : y1 + 1, x0 : x1 + 1])
        if not len(xs):
            refined.append((x, y))
            continue
        candidates = tuple(
            (int(candidate_x + x0), int(candidate_y + y0))
            for candidate_x, candidate_y in zip(xs, ys, strict=False)
        )
        best = max(
            candidates,
            key=lambda candidate: (
                _local_skin_coverage(skin, candidate[0], candidate[1]),
                -((candidate[0] - x) ** 2 + (candidate[1] - y) ** 2),
            ),
        )
        refined.append(best)
    return tuple(refined)


def _local_skin_coverage(skin: object, x: int, y: int) -> float:
    height, width = skin.shape
    x0 = max(0, x - 2)
    x1 = min(width - 1, x + 2)
    y0 = max(0, y - 2)
    y1 = min(height - 1, y + 2)
    return float(skin[y0 : y1 + 1, x0 : x1 + 1].mean())


def _skin_coverage(observation: HandObservation, rgba: object) -> float:
    height, width = rgba.shape[:2]
    values = []
    skin = _skin_mask(rgba)
    for point in observation.landmarks:
        x = round(point.x * width)
        y = round(point.y * height)
        x0 = max(0, x - 2)
        x1 = min(width - 1, x + 2)
        y0 = max(0, y - 2)
        y1 = min(height - 1, y + 2)
        window = skin[y0 : y1 + 1, x0 : x1 + 1]
        values.append(float(window.mean()))
    return sum(values) / len(values)


def _skin_mask(rgba: object) -> object:
    b, g, r, alpha = cv2.split(rgba)
    spread = numpy.maximum(numpy.maximum(r, g), b) - numpy.minimum(
        numpy.minimum(r, g), b
    )
    return (
        (alpha >= MIN_OPAQUE_ALPHA)
        & (r >= MIN_SKIN_RED)
        & (r > b)
        & (r >= g.astype(numpy.float32) * 0.85)
        & (spread >= MIN_SKIN_CHANNEL_SPREAD)
    )


def _hand_center(observation: HandObservation) -> tuple[float, float]:
    points = observation.landmarks
    return (
        sum(point.x for point in points) / len(points),
        sum(point.y for point in points) / len(points),
    )


def _distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    return math.hypot(first[0] - second[0], first[1] - second[1]) * CANVAS_WIDTH


def _hand_roi(
    points: tuple[tuple[int, int], ...],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    left = max(0, min(point[0] for point in points) - HAND_ROI_MARGIN)
    top = max(0, min(point[1] for point in points) - HAND_ROI_MARGIN)
    right = min(width - 1, max(point[0] for point in points) + HAND_ROI_MARGIN)
    bottom = min(height - 1, max(point[1] for point in points) + HAND_ROI_MARGIN)
    return left, top, right - left + 1, bottom - top + 1


def _rgba_to_rgb(rgba: object) -> object:
    background = numpy.full(rgba.shape[:2] + (3,), 245, dtype=numpy.uint8)
    alpha = rgba[:, :, 3:4].astype(numpy.float32) / 255.0
    bgr = (rgba[:, :, :3].astype(numpy.float32) * alpha + background * (1.0 - alpha)).astype(numpy.uint8)
    return bgr[:, :, ::-1]


def _read_rgba(path: Path) -> object:
    rgba = cv2.imdecode(numpy.fromfile(str(path), dtype=numpy.uint8), cv2.IMREAD_UNCHANGED)
    if rgba is None or len(rgba.shape) != BGR_CHANNEL_COUNT or rgba.shape[2] != RGBA_CHANNEL_COUNT:
        raise BuildError(f"invalid_rgba_png:{path.name}")
    if rgba.shape[1] != CANVAS_WIDTH or rgba.shape[0] != CANVAS_HEIGHT:
        raise BuildError(f"unexpected_canvas:{path.name}")
    return rgba


def _alpha_bounds(rgba: object) -> tuple[int, int, int, int]:
    mask = rgba[:, :, 3] > ALPHA_THRESHOLD
    points = cv2.findNonZero(mask.astype(numpy.uint8))
    if points is None:
        raise BuildError("empty_alpha")
    x, y, width, height = cv2.boundingRect(points)
    return x, y, x + width - 1, y + height - 1


def _row_runs(row: object) -> tuple[tuple[int, int], ...]:
    indexes = numpy.flatnonzero(row)
    if len(indexes) == 0:
        return ()
    result = []
    start = previous = int(indexes[0])
    for value in indexes[1:]:
        current = int(value)
        if current != previous + 1:
            result.append((start, previous))
            start = current
        previous = current
    result.append((start, previous))
    return tuple(result)


def _median_height(values: tuple[int, ...]) -> int:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return round((ordered[middle - 1] + ordered[middle]) / 2.0)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _working_provenance(
    source_root: Path,
    target_height: int,
    target_bottom: int,
    records: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": PROVENANCE_SCHEMA,
        "status": "working-evidence-only",
        "formal_promotion": "blocked_until_visual_review_and_release_audits",
        "source_root": source_root.name,
        "source_authorization": "confirmed_by_rights_holder_2026-08-16",
        "redistribution": "authorized_under_project_license_pending_visual_review_and_release_gates",
        "normalization": {
            "canvas": [CANVAS_WIDTH, CANVAS_HEIGHT],
            "target_subject_height": target_height,
            "target_sole_baseline": target_bottom,
            "method": "uniform-alpha-bbox-scale-and-centered-registration",
        },
        "hand_evidence": {
            "model": "OpenCV Zoo MediaPipe PalmDet + HandPose FP32 ONNX",
            "palm_threshold": HAND_PALM_THRESHOLD,
            "hand_confidence_threshold": HAND_CONFIDENCE_THRESHOLD,
            "augmentations": ["native", "flip-horizontal", "rotate-clockwise", "rotate-counterclockwise"],
            "landmark_count": 21,
            "coordinates": "pixel_xy_plus_relative_z",
        },
        "views": records,
    }


def _write_working_readme(output_root: Path, provenance: dict[str, object]) -> None:
    text = (
        "# PoseAtlas v4 working evidence\n\n"
        "This directory is a reproducible local working build. It is not a formal release asset directory.\n\n"
        "The PNG files are normalized native RGBA assets. Body sidecars use alpha-silhouette registration.\n"
        "Hand sidecars contain only observations produced by the project ONNX hand model after the\n"
        "fixed augmentations recorded in `BUILD-METADATA.json`. Natural occlusion is represented by\n"
        "explicit declarations and never by invented landmark coordinates.\n\n"
        "Source authorization and redistribution were confirmed by the rights holder on 2026-08-16.\n"
        "Formal promotion still requires visual review and every release audit to pass.\n"
    )
    (output_root / "README.md").write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = build(args.source_root, args.output_root)
    except (BuildError, OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps({"status": "working-evidence-built", "views": len(report["views"])}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
