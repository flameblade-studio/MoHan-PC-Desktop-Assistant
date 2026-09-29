from __future__ import annotations

lazy import argparse
lazy import importlib
lazy import re
lazy import shutil
lazy import subprocess
lazy import sys
lazy import tempfile
lazy from importlib.metadata import distribution as metadata_distribution
lazy from pathlib import Path

lazy from build_python315_qt_compat import (
    COMPATIBILITY_VERSION,
    QT_DISTRIBUTIONS,
    build_wheelhouse,
    verify_wheelhouse,
)
lazy from check_python315_qt_release import inspect_official_release
lazy from qt315_wheel_lock import (
    DEFAULT_LOCK,
    default_shared_wheelhouse,
    verify_locked_wheelhouse,
)

ROOT = Path(__file__).resolve().parents[1]
ABI3_TAG = re.compile(r"^Tag:\s+cp3\d+-abi3-", re.MULTILINE)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
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
    parser.add_argument(
        "--like-ci",
        action="store_true",
        help=(
            "Build or reuse the hash-locked CI Qt wheel set, then install and "
            "verify dependencies through the same path used by Windows CI."
        ),
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Prepare and verify the --like-ci wheelhouse without installing.",
    )
    return parser.parse_args(argv)


def prepare_like_ci_wheelhouse(wheelhouse: Path, requirements: Path) -> None:
    wheelhouse = wheelhouse.resolve()
    if wheelhouse.exists():
        verify_wheelhouse(wheelhouse)
        verify_locked_wheelhouse(wheelhouse, DEFAULT_LOCK)
        print(f"QT315_LIKE_CI_WHEELHOUSE_REUSED path={wheelhouse}")
        return
    wheelhouse.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="mohan-qt315-ci-",
        dir=wheelhouse.parent,
    ) as temporary:
        staged = Path(temporary) / "wheelhouse"
        build_wheelhouse(staged, requirements)
        verify_wheelhouse(staged)
        verify_locked_wheelhouse(staged, DEFAULT_LOCK)
        shutil.move(str(staged), str(wheelhouse))
    print(f"QT315_LIKE_CI_WHEELHOUSE_BUILT path={wheelhouse}")


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
        raise RuntimeError("PySide6 Qt runtime initialization requires attention")


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


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    if sys.version_info[:2] != (3, 15):
        raise SystemExit("MoHan dependencies must be installed with Python 3.15.")
    requirements_path = args.requirements.resolve()
    if args.like_ci:
        if args.qt_compat_wheelhouse is None:
            args.qt_compat_wheelhouse = default_shared_wheelhouse()
        prepare_like_ci_wheelhouse(
            args.qt_compat_wheelhouse,
            requirements_path,
        )
        if args.prepare_only:
            print("QT315_LIKE_CI_WHEELHOUSE_READY")
            return 0
    elif args.prepare_only:
        raise SystemExit("--prepare-only requires --like-ci")
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
                    "This clean install requires compatible official Qt for Python metadata:\n"
                    f"{details}\n"
                    "Use the verified MoHan Qt compatibility wheelhouse and preserve "
                    "the resolver's Python-version metadata check."
                )
            pip_install(requirements)
    verify_qt_stable_abi()
    if args.qt_compat_wheelhouse:
        verify_qt_compatibility_install()
    print("PYTHON315_DEPENDENCIES_AND_QT_STABLE_ABI_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
