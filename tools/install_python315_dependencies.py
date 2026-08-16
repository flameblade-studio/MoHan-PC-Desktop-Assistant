from __future__ import annotations

lazy import argparse
lazy import importlib
lazy import re
lazy import subprocess
lazy import sys
lazy from importlib.metadata import distribution as metadata_distribution
lazy from pathlib import Path

lazy from build_python315_qt_compat import (
    COMPATIBILITY_VERSION,
    QT_DISTRIBUTIONS,
    verify_wheelhouse,
)
lazy from check_python315_qt_release import inspect_official_release

ROOT = Path(__file__).resolve().parents[1]
ABI3_TAG = re.compile(r"^Tag:\s+cp3\d+-abi3-", re.MULTILINE)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install and verify MoHan dependencies on Python 3.15."
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        default=ROOT / "requirements.txt",
    )
    parser.add_argument(
        "--qt-compat-wheelhouse",
        type=Path,
        help=(
            "Use the verified project-owned Python 3.15 Qt compatibility "
            "wheelhouse through the normal pip resolver."
        ),
    )
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args()


def requirement_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def verify_qt_stable_abi() -> None:
    for distribution_name in QT_DISTRIBUTIONS:
        distribution = metadata_distribution(distribution_name)
        wheel = distribution.read_text("WHEEL") or ""
        if not ABI3_TAG.search(wheel):
            raise RuntimeError(
                f"{distribution_name} is not installed from a CPython stable-ABI wheel"
            )
    qt_core = importlib.import_module("PySide6.QtCore")
    if not qt_core.qVersion():
        raise RuntimeError("PySide6 Qt runtime did not initialize")


def verify_qt_compatibility_install() -> None:
    for distribution_name in QT_DISTRIBUTIONS:
        distribution = metadata_distribution(distribution_name)
        if distribution.version != COMPATIBILITY_VERSION:
            raise RuntimeError(
                f"{distribution_name} is not installed from the verified "
                f"MoHan Qt compatibility version {COMPATIBILITY_VERSION}"
            )


def pip_install(requirements: list[str]) -> None:
    if not requirements:
        return
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--only-binary=:all:",
            *requirements,
        ],
        check=True,
    )


def pip_install_qt_compatibility(wheelhouse: Path) -> None:
    verify_wheelhouse(wheelhouse)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--only-binary=:all:",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            f"PySide6=={COMPATIBILITY_VERSION}",
        ],
        check=True,
    )


def main() -> int:
    args = arguments()
    if sys.version_info[:2] != (3, 15):
        raise SystemExit("MoHan dependencies must be installed with Python 3.15.")
    requirements_path = args.requirements.resolve()
    requirements = requirement_lines(requirements_path)
    qt = [item for item in requirements if item.casefold().startswith("pyside6==")]
    if len(qt) != 1:
        raise SystemExit("Expected exactly one pinned PySide6 requirement.")

    if not args.verify_only:
        non_qt_requirements = [
            item
            for item in requirements
            if not item.casefold().startswith("pyside6==")
        ]
        if args.qt_compat_wheelhouse:
            pip_install_qt_compatibility(args.qt_compat_wheelhouse.resolve())
            pip_install(non_qt_requirements)
        else:
            report = inspect_official_release(requirements=requirements_path)
            if not report.releasable:
                details = "\n".join(f"- {issue}" for issue in report.issues)
                raise SystemExit(
                    "Official Qt for Python metadata blocks this clean install:\n"
                    f"{details}\n"
                    "Use the verified MoHan Qt compatibility wheelhouse; do not "
                    "bypass the resolver's Python-version metadata check."
                )
            pip_install(requirements)
    verify_qt_stable_abi()
    if args.qt_compat_wheelhouse:
        verify_qt_compatibility_install()
    print("PYTHON315_DEPENDENCIES_AND_QT_STABLE_ABI_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
