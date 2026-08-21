from __future__ import annotations

lazy import hashlib
lazy import hmac
lazy import json
lazy import os
lazy import secrets
lazy import sqlite3
lazy import stat
lazy import threading
lazy import time
lazy from collections.abc import Callable, Iterator, Mapping
lazy from contextlib import suppress
lazy from dataclasses import dataclass
lazy from http import HTTPStatus
lazy from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
lazy from pathlib import Path
lazy from typing import Any, BinaryIO
lazy from urllib.parse import parse_qs, urlparse

lazy from domain.language_support import canonical_ui_language

StatusProvider = Callable[[], dict[str, Any]]
CommandHandler = Callable[[str, str], dict[str, Any]]
ScreenProvider = Callable[[], bytes]

MAX_PORT = 65_535
RATE_LIMIT_WINDOW_SECONDS = 60
MAX_REQUEST_BYTES = 16_384
MAX_COMMAND_TEXT_LENGTH = 2000

SAFE_DOWNLOAD_TYPES = frozendict({
    ".csv": "text/csv; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".json": "application/json",
    ".md": "text/markdown; charset=utf-8",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain; charset=utf-8",
    ".wav": "audio/wav",
    ".webp": "image/webp",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".zip": "application/zip",
})
PROTECTED_REMOTE_PARTS = frozenset({
    ".gnupg",
    ".ssh",
    "appdata",
    "credentials",
    "passwords",
})
PROTECTED_REMOTE_SUFFIXES = frozenset({".kdbx", ".key", ".pem", ".pfx"})
REMOTE_FILE_UNAVAILABLE_MESSAGES = frozendict({
    "zh-TW": "檔案目前無法提供",
    "zh-CN": "文件目前无法提供",
    "en-US": "The file is currently unavailable.",
    "ja-JP": "現在このファイルを提供できません。",
})
REMOTE_FILE_UNAVAILABLE = REMOTE_FILE_UNAVAILABLE_MESSAGES["zh-TW"]


def remote_file_unavailable(language: str) -> str:
    normalized = canonical_ui_language(language)
    key = "en-US" if normalized == "en" else normalized
    return REMOTE_FILE_UNAVAILABLE_MESSAGES[key]

MOBILE_PAGE = """<!doctype html>
<html lang="zh-Hant-TW"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>墨寒遠端</title>
<style>
body{font-family:system-ui;background:#0d1b28;color:#e8f5fb;margin:0;padding:20px}
main{max-width:680px;margin:auto}.card{background:#152a3a;border:1px solid #35566a;
border-radius:14px;padding:16px;margin:12px 0}input,button{box-sizing:border-box;
font:inherit;border-radius:10px;border:1px solid #467089;padding:12px}
input{width:100%;background:#102333;color:white;margin:6px 0}button{background:#28546b;
color:white;margin:6px 6px 6px 0}pre{white-space:pre-wrap;word-break:break-word}
</style><main><h1>墨寒遠端</h1>
<div class="card"><label>一次性配對權杖</label><input id="token" type="password"
autocomplete="off"><button onclick="save()">只保存於此瀏覽器</button></div>
<div class="card"><button onclick="status()">更新狀態</button>
<pre id="status">尚未連線</pre></div>
<div class="card"><label>傳給墨寒</label><input id="command" maxlength="2000"
placeholder="例如：顯示今天待辦"><button onclick="send()">送出指令</button>
<pre id="result"></pre></div>
<script>
const token=document.querySelector('#token'),out=document.querySelector('#status');
token.value=sessionStorage.getItem('mohanToken')||'';
function save(){sessionStorage.setItem('mohanToken',token.value);status()}
async function call(path,opt={}){opt.headers={...(opt.headers||{}),
'Authorization':'Bearer '+token.value,'Content-Type':'application/json'};
const r=await fetch(path,opt),j=await r.json();if(!r.ok)throw Error(j.error||r.status);return j}
async function status(){try{out.textContent=JSON.stringify(await call('/api/v1/status'),null,2)}
catch(e){out.textContent='連線失敗：'+e.message}}
async function send(){const text=document.querySelector('#command').value;
try{document.querySelector('#result').textContent=JSON.stringify(await call('/api/v1/command',
{method:'POST',body:JSON.stringify({text})}),null,2)}catch(e){
document.querySelector('#result').textContent='送出失敗：'+e.message}}
</script></main></html>"""


@dataclass(frozen=True, slots=True)
class RemoteServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    enabled: bool = False
    trusted_private_transport: bool = False
    allow_commands: bool = True
    allow_screen: bool = False
    allow_files: bool = False
    max_requests_per_minute: int = 60
    language: str = "zh-TW"


@dataclass(frozen=True, slots=True)
class RemoteServerServices:
    status_provider: StatusProvider
    command_handler: CommandHandler
    screen_provider: ScreenProvider | None = None
    allowed_folders: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RemoteDevice:
    id: int
    name: str
    permissions: frozenset[str]


class TokenRegistry:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def pair(
        self,
        device_name: str,
        permissions: list[str],
    ) -> str:
        token = secrets.token_urlsafe(32)
        self.db.add_paired_device(
            device_name.strip() or "未命名裝置",
            self.hash_token(token),
            permissions,
        )
        return token

    def authenticate(self, token: str) -> RemoteDevice | None:
        if not token:
            return None
        digest = self.hash_token(token)
        connection = sqlite3.connect(self.db.path, timeout=3.0)
        connection.row_factory = sqlite3.Row
        try:
            row = connection.execute(
                "SELECT * FROM paired_devices WHERE token_hash=?",
                (digest,),
            ).fetchone()
            if row is None or not bool(row["enabled"]):
                return None
            connection.execute(
                "UPDATE paired_devices SET last_seen_at=? WHERE id=?",
                (
                    time.strftime("%Y-%m-%dT%H:%M:%S"),
                    int(row["id"]),
                ),
            )
            connection.commit()
        finally:
            connection.close()
        try:
            permissions = json.loads(row["permissions"])
        except json.JSONDecodeError:
            permissions = []
        return RemoteDevice(
            id=int(row["id"]),
            name=str(row["device_name"]),
            permissions=frozenset(str(value) for value in permissions),
        )


class RemoteControlServer:
    """Opt-in private-network API. It never exposes desktop control by itself."""

    def __init__(
        self,
        config: RemoteServerConfig,
        tokens: TokenRegistry,
        services: RemoteServerServices,
    ):
        self.config = config
        self.tokens = tokens
        self.status_provider = services.status_provider
        self.command_handler = services.command_handler
        self.screen_provider = services.screen_provider
        self.allowed_folders = [
            Path(value).expanduser().resolve()
            for value in services.allowed_folders
            if str(value).strip()
        ]
        self._server: RemoteThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._rate: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._server is not None

    def _validate_start_config(self) -> None:
        if not self.config.enabled:
            raise PermissionError("遠端服務尚未由使用者啟用")
        if (
            self.config.host not in {"127.0.0.1", "::1", "localhost"}
            and not self.config.trusted_private_transport
        ):
            raise PermissionError(
                "非本機綁定必須先確認使用 Home Assistant Cloud、"
                "Tailscale 或其他可信任的加密私人網路"
            )
        if not 0 <= int(self.config.port) <= MAX_PORT:
            raise ValueError("遠端服務連接埠必須介於 0 與 65535")

    def start(self) -> None:
        self._validate_start_config()
        with self._lifecycle_lock:
            if self.running:
                return
            server = RemoteThreadingHTTPServer(
                (self.config.host, int(self.config.port)),
                self,
            )
            server.daemon_threads = True
            thread = threading.Thread(
                target=server.serve_forever,
                name="MoHanRemoteServer",
                daemon=True,
            )
            self._server = server
            self._thread = thread
            try:
                thread.start()
            except Exception:
                self._server = None
                self._thread = None
                server.server_close()
                raise

    def stop(self) -> None:
        with self._lifecycle_lock:
            server = self._server
            thread = self._thread
            self._server = None
            self._thread = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

    def _within_rate_limit(self, client_key: str) -> bool:
        digest = hashlib.sha256(client_key.encode("utf-8")).hexdigest()
        now = time.monotonic()
        with self._lock:
            recent = [stamp for stamp in self._rate.get(digest, []) if now - stamp < RATE_LIMIT_WINDOW_SECONDS]
            if len(recent) >= max(5, self.config.max_requests_per_minute):
                self._rate[digest] = recent
                return False
            recent.append(now)
            self._rate[digest] = recent
        return True

    def _allowed_file(self, raw: str) -> Path:
        requested_key = os.path.normcase(
            os.path.abspath(os.path.expanduser(raw))
        )
        for target in self._allowed_file_catalog():
            if os.path.normcase(str(target)) == requested_key:
                return target
        raise PermissionError("檔案不在遠端白名單或已受保護")

    def _allowed_file_catalog(self) -> Iterator[Path]:
        seen: set[str] = set()
        for root in self.allowed_folders:
            root_prefix = os.path.normcase(os.path.join(str(root), ""))
            for directory, folder_names, file_names in os.walk(
                root,
                followlinks=False,
            ):
                folder_names[:] = [
                    name
                    for name in folder_names
                    if name.casefold() not in PROTECTED_REMOTE_PARTS
                ]
                for file_name in file_names:
                    candidate = Path(directory, file_name)
                    try:
                        target = candidate.resolve(strict=True)
                    except (OSError, RuntimeError):
                        continue
                    target_key = os.path.normcase(str(target))
                    if not target_key.startswith(root_prefix) or target_key in seen:
                        continue
                    if not target.is_file() or self._is_sensitive_file(target):
                        continue
                    seen.add(target_key)
                    yield target

    @staticmethod
    def _is_sensitive_file(target: Path) -> bool:
        lowered = {part.casefold() for part in target.parts}
        return bool(
            lowered & PROTECTED_REMOTE_PARTS
            or target.suffix.casefold() in PROTECTED_REMOTE_SUFFIXES
        )

    @staticmethod
    def _download_metadata(target: Path) -> tuple[str, str]:
        suffix = target.suffix.casefold()
        content_type = SAFE_DOWNLOAD_TYPES.get(
            suffix,
            "application/octet-stream",
        )
        safe_suffix = suffix if suffix in SAFE_DOWNLOAD_TYPES else ".bin"
        digest = hashlib.sha256(target.name.encode("utf-8")).hexdigest()[:16]
        disposition = f'attachment; filename="mohan-{digest}{safe_suffix}"'
        return content_type, disposition


class RemoteThreadingHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        control: RemoteControlServer,
    ) -> None:
        self.control = control
        super().__init__(server_address, RemoteRequestHandler)


class RemoteRequestHandler(BaseHTTPRequestHandler):
    server: RemoteThreadingHTTPServer
    server_version = "MoHanRemote/2.0"

    @property
    def _owner(self) -> RemoteControlServer:
        return self.server.control

    def log_message(self, _format: str, *_args) -> None:
        return

    def _send_headers(
        self,
        status: int,
        content_length: int,
        content_type: str,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def _write_response(
        self,
        status: int,
        content: bytes,
        content_type: str,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        self._send_headers(
            status,
            len(content),
            content_type,
            extra_headers,
        )
        self.wfile.write(content)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")
        self._write_response(
            status,
            body,
            "application/json; charset=utf-8",
        )

    def _serve_mobile_page(self) -> None:
        self._write_response(
            HTTPStatus.OK,
            MOBILE_PAGE.encode("utf-8"),
            "text/html; charset=utf-8",
            {
                "Content-Security-Policy": (
                    "default-src 'self'; style-src 'unsafe-inline'; "
                    "script-src 'unsafe-inline'"
                ),
                "Referrer-Policy": "no-referrer",
            },
        )

    def _authorized_device(self) -> RemoteDevice | None:
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            self._json(
                HTTPStatus.UNAUTHORIZED,
                {"error": "未授權裝置"},
            )
            return None
        token = auth[7:].strip()
        client_ip = str(self.client_address[0])
        if not token:
            self._json(
                HTTPStatus.UNAUTHORIZED,
                {"error": "未授權裝置"},
            )
            return None
        if not self._owner._within_rate_limit(client_ip):
            self._json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"error": "請求過於頻繁"},
            )
            return None
        device = self._owner.tokens.authenticate(token)
        if device is None:
            self._json(
                HTTPStatus.UNAUTHORIZED,
                {"error": "未授權裝置"},
            )
        return device

    def _serve_status(self, device: RemoteDevice) -> None:
        if "status" not in device.permissions:
            self._json(
                HTTPStatus.FORBIDDEN,
                {"error": "缺少狀態權限"},
            )
        else:
            self._json(
                HTTPStatus.OK,
                self._owner.status_provider(),
            )

    def _serve_screen(self, device: RemoteDevice) -> None:
        owner = self._owner
        provider = owner.screen_provider
        if (
            not owner.config.allow_screen
            or "screen" not in device.permissions
            or provider is None
        ):
            self._json(
                HTTPStatus.FORBIDDEN,
                {"error": "畫面權限未啟用"},
            )
        else:
            self._write_response(
                HTTPStatus.OK,
                provider(),
                "image/png",
            )

    def _serve_file(
        self,
        device: RemoteDevice,
        query_string: str,
    ) -> None:
        owner = self._owner
        if (
            not owner.config.allow_files
            or "files" not in device.permissions
        ):
            self._json(
                HTTPStatus.FORBIDDEN,
                {"error": "檔案權限未啟用"},
            )
            return
        raw_path = parse_qs(query_string).get("path", [""])[0]
        stream: BinaryIO | None = None
        content_length = 0
        open_failed = False
        try:
            target = owner._allowed_file(raw_path)
            stream = target.open("rb")
            opened_file = os.fstat(stream.fileno())
            if stat.S_ISREG(opened_file.st_mode):
                content_length = opened_file.st_size
            else:
                open_failed = True
        except (OSError, RuntimeError, ValueError):
            open_failed = True

        if open_failed or stream is None:
            if stream is not None:
                with suppress(OSError):
                    stream.close()
            self._json(
                HTTPStatus.FORBIDDEN,
                {"error": remote_file_unavailable(owner.config.language)},
            )
            return

        content_type, disposition = owner._download_metadata(target)
        try:
            with stream:
                self._send_headers(
                    HTTPStatus.OK,
                    content_length,
                    content_type,
                    {"Content-Disposition": disposition},
                )
                remaining = content_length
                while remaining and (
                    chunk := stream.read(min(64 * 1024, remaining))
                ):
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (OSError, RuntimeError, ValueError):
            # Headers may already be committed. Close the truncated response
            # without exposing the local I/O failure through a server traceback.
            self.close_connection = True

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._serve_mobile_page()
            return
        device = self._authorized_device()
        if device is None:
            return
        if parsed.path == "/api/v1/status":
            self._serve_status(device)
        elif parsed.path == "/api/v1/screen":
            self._serve_screen(device)
        elif parsed.path == "/api/v1/file":
            self._serve_file(device, parsed.query)
        else:
            self._json(
                HTTPStatus.NOT_FOUND,
                {"error": "找不到端點"},
            )

    def _read_command_text(self) -> str | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if not 0 < length <= MAX_REQUEST_BYTES:
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"error": "請求大小不正確"},
            )
            return None
        try:
            payload = json.loads(
                self.rfile.read(length).decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"error": "JSON 格式錯誤"},
            )
            return None
        if not isinstance(payload, dict):
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"error": "JSON 格式錯誤"},
            )
            return None
        text = str(payload.get("text", "")).strip()
        if not text or len(text) > MAX_COMMAND_TEXT_LENGTH:
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"error": "指令文字不正確"},
            )
            return None
        return text

    def do_POST(self) -> None:
        device = self._authorized_device()
        if device is None:
            return
        if self.path != "/api/v1/command":
            self._json(
                HTTPStatus.NOT_FOUND,
                {"error": "找不到端點"},
            )
            return
        if (
            not self._owner.config.allow_commands
            or "commands" not in device.permissions
        ):
            self._json(
                HTTPStatus.FORBIDDEN,
                {"error": "指令權限未啟用"},
            )
            return
        text = self._read_command_text()
        if text is None:
            return
        result = self._owner.command_handler(text, device.name)
        self._json(HTTPStatus.ACCEPTED, result)


def constant_time_token_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(left.encode("utf-8")).digest(),
        hashlib.sha256(right.encode("utf-8")).digest(),
    )
