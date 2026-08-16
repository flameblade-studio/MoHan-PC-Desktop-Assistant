from __future__ import annotations

lazy from typing import Any

lazy from PySide6.QtCore import QObject, QRunnable, Signal

from domain.python315_concurrency import ThreadPoolExecutor, as_completed
lazy from domain.safe_error_localization import safe_error_message
lazy from domain.time_utils import local_aware_time
lazy from integrations.cloud_connectors import (
    PROVIDERS,
    GitHubConnector,
    GmailConnector,
    GoogleCalendarConnector,
    GoogleDriveConnector,
    MicrosoftGraphConnector,
)
lazy from presentation.flagship_ui_localization import FlagshipTranslator

__all__ = ("CloudHealthSignals", "CloudHealthWorker")


class CloudHealthSignals(QObject):
    done = Signal(str, object)


class CloudHealthWorker(QRunnable):
    """Probe cloud services concurrently so a slow API cannot freeze the UI."""

    def __init__(
        self,
        provider_id: str,
        token: str,
        language: str = "zh-TW",
    ):
        super().__init__()
        self.provider_id = provider_id
        self.token = token
        self._translator = FlagshipTranslator(language)
        self.signals = CloudHealthSignals()

    def _google_probes(self) -> dict[str, Any]:
        def gmail() -> str:
            payload = GmailConnector(self.token).request("GET", "/profile")
            return str(
                payload.get(
                    "emailAddress",
                    self._translator.text("Google 帳戶"),
                )
            )

        def calendar() -> str:
            GoogleCalendarConnector(self.token).request(
                "GET",
                "/calendars/primary/events",
                query={
                    "maxResults": 1,
                    "singleEvents": "true",
                    "timeMin": local_aware_time().isoformat(),
                },
            )
            return self._translator.text("主要日曆可讀取")

        def drive() -> str:
            GoogleDriveConnector(self.token).request(
                "GET",
                "/files",
                query={
                    "pageSize": 1,
                    "fields": "files(id,name)",
                    "q": "trashed=false",
                },
            )
            return self._translator.text("雲端硬碟中繼資料可讀取")

        probes = {"Gmail": gmail, "Calendar": calendar, "Drive": drive}
        results: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(probe): name for name, probe in probes.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = {"ok": True, "detail": future.result()}
                except Exception as exc:  # noqa: BLE001 -- isolate each health probe
                    results[name] = {
                        "ok": False,
                        "detail": safe_error_message(
                            self._translator.language,
                            exc,
                        ),
                    }
        return results

    def run(self) -> None:
        if self.provider_id == "google":
            results = self._google_probes()
        else:
            try:
                if self.provider_id == "microsoft":
                    payload = MicrosoftGraphConnector(self.token).request(
                        "GET",
                        "/me",
                    )
                    identity = payload.get(
                        "displayName",
                        self._translator.text("Microsoft 帳戶"),
                    )
                else:
                    payload = GitHubConnector(self.token).viewer()
                    identity = payload.get(
                        "login",
                        self._translator.text("GitHub 帳戶"),
                    )
                results = {
                    PROVIDERS[self.provider_id].display_name: {
                        "ok": True,
                        "detail": str(identity),
                    }
                }
            except Exception as exc:  # noqa: BLE001 -- cloud probe returns diagnostics
                results = {
                    PROVIDERS[self.provider_id].display_name: {
                        "ok": False,
                        "detail": safe_error_message(
                            self._translator.language,
                            exc,
                        ),
                    }
                }
        self.signals.done.emit(self.provider_id, results)
