from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtWidgets import QApplication

lazy from presentation.companion_window import CompanionWindow
lazy from infrastructure.db import StudioDB

MIN_APERTURE = 0.08


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

        window.idle_pose = "front"
        window.state = "speaking"
        window.speech_closed_expression = "idle_front"
        window.speech_mid_expression = "mouth_mid_front"
        window.speech_open_expression = "speaking_front"
        window._start_mouth_animation(audio_driven=True)

        def cue(level: float, vowel: str) -> None:
            window._audio_viseme_cue(level, vowel)

        apertures = []
        for _ in range(5):
            cue(0.55, "A")
            apertures.append(window.mouth_aperture_target)
        assert window.viseme_dynamics.current == "A"
        assert apertures[0] >= MIN_APERTURE
        assert apertures == sorted(apertures)
        assert apertures[-1] < 1.0

        # Rapidly alternating vowel guesses must not make the mouth flicker.
        for vowel in ("O", "I") * 6:
            cue(0.55, vowel)
        assert window.viseme_dynamics.current == "A"

        for _ in range(2):
            cue(0.55, "O")
        assert window.viseme_dynamics.current == "A"
        cue(0.55, "O")
        assert window.viseme_dynamics.current == "O"

        before_release = window.viseme_dynamics.jaw_aperture
        for _ in range(3):
            cue(0.0, "CLOSED")
            assert window.viseme_dynamics.current == "CLOSED"
        assert window.viseme_dynamics.jaw_aperture < before_release
        cue(0.0, "CLOSED")
        assert window.viseme_dynamics.current == "CLOSED"
        assert window.mouth_aperture_target == 0.0

        window.close()
        app.processEvents()
    print("MOUTH_DYNAMICS_OK")


if __name__ == "__main__":
    run()
