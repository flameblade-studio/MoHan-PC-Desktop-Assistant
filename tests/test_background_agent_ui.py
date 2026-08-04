from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from app import CompanionWindow
from background_agents import AgentObservation
from db import StudioDB


class FakeScheduler:
    def __init__(self) -> None:
        self.closed = False
        self.quiet_values: list[bool] = []
        self.pending = True

    def tick(self) -> None:
        return

    def drain(self, *, now=None, quiet=False):
        self.quiet_values.append(bool(quiet))
        if quiet or not self.pending:
            return []
        self.pending = False
        return [
            AgentObservation(
                "test",
                "ide-report",
                "唯讀診斷已完成。",
                "attentive_front",
            )
        ]

    def close(self) -> None:
        self.closed = True


def run() -> None:
    with TemporaryDirectory() as temp_dir:
        os.environ["LOCALAPPDATA"] = temp_dir
        db_path = Path(temp_dir) / "YanJianStudio" / "MoHan" / "mohan.db"
        preflight = StudioDB(db_path)
        preflight.set_setting("tts_enabled", False)
        preflight.close()

        app = QApplication([])
        window = CompanionWindow(startup_speech=False)
        window.show()
        app.processEvents()
        window.background_agent_timer.stop()
        fake = FakeScheduler()
        window.background_scheduler = fake
        window.state = "idle"
        window._background_agent_tick()
        app.processEvents()
        assert window.state == "attentive_front"
        assert "唯讀診斷" in window.bubble_text.text()
        assert fake.quiet_values == [False]

        window.set_state("idle", force=True)
        window.dashboard.mode = "勿擾"
        fake.pending = True
        window._background_agent_tick()
        assert fake.quiet_values[-1] is True
        assert fake.pending

        window.close()
        app.processEvents()
        assert fake.closed

    print("BACKGROUND_AGENT_UI_ARBITRATION_OK")


if __name__ == "__main__":
    run()
