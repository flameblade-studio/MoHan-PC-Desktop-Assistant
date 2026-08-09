from __future__ import annotations

lazy import json
lazy import sys
lazy import time
lazy from collections.abc import Callable
lazy from concurrent.futures import Future, ThreadPoolExecutor, as_completed
lazy from functools import partial
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from cloud_connectors import (
    GmailConnector,
    GoogleCalendarConnector,
    GoogleDriveConnector,
    normalize_cloud_provider,
)
lazy from flagship_ui import FlagshipControlCenter
lazy from secret_store import SecretStore

Probe = Callable[[], None]


def _load_access_token(data_path_text: str) -> tuple[str | None, int]:
    data_path = Path(data_path_text).resolve()
    raw = SecretStore(data_path / "oauth-google.dpapi").load()
    if not raw:
        print("OAUTH=unavailable")
        return None, 2
    token_payload = json.loads(raw)
    token = str(token_payload.get("access_token", "")).strip()
    if not token:
        print("OAUTH=incomplete")
        return None, 3
    print("OAUTH=available")
    return token, 0


def _probe_gmail(token: str) -> None:
    GmailConnector(token).request("GET", "/profile")


def _probe_calendar(token: str) -> None:
    GoogleCalendarConnector(token).request(
        "GET",
        "/calendars/primary/events",
        query={
            "maxResults": 1,
            "singleEvents": "true",
            "timeMin": "2020-01-01T00:00:00+00:00",
        },
    )


def _probe_drive(token: str) -> None:
    GoogleDriveConnector(token).request(
        "GET",
        "/files",
        query={
            "pageSize": 1,
            "fields": "files(id)",
            "q": "trashed=false",
        },
    )


def _probe_calendar_legacy_arguments(token: str) -> None:
    provider = normalize_cloud_provider(
        "google_calendar",
        "讀取今天到明天的 Google Calendar 行程",
    )
    if provider != "google":
        raise RuntimeError("provider normalization failed")
    start, end = FlagshipControlCenter._calendar_read_bounds(
        {"range": "today_to_tomorrow", "source": "google_calendar"}
    )
    GoogleCalendarConnector(token).events(time_min=start, time_max=end)


def _probe_drive_legacy_arguments(token: str) -> None:
    provider = normalize_cloud_provider("", "在 Google Drive 中搜尋檔名")
    if provider != "google":
        raise RuntimeError("provider normalization failed")
    arguments = {"query": "墨寒", "search_scope": "name_only"}
    name = str(
        arguments.get("name")
        or arguments.get("query")
        or arguments.get("search_term")
        or arguments.get("filename")
        or ""
    ).strip()
    GoogleDriveConnector(token).search(name, 20)


def _probes(token: str) -> dict[str, Probe]:
    return {
        "Gmail": partial(_probe_gmail, token),
        "Calendar": partial(_probe_calendar, token),
        "Drive": partial(_probe_drive, token),
        "CalendarLegacyArgs": partial(
            _probe_calendar_legacy_arguments,
            token,
        ),
        "DriveLegacyArgs": partial(_probe_drive_legacy_arguments, token),
    }


def _report_probe(name: str, began: float, future: Future[None]) -> bool:
    elapsed = time.monotonic() - began
    try:
        future.result()
        print(f"{name}=ok,elapsed={elapsed:.2f}s")
        return True
    except Exception as exc:  # noqa: BLE001 -- diagnostic must report each probe
        print(
            f"{name}=failed,elapsed={elapsed:.2f}s,"
            f"error={type(exc).__name__}:{exc}"
        )
        return False


def _run_probes(probes: dict[str, Probe]) -> int:
    with ThreadPoolExecutor(max_workers=3) as pool:
        started = {
            pool.submit(probe): (name, time.monotonic())
            for name, probe in probes.items()
        }
        return sum(
            not _report_probe(*started[future], future)
            for future in as_completed(started)
        )


def main(data_path_text: str) -> int:
    token, status = _load_access_token(data_path_text)
    if token is None:
        return status
    return 0 if _run_probes(_probes(token)) == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
