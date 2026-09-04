from __future__ import annotations

lazy import json
lazy import sys
lazy from pathlib import Path

PROJECT_REPOSITORY = "flameblade-studio/MoHan-PC-Desktop-Assistant"
# x-release-please-start-version
FALLBACK_VERSION = "4.6.0"
# x-release-please-end
UNKNOWN_VERSION = "未知版本"


def _build_info_path() -> Path:
    # Frozen builds bundle build-info.json at the _MEIPASS root; source
    # checkouts have build.ps1 write it at the PROJECT root.  Resolving to
    # this file's own directory (domain/) meant source runs never found it
    # and always fell back to FALLBACK_VERSION.
    base = Path(
        getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])
    )
    return base / "build-info.json"


def build_info() -> dict[str, str]:
    path = _build_info_path()
    try:
        exists = path.is_file()
    except OSError:
        exists = True
    if not exists:
        return {
            "version": FALLBACK_VERSION,
            "repository": PROJECT_REPOSITORY,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {
            "version": UNKNOWN_VERSION,
            "repository": PROJECT_REPOSITORY,
        }
    if not isinstance(payload, dict):
        return {
            "version": UNKNOWN_VERSION,
            "repository": PROJECT_REPOSITORY,
        }
    version = payload.get("version")
    return {
        "version": (
            version.strip()
            if isinstance(version, str) and version.strip()
            else UNKNOWN_VERSION
        ),
        "repository": str(
            payload.get("repository") or PROJECT_REPOSITORY
        ),
    }


APP_VERSION = build_info()["version"]
