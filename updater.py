from __future__ import annotations

lazy import hashlib
lazy import json
lazy import os
lazy import re
lazy import ssl
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Any
lazy from urllib.error import HTTPError, URLError
lazy from urllib.parse import urlparse
lazy from urllib.request import Request, urlopen

MAX_MANIFEST_BYTES = 256 * 1024
MAX_INSTALLER_BYTES = 750 * 1024 * 1024
ALLOWED_DOWNLOAD_HOSTS = frozenset(
    {
        "api.github.com",
        "github.com",
        "objects.githubusercontent.com",
        "release-assets.githubusercontent.com",
    }
)
SEMVER_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)


class UpdateError(RuntimeError):
    """A safe, user-displayable updater failure."""


@dataclass(frozen=True)
class InstallerAsset:
    kind: str
    name: str
    url: str
    sha256: str
    size: int


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag: str
    release_url: str
    notes: str
    published_at: str
    prerelease: bool
    installers: tuple[InstallerAsset, ...]

    def preferred_installer(self) -> InstallerAsset:
        for kind in ("exe", "msi"):
            for installer in self.installers:
                if installer.kind == kind:
                    return installer
        raise UpdateError("此版本沒有可用的 Windows 安裝程式。")


def _prerelease_key(value: str) -> tuple[tuple[int, object], ...]:
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in value.lower().split(".")
    )


def semantic_version_key(value: str) -> tuple[Any, ...]:
    match = SEMVER_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"不是有效的語意版本：{value}")
    prerelease = match.group("pre")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        1 if prerelease is None else 0,
        () if prerelease is None else _prerelease_key(prerelease),
    )


def is_newer_version(candidate: str, current: str) -> bool:
    return semantic_version_key(candidate) > semantic_version_key(current)


class UpdateManager:
    def __init__(
        self,
        repository: str,
        current_version: str,
        download_dir: Path,
        opener: Callable[..., Any] | None = None,
    ):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("GitHub repository 格式錯誤。")
        semantic_version_key(current_version)
        self.repository = repository
        self.current_version = current_version
        self.download_dir = Path(download_dir)
        self._opener = opener or urlopen
        self._ssl_context = ssl.create_default_context()

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS:
            raise UpdateError("更新網址不是受信任的 GitHub HTTPS 來源。")
        if parsed.username or parsed.password:
            raise UpdateError("更新網址不得包含登入憑證。")

    def _request_bytes(self, url: str, limit: int) -> bytes:
        self._validate_url(url)
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "MoHan-Desktop-Assistant-Updater",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with self._opener(
                request,
                timeout=20,
                context=self._ssl_context,
            ) as response:
                final_url = response.geturl()
                self._validate_url(final_url)
                announced = response.headers.get("Content-Length")
                if announced and int(announced) > limit:
                    raise UpdateError("更新資料超過安全大小限制。")
                data = response.read(limit + 1)
        except HTTPError as exc:
            if exc.code == 404:
                raise UpdateError("目前沒有符合更新頻道的已發布版本。") from exc
            raise UpdateError(f"GitHub 更新服務回應錯誤（{exc.code}）。") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise UpdateError("無法連線至 GitHub 更新服務。") from exc
        if len(data) > limit:
            raise UpdateError("更新資料超過安全大小限制。")
        return data

    def _request_json(self, url: str, limit: int = MAX_MANIFEST_BYTES) -> Any:
        try:
            return json.loads(self._request_bytes(url, limit).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpdateError("GitHub 更新資料格式不正確。") from exc

    def _release_candidates(self, channel: str) -> list[dict[str, Any]]:
        endpoint = f"https://api.github.com/repos/{self.repository}/releases"
        payload = self._request_json(
            endpoint + ("/latest" if channel == "stable" else "?per_page=20")
        )
        releases = [payload] if isinstance(payload, dict) else payload
        if not isinstance(releases, list):
            raise UpdateError("GitHub Release 回應格式不正確。")
        return [
            release
            for release in releases
            if isinstance(release, dict)
            and not bool(release.get("draft"))
            and (channel == "preview" or not bool(release.get("prerelease")))
        ]

    def check(self, channel: str = "stable") -> ReleaseInfo | None:
        if channel not in {"stable", "preview"}:
            raise ValueError("更新頻道必須是 stable 或 preview。")
        candidates = []
        for release in self._release_candidates(channel):
            try:
                semantic_version_key(str(release.get("tag_name", "")))
            except ValueError:
                continue
            candidates.append(release)
        candidates.sort(
            key=lambda item: semantic_version_key(
                str(item.get("tag_name", ""))
            ),
            reverse=True,
        )
        for release in candidates:
            tag = str(release.get("tag_name", ""))
            version = tag.lstrip("v")
            if not is_newer_version(version, self.current_version):
                continue
            manifest_name = f"MoHan-Desktop-Assistant-{tag}-update.json"
            manifest_asset = next(
                (
                    asset
                    for asset in release.get("assets", [])
                    if asset.get("name") == manifest_name
                ),
                None,
            )
            if not manifest_asset:
                continue
            manifest = self._request_json(
                str(manifest_asset.get("browser_download_url", ""))
            )
            return self._parse_manifest(manifest, release)
        return None

    def _parse_manifest(
        self,
        manifest: Any,
        release: dict[str, Any],
    ) -> ReleaseInfo:
        version, tag = self._validate_manifest_identity(manifest, release)
        installers = tuple(
            asset
            for item in manifest.get("installers", [])
            if (asset := self._parse_installer(item)) is not None
        )
        if not installers:
            raise UpdateError("更新清單沒有可驗證的 Windows 安裝程式。")
        return ReleaseInfo(
            version=version,
            tag=tag,
            release_url=str(release.get("html_url", "")),
            notes=str(release.get("body", "")),
            published_at=str(release.get("published_at", "")),
            prerelease=bool(release.get("prerelease")),
            installers=installers,
        )

    def _validate_manifest_identity(
        self,
        manifest: Any,
        release: dict[str, Any],
    ) -> tuple[str, str]:
        if not isinstance(manifest, dict) or manifest.get("schema") != 1:
            raise UpdateError("更新清單版本不受支援。")
        version = str(manifest.get("version", ""))
        tag = str(manifest.get("tag", ""))
        if tag != release.get("tag_name") or version != tag.lstrip("v"):
            raise UpdateError("更新清單與 GitHub Release 版本不一致。")
        if manifest.get("repository") != self.repository:
            raise UpdateError("更新清單不屬於官方儲存庫。")
        return version, tag

    def _parse_installer(self, item: object) -> InstallerAsset | None:
        if not isinstance(item, dict):
            return None
        kind = str(item.get("kind", "")).lower()
        if kind not in {"exe", "msi"}:
            return None
        name = str(item.get("name", ""))
        url = str(item.get("url", ""))
        digest = str(item.get("sha256", "")).lower()
        size = int(item.get("size", 0))
        if Path(name).name != name or not re.fullmatch(
            r"[A-Za-z0-9_.-]+",
            name,
        ):
            raise UpdateError("安裝程式檔名不安全。")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise UpdateError("安裝程式 SHA256 格式錯誤。")
        if size <= 0 or size > MAX_INSTALLER_BYTES:
            raise UpdateError("安裝程式大小超過安全限制。")
        self._validate_url(url)
        return InstallerAsset(kind, name, url, digest, size)

    def download(
        self,
        asset: InstallerAsset,
        progress: Callable[[int, int], None] | None = None,
    ) -> Path:
        self._validate_url(asset.url)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        target = self.download_dir / asset.name
        partial = target.with_suffix(target.suffix + ".part")
        request = Request(
            asset.url,
            headers={"User-Agent": "MoHan-Desktop-Assistant-Updater"},
        )
        digest = hashlib.sha256()
        received = 0
        try:
            with self._opener(
                request,
                timeout=30,
                context=self._ssl_context,
            ) as response, partial.open("wb") as handle:
                self._validate_url(response.geturl())
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > asset.size or received > MAX_INSTALLER_BYTES:
                        raise UpdateError("安裝程式下載大小與清單不符。")
                    digest.update(chunk)
                    handle.write(chunk)
                    if progress:
                        progress(received, asset.size)
            if received != asset.size:
                raise UpdateError("安裝程式下載不完整。")
            if digest.hexdigest().lower() != asset.sha256:
                raise UpdateError("安裝程式 SHA256 驗證失敗，已拒絕執行。")
            os.replace(partial, target)
            return target
        except UpdateError:
            partial.unlink(missing_ok=True)
            raise
        except (URLError, TimeoutError, OSError) as exc:
            partial.unlink(missing_ok=True)
            raise UpdateError("安裝程式下載失敗。") from exc
