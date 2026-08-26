"""Desktop companion status card for the dashboard shell.

The dashboard shell stays within the physically layered line budget by
delegating the desktop companion's live status card construction and its
label updates to this small presentation helper module.  Every function here
belongs to the presentation layer and only touches companion UI concerns.
"""

from __future__ import annotations

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

lazy from presentation.ui_localization import (
    MODE_LABELS,
    SIMPLIFIED_MODE_LABELS,
    display_label,
)
lazy from presentation.ui_localization_ja import JAPANESE_MODE_LABELS

__all__ = (
    "build_desktop_companion_stage",
    "desktop_companion_initial_status",
    "gesture_status_message",
    "mode_status_label",
    "update_desktop_companion_status",
    "visual_status_message",
)


def desktop_companion_initial_status(shell) -> dict[str, str]:
    """Seed the five live status rows in the console's current language."""

    return {
        "mode": mode_status_label(shell, shell.mode),
        "expression": shell._t("desktop_status_idle", "待機中"),
        "voice": shell._t("voice_ready_short", "準備就緒"),
        "vision": shell._t("desktop_status_camera_waiting", "鏡頭待命"),
        "gesture": shell._t("desktop_status_gesture_waiting", "等待手勢"),
    }


def mode_status_label(shell, mode: str) -> str:
    """Localize a companion mode for the status card."""

    return display_label(
        shell.ui_language,
        mode,
        MODE_LABELS,
        SIMPLIFIED_MODE_LABELS,
        JAPANESE_MODE_LABELS,
    )


def build_desktop_companion_stage(
    shell,
    status_values: dict[str, str],
) -> tuple[QFrame, dict[str, QLabel]]:
    """Build the desktop companion stage with a live status card.

    Returns the stage frame together with the live value labels so the caller
    can keep updating them across dashboard rebuilds.
    """

    stage = QFrame()
    stage.setObjectName("desktopCompanionStage")
    stage.setProperty("mohanRole", "desktopCompanionStage")
    # Keep the live stage present on compact dashboards without forcing it
    # underneath the conversation dock.  The old 400 px hard minimum combined
    # with the dock's 500 px minimum exceeded the space left beside navigation.
    stage.setMinimumWidth(220)
    stage.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
    stage_layout = QVBoxLayout(stage)
    stage_layout.setContentsMargins(18, 18, 18, 18)
    status_card = QFrame()
    status_card.setObjectName("desktopCompanionStatusCard")
    status_card.setProperty("mohanRole", "desktopCompanionStatusCard")
    status_card.setMinimumWidth(0)
    status_card.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
    status_layout = QVBoxLayout(status_card)
    status_layout.setContentsMargins(18, 18, 18, 18)
    status_layout.setSpacing(12)
    status_title = QLabel(
        shell._t("desktop_status_title", "墨寒正在桌面上與您互動")
    )
    status_title.setProperty("mohanRole", "desktopCompanionStatusTitle")
    status_title.setWordWrap(True)
    status_layout.addWidget(status_title)
    status_note = QLabel(
        shell._t(
            "desktop_status_description",
            "桌面上的墨寒是唯一可見、可拖移並會回應您的角色。",
        )
    )
    status_note.setProperty("mohanRole", "desktopCompanionStatusNote")
    status_note.setWordWrap(True)
    status_layout.addWidget(status_note)
    labels: dict[str, QLabel] = {}
    for key, caption in (
        ("mode", shell._t("desktop_status_mode", "模式")),
        ("expression", shell._t("desktop_status_expression", "姿態／表情")),
        ("voice", shell._t("desktop_status_voice", "語音")),
        ("vision", shell._t("desktop_status_vision", "鏡頭感知")),
        ("gesture", shell._t("desktop_status_gesture", "手勢")),
    ):
        row = QFrame()
        row.setProperty("mohanRole", "desktopCompanionStatusRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(10)
        name = QLabel(caption)
        name.setProperty("mohanRole", "desktopCompanionStatusName")
        name.setMinimumWidth(0)
        value = QLabel(status_values[key])
        value.setObjectName(f"desktopCompanionStatus{key.title()}")
        value.setProperty("mohanRole", "desktopCompanionStatusValue")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value.setWordWrap(True)
        value.setMinimumWidth(0)
        row_layout.addWidget(name)
        row_layout.addWidget(value, 1)
        status_layout.addWidget(row)
        labels[key] = value
    status_layout.addStretch(1)
    stage_layout.addWidget(status_card, 1)
    return stage, labels


def update_desktop_companion_status(
    shell,
    status_values: dict[str, str],
    label_sets: list[dict[str, QLabel]],
    key: str,
    value: str,
) -> list[dict[str, QLabel]]:
    """Reflect one status value, discarding label sets whose widgets died.

    Feature pages can be reconstructed while the dashboard is hidden.  Those
    released Qt labels are dropped, while a gesture must still be able to
    open the real desktop conversation.
    """

    status_values[key] = str(value).strip()
    live: list[dict[str, QLabel]] = []
    for labels in label_sets:
        label = labels.get(key)
        try:
            if label is not None:
                label.setText(status_values[key])
        except RuntimeError:
            continue
        live.append(labels)
    return live


def visual_status_message(
    presence: str,
    *,
    active: bool = False,
) -> tuple[str, str]:
    """Pick the vision status translation key for camera activity."""

    if active and presence == "present":
        return "desktop_status_vision_motion", "偵測到活動"
    return {
        "present": ("desktop_status_vision_present", "已看見您"),
        "away": ("desktop_status_vision_away", "暫時未看見您"),
    }.get(presence, ("desktop_status_vision_unknown", "鏡頭待命"))


def gesture_status_message(gesture: str) -> tuple[str, str]:
    """Pick the gesture status translation key without leaking internal labels."""

    return {
        "wave": ("desktop_status_gesture_wave", "已辨識揮手"),
    }.get(gesture, ("desktop_status_gesture_waiting", "等待手勢"))
