"""Complete expression frames own coordinated head and eye pixels atomically."""

from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy from dataclasses import replace
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import pytest
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
lazy from PySide6.QtCore import QRect
lazy from PySide6.QtGui import QRegion
lazy from PySide6.QtWidgets import QApplication
lazy from domain.face_rig import (
    ExpressionShape,
    EyeState,
    FaceMotionFrame,
    FacePose,
    MouthShape,
    Viseme,
)
lazy from infrastructure import layered_full_body_assets as assets
lazy from infrastructure.layered_full_body_renderer import (
    MOUTH_APERTURE_THRESHOLD,
    LayeredFullBodyRenderer,
)
lazy from infrastructure.active_outfit_overlay import ActiveOutfitOverlay
lazy from infrastructure.appearance_layer_stack import AppearanceLayerStack

VIEW = "complete-expression-test-view"
CANVAS = (40, 40)
EYE_POINT = (10, 10)
OUTLINE_POINT = (30, 30)
MOUTH_POINT = (20, 20)
HAIR_POINT = (35, 5)
OPAQUE_ALPHA = 255
SOFT_MASK_ALPHA = 128
SOFT_BLEND_TOLERANCE = 2
STATE_COLORS = {
    EyeState.REST: (21, 101, 192, 255),
    EyeState.HALF: (216, 116, 32, 255),
    EyeState.CLOSED: (136, 44, 169, 255),
}
NEUTRAL_COLORS = {
    EyeState.REST: (31, 131, 72, 255),
    EyeState.HALF: (181, 91, 24, 255),
    EyeState.CLOSED: (108, 30, 133, 255),
}


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _write_png(
    path: Path,
    *,
    fill: tuple[int, int, int, int] = (80, 80, 80, 255),
    point: tuple[int, int] | None = None,
    point_color: tuple[int, int, int, int] | None = None,
    transparent_corner: bool = True,
    size: tuple[int, int] = CANVAS,
    opaque_rect: tuple[int, int, int, int] | None = None,
) -> None:
    image = QImage(size[0], size[1], QImage.Format_RGBA8888)
    image.fill(QColor(*fill))
    if transparent_corner:
        image.setPixelColor(0, 0, QColor(0, 0, 0, 0))
    if point is not None and point_color is not None:
        image.setPixelColor(*point, QColor(*point_color))
    if opaque_rect is not None:
        left, top, right, bottom = opaque_rect
        for y in range(top, bottom):
            for x in range(left, right):
                image.setPixelColor(x, y, QColor(255, 255, 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    assert image.save(str(path), "PNG")


def _group(
    root: Path,
    *,
    missing: tuple[Viseme, EyeState] | None = None,
    with_oral_masks: bool = False,
    with_neutral: bool = False,
    motion_policy: str = assets.COMPLETE_EXPRESSION_MOTION_POLICY,
    with_replacement_mask: bool = False,
) -> assets.CompleteExpressionFrameSet:
    frames: dict[Viseme, frozendict[EyeState, Path]] = {}
    oral_masks: dict[Viseme, frozendict[EyeState, Path]] = {}
    for viseme in assets.SPOKEN_VISEMES:
        state_paths: dict[EyeState, Path] = {}
        mask_paths: dict[EyeState, Path] = {}
        for state in assets.COMPLETE_EXPRESSION_STATES:
            if missing == (viseme, state):
                continue
            path = root / "frames" / f"{viseme.value.lower()}-{state.value}.png"
            _write_png(
                path,
                fill=(0, 0, 0, 0) if with_replacement_mask else STATE_COLORS[state],
                point=None if with_replacement_mask else EYE_POINT,
                point_color=None if with_replacement_mask else STATE_COLORS[state],
                opaque_rect=(7, 7, 26, 26) if with_replacement_mask else None,
            )
            if with_replacement_mask:
                image = QImage(str(path))
                image.setPixelColor(*EYE_POINT, QColor(*STATE_COLORS[state]))
                assert image.save(str(path), "PNG")
            state_paths[state] = path
            if with_oral_masks:
                mask = root / "masks" / f"{viseme.value.lower()}-{state.value}.png"
                _write_png(
                    mask,
                    fill=(0, 0, 0, 0),
                    point=MOUTH_POINT,
                    point_color=(255, 255, 255, 255),
                )
                mask_paths[state] = mask
        frames[viseme] = frozendict(state_paths)
        if with_oral_masks:
            oral_masks[viseme] = frozendict(mask_paths)
    neutral_frames: dict[EyeState, Path] = {}
    if with_neutral:
        for state in assets.COMPLETE_EXPRESSION_STATES:
            path = root / "neutral" / f"{state.value}.png"
            _write_png(
                path,
                fill=NEUTRAL_COLORS[state],
                point=OUTLINE_POINT,
                point_color=NEUTRAL_COLORS[state],
            )
            neutral_frames[state] = path
    replacement_mask: Path | None = None
    if with_replacement_mask:
        replacement_mask = root / "replacement-mask.png"
        _write_png(
            replacement_mask,
            fill=(0, 0, 0, 0),
            opaque_rect=(3, 3, 28, 28),
        )
    return assets.CompleteExpressionFrameSet(
        "complete-test-group-01",
        "approved-source-06",
        frozendict(frames),
        frozendict(oral_masks),
        frozendict(neutral_frames),
        motion_policy,
        replacement_mask,
    )


def _view(
    root: Path,
    *,
    group: assets.CompleteExpressionFrameSet | None = None,
    blink: bool = False,
    speech: bool = False,
    with_motion_layers: bool = False,
) -> assets.LayeredFullBodyView:
    body = root / "body.png"
    _write_png(body, fill=(62, 62, 62, 255), point=OUTLINE_POINT,
               point_color=(62, 62, 62, 255), transparent_corner=False)
    layers: dict[str, Path] = {"body": body}
    blink_frames: dict[EyeState, Path] = {}
    if blink:
        for state, color in (
            (EyeState.HALF, (255, 0, 0, 255)),
            (EyeState.CLOSED, (0, 0, 255, 255)),
        ):
            path = root / f"legacy-{state.value}.png"
            _write_png(path, fill=(0, 0, 0, 0), point=EYE_POINT,
                       point_color=color)
            blink_frames[state] = path
    speech_frames: dict[Viseme, Path] = {}
    if speech:
        path = root / "legacy-speech-a.png"
        _write_png(path, fill=(0, 0, 0, 0), point=MOUTH_POINT,
                   point_color=(255, 255, 255, 255))
        speech_frames[Viseme.A] = path
    if with_motion_layers:
        sleeve = root / "sleeve-left.png"
        _write_png(
            sleeve,
            fill=(0, 0, 0, 0),
            point=(12, 30),
            point_color=(230, 200, 40, 255),
        )
        layers["sleeve_left"] = sleeve
        old_head_edge = root / "old-head-edge.png"
        _write_png(
            old_head_edge,
            fill=(0, 0, 0, 0),
            point=(4, 4),
            point_color=(240, 20, 20, 255),
        )
        layers["hair_left"] = old_head_edge
    return assets.LayeredFullBodyView(
        VIEW,
        frozendict(layers),
        blink_frames=frozendict(blink_frames),
        speech_frames=frozendict(speech_frames),
        complete_expression_frames=group,
    )


def _motion(
    viseme: Viseme = Viseme.A,
    *,
    aperture: float = 0.6,
    blink: float = 0.0,
) -> FaceMotionFrame:
    return FaceMotionFrame(
        FacePose.FRONT,
        "complete_expression_test",
        viseme,
        MouthShape(aperture=aperture),
        ExpressionShape(blink=blink),
        breath=0.5,
    )


def _rgba(pixmap: QPixmap, point: tuple[int, int]) -> tuple[int, int, int, int]:
    color = pixmap.toImage().pixelColor(*point)
    return color.red(), color.green(), color.blue(), color.alpha()


def _pixel_grid(pixmap: QPixmap) -> tuple[tuple[int, int, int, int], ...]:
    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    return tuple(
        (
            image.pixelColor(x, y).red(),
            image.pixelColor(x, y).green(),
            image.pixelColor(x, y).blue(),
            image.pixelColor(x, y).alpha(),
        )
        for y in range(image.height())
        for x in range(image.width())
    )


def _contains_color(
    pixmap: QPixmap,
    color: tuple[int, int, int, int],
    rect: tuple[int, int, int, int],
) -> bool:
    image = pixmap.toImage()
    left, top, right, bottom = rect
    return any(
        image.pixelColor(x, y).getRgb() == color
        for y in range(top, bottom)
        for x in range(left, right)
    )


def test_complete_expression_selects_eye_states_and_owns_full_outline(tmp_path: Path) -> None:
    _app()
    group = _group(tmp_path)
    view = _view(tmp_path, group=group, blink=True)
    renderer = LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))

    for blink, state in ((0.0, EyeState.REST), (0.5, EyeState.HALF), (1.0, EyeState.CLOSED)):
        result = renderer.render_view(VIEW, _motion(blink=blink)).toImage()
        assert _rgba(QPixmap.fromImage(result), EYE_POINT) == STATE_COLORS[state]
        assert _rgba(QPixmap.fromImage(result), OUTLINE_POINT) == STATE_COLORS[state]


def test_complete_expression_rejects_missing_eye_state_at_initialization(tmp_path: Path) -> None:
    _app()
    group = _group(tmp_path, missing=(Viseme.A, EyeState.HALF))
    view = _view(tmp_path, group=group)
    with pytest.raises(ValueError, match="rest/half/closed"):
        LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))


def test_optional_neutral_group_owns_closed_mouth_rest_without_forcing_oral_mask(
    tmp_path: Path,
) -> None:
    _app()
    group = _group(tmp_path, with_neutral=True)
    view = _view(tmp_path, group=group, blink=True)
    renderer = LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))
    result = renderer.render_view(VIEW, _motion(Viseme.CLOSED, aperture=0.0, blink=0.5)).toImage()
    assert result.pixelColor(*EYE_POINT) == QColor(*NEUTRAL_COLORS[EyeState.HALF])
    assert result.pixelColor(*OUTLINE_POINT) == QColor(*NEUTRAL_COLORS[EyeState.HALF])


def test_closed_positive_aperture_keeps_the_consonant_transition_with_neutral_frames(
    tmp_path: Path,
) -> None:
    _app()
    group = _group(tmp_path, with_neutral=True)
    view = _view(tmp_path, group=group)
    renderer = LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))
    result = renderer.render_view(
        VIEW,
        _motion(Viseme.CLOSED, aperture=MOUTH_APERTURE_THRESHOLD + 0.02),
    ).toImage()
    assert result.pixelColor(*OUTLINE_POINT) == QColor(*STATE_COLORS[EyeState.REST])
    assert result.pixelColor(*OUTLINE_POINT) != QColor(*NEUTRAL_COLORS[EyeState.REST])


def test_preserve_body_layers_replaces_head_region_and_keeps_motion_inputs(tmp_path: Path) -> None:
    _app()
    group = _group(
        tmp_path,
        motion_policy=assets.COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY,
        with_replacement_mask=True,
    )
    view = _view(tmp_path, group=group, with_motion_layers=True)
    renderer = LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))

    neutral = renderer.render_view(VIEW, _motion())
    low_energy = renderer.render_view(
        VIEW,
        _motion(),
        pose_id="greeting-wave",
        left_hand="open-left",
        body_energy=0.2,
    )
    high_energy = renderer.render_view(
        VIEW,
        _motion(),
        pose_id="greeting-wave",
        left_hand="open-left",
        body_energy=0.8,
    )
    gesture = renderer.render_view(VIEW, _motion(), gesture_beat=True)

    for result in (neutral, low_energy, high_energy, gesture):
        assert _contains_color(
            result, STATE_COLORS[EyeState.REST], (7, 7, 28, 28)
        )
    assert _rgba(neutral, (4, 4))[3] == 0
    assert _pixel_grid(neutral) != _pixel_grid(low_energy)
    assert _pixel_grid(low_energy) != _pixel_grid(high_energy)
    assert _pixel_grid(neutral) != _pixel_grid(gesture)


def test_replacement_region_soft_edge_is_premultiplied_and_clears_transparent_source(
    tmp_path: Path,
) -> None:
    _app()
    group = _group(
        tmp_path,
        motion_policy=assets.COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY,
        with_replacement_mask=True,
    )
    assert group.replacement_mask is not None
    soft_mask = QImage(CANVAS[0], CANVAS[1], QImage.Format_RGBA8888)
    soft_mask.fill(QColor(0, 0, 0, 0))
    soft_mask.setPixelColor(4, 4, QColor(255, 255, 255, 255))
    soft_mask.setPixelColor(8, 8, QColor(255, 255, 255, SOFT_MASK_ALPHA))
    assert soft_mask.save(str(group.replacement_mask), "PNG")
    view = _view(tmp_path, group=group, with_motion_layers=True)
    renderer = LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))

    result = renderer.render_view(VIEW, _motion())
    blended = _rgba(result, (8, 8))
    expected_channel = round((62 * (OPAQUE_ALPHA - SOFT_MASK_ALPHA) + 255 * SOFT_MASK_ALPHA) / OPAQUE_ALPHA)
    assert blended[3] == OPAQUE_ALPHA
    assert all(abs(channel - expected_channel) <= SOFT_BLEND_TOLERANCE for channel in blended[:3])
    assert _rgba(result, (4, 4))[3] == 0


def test_preserve_body_layers_requires_a_hashed_same_canvas_replacement_mask(
    tmp_path: Path,
) -> None:
    _app()
    group = _group(
        tmp_path,
        motion_policy=assets.COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY,
    )
    view = _view(tmp_path, group=group)
    with pytest.raises(ValueError, match="replacement_mask"):
        LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))


def test_preserve_body_layers_rejects_a_replacement_mask_with_the_wrong_canvas(
    tmp_path: Path,
) -> None:
    _app()
    group = _group(
        tmp_path,
        motion_policy=assets.COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY,
        with_replacement_mask=True,
    )
    bad_mask = tmp_path / "bad-replacement-mask.png"
    _write_png(bad_mask, fill=(0, 0, 0, 0), opaque_rect=(1, 1, 4, 4), size=(8, 8))
    view = _view(tmp_path, group=replace(group, replacement_mask=bad_mask))
    with pytest.raises(ValueError, match="canvas mismatch"):
        LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))


def test_versioned_sidecar_loads_sha_bound_expression_group_and_rejects_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(assets, "VIEW_IDS", (VIEW,))
    monkeypatch.setattr(assets, "FULL_BODY_DIMENSION_WIDTH", CANVAS[0])
    monkeypatch.setattr(assets, "FULL_BODY_DIMENSION_HEIGHT", CANVAS[1])
    group = _group(
        tmp_path,
        with_neutral=True,
        motion_policy=assets.COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY,
        with_replacement_mask=True,
    )
    records: dict[str, dict[str, dict[str, str]]] = {}
    for viseme in assets.SPOKEN_VISEMES:
        records[viseme.value] = {}
        for state in assets.COMPLETE_EXPRESSION_STATES:
            path = group.frame(viseme, state)
            records[viseme.value][state.value] = {
                "path": path.relative_to(tmp_path).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    neutral_records: dict[str, dict[str, str]] = {}
    for state in assets.COMPLETE_EXPRESSION_STATES:
        path = group.neutral_frames[state]
        neutral_records[state.value] = {
            "path": path.relative_to(tmp_path).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    assert group.replacement_mask is not None
    replacement_record = {
        "path": group.replacement_mask.relative_to(tmp_path).as_posix(),
        "sha256": hashlib.sha256(group.replacement_mask.read_bytes()).hexdigest(),
    }
    manifest_path = tmp_path / assets.COMPLETE_EXPRESSION_MANIFEST_NAME

    def write_manifest(payload: dict) -> None:
        manifest_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    payload = {
        "schema": assets.COMPLETE_EXPRESSION_SCHEMA,
        "version": assets.COMPLETE_EXPRESSION_VERSION,
        "views": {
            VIEW: {
                "source_group_id": "complete-test-group-01",
                "source_lineage": {"approval": "source-06", "revision": 1},
                "motion_policy": assets.COMPLETE_EXPRESSION_PRESERVE_BODY_POLICY,
                "frames": records,
                "neutral_frames": neutral_records,
                "replacement_mask": replacement_record,
            },
        },
    }
    write_manifest(payload)
    loaded = assets._load_complete_expression_manifest(tmp_path)
    loaded_group = loaded[VIEW]
    assert loaded_group.source_lineage == '{"approval":"source-06","revision":1}'
    assert loaded_group.frame(Viseme.A, EyeState.HALF) == group.frame(Viseme.A, EyeState.HALF)
    assert loaded_group.neutral_frames[EyeState.CLOSED] == group.neutral_frames[EyeState.CLOSED]
    assert loaded_group.replacement_mask == group.replacement_mask

    payload["views"][VIEW]["replacement_mask"]["sha256"] = "0" * 64
    write_manifest(payload)
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        assets._load_complete_expression_manifest(tmp_path)

    payload["views"][VIEW]["replacement_mask"] = replacement_record
    del payload["views"][VIEW]["frames"][Viseme.A.value][EyeState.HALF.value]
    write_manifest(payload)
    with pytest.raises(ValueError, match="rest/half/closed"):
        assets._load_complete_expression_manifest(tmp_path)


def test_versioned_sidecar_rejects_boolean_and_float_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(assets, "VIEW_IDS", (VIEW,))
    monkeypatch.setattr(assets, "FULL_BODY_DIMENSION_WIDTH", CANVAS[0])
    monkeypatch.setattr(assets, "FULL_BODY_DIMENSION_HEIGHT", CANVAS[1])
    group = _group(tmp_path)
    records: dict[str, dict[str, dict[str, str]]] = {}
    for viseme in assets.SPOKEN_VISEMES:
        records[viseme.value] = {
            state.value: {
                "path": group.frame(viseme, state).relative_to(tmp_path).as_posix(),
                "sha256": hashlib.sha256(group.frame(viseme, state).read_bytes()).hexdigest(),
            }
            for state in assets.COMPLETE_EXPRESSION_STATES
        }
    manifest_path = tmp_path / assets.COMPLETE_EXPRESSION_MANIFEST_NAME
    payload = {
        "schema": assets.COMPLETE_EXPRESSION_SCHEMA,
        "version": assets.COMPLETE_EXPRESSION_VERSION,
        "views": {
            VIEW: {
                "source_group_id": "complete-test-group-01",
                "source_lineage": "approved-source-06",
                "frames": records,
            },
        },
    }
    for invalid_version in (True, 1.0):
        payload["version"] = invalid_version
        manifest_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with pytest.raises(ValueError, match="schema/version"):
            assets._load_complete_expression_manifest(tmp_path)


def test_complete_expression_rejects_unknown_motion_policy(tmp_path: Path) -> None:
    group = _group(tmp_path)
    malformed = replace(group, motion_policy="pose_bound")
    view = _view(tmp_path, group=malformed)
    with pytest.raises(ValueError, match="motion_policy"):
        LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))


@pytest.mark.parametrize(
    "kwargs",
    (
        {"pose_id": "greeting-wave"},
        {"left_hand": "open-left"},
        {"right_hand": "open-right"},
        {"body_energy": 0.8},
        {"gesture_beat": True},
    ),
)
def test_complete_expression_rejects_unrepresentable_body_motion(
    tmp_path: Path,
    kwargs: dict[str, object],
) -> None:
    _app()
    group = _group(tmp_path)
    view = _view(tmp_path, group=group)
    renderer = LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))
    with pytest.raises(ValueError, match="neutral_body_only"):
        renderer.render_view(VIEW, _motion(), **kwargs)


@pytest.mark.parametrize("field", ("neutral_frames", "oral_masks"))
def test_malformed_complete_expression_optional_mapping_raises_value_error(
    tmp_path: Path,
    field: str,
) -> None:
    _app()
    group = _group(tmp_path)
    malformed = replace(group, **{field: None})
    view = _view(tmp_path, group=malformed)
    with pytest.raises(ValueError, match=f"{field}.*mapping"):
        LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))


def test_complete_expression_restores_oral_pixels_after_makeup_before_front_hair(
    tmp_path: Path,
) -> None:
    _app()
    group = _group(tmp_path, with_oral_masks=True)
    view = _view(tmp_path, group=group)
    events: list[str] = []
    makeup_options: list[tuple[frozenset[str], str]] = []

    class Overlay:
        def apply_animated(
            self, frame, view_id, paint_motion, *, paint_after_makeup=None, **options,
        ):
            del view_id
            makeup_options.append((frozenset(options["suppress_makeup_slots"]), options["eye_state"]))
            paint_motion(frame)
            events.append("motion")
            painter = QPainter(frame)
            painter.fillRect(MOUTH_POINT[0], MOUTH_POINT[1], 1, 1, QColor("red"))
            painter.end()
            events.append("makeup")
            if paint_after_makeup is not None:
                paint_after_makeup(frame)
                events.append("oral")
            painter = QPainter(frame)
            painter.fillRect(HAIR_POINT[0], HAIR_POINT[1], 1, 1, QColor("black"))
            painter.end()
            events.append("front_hair")
            return frame

    renderer = LayeredFullBodyRenderer(
        assets.LayeredFullBodyManifest(frozendict({VIEW: view})),
        outfit_overlay=Overlay(),
    )
    result = renderer.render_view(VIEW, _motion()).toImage()
    assert events == ["motion", "makeup", "oral", "front_hair"]
    assert makeup_options == [(frozenset(), "rest")]
    assert result.pixelColor(*MOUTH_POINT) == QColor(*STATE_COLORS[EyeState.REST])
    assert result.pixelColor(*HAIR_POINT) == QColor("black")


def test_complete_expression_protects_only_non_rest_eye_states(tmp_path: Path) -> None:
    _app()
    group = _group(tmp_path)
    view = _view(tmp_path, group=group)
    observed: list[tuple[frozenset[str], str]] = []

    class Overlay:
        def apply_animated(
            self, frame, view_id, paint_motion, *, paint_after_makeup=None, **options,
        ):
            del view_id, paint_after_makeup
            observed.append((frozenset(options["suppress_makeup_slots"]), options["eye_state"]))
            paint_motion(frame)
            return frame

    renderer = LayeredFullBodyRenderer(
        assets.LayeredFullBodyManifest(frozendict({VIEW: view})),
        outfit_overlay=Overlay(),
    )
    renderer.render_view(VIEW, _motion(blink=0.5))
    renderer.render_view(VIEW, _motion(blink=1.0))
    assert observed == [
        (frozenset({"eyes"}), "half"),
        (frozenset({"eyes"}), "closed"),
    ]


def test_missing_complete_group_preserves_legacy_blink_and_speech_routes(tmp_path: Path) -> None:
    _app()
    view = _view(tmp_path, blink=True, speech=True)
    renderer = LayeredFullBodyRenderer(assets.LayeredFullBodyManifest(frozendict({VIEW: view})))
    half = renderer.render_view(VIEW, _motion(aperture=0.0, blink=0.5)).toImage()
    assert half.pixelColor(*EYE_POINT) == QColor(255, 0, 0, 255)
    speech = renderer.render_view(VIEW, _motion(aperture=0.6)).toImage()
    assert speech.pixelColor(*MOUTH_POINT) == QColor(255, 255, 255, 255)


def _restoring_outfit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, fail_makeup: bool):
    overlay = ActiveOutfitOverlay(tmp_path / "store", tmp_path, visible_hand_region=None)
    clip = QRegion(QRect(0, 0, *CANVAS))
    old_skin = QPixmap(*CANVAS)
    old_skin.fill(QColor("green"))
    garment = QPixmap(*CANVAS)
    garment.fill(QColor(0, 0, 0, 0))
    painter = QPainter(garment)
    painter.fillRect(10, 24, 1, 1, QColor("cyan"))
    painter.end()
    rear = QPixmap(*CANVAS)
    rear.fill(QColor(0, 0, 0, 0))
    painter = QPainter(rear)
    painter.fillRect(4, 4, 1, 1, QColor("red"))
    painter.end()
    stack = AppearanceLayerStack(((rear, 0, 0, clip, 1.0),), ((garment, 0, 0, clip, 1.0),))

    def active_layers(*args, categories, **kwargs):
        if categories == frozenset({"makeup"}):
            if fail_makeup:
                raise OSError("Makeup archive is unavailable")
            return AppearanceLayerStack((), ())
        return stack

    monkeypatch.setattr(overlay, "_refresh_state", lambda: None)
    monkeypatch.setattr(overlay, "_reviewed_frame", lambda *args, **kwargs: None)
    monkeypatch.setattr(overlay, "_active_layers", active_layers)
    monkeypatch.setattr(overlay, "_garment_is_active", lambda: True)
    monkeypatch.setattr(overlay, "_official_outfit_is_active", lambda: False)
    monkeypatch.setattr(overlay, "_selected_silhouette_region", lambda *args: None)
    monkeypatch.setattr(overlay, "_core_body_overlay_layers", lambda *args: ((old_skin, 0, 0, clip, 1.0),))
    monkeypatch.setattr(overlay, "_core_hand_overlay_layers", lambda *args: ())
    return overlay


@pytest.mark.parametrize("fail_makeup", [False, True])
def test_complete_head_survives_dressed_body_restoration_and_asset_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_makeup: bool,
) -> None:
    _app()
    group = _group(tmp_path, motion_policy="preserve_body_layers", with_replacement_mask=True)
    view = _view(tmp_path, group=group)
    renderer = LayeredFullBodyRenderer(
        assets.LayeredFullBodyManifest(frozendict({VIEW: view})),
        outfit_overlay=_restoring_outfit(tmp_path, monkeypatch, fail_makeup=fail_makeup),
    )
    for blink, state in ((0.0, EyeState.REST), (0.5, EyeState.HALF), (1.0, EyeState.CLOSED)):
        rendered = renderer.render_view(VIEW, _motion(blink=blink)).toImage()
        assert rendered.pixelColor(*EYE_POINT) == QColor(*STATE_COLORS[state])
        if not fail_makeup:
            assert rendered.pixelColor(10, 24) == QColor("cyan")
            assert rendered.pixelColor(4, 4) == QColor("red")
        else:
            assert rendered.pixelColor(4, 4).alpha() == 0
            assert rendered.pixelColor(10, 24) == QColor("white")


@pytest.mark.parametrize("failure_at", [1, 2])
def test_replacement_errors_escape_without_replay_or_wrapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_at: int,
) -> None:
    _app()
    overlay = _restoring_outfit(tmp_path, monkeypatch, fail_makeup=True)
    frame = QPixmap(*CANVAS)
    frame.fill(QColor("white"))
    original_error = ValueError("Invalid canonical body")
    calls = []

    def replace_body(target):
        calls.append(target.cacheKey())
        if len(calls) == failure_at:
            raise original_error
        return target

    with pytest.raises(ValueError) as error:
        overlay.apply_animated(frame, VIEW, lambda _frame: None, replace_body=replace_body)
    assert error.value is original_error
    assert len(calls) == failure_at
    assert frame.toImage().pixelColor(*EYE_POINT) == QColor("white")
