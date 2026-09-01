"""Allow-listed Windows and filesystem tools for the flagship executor."""

from __future__ import annotations

lazy import webbrowser
lazy from pathlib import Path
lazy from typing import Protocol
lazy from urllib.parse import ParseResult, urlparse

lazy from domain.flagship_action_models import ActionRequest, ActionResult
lazy from infrastructure.platform_contracts import PlatformServicePort
lazy from infrastructure.platform_services import current_platform_services

__all__ = ("WindowsToolbox",)

MAX_SEARCH_RESULTS = 200


class ActionRegistrar(Protocol):
    def register(self, capability: str, handler, verifier=None) -> None: ...


def _origin(parsed: ParseResult) -> tuple[str, str, int] | None:
    """(scheme, host, port)；port 補上該 scheme 的預設值。

    原本只比 `hostname`，於是 `https://portal.example/app` 這一條同時放行了
    `http://portal.example:8080/...`：scheme 沒被要求相符（那一行檢查的是
    白名單項目自己的 scheme），而 `hostname` 不含 port。
    """
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    default_port = 443 if parsed.scheme == "https" else 80
    try:
        port = parsed.port or default_port
    except ValueError:
        return None
    return parsed.scheme, parsed.hostname.lower(), port


def _same_origin(request: ParseResult, allowed: ParseResult) -> bool:
    request_origin = _origin(request)
    return request_origin is not None and request_origin == _origin(allowed)


def _path_within(request_path: str, allowed_path: str) -> bool:
    """路徑必須落在允許的**路徑段**之下，不是字首相符。

    字首比對讓 `/app` 涵蓋 `/app-delete`——相鄰但無關的路徑，對帶有 GET
    副作用的管理介面尤其危險。
    """
    request_path = request_path or "/"
    allowed_path = allowed_path or "/"
    if allowed_path == "/":
        return True
    allowed_path = allowed_path.rstrip("/")
    return request_path == allowed_path or request_path.startswith(allowed_path + "/")


class WindowsToolbox:
    """Small, explicit Windows tool surface; never executes arbitrary shell."""

    def __init__(
        self,
        *,
        allowed_folders: list[str] | None = None,
        writable_folders: list[str] | None = None,
        allowed_apps: dict[str, str] | None = None,
        allowed_websites: list[str] | None = None,
        platform_services: PlatformServicePort | None = None,
    ) -> None:
        self.platform_services = platform_services or current_platform_services()
        self.allowed_folders = [
            Path(value).expanduser().resolve()
            for value in (allowed_folders or [])
            if str(value).strip()
        ]
        # 可寫入的資料夾是 allowed_folders 的子集合，而且**預設為空**。
        # 安全設定把每個資料夾存成「唯讀」或「可寫入」，但先前只有
        # target_value 被讀出來，access_mode 整個被丟掉——使用者在介面上
        # 選的「唯讀」因此完全沒有作用，create_file／move_file／rename_file
        # 照樣能寫進去。介面告訴使用者的權限邊界是假的。
        #
        # 這裡刻意 fail-closed：沒有明確指定就一律不可寫。呼叫端必須把
        # access_mode 傳進來，忘了傳的後果是「不能寫」而不是「什麼都能寫」。
        self.writable_folders = [
            Path(value).expanduser().resolve()
            for value in (writable_folders or [])
            if str(value).strip()
        ]
        self.allowed_apps = {
            name.casefold(): str(Path(path).expanduser().resolve())
            for name, path in (allowed_apps or {}).items()
            if name.strip() and str(path).strip()
        }
        self.allowed_websites = [
            value.rstrip("/")
            for value in (allowed_websites or [])
            if str(value).strip()
        ]

    def register_with(self, executor: ActionRegistrar) -> None:
        executor.register("open_web", self.open_web)
        executor.register("open_folder", self.open_folder)
        executor.register("launch_app", self.launch_app)
        executor.register("search_local", self.search_local)
        executor.register("create_file", self.create_file, self.verify_file)
        executor.register("rename_file", self.rename_file, self.verify_destination)
        executor.register("move_file", self.move_file, self.verify_destination)

    def _allowed_path(
        self,
        raw: str,
        *,
        must_exist: bool = False,
        write: bool = False,
    ) -> Path:
        if not self.allowed_folders:
            raise PermissionError("尚未設定允許操作的資料夾")
        target = Path(raw).expanduser().resolve()
        if not any(
            root == target or root in target.parents
            for root in self.allowed_folders
        ):
            raise PermissionError("路徑不在允許清單內")
        if write and not any(
            root == target or root in target.parents
            for root in self.writable_folders
        ):
            raise PermissionError("此資料夾設定為唯讀，不允許寫入")
        if must_exist and not target.exists():
            raise FileNotFoundError(target)
        return target

    def open_web(self, request: ActionRequest) -> ActionResult:
        value = str(request.arguments.get("url", "")).strip()
        parsed = urlparse(value)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("只允許完整的 HTTP 或 HTTPS 網址")
        if not self.allowed_websites:
            raise PermissionError("尚未設定允許開啟的網站")
        allowed = any(
            _same_origin(parsed, allowed_parsed)
            and _path_within(parsed.path, allowed_parsed.path)
            for entry in self.allowed_websites
            if (allowed_parsed := urlparse(entry))
        )
        if not allowed:
            raise PermissionError("網址不在允許清單內")
        opened = webbrowser.open(value, new=2)
        return ActionResult(request.request_id, bool(opened), "已開啟網站")

    def open_folder(self, request: ActionRequest) -> ActionResult:
        target = self._allowed_path(
            str(request.arguments.get("path", "")),
            must_exist=True,
        )
        if not target.is_dir():
            raise NotADirectoryError(target)
        self.platform_services.open_path(target)
        return ActionResult(request.request_id, True, f"已開啟資料夾：{target}")

    def launch_app(self, request: ActionRequest) -> ActionResult:
        name = str(request.arguments.get("name", "")).strip().casefold()
        target = self.allowed_apps.get(name)
        if not target:
            raise PermissionError("程式不在允許清單內")
        if not Path(target).is_file():
            raise FileNotFoundError(target)
        self.platform_services.open_path(Path(target))
        return ActionResult(request.request_id, True, f"已啟動：{name}")

    def create_file(self, request: ActionRequest) -> ActionResult:
        target = self._allowed_path(
            str(request.arguments.get("path", "")), write=True)
        if target.exists():
            raise FileExistsError("預設禁止覆寫既有檔案")
        target.parent.mkdir(parents=True, exist_ok=True)
        content = str(request.arguments.get("content", ""))
        target.write_text(content, encoding="utf-8")
        return ActionResult(
            request.request_id,
            True,
            f"已建立檔案：{target.name}",
            {"path": str(target), "size": target.stat().st_size},
        )

    def search_local(self, request: ActionRequest) -> ActionResult:
        query = str(request.arguments.get("query", "")).strip().casefold()
        if not query:
            raise ValueError("搜尋文字不可留空")
        results: list[dict[str, object]] = []
        for root in self.allowed_folders:
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if len(results) >= MAX_SEARCH_RESULTS:
                    break
                try:
                    relative = path.relative_to(root)
                except ValueError:
                    continue
                if query not in path.name.casefold():
                    continue
                results.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "relative": str(relative),
                        "is_file": path.is_file(),
                    }
                )
        return ActionResult(
            request.request_id,
            True,
            f"找到 {len(results)} 個符合項目",
            {"results": results, "truncated": len(results) >= MAX_SEARCH_RESULTS},
        )

    def rename_file(self, request: ActionRequest) -> ActionResult:
        return self._relocate(request)

    def move_file(self, request: ActionRequest) -> ActionResult:
        return self._relocate(request)

    def _relocate(self, request: ActionRequest) -> ActionResult:
        # 兩邊都要 write 權限。搬移會讓來源消失、重新命名會改掉來源，
        # 只檢查目的地等於允許把唯讀資料夾裡的東西搬走。
        source = self._allowed_path(
            str(request.arguments.get("source", "")),
            must_exist=True,
            write=True,
        )
        destination = self._allowed_path(
            str(request.arguments.get("destination", "")),
            write=True,
        )
        if destination.exists():
            raise FileExistsError("目的地已存在，預設禁止覆寫")
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)
        return ActionResult(
            request.request_id,
            True,
            f"已移動至：{destination}",
            {"source": str(source), "destination": str(destination)},
        )

    @staticmethod
    def verify_file(_request: ActionRequest, result: ActionResult) -> bool:
        raw = result.data.get("path")
        return isinstance(raw, str) and Path(raw).is_file()

    @staticmethod
    def verify_destination(
        _request: ActionRequest,
        result: ActionResult,
    ) -> bool:
        destination = result.data.get("destination")
        source = result.data.get("source")
        return (
            isinstance(destination, str)
            and Path(destination).exists()
            and isinstance(source, str)
            and not Path(source).exists()
        )
