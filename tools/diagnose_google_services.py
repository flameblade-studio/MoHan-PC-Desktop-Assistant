from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cloud_connectors import (
    GmailConnector,
    GoogleCalendarConnector,
    GoogleDriveConnector,
    normalize_cloud_provider,
)
from flagship_ui import FlagshipControlCenter
from secret_store import SecretStore


def main(data_path_text: str) -> int:
    data_path = Path(data_path_text).resolve()
    raw = SecretStore(data_path / "oauth-google.dpapi").load()
    if not raw:
        print("OAUTH=unavailable")
        return 2
    token_payload = json.loads(raw)
    token = str(token_payload.get("access_token", "")).strip()
    if not token:
        print("OAUTH=incomplete")
        return 3
    print("OAUTH=available")

    def gmail() -> None:
        GmailConnector(token).request("GET", "/profile")

    def calendar() -> None:
        GoogleCalendarConnector(token).request(
            "GET",
            "/calendars/primary/events",
            query={
                "maxResults": 1,
                "singleEvents": "true",
                "timeMin": "2020-01-01T00:00:00+00:00",
            },
        )

    def drive() -> None:
        GoogleDriveConnector(token).request(
            "GET",
            "/files",
            query={
                "pageSize": 1,
                "fields": "files(id)",
                "q": "trashed=false",
            },
        )

    def calendar_legacy_arguments() -> None:
        provider = normalize_cloud_provider(
            "google_calendar",
            "讀取今天到明天的 Google Calendar 行程",
        )
        if provider != "google":
            raise RuntimeError("provider normalization failed")
        start, end = FlagshipControlCenter._calendar_read_bounds(
            {"range": "today_to_tomorrow", "source": "google_calendar"}
        )
        GoogleCalendarConnector(token).events(
            time_min=start,
            time_max=end,
        )

    def drive_legacy_arguments() -> None:
        provider = normalize_cloud_provider(
            "",
            "在 Google Drive 中搜尋檔名",
        )
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

    probes = {
        "Gmail": gmail,
        "Calendar": calendar,
        "Drive": drive,
        "CalendarLegacyArgs": calendar_legacy_arguments,
        "DriveLegacyArgs": drive_legacy_arguments,
    }
    failures = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        started = {
            pool.submit(probe): (name, time.monotonic())
            for name, probe in probes.items()
        }
        for future in as_completed(started):
            name, began = started[future]
            elapsed = time.monotonic() - began
            try:
                future.result()
                print(f"{name}=ok,elapsed={elapsed:.2f}s")
            except Exception as exc:
                failures += 1
                print(
                    f"{name}=failed,elapsed={elapsed:.2f}s,"
                    f"error={type(exc).__name__}:{exc}"
                )
    return 0 if failures == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
