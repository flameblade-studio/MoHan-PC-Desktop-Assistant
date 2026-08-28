from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from application.desktop_presence import seconds_since_local_input


def run() -> None:
    with patch("application.desktop_presence.sys.platform", "linux"):
        assert seconds_since_local_input() is None
    if sys.platform == "win32":
        value = seconds_since_local_input()
        assert value is None or value >= 0.0


if __name__ == "__main__":
    run()
    print("DESKTOP_PRESENCE_OK")
