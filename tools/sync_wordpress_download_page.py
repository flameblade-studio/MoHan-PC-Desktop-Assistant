from __future__ import annotations

import argparse
import base64
import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


START_MARKER = "<!-- MOHAN_RELEASE_START -->"
END_MARKER = "<!-- MOHAN_RELEASE_END -->"
DEFAULT_SLUG = "mohan-desktop-assistant-download"


def request_json(
    url: str,
    method: str = "GET",
    payload: dict | None = None,
) -> object:
    base_url = os.environ["WORDPRESS_BASE_URL"].rstrip("/")
    parsed_base = urllib.parse.urlparse(base_url)
    parsed_url = urllib.parse.urlparse(url)
    if (
        parsed_base.scheme != "https"
        or parsed_url.scheme != "https"
        or parsed_url.hostname != parsed_base.hostname
    ):
        raise RuntimeError("WordPress API must use the configured HTTPS host")
    username = os.environ["WORDPRESS_USERNAME"]
    password = os.environ["WORDPRESS_APP_PASSWORD"].replace(" ", "")
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    data = None
    headers = {
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
        "User-Agent": "MoHan-GitHub-Release-Sync",
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", "replace")
        raise RuntimeError(
            f"WordPress API returned {exc.code}: {detail}"
        ) from exc


def release_block(manifest: dict, release_url: str) -> str:
    version = html.escape(str(manifest["version"]))
    tag = html.escape(str(manifest["tag"]))
    cards = []
    for installer in manifest["installers"]:
        label = "EXE 安裝程式（建議）" if installer["kind"] == "exe" else "MSI 安裝套件"
        cards.append(
            '<p><a class="wp-element-button" rel="noopener" '
            f'href="{html.escape(installer["url"], quote=True)}">'
            f'下載 {label} / Download {installer["kind"].upper()}</a><br>'
            f'<small>SHA256: <code>{html.escape(installer["sha256"])}</code></small></p>'
        )
    return (
        f"{START_MARKER}\n"
        '<section class="mohan-release-download">'
        '<h2>墨寒桌面助理下載 / MoHan Desktop Assistant</h2>'
        f'<p><strong>最新版本 / Latest version: {version}</strong> ({tag})</p>'
        '<p>Windows 10/11 x64。安裝程式由 GitHub Actions 自動建置，'
        '並附 SHA256、SBOM 與 Artifact Attestation。</p>'
        '<p>Windows 10/11 x64. Built automatically by GitHub Actions with '
        'SHA256 checksums, an SBOM, and artifact attestations.</p>'
        + "".join(cards)
        + f'<p><a href="{html.escape(release_url, quote=True)}" rel="noopener">'
        '查看完整 Release Notes 與驗證資料 / Release notes and verification</a></p>'
        '</section>\n'
        f"{END_MARKER}"
    )


def replace_managed_block(current: str, block: str) -> str:
    if START_MARKER in current and END_MARKER in current:
        before, remainder = current.split(START_MARKER, 1)
        _, after = remainder.split(END_MARKER, 1)
        return before.rstrip() + "\n\n" + block + "\n" + after.lstrip()
    return current.rstrip() + "\n\n" + block + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--release-url", required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    base = os.environ["WORDPRESS_BASE_URL"].rstrip("/")
    api = f"{base}/wp-json/wp/v2/pages"
    page_id = os.environ.get("WORDPRESS_DOWNLOAD_PAGE_ID", "").strip()

    if page_id:
        page = request_json(f"{api}/{int(page_id)}?context=edit")
    else:
        query = urllib.parse.urlencode(
            {"slug": DEFAULT_SLUG, "context": "edit", "per_page": 1}
        )
        pages = request_json(f"{api}?{query}")
        page = pages[0] if isinstance(pages, list) and pages else None

    block = release_block(manifest, args.release_url)
    if page is None:
        updated = request_json(
            api,
            method="POST",
            payload={
                "title": "墨寒桌面助理下載 / MoHan Desktop Assistant",
                "slug": DEFAULT_SLUG,
                "status": "publish",
                "content": block,
            },
        )
    else:
        page_id = int(page["id"])
        current = str(page.get("content", {}).get("raw", ""))
        updated = request_json(
            f"{api}/{page_id}",
            method="POST",
            payload={"content": replace_managed_block(current, block)},
        )
    print(updated["link"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
