from __future__ import annotations

lazy import sys
lazy import tempfile
lazy from datetime import datetime
lazy from pathlib import Path
lazy from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from infrastructure.db import StudioDB
lazy from proactive_companion_app_bridge import (
    ProactiveAppDisposition,
    ProactiveAppEvent,
    ProactiveAppState,
)
lazy from proactive_companion_composition import create_proactive_companion_bridge
lazy from visual_perception import PresenceState
lazy from wellbeing_app_bridge import ReminderTrigger


def _state(now: datetime) -> ProactiveAppState:
    return ProactiveAppState(
        generation=1,
        now=now,
        language="zh-TW",
        user_title="使用者",
        session_user_active=True,
        camera_enabled=False,
        camera_presence=PresenceState.UNKNOWN,
        seconds_since_user_interaction=0.0,
    )


def run() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        db = StudioDB(Path(temporary) / "mohan.db")
        submitted: list[tuple[str, str, str, object]] = []

        def enqueue(text: str, state: str, token: str, completed) -> bool:
            submitted.append((text, state, token, completed))
            return True

        bridge = create_proactive_companion_bridge(db, enqueue)
        local_now = datetime.now().astimezone()
        now = local_now.replace(
            year=max(2000, local_now.date().year),
            hour=12,
            minute=0,
            second=0,
            microsecond=0,
        )
        # The occasion service reads the real wall clock (not the injected
        # ``now``), so on a special-occasion day such as Qixi it would outrank
        # the lunch reminder and change the submitted speech state.  Neutralise
        # the occasion lookup so this test deterministically exercises the
        # reminder path regardless of the calendar date.
        with patch(
            "application.wellbeing_runtime.active_occasion",
            return_value=None,
        ):
            result = bridge.dispatch(
                ProactiveAppEvent(_state(now), ReminderTrigger.LUNCH)
            )
        assert result.disposition is ProactiveAppDisposition.SUBMITTED
        assert len(submitted) == 1
        assert submitted[0][0].strip()
        assert submitted[0][1] == "reminder"
        assert submitted[0][2]
        submitted[0][3](True)
        db.close()
    print("PROACTIVE_COMPANION_COMPOSITION_OK")


if __name__ == "__main__":
    run()
