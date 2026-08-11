from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import re
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from urllib.parse import quote

TAG_PATTERN = re.compile(
    r"^v[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[1-9][0-9]*)?$"
)


@dataclass(frozen=True, slots=True)
class ReleaseArguments:
    artifacts: Path
    tag: str
    repository: str


@dataclass(frozen=True, slots=True)
class PackageSpec:
    kind: str
    platform: str
    architecture: str
    maturity: str
    name: str
    locale: str | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_arguments() -> ReleaseArguments:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    return ReleaseArguments(args.artifacts, args.tag, args.repository)


def _validate_tag(tag: str) -> None:
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError("Release metadata requires a vN.N.N or vN.N.N-rc.N tag")


def _package_specs(tag: str) -> tuple[PackageSpec, ...]:
    base = f"MoHan-Desktop-Assistant-{tag}"
    return (
        PackageSpec(
            "exe",
            "windows",
            "x86_64",
            "complete",
            f"{base}-Windows-x64-Setup.exe",
        ),
        PackageSpec(
            "msi",
            "windows",
            "x86_64",
            "complete",
            f"{base}-Windows-x64.msi",
            "zh-TW",
        ),
        PackageSpec(
            "mst",
            "windows",
            "x86_64",
            "complete",
            f"{base}-en-US.mst",
            "en-US",
        ),
        PackageSpec(
            "mst",
            "windows",
            "x86_64",
            "complete",
            f"{base}-zh-CN.mst",
            "zh-CN",
        ),
        PackageSpec(
            "mst",
            "windows",
            "x86_64",
            "complete",
            f"{base}-ja-JP.mst",
            "ja-JP",
        ),
        PackageSpec(
            "zip",
            "windows",
            "x86_64",
            "complete",
            f"{base}-Windows-x64.zip",
        ),
        PackageSpec(
            "dmg",
            "macos",
            "arm64",
            "preview",
            f"{base}-macOS-arm64-Preview.dmg",
        ),
        PackageSpec(
            "dmg",
            "macos",
            "x86_64",
            "preview",
            f"{base}-macOS-x86_64-Preview.dmg",
        ),
        PackageSpec(
            "appimage",
            "linux",
            "x86_64",
            "preview",
            f"{base}-Linux-x86_64-Preview.AppImage",
        ),
    )


def _installer_item(
    artifacts: Path,
    prefix: str,
    spec: PackageSpec,
) -> dict[str, object]:
    matches = sorted(artifacts.glob(spec.name))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one {spec.kind} package, found {len(matches)}"
        )
    path = matches[0]
    item: dict[str, object] = {
        "kind": spec.kind,
        "platform": spec.platform,
        "architecture": spec.architecture,
        "maturity": spec.maturity,
        "name": path.name,
        "url": f"{prefix}/{quote(path.name)}",
        "sha256": sha256(path),
        "size": path.stat().st_size,
    }
    if spec.locale is not None:
        item["locale"] = spec.locale
    return item


def _collect_installers(
    artifacts: Path,
    tag: str,
    repository: str,
) -> list[dict[str, object]]:
    prefix = f"https://github.com/{repository}/releases/download/{tag}"
    return [
        _installer_item(artifacts, prefix, spec)
        for spec in _package_specs(tag)
    ]


def _write_manifest(
    artifacts: Path,
    args: ReleaseArguments,
    installers: list[dict[str, object]],
) -> Path:
    version = args.tag.removeprefix("v")
    manifest = {
        "schema": 1,
        "repository": args.repository,
        "version": version,
        "tag": args.tag,
        "channel": "preview" if "-" in version else "stable",
        "release_url": (
            f"https://github.com/{args.repository}/releases/tag/{args.tag}"
        ),
        "installers": installers,
    }
    manifest_path = (
        artifacts / f"MoHan-Desktop-Assistant-{args.tag}-update.json"
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _write_checksum_catalogs(
    artifacts: Path,
    tag: str,
) -> tuple[Path, Path]:
    checksum_path = (
        artifacts / f"MoHan-Desktop-Assistant-{tag}-SHA256SUMS.txt"
    )
    compatibility_path = (
        artifacts / f"MoHan-Desktop-Assistant-{tag}-SHA256.txt"
    )
    excluded = {checksum_path, compatibility_path}
    checksum_targets = sorted(
        path
        for path in artifacts.iterdir()
        if path.is_file() and path not in excluded
    )
    catalog = "".join(
        f"{sha256(path)}  {path.name}\n" for path in checksum_targets
    )
    checksum_path.write_text(catalog, encoding="ascii")
    compatibility_path.write_text(catalog, encoding="ascii")
    return checksum_path, compatibility_path


def main() -> int:
    args = _parse_arguments()
    _validate_tag(args.tag)
    artifacts = args.artifacts.resolve()
    installers = _collect_installers(artifacts, args.tag, args.repository)
    manifest_path = _write_manifest(artifacts, args, installers)
    checksum_path, compatibility_path = _write_checksum_catalogs(
        artifacts,
        args.tag,
    )
    print(manifest_path)
    print(checksum_path)
    print(compatibility_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
