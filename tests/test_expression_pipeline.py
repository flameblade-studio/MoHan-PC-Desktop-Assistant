from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QRect, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app import (
    CompanionWindow,
    EYES_CLOSED_EXPRESSIONS,
    EXPRESSION_FACE_OFFSETS,
    EXPRESSION_BLINK_FRAMES,
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_EXPRESSIONS,
    EXPRESSION_SPEECH_FRAMES,
    EXPRESSION_SPEECH_MOUTH_RECTS,
    GESTURE_SPEECH_EXPRESSIONS,
    GESTURE_SPEECH_FRAMES,
    GESTURE_SPEECH_MOUTH_RECTS,
    NEW_EXPRESSION_ASSETS,
)


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


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        stop_automatic_timers(window)

        assert all(window._physics_enabled(key) for key in FEATURES)
        assert "skeptical_front" not in window.expression_pixmaps
        assert set(NEW_EXPRESSION_ASSETS).issubset(window.expression_pixmaps)
        assert set(EXPRESSION_BLINK_FRAMES.values()).issubset(
            window.expression_pixmaps
        )
        assert set(EXPRESSION_POSES).issubset(
            window.physics_expression_poses
        )
        assert set(EXPRESSION_POSES).issubset(
            window.expression_anchor_profiles
        )
        assert set(EXPRESSION_FACE_OFFSETS) == set(EXPRESSION_POSES)
        for expression in EXPRESSION_POSES:
            profile = window.expression_anchor_profiles[expression]
            assert profile.pose == EXPRESSION_POSES[expression]
            assert -6 <= profile.offset_x <= 6
            assert -6 <= profile.offset_y <= 6
            assert -6 <= profile.eye_offset_x <= 6
            assert -6 <= profile.eye_offset_y <= 6
            assert -6 <= profile.mouth_offset_x <= 6
            assert -6 <= profile.mouth_offset_y <= 6
            assert 0.0 <= profile.confidence <= 1.0
            measured_x, measured_y, confidence, _score = (
                window._estimate_face_offset(
                    window.expression_pixmaps[
                        window.expression_anchor_base_expressions[
                            profile.pose
                        ]
                    ],
                    window.expression_pixmaps[expression],
                    window.expression_anchor_face_regions[profile.pose],
                )
            )
            if confidence >= 0.15:
                assert abs(measured_x - profile.offset_x) <= 2
                assert abs(measured_y - profile.offset_y) <= 2
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

        window.state = "idle"
        window.idle_pose = "front"
        window._set_expression("idle_front", fade=False)
        window.conservative_idle = False
        window._show_ambient_expression()
        assert window.state == "idle"
        assert window.current_expression == "idle_front"

        eye_rects = {
            pose: eye_bounds(window, pose)
            for pose in ("cheek", "lean", "front")
        }
        checked = 0
        for expression, pose in EXPRESSION_POSES.items():
            if expression not in window.expression_pixmaps:
                continue
            checked += 1
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
            assert all(
                not pixmap.isNull() for pixmap in local_layers.values()
            )

            base = window.expression_pixmaps[expression]
            blink = window._blink_composite(base, expression)
            eye_offset_x, eye_offset_y = window._expression_eye_offset(
                expression
            )
            blink_inside, blink_outside = changed_pixels(
                base,
                blink,
                eye_rects[pose].translated(eye_offset_x, eye_offset_y),
            )
            assert blink_inside == 0
            assert blink_outside == 0
            # The eye replacement mask must stay below the eyebrows. This
            # guards against the neutral blink frame erasing an expression's
            # own brow shape.
            translated_eye_rect = eye_rects[pose].translated(
                eye_offset_x,
                eye_offset_y,
            )
            eyebrow_strip = QRect(
                translated_eye_rect.left(),
                translated_eye_rect.top() - 12,
                translated_eye_rect.width(),
                12,
            )
            assert rect_difference(
                base,
                blink,
                eyebrow_strip,
                eyebrow_strip,
            ) == 0

            suffix = window._pose_suffix(pose)
            window.state = "speaking"
            window.speech_pose_suffix = suffix
            window.speech_closed_expression = f"idle{suffix}"
            window.speech_mid_expression = f"mouth_mid{suffix}"
            window.speech_open_expression = f"speaking{suffix}"
            mouth = window._mouth_aperture_pixmap(
                window.speech_open_expression,
                0.85,
            )
            mouth_inside, mouth_outside = changed_pixels(
                window.expression_pixmaps[f"idle{suffix}"],
                mouth,
                window.mouth_clips[suffix],
            )
            assert mouth_inside > 0
            assert mouth_outside == 0
            mouth_offset_x, mouth_offset_y = (0, 0)
            source_detail = window.mouth_clips[suffix].adjusted(
                10,
                8,
                -10,
                -8,
            )
            composed_detail = source_detail.translated(
                mouth_offset_x,
                mouth_offset_y,
            )
            source_energy = edge_energy(
                window.expression_pixmaps[window.speech_open_expression],
                source_detail,
            )
            composed_energy = edge_energy(mouth, composed_detail)
            assert source_energy > 0
            assert rect_difference(
                window.expression_pixmaps[window.speech_open_expression],
                mouth,
                source_detail,
                composed_detail,
            ) == 0
            assert composed_energy >= source_energy * 0.98

        assert checked == len(EXPRESSION_POSES)

        # Every emotion uses identity-locked, expression-local speech assets.
        # Every pixel outside the mouth region remains the original portrait,
        # including hands, brows, eyes, jaw, costume and transparent edges.
        assert EXPRESSION_SPEECH_EXPRESSIONS == frozenset(
            EXPRESSION_POSES
        )
        for expression in EXPRESSION_SPEECH_EXPRESSIONS:
            window.state = "speaking"
            window.speech_pose_suffix = window._pose_suffix(
                EXPRESSION_POSES[expression]
            )
            gesture_frames = EXPRESSION_SPEECH_FRAMES[expression]
            window.speech_closed_expression = expression
            window.speech_mid_expression = gesture_frames["mid"]
            window.speech_open_expression = gesture_frames["open"]
            window.speech_gesture_expression = expression
            original = window.expression_pixmaps[expression]
            mouth_rect = EXPRESSION_SPEECH_MOUTH_RECTS[expression]
            for speech_expression, aperture in (
                (gesture_frames["mid"], 0.48),
                (gesture_frames["open"], 0.90),
                (gesture_frames["round"], 0.72),
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
                composed = window._mouth_aperture_pixmap(
                    speech_expression,
                    aperture,
                )
                inside, outside = changed_pixels(
                    original,
                    composed,
                    mouth_rect,
                )
                assert inside > 0
                assert outside == 0, (
                    expression,
                    speech_expression,
                    outside,
                    mouth_rect.getRect(),
                )
            opened = window._mouth_aperture_pixmap(
                gesture_frames["open"],
                0.90,
            )
            blinked = window._blink_composite(opened, expression)
            eye_offset_x, eye_offset_y = window._expression_eye_offset(
                expression
            )
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

        # Expressions called out during pixel-level visual review use their
        # own identity-locked eyelid assets. The replacement must alter only
        # the eye mask; brows, mouth, face contour and pose stay untouched.
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
            allowed = alpha_bounds(
                window.dedicated_blink_masks[pose]
            ).translated(offset_x, offset_y)
            inside, outside = changed_pixels(
                original,
                dedicated,
                allowed.adjusted(-3, -3, 3, 3),
            )
            assert inside > 0, expression
            assert outside == 0, (expression, outside)

        # Gesture speech still blinks through the eye-only layer. The mouth,
        # hand, brows and body remain untouched during the blink.
        expression = "mock_scold"
        gesture_frames = GESTURE_SPEECH_FRAMES[expression]
        window.state = "speaking"
        window.speech_pose_suffix = "_front"
        window.speech_closed_expression = expression
        window.speech_mid_expression = gesture_frames["mid"]
        window.speech_open_expression = gesture_frames["open"]
        window.speech_gesture_expression = expression
        window.speech_current_expression = gesture_frames["mid"]
        window._show_speech_frame(gesture_frames["mid"], 0.48)
        pre_gesture_blink = QPixmap(window.character.pixmap())
        window._blink()
        gesture_blink = QPixmap(window.character.pixmap())
        offset_x, offset_y = window._expression_eye_offset(expression)
        gesture_eye_rect = eye_rects["front"].translated(
            offset_x,
            offset_y,
        )
        inside, outside = changed_pixels(
            pre_gesture_blink,
            gesture_blink,
            gesture_eye_rect.adjusted(-3, -3, 3, 3),
        )
        assert inside > 0
        assert outside == 0
        window._finish_speaking_blink(
            window.speech_current_expression,
            window.blink_generation,
        )

        expression = "shy_cute_front"
        expression_frames = EXPRESSION_SPEECH_FRAMES[expression]
        window.state = "speaking"
        window.speech_pose_suffix = "_front"
        window.speech_closed_expression = expression
        window.speech_mid_expression = expression_frames["mid"]
        window.speech_open_expression = expression_frames["open"]
        window.speech_gesture_expression = expression
        window.speech_current_expression = expression_frames["mid"]
        window._show_speech_frame(expression_frames["mid"], 0.48)
        pre_blink = QPixmap(window.character.pixmap())
        window._blink()
        assert window.speech_blinking
        assert window.current_expression == expression_frames["mid"]
        during_blink = QPixmap(window.character.pixmap())
        inside, outside = changed_pixels(
            pre_blink,
            during_blink,
            eye_rects["front"],
        )
        assert inside > 0
        assert outside == 0
        window._finish_speaking_blink(
            window.speech_current_expression,
            window.blink_generation,
        )
        restored_inside, restored_outside = changed_pixels(
            pre_blink,
            window.character.pixmap(),
            QRect(0, 0, 0, 0),
        )
        assert restored_inside == 0
        assert restored_outside == 0

        # A delayed hold may only release the exact expression generation
        # which created it. It must never overwrite a newer emotion or speech.
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
        QTest.qWait(35)
        assert window.state == "idle"

        captured_replies = []
        original_reply = window.dashboard._reply
        window.dashboard._reply = (
            lambda text, state, **metadata: captured_replies.append(
                (text, state, metadata)
            )
        )
        window.dashboard._ai_done(
            "主上，妾會護著你。"
            "[[MOHAN_EMOTION:protective:0.88]]"
        )
        window.dashboard._reply = original_reply
        assert captured_replies == [
            (
                "主上，妾會護著你。",
                "protective_front",
                {"intensity": 0.88, "source": "ai_tag"},
            )
        ]

        window.close()
        app.processEvents()
    print("EXPRESSION_PIPELINE_OK")


if __name__ == "__main__":
    run()
