from __future__ import annotations

lazy import argparse
lazy import json
lazy from dataclasses import asdict, dataclass
lazy from pathlib import Path
lazy from typing import Final
lazy from urllib.request import urlopen

try:
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version
except ImportError:
    from pip._vendor.packaging.specifiers import SpecifierSet
    from pip._vendor.packaging.version import Version

ROOT: Final = Path(__file__).resolve().parents[1]
TARGET_PYTHON: Final = "3.15.0rc1"
QT_VERSION: Final = "6.11.1"
QT_DISTRIBUTIONS: Final = (
    "PySide6",
    "PySide6_Addons",
    "PySide6_Essentials",
    "shiboken6",
)
PYPI_JSON_TEMPLATE: Final = "https://pypi.org/pypi/{name}/{version}/json"


@dataclass(frozen=True, slots=True)
class QtMetadataEvidence:
    distribution: str
    version: str
    requires_python: str
    source: str
    target_supported: bool


@dataclass(frozen=True, slots=True)
class QtReleaseReport:
    target_python: str
    qt_version: str
    evidence: tuple[QtMetadataEvidence, ...]
    issues: tuple[str, ...]

    @property
    def releasable(self) -> bool:
        return not self.issues


def pinned_pyside_version(requirements: Path) -> str:
    pins = [
        line.partition("==")[2].strip()
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip().casefold().startswith("pyside6==")
    ]
    if len(pins) != 1 or not pins[0]:
        raise ValueError("requirements must contain exactly one exact PySide6 pin")
    return pins[0]


def metadata_url(distribution: str, version: str) -> str:
    return PYPI_JSON_TEMPLATE.format(name=distribution, version=version)


def load_official_metadata(distribution: str, version: str) -> tuple[dict, str]:
    source = metadata_url(distribution, version)
    with urlopen(source, timeout=30) as response:
        payload = json.load(response)
    return payload, source


def load_snapshot_metadata(
    directory: Path,
    distribution: str,
) -> tuple[dict, str]:
    path = directory / f"{distribution}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload, f"snapshot:{path}"


def inspect_metadata(
    metadata_by_distribution: dict[str, tuple[dict, str]],
    *,
    target_python: str = TARGET_PYTHON,
    qt_version: str = QT_VERSION,
) -> QtReleaseReport:
    target = Version(target_python)
    evidence: list[QtMetadataEvidence] = []
    issues: list[str] = []
    for distribution in QT_DISTRIBUTIONS:
        payload, source = metadata_by_distribution[distribution]
        info = payload.get("info", {})
        actual_version = str(info.get("version", ""))
        requires_python = str(info.get("requires_python", ""))
        supported = bool(requires_python) and SpecifierSet(requires_python).contains(
            target,
            prereleases=True,
        )
        evidence.append(
            QtMetadataEvidence(
                distribution=distribution,
                version=actual_version,
                requires_python=requires_python,
                source=source,
                target_supported=supported,
            )
        )
        if actual_version != qt_version:
            issues.append(
                f"{distribution} metadata version is {actual_version!r}; expected {qt_version}."
            )
        if not supported:
            issues.append(
                f"{distribution} {actual_version} declares Requires-Python "
                f"{requires_python!r}, which excludes Python {target_python}."
            )
    return QtReleaseReport(target_python, qt_version, tuple(evidence), tuple(issues))


def inspect_official_release(
    *,
    requirements: Path = ROOT / "requirements.txt",
    target_python: str = TARGET_PYTHON,
) -> QtReleaseReport:
    qt_version = pinned_pyside_version(requirements)
    metadata = {
        distribution: load_official_metadata(distribution, qt_version)
        for distribution in QT_DISTRIBUTIONS
    }
    return inspect_metadata(
        metadata,
        target_python=target_python,
        qt_version=qt_version,
    )


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fail closed unless official PyPI metadata permits MoHan's pinned "
            "Qt for Python release on Python 3.15."
        )
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        default=ROOT / "requirements.txt",
    )
    parser.add_argument("--python-version", default=TARGET_PYTHON)
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        help="Use test/evidence JSON snapshots instead of querying official PyPI.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    qt_version = pinned_pyside_version(args.requirements.resolve())
    if args.metadata_dir:
        metadata = {
            distribution: load_snapshot_metadata(
                args.metadata_dir.resolve(),
                distribution,
            )
            for distribution in QT_DISTRIBUTIONS
        }
        report = inspect_metadata(
            metadata,
            target_python=args.python_version,
            qt_version=qt_version,
        )
    else:
        report = inspect_official_release(
            requirements=args.requirements.resolve(),
            target_python=args.python_version,
        )
    print(
        json.dumps(
            {
                "releasable": report.releasable,
                "target_python": report.target_python,
                "qt_version": report.qt_version,
                "evidence": [asdict(item) for item in report.evidence],
                "issues": report.issues,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report.releasable else 1


if __name__ == "__main__":
    raise SystemExit(main())
