from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtCore import QRect, QTimer
lazy from PySide6.QtGui import QImage, QPixmap
lazy from PySide6.QtTest import QTest
lazy from PySide6.QtWidgets import QApplication

lazy from companion_animation_contract import (
    EXPRESSION_BLINK_FRAMES,
    EXPRESSION_FACE_OFFSETS,
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_EXPRESSIONS,
    EXPRESSION_SPEECH_FRAMES,
    EXPRESSION_SPEECH_MOUTH_RECTS,
    EYES_CLOSED_EXPRESSIONS,
    GESTURE_SPEECH_FRAMES,
    NEW_EXPRESSION_ASSETS,
)
lazy from companion_window import CompanionWindow

ANCHOR_OFFSET_BOUND = 6
ANCHOR_CONFIDENCE_THRESHOLD = 0.15
ANCHOR_OFFSET_TOLERANCE = 2

FEATURES = (
    "physics_sleeves",
    "physics_hair",
    "physics_ornament",
    "physics_eye_tracking",
    "physics_face_parallax",
)


def stop_automatic_timers(window: CompanionWindow) -> None:
    for timer in window.findChildren(QTimer):
        timer.stop()


def changed_pixels(
    before: QPixmap,
    after: QPixmap,
    allowed: QRect,
) -> tuple[int, int]:
    first = before.toImage().convertToFormat(QImage.Format_RGBA8888)
    second = after.toImage().convertToFormat(QImage.Format_RGBA8888)
    inside = 0
    outside = 0
    for y in range(first.height()):
        for x in range(first.width()):
            if first.pixel(x, y) == second.pixel(x, y):
                continue
            if allowed.contains(x, y):
                inside += 1
            else:
                outside += 1
    return inside, outside


def alpha_bounds(pixmap: QPixmap) -> QRect:
    image = pixmap.toImage()
    left = image.width()
    top = image.height()
    right = -1
    bottom = -1
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() == 0:
                continue
            left = min(left, x)
            top = min(top, y)
            right = max(right, x)
            bottom = max(bottom, y)
    assert right >= left and bottom >= top
    return QRect(left, top, right - left + 1, bottom - top + 1)


def eye_bounds(window: CompanionWindow, pose: str) -> QRect:
    return alpha_bounds(window.blink_masks[pose])


def rect_difference(
    first: QPixmap,
    second: QPixmap,
    first_rect: QRect,
    second_rect: QRect,
) -> int:
    """Count non-identical pixels in two equally sized detail regions."""
    assert first_rect.size() == second_rect.size()
    first_image = first.toImage().convertToFormat(QImage.Format_RGBA8888)
    second_image = second.toImage().convertToFormat(QImage.Format_RGBA8888)
    difference = 0
    for row in range(first_rect.height()):
        for column in range(first_rect.width()):
            if first_image.pixel(
                first_rect.x() + column,
                first_rect.y() + row,
            ) != second_image.pixel(
                second_rect.x() + column,
                second_rect.y() + row,
            ):
                difference += 1
    return difference


def edge_energy(pixmap: QPixmap, region: QRect) -> int:
    """Measure local detail so a blurred mouth cannot pass unnoticed."""
    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)

    def luminance(x: int, y: int) -> int:
        color = image.pixelColor(x, y)
        return (
            color.red() * 54
            + color.green() * 183
            + color.blue() * 19
        ) // 256

    energy = 0
    for y in range(region.top(), region.bottom()):
        for x in range(region.left(), region.right()):
            center = luminance(x, y)
            energy += abs(center - luminance(x + 1, y))
            energy += abs(center - luminance(x, y + 1))
    return energy


def assert_asset_registry(window: CompanionWindow) -> None:
    assert all(window._physics_enabled(key) for key in FEATURES)
    assert "skeptical_front" not in window.expression_pixmaps
    assert set(NEW_EXPRESSION_ASSETS).issubset(window.expression_pixmaps)
    assert set(EXPRESSION_BLINK_FRAMES.values()).issubset(
        window.expression_pixmaps
    )
    assert set(EXPRESSION_POSES).issubset(window.physics_expression_poses)
    assert set(EXPRESSION_POSES).issubset(window.expression_anchor_profiles)
    assert set(EXPRESSION_FACE_OFFSETS) == set(EXPRESSION_POSES)


def assert_anchor_profile(window: CompanionWindow, expression: str) -> None:
    profile = window.expression_anchor_profiles[expression]
    assert profile.pose == EXPRESSION_POSES[expression]
    assert -ANCHOR_OFFSET_BOUND <= profile.offset_x <= ANCHOR_OFFSET_BOUND
    assert -ANCHOR_OFFSET_BOUND <= profile.offset_y <= ANCHOR_OFFSET_BOUND
    assert -ANCHOR_OFFSET_BOUND <= profile.eye_offset_x <= ANCHOR_OFFSET_BOUND
    assert -ANCHOR_OFFSET_BOUND <= profile.eye_offset_y <= ANCHOR_OFFSET_BOUND
    assert -ANCHOR_OFFSET_BOUND <= profile.mouth_offset_x <= ANCHOR_OFFSET_BOUND
    assert -ANCHOR_OFFSET_BOUND <= profile.mouth_offset_y <= ANCHOR_OFFSET_BOUND
    assert 0.0 <= profile.confidence <= 1.0
    measured_x, measured_y, confidence, _score = window._estimate_face_offset(
        window.expression_pixmaps[
            window.expression_anchor_base_expressions[profile.pose]
        ],
        window.expression_pixmaps[expression],
        window.expression_anchor_face_regions[profile.pose],
    )
    if confidence >= ANCHOR_CONFIDENCE_THRESHOLD:
        assert abs(measured_x - profile.offset_x) <= ANCHOR_OFFSET_TOLERANCE
        assert abs(measured_y - profile.offset_y) <= ANCHOR_OFFSET_TOLERANCE


def assert_anchor_profiles(window: CompanionWindow) -> None:
    for expression in EXPRESSION_POSES:
        assert_anchor_profile(window, expression)


def assert_reply_expression_policy(window: CompanionWindow) -> None:
    trigger_cases = {
        "再胡說妾便敲你。": "mock_hit_front",
        "主上莫要自作多情。": "shy_cute_front",
        "妾想到了，關鍵原來在於此。": "eureka_front",
        "誰也不得傷主上。": "protective_front",
        "真拿主上沒辦法。": "exasperated_front",
        "主上是在逗妾麼？": "restrained_amused_front",
        "妾在聽，主上慢慢說。": "attentive_front",
        "計策已定，便照此執行。": "determined_front",
        "真沒想到竟會如此。": "surprised_front",
        "主上別逞強，妾放心不下。": "worried_front",
        "該吃飯了，先去吃飯。": "reminder",
        "主上平安便好。": "relieved_front",
        "不出妾所料。": "proud_front",
        "主上做得很好。": "gentle_smile_front",
        "妾先分析，再排優先順序。": "thinking_front",
    }
    for text, expected in trigger_cases.items():
        assert window.dashboard._reply_expression(text) == expected

    false_positive_cases = (
        "資料已完成，謝謝主上。",
        "這個計畫包含提醒設定。",
        "這只是一般的安全資料說明。",
        "報表中提到吃飯與下班兩個欄位。",
        "當真只是普通敘述，沒有其他意思。",
    )
    for text in false_positive_cases:
        assert window.dashboard._reply_expression(text) == "speaking"


def assert_conservative_idle_policy(window: CompanionWindow) -> None:
    window.state = "idle"
    window.idle_pose = "front"
    window._set_expression("idle_front", fade=False)
    window.conservative_idle = False
    window._show_ambient_expression()
    assert window.state == "idle"
    assert window.current_expression == "idle_front"


def activate_expression_physics(
    window: CompanionWindow,
    expression: str,
    pose: str,
) -> None:
    window.state = expression
    window._set_expression(expression, fade=False)
    window._attention_tick()
    assert window.active_physics_pose == pose
    assert window.physics_overlay.isVisible()
    assert window.hair_left_overlay.isVisible()
    assert window.hair_right_overlay.isVisible()
    assert window.sleeve_left_overlay.isVisible()
    assert window.sleeve_right_overlay.isVisible()
    assert window.face_overlay.isVisible()
    assert window.eye_overlay.isVisible()

    local_layers = window.expression_physics_sources[expression]
    assert set(local_layers) == {
        "ornament",
        "hair_left",
        "hair_right",
        "sleeve_left",
        "sleeve_right",
    }
    assert all(not pixmap.isNull() for pixmap in local_layers.values())


def assert_expression_blink_identity(
    window: CompanionWindow,
    expression: str,
    eye_rect: QRect,
) -> None:
    base = window.expression_pixmaps[expression]
    blink = window._blink_composite(base, expression)
    eye_offset_x, eye_offset_y = window._expression_eye_offset(expression)
    translated_eye_rect = eye_rect.translated(eye_offset_x, eye_offset_y)
    blink_inside, blink_outside = changed_pixels(
        base,
        blink,
        translated_eye_rect,
    )
    assert blink_inside == 0
    assert blink_outside == 0
    # The eye replacement mask must stay below the eyebrows. This guards
    # against the neutral blink frame erasing an expression's own brow shape.
    eyebrow_strip = QRect(
        translated_eye_rect.left(),
        translated_eye_rect.top() - 12,
        translated_eye_rect.width(),
        12,
    )
    assert rect_difference(base, blink, eyebrow_strip, eyebrow_strip) == 0


def configure_neutral_speech(window: CompanionWindow, pose: str) -> str:
    suffix = window._pose_suffix(pose)
    window.state = "speaking"
    window.speech_pose_suffix = suffix
    window.speech_closed_expression = f"idle{suffix}"
    window.speech_mid_expression = f"mouth_mid{suffix}"
    window.speech_open_expression = f"speaking{suffix}"
    return suffix


def assert_neutral_mouth_composition(
    window: CompanionWindow,
    suffix: str,
) -> None:
    # The layered renderer composes the whole half-body portrait from 25 layers
    # instead of patching only the mouth region. The composition must produce a
    # non-null frame at the caller's canvas size, and the mouth region must
    # still differ from the closed idle frame (the mouth is open).
    mouth = window._mouth_aperture_pixmap(window.speech_open_expression, 0.85)
    assert not mouth.isNull()
    closed = window.expression_pixmaps[f"idle{suffix}"]
    assert mouth.size() == closed.size()
    mouth_inside, _mouth_outside = changed_pixels(
        closed,
        mouth,
        window.mouth_clips[suffix],
    )
    assert mouth_inside > 0


def assert_expression_pose_pipeline(
    window: CompanionWindow,
) -> dict[str, QRect]:
    eye_rects = {
        pose: eye_bounds(window, pose)
        for pose in ("cheek", "lean", "front")
    }
    checked = 0
    for expression, pose in EXPRESSION_POSES.items():
        if expression not in window.expression_pixmaps:
            continue
        checked += 1
        activate_expression_physics(window, expression, pose)
        assert_expression_blink_identity(window, expression, eye_rects[pose])
        suffix = configure_neutral_speech(window, pose)
        assert_neutral_mouth_composition(window, suffix)
    assert checked == len(EXPRESSION_POSES)
    return eye_rects


def configure_expression_speech(
    window: CompanionWindow,
    expression: str,
    frames: dict[str, str],
) -> None:
    window.state = "speaking"
    window.speech_pose_suffix = window._pose_suffix(EXPRESSION_POSES[expression])
    window.speech_closed_expression = expression
    window.speech_mid_expression = frames["mid"]
    window.speech_open_expression = frames["open"]
    window.speech_gesture_expression = expression


def assert_expression_speech_variants(
    window: CompanionWindow,
    expression: str,
    frames: dict[str, str],
) -> None:
    original = window.expression_pixmaps[expression]
    mouth_rect = EXPRESSION_SPEECH_MOUTH_RECTS[expression]
    for speech_expression, aperture in (
        (frames["mid"], 0.48),
        (frames["open"], 0.90),
        (frames["round"], 0.72),
    ):
        asset_inside, asset_outside = changed_pixels(
            original,
            window.expression_pixmaps[speech_expression],
            mouth_rect,
        )
        assert asset_inside > 0
        assert asset_outside == 0, (
            expression,
            speech_expression,
            asset_outside,
            mouth_rect.getRect(),
        )
        composed = window._mouth_aperture_pixmap(speech_expression, aperture)
        # The layered renderer composes the whole half-body portrait, so the
        # composed frame must be non-null and match the caller's canvas size.
        assert not composed.isNull()
        assert composed.size() == original.size()


def assert_expression_speech_blink(
    window: CompanionWindow,
    expression: str,
    frames: dict[str, str],
) -> None:
    opened = window._mouth_aperture_pixmap(frames["open"], 0.90)
    blinked = window._blink_composite(opened, expression)
    eye_offset_x, eye_offset_y = window._expression_eye_offset(expression)
    pose = EXPRESSION_POSES[expression]
    blink_mask = (
        window.dedicated_blink_masks[pose]
        if expression in EXPRESSION_BLINK_FRAMES
        else window.blink_masks[pose]
    )
    expression_eye_rect = alpha_bounds(blink_mask).translated(
        eye_offset_x,
        eye_offset_y,
    )
    blink_inside, blink_outside = changed_pixels(
        opened,
        blinked,
        expression_eye_rect.adjusted(-3, -3, 3, 3),
    )
    if expression in EYES_CLOSED_EXPRESSIONS:
        assert blink_inside == 0
        assert blink_outside == 0
    else:
        assert blink_inside > 0, expression
        assert blink_outside == 0, expression


def assert_expression_local_speech_assets(window: CompanionWindow) -> None:
    # Every emotion uses identity-locked, expression-local speech assets.
    # Every pixel outside the mouth region remains the original portrait.
    assert frozenset(EXPRESSION_POSES) == EXPRESSION_SPEECH_EXPRESSIONS
    for expression in EXPRESSION_SPEECH_EXPRESSIONS:
        frames = EXPRESSION_SPEECH_FRAMES[expression]
        configure_expression_speech(window, expression, frames)
        assert_expression_speech_variants(window, expression, frames)
        assert_expression_speech_blink(window, expression, frames)


def assert_dedicated_blink_assets(window: CompanionWindow) -> None:
    # Identity-locked eyelids may alter only the eye mask.
    assert set(EXPRESSION_BLINK_FRAMES) == {
        "thinking_front",
        "glance",
        "happy",
        "worried",
        "reminder",
    }
    for expression, blink_asset in EXPRESSION_BLINK_FRAMES.items():
        original = window.expression_pixmaps[expression]
        assert not window.expression_pixmaps[blink_asset].isNull()
        dedicated = window._blink_composite(original, expression)
        pose = EXPRESSION_POSES[expression]
        offset_x, offset_y = window._expression_eye_offset(expression)
        allowed = alpha_bounds(window.dedicated_blink_masks[pose]).translated(
            offset_x,
            offset_y,
        )
        inside, outside = changed_pixels(
            original,
            dedicated,
            allowed.adjusted(-3, -3, 3, 3),
        )
        assert inside > 0, expression
        assert outside == 0, (expression, outside)


def show_expression_speech_frame(
    window: CompanionWindow,
    expression: str,
    frames: dict[str, str],
) -> None:
    window.state = "speaking"
    window.speech_pose_suffix = "_front"
    window.speech_closed_expression = expression
    window.speech_mid_expression = frames["mid"]
    window.speech_open_expression = frames["open"]
    window.speech_gesture_expression = expression
    window.speech_current_expression = frames["mid"]
    window._show_speech_frame(frames["mid"], 0.48)


def assert_gesture_speech_blink(
    window: CompanionWindow,
    eye_rects: dict[str, QRect],
) -> None:
    # Gesture speech blinks through the eye-only layer. Mouth, hand, brows and
    # body remain untouched.
    expression = "mock_scold"
    gesture_frames = GESTURE_SPEECH_FRAMES[expression]
    show_expression_speech_frame(window, expression, gesture_frames)
    pre_gesture_blink = QPixmap(window.character.pixmap())
    window._blink()
    # The discrete blink contract keeps HALF frames untouched when no
    # registered half-eye source exists, so advance to the CLOSED authority
    # frame before sampling the eye region.
    window._advance_speaking_blink(window.blink_generation, 1.0)
    gesture_blink = QPixmap(window.character.pixmap())
    offset_x, offset_y = window._expression_eye_offset(expression)
    gesture_eye_rect = eye_rects["front"].translated(offset_x, offset_y)
    inside, outside = changed_pixels(
        pre_gesture_blink,
        gesture_blink,
        gesture_eye_rect.adjusted(-3, -3, 3, 3),
    )
    assert inside > 0
    assert outside == 0
    window._finish_speaking_blink(window.blink_generation)


def assert_expression_speech_blink_restore(
    window: CompanionWindow,
    eye_rects: dict[str, QRect],
) -> None:
    expression = "shy_cute_front"
    expression_frames = EXPRESSION_SPEECH_FRAMES[expression]
    show_expression_speech_frame(window, expression, expression_frames)
    pre_blink = QPixmap(window.character.pixmap())
    window._blink()
    assert window.speech_blinking
    assert window.current_expression == expression_frames["mid"]
    # Discrete blink contract: HALF frames stay untouched without a half-eye
    # source, so sample the CLOSED authority frame.
    window._advance_speaking_blink(window.blink_generation, 1.0)
    during_blink = QPixmap(window.character.pixmap())
    inside, outside = changed_pixels(
        pre_blink,
        during_blink,
        eye_rects["front"],
    )
    assert inside > 0
    assert outside == 0
    window._finish_speaking_blink(window.blink_generation)
    restored_inside, restored_outside = changed_pixels(
        pre_blink,
        window.character.pixmap(),
        QRect(0, 0, 0, 0),
    )
    assert restored_inside == 0
    assert restored_outside == 0


def assert_expression_generation_guards(window: CompanionWindow) -> None:
    # A delayed hold may release only the generation which created it.
    window.set_state("shy_cute_front", force=True)
    window._schedule_return_to_idle(25, "shy_cute_front")
    QTest.qWait(5)
    window.set_state("protective_front", force=True)
    QTest.qWait(35)
    assert window.state == "protective_front"

    window.set_state("thinking_front", force=True)
    window._schedule_return_to_idle(25, "thinking_front")
    QTest.qWait(5)
    window.set_state("speaking")
    window.speech_playing = True
    QTest.qWait(35)
    assert window.state == "speaking"
    window.speech_playing = False

    window.set_state("attentive_front", force=True)
    window._schedule_return_to_idle(20, "attentive_front")
    assert window.expression_return_timer.isActive()
    window._release_scheduled_expression()
    assert window.state == "idle", (
        "scheduled expression release did not restore idle: "
        f"state={window.state!r}, "
        f"generation={window.expression_generation}, "
        f"speech_playing={window.speech_playing!r}, "
        f"realtime_mouth_active={window.realtime_mouth_active!r}"
    )
    assert not window.expression_return_timer.isActive()


def assert_ai_emotion_metadata(window: CompanionWindow) -> None:
    captured_replies = []
    original_reply = window.dashboard._reply
    window.dashboard._reply = (
        lambda text, state, **metadata: captured_replies.append(
            (text, state, metadata)
        )
    )
    window.dashboard._ai_done(
        "主上，妾會護著你。[[MOHAN_EMOTION:protective:0.88]]"
    )
    window.dashboard._reply = original_reply
    assert captured_replies == [
        (
            "主上，妾會護著你。",
            "protective_front",
            {"intensity": 0.88, "source": "ai_tag"},
        )
    ]


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        stop_automatic_timers(window)
        assert_asset_registry(window)
        assert_anchor_profiles(window)
        assert_reply_expression_policy(window)
        assert_conservative_idle_policy(window)
        eye_rects = assert_expression_pose_pipeline(window)
        assert_expression_local_speech_assets(window)
        assert_dedicated_blink_assets(window)
        assert_gesture_speech_blink(window, eye_rects)
        assert_expression_speech_blink_restore(window, eye_rects)
        assert_expression_generation_guards(window)
        assert_ai_emotion_metadata(window)
        window.close()
        app.processEvents()
    print("EXPRESSION_PIPELINE_OK")


if __name__ == "__main__":
    run()
