from __future__ import annotations

lazy from collections.abc import Callable
lazy from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GestureApplicationCallbacks:
    show_control_center: Callable[[], None]
    hide_control_center: Callable[[], None]
    set_audio_muted: Callable[[bool], None]
    stop_current_speech: Callable[[], None]
    toggle_listening: Callable[[], None]
    set_realtime_enabled: Callable[[bool], None]
    set_interaction_mode: Callable[[str], None]
    acknowledge_positive: Callable[[], None]
    submit_safe_text_command: Callable[[str], None]

    def __post_init__(self) -> None:
        if not all(
            callable(callback)
            for callback in (
                self.show_control_center,
                self.hide_control_center,
                self.set_audio_muted,
                self.stop_current_speech,
                self.toggle_listening,
                self.set_realtime_enabled,
                self.set_interaction_mode,
                self.acknowledge_positive,
                self.submit_safe_text_command,
            )
        ):
            raise TypeError("Gesture application callbacks must be callable.")


class GestureApplicationAdapter:
    """One explicit bridge from gesture intents to established application paths."""

    def __init__(self, callbacks: GestureApplicationCallbacks) -> None:
        if not isinstance(callbacks, GestureApplicationCallbacks):
            raise TypeError("Gesture application callbacks must be canonical.")
        self._callbacks = callbacks

    def show_control_center(self) -> None:
        self._callbacks.show_control_center()

    def hide_control_center(self) -> None:
        self._callbacks.hide_control_center()

    def set_audio_muted(self, muted: bool) -> None:
        if type(muted) is not bool:
            raise TypeError("Gesture mute state must be boolean.")
        self._callbacks.set_audio_muted(muted)

    def stop_current_speech(self) -> None:
        self._callbacks.stop_current_speech()

    def toggle_listening(self) -> None:
        self._callbacks.toggle_listening()

    def set_realtime_enabled(self, enabled: bool) -> None:
        if type(enabled) is not bool:
            raise TypeError("Gesture Realtime state must be boolean.")
        self._callbacks.set_realtime_enabled(enabled)

    def set_interaction_mode(self, mode: str) -> None:
        canonical = mode.strip()
        if canonical not in {"work", "companion", "do-not-disturb"}:
            raise ValueError("Gesture interaction mode is unsupported.")
        self._callbacks.set_interaction_mode(canonical)

    def acknowledge_positive(self) -> None:
        self._callbacks.acknowledge_positive()

    def submit_safe_text_command(self, command: str) -> None:
        canonical = command.strip()
        if not canonical or len(canonical) > 256 or any(
            character in canonical for character in "\r\n\0"
        ):
            raise ValueError("Gesture text command must be one short line.")
        self._callbacks.submit_safe_text_command(canonical)
