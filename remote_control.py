from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import sqlite3
import threading
import time
import urllib.parse
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable


StatusProvider = Callable[[], dict[str, Any]]
CommandHandler = Callable[[str, str], dict[str, Any]]
ScreenProvider = Callable[[], bytes]

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


@dataclass(slots=True)
class RemoteServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    enabled: bool = False
    trusted_private_transport: bool = False
    allow_commands: bool = True
    allow_screen: bool = False
    allow_files: bool = False
    max_requests_per_minute: int = 60


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

    def authenticate(self, token: str) -> dict[str, Any] | None:
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
        return {
            "id": int(row["id"]),
            "name": str(row["device_name"]),
            "permissions": set(str(value) for value in permissions),
        }


class RemoteControlServer:
    """Opt-in private-network API. It never exposes desktop control by itself."""

    def __init__(
        self,
        config: RemoteServerConfig,
        tokens: TokenRegistry,
        *,
        status_provider: StatusProvider,
        command_handler: CommandHandler,
        screen_provider: ScreenProvider | None = None,
        allowed_folders: list[str] | None = None,
    ):
        self.config = config
        self.tokens = tokens
        self.status_provider = status_provider
        self.command_handler = command_handler
        self.screen_provider = screen_provider
        self.allowed_folders = [
            Path(value).expanduser().resolve()
            for value in (allowed_folders or [])
            if str(value).strip()
        ]
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._rate: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._server is not None

    def start(self) -> None:
        if not self.config.enabled:
            raise PermissionError("遠端服務尚未由使用者啟用")
        if self.config.host not in {"127.0.0.1", "::1", "localhost"}:
            if not self.config.trusted_private_transport:
                raise PermissionError(
                    "非本機綁定必須先確認使用 Home Assistant Cloud、"
                    "Tailscale 或其他可信任的加密私人網路"
                )
        if self.running:
            return
        owner = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "MoHanRemote/2.0"

            def log_message(self, _format: str, *_args) -> None:
                return

            def _json(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(body)

            def _device(self) -> dict[str, Any] | None:
                auth = self.headers.get("Authorization", "")
                if not auth.startswith("Bearer "):
                    return None
                token = auth[7:].strip()
                if not owner._within_rate_limit(token):
                    self._json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "請求過於頻繁"})
                    return None
                return owner.tokens.authenticate(token)

            def do_GET(self) -> None:  # noqa: N802
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path in {"/", "/index.html"}:
                    body = MOBILE_PAGE.encode("utf-8")
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Security-Policy", "default-src 'self'; "
                                     "style-src 'unsafe-inline'; script-src 'unsafe-inline'")
                    self.send_header("X-Frame-Options", "DENY")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                device = self._device()
                if device is None:
                    if not self.wfile.closed:
                        self._json(HTTPStatus.UNAUTHORIZED, {"error": "未授權裝置"})
                    return
                if parsed.path == "/api/v1/status":
                    if "status" not in device["permissions"]:
                        self._json(HTTPStatus.FORBIDDEN, {"error": "缺少狀態權限"})
                        return
                    self._json(HTTPStatus.OK, owner.status_provider())
                    return
                if parsed.path == "/api/v1/screen":
                    if (
                        not owner.config.allow_screen
                        or "screen" not in device["permissions"]
                        or owner.screen_provider is None
                    ):
                        self._json(HTTPStatus.FORBIDDEN, {"error": "畫面權限未啟用"})
                        return
                    content = owner.screen_provider()
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(content)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(content)
                    return
                if parsed.path == "/api/v1/file":
                    if (
                        not owner.config.allow_files
                        or "files" not in device["permissions"]
                    ):
                        self._json(HTTPStatus.FORBIDDEN, {"error": "檔案權限未啟用"})
                        return
                    query = urllib.parse.parse_qs(parsed.query)
                    raw = query.get("path", [""])[0]
                    try:
                        target = owner._allowed_file(raw)
                    except (PermissionError, FileNotFoundError) as exc:
                        self._json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
                        return
                    content = target.read_bytes()
                    self.send_response(HTTPStatus.OK)
                    self.send_header(
                        "Content-Type",
                        mimetypes.guess_type(target.name)[0]
                        or "application/octet-stream",
                    )
                    self.send_header("Content-Length", str(len(content)))
                    self.send_header(
                        "Content-Disposition",
                        f'attachment; filename="{target.name}"',
                    )
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(content)
                    return
                self._json(HTTPStatus.NOT_FOUND, {"error": "找不到端點"})

            def do_POST(self) -> None:  # noqa: N802
                device = self._device()
                if device is None:
                    if not self.wfile.closed:
                        self._json(HTTPStatus.UNAUTHORIZED, {"error": "未授權裝置"})
                    return
                if self.path != "/api/v1/command":
                    self._json(HTTPStatus.NOT_FOUND, {"error": "找不到端點"})
                    return
                if (
                    not owner.config.allow_commands
                    or "commands" not in device["permissions"]
                ):
                    self._json(HTTPStatus.FORBIDDEN, {"error": "指令權限未啟用"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    length = 0
                if length <= 0 or length > 16_384:
                    self._json(HTTPStatus.BAD_REQUEST, {"error": "請求大小不正確"})
                    return
                try:
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._json(HTTPStatus.BAD_REQUEST, {"error": "JSON 格式錯誤"})
                    return
                text = str(payload.get("text", "")).strip()
                if not text or len(text) > 2000:
                    self._json(HTTPStatus.BAD_REQUEST, {"error": "指令文字不正確"})
                    return
                result = owner.command_handler(text, device["name"])
                self._json(HTTPStatus.ACCEPTED, result)

        self._server = ThreadingHTTPServer(
            (self.config.host, int(self.config.port)),
            Handler,
        )
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="MoHanRemoteServer",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        server = self._server
        self._server = None
        if server is not None:
            server.shutdown()
            server.server_close()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

    def _within_rate_limit(self, token: str) -> bool:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = time.monotonic()
        with self._lock:
            recent = [stamp for stamp in self._rate.get(digest, []) if now - stamp < 60]
            if len(recent) >= max(5, self.config.max_requests_per_minute):
                self._rate[digest] = recent
                return False
            recent.append(now)
            self._rate[digest] = recent
        return True

    def _allowed_file(self, raw: str) -> Path:
        candidate_text = os.path.normpath(
            os.path.abspath(os.path.expanduser(raw))
        )
        candidate_key = os.path.normcase(candidate_text)
        allowed_prefixes = tuple(
            os.path.normcase(os.path.join(str(root), ""))
            for root in self.allowed_folders
        )
        if not any(candidate_key.startswith(prefix) for prefix in allowed_prefixes):
            raise PermissionError("檔案不在遠端白名單")
        try:
            resolved_text = os.path.realpath(candidate_text)
        except (OSError, RuntimeError) as exc:
            raise PermissionError("無法安全解析遠端檔案") from exc
        resolved_key = os.path.normcase(resolved_text)
        if not any(resolved_key.startswith(prefix) for prefix in allowed_prefixes):
            raise PermissionError("檔案不在遠端白名單")
        target = Path(resolved_text)
        if not target.is_file():
            raise FileNotFoundError("找不到檔案")
        lowered = {part.casefold() for part in target.parts}
        protected = {
            ".ssh",
            ".gnupg",
            "credentials",
            "passwords",
            "appdata",
        }
        if lowered & protected or target.suffix.casefold() in {
            ".key",
            ".pem",
            ".pfx",
            ".kdbx",
        }:
            raise PermissionError("敏感檔案禁止遠端存取")
        return target


def constant_time_token_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(left.encode("utf-8")).digest(),
        hashlib.sha256(right.encode("utf-8")).digest(),
    )
