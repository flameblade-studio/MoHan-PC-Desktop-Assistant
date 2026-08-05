from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote


TAG_PATTERN = re.compile(r"^v2\.2\.0-rc\.[1-9][0-9]*$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    if not TAG_PATTERN.fullmatch(args.tag):
        raise ValueError("Release metadata is restricted to v2.2.0-rc.N tags")
    version = args.tag.removeprefix("v")
    artifacts = args.artifacts.resolve()
    prefix = f"https://github.com/{args.repository}/releases/download/{args.tag}"

    installers = []
    base = f"MoHan-Desktop-Assistant-{args.tag}"
    package_specs = (
        (
            "exe",
            "windows",
            "x86_64",
            "complete",
            f"{base}-Windows-x64-Setup.exe",
            None,
        ),
        (
            "msi",
            "windows",
            "x86_64",
            "complete",
            f"{base}-Windows-x64.msi",
            "zh-TW",
        ),
        (
            "mst",
            "windows",
            "x86_64",
            "complete",
            f"{base}-en-US.mst",
            "en-US",
        ),
        (
            "mst",
            "windows",
            "x86_64",
            "complete",
            f"{base}-zh-CN.mst",
            "zh-CN",
        ),
        (
            "mst",
            "windows",
            "x86_64",
            "complete",
            f"{base}-ja-JP.mst",
            "ja-JP",
        ),
        (
            "zip",
            "windows",
            "x86_64",
            "complete",
            f"{base}-Windows-x64.zip",
            None,
        ),
        (
            "dmg",
            "macos",
            "arm64",
            "preview",
            f"{base}-macOS-arm64-Preview.dmg",
            None,
        ),
        (
            "dmg",
            "macos",
            "x86_64",
            "preview",
            f"{base}-macOS-x86_64-Preview.dmg",
            None,
        ),
        (
            "appimage",
            "linux",
            "x86_64",
            "preview",
            f"{base}-Linux-x86_64-Preview.AppImage",
            None,
        ),
    )
    for kind, platform, architecture, maturity, pattern, locale in package_specs:
        matches = sorted(artifacts.glob(pattern))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one {kind} package, found {len(matches)}")
        path = matches[0]
        item = {
            "kind": kind,
            "platform": platform,
            "architecture": architecture,
            "maturity": maturity,
            "name": path.name,
            "url": f"{prefix}/{quote(path.name)}",
            "sha256": sha256(path),
            "size": path.stat().st_size,
        }
        if locale is not None:
            item["locale"] = locale
        installers.append(item)

    manifest_name = f"MoHan-Desktop-Assistant-{args.tag}-update.json"
    manifest = {
        "schema": 1,
        "repository": args.repository,
        "version": version,
        "tag": args.tag,
        "channel": "preview" if "-" in version else "stable",
        "release_url": f"https://github.com/{args.repository}/releases/tag/{args.tag}",
        "installers": installers,
    }
    manifest_path = artifacts / manifest_name
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    checksum_path = (
        artifacts / f"MoHan-Desktop-Assistant-{args.tag}-SHA256SUMS.txt"
    )
    compatibility_checksum_path = (
        artifacts / f"MoHan-Desktop-Assistant-{args.tag}-SHA256.txt"
    )
    checksum_targets = sorted(
        path
        for path in artifacts.iterdir()
        if path.is_file()
        and path not in {checksum_path, compatibility_checksum_path}
    )
    checksum_catalog = "".join(
        f"{sha256(path)}  {path.name}\n" for path in checksum_targets
    )
    checksum_path.write_text(checksum_catalog, encoding="ascii")
    compatibility_checksum_path.write_text(checksum_catalog, encoding="ascii")
    print(manifest_path)
    print(checksum_path)
    print(compatibility_checksum_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
