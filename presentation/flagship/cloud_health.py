from __future__ import annotations

lazy from typing import Any

lazy from PySide6.QtCore import QObject, QRunnable, Signal

from domain.python315_concurrency import ThreadPoolExecutor, as_completed
lazy from domain.safe_error_localization import safe_error_message
lazy from domain.time_utils import local_aware_time
lazy from integrations.cloud_connectors import (
    OAuthError,
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
            # 缺少 emailAddress 時先前退回泛用名稱「Google 帳戶」並報 ok=True，
            # 於是無法分辨「連上了但拿不到身份」與「真的連上了」。
            address = str(payload.get("emailAddress", "")).strip() if isinstance(
                payload, dict
            ) else ""
            if not address:
                raise OAuthError("Gmail 回應缺少帳戶識別，無法確認連線")
            return address

        def calendar() -> str:
            # 先前完全不看 payload：任何 2xx JSON 都被報成「已連線」，包含
            # 代理層或中間設備回的空物件。健康檢查的用途正是分辨「真的通了」
            # 與「看起來像通了」，它自己不能只看狀態碼。
            payload = GoogleCalendarConnector(self.token).request(
                "GET",
                "/calendars/primary/events",
                query={
                    "maxResults": 1,
                    "singleEvents": "true",
                    "timeMin": local_aware_time().isoformat(),
                },
            )
            if not isinstance(payload, dict) or "items" not in payload:
                raise OAuthError("Google Calendar 回應缺少 items 欄位，無法確認連線")
            return self._translator.text("主要日曆可讀取")

        def drive() -> str:
            payload = GoogleDriveConnector(self.token).request(
                "GET",
                "/files",
                query={
                    "pageSize": 1,
                    "fields": "files(id,name)",
                    "q": "trashed=false",
                },
            )
            if not isinstance(payload, dict) or "files" not in payload:
                raise OAuthError("Google Drive 回應缺少 files 欄位，無法確認連線")
            return self._translator.text("雲端硬碟中繼資料可讀取")

        probes = {"Gmail": gmail, "Calendar": calendar, "Drive": drive}
        results: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(probe): name for name, probe in probes.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = {"ok": True, "detail": future.result()}
                except Exception as exc:
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
            except Exception as exc:
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
