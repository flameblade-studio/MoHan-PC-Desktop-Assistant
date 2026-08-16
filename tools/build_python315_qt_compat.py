"""Build MoHan's provenance-preserving Python 3.15 Qt compatibility wheelhouse."""

from __future__ import annotations

lazy import argparse
lazy import base64
lazy import hashlib
lazy import json
lazy import platform
lazy import re
lazy import sys
lazy import tempfile
lazy import zipfile
lazy from pathlib import Path
lazy from urllib.request import Request, urlopen

try:
    from packaging.tags import sys_tags
    from packaging.utils import parse_wheel_filename
except ImportError:
    from pip._vendor.packaging.tags import sys_tags
    from pip._vendor.packaging.utils import parse_wheel_filename

ROOT = Path(__file__).resolve().parents[1]
QT_DISTRIBUTIONS = (
    "PySide6",
    "PySide6_Addons",
    "PySide6_Essentials",
    "shiboken6",
)
UPSTREAM_VERSION = "6.11.1"
COMPATIBILITY_VERSION = "6.11.1+mohan.py315.1"
TARGET_PYTHON = "3.15"
TARGET_REQUIRES_PYTHON = ">=3.10,<3.16"
PYPI_JSON_TEMPLATE = "https://pypi.org/pypi/{name}/{version}/json"
USER_AGENT = "MoHan-Qt315-Compatibility/1.0"
WHEEL_SUFFIX = ".whl"
DIST_INFO_PATTERN = re.compile(r"^(?P<name>.+)-(?P<version>[^/]+)\.dist-info/")


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download the pinned official Qt wheels, record their provenance, "
            "and create a local Python 3.15 compatibility wheelhouse."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Empty or dedicated directory for the generated wheelhouse.",
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        default=ROOT / "requirements.txt",
    )
    parser.add_argument("--python-version", default=TARGET_PYTHON)
    return parser.parse_args(argv)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        for block in iter(lambda: response.read(1024 * 1024), b""):
            if not block:
                break
            handle.write(block)


def _load_metadata(distribution: str) -> tuple[dict[str, object], str]:
    url = PYPI_JSON_TEMPLATE.format(name=distribution, version=UPSTREAM_VERSION)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise RuntimeError(f"PyPI metadata for {distribution} is not an object")
    return payload, url


def _accepted_tags() -> frozenset[str]:
    return frozenset(str(tag) for tag in sys_tags())


def _choose_wheel(
    payload: dict[str, object],
    distribution: str,
) -> tuple[dict[str, object], frozenset[str]]:
    accepted = _accepted_tags()
    urls = payload.get("urls")
    if not isinstance(urls, list):
        raise RuntimeError(f"PyPI metadata for {distribution} has no files")
    candidates: list[dict[str, object]] = []
    for item in urls:
        if not isinstance(item, dict) or item.get("packagetype") != "bdist_wheel":
            continue
        filename = item.get("filename")
        if not isinstance(filename, str) or not filename.endswith(WHEEL_SUFFIX):
            continue
        try:
            _, version, _, tags = parse_wheel_filename(filename)
        except ValueError:
            continue
        if str(version) != UPSTREAM_VERSION:
            continue
        if any(str(tag) in accepted for tag in tags):
            candidates.append(item)
    if len(candidates) != 1:
        names = tuple(
            sorted(str(item.get("filename", "")) for item in candidates)
        )
        raise RuntimeError(
            f"Expected exactly one compatible {distribution} wheel for "
            f"{platform.platform()}; found {names}"
        )
    return candidates[0], accepted


def _requirements_pin(requirements: Path) -> str:
    pins = tuple(
        line.partition("==")[2].strip()
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip().casefold().startswith("pyside6==")
    )
    if pins != (UPSTREAM_VERSION,):
        raise RuntimeError(
            f"requirements must pin exactly PySide6=={UPSTREAM_VERSION}; found {pins}"
        )
    return pins[0]


def _dist_info_directory(names: tuple[str, ...]) -> str:
    candidates = tuple(
        name.rsplit("/", 1)[0]
        for name in names
        if name.endswith(".dist-info/METADATA")
    )
    if len(candidates) != 1:
        raise RuntimeError("Wheel must contain exactly one dist-info METADATA file")
    return candidates[0]


def _rewrite_metadata(data: bytes) -> bytes:
    lines = data.decode("utf-8").splitlines()
    result: list[str] = []
    saw_version = False
    saw_requires_python = False
    for line in lines:
        if line.startswith("Version: "):
            result.append(f"Version: {COMPATIBILITY_VERSION}")
            saw_version = True
            continue
        if line.startswith("Requires-Python: "):
            result.append(f"Requires-Python: {TARGET_REQUIRES_PYTHON}")
            saw_requires_python = True
            continue
        if line.startswith("Requires-Dist:") and f"=={UPSTREAM_VERSION}" in line:
            line = line.replace(
                f"=={UPSTREAM_VERSION}",
                f"=={COMPATIBILITY_VERSION}",
            )
        result.append(line)
    if not saw_version or not saw_requires_python:
        raise RuntimeError("Qt wheel metadata lacks Version or Requires-Python")
    return ("\n".join(result) + "\n").encode("utf-8")


def _renamed_member(name: str, source_dist_info: str, target_dist_info: str) -> str:
    if name == source_dist_info or name.startswith(f"{source_dist_info}/"):
        return f"{target_dist_info}{name[len(source_dist_info):]}"
    return name


def _record_line(name: str, data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    return f"{name},sha256={digest.decode('ascii')},{len(data)}"


def _zip_info(source: zipfile.ZipInfo, name: str) -> zipfile.ZipInfo:
    target = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    target.compress_type = source.compress_type
    target.external_attr = source.external_attr
    target.create_system = source.create_system
    target.flag_bits = source.flag_bits & 0x800
    return target


def _repack_wheel(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        names = tuple(info.filename for info in archive.infolist())
        source_dist_info = _dist_info_directory(names)
        source_dist_root = source_dist_info.removesuffix(".dist-info")
        target_dist_info = source_dist_root.rsplit("-", 1)[0] + (
            f"-{COMPATIBILITY_VERSION}.dist-info"
        )
        members: list[tuple[zipfile.ZipInfo, str, bytes]] = []
        for info in archive.infolist():
            if info.filename.endswith("/"):
                continue
            target_name = _renamed_member(
                info.filename,
                source_dist_info,
                target_dist_info,
            )
            data = archive.read(info)
            if target_name == f"{target_dist_info}/METADATA":
                data = _rewrite_metadata(data)
            if target_name == f"{target_dist_info}/RECORD":
                continue
            members.append((info, target_name, data))

    records = [_record_line(name, data) for _, name, data in members]
    records.append(f"{target_dist_info}/RECORD,,")
    record_data = ("\n".join(sorted(records)) + "\n").encode("utf-8")
    with zipfile.ZipFile(destination, "w") as output:
        for source_info, name, data in members:
            output.writestr(_zip_info(source_info, name), data)
        record_source = zipfile.ZipInfo(
            f"{target_dist_info}/RECORD",
            date_time=(1980, 1, 1, 0, 0, 0),
        )
        record_source.compress_type = zipfile.ZIP_DEFLATED
        output.writestr(record_source, record_data)


def _custom_filename(source_filename: str) -> str:
    marker = f"-{UPSTREAM_VERSION}-"
    if marker not in source_filename:
        raise RuntimeError(f"Unexpected Qt wheel filename: {source_filename}")
    return source_filename.replace(
        marker,
        f"-{COMPATIBILITY_VERSION}-",
        1,
    )


def build_wheelhouse(output_dir: Path, requirements: Path) -> dict[str, object]:
    _requirements_pin(requirements.resolve())
    if sys.version_info[:2] != (3, 15):
        raise RuntimeError("Qt compatibility wheels must be prepared with Python 3.15")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="mohan-qt315-upstream-") as raw:
        temporary = Path(raw)
        for distribution in QT_DISTRIBUTIONS:
            payload, metadata_url = _load_metadata(distribution)
            selected, accepted = _choose_wheel(payload, distribution)
            filename = selected.get("filename")
            url = selected.get("url")
            expected_hash = selected.get("digests", {})
            if not isinstance(filename, str) or not isinstance(url, str):
                raise RuntimeError(f"Invalid PyPI file metadata for {distribution}")
            if not isinstance(expected_hash, dict) or not isinstance(
                expected_hash.get("sha256"), str
            ):
                raise RuntimeError(f"Missing upstream SHA-256 for {filename}")
            upstream = temporary / filename
            _download(url, upstream)
            actual_hash = _sha256_path(upstream)
            if actual_hash != expected_hash["sha256"]:
                raise RuntimeError(f"Upstream SHA-256 mismatch for {filename}")
            output_name = _custom_filename(filename)
            output_path = output_dir / output_name
            _repack_wheel(upstream, output_path)
            manifest_entries.append(
                {
                    "distribution": distribution,
                    "upstream_version": UPSTREAM_VERSION,
                    "compatibility_version": COMPATIBILITY_VERSION,
                    "upstream_metadata_url": metadata_url,
                    "upstream_wheel_url": url,
                    "upstream_filename": filename,
                    "upstream_sha256": actual_hash,
                    "compatibility_filename": output_name,
                    "compatibility_sha256": _sha256_path(output_path),
                    "accepted_tags": sorted(accepted),
                    "upstream_requires_python": payload.get("info", {}).get(
                        "requires_python", ""
                    ),
                    "compatibility_requires_python": TARGET_REQUIRES_PYTHON,
                }
            )
    manifest: dict[str, object] = {
        "schema_version": 1,
        "status": "complete",
        "target_python": TARGET_PYTHON,
        "platform": platform.platform(),
        "source": "official PyPI Qt wheels",
        "compatibility_scope": "local wheelhouse only",
        "compatibility_version": COMPATIBILITY_VERSION,
        "target_requires_python": TARGET_REQUIRES_PYTHON,
        "install_policy": {
            "normal_pip_resolver": True,
            "ignore_requires_python": False,
            "metadata_rewrite_only": True,
            "source_binary_bytes_unchanged": True,
        },
        "wheels": sorted(manifest_entries, key=lambda item: str(item["distribution"])),
    }
    manifest_path = output_dir / "mohan-qt315-compatibility.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _wheel_metadata(path: Path) -> tuple[str, str, tuple[str, ...]]:
    with zipfile.ZipFile(path) as archive:
        metadata_names = tuple(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        wheel_names = tuple(
            name for name in archive.namelist() if name.endswith(".dist-info/WHEEL")
        )
        if len(metadata_names) != 1 or len(wheel_names) != 1:
            raise RuntimeError(f"Invalid wheel metadata members: {path.name}")
        metadata = archive.read(metadata_names[0]).decode("utf-8")
        wheel = archive.read(wheel_names[0]).decode("utf-8")
    version = next(
        line.partition(":")[2].strip()
        for line in metadata.splitlines()
        if line.startswith("Version:")
    )
    requires_python = next(
        line.partition(":")[2].strip()
        for line in metadata.splitlines()
        if line.startswith("Requires-Python:")
    )
    tags = tuple(
        line.partition(":")[2].strip()
        for line in wheel.splitlines()
        if line.startswith("Tag:")
    )
    return version, requires_python, tags


def verify_wheelhouse(wheelhouse: Path) -> dict[str, object]:
    wheelhouse = wheelhouse.resolve()
    manifest_path = wheelhouse / "mohan-qt315-compatibility.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("status") != "complete":
        raise RuntimeError("Qt compatibility manifest is incomplete")
    if manifest.get("compatibility_version") != COMPATIBILITY_VERSION:
        raise RuntimeError("Unexpected Qt compatibility version")
    entries = manifest.get("wheels")
    if not isinstance(entries, list) or len(entries) != len(QT_DISTRIBUTIONS):
        raise RuntimeError("Qt compatibility manifest has an incomplete wheel set")
    expected = set(QT_DISTRIBUTIONS)
    found: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("Invalid Qt compatibility manifest entry")
        distribution = entry.get("distribution")
        filename = entry.get("compatibility_filename")
        digest = entry.get("compatibility_sha256")
        if not isinstance(distribution, str) or not isinstance(filename, str):
            raise RuntimeError("Invalid Qt compatibility manifest identity")
        path = wheelhouse / filename
        if not path.is_file() or not isinstance(digest, str):
            raise RuntimeError(f"Missing Qt compatibility wheel: {filename}")
        if _sha256_path(path) != digest:
            raise RuntimeError(f"Qt compatibility wheel hash mismatch: {filename}")
        version, requires_python, tags = _wheel_metadata(path)
        if version != COMPATIBILITY_VERSION or requires_python != TARGET_REQUIRES_PYTHON:
            raise RuntimeError(f"Invalid compatibility metadata: {filename}")
        if not any("-abi3-" in tag for tag in tags):
            raise RuntimeError(f"Qt compatibility wheel is not stable ABI3: {filename}")
        found.add(distribution)
    if found != expected:
        raise RuntimeError(f"Qt compatibility wheel set mismatch: {found}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    manifest = build_wheelhouse(args.output_dir, args.requirements)
    verify_wheelhouse(args.output_dir)
    print(
        json.dumps(
            {
                "status": "complete",
                "compatibility_version": manifest["compatibility_version"],
                "wheelhouse": str(args.output_dir.resolve()),
                "wheels": len(manifest["wheels"]),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
