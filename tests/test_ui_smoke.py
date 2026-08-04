import os
import sys
import threading
from unittest.mock import patch
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLayout,
    QMessageBox,
    QScrollArea,
)

from app import (
    ChatHistoryDialog,
    CompanionWindow,
    FirstRunWizard,
    IdeaEditorDialog,
    MemoryEditorDialog,
)
from db import StudioDB


def run() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.environ["LOCALAPPDATA"] = tmp
        db_path = Path(tmp) / "YanJianStudio" / "MoHan" / "mohan.db"
        preflight = StudioDB(db_path)
        preflight.set_setting("tts_enabled", False)
        preflight.set_setting(
            "windows_voice",
            "OneCore::Microsoft Zhiwei",
        )
        preflight.set_setting("voice_instructions", "舊語音提示")
        preflight.set_setting("tts_voice", "marin")
        preflight.set_setting("cloud_voice", "marin")
        preflight.set_setting("realtime_voice", "shimmer")
        preflight.close()
        app = QApplication([])
        wizard_db = StudioDB(Path(tmp) / "wizard-new-user.db")
        wizard = FirstRunWizard(wizard_db)
        assert wizard.organization_name.text() == ""
        assert wizard.work_type.currentText() == "一般辦公／行政"
        wizard.assistant_name.setText("Ava")
        wizard.user_title.setText("Alex")
        wizard.organization_name.setText("Example Team")
        wizard.window_title.setText("Ava Workspace")
        wizard.work_type.setCurrentText("Project Management")
        wizard.wake_word.setText("Hey Ava")
        wizard._save()
        assert wizard_db.setting("assistant_name") == "Ava"
        assert wizard_db.setting("user_title") == "Alex"
        assert wizard_db.setting("organization_name") == "Example Team"
        assert wizard_db.setting("window_title") == "Ava Workspace"
        assert wizard_db.setting("work_type") == "Project Management"
        assert wizard_db.setting("wake_word") == "Hey Ava"
        assert wizard_db.setting("onboarding_complete") is True
        wizard_db.close()
        # Keep voice-selection UI coverage deterministic.  Clean CI runners do
        # not necessarily include Taiwan's optional Windows speech packs,
        # while a developer workstation may have Yating and Hanhan installed.
        test_voices = [
            ("OneCore::Microsoft Yating", "zh-TW"),
            ("OneCore::Microsoft Hanhan", "zh-TW"),
            ("OneCore::Microsoft Zhiwei", "zh-TW"),
        ]
        with patch("app.windows_voices", return_value=test_voices):
            window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        wait_states: list[str] = []
        window.dashboard.ai_wait_expression_requested.connect(
            lambda _generation, expression, _intensity: wait_states.append(
                expression
            )
        )
        window.dashboard.ai_busy = True
        window.dashboard._schedule_ai_wait_expressions("早安，墨寒")
        QTest.qWait(900)
        assert "thinking_front" not in wait_states

        # A completed request must invalidate its delayed reaction.  Otherwise
        # the old timer can make MoHan turn and think after she has replied.
        window.dashboard._schedule_ai_wait_expressions(
            "請分析兩個方案的利弊、風險與優先順序。"
        )
        window.dashboard.ai_busy = False
        QTest.qWait(1300)
        assert "thinking_front" not in wait_states

        window.dashboard.ai_busy = True
        window.dashboard._schedule_ai_wait_expressions(
            "請分析兩個方案的利弊、風險與優先順序。"
        )
        QTest.qWait(1300)
        assert wait_states[-1] == "thinking_front"
        window.dashboard.ai_busy = False
        window.dashboard._finish_ai_wait_expression()
        QTest.qWait(700)
        app.processEvents()
        window._set_expression(window._idle_expression(), fade=False)
        window.overlay_opacity.setOpacity(0.0)
        assert window.dashboard.portable_profile_panel is not None
        assert (
            window.dashboard.portable_profile_panel.export_button.text()
            == "匯出墨寒攜帶檔"
        )
        assert (
            window.dashboard.portable_profile_panel.import_button.text()
            == "匯入並接續進度"
        )
        feature_ids = {
            window.dashboard.tabs.widget(index).property(
                "mohanFeatureId"
            )
            for index in range(window.dashboard.tabs.count())
        }
        assert feature_ids == {
            "chat",
            "today",
            "platforms",
            "memory",
            "voice",
            "permissions",
            "settings",
        }
        assert window.character.pixmap() is not None
        assert window.character_opacity.opacity() == 1.0
        assert window.overlay_opacity.opacity() == 0.0
        assert window.height() == 680
        window._show_bubble("這是一段需要自動換行的長回覆。" * 30)
        app.processEvents()
        assert 105 < window.bubble.height() <= 202
        assert "完整內容請見對話頁" in window.bubble_text.text()
        window.bubble.hide()
        assert all(not pixmap.isNull() for pixmap in window.expression_pixmaps.values())
        assert {
            "idle_lean",
            "idle_front",
            "speaking_lean",
            "speaking_front",
            "blink",
            "blink_lean",
            "blink_front",
            "glance",
            "caught",
            "thinking_front",
            "gentle_smile_front",
            "worried_front",
            "shy_front",
            "mock_scold",
            "surprised_front",
            "relieved_front",
            "tired_front",
            "proud_front",
            "shy_cute_front",
            "mock_hit_front",
            "attentive_front",
            "determined_front",
            "restrained_amused_front",
            "exasperated_front",
            "eureka_front",
            "protective_front",
            "viseme_mid_front",
            "viseme_wide_front",
            "viseme_round",
            "viseme_round_lean",
            "viseme_round_front",
            "viseme_i",
            "viseme_i_lean",
            "viseme_i_front",
            "viseme_o",
            "viseme_o_lean",
            "viseme_o_front",
            "mouth_mid",
            "mouth_mid_lean",
            "mouth_mid_front",
            "blink_mid",
            "blink_mid_lean",
            "blink_mid_front",
            "blink_open",
            "blink_open_lean",
            "blink_open_front",
            "mouth_wide",
            "mouth_wide_lean",
            "mouth_wide_front",
            "mouth_round",
            "mouth_round_lean",
            "mouth_round_front",
            "blink_wide",
            "blink_wide_lean",
            "blink_wide_front",
            "blink_round",
            "blink_round_lean",
            "blink_round_front",
            "mouth_i",
            "mouth_i_lean",
            "mouth_i_front",
            "mouth_o",
            "mouth_o_lean",
            "mouth_o_front",
            "blink_i",
            "blink_i_lean",
            "blink_i_front",
            "blink_o",
            "blink_o_lean",
            "blink_o_front",
        } <= set(window.expression_pixmaps)
        assert (
            window.expression_pixmaps["mouth_round_front"].cacheKey()
            != window.expression_pixmaps["mouth_wide_front"].cacheKey()
        )
        assert window.dashboard._reply_expression(
            "先分析風險與優先順序。"
        ) == "thinking_front"
        assert window.dashboard._reply_expression(
            "主上做得很好。"
        ) == "gentle_smile_front"
        assert window.dashboard._reply_expression(
            "先去吃飯與休息。"
        ) == "reminder"
        assert window.dashboard._reply_expression(
            "主上休得胡言，再胡說妾便敲你一下。"
        ) == "mock_hit_front"
        assert window.dashboard._reply_expression(
            "主上莫要自作多情，並無此事。"
        ) == "shy_cute_front"
        assert window.dashboard._reply_expression(
            "這不是藉口，妾只是想把情況說清楚。"
        ) == "speaking"
        assert window.dashboard._reply_expression(
            "主上這個藉口，當妾看不出來嗎？"
        ) == "speaking"
        assert "skeptical_front" not in window.expression_pixmaps
        ambient_choices = []
        window.conservative_idle = False
        window.state = "idle"
        with patch(
            "app.random.choice",
            side_effect=lambda choices: (
                ambient_choices.extend(choices) or choices[0]
            ),
        ):
            window._show_ambient_expression()
        assert "skeptical_front" not in ambient_choices
        window.ambient_timer.stop()
        window.conservative_idle = True
        window.set_state("idle")
        window.dashboard.move(80, 80)
        app.processEvents()
        assert not (
            window.dashboard.windowFlags() & Qt.WindowStaysOnTopHint
        )
        assert window.character_topmost_active
        window.dashboard.show()
        app.processEvents()
        assert not window.character_topmost_active
        window.dashboard.hide()
        app.processEvents()
        assert window.character_topmost_active
        z_order_calls = []
        window._set_windows_character_z_order = (
            lambda enabled, behind=0: z_order_calls.append(
                (enabled, behind)
            )
        )
        window._smart_overlap_hwnd = 24680
        window._external_foreground_overlaps_character = lambda: True
        window.dashboard.topmost_mode.setCurrentText("智慧置頂（推薦）")
        window._topmost_policy_tick()
        assert not window.character_topmost_active
        assert window.character_behind_hwnd == 24680
        assert z_order_calls[-1] == (False, 24680)
        window._smart_overlap_hwnd = 13579
        window._topmost_policy_tick()
        assert window.character_behind_hwnd == 13579
        assert z_order_calls[-1] == (False, 13579)
        window._external_foreground_overlaps_character = lambda: False
        window._topmost_policy_tick()
        assert window.character_topmost_active
        assert window.character_behind_hwnd == 0
        assert z_order_calls[-1] == (True, 0)
        assert window._rectangles_overlap_or_near(
            (900, 100, 1300, 700),
            (1280, 200, 1750, 880),
        )
        assert not window._rectangles_overlap_or_near(
            (100, 100, 500, 700),
            (1280, 200, 1750, 880),
        )

        class FakeUser32:
            def __init__(self):
                self.calls = []

            def SetWindowPos(
                self,
                hwnd,
                insert_after,
                x,
                y,
                width,
                height,
                flags,
            ):
                self.calls.append((hwnd, insert_after, flags))
                return 1

            @staticmethod
            def IsWindow(_hwnd):
                return 1

        fake_user32 = FakeUser32()
        CompanionWindow._set_windows_character_z_order(
            window,
            False,
            54321,
            user32=fake_user32,
            hwnd=12345,
        )
        assert fake_user32.calls == [
            (12345, -2, 0x0001 | 0x0002 | 0x0010),
            (12345, 54321, 0x0001 | 0x0002 | 0x0010),
        ]
        fake_user32.calls.clear()
        CompanionWindow._set_windows_character_z_order(
            window,
            True,
            user32=fake_user32,
            hwnd=12345,
        )
        assert fake_user32.calls == [
            (12345, -1, 0x0001 | 0x0002 | 0x0010)
        ]
        window.dashboard.topmost_mode.setCurrentText("不置頂")
        assert not window.character_topmost_active
        window.dashboard.topmost_mode.setCurrentText("永遠置頂")
        assert window.character_topmost_active
        window.dashboard.topmost_mode.setCurrentText("智慧置頂（推薦）")
        # Keep the direct physics-layer assertions isolated from the live idle
        # pose scheduler.  On slower CI runners its transition can begin while
        # processEvents() runs below and intentionally hide every local layer
        # for one animation frame.
        window.pose_timer.stop()
        window._cancel_pose_transition()
        window.idle_pose = "lean"
        window._set_expression(window._idle_expression(), fade=False)
        app.processEvents()
        assert window.current_expression == "idle_lean"
        assert {"cheek", "lean", "front"} == set(window.physics_sources)
        assert {"cheek", "lean", "front"} == set(window.hair_sources)
        assert {"cheek", "lean", "front"} == set(window.sleeve_sources)
        assert {"cheek", "lean", "front"} == set(window.face_sources)
        assert {"cheek", "lean", "front"} == set(window.eye_sources)
        assert all(
            not pixmap.isNull() for pixmap in window.physics_sources.values()
        )
        assert all(
            not window.hair_sources[pose][side].isNull()
            for pose in window.hair_sources
            for side in ("left", "right")
        )
        assert all(
            not window.sleeve_sources[pose][side].isNull()
            for pose in window.sleeve_sources
            for side in ("left", "right")
        )
        assert all(
            not window.face_sources[pose].isNull()
            and not window.eye_sources[pose].isNull()
            for pose in ("cheek", "lean", "front")
        )
        assert window.active_physics_pose == "lean"
        assert window.safe_layer_rendering
        assert window.physics_overlay.isVisible()
        assert window.hair_left_overlay.isVisible()
        assert window.hair_right_overlay.isVisible()
        assert window.sleeve_left_overlay.isVisible()
        assert window.sleeve_right_overlay.isVisible()
        assert all(
            control.isChecked()
            for control in window.dashboard.physics_controls.values()
        )
        window._render_sleeve_layers(force=True)
        window._render_hair_layers(force=True)
        window._render_physics_layer(force=True)
        neutral_ornament_key = window.physics_overlay.pixmap().cacheKey()
        neutral_left_hair_key = window.hair_left_overlay.pixmap().cacheKey()
        neutral_right_hair_key = window.hair_right_overlay.pixmap().cacheKey()
        neutral_left_sleeve_key = (
            window.sleeve_left_overlay.pixmap().cacheKey()
        )
        neutral_right_sleeve_key = (
            window.sleeve_right_overlay.pixmap().cacheKey()
        )
        window.ornament_angle = 1.8
        window.hair_left_angle = 0.7
        window.hair_right_angle = -0.6
        window.sleeve_left_angle = 0.28
        window.sleeve_right_angle = -0.26
        window.current_breath = 0.9
        window._render_sleeve_layers(force=True)
        window._render_hair_layers(force=True)
        window._render_physics_layer(force=True)
        assert (
            window.physics_overlay.pixmap().cacheKey()
            != neutral_ornament_key
        )
        assert (
            window.hair_left_overlay.pixmap().cacheKey()
            != neutral_left_hair_key
        )
        assert (
            window.hair_right_overlay.pixmap().cacheKey()
            != neutral_right_hair_key
        )
        assert (
            window.sleeve_left_overlay.pixmap().cacheKey()
            != neutral_left_sleeve_key
        )
        assert (
            window.sleeve_right_overlay.pixmap().cacheKey()
            != neutral_right_sleeve_key
        )
        window._set_expression("mock_scold", fade=False)
        assert window.physics_overlay.isVisible()
        assert window.hair_left_overlay.isVisible()
        assert window.hair_right_overlay.isVisible()
        assert window.sleeve_left_overlay.isVisible()
        assert window.sleeve_right_overlay.isVisible()
        window.idle_pose = "front"
        window._set_expression("idle_front", fade=False)
        assert window.active_physics_pose == "front"
        assert window.physics_overlay.isVisible()
        window.state = "idle"
        window.gaze_x = 1.0
        window.gaze_y = -1.0
        window._render_attention_layers(force=True)
        window._position_character_layers(0, window.character_base_y)
        assert window.character.x() == window.character_base_x + 2
        assert window.face_overlay.x() == window.character.x()
        assert window.eye_overlay.x() == window.character.x()
        gaze_face_key = window.face_overlay.pixmap().cacheKey()
        gaze_eye_key = window.eye_overlay.pixmap().cacheKey()
        # The live blink timer may have entered a blink during earlier QTest
        # waits. This assertion tests gaze-layer visibility, so establish the
        # non-blinking precondition explicitly before invoking the renderer.
        window.idle_blinking = False
        window._attention_tick()
        assert window.face_overlay.isVisible()
        assert window.eye_overlay.isVisible()
        window.gaze_x = -1.0
        window.gaze_y = 1.0
        window._render_attention_layers(force=True)
        assert window.face_overlay.pixmap().cacheKey() != gaze_face_key
        assert window.eye_overlay.pixmap().cacheKey() != gaze_eye_key
        window.idle_blinking = True
        window._attention_tick()
        assert window.eye_overlay.isHidden()
        window.idle_blinking = False
        window.current_expression = "idle_front"
        window.gaze_x = 0.0
        window.gaze_y = 0.0
        window._position_character_layers(0, window.character_base_y)
        stable_idle_expression = window.current_expression
        window._show_ambient_expression()
        window._start_attention_glance()
        assert window.current_expression == stable_idle_expression
        assert window.state == "idle"
        window.current_expression = "speaking_front"
        window.mouth_open = True
        window.mouth_timer.start(500)
        window._idle_tick()
        assert window.current_expression == "idle_front"
        assert window.mouth_open is False
        assert not window.mouth_timer.isActive()
        window.ornament_angle = 0.0
        window.ornament_velocity = 0.0
        window.hair_left_angle = 0.0
        window.hair_right_angle = 0.0
        window.hair_left_velocity = 0.0
        window.hair_right_velocity = 0.0
        window.sleeve_left_angle = 0.0
        window.sleeve_right_angle = 0.0
        window.sleeve_left_velocity = 0.0
        window.sleeve_right_velocity = 0.0
        window._physics_tick()
        assert any(
            abs(value) > 0.0
            for value in (
                window.ornament_velocity,
                window.hair_left_velocity,
                window.hair_right_velocity,
                window.sleeve_left_velocity,
                window.sleeve_right_velocity,
            )
        )
        window.db.set_setting("physics_sleeves", False)
        window._reload_physics_settings()
        assert window.sleeve_left_overlay.isHidden()
        assert window.sleeve_right_overlay.isHidden()
        assert window.hair_left_overlay.isVisible()
        assert window.physics_overlay.isVisible()
        window.db.set_setting("physics_sleeves", True)
        window._reload_physics_settings()
        assert window.sleeve_left_overlay.isVisible()
        assert window.sleeve_right_overlay.isVisible()
        assert window.dashboard.tabs.count() == 7
        assert window.dashboard.windowTitle() == "墨寒．炎劍文化工作室"
        assert (
            window.dashboard.layout().sizeConstraint()
            == QLayout.SetNoConstraint
        )
        assert window.dashboard.minimumSize().height() == 480
        assert window.dashboard.maximumHeight() > 10000
        dashboard_was_visible = window.dashboard.isVisible()
        window.dashboard.show()
        for tab_index in (4, 5, 6):
            form_scroll = window.dashboard.tabs.widget(tab_index)
            assert isinstance(form_scroll, QScrollArea)
            assert form_scroll.objectName() == "formScrollPage"
            assert form_scroll.widget().objectName() == "formScrollContent"
            window.dashboard.tabs.setCurrentIndex(tab_index)
            app.processEvents()
            rendered = form_scroll.viewport().grab().toImage()
            assert not rendered.isNull()
            assert rendered.pixelColor(3, 3).name().lower() == "#122231"
        window.dashboard.tabs.setCurrentIndex(1)
        app.processEvents()
        split_sizes = window.dashboard.today_splitter.sizes()
        assert len(split_sizes) == 2
        assert min(split_sizes) > 0
        assert abs(split_sizes[0] - split_sizes[1]) <= 4
        assert window.dashboard.todo_scroll.widgetResizable()
        assert window.dashboard.idea_list.maximumHeight() > 10000
        if not dashboard_was_visible:
            window.dashboard.hide()
        window.dashboard.resize(760, 500)
        app.processEvents()
        assert window.dashboard.size().width() == 760
        assert window.dashboard.size().height() == 500
        window.dashboard.resize(1080, 820)
        app.processEvents()
        assert window.dashboard.size().width() == 1080
        assert window.dashboard.size().height() == 820
        assert window.dashboard.tabs.tabText(2) == "工作平台"
        assert window.dashboard.platform_controls == {}
        assert not window.dashboard.platform_empty.isHidden()
        window.dashboard.new_platform_name.setText("Company ERP")
        window.dashboard.new_platform_url.setText("portal.example.com")
        window.dashboard.add_custom_platform()
        assert "Company ERP" in window.dashboard.platform_controls
        platform = window.dashboard.platform_controls["Company ERP"]
        assert platform["url"].text() == "https://portal.example.com"
        platform["item_name"].setText("Q3 report")
        platform["missing"].setText("Manager approval")
        window.dashboard.save_platform("Company ERP", silent=True)
        saved_platform = next(
            row
            for row in window.db.platform_rows()
            if row["platform"] == "Company ERP"
        )
        assert saved_platform["item_name"] == "Q3 report"
        assert saved_platform["missing"] == "Manager approval"
        with patch(
            "app.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ):
            window.dashboard.delete_custom_platform("Company ERP")
        assert window.dashboard.platform_controls == {}
        assert window.db.platform_rows() == []
        assert not window.dashboard.windowIcon().isNull()
        assert not window.tray.icon().isNull()
        assert window.dashboard.windowFlags() & Qt.WindowMinimizeButtonHint
        assert window.dashboard.windowFlags() & Qt.WindowMaximizeButtonHint
        assert window.db.start_work()
        started_at = datetime.now() - timedelta(seconds=65)
        window.db.conn.execute(
            "UPDATE work_sessions SET started_at=? WHERE ended_at IS NULL",
            (started_at.isoformat(timespec="seconds"),),
        )
        window.db.conn.commit()
        window.dashboard.refresh_work_time()
        first_timer_text = window.dashboard.work_label.text()
        assert "00:01:" in first_timer_text
        assert "計時中" in first_timer_text
        QTest.qWait(1100)
        window.dashboard.refresh_work_time()
        assert window.dashboard.work_label.text() != first_timer_text
        assert window.db.stop_work()
        assert window.dashboard.permission_controls["delete_files"].currentText() == "禁止"
        assert window.dashboard.cloud_voice.currentText() == "coral"
        assert window.dashboard.tts_voice.currentText() == "coral"
        assert window.dashboard.realtime_voice.currentText() == "coral"
        assert (
            window.dashboard.voice_instructions.text()
            == window.db.setting("voice_instructions")
        )
        assert "二十多歲的女性動漫配音" in (
            window.dashboard.voice_instructions.text()
        )
        assert window.dashboard.realtime_voice.findText("nova") == -1
        assert (
            window.dashboard.windows_voice.currentData()
            == "OneCore::Microsoft Yating"
        )
        assert "OneCore" in window.dashboard.windows_voice.currentText()
        assert all(
            "zhiwei"
            not in window.dashboard.windows_voice.itemText(index).lower()
            for index in range(window.dashboard.windows_voice.count())
        )
        hanhan_index = window.dashboard.windows_voice.findData(
            "OneCore::Microsoft Hanhan"
        )
        yating_index = window.dashboard.windows_voice.findData(
            "OneCore::Microsoft Yating"
        )
        assert hanhan_index >= 0 and yating_index >= 0
        window.dashboard.windows_voice.setCurrentIndex(hanhan_index)
        assert (
            window.db.setting("windows_voice")
            == "OneCore::Microsoft Hanhan"
        )
        window.dashboard.windows_voice.setCurrentIndex(yating_index)
        assert (
            window.db.setting("windows_voice")
            == "OneCore::Microsoft Yating"
        )
        assert (
            window.dashboard.speech_recognition.currentText()
            == "OpenAI 高準確辨識（推薦）"
        )
        assert window.dashboard.windows_transcription_fallback.isChecked()
        window.dashboard.windows_transcription_fallback.setChecked(False)
        window.dashboard.save_voice_settings(silent=True)
        assert (
            window.db.setting("windows_transcription_fallback")
            is False
        )
        window.dashboard.windows_transcription_fallback.setChecked(True)
        window.dashboard.save_voice_settings(silent=True)
        assert "尚無" in window.dashboard.transcription_diagnostic.text()
        assert window.dashboard.ai_model.currentText() == "gpt-5.6-luna"
        assert window.dashboard.ai_model.findText("gpt-5.4-mini") == -1
        assert window.dashboard.ai_model.findText("gpt-5.6-luna") >= 0
        assert window.dashboard.ai_model.findText("gpt-5.6-terra") >= 0
        assert window.dashboard.ai_model.findText("gpt-5.6-sol") >= 0
        assert (
            window.dashboard.realtime_model.currentText()
            == "gpt-realtime-2.1-mini"
        )
        assert (
            window.dashboard.realtime_transcription_model.currentText()
            == "gpt-4o-mini-transcribe"
        )
        assert (
            window.dashboard.realtime_noise_reduction.currentData()
            == "near_field"
        )
        assert (
            window.dashboard.realtime_turn_detection.currentData()
            == "server_vad"
        )
        assert (
            window.dashboard.realtime_hybrid_transcription.isChecked()
        )
        window.dashboard.save_voice_settings(silent=True)
        assert (
            window.db.setting("realtime_transcription_model")
            == "gpt-4o-mini-transcribe"
        )
        assert (
            window.db.setting("realtime_noise_reduction")
            == "near_field"
        )
        assert (
            window.db.setting("realtime_turn_detection")
            == "server_vad"
        )
        assert window.dashboard.realtime_echo_guard.isChecked()
        assert (
            window.db.setting("realtime_hybrid_transcription")
            is True
        )
        window.dashboard.voice_rate.setValue(-1)
        QTest.mouseClick(window.dashboard.voice_rate_up, Qt.LeftButton)
        assert window.dashboard.voice_rate.value() == 0
        QTest.mouseClick(window.dashboard.voice_rate_down, Qt.LeftButton)
        assert window.dashboard.voice_rate.value() == -1
        assert window.dashboard.voice_volume.value() == 125
        assert window.dashboard.voice_volume_label.text() == "125%"
        window.dashboard.voice_volume.setValue(140)
        assert window.db.setting("voice_volume_percent") == 140
        assert window.tts.volume_percent == 140
        assert window.cloud_tts.volume_percent == 140
        assert window.realtime.volume_percent == 140
        window.dashboard.voice_muted.setChecked(True)
        assert window.db.setting("voice_muted") is True
        assert window.tts.muted
        assert window.cloud_tts.muted
        assert window.realtime.muted
        window.dashboard.voice_muted.setChecked(False)
        for kind, (_, time_editor) in window.dashboard.reminder_controls.items():
            original_time = time_editor.time()
            up, down = window.dashboard.reminder_step_buttons[kind]
            QTest.mouseClick(up, Qt.LeftButton)
            assert time_editor.time() != original_time
            QTest.mouseClick(down, Qt.LeftButton)
            assert time_editor.time() == original_time
        original_break_minutes = window.dashboard.break_minutes.value()
        QTest.mouseClick(
            window.dashboard.break_minutes_up,
            Qt.LeftButton,
        )
        assert (
            window.dashboard.break_minutes.value()
            == original_break_minutes + 1
        )
        QTest.mouseClick(
            window.dashboard.break_minutes_down,
            Qt.LeftButton,
        )
        assert window.dashboard.break_minutes.value() == original_break_minutes
        assert window.dashboard.chat_zoom_label.text() == "100%"
        QTest.mouseClick(window.dashboard.chat_zoom_up, Qt.LeftButton)
        assert window.dashboard.chat_zoom_percent == 110
        assert window.db.setting("chat_zoom_percent") == 110
        window.dashboard.chat.zoom_step_requested.emit(-1)
        assert window.dashboard.chat_zoom_percent == 100
        assert "準備就緒" in window.dashboard.voice_phase.text()
        window.listener._recording_active.set()
        window.listener.recording_changed.emit(True)
        app.processEvents()
        assert window.dashboard.mic_btn.isEnabled()
        assert "立即送出" in window.dashboard.mic_btn.text()
        window.listener._recording_active.clear()
        window.listener.recording_changed.emit(False)
        app.processEvents()
        assert not window.dashboard.mic_btn.isEnabled()
        assert "辨識中" in window.dashboard.mic_btn.text()
        window.listener.listening_changed.emit(False)
        app.processEvents()
        assert window.dashboard.mic_btn.isEnabled()
        assert "麥克風" in window.dashboard.mic_btn.text()
        window.listener.status_changed.emit("收音中…")
        app.processEvents()
        assert "收音中" in window.dashboard.voice_phase.text()
        window.dashboard.set_voice_phase("準備就緒")
        window._realtime_user_text("你还记得自己的故事吗？")
        window._realtime_assistant_text("妾会保持专注，好好陪着你。")
        app.processEvents()
        chat_text = window.dashboard.chat.toPlainText()
        assert "你還記得自己的故事嗎？" in chat_text
        assert "妾會保持專注，好好陪著你。" in chat_text
        assert "你还记得" not in chat_text
        history_manager = ChatHistoryDialog(window.db)
        assert history_manager.history_list.count() == window.db.chat_count()
        history_manager.history_list.item(0).setCheckState(Qt.Checked)
        assert len(history_manager.checked_chat_ids()) == 1
        history_manager.close()
        assert window.db.list_todos() == []
        window.dashboard.blockSignals(True)
        window.dashboard.todo_input.setText("完成漫畫第 3 話分鏡")
        window.dashboard.add_todo()
        app.processEvents()
        todos = window.db.list_todos()
        assert len(todos) == 1
        assert todos[0]["title"] == "完成漫畫第 3 話分鏡"
        assert window.dashboard.todo_count.text() == "1 件未完成"
        assert "完成漫畫第 3 話分鏡" in window.dashboard.todo_feedback.text()
        visible_todo_titles = [
            label.text()
            for label in window.dashboard.findChildren(QLabel, "todoTitle")
        ]
        assert "完成漫畫第 3 話分鏡" in visible_todo_titles
        assert (
            window.dashboard.todo_scroll.viewport().objectName()
            == "todoViewport"
        )
        window.dashboard.todo_input.setText("劍魂在雨夜醒來")
        window.dashboard.add_idea()
        app.processEvents()
        assert len(window.db.list_ideas()) == 1
        assert window.dashboard.idea_count.text() == "1 則"
        assert "劍魂在雨夜醒來" in window.dashboard.idea_list.item(0).text()
        assert window.dashboard.idea_list.item(0).data(Qt.UserRole)
        window.dashboard.idea_list.item(0).setCheckState(Qt.Checked)
        assert window.dashboard.checked_idea_ids() == [
            window.dashboard.idea_list.item(0).data(Qt.UserRole)
        ]
        window.dashboard.idea_list.item(0).setCheckState(Qt.Unchecked)
        editor = IdeaEditorDialog("剑魂故事", "她听见主上的声音。")
        assert editor.values() == (
            "劍魂故事",
            "她聽見主上的聲音。",
        )
        editor.close()
        window.dashboard.memory_input.setText("林小姐是我的出版窗口")
        window.dashboard.memory_category.setCurrentText("人物")
        window.dashboard.add_memory()
        app.processEvents()
        memories = window.db.list_memories(category="人物")
        assert len(memories) == 1
        assert memories[0]["title"] == "林小姐是我的出版視窗"
        assert window.dashboard.memory_count.text() == "1 則"
        assert "【人物】" in window.dashboard.memory_list.item(0).text()
        assert "全部記憶（1）" == window.dashboard.memory_filter.itemText(0)
        person_filter = window.dashboard.memory_filter.findData("人物")
        window.dashboard.memory_filter.setCurrentIndex(person_filter)
        app.processEvents()
        assert window.dashboard.memory_list.count() == 1
        memory_item = window.dashboard.memory_list.item(0)
        memory_item.setCheckState(Qt.Checked)
        assert window.dashboard.checked_memory_ids() == [
            int(memories[0]["id"])
        ]
        memory_editor = MemoryEditorDialog(memories[0])
        memory_editor.title_input.setText("主要出版窗口")
        memory_editor.content_input.setPlainText("林小姐每週一聯絡")
        memory_editor.category_input.setCurrentText("工作流程")
        assert memory_editor.values() == (
            "主要出版視窗",
            "林小姐每週一聯絡",
            "工作流程",
            4,
        )
        memory_editor.close()
        with patch(
            "app.QMessageBox.question",
            return_value=QMessageBox.Yes,
        ):
            window.dashboard.delete_checked_memories()
        assert window.db.list_memories() == []
        window.dashboard.blockSignals(False)
        window.speak("第一句", "speaking")
        window.speak("第二句", "happy")
        assert window.speech_playing is True
        assert window.mouth_timer.isActive()
        assert window.mouth_open is False
        window._mouth_tick()
        assert window.mouth_frame_index == 1
        assert window.mouth_open is True
        assert window.current_expression == window.speech_mid_expression
        expected_speech_blink = window._speaking_blink_expression()
        assert expected_speech_blink.startswith("blink_mid")
        pre_blink_key = window.character.pixmap().cacheKey()
        window._blink()
        assert window.speech_blinking is True
        assert window.current_expression == window.speech_mid_expression
        assert window.character.pixmap().cacheKey() != pre_blink_key
        # Blinking is an eye-only layer. Speech timing must keep advancing
        # underneath it instead of pausing and restoring a stale mouth frame.
        assert window.mouth_timer.isActive()
        window._finish_speaking_blink(
            window.speech_mid_expression,
            window.blink_generation,
        )
        assert window.speech_blinking is False
        assert window.current_expression == window.speech_mid_expression
        assert window.mouth_timer.isActive()
        assert list(window.speech_queue) == [("第二句", "happy")]
        window._speech_audio_finished()
        assert window.mouth_open is False
        assert window.speech_blinking is False
        QTest.qWait(160)
        app.processEvents()
        assert window.speech_playing is True
        assert list(window.speech_queue) == []
        window._speech_audio_finished()
        window.state = "speaking"
        window.speech_closed_expression = window._idle_expression()
        window.speech_mid_expression = window._mouth_mid_expression()
        window.speech_open_expression = window._speaking_expression()
        window.speech_gesture_expression = None
        window._start_mouth_animation(audio_driven=True)
        assert window.audio_driven_mouth is True
        assert not window.mouth_timer.isActive()
        window._audio_viseme_cue(0.85, "I")
        window._audio_viseme_cue(0.85, "I")
        window._audio_viseme_cue(0.85, "I")
        assert window.current_expression.startswith("mouth_i")
        assert window.mouth_open is True
        position_after_loud_cue = window.character.y()
        assert position_after_loud_cue < window.character_base_y
        viseme_before_blink = window.current_expression
        viseme_pixmap_key = window.character.pixmap().cacheKey()
        window._blink()
        assert window.speech_blinking is True
        assert window.current_expression == viseme_before_blink
        assert window.character.pixmap().cacheKey() != viseme_pixmap_key
        window._finish_speaking_blink(
            window.speech_current_expression,
            window.blink_generation,
        )
        assert window.speech_blinking is False
        assert not window.mouth_timer.isActive()
        window._audio_viseme_cue(0.9, "O")
        window._audio_viseme_cue(0.9, "O")
        window._audio_viseme_cue(0.9, "O")
        assert window.current_expression.startswith("mouth_o")
        window._stop_mouth_animation()
        assert window.mouth_open is False
        # Speech emphasis settles back to the anchor instead of snapping on
        # the exact audio-finished frame.
        assert window.character.y() <= window.character_base_y
        for _ in range(32):
            window._motion_tick()
        assert window.character.y() == window.character_base_y
        window.state = "idle"

        class DummyStream:
            def __init__(self):
                self.aborts = 0
                self.closes = 0

            def abort(self):
                self.aborts += 1

            def close(self):
                self.closes += 1

        dummy_input = DummyStream()
        dummy_output = DummyStream()
        window.realtime._input_stream = dummy_input
        window.realtime._output_stream = dummy_output
        closers = [
            threading.Thread(target=window.realtime._close_audio)
            for _ in range(4)
        ]
        for closer in closers:
            closer.start()
        for closer in closers:
            closer.join()
        assert dummy_input.aborts == dummy_input.closes == 1
        assert dummy_output.aborts == dummy_output.closes == 1
        window.dashboard.profile_assistant_name.setText("Ava")
        window.dashboard.profile_user_title.setText("Alex")
        window.dashboard.profile_organization_name.setText("Example Team")
        window.dashboard.profile_window_title.setText("Ava Workspace")
        with patch("app.set_autostart"):
            window.dashboard.save_settings()
        app.processEvents()
        assert window.db.setting("assistant_name") == "Ava"
        assert window.db.setting("user_title") == "Alex"
        assert window.dashboard.windowTitle() == "Ava Workspace"
        assert window.windowTitle() == "Ava Workspace"
        assert window.dashboard.header_title.text() == "<b>Ava Workspace</b>"
        assert window.bubble_name.text() == "Ava"
        assert window.tray.toolTip() == "Ava Workspace"
        preview = os.getenv("MOHAN_PREVIEW_PATH")
        if preview:
            window.grab().save(preview)
            window._show_bubble(
                "主上，妾已把今日的工作拆成三步：先完成漫畫分鏡，"
                "再核對出版平台資料，最後整理明日要用的素材。"
                "其餘細節妾會留在對話頁，不讓桌面氣泡遮住你的工作。"
            )
            app.processEvents()
            window.grab().save(
                str(Path(preview).with_name("墨寒-v1.14-長對話氣泡.png"))
            )
            window.bubble.hide()
            window.dashboard.show()
            app.processEvents()
            dashboard_path = str(Path(preview).with_name("墨寒語音完整版-v0.9-設定介面.png"))
            window.dashboard.grab().save(dashboard_path)
            window.dashboard.tabs.setCurrentIndex(4)
            app.processEvents()
            window.dashboard.grab().save(
                str(Path(preview).with_name("墨寒語音完整版-v0.9-聲音頁.png"))
            )
            window.dashboard.tabs.setCurrentIndex(5)
            app.processEvents()
            window.dashboard.grab().save(
                str(Path(preview).with_name("墨寒語音完整版-v0.9-權限頁.png"))
            )
            window.dashboard.tabs.setCurrentIndex(1)
            app.processEvents()
            window.dashboard.grab().save(
                str(Path(preview).with_name("墨寒語音完整版-v0.9-今日待辦頁.png"))
            )
            window.db.add_memory(
                "林小姐是主上的主要出版視窗，固定於週一聯絡。",
                "人物",
                "manual",
                5,
                "主要出版視窗",
            )
            window.db.add_memory(
                "主上偏好先完成創作，再集中處理行政事項。",
                "偏好",
                "manual",
                4,
                "工作順序偏好",
            )
            window.dashboard.refresh_memories()
            window.dashboard.tabs.setCurrentIndex(3)
            app.processEvents()
            window.dashboard.grab().save(
                str(Path(preview).with_name("墨寒-v1.22-長期記憶頁.png"))
            )
            memory_preview_row = window.db.list_memories()[0]
            memory_editor = MemoryEditorDialog(
                memory_preview_row,
                window.dashboard,
            )
            memory_editor.show()
            app.processEvents()
            memory_editor.grab().save(
                str(Path(preview).with_name("墨寒-v1.22-記憶編輯視窗.png"))
            )
            memory_editor.close()
            idea_editor = IdeaEditorDialog(
                "雨夜中的赤焰劍",
                "墨寒在雨幕裡聽見劍鳴，轉身看向主上。\n"
                "待補：場景色調、關鍵台詞、分鏡節奏。",
                window.dashboard,
            )
            idea_editor.show()
            app.processEvents()
            idea_editor.grab().save(
                str(Path(preview).with_name("墨寒-v1.13-靈感編輯視窗.png"))
            )
            idea_editor.close()
        window.close()
        app.processEvents()
    print("UI_SMOKE_OK")


if __name__ == "__main__":
    run()
