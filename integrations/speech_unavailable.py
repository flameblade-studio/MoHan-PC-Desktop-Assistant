from __future__ import annotations

lazy from PySide6.QtCore import QObject, Signal


class UnavailableSystemTTS(QObject):
    """Fail closed when a platform has no verified local speech adapter."""

    failed = Signal(str)
    finished = Signal()
    viseme_cue = Signal(float, str)

    def __init__(
        self,
        reason: str,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.reason = reason
        self.volume_percent = 125
        self.muted = False

    def set_volume(self, volume_percent: int, muted: bool = False) -> None:
        self.volume_percent = max(0, min(160, int(volume_percent)))
        self.muted = bool(muted)

    def speak(self, text: str, voice_name: str = "", rate: int = -1) -> None:
        del voice_name, rate
        if text.strip():
            self.failed.emit(self.reason)
        self.finished.emit()

    def stop(self) -> None:
        """Match the local speech contract when no adapter is available."""
