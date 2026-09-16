"""Verify retained MPL notices and exact, available source snapshots."""

from __future__ import annotations

lazy import argparse
lazy from email.parser import Parser
lazy import hashlib
lazy import json
lazy from pathlib import Path, PurePosixPath
lazy import re
lazy import sys
lazy from zipfile import BadZipFile, ZipFile


MANIFEST = "third_party_licenses/mpl/components.json"
SCHEMA = "mohan.mpl-compliance.v1"
EXPRESSIONS = frozenset({
    "MPL-2.0", "MPL-2.0 AND MIT", "MPL-2.0 AND (Apache-2.0 OR MIT)",
})
SHA_PATTERN = re.compile(r"[0-9a-fA-F]{64}")
MAX_SOURCE_BYTES = 32 * 1024 * 1024
MPL_TEXT_SHA256 = "3f3d9e0024b1921b067d6f7f88deb4a60cbe7a78e76c64e3f1d7fc3b779b9d04"


def _relative(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("evidence path must be a portable relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in (".", "..", "") for part in value.split("/")):
        raise ValueError("evidence path escapes its root")
    return value


def _digest(value: object) -> str:
    if not isinstance(value, str) or not SHA_PATTERN.fullmatch(value):
        raise ValueError("evidence SHA-256 requires the valid digest format")
    return value.lower()


def _artifact(root: Path, record: object) -> Path:
    if not isinstance(record, dict):
        raise ValueError("artifact record must be an object")
    path = (root / _relative(record.get("path"))).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("evidence symlink escapes its root")
    if hashlib.sha256(path.read_bytes()).hexdigest() != _digest(record.get("sha256")):
        raise ValueError(f"evidence hash mismatch: {record['path']}")
    return path


def _text(record: dict, key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing {key}")
    return value


def _file_rows(rows: object) -> dict[str, str]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("file evidence must be nonempty")
    files: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("source entry must be an object")
        name = _relative(row.get("path"))
        if name in files:
            raise ValueError("duplicate source entry")
        files[name] = _digest(row.get("sha256"))
    return files


def _source_rows(component: dict) -> dict[str, str]:
    files = _file_rows(component.get("source_files"))
    if not any(name.endswith((".py", ".rs", ".c", ".h")) for name in files):
        raise ValueError("source snapshot requires editable source files")
    return files


def _package_root(component: dict) -> str:
    name = _text(component, "name").replace("-", "_")
    if not name.isidentifier():
        raise ValueError("component name must identify one Python package")
    return name


def _verify_component(root: Path, component: object) -> None:
    if not isinstance(component, dict):
        raise ValueError("component must be an object")
    for key in ("name", "version", "scope", "upstream_url"):
        _text(component, key)
    if not component["upstream_url"].startswith("https://"):
        raise ValueError("upstream source URL must use HTTPS")
    if component.get("license_expression") not in EXPRESSIONS:
        raise ValueError("unreviewed MPL license expression")
    if component.get("source_status") not in {"installed-source-snapshot", "upstream-source-archive"}:
        raise ValueError("source snapshot status must be explicit")
    if component["source_status"] == "upstream-source-archive":
        installed = _file_rows(component.get("installed_files"))
        package_root = _package_root(component)
        metadata_root = f"{package_root}-{component['version']}.dist-info"
        if any(name.split("/")[0] not in {package_root, metadata_root} for name in installed):
            raise ValueError("installed file requires membership in the declared component")
        if not any(name.startswith(package_root + "/") and name.endswith((".pyd", ".so")) for name in installed):
            raise ValueError("upstream source evidence must identify its installed extension")
    notices = component.get("notices")
    if not isinstance(notices, list) or not notices:
        raise ValueError("provide the component notices")
    archive = _artifact(root, component.get("source_archive"))
    files = _source_rows(component)
    for notice in notices:
        path = _artifact(root, notice)
        if not path.read_bytes().strip() or notice["sha256"] not in files.values():
            raise ValueError("retain the component notice in its source archive")
    with ZipFile(archive) as bundle:
        entries = bundle.infolist()
        names = [_relative(entry.filename) for entry in entries]
        if len(set(names)) != len(names) or set(names) != set(files):
            raise ValueError("source archive entries differ from the source ledger")
        if sum(entry.file_size for entry in entries) > MAX_SOURCE_BYTES:
            raise ValueError("source archive exceeds its verification size limit")
        for name in names:
            if hashlib.sha256(bundle.read(name)).hexdigest() != files[name]:
                raise ValueError(f"source archive content mismatch: {name}")


def _load(root: Path) -> dict:
    data = json.loads((root / MANIFEST).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("unsupported MPL evidence schema")
    components = data.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("MPL components must be nonempty")
    return data


def verify_evidence(root: Path) -> list[str]:
    """Return all evidence errors; an empty list certifies this manifest only."""
    errors: list[str] = []
    try:
        data = _load(root)
        license_path = _artifact(root, data.get("license_text"))
        if hashlib.sha256(license_path.read_bytes()).hexdigest() != MPL_TEXT_SHA256:
            raise ValueError("provide the full MPL license text")
    except (OSError, ValueError, TypeError) as error:
        return [str(error)]
    seen: set[tuple[str, str]] = set()
    for component in data["components"]:
        try:
            _verify_component(root, component)
            identity = (component["name"].casefold(), component["version"])
            if identity in seen:
                raise ValueError("duplicate MPL component version")
            seen.add(identity)
        except (OSError, ValueError, TypeError, BadZipFile, RuntimeError) as error:
            errors.append(str(error))
    return errors


def verify_environment(root: Path, site_packages: Path) -> list[str]:
    """Inspect metadata/source exclusively as data."""
    errors = verify_evidence(root)
    if errors:
        return errors
    if not site_packages.is_dir():
        return [f"site-packages is missing: {site_packages}"]
    data = _load(root)
    known = {(item["name"].casefold(), item["version"]): item for item in data["components"]}
    found: set[str] = set()
    for metadata_path in sorted(site_packages.glob("*.dist-info/METADATA")):
        try:
            metadata = Parser().parsestr(metadata_path.read_text(encoding="utf-8"))
            expression = metadata.get("License-Expression") or metadata.get("License", "")
            classifiers = metadata.get_all("Classifier", [])
            is_mpl = bool(re.search(r"\bMPL(?:-2\.0)?\b", expression, re.IGNORECASE))
            is_mpl = is_mpl or "MOZILLA PUBLIC LICENSE" in expression.upper()
            if not is_mpl and not any("Mozilla Public License" in value for value in classifiers):
                continue
            key = (metadata.get("Name", "").casefold(), metadata.get("Version", ""))
            found.add(key[0])
            component = known.get(key)
            if component is None:
                raise ValueError(f"MPL source evidence missing for {key[0]} {key[1]}")
            if expression != component["license_expression"]:
                raise ValueError(f"MPL license expression drift: {key[0]}")
            installed = (
                _file_rows(component.get("installed_files"))
                if component["source_status"] == "upstream-source-archive"
                else _source_rows(component)
            )
            package_root = _package_root(component)
            actual = {
                path.relative_to(site_packages).as_posix()
                for path in (site_packages / package_root).rglob("*")
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
            }
            expected = {name for name in installed if name.startswith(package_root + "/")}
            if actual != expected:
                raise ValueError(f"installed MPL file inventory changed: {key[0]}")
            for name, digest in installed.items():
                path = (site_packages / name).resolve()
                if not path.is_relative_to(site_packages.resolve()):
                    raise ValueError("installed source symlink escapes site-packages")
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError(f"installed MPL source changed: {name}")
        except (OSError, ValueError, TypeError) as error:
            errors.append(str(error))
    for component in data["components"]:
        if (site_packages / _package_root(component)).exists() and component["name"].casefold() not in found:
            errors.append(f"MPL package metadata is missing or changed: {component['name']}")
    return errors


def verify_policy(root: Path) -> list[str]:
    """Require the owner's explicit project allowlist entry."""
    try:
        policy = json.loads((root / "THIRD_PARTY_DENYLIST.json").read_text(encoding="utf-8-sig"))
        if "MPL-2.0" not in policy["policy"]["allowed_licenses"]:
            return ["MPL-2.0 use requires authorization in the project allowlist"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        return [f"MPL project policy unavailable: {error}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--site-packages", type=Path, action="append", default=[])
    parser.add_argument("--require-allowlist", action="store_true")
    args = parser.parse_args()
    errors = verify_evidence(args.root)
    if args.require_allowlist:
        errors.extend(verify_policy(args.root))
    for path in args.site_packages:
        errors.extend(verify_environment(args.root, path))
    if errors:
        for error in sorted(set(errors)):
            print(error, file=sys.stderr)
        return 2
    print("MPL_COMPLIANCE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
