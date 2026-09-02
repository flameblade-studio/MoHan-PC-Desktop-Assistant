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

lazy from infrastructure.update_manifest_signature import (
    MAX_SIGNATURE_BYTES,
    UpdateManifestSignatureError,
    signature_asset_name,
    verify_manifest_signature,
)

MAX_MANIFEST_BYTES = 256 * 1024
MAX_INSTALLER_BYTES = 750 * 1024 * 1024
HTTP_NOT_FOUND = 404
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
        public_keys: tuple[str, ...] | None = None,
    ):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("GitHub repository 格式錯誤。")
        semantic_version_key(current_version)
        self.repository = repository
        self.current_version = current_version
        self.download_dir = Path(download_dir)
        self._opener = opener or urlopen
        self._ssl_context = ssl.create_default_context()
        # None 代表用內嵌公鑰；測試才會注入臨時公鑰。
        self._public_keys = public_keys

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = None
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
        except (AttributeError, TypeError, ValueError):
            hostname = None
        if (
            parsed is None
            or parsed.scheme != "https"
            or hostname not in ALLOWED_DOWNLOAD_HOSTS
        ):
            raise UpdateError("更新網址不是受信任的 GitHub HTTPS 來源。")
        if parsed.username or parsed.password:
            raise UpdateError("更新網址不得包含登入憑證。")

    def _request_bytes(self, url: str, limit: int) -> bytes:
        self._validate_url(url)
        failure: str | None = None
        data: bytes | None = None
        try:
            request = Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "MoHan-Desktop-Assistant-Updater",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            with self._opener(
                request,
                timeout=20,
                context=self._ssl_context,
            ) as response:
                final_url = response.geturl()
                self._validate_url(final_url)
                announced = response.headers.get("Content-Length")
                if announced and int(announced) > limit:
                    failure = "更新資料超過安全大小限制。"
                else:
                    data = response.read(limit + 1)
        except UpdateError:
            failure = "GitHub 更新服務回應格式不正確。"
        except HTTPError as exc:
            failure = (
                "目前沒有符合更新頻道的已發布版本。"
                if exc.code == HTTP_NOT_FOUND
                else "GitHub 更新服務回應錯誤。"
            )
        except (URLError, TimeoutError, OSError):
            failure = "無法連線至 GitHub 更新服務。"
        except (AttributeError, RuntimeError, TypeError, ValueError):
            failure = "GitHub 更新服務回應格式不正確。"
        if failure is not None:
            raise UpdateError(failure)
        if data is None:
            raise UpdateError("GitHub 更新服務沒有回傳資料。")
        if len(data) > limit:
            raise UpdateError("更新資料超過安全大小限制。")
        return data

    def _request_json(self, url: str, limit: int = MAX_MANIFEST_BYTES) -> Any:
        return self._decode_json(self._request_bytes(url, limit))

    @staticmethod
    def _decode_json(data: bytes) -> Any:
        invalid_json = False
        result: Any = None
        try:
            result = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
            invalid_json = True
        if invalid_json:
            raise UpdateError("GitHub 更新資料格式不正確。")
        return result

    def _verified_manifest(
        self,
        manifest_asset: dict[str, Any],
        release: dict[str, Any],
    ) -> Any:
        # SHA-256 只證明安裝程式與清單一致；清單與安裝程式同在一個 Release，
        # 能改 Release 的人兩者一起換。簽章證明清單是持有擁有者私鑰的人發的。
        # 沒有簽章、簽章驗不過、沒有內嵌公鑰，一律拒絕，不退回「只看雜湊」。
        manifest_name = str(manifest_asset.get("name", ""))
        expected = signature_asset_name(manifest_name)
        signature_asset = next(
            (
                asset
                for asset in release.get("assets", [])
                if isinstance(asset, dict) and asset.get("name") == expected
            ),
            None,
        )
        if not signature_asset:
            raise UpdateError("此版本的更新清單尚未簽章，已拒絕更新。")
        manifest_bytes = self._request_bytes(
            str(manifest_asset.get("browser_download_url", "")),
            MAX_MANIFEST_BYTES,
        )
        signature_text = self._request_bytes(
            str(signature_asset.get("browser_download_url", "")),
            MAX_SIGNATURE_BYTES,
        )
        try:
            verify_manifest_signature(
                manifest_bytes,
                signature_text,
                self._public_keys,
            )
        except UpdateManifestSignatureError:
            raise UpdateError("更新清單簽章驗證失敗，已拒絕更新。") from None
        return self._decode_json(manifest_bytes)

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
            manifest = self._verified_manifest(manifest_asset, release)
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
        invalid_size = False
        try:
            size = int(item.get("size", 0))
        except (TypeError, ValueError, OverflowError):
            invalid_size = True
        if invalid_size:
            raise UpdateError("安裝程式大小格式錯誤。")
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
        target = self.download_dir / asset.name
        partial = target.with_suffix(target.suffix + ".part")
        received, actual_digest, failure = self._download_to_partial(
            asset,
            partial,
            progress,
        )
        if failure is not None:
            self._discard_partial(partial)
            raise UpdateError(failure)
        if received != asset.size:
            self._discard_partial(partial)
            raise UpdateError("安裝程式下載不完整。")
        if actual_digest != asset.sha256:
            self._discard_partial(partial)
            raise UpdateError("安裝程式 SHA256 驗證失敗，已拒絕執行。")
        if not self._replace_partial(partial, target):
            self._discard_partial(partial)
            raise UpdateError("安裝程式無法安全儲存。")
        return target

    def _download_to_partial(
        self,
        asset: InstallerAsset,
        partial: Path,
        progress: Callable[[int, int], None] | None,
    ) -> tuple[int, str, str | None]:
        digest = hashlib.sha256()
        received = 0
        failure: str | None = None
        try:
            request = Request(
                asset.url,
                headers={"User-Agent": "MoHan-Desktop-Assistant-Updater"},
            )
            self.download_dir.mkdir(parents=True, exist_ok=True)
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
                        failure = "安裝程式下載大小與清單不符。"
                        break
                    digest.update(chunk)
                    handle.write(chunk)
                    if progress:
                        progress(received, asset.size)
        except UpdateError:
            failure = "安裝程式下載失敗。"
        except (
            AttributeError,
            HTTPError,
            OSError,
            RuntimeError,
            TimeoutError,
            TypeError,
            URLError,
            ValueError,
        ):
            failure = "安裝程式下載失敗。"
        return received, digest.hexdigest().lower(), failure

    @staticmethod
    def _replace_partial(partial: Path, target: Path) -> bool:
        try:
            os.replace(partial, target)
        except (OSError, TypeError, ValueError):
            return False
        return True

    @staticmethod
    def _discard_partial(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except (OSError, TypeError, ValueError):
            # The original safe failure must not be replaced by a private path.
            return
