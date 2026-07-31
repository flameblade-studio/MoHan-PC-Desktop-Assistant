from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app import CompanionWindow
from db import StudioDB


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        db_path = (
            Path(temp_dir)
            / "YanJianStudio"
            / "MoHan"
            / "mohan.db"
        )
        preflight = StudioDB(db_path)
        preflight.set_setting("tts_enabled", False)
        preflight.close()
        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        for timer in window.findChildren(QTimer):
            timer.stop()

        window.idle_pose = "front"
        window.state = "speaking"
        window.speech_playing = True
        window.audio_driven_mouth = True
        window.speech_closed_expression = "idle_front"
        window.speech_mid_expression = "mouth_mid_front"
        window.speech_open_expression = "speaking_front"
        window.after_speech_state = "idle"
        window.current_expression = "mouth_o_front"
        window.character.setPixmap(
            window.expression_pixmaps["mouth_o_front"]
        )
        window._speech_audio_finished()
        assert window.speech_playing
        assert window.speech_finish_timer.isActive()
        assert window.mouth_visual_timer.isActive()
        assert window.current_expression == "idle_front"
        # Duplicate completion signals must not skip the natural mouth close.
        window._speech_audio_finished()
        assert window.speech_playing
        assert window.speech_finish_timer.isActive()
        QTest.qWait(165)
        app.processEvents()
        assert not window.speech_playing
        assert not window.speech_finish_timer.isActive()
        assert not window.mouth_visual_timer.isActive()
        assert window.state == "idle"
        assert window.character.pixmap().cacheKey() == (
            window.expression_pixmaps["idle_front"].cacheKey()
        )

        window.state = "speaking"
        window.audio_driven_mouth = True
        window.speech_closed_expression = "idle_front"
        window.speech_mid_expression = "mouth_mid_front"
        window.speech_open_expression = "speaking_front"
        window.current_expression = "mouth_i_front"
        window.character.setPixmap(
            window.expression_pixmaps["mouth_i_front"]
        )
        window.realtime_after_speech_state = "idle"
        window._realtime_speaking(False)
        assert window.realtime_finish_timer.isActive()
        assert window.mouth_visual_timer.isActive()
        assert window.mouth_closing
        closing_expression = window.current_expression
        closing_target = window.mouth_transition_to.cacheKey()
        for _ in range(4):
            window._audio_viseme_cue(0.8, "A")
        assert window.current_viseme == "CLOSED"
        assert window.current_expression == closing_expression
        assert window.mouth_transition_to.cacheKey() == closing_target
        window._realtime_speaking(False)
        assert window.realtime_finish_timer.isActive()
        QTest.qWait(165)
        app.processEvents()
        assert not window.realtime_finish_timer.isActive()
        assert not window.mouth_visual_timer.isActive()
        assert window.state == "idle"

        # A normal Realtime transcript maps to idle after playback. "speaking"
        # must never survive as a post-audio state and restart the mouth timer.
        window._realtime_speaking(True)
        window._realtime_assistant_text("主上，妾已經聽明白了。")
        assert window.realtime_after_speech_state == "idle"
        window._audio_viseme_cue(0.42, "A")
        window._realtime_speaking(False)
        QTest.qWait(165)
        app.processEvents()
        assert window.state == "idle"
        assert not window.mouth_timer.isActive()
        assert not window.mouth_visual_timer.isActive()
        QTest.qWait(180)
        app.processEvents()
        assert window.state == "idle"
        assert not window.mouth_timer.isActive()

        # Internal emotion metadata is never shown, logged or spoken.
        window._realtime_speaking(True)
        window._realtime_assistant_text(
            "主上，妾會護著你。"
            "[[MOHAN_EMOTION:protective:0.86]]"
        )
        assert window.realtime_after_speech_state == "protective_front"
        assert window.realtime_after_speech_intensity == 0.86
        assert "MOHAN_EMOTION" not in window.bubble_text.text()
        assert "MOHAN_EMOTION" not in window.db.recent_chat(1)[0][
            "content"
        ]
        window._realtime_speaking(False)
        window._complete_realtime_speaking_stop()

        # A new answer always clears a previous special expression selection.
        window.realtime_after_speech_state = "mock_scold"
        window._realtime_speaking(True)
        assert window.realtime_after_speech_state == "idle"
        window._realtime_speaking(False)
        QTest.qWait(130)
        app.processEvents()
        assert window.state == "idle"

        # A stale delayed idle callback cannot interrupt an active answer.
        window._realtime_speaking(True)
        window._return_to_idle()
        assert window.state == "speaking"
        window._realtime_speaking(False)
        QTest.qWait(130)
        app.processEvents()
        assert window.state == "idle"

        # Realtime completion must also recover from an unrelated state
        # change and leave no mouth animation timer running.
        window.realtime_mouth_active = True
        window.state = "idle"
        window.audio_driven_mouth = True
        window.current_expression = "mouth_o_front"
        window.character.setPixmap(
            window.expression_pixmaps["mouth_o_front"]
        )
        window.mouth_visual_timer.start()
        window.realtime_finish_timer.start(500)
        window._realtime_speaking(False)
        assert window.realtime_finish_timer.isActive()
        window._complete_realtime_speaking_stop()
        assert not window.realtime_finish_timer.isActive()
        assert not window.mouth_visual_timer.isActive()
        assert not window.audio_driven_mouth
        assert not window.realtime_mouth_active
        assert window.current_expression == "idle_front"

        # A queued reply starts only after the prior reply closes naturally.
        window.state = "speaking"
        window.speech_playing = True
        window.audio_driven_mouth = True
        window.speech_closed_expression = "idle_front"
        window.speech_mid_expression = "mouth_mid_front"
        window.speech_open_expression = "speaking_front"
        window.current_expression = "mouth_o_front"
        window.character.setPixmap(
            window.expression_pixmaps["mouth_o_front"]
        )
        window.after_speech_state = "idle"
        window.speech_queue.append(("下一句", "idle"))
        window._speech_audio_finished()
        QTest.qWait(165)
        app.processEvents()
        assert not window.speech_finish_timer.isActive()
        assert not window.speech_playing
        QTest.qWait(140)
        app.processEvents()
        assert window.speech_playing
        assert window.state == "speaking"
        assert "下一句" in window.bubble_text.text()

        window.close()
        app.processEvents()
    print("SPEECH_STATE_MACHINE_OK")


if __name__ == "__main__":
    run()
