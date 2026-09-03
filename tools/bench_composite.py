"""Measure the offscreen runtime cost of MoHan's layered compositors.

The benchmark deliberately exercises the production renderers with the shipped
official appearance packs.  It does not alter the compositor implementation:
the decode audit observes the Qt constructor boundaries from a temporary probe
and restores them before returning.
"""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import platform
lazy import statistics
lazy import sys
lazy import time
lazy from collections import Counter
lazy from collections.abc import Callable, Iterator, Sequence
lazy from contextlib import contextmanager
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QImage as REAL_QIMAGE
lazy from PySide6.QtGui import QPixmap as REAL_QPIXMAP
lazy from PySide6.QtGui import QPixmapCache
lazy from PySide6.QtWidgets import QApplication

lazy from domain import outfit_pack_makeup as makeup_module
lazy from infrastructure import active_outfit_overlay as overlay_module
lazy from infrastructure import layered_face_renderer as half_module
lazy from infrastructure import layered_full_body_renderer as full_module
lazy from domain.face_rig import (
    ExpressionShape,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from infrastructure.layered_face_renderer import LayeredParametricFaceRenderer
lazy from infrastructure.layered_full_body_renderer import LayeredFullBodyRenderer
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay

SCHEMA = "mohan.composite-performance.v1"
DEFAULT_ITERATIONS = 5
DEFAULT_ROUNDS = 5
PERCENTILE_P95 = 0.95
MILLISECONDS_PER_SECOND = 1_000.0
NANOSECONDS_PER_SECOND = 1_000_000_000
HALF_BODY_SIZE = (1_254, 1_254)
FULL_BODY_SOURCE_VIEW = "yaw+000-pitch+00"
FULL_BODY_TARGET_VIEW = "yaw+015-pitch+00"
HALF_BODY_SOURCE_SILHOUETTE = "cheek-rest"
HALF_BODY_TARGET_SILHOUETTE = "front-crossed"
DECODE_AUDIT_CACHE_LIMIT = 0
ONE_ARGUMENT = 1
PATH_ARGUMENT_INDEX = 0
DATA_ARGUMENT_INDEX = 0
PNG_SUFFIX = ".png"
IMAGE_FORMAT_NAMES = (
    "Format_RGBA8888",
    "Format_ARGB32_Premultiplied",
    "Format_Grayscale8",
    "Format_Alpha8",
    "Format_ARGB32",
)


class DecodeProbe:
    """Collect Qt image-load calls without changing the returned Qt objects."""

    def __init__(self) -> None:
        self.pixmap_paths: list[str] = []
        self.image_payload_hashes: list[str] = []


def _motion(pose: FacePose, expression: str) -> FaceMotionFrame:
    return FaceMotionFrame(
        pose,
        expression,
        Viseme.CLOSED,
        MouthShape(),
        ExpressionShape(),
        breath=0.5,
    )


def _full_body_motion() -> FaceMotionFrame:
    return _motion(FacePose.FRONT, "idle_front")


def _half_body_motions() -> tuple[FaceMotionFrame, FaceMotionFrame]:
    return (
        _motion(FacePose.CHEEK, "idle"),
        _motion(FacePose.FRONT, "idle_front"),
    )


def _new_overlay(store: Path) -> ActiveOutfitOverlay:
    """Use a fresh overlay so a cold sample cannot inherit runtime state."""

    return ActiveOutfitOverlay(store, ROOT)


def _require_frame(frame) -> object:
    if frame.isNull():
        raise RuntimeError("The compositor returned a null frame.")
    return frame


def _timed(operation: Callable[[], object]) -> float:
    started = time.perf_counter_ns()
    frame = operation()
    elapsed_ns = time.perf_counter_ns() - started
    _require_frame(frame)
    return elapsed_ns / (NANOSECONDS_PER_SECOND / MILLISECONDS_PER_SECOND)


def _clear_pixmap_cache() -> None:
    QPixmapCache.clear()


def _cold_full_body_sample(store: Path, motion: FaceMotionFrame) -> float:
    _clear_pixmap_cache()
    renderer = LayeredFullBodyRenderer(outfit_overlay=_new_overlay(store))
    return _timed(
        lambda: renderer.render_view(FULL_BODY_SOURCE_VIEW, motion)
    )


def _cold_full_body_round(
    store: Path,
    motion: FaceMotionFrame,
) -> Callable[[], float]:
    def sample() -> float:
        return _cold_full_body_sample(store, motion)

    return sample


def _hot_full_body_round(
    store: Path,
    motion: FaceMotionFrame,
) -> Callable[[], float]:
    _clear_pixmap_cache()
    renderer = LayeredFullBodyRenderer(outfit_overlay=_new_overlay(store))
    _require_frame(renderer.render_view(FULL_BODY_SOURCE_VIEW, motion))
    _require_frame(renderer.render_view(FULL_BODY_TARGET_VIEW, motion))

    def sample() -> float:
        _require_frame(renderer.render_view(FULL_BODY_SOURCE_VIEW, motion))
        return _timed(
            lambda: renderer.render_view(FULL_BODY_TARGET_VIEW, motion)
        )

    return sample


def _half_frame(renderer: LayeredParametricFaceRenderer, base, motion: FaceMotionFrame):
    return renderer.render(base, motion, None)


def _new_half_base():
    base = REAL_QPIXMAP(*HALF_BODY_SIZE)
    base.fill(Qt.transparent)
    return base


def _hot_half_body_round(
    store: Path,
    source_motion: FaceMotionFrame,
    target_motion: FaceMotionFrame,
) -> Callable[[], float]:
    _clear_pixmap_cache()
    renderer = LayeredParametricFaceRenderer(outfit_overlay=_new_overlay(store))
    base = _new_half_base()
    _require_frame(_half_frame(renderer, base, source_motion))
    _require_frame(_half_frame(renderer, base, target_motion))

    def sample() -> float:
        _require_frame(_half_frame(renderer, base, source_motion))
        return _timed(lambda: _half_frame(renderer, base, target_motion))

    return sample


def _percentile(values: Sequence[float], ratio: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a percentile from no samples.")
    ordered = sorted(values)
    position = (len(ordered) - 1) * ratio
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _summary(samples_ms: Sequence[float]) -> dict[str, object]:
    values = tuple(float(value) for value in samples_ms)
    return {
        "count": len(values),
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(_percentile(values, PERCENTILE_P95), 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


def _scatter(round_summaries: Sequence[dict[str, object]]) -> dict[str, object]:
    medians = tuple(float(item["median_ms"]) for item in round_summaries)
    p95s = tuple(float(item["p95_ms"]) for item in round_summaries)
    median_center = statistics.median(medians)
    p95_center = statistics.median(p95s)
    return {
        "round_medians_ms": [round(value, 3) for value in medians],
        "round_p95s_ms": [round(value, 3) for value in p95s],
        "median_min_ms": round(min(medians), 3),
        "median_max_ms": round(max(medians), 3),
        "median_spread_ms": round(max(medians) - min(medians), 3),
        "median_spread_percent": round(
            (max(medians) - min(medians)) / median_center * 100.0,
            3,
        )
        if median_center
        else 0.0,
        "p95_min_ms": round(min(p95s), 3),
        "p95_max_ms": round(max(p95s), 3),
        "p95_spread_ms": round(max(p95s) - min(p95s), 3),
        "p95_spread_percent": round(
            (max(p95s) - min(p95s)) / p95_center * 100.0,
            3,
        )
        if p95_center
        else 0.0,
    }


def _measure_rounds(
    round_factory: Callable[[], Callable[[], float]],
    *,
    iterations: int,
    rounds: int,
) -> dict[str, object]:
    round_records: list[dict[str, object]] = []
    all_samples: list[float] = []
    for round_index in range(rounds):
        sample_factory = round_factory()
        samples = [sample_factory() for _ in range(iterations)]
        all_samples.extend(samples)
        round_records.append(
            {
                "round": round_index + 1,
                "samples_ms": [round(value, 3) for value in samples],
                "summary": _summary(samples),
            }
        )
    summaries = [record["summary"] for record in round_records]
    return {
        "iterations_per_round": iterations,
        "round_count": rounds,
        "rounds": round_records,
        "summary": _summary(all_samples),
        "round_scatter": _scatter(summaries),
    }


def _repo_relative(path_text: str) -> str:
    path = Path(path_text)
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return "<outside-project>"


def _decode_summary(
    pixmap_paths: Sequence[str],
    image_payload_hashes: Sequence[str],
) -> dict[str, object]:
    path_counts = Counter(pixmap_paths)
    payload_counts = Counter(image_payload_hashes)
    repeated_paths = [
        {"path": _repo_relative(path), "count": count}
        for path, count in sorted(path_counts.items())
        if count > ONE_ARGUMENT
    ]
    repeated_payloads = [
        {"sha256": digest, "count": count}
        for digest, count in sorted(payload_counts.items())
        if count > ONE_ARGUMENT
    ]
    return {
        "q_pixmap_path_load_calls": len(pixmap_paths),
        "q_pixmap_unique_paths": len(path_counts),
        "q_pixmap_repeated_paths": repeated_paths,
        "q_image_from_data_calls": len(image_payload_hashes),
        "q_image_unique_payloads": len(payload_counts),
        "q_image_repeated_payloads": repeated_payloads,
    }


def _probe_mark(probe: DecodeProbe) -> tuple[int, int]:
    return (len(probe.pixmap_paths), len(probe.image_payload_hashes))


def _probe_delta(
    probe: DecodeProbe,
    mark: tuple[int, int],
) -> dict[str, object]:
    return _decode_summary(
        probe.pixmap_paths[mark[0] :],
        probe.image_payload_hashes[mark[1] :],
    )


@contextmanager
def _decode_probe() -> Iterator[DecodeProbe]:
    """Patch only module-local Qt symbols for a bounded decode audit."""

    probe = DecodeProbe()

    def pixmap_loader(*args, **kwargs):
        if (
            len(args) > PATH_ARGUMENT_INDEX
            and isinstance(args[PATH_ARGUMENT_INDEX], (str, os.PathLike))
        ):
            probe.pixmap_paths.append(str(args[PATH_ARGUMENT_INDEX]))
        return REAL_QPIXMAP(*args, **kwargs)

    def pixmap_from_image(*args, **kwargs):
        return REAL_QPIXMAP.fromImage(*args, **kwargs)

    def image_loader(*args, **kwargs):
        return REAL_QIMAGE(*args, **kwargs)

    def image_from_data(*args, **kwargs):
        data = (
            args[DATA_ARGUMENT_INDEX]
            if len(args) > DATA_ARGUMENT_INDEX
            else kwargs.get("data")
        )
        if isinstance(data, (bytes, bytearray, memoryview)):
            probe.image_payload_hashes.append(
                hashlib.sha256(bytes(data)).hexdigest()
            )
        return REAL_QIMAGE.fromData(*args, **kwargs)

    setattr(pixmap_loader, "fromImage", pixmap_from_image)
    for name in IMAGE_FORMAT_NAMES:
        setattr(image_loader, name, getattr(REAL_QIMAGE, name))
    setattr(image_loader, "fromData", image_from_data)

    patched = (
        (full_module, "QPixmap", pixmap_loader),
        (half_module, "QPixmap", pixmap_loader),
        (overlay_module, "QPixmap", pixmap_loader),
        (overlay_module, "QImage", image_loader),
        (makeup_module, "QImage", image_loader),
    )
    originals = tuple((module, name, getattr(module, name)) for module, name, _ in patched)
    previous_limit = QPixmapCache.cacheLimit()
    QPixmapCache.setCacheLimit(DECODE_AUDIT_CACHE_LIMIT)
    try:
        for module, name, replacement in patched:
            setattr(module, name, replacement)
        yield probe
    finally:
        for module, name, original in originals:
            setattr(module, name, original)
        QPixmapCache.setCacheLimit(previous_limit)


def _audit_full_body_switch(store: Path, motion: FaceMotionFrame) -> dict[str, object]:
    _clear_pixmap_cache()
    with _decode_probe() as probe:
        renderer = LayeredFullBodyRenderer(outfit_overlay=_new_overlay(store))
        _require_frame(renderer.render_view(FULL_BODY_SOURCE_VIEW, motion))
        mark = _probe_mark(probe)
        _require_frame(renderer.render_view(FULL_BODY_TARGET_VIEW, motion))
        first_switch = _probe_delta(probe, mark)
        mark = _probe_mark(probe)
        _require_frame(renderer.render_view(FULL_BODY_SOURCE_VIEW, motion))
        _require_frame(renderer.render_view(FULL_BODY_TARGET_VIEW, motion))
        hot_switch = _probe_delta(probe, mark)
    return {
        "source": FULL_BODY_SOURCE_VIEW,
        "target": FULL_BODY_TARGET_VIEW,
        "first_target_load_after_source": first_switch,
        "hot_switch_after_both_loaded": hot_switch,
    }


def _audit_half_body_switch(
    store: Path,
    source_motion: FaceMotionFrame,
    target_motion: FaceMotionFrame,
) -> dict[str, object]:
    _clear_pixmap_cache()
    with _decode_probe() as probe:
        renderer = LayeredParametricFaceRenderer(outfit_overlay=_new_overlay(store))
        base = _new_half_base()
        _require_frame(_half_frame(renderer, base, source_motion))
        mark = _probe_mark(probe)
        _require_frame(_half_frame(renderer, base, target_motion))
        first_switch = _probe_delta(probe, mark)
        mark = _probe_mark(probe)
        _require_frame(_half_frame(renderer, base, source_motion))
        _require_frame(_half_frame(renderer, base, target_motion))
        hot_switch = _probe_delta(probe, mark)
    return {
        "source": HALF_BODY_SOURCE_SILHOUETTE,
        "target": HALF_BODY_TARGET_SILHOUETTE,
        "first_target_load_after_source": first_switch,
        "hot_switch_after_both_loaded": hot_switch,
    }


def _has_repeated_decode(audit: dict[str, object]) -> bool:
    return bool(
        audit["q_pixmap_repeated_paths"]
        or audit["q_image_repeated_payloads"]
    )


def _decode_audit(store: Path) -> dict[str, object]:
    full = _audit_full_body_switch(store, _full_body_motion())
    half_source, half_target = _half_body_motions()
    half = _audit_half_body_switch(store, half_source, half_target)
    full_first = full["first_target_load_after_source"]
    half_first = half["first_target_load_after_source"]
    return {
        "method": (
            "Count QPixmap(path) and QImage.fromData calls with "
            "QPixmapCache disabled for this audit only."
        ),
        "q_pixmap_cache_limit_during_audit": DECODE_AUDIT_CACHE_LIMIT,
        "full_body": full,
        "half_body": half,
        "conclusion": {
            "repeated_png_decode_calls_on_first_full_body_switch": _has_repeated_decode(full_first),
            "repeated_png_decode_calls_on_first_half_body_switch": _has_repeated_decode(half_first),
            "new_decode_calls_on_hot_full_body_switch": bool(
                full["hot_switch_after_both_loaded"]["q_pixmap_path_load_calls"]
                or full["hot_switch_after_both_loaded"]["q_image_from_data_calls"]
            ),
            "new_decode_calls_on_hot_half_body_switch": bool(
                half["hot_switch_after_both_loaded"]["q_pixmap_path_load_calls"]
                or half["hot_switch_after_both_loaded"]["q_image_from_data_calls"]
            ),
        },
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args(tuple(argv or ()))
    if arguments.iterations <= 0 or arguments.rounds <= 0:
        parser.error("--iterations and --rounds must be positive")
    return arguments


def _result(iterations: int, rounds: int) -> dict[str, object]:
    app = QApplication.instance() or QApplication([])
    del app
    full_motion = _full_body_motion()
    half_source, half_target = _half_body_motions()
    with TemporaryDirectory(prefix="mohan-composite-bench-") as raw_store:
        store = Path(raw_store) / "store"
        measurements = {
            "cold_full_body": _measure_rounds(
                lambda: _cold_full_body_round(store, full_motion),
                iterations=iterations,
                rounds=rounds,
            ),
            "hot_full_body_view_switch": _measure_rounds(
                lambda: _hot_full_body_round(store, full_motion),
                iterations=iterations,
                rounds=rounds,
            ),
            "hot_half_body_silhouette_switch": _measure_rounds(
                lambda: _hot_half_body_round(
                    store,
                    half_source,
                    half_target,
                ),
                iterations=iterations,
                rounds=rounds,
            ),
        }
        decode_audit = _decode_audit(store)
    return {
        "schema": SCHEMA,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "qt_qpa_platform": os.environ.get("QT_QPA_PLATFORM"),
            "qt_offscreen": os.environ.get("QT_QPA_PLATFORM") == "offscreen",
        },
        "configuration": {
            "iterations_per_round": iterations,
            "rounds": rounds,
            "percentile": "linear interpolation over sorted samples",
            "asset_root": "assets/pose-atlas/v5-base-layered",
            "official_appearance": (
                "built-in official blue-white Hanfu outfit with classic makeup; "
                "accessory slots remain builtin/none"
            ),
            "full_body_canvas": [1_024, 1_536],
            "half_body_canvas": list(HALF_BODY_SIZE),
            "full_body_switch_views": [
                FULL_BODY_SOURCE_VIEW,
                FULL_BODY_TARGET_VIEW,
            ],
            "half_body_switch_silhouettes": [
                HALF_BODY_SOURCE_SILHOUETTE,
                HALF_BODY_TARGET_SILHOUETTE,
            ],
        },
        "measurements": measurements,
        "decode_audit": decode_audit,
    }


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _arguments(argv)
    result = _result(arguments.iterations, arguments.rounds)
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if arguments.output is not None:
        arguments.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
