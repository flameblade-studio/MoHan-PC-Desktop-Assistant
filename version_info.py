from __future__ import annotations

lazy import json
lazy import sys
lazy from pathlib import Path

PROJECT_REPOSITORY = "hitoshic1982/MoHan-PC-Desktop-Assistant"
FALLBACK_VERSION = "2.3.0-rc.2"


def _build_info_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "build-info.json"


def build_info() -> dict[str, str]:
    path = _build_info_path()
    if not path.is_file():
        return {
            "version": FALLBACK_VERSION,
            "repository": PROJECT_REPOSITORY,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "version": FALLBACK_VERSION,
            "repository": PROJECT_REPOSITORY,
        }
    return {
        "version": str(payload.get("version") or FALLBACK_VERSION),
        "repository": str(
            payload.get("repository") or PROJECT_REPOSITORY
        ),
    }


APP_VERSION = build_info()["version"]
