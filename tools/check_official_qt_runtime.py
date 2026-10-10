"""Verify MoHan's official Qt for Python runtime and download provenance."""

from __future__ import annotations

lazy import argparse
lazy import importlib
lazy import json
lazy import platform
lazy import subprocess
lazy import sys
lazy from collections import Counter
lazy from importlib.metadata import PackageNotFoundError, distribution
lazy from pathlib import Path
lazy from typing import Final
lazy from urllib.parse import unquote, urlsplit
lazy from pip._vendor.packaging.specifiers import SpecifierSet
lazy from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
lazy from pip._vendor.packaging.version import Version

ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_LOCK: Final = ROOT / "tools" / "qt" / "official-wheel-lock.json"
DEFAULT_HASH_REQUIREMENTS: Final = ROOT / "requirements-qt.txt"
QT_VERSION: Final = "6.12.0"
QT_DISTRIBUTIONS: Final = (
    "PySide6",
    "PySide6_Addons",
    "PySide6_Essentials",
    "shiboken6",
)
QT_CANONICAL_NAMES: Final = frozenset(
    canonicalize_name(name) for name in QT_DISTRIBUTIONS
)
EXPECTED_WHEEL_COUNT: Final = 20
EXPECTED_WHEELS_PER_DISTRIBUTION: Final = 5
SHA256_HEXDIGEST_LENGTH: Final = 64


def pinned_pyside_version(requirements: Path) -> str:
    pins = [
        line.partition("==")[2].strip()
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip().casefold().startswith("pyside6==")
    ]
    if pins != [QT_VERSION]:
        raise RuntimeError(
            f"{requirements} must contain exactly PySide6=={QT_VERSION}; found {pins}"
        )
    return pins[0]


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == SHA256_HEXDIGEST_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def load_official_wheel_lock(path: Path = DEFAULT_LOCK) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read official Qt wheel lock {path}: {error}") from error
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RuntimeError("Official Qt wheel lock requires schema_version 1")
    if payload.get("qt_version") != QT_VERSION:
        raise RuntimeError(f"Official Qt wheel lock must target {QT_VERSION}")
    wheels = payload.get("wheels")
    if not isinstance(wheels, list) or len(wheels) != EXPECTED_WHEEL_COUNT:
        raise RuntimeError(
            f"Official Qt wheel lock requires {EXPECTED_WHEEL_COUNT} wheels"
        )

    filenames: set[str] = set()
    distribution_counts: Counter[str] = Counter()
    for entry in wheels:
        if not isinstance(entry, dict):
            raise RuntimeError("Official Qt wheel lock entries must be objects")
        filename = entry.get("filename")
        digest = entry.get("sha256")
        size = entry.get("size")
        requires_python = entry.get("requires_python")
        if (
            not isinstance(filename, str)
            or not filename.endswith(".whl")
            or not _valid_sha256(digest)
            or not isinstance(size, int)
            or size <= 0
            or not isinstance(requires_python, str)
            or not requires_python
        ):
            raise RuntimeError("Official Qt wheel lock entry fields are invalid")
        if filename in filenames:
            raise RuntimeError(f"Official Qt wheel lock repeats {filename}")
        filenames.add(filename)
        try:
            parsed_name, version, _, tags = parse_wheel_filename(filename)
        except ValueError as error:
            raise RuntimeError(f"Invalid locked Qt wheel filename: {filename}") from error
        canonical_name = canonicalize_name(parsed_name)
        if canonical_name not in QT_CANONICAL_NAMES or str(version) != QT_VERSION:
            raise RuntimeError(f"Unexpected locked Qt wheel identity: {filename}")
        if not any(tag.interpreter == "cp310" and tag.abi == "abi3" for tag in tags):
            raise RuntimeError(f"Locked Qt wheel is not cp310-abi3: {filename}")
        if not SpecifierSet(requires_python).contains(
            Version("3.15.0"),
            prereleases=True,
        ):
            raise RuntimeError(f"Locked Qt wheel excludes Python 3.15: {filename}")
        distribution_counts[canonical_name] += 1

    expected_counts = dict.fromkeys(
        QT_CANONICAL_NAMES,
        EXPECTED_WHEELS_PER_DISTRIBUTION,
    )
    if dict(distribution_counts) != expected_counts:
        raise RuntimeError(
            "Official Qt wheel lock must cover five platforms for every distribution"
        )
    return payload


def _locked_wheels(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    wheels = payload["wheels"]
    if not isinstance(wheels, list):
        raise RuntimeError("Official Qt wheel lock has no wheel entries")
    return {
        str(entry["filename"]): entry
        for entry in wheels
        if isinstance(entry, dict) and "filename" in entry
    }


def hashed_requirements_text(lock: dict[str, object]) -> str:
    """Return pip's complete hash-checking input for the official Qt closure."""
    wheels = _locked_wheels(lock)
    hashes_by_distribution: dict[str, list[str]] = {
        canonicalize_name(name): [] for name in QT_DISTRIBUTIONS
    }
    for filename, entry in sorted(wheels.items()):
        parsed_name, _, _, _ = parse_wheel_filename(filename)
        canonical_name = canonicalize_name(parsed_name)
        digest = entry.get("sha256")
        if canonical_name not in hashes_by_distribution or not _valid_sha256(digest):
            raise RuntimeError(f"Cannot build hashed requirements from {filename}")
        hashes_by_distribution[canonical_name].append(str(digest))

    lines = [
        "# Hash-locked official Qt for Python wheels.",
        "# Source of truth: tools/qt/official-wheel-lock.json.",
        "",
    ]
    for distribution_name in QT_DISTRIBUTIONS:
        hashes = hashes_by_distribution[canonicalize_name(distribution_name)]
        if len(hashes) != EXPECTED_WHEELS_PER_DISTRIBUTION:
            raise RuntimeError(
                f"Official Qt hash requirements are incomplete for {distribution_name}"
            )
        lines.append(f"{distribution_name}=={QT_VERSION} \\")
        for index, digest in enumerate(hashes):
            suffix = " \\" if index < len(hashes) - 1 else ""
            lines.append(f"    --hash=sha256:{digest}{suffix}")
        lines.append("")
    return "\n".join(lines)


def validate_hashed_requirements(path: Path, lock: dict[str, object]) -> None:
    try:
        actual = path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(f"Cannot read official Qt hash requirements {path}: {error}") from error
    if actual != hashed_requirements_text(lock):
        raise RuntimeError(
            f"Official Qt hash requirements {path} do not match the wheel lock"
        )


def _report_digest(download_info: dict[str, object]) -> str:
    archive_info = download_info.get("archive_info")
    if not isinstance(archive_info, dict):
        return ""
    hashes = archive_info.get("hashes")
    if isinstance(hashes, dict) and isinstance(hashes.get("sha256"), str):
        return str(hashes["sha256"])
    digest = archive_info.get("hash")
    if isinstance(digest, str) and digest.startswith("sha256="):
        return digest.removeprefix("sha256=")
    return ""


def inspect_pip_report(
    path: Path,
    lock: dict[str, object],
) -> tuple[str, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return (f"Cannot read pip installation report {path}: {error}",)
    if not isinstance(payload, dict) or not isinstance(payload.get("install"), list):
        return ("pip installation report has no install list",)

    locked = _locked_wheels(lock)
    found: set[str] = set()
    issues: list[str] = []
    for item in payload["install"]:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            continue
        canonical_name = canonicalize_name(str(metadata.get("name", "")))
        if canonical_name not in QT_CANONICAL_NAMES:
            continue
        if canonical_name in found:
            issues.append(f"pip report repeats Qt distribution {canonical_name}")
            continue
        found.add(canonical_name)
        version = str(metadata.get("version", ""))
        download_info = item.get("download_info")
        if not isinstance(download_info, dict):
            issues.append(f"pip report has no download provenance for {canonical_name}")
            continue
        url = str(download_info.get("url", ""))
        filename = unquote(Path(urlsplit(url).path).name)
        expected = locked.get(filename)
        if version != QT_VERSION:
            issues.append(f"pip installed {canonical_name} {version}; expected {QT_VERSION}")
        if expected is None:
            issues.append(f"pip selected an unlocked official Qt wheel: {filename}")
            continue
        digest = _report_digest(download_info)
        if digest != expected["sha256"]:
            issues.append(f"pip report SHA-256 mismatch for {filename}")

    missing = sorted(QT_CANONICAL_NAMES - found)
    if missing:
        issues.append(f"pip report is missing official Qt distributions: {missing}")
    return tuple(issues)


def inspect_installed_runtime() -> tuple[str, ...]:
    target = Version(platform.python_version())
    issues: list[str] = []
    for distribution_name in QT_DISTRIBUTIONS:
        try:
            installed = distribution(distribution_name)
        except PackageNotFoundError:
            issues.append(f"{distribution_name} is not installed")
            continue
        if installed.version != QT_VERSION:
            issues.append(
                f"{distribution_name} version is {installed.version}; expected {QT_VERSION}"
            )
        requires_python = installed.metadata.get("Requires-Python", "")
        if not requires_python or not SpecifierSet(requires_python).contains(
            target,
            prereleases=True,
        ):
            issues.append(
                f"{distribution_name} Requires-Python {requires_python!r} "
                f"excludes Python {target}"
            )
        wheel_file = next(
            (
                file
                for file in installed.files or ()
                if file.name == "WHEEL" and file.parent.name.endswith(".dist-info")
            ),
            None,
        )
        if wheel_file is None:
            issues.append(f"{distribution_name} has no installed WHEEL metadata")
            continue
        wheel_path = Path(installed.locate_file(wheel_file))
        try:
            wheel_metadata = wheel_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            issues.append(f"Cannot read {distribution_name} WHEEL metadata: {error}")
            continue
        wheel_tags = tuple(
            line.partition(":")[2].strip()
            for line in wheel_metadata.splitlines()
            if line.startswith("Tag:")
        )
        if not any(tag.startswith("cp310-abi3-") for tag in wheel_tags):
            issues.append(f"{distribution_name} is not installed from a cp310-abi3 wheel")

    if issues:
        return tuple(issues)
    pyside = importlib.import_module("PySide6")
    qt_core = importlib.import_module("PySide6.QtCore")
    if str(pyside.__version__) != QT_VERSION:
        issues.append(f"PySide6.__version__ is {pyside.__version__}; expected {QT_VERSION}")
    if str(qt_core.qVersion()) != QT_VERSION:
        issues.append(f"Qt runtime is {qt_core.qVersion()}; expected {QT_VERSION}")
    return tuple(issues)


def inspect_pip_check() -> tuple[str, ...]:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return ()
    details = (result.stdout + result.stderr).strip()
    return (f"pip check failed: {details}",)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify the pinned official Qt for Python wheels, their Python "
            "support declaration, and the initialized Qt runtime."
        )
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        default=ROOT / "requirements.txt",
    )
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument(
        "--hash-requirements",
        type=Path,
        default=DEFAULT_HASH_REQUIREMENTS,
    )
    parser.add_argument("--pip-report", type=Path)
    parser.add_argument(
        "--policy-only",
        action="store_true",
        help="Validate checked-in pins and official wheel evidence before installation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    issues: list[str] = []
    try:
        pinned_pyside_version(args.requirements.resolve())
        lock = load_official_wheel_lock(args.lock.resolve())
        validate_hashed_requirements(args.hash_requirements.resolve(), lock)
    except RuntimeError as error:
        issues.append(str(error))
        lock = {}
    if not args.policy_only and args.pip_report is None:
        issues.append("Runtime verification requires a pip installation report")
    elif args.pip_report is not None and lock:
        issues.extend(inspect_pip_report(args.pip_report.resolve(), lock))
    if not issues and not args.policy_only:
        issues.extend(inspect_installed_runtime())
        issues.extend(inspect_pip_check())
    payload = {
        "status": "passed" if not issues else "blocked",
        "python": platform.python_version(),
        "qt_version": QT_VERSION,
        "official_wheel_lock": str(args.lock.resolve()),
        "hash_requirements": str(args.hash_requirements.resolve()),
        "pip_report": str(args.pip_report.resolve()) if args.pip_report else None,
        "issues": issues,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if issues:
        return 1
    print("OFFICIAL_QT_RUNTIME_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
