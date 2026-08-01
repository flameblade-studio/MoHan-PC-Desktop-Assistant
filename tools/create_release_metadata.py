from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


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
    version = args.tag.removeprefix("v")
    artifacts = args.artifacts.resolve()
    prefix = f"https://github.com/{args.repository}/releases/download/{args.tag}"

    installers = []
    for kind, pattern in (("exe", "*Setup.exe"), ("msi", "*.msi")):
        matches = sorted(artifacts.glob(pattern))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one {kind} installer, found {len(matches)}")
        path = matches[0]
        installers.append(
            {
                "kind": kind,
                "name": path.name,
                "url": f"{prefix}/{path.name}",
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
        )

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

    checksum_path = artifacts / f"MoHan-Desktop-Assistant-{args.tag}-SHA256.txt"
    checksum_targets = sorted(
        path
        for path in artifacts.iterdir()
        if path.is_file() and path != checksum_path
    )
    checksum_path.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in checksum_targets),
        encoding="ascii",
    )
    print(manifest_path)
    print(checksum_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
