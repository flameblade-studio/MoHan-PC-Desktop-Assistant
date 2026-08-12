from __future__ import annotations

lazy import base64
lazy import hashlib
lazy import json
lazy import re
lazy import secrets
lazy import threading
lazy import time
lazy import webbrowser
lazy from dataclasses import dataclass
lazy from http.server import BaseHTTPRequestHandler, HTTPServer
lazy from typing import Any
lazy from urllib.error import HTTPError, URLError
lazy from urllib.parse import parse_qs, quote, urlencode, urlparse
lazy from urllib.request import Request, urlopen

lazy from flagship_core import sanitize_external_content
lazy from safe_error import sanitize_error


@dataclass(frozen=True, slots=True)
class OAuthProvider:
    provider_id: str
    display_name: str
    authorization_endpoint: str
    token_endpoint: str
    default_scopes: tuple[str, ...]


PROVIDERS = frozendict({
    "google": OAuthProvider(
        "google",
        "Google（Gmail／Calendar／Drive）",
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
        (
            "openid",
            "email",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.metadata.readonly",
        ),
    ),
    "microsoft": OAuthProvider(
        "microsoft",
        "Microsoft（Outlook／Calendar／OneDrive）",
        "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        (
            "openid",
            "offline_access",
            "User.Read",
            "Mail.ReadWrite",
            "Mail.Send",
            "Calendars.ReadWrite",
            "Files.ReadWrite",
        ),
    ),
    "github": OAuthProvider(
        "github",
        "GitHub",
        "https://github.com/login/oauth/authorize",
        "https://github.com/login/oauth/access_token",
        ("read:user", "repo"),
    ),
})

_CLOUD_PROVIDER_ALIASES: dict[str, str] = {}


def register_cloud_provider_alias(provider: str, *aliases: str) -> None:
    """Allow future service adapters to join a provider without UI rewrites."""
    provider_id = provider.casefold().strip()
    if provider_id not in PROVIDERS:
        raise ValueError(f"未知的雲端供應商：{provider}")
    for alias in (provider_id, *aliases):
        compact = re.sub(r"[\s_.\-/]+", "", alias.casefold().strip())
        if compact:
            _CLOUD_PROVIDER_ALIASES[compact] = provider_id


register_cloud_provider_alias(
    "google",
    "gmail",
    "google calendar",
    "google drive",
    "gdrive",
    "youtube",
    "youtube studio",
    "google sheets",
    "google docs",
    "google tasks",
    "google contacts",
    "google photos",
    "google play books",
)
register_cloud_provider_alias(
    "microsoft",
    "microsoft graph",
    "outlook",
    "outlook calendar",
    "onedrive",
    "sharepoint",
    "teams",
)
register_cloud_provider_alias("github")


def normalize_cloud_provider(value: str, description: str = "") -> str:
    raw = str(value).casefold().strip()
    compact = re.sub(r"[\s_.\-/]+", "", raw)
    provider = _CLOUD_PROVIDER_ALIASES.get(compact, "")
    if provider:
        return provider

    # Future adapters commonly name services "google_xxx" or describe them as
    # Google services. Accept the provider family without enumerating every API.
    if compact.startswith("google"):
        return "google"
    if compact.startswith("microsoft"):
        return "microsoft"

    folded_description = str(description).casefold()
    description_compact = re.sub(
        r"[\s_.\-/]+",
        "",
        folded_description,
    )
    for alias, provider_id in _CLOUD_PROVIDER_ALIASES.items():
        if alias and alias in description_compact:
            return provider_id
    return ""


class OAuthError(RuntimeError):
    pass


def _sanitized_external_error(
    error: BaseException | str,
    *,
    http_status: int | None = None,
) -> str:
    """Discard provider detail before an error crosses the cloud boundary."""
    safe_input = UnicodeError() if isinstance(error, json.JSONDecodeError) else error
    return str(sanitize_error(safe_input, http_status=http_status))


def _callback_handler(
    received: dict[str, str],
    ready: threading.Event,
) -> type[BaseHTTPRequestHandler]:
    class Callback(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args) -> None:
            return

        def do_GET(self) -> None:
            query = parse_qs(urlparse(self.path).query)
            for key in ("code", "state", "error", "error_description"):
                if query.get(key):
                    received[key] = query[key][0]
            body = (
                "墨寒已收到授權結果，可以關閉此頁。"
                if "code" in received
                else "授權未完成，可以關閉此頁。"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            ready.set()

    return Callback


def _wait_for_callback(
    server: HTTPServer,
    ready: threading.Event,
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    try:
        while not ready.is_set() and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()


def _authorization_code(received: dict[str, str], expected_state: str) -> str:
    if received.get("state") != expected_state:
        raise OAuthError("OAuth state 驗證失敗")
    if received.get("error"):
        detail = received.get("error_description") or received["error"]
        raise OAuthError(_sanitized_external_error(detail))
    code = received.get("code")
    if not code:
        raise OAuthError("授權服務未傳回授權碼")
    return code


class OAuthPKCEFlow:
    def __init__(
        self,
        provider: OAuthProvider,
        client_id: str,
        *,
        client_secret: str = "",
        scopes: list[str] | None = None,
        timeout_seconds: float = 180.0,
    ):
        self.provider = provider
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.scopes = scopes or list(provider.default_scopes)
        self.timeout_seconds = timeout_seconds
        if not self.client_id:
            raise ValueError("OAuth Client ID 不可留空")

    def authorize(self) -> dict[str, Any]:
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        state = secrets.token_urlsafe(24)
        received: dict[str, str] = {}
        ready = threading.Event()
        server = HTTPServer(
            ("127.0.0.1", 0),
            _callback_handler(received, ready),
        )
        server.timeout = 0.5
        redirect_uri = f"http://127.0.0.1:{server.server_port}/oauth/callback"
        parameters = self._authorization_parameters(
            redirect_uri,
            state,
            challenge,
        )
        webbrowser.open(
            self.provider.authorization_endpoint
            + "?"
            + urlencode(parameters),
            new=2,
        )
        _wait_for_callback(server, ready, self.timeout_seconds)
        if not ready.is_set():
            raise OAuthError("等待瀏覽器授權逾時")
        code = _authorization_code(received, state)
        return self._exchange(code, verifier, redirect_uri)

    def _authorization_parameters(
        self,
        redirect_uri: str,
        state: str,
        challenge: str,
    ) -> dict[str, str]:
        parameters = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        if self.provider.provider_id == "google":
            parameters.update(
                {
                    "access_type": "offline",
                    "prompt": "consent",
                }
            )
        return parameters

    def _exchange(
        self,
        code: str,
        verifier: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        payload = {
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
        if self.client_secret:
            payload["client_secret"] = self.client_secret
        exchange_failure: str | None = None
        try:
            request = Request(
                self.provider.token_endpoint,
                data=urlencode(payload).encode("ascii"),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            )
            with urlopen(request, timeout=30) as response:
                token = json.load(response)
        except (
            HTTPError,
            URLError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as exc:
            exchange_failure = _sanitized_external_error(exc)
        if exchange_failure is not None:
            raise OAuthError(exchange_failure)

        if not isinstance(token, dict) or not token.get("access_token"):
            raise OAuthError("授權服務未傳回存取權杖")
        token["obtained_at"] = int(time.time())
        token["provider"] = self.provider.provider_id
        token["client_id"] = self.client_id
        return token


def refresh_oauth_token(
    provider: OAuthProvider,
    token: dict[str, Any],
) -> dict[str, Any]:
    refresh_token = str(token.get("refresh_token", ""))
    client_id = str(token.get("client_id", ""))
    if not refresh_token or not client_id:
        raise OAuthError("此授權沒有可用的更新權杖，請重新連線")
    payload = {
        "client_id": client_id,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    client_secret = str(token.get("client_secret", ""))
    if client_secret:
        payload["client_secret"] = client_secret
    refresh_failure: str | None = None
    try:
        request = Request(
            provider.token_endpoint,
            data=urlencode(payload).encode("ascii"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            updated = json.load(response)
    except (HTTPError, URLError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        refresh_failure = _sanitized_external_error(exc)
    if refresh_failure is not None:
        raise OAuthError(refresh_failure)

    if not isinstance(updated, dict) or not updated.get("access_token"):
        raise OAuthError("服務商未傳回新的存取權杖")
    merged = dict(token)
    merged.update(updated)
    merged["obtained_at"] = int(time.time())
    return merged


class JsonApiClient:
    def __init__(self, token: str, base_url: str):
        self.token = token
        self.base_url = base_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        query: dict[str, Any] | None = None,
    ) -> Any:
        url = self.base_url + path
        if query:
            url += "?" + urlencode(query)
        data = (
            json.dumps(payload).encode("utf-8")
            if payload is not None
            else None
        )
        request_failure: str | None = None
        try:
            request = Request(
                url,
                data=data,
                method=method,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "MoHan-Desktop-Assistant/2.0",
                },
            )
            with urlopen(request, timeout=30) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except (
            HTTPError,
            URLError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as exc:
            request_failure = _sanitized_external_error(exc)
        raise OAuthError(request_failure)

    def request_bytes(
        self,
        method: str,
        path: str,
        content: bytes,
        content_type: str,
    ) -> Any:
        request_failure: str | None = None
        try:
            request = Request(
                self.base_url + path,
                data=content,
                method=method,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/json",
                    "Content-Type": content_type,
                    "User-Agent": "MoHan-Desktop-Assistant/2.0",
                },
            )
            with urlopen(request, timeout=45) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except (
            HTTPError,
            URLError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as exc:
            request_failure = _sanitized_external_error(exc)
        raise OAuthError(request_failure)


class GmailConnector(JsonApiClient):
    def __init__(self, token: str):
        super().__init__(token, "https://gmail.googleapis.com/gmail/v1/users/me")

    def search(self, query: str, max_results: int = 20) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            "/messages",
            query={"q": query, "maxResults": max(1, min(100, max_results))},
        )
        return list(result.get("messages", [])) if isinstance(result, dict) else []

    def message(self, message_id: str) -> dict[str, Any]:
        result = self.request(
            "GET",
            f"/messages/{quote(message_id)}",
            query={"format": "full"},
        )
        if not isinstance(result, dict):
            raise OAuthError("Gmail 郵件格式錯誤")
        snippet = result.get("snippet")
        if isinstance(snippet, str):
            result["snippet"] = sanitize_external_content(snippet)
        return result

    def create_draft(self, raw_rfc822: bytes) -> dict[str, Any]:
        encoded = base64.urlsafe_b64encode(raw_rfc822).decode("ascii").rstrip("=")
        result = self.request(
            "POST",
            "/drafts",
            {"message": {"raw": encoded}},
        )
        if not isinstance(result, dict):
            raise OAuthError("Gmail 草稿建立失敗")
        return result

    def send_draft(self, draft_id: str) -> dict[str, Any]:
        result = self.request("POST", "/drafts/send", {"id": draft_id})
        if not isinstance(result, dict):
            raise OAuthError("Gmail 寄送失敗")
        return result


class GoogleCalendarConnector(JsonApiClient):
    def __init__(self, token: str):
        super().__init__(token, "https://www.googleapis.com/calendar/v3")

    def events(
        self,
        calendar_id: str = "primary",
        *,
        time_min: str,
        time_max: str,
    ) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            f"/calendars/{quote(calendar_id, safe='')}/events",
            query={
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": "true",
                "orderBy": "startTime",
            },
        )
        return list(result.get("items", [])) if isinstance(result, dict) else []

    def create_event(
        self,
        event: dict[str, Any],
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        result = self.request(
            "POST",
            f"/calendars/{quote(calendar_id, safe='')}/events",
            event,
        )
        if not isinstance(result, dict):
            raise OAuthError("Google Calendar 建立事件失敗")
        return result


class GoogleDriveConnector(JsonApiClient):
    def __init__(self, token: str):
        super().__init__(token, "https://www.googleapis.com/drive/v3")

    def search(self, name: str, page_size: int = 30) -> list[dict[str, Any]]:
        escaped = name.replace("\\", "\\\\").replace("'", "\\'")
        result = self.request(
            "GET",
            "/files",
            query={
                "q": f"name contains '{escaped}' and trashed=false",
                "pageSize": max(1, min(100, page_size)),
                "fields": "files(id,name,mimeType,modifiedTime,webViewLink,size)",
            },
        )
        return list(result.get("files", [])) if isinstance(result, dict) else []

    def recent(self, page_size: int = 20) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            "/files",
            query={
                "q": "trashed=false",
                "pageSize": max(1, min(100, page_size)),
                "orderBy": "modifiedTime desc",
                "fields": "files(id,name,mimeType,modifiedTime,webViewLink,size)",
            },
        )
        return list(result.get("files", [])) if isinstance(result, dict) else []

    def upload_small(
        self,
        filename: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        if len(content) > 5 * 1024 * 1024:
            raise ValueError("安全簡易上傳上限為 5 MB")
        boundary = "mohan-" + secrets.token_hex(12)
        metadata = json.dumps({"name": filename}, ensure_ascii=False).encode("utf-8")
        body = (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode()
            + metadata
            + f"\r\n--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n".encode()
            + content
            + f"\r\n--{boundary}--\r\n".encode()
        )
        upload_failure: str | None = None
        try:
            request = Request(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/json",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
            )
            with urlopen(request, timeout=45) as response:
                result = json.load(response)
        except (
            HTTPError,
            URLError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as exc:
            upload_failure = _sanitized_external_error(exc)
        if upload_failure is not None:
            raise OAuthError(upload_failure)

        if not isinstance(result, dict):
            raise OAuthError("Google Drive 上傳回應格式錯誤")
        return result


class MicrosoftGraphConnector(JsonApiClient):
    def __init__(self, token: str):
        super().__init__(token, "https://graph.microsoft.com/v1.0")

    def messages(self, top: int = 20) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            "/me/messages",
            query={"$top": max(1, min(100, top)), "$select": "id,subject,from,receivedDateTime,bodyPreview"},
        )
        rows = list(result.get("value", [])) if isinstance(result, dict) else []
        for row in rows:
            if isinstance(row.get("bodyPreview"), str):
                row["bodyPreview"] = sanitize_external_content(row["bodyPreview"])
        return rows

    def create_message_draft(self, message: dict[str, Any]) -> dict[str, Any]:
        result = self.request("POST", "/me/messages", message)
        if not isinstance(result, dict):
            raise OAuthError("Outlook 草稿建立失敗")
        return result

    def send_message(self, message: dict[str, Any]) -> None:
        self.request("POST", "/me/sendMail", {"message": message, "saveToSentItems": True})

    def calendar_events(self, start: str, end: str) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            "/me/calendarView",
            query={"startDateTime": start, "endDateTime": end},
        )
        return list(result.get("value", [])) if isinstance(result, dict) else []

    def create_event(self, event: dict[str, Any]) -> dict[str, Any]:
        result = self.request("POST", "/me/events", event)
        if not isinstance(result, dict):
            raise OAuthError("Outlook Calendar 建立事件失敗")
        return result

    def search_drive(self, name: str) -> list[dict[str, Any]]:
        encoded = quote(name.replace("'", "''"), safe="")
        result = self.request(
            "GET",
            f"/me/drive/root/search(q='{encoded}')",
        )
        return list(result.get("value", [])) if isinstance(result, dict) else []

    def upload_small(
        self,
        filename: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        if len(content) > 4 * 1024 * 1024:
            raise ValueError("OneDrive 簡易上傳上限為 4 MB")
        safe_name = quote(filename, safe="")
        result = self.request_bytes(
            "PUT",
            f"/me/drive/root:/{safe_name}:/content",
            content,
            mime_type,
        )
        if not isinstance(result, dict):
            raise OAuthError("OneDrive 上傳回應格式錯誤")
        return result


class GitHubConnector(JsonApiClient):
    def __init__(self, token: str):
        super().__init__(token, "https://api.github.com")

    def viewer(self) -> dict[str, Any]:
        result = self.request("GET", "/user")
        if not isinstance(result, dict):
            raise OAuthError("GitHub 使用者資料格式錯誤")
        return result

    def repositories(self, per_page: int = 30) -> list[dict[str, Any]]:
        result = self.request(
            "GET",
            "/user/repos",
            query={
                "per_page": max(1, min(100, per_page)),
                "sort": "updated",
            },
        )
        return list(result) if isinstance(result, list) else []
