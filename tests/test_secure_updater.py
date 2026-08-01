from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from email.message import Message
from pathlib import Path
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from updater import (
    InstallerAsset,
    UpdateError,
    UpdateManager,
    is_newer_version,
)


class FakeResponse:
    def __init__(self, url: str, payload: bytes):
        self.url = url
        self.payload = payload
        self.offset = 0
        self.headers = Message()
        self.headers["Content-Length"] = str(len(payload))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self) -> str:
        return self.url

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.payload) - self.offset
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


def main() -> None:
    assert is_newer_version("2.0.14", "2.0.14-rc.9")
    assert is_newer_version("2.0.14-rc.10", "2.0.14-rc.2")
    assert not is_newer_version("2.0.13", "2.0.14-rc.2")

    installer_bytes = b"verified installer payload"
    digest = hashlib.sha256(installer_bytes).hexdigest()
    repo = "hitoshic1982/MoHan-PC-Desktop-Assistant"
    tag = "v2.0.15"
    manifest_name = f"MoHan-Desktop-Assistant-{tag}-update.json"
    installer_name = f"MoHan-Desktop-Assistant-{tag}-Windows-x64-Setup.exe"
    installer_url = f"https://github.com/{repo}/releases/download/{tag}/{installer_name}"
    manifest_url = f"https://github.com/{repo}/releases/download/{tag}/{manifest_name}"
    manifest = {
        "schema": 1,
        "repository": repo,
        "version": "2.0.15",
        "tag": tag,
        "installers": [
            {
                "kind": "exe",
                "name": installer_name,
                "url": installer_url,
                "sha256": digest,
                "size": len(installer_bytes),
            }
        ],
    }
    release = {
        "tag_name": tag,
        "draft": False,
        "prerelease": False,
        "html_url": f"https://github.com/{repo}/releases/tag/{tag}",
        "body": "Release notes",
        "published_at": "2026-08-01T00:00:00Z",
        "assets": [
            {"name": manifest_name, "browser_download_url": manifest_url}
        ],
    }
    responses = {
        f"https://api.github.com/repos/{repo}/releases/latest": json.dumps(release).encode(),
        manifest_url: json.dumps(manifest).encode(),
        installer_url: installer_bytes,
    }

    def opener(request, **_kwargs):
        url = request.full_url
        if url not in responses:
            raise URLError("unexpected URL")
        return FakeResponse(url, responses[url])

    with tempfile.TemporaryDirectory() as temp:
        manager = UpdateManager(repo, "2.0.14-rc.2", Path(temp), opener)
        update = manager.check("stable")
        assert update is not None and update.version == "2.0.15"
        asset = update.preferred_installer()
        downloaded = manager.download(asset)
        assert downloaded.read_bytes() == installer_bytes

        bad = InstallerAsset(
            asset.kind,
            "bad.exe",
            asset.url,
            "0" * 64,
            asset.size,
        )
        try:
            manager.download(bad)
        except UpdateError as exc:
            assert "SHA256" in str(exc)
        else:
            raise AssertionError("invalid SHA256 was accepted")

    for unsafe in (
        "http://github.com/update.exe",
        "https://evil.example/update.exe",
        "https://user:pass@github.com/update.exe",
    ):
        try:
            UpdateManager._validate_url(unsafe)
        except UpdateError:
            pass
        else:
            raise AssertionError(f"unsafe URL accepted: {unsafe}")

    print("SECURE_AUTO_UPDATE_OK")


if __name__ == "__main__":
    main()
