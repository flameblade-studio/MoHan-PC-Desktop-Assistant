"""Audit the generated demo video frame-by-frame against its audio timeline."""

from __future__ import annotations

lazy import argparse
lazy import json
lazy import re
lazy import shutil
lazy import subprocess
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy import cv2
lazy import numpy as np

VIDEO = ROOT / "docs" / "media" / "mohan-demo.mp4"
EVIDENCE = ROOT / "docs" / "release-evidence" / "media-generation-coherence"
WIDTH = 1280
HEIGHT = 720
FPS = 10
SILENCE_FILTER = "silencedetect=noise=-35dB:d=0.12"
MIN_SCENE_TRANSITION_SEPARATION_FRAMES = 3
MAX_VOICED_ZERO_CHANGE_PERCENT = 15.0
FULL_PERCENT = 100.0
VISEME_CUES_PER_SECOND = 50
CUES_PER_VIDEO_FRAME = VISEME_CUES_PER_SECOND // FPS
MOUTH_SILENCE_MIN_CUES = 13
MOUTH_SILENCE_MIN_SECONDS = MOUTH_SILENCE_MIN_CUES / VISEME_CUES_PER_SECOND
MOUTH_CORE_ROI = (1048, 485, 1085, 515)
MOUTH_CORE_DARK_THRESHOLD = 130
# The closed-lip reference retains 22 dark antialiased lip pixels after the
# 1254->450 crop and H.264 encode; open speech frames exceed this count.
MAX_CLOSED_CORE_DARK_PIXELS = 22
MOUTH_ROI = (990, 440, 1140, 555)
MOUTH_BASELINE_FRAME_COUNT = FPS
MOUTH_BASELINE_CHANNEL_DELTA = 20
MOUTH_OPEN_PIXEL_THRESHOLD = 50
MIN_MOUTH_STATE_PERCENT = 95.0
# Match the owner's one-decimal independent report (227/239 -> 95.0%).
MOUTH_STATE_PERCENT_DECIMAL_PLACES = 1
SILENCE_INTERVAL_ENDPOINT_COUNT = 2
CHARACTER_PANEL_XYWH = (874, 103, 378, 503)
PORTRAIT_CROP_XYWH = (402, 100, 450, 600)
FRONT_CROSS_FACE_BBOX_XYWH = (456, 279, 307, 347)
MIN_FACE_HEIGHT_RATIO = 0.2

# These are the measured windows printed by record_demo_video.py for the
# owner-approved six lines. A regenerated recording must update this tuple
# from its AUDIO_SEGMENT output before reusing this audit.
SCENE_WINDOWS = (
    (1.000, 5.263, 5.663),
    (5.663, 11.940, 12.340),
    (12.340, 15.997, 16.397),
    (16.397, 23.253, 23.653),
    (23.653, 30.845, 31.245),
    (31.245, 34.111, 35.200),
)

# x0, y0, x1, y1 in the encoded 1280x720 frame. All scenes now use the same
# explicit head-and-shoulders crop, so the measured mouth ROI is invariant.
SCENE_ROIS = {
    0: (990, 440, 1140, 555),
    1: (990, 440, 1140, 555),
    2: (990, 440, 1140, 555),
    3: (990, 440, 1140, 555),
    4: (990, 440, 1140, 555),
    5: (990, 440, 1140, 555),
}


def _ffprobe(video: Path) -> dict[str, object]:
    result = subprocess.run(
        [
            shutil.which("ffprobe") or "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(video),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    return json.loads(result.stdout)


def _silence_intervals(video: Path) -> list[tuple[float, float]]:
    result = subprocess.run(
        [
            shutil.which("ffmpeg") or "ffmpeg",
            "-hide_banner",
            "-i",
            str(video),
            "-af",
            SILENCE_FILTER,
            "-f",
            "null",
            "NUL",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=60,
    )
    output = f"{result.stdout}\n{result.stderr}"
    starts = [
        float(value)
        for value in re.findall(r"silence_start:\s*([0-9.]+)", output)
    ]
    ends = [
        float(value)
        for value in re.findall(r"silence_end:\s*([0-9.]+)", output)
    ]
    if len(starts) != len(ends):
        raise RuntimeError(
            f"silencedetect returned unpaired intervals: {len(starts)} starts/{len(ends)} ends"
        )
    return list(zip(starts, ends))


def _load_silence_intervals(path: Path) -> list[tuple[float, float]]:
    """Load ``[{"start": seconds, "end": seconds}, ...]`` intervals."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_intervals = payload
    if isinstance(payload, dict):
        raw_intervals = payload.get("intervals")
        if raw_intervals is None and isinstance(payload.get("mouth_silence"), dict):
            raw_intervals = payload["mouth_silence"].get("intervals")
        if raw_intervals is None and isinstance(payload.get("silencedetect"), dict):
            raw_intervals = payload["silencedetect"].get("intervals")
    if not isinstance(raw_intervals, list):
        raise ValueError(f"Silence interval JSON must contain a list: {path}")
    intervals: list[tuple[float, float]] = []
    for item in raw_intervals:
        if isinstance(item, dict):
            start = float(item["start"])
            end = float(item["end"])
        elif (
            isinstance(item, list)
            and len(item) == SILENCE_INTERVAL_ENDPOINT_COUNT
        ):
            start, end = (float(value) for value in item)
        else:
            raise ValueError(f"Invalid silence interval: {item!r}")
        if start < 0.0 or end < start:
            raise ValueError(f"Invalid silence interval bounds: {item!r}")
        intervals.append((start, end))
    return sorted(intervals)


def _stable_mouth_silence_intervals(
    intervals: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Keep the stable per-segment pauses used by the mouth-state contract."""

    return [
        (start, end)
        for start, end in intervals
        if end - start >= MOUTH_SILENCE_MIN_SECONDS
    ]


def _frames(video: Path) -> list[np.ndarray]:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video}")
    result: list[np.ndarray] = []
    try:
        while True:
            success, frame = capture.read()
            if not success:
                break
            result.append(frame)
    finally:
        capture.release()
    return result


def _scene_at(second: float) -> int:
    for index, (_start, _end, visual_end) in enumerate(SCENE_WINDOWS):
        if second < visual_end:
            return index
    return len(SCENE_WINDOWS) - 1


def _is_silent(second: float, intervals: list[tuple[float, float]]) -> bool:
    return any(start <= second < end for start, end in intervals)


def _roi(frame: np.ndarray, scene: int) -> np.ndarray:
    x0, y0, x1, y1 = SCENE_ROIS[scene]
    return frame[y0:y1, x0:x1]


def _contiguous_runs(indices: list[int]) -> list[list[int]]:
    runs: list[list[int]] = []
    for index in indices:
        if not runs or index != runs[-1][-1] + 1:
            runs.append([index])
        else:
            runs[-1].append(index)
    return runs


def _mouth_silence_frame_sets(
    frame_count: int,
    silence: list[tuple[float, float]],
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    """Return measured silence, excluded first silence, and boundary frames."""

    candidates = [
        index
        for index in range(MOUTH_BASELINE_FRAME_COUNT, frame_count)
        if _is_silent(index / FPS, silence)
    ]
    runs = _contiguous_runs(candidates)
    first_frames = tuple(run[0] for run in runs)
    first_frame_set = set(first_frames)
    measured = tuple(index for index in candidates if index not in first_frame_set)
    boundary_frames = tuple(run[1] for run in runs if len(run) > 1)
    return measured, first_frames, boundary_frames, tuple(candidates)


def _mouth_pixel_differences(
    frames: list[np.ndarray],
    baseline: np.ndarray,
) -> dict[int, int]:
    x0, y0, x1, y1 = MOUTH_ROI
    return {
        index: int(
            np.any(
                cv2.absdiff(frame[y0:y1, x0:x1], baseline)
                > MOUTH_BASELINE_CHANNEL_DELTA,
                axis=2,
            ).sum()
        )
        for index, frame in enumerate(
            frames[MOUTH_BASELINE_FRAME_COUNT:],
            start=MOUTH_BASELINE_FRAME_COUNT,
        )
    }


def _mouth_state_metrics(
    frames: list[np.ndarray],
    silence: list[tuple[float, float]],
) -> dict[str, object]:
    """Measure the owner's ROI contract from a video and silence timeline."""

    if len(frames) <= MOUTH_BASELINE_FRAME_COUNT:
        raise RuntimeError("Video does not contain a full one-second baseline.")
    baseline = np.median(
        np.stack(
            [
                frame[MOUTH_ROI[1] : MOUTH_ROI[3], MOUTH_ROI[0] : MOUTH_ROI[2]]
                for frame in frames[:MOUTH_BASELINE_FRAME_COUNT]
            ]
        ),
        axis=0,
    ).astype(np.uint8)
    (
        measured_silence,
        excluded_first_silence,
        boundary_frames,
        silence_candidates,
    ) = _mouth_silence_frame_sets(len(frames), silence)
    silence_candidate_set = set(silence_candidates)
    differences_by_index = _mouth_pixel_differences(frames, baseline)
    silent_differences = [
        differences_by_index[index] for index in measured_silence
    ]
    voiced_differences = [
        difference
        for index, difference in differences_by_index.items()
        if index not in silence_candidate_set
    ]
    silent_open_frame_differences = [
        {"frame_index": index, "pixel_difference": differences_by_index[index]}
        for index in measured_silence
        if differences_by_index[index] > MOUTH_OPEN_PIXEL_THRESHOLD
    ]
    voiced_closed_frame_differences = [
        {"frame_index": index, "pixel_difference": difference}
        for index, difference in differences_by_index.items()
        if index not in silence_candidate_set
        and difference <= MOUTH_OPEN_PIXEL_THRESHOLD
    ]

    silent_closed = len(silent_differences) - len(silent_open_frame_differences)
    voiced_open = len(voiced_differences) - len(voiced_closed_frame_differences)
    silent_closed_percent = round(
        100.0 * silent_closed / max(1, len(silent_differences)),
        MOUTH_STATE_PERCENT_DECIMAL_PLACES,
    )
    voiced_open_percent = round(
        100.0 * voiced_open / max(1, len(voiced_differences)),
        MOUTH_STATE_PERCENT_DECIMAL_PLACES,
    )
    silence_boundary_frame_differences = [
        {
            "frame_index": index,
            "pixel_difference": differences_by_index[index],
        }
        for index in boundary_frames
        if index in differences_by_index
    ]
    silence_boundary_closed = all(
        item["pixel_difference"] <= MOUTH_OPEN_PIXEL_THRESHOLD
        for item in silence_boundary_frame_differences
    )
    return {
        "roi_xyxy": list(MOUTH_ROI),
        "baseline_frame_count": MOUTH_BASELINE_FRAME_COUNT,
        "baseline_seconds": MOUTH_BASELINE_FRAME_COUNT / FPS,
        "baseline_channel_delta": MOUTH_BASELINE_CHANNEL_DELTA,
        "open_pixel_threshold": MOUTH_OPEN_PIXEL_THRESHOLD,
        "video_frame_cue_count": CUES_PER_VIDEO_FRAME,
        "frames_excluded_for_baseline": MOUTH_BASELINE_FRAME_COUNT,
        "silence_interval_minimum_seconds": MOUTH_SILENCE_MIN_SECONDS,
        "silence_intervals_frame_count": len(silence_candidates),
        "silence_first_frame_indices": list(excluded_first_silence),
        "silence_boundary_frame_indices": list(boundary_frames),
        "silent_frames": len(silent_differences),
        "silent_closed_frames": silent_closed,
        "silent_closed_percent": silent_closed_percent,
        "silent_median_pixel_difference": int(
            np.median(silent_differences) if silent_differences else 0
        ),
        "silent_open_frame_indices": [
            item["frame_index"] for item in silent_open_frame_differences
        ],
        "silent_open_frame_differences": silent_open_frame_differences,
        "voiced_frames": len(voiced_differences),
        "voiced_open_frames": voiced_open,
        "voiced_open_percent": voiced_open_percent,
        "voiced_median_pixel_difference": int(
            np.median(voiced_differences) if voiced_differences else 0
        ),
        "voiced_closed_frame_indices": [
            item["frame_index"] for item in voiced_closed_frame_differences
        ],
        "voiced_closed_frame_differences": voiced_closed_frame_differences,
        "silence_boundary_frame_differences": silence_boundary_frame_differences,
        "silence_boundary_closed": silence_boundary_closed,
        "minimum_required_percent": MIN_MOUTH_STATE_PERCENT,
        "gate_pass": (
            silent_closed_percent >= MIN_MOUTH_STATE_PERCENT
            and voiced_open_percent >= MIN_MOUTH_STATE_PERCENT
            and silence_boundary_closed
        ),
    }


def _changed_pixels(first: np.ndarray, second: np.ndarray) -> int:
    return int(np.any(cv2.absdiff(first, second), axis=2).sum())


def _scene_transition_frames(frames: list[np.ndarray]) -> list[int]:
    scores = []
    for index in range(1, len(frames)):
        previous = frames[index - 1][632:696, 28:1252]
        current = frames[index][632:696, 28:1252]
        scores.append(float(cv2.absdiff(previous, current).mean()))
    candidates = np.argsort(np.asarray(scores))[::-1]
    selected: list[int] = []
    for candidate in candidates.tolist():
        frame_index = candidate + 1
        if all(
            abs(frame_index - existing) >= MIN_SCENE_TRANSITION_SEPARATION_FRAMES
            for existing in selected
        ):
            selected.append(frame_index)
        if len(selected) == len(SCENE_WINDOWS) - 1:
            break
    return sorted(selected)


def _motion_metrics(
    frames: list[np.ndarray],
    silence: list[tuple[float, float]],
) -> dict[str, object]:
    per_scene = {
        str(index + 1): {
            "roi_xyxy": list(SCENE_ROIS[index]),
            "voiced_pairs": 0,
            "voiced_zero_change_pairs": 0,
            "silent_pairs": 0,
            "silent_zero_change_pairs": 0,
            "voiced_changed_pixel_counts": [],
            "silent_changed_pixel_counts": [],
            "silent_core_dark_counts": [],
        }
        for index in range(len(SCENE_WINDOWS))
    }
    transition_set = set(_scene_transition_frames(frames))
    for index in range(1, len(frames)):
        second = (index - 0.5) / FPS
        scene = _scene_at(second)
        if index in transition_set or _scene_at((index - 1) / FPS) != scene:
            continue
        changed = _changed_pixels(_roi(frames[index - 1], scene), _roi(frames[index], scene))
        item = per_scene[str(scene + 1)]
        if _is_silent(second, silence):
            item["silent_pairs"] += 1
            item["silent_changed_pixel_counts"].append(changed)
            core = frames[index][
                MOUTH_CORE_ROI[1]:MOUTH_CORE_ROI[3],
                MOUTH_CORE_ROI[0]:MOUTH_CORE_ROI[2],
            ]
            gray = cv2.cvtColor(core, cv2.COLOR_BGR2GRAY)
            item["silent_core_dark_counts"].append(
                int((gray < MOUTH_CORE_DARK_THRESHOLD).sum())
            )
            if changed == 0:
                item["silent_zero_change_pairs"] += 1
        else:
            item["voiced_pairs"] += 1
            item["voiced_changed_pixel_counts"].append(changed)
            if changed == 0:
                item["voiced_zero_change_pairs"] += 1

    voiced_pairs = sum(item["voiced_pairs"] for item in per_scene.values())
    voiced_zero = sum(
        item["voiced_zero_change_pairs"] for item in per_scene.values()
    )
    silent_pairs = sum(item["silent_pairs"] for item in per_scene.values())
    silent_zero = sum(
        item["silent_zero_change_pairs"] for item in per_scene.values()
    )
    for item in per_scene.values():
        voiced = item["voiced_pairs"]
        silent = item["silent_pairs"]
        item["voiced_zero_change_percent"] = round(
            100.0 * item["voiced_zero_change_pairs"] / max(1, voiced),
            4,
        )
        item["silent_zero_change_percent"] = round(
            100.0 * item["silent_zero_change_pairs"] / max(1, silent),
            4,
        )
        item["voiced_changed_pixel_min"] = min(
            item["voiced_changed_pixel_counts"], default=0
        )
        item["voiced_changed_pixel_max"] = max(
            item["voiced_changed_pixel_counts"], default=0
        )
        item["silent_changed_pixel_max"] = max(
            item["silent_changed_pixel_counts"], default=0
        )
        item["silent_core_dark_pixel_max"] = max(
            item["silent_core_dark_counts"], default=0
        )
        item["silent_core_closed_pairs"] = sum(
            count <= MAX_CLOSED_CORE_DARK_PIXELS
            for count in item["silent_core_dark_counts"]
        )
        item["silent_core_closed_percent"] = round(
            100.0 * item["silent_core_closed_pairs"] / max(1, silent),
            4,
        )
        del item["voiced_changed_pixel_counts"]
        del item["silent_changed_pixel_counts"]
        del item["silent_core_dark_counts"]
    return {
        "adjacent_pairs_measured": len(frames) - 1,
        "scene_transition_frames_excluded": sorted(transition_set),
        "voiced_pairs": voiced_pairs,
        "voiced_zero_change_pairs": voiced_zero,
        "voiced_zero_change_percent": round(
            100.0 * voiced_zero / max(1, voiced_pairs), 4
        ),
        "voiced_zero_change_limit_percent": MAX_VOICED_ZERO_CHANGE_PERCENT,
        "voiced_gate_pass": (
            100.0 * voiced_zero / max(1, voiced_pairs)
            <= MAX_VOICED_ZERO_CHANGE_PERCENT
        ),
        "silent_pairs": silent_pairs,
        "silent_zero_change_pairs": silent_zero,
        "silent_zero_change_percent": round(
            100.0 * silent_zero / max(1, silent_pairs), 4
        ),
        "mouth_core_roi_xyxy": list(MOUTH_CORE_ROI),
        "mouth_core_dark_threshold": MOUTH_CORE_DARK_THRESHOLD,
        "mouth_core_closed_max_dark_pixels": MAX_CLOSED_CORE_DARK_PIXELS,
        "silent_core_closed_pairs": sum(
            item["silent_core_closed_pairs"] for item in per_scene.values()
        ),
        "silent_core_closed_percent": round(
            100.0
            * sum(item["silent_core_closed_pairs"] for item in per_scene.values())
            / max(1, silent_pairs),
            4,
        ),
        "silent_core_dark_pixel_max": max(
            (item["silent_core_dark_pixel_max"] for item in per_scene.values()),
            default=0,
        ),
        "silent_core_closed_gate_pass": all(
            item["silent_core_closed_percent"] == FULL_PERCENT
            for item in per_scene.values()
            if item["silent_pairs"]
        ),
        "per_scene": per_scene,
    }


def audit(
    video: Path,
    silence_intervals: list[tuple[float, float]] | None = None,
) -> dict[str, object]:
    video = video.resolve()
    metadata = _ffprobe(video)
    frames = _frames(video)
    streams = metadata.get("streams", [])
    video_stream = next(stream for stream in streams if stream["codec_type"] == "video")
    audio_stream = next(stream for stream in streams if stream["codec_type"] == "audio")
    detected_silence = _silence_intervals(video)
    raw_mouth_silence = (
        detected_silence if silence_intervals is None else list(silence_intervals)
    )
    mouth_silence = _stable_mouth_silence_intervals(raw_mouth_silence)
    duration = float(metadata["format"]["duration"])
    return {
        "video": str(video.relative_to(ROOT)),
        "specs": {
            "width": int(video_stream["width"]),
            "height": int(video_stream["height"]),
            "fps": str(video_stream["r_frame_rate"]),
            "frame_count_decoded": len(frames),
            "duration_seconds": duration,
            "video_codec": video_stream["codec_name"],
            "audio_codec": audio_stream["codec_name"],
            "audio_sample_rate": int(audio_stream["sample_rate"]),
            "audio_channels": int(audio_stream["channels"]),
        },
        "silencedetect": {
            "filter": SILENCE_FILTER,
            "source": "ffmpeg-silencedetect",
            "intervals": [
                {"start": round(start, 6), "end": round(end, 6)}
                for start, end in detected_silence
            ],
        },
        "mouth_silence": {
            "source": (
                "ffmpeg-silencedetect"
                if silence_intervals is None
                else "provided-json"
            ),
            "filter": SILENCE_FILTER if silence_intervals is None else None,
            "minimum_duration_seconds": MOUTH_SILENCE_MIN_SECONDS,
            "intervals": [
                {"start": round(start, 6), "end": round(end, 6)}
                for start, end in mouth_silence
            ],
        },
        "scene_windows": [
            {
                "scene": index + 1,
                "start": start,
                "end": end,
                "visual_end": visual_end,
                "mouth_roi_xyxy": list(SCENE_ROIS[index]),
            }
            for index, (start, end, visual_end) in enumerate(SCENE_WINDOWS)
        ],
        "composition": {
            "character_panel_xywh": list(CHARACTER_PANEL_XYWH),
            "portrait_crop_xywh": list(PORTRAIT_CROP_XYWH),
            "face_bbox_source_xywh": list(FRONT_CROSS_FACE_BBOX_XYWH),
            "rendered_face_height_px": round(
                FRONT_CROSS_FACE_BBOX_XYWH[3] * 466 / PORTRAIT_CROP_XYWH[3],
                4,
            ),
            "minimum_required_face_height_px": HEIGHT * MIN_FACE_HEIGHT_RATIO,
            "face_gate_pass": (
                FRONT_CROSS_FACE_BBOX_XYWH[3] * 466 / PORTRAIT_CROP_XYWH[3]
                >= HEIGHT * MIN_FACE_HEIGHT_RATIO
            ),
        },
        "motion": _motion_metrics(frames, detected_silence),
        "mouth_state": _mouth_state_metrics(frames, mouth_silence),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=VIDEO)
    parser.add_argument(
        "--silence-json",
        type=Path,
        help="Use silence intervals from JSON instead of running silencedetect.",
    )
    parser.add_argument("--output", type=Path, default=EVIDENCE / "video-coherence.json")
    arguments = parser.parse_args(argv)
    silence = (
        _load_silence_intervals(arguments.silence_json)
        if arguments.silence_json is not None
        else None
    )
    result = audit(arguments.video, silence)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    mouth = result["mouth_state"]
    print(
        "MOUTH_STATE "
        f"silent_closed={mouth['silent_closed_percent']:.1f}% "
        f"({mouth['silent_closed_frames']}/{mouth['silent_frames']}) "
        f"voiced_open={mouth['voiced_open_percent']:.1f}% "
        f"({mouth['voiced_open_frames']}/{mouth['voiced_frames']}) "
        f"gate={'PASS' if mouth['gate_pass'] else 'FAIL'}",
    )
    print("MOUTH_STATE_UNQUALIFIED")
    unqualified = (
        [
            ("silent_open", item)
            for item in mouth["silent_open_frame_differences"]
        ]
        + [
            ("voiced_closed", item)
            for item in mouth["voiced_closed_frame_differences"]
        ]
    )
    if not unqualified:
        print("none")
    else:
        for category, item in unqualified:
            print(
                f"{category} frame={item['frame_index']} "
                f"pixel_difference={item['pixel_difference']}"
            )
    print(json.dumps(result["motion"], ensure_ascii=False, indent=2))
    return 0 if result["motion"]["voiced_gate_pass"] and mouth["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
